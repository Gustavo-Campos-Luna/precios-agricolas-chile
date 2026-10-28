"""ODEPA CKAN: descubrimiento, descarga inmutable y normalización mayorista.

El precio queda en CLP por unidad comercial original. No se supone que una
caja pese un número fijo de kilos ni que la región de mercado sea el origen.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import time
import unicodedata
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import pandas as pd

from .storage import atomic_write, receipt, write_json

API = "https://datos.odepa.gob.cl/api/3/action/"
DATASET = "precios-mayoristas-de-frutas-y-hortalizas"


def fetch(url: str, *, attempts: int = 3, timeout: int = 90) -> bytes:
    """GET con TLS verificado, identificación, timeout y reintentos acotados."""
    if urlparse(url).scheme != "https":
        raise ValueError("Solo se aceptan fuentes HTTPS")
    last_error = None
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers={"User-Agent": "MateriasPrimasChile/0.1 (academic data collection)"}), timeout=timeout) as response:
                return response.read()
        except OSError as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"No se pudo descargar {url}: {last_error}") from last_error


def discover_resources(dataset: str = DATASET) -> list[dict]:
    payload = json.loads(fetch(API + "package_show?" + urlencode({"id": dataset})))
    if not payload.get("success"):
        raise ValueError(f"CKAN rechazó package_show: {payload.get('error')}")
    return [resource for resource in payload["result"]["resources"] if resource.get("format", "").upper() == "CSV"]


def download_datastore(resource: dict, root: str | Path, *, page_size: int = 10000) -> Path:
    """Ruta alternativa CKAN paginada; exige total estable y no acepta truncamiento.

    Guarda JSON en lugar de aparentar que se recuperaron los bytes CSV originales.
    Para grandes históricos se recomienda CSV anual por consumo de memoria.
    """
    if not 1 <= page_size <= 10000:
        raise ValueError("page_size debe estar entre 1 y 10000")
    rows, offset, expected_total = [], 0, None
    while True:
        url = API + "datastore_search?" + urlencode({"resource_id": resource["id"], "limit": page_size, "offset": offset})
        payload = json.loads(fetch(url))
        if not payload.get("success"):
            raise ValueError(f"DataStore rechazó consulta: {payload.get('error')}")
        result = payload["result"]
        total = int(result["total"])
        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise ValueError("El recurso cambió durante paginación; repetir con snapshot CSV")
        records = result["records"]
        if not records and offset < total:
            raise ValueError("DataStore truncado: faltan registros")
        rows.extend(records)
        offset += len(records)
        if offset >= total:
            break
    payload = (json.dumps(rows, ensure_ascii=False) + "\n").encode()
    digest = hashlib.sha256(payload).hexdigest()
    path = Path(root) / "odepa" / resource["id"] / f"{digest}.json"
    atomic_write(path, payload)
    receipt(path, url=API + "datastore_search?" + urlencode({"resource_id": resource["id"]}),
            source="ODEPA", resource_id=resource["id"], retrieval_method="CKAN DataStore paginated",
            row_count=len(rows), complete_resource=len(rows) == expected_total)
    return path


def download_resource(resource: dict, root: str | Path) -> Path:
    """Snapshot por hash; repetir descarga no sobrescribe versiones anteriores."""
    payload = fetch(resource["url"])
    digest = hashlib.sha256(payload).hexdigest()
    resource_id = resource["id"]
    if not re.fullmatch(r"[A-Za-z0-9_-]+", resource_id):
        raise ValueError("resource id inseguro")
    path = Path(root) / "odepa" / resource_id / f"{digest}.csv"
    if not path.exists():
        atomic_write(path, payload)
    receipt(path, url=resource["url"], source="ODEPA", resource_id=resource_id,
            resource_name=resource.get("name"), resource_last_modified=resource.get("last_modified"),
            license="cc-by", complete_resource=True)
    write_json(path.parent / "resource.json", resource)
    return path


def read_csv(path: str | Path) -> pd.DataFrame:
    """Detecta UTF-8/Latin-1 y separador; mantiene números originales como texto."""
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    try:
        delimiter = csv.Sniffer().sniff(text[:32768], delimiters=";,\t|").delimiter
    except csv.Error:
        delimiter = ";"
    return pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, keep_default_na=False)


def _key(value: object) -> str:
    plain = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", plain).strip("_")


def _number(value: object) -> float:
    text = str(value).strip().replace(" ", "").replace("\u00a0", "")
    if not text or text.lower() in {"nan", "none", "null", "s/i", "-"}:
        return float("nan")
    # ODEPA CSV: decimal coma; miles punto cuando existe decimal coma.
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return pd.to_numeric(text, errors="coerce")


def normalize_prices(frame: pd.DataFrame, source_resource_id: str = "") -> pd.DataFrame:
    """Falla ante cambios de contrato, preserva columnas extra como source_record."""
    data = frame.rename(columns={column: _key(column) for column in frame.columns}).copy()
    mapping = {
        "fecha": "date", "id_region": "market_region_code", "region": "market_region",
        "mercado": "market", "subsector": "subsector", "producto": "product",
        "variedad_tipo": "variety", "calidad": "quality", "unidad_de_comercializacion": "unit",
        "origen": "origin", "volumen": "volume", "precio_minimo": "price_min",
        "precio_maximo": "price_max", "precio_promedio": "price",
    }
    required = set(mapping) - {"subsector", "volumen", "precio_minimo", "precio_maximo"}
    missing = required - set(data)
    if missing:
        raise ValueError(f"Cambio de esquema ODEPA: faltan {sorted(missing)}; columnas={list(data)}")
    result = pd.DataFrame(index=data.index)
    for original, canonical in mapping.items():
        result[canonical] = data[original].fillna("").astype(str).str.strip() if original in data else pd.NA
    date_text = result["date"].astype(str)
    # ISO first; DD/MM/YYYY separately to prevent pandas mixed-format ambiguity.
    iso = date_text.str.match(r"^\d{4}-\d{2}-\d{2}")
    parsed = pd.Series(pd.NaT, index=result.index, dtype="datetime64[ns]")
    parsed.loc[iso] = pd.to_datetime(date_text.loc[iso], errors="coerce")
    parsed.loc[~iso] = pd.to_datetime(date_text.loc[~iso], dayfirst=True, errors="coerce")
    result["date"] = parsed
    for column in ("price", "price_min", "price_max", "volume"):
        result[column] = result[column].map(_number)
    result["currency"] = "CLP"
    result["market_level"] = "wholesale"
    result["source"] = "ODEPA"
    result["source_resource_id"] = source_resource_id
    dimensions = ["market_region_code", "market", "product", "variety", "quality", "unit", "origin", "currency", "market_level"]
    result["series_id"] = result[dimensions].fillna("").astype(str).apply(
        lambda row: hashlib.sha256(json.dumps(row.tolist(), ensure_ascii=False).encode()).hexdigest()[:24], axis=1)
    result["source_record"] = frame.apply(lambda row: json.dumps(row.to_dict(), ensure_ascii=False), axis=1)
    from .units import enrich_units
    return enrich_units(result)
