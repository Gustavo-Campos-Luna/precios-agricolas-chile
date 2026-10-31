"""Cliente de las series de tiempo mensuales de ODEPA (1975 en adelante).

La aplicación oficial (aplicativos.odepa.gob.cl/series-precios) arma cada consulta con
dos campos de auditoría que el transporte anterior no enviaba: ``ip`` (IP pública de
quien consulta, obtenida de api.ipify.org) y ``jsonParam`` (registro de los filtros
elegidos). Sin ellos el servidor respondía HTTP 500. Este cliente replica ese
contrato público con valores verdaderos: la IP real de esta máquina y los filtros
realmente consultados. No usa credenciales ni elude controles; ante 403/429/5xx espera
y reintenta con pausas crecientes en vez de insistir.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from pathlib import Path

import httpx
import pandas as pd

from .storage import atomic_write, receipt, write_json

BASE = "https://aplicativos.odepa.gob.cl/series-precios/results/"
ENDPOINT = BASE + "series-tiempo"
IP_SERVICE = "https://api.ipify.org"
USER_AGENT = "MateriasPrimasChile/0.1 (agricultural price research; public ODEPA data)"
CONSUMER_TYPES = {7, 3}  # minorista y supermercado: el subsector es un grupo de consumidor
# Tipos que el controlador oficial presenta con IVA. El resto se consulta con precioConIva=False.
VAT_BASIS = {7: "con_iva", 3: "con_iva", 5: "no_aplica"}
MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


class OdepaSeriesError(RuntimeError):
    pass


class OdepaSeriesClient:
    def __init__(self, raw_root: str | Path = "data/raw/odepa_series", *, pace: float = 2.0, timeout: float = 90):
        self.raw_root = Path(raw_root)
        self.pace = pace
        self._client = httpx.Client(timeout=timeout, headers={"User-Agent": USER_AGENT})
        self._last = 0.0
        self._ip: str | None = None
        self._window: dict | None = None
        self._ipc: str | None = None

    def close(self) -> None:
        self._client.close()

    def _wait(self) -> None:
        delay = self.pace - (time.monotonic() - self._last)
        if delay > 0:
            time.sleep(delay)
        self._last = time.monotonic()

    def _request(self, method: str, url: str, *, attempts: int = 5, **kwargs) -> httpx.Response:
        last = "sin respuesta"
        for attempt in range(attempts):
            self._wait()
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__}: {exc}"
            else:
                if response.status_code == 200:
                    return response
                last = f"HTTP {response.status_code}"
                if response.status_code not in (403, 408, 425, 429, 500, 502, 503, 504):
                    break
            time.sleep(min(60, 5 * 2 ** attempt))
        raise OdepaSeriesError(f"{method} {url} falló tras reintentos: {last}")

    def _get_json(self, path: str, **params):
        return self._request("GET", BASE + path, params=params).json()

    @property
    def public_ip(self) -> str:
        if self._ip is None:
            self._ip = self._request("GET", IP_SERVICE).text.strip()
        return self._ip

    @property
    def window(self) -> dict:
        if self._window is None:
            self._window = self._get_json("min-max-date-precio")
        return self._window

    @property
    def ipc_id(self) -> int:
        """Valor IPC más reciente del catálogo; en consultas nominales solo debe ser válido."""
        if self._ipc is None:
            self._ipc = self._get_json("ipc")[0]["valor"]
        return int(self._ipc)

    # --- catálogo -------------------------------------------------------------------
    def market_types(self) -> list[dict]:
        return self._get_json("tipos-mercados")

    def catalog(self, market_ids: list[int] | None = None) -> pd.DataFrame:
        """Recorre tipo de precio -> subsector/grupo -> producto con los endpoints públicos."""
        rows = []
        for market in self.market_types():
            tipo = market["id"]
            if market_ids and tipo not in market_ids:
                continue
            if tipo in CONSUMER_TYPES:
                groups = [(g["id"], g["glosa"]) for g in self._get_json("pc-grupos", tipoMercado=tipo)]
                for group_id, group in groups:
                    for p in self._get_json("productos-by-pc-sm", grupo=group_id):
                        rows.append(dict(market_type_id=tipo, market_type=market["glosa"], subsector_id=group_id,
                                         subsector=group, product_id=p["id"], product=p["glosaFull"]))
            else:
                for s in self._get_json("sub-sectores-by-tipo-mercado", tipoMercado=tipo):
                    for p in self._get_json("productos-by-sub-sector", subSector=s["sseCod"], tipoMercado=tipo):
                        rows.append(dict(market_type_id=tipo, market_type=market["glosa"], subsector_id=s["sseCod"],
                                         subsector=s["sseDes"], product_id=p["id"], product=p["producto"]))
        return pd.DataFrame(rows)

    # --- descarga -------------------------------------------------------------------
    def _form(self, entry: dict) -> dict:
        start, end = self.window["fechaInicio"], self.window["fechaTermino"]
        d0, m0, y0 = start.split("/")
        d1, m1, y1 = end.split("/")
        con_iva = VAT_BASIS.get(entry["market_type_id"]) == "con_iva"
        tax_label = {"con_iva": "con IVA", "no_aplica": ""}.get(VAT_BASIS.get(entry["market_type_id"]), "sin IVA")
        filters = {"Parametros": {
            "fecha": date.today().isoformat(), "IP": self.public_ip,
            "Sistema": "Series de Precios", "Modulo": "Series de Tiempo",
            "Fecha desde": f"{m0}/{y0}", "Fecha hasta": f"{m1}/{y1}",
            "Tipo de Precios": entry["market_type"], "Precios": "nominal",
            "Subsector": entry["subsector"], "Producto": entry["product"],
            "Tipo consulta": "Serie anual", "IVA": tax_label,
        }}
        return {
            "periodoInicio": f"{y0}-{m0}-{d0}T03:00:00.000Z", "periodoTermino": f"{y1}-{m1}-{d1}T04:00:00.000Z",
            "tipoConsulta": "nominal", "idIPC": self.ipc_id, "tipoMercado": int(entry["market_type_id"]),
            "tipoSalida": "SA", "precioConIva": False, "subSector": int(entry["subsector_id"]),
            "producto": int(entry["product_id"]),
            "jsonParam": json.dumps(filters, ensure_ascii=False), "ip": self.public_ip,
        }

    def path_for(self, entry: dict) -> Path:
        return self.raw_root / str(int(entry["market_type_id"])) / f"{int(entry['product_id'])}.json"

    def fetch(self, entry: dict, *, force: bool = False) -> Path:
        """Descarga una serie y conserva la respuesta original más su manifiesto."""
        path = self.path_for(entry)
        if path.exists() and not force:
            return path
        form = self._form(entry)
        response = self._request("POST", ENDPOINT, json=form)
        try:
            document = response.json()
        except ValueError as exc:
            raise OdepaSeriesError(f"Respuesta no JSON para producto {entry['product_id']}") from exc
        if not isinstance(document, dict) or "resultSeriesTiempo" not in document:
            raise OdepaSeriesError(f"Respuesta sin resultSeriesTiempo para producto {entry['product_id']}")
        atomic_write(path, response.content)
        query = {k: v for k, v in form.items() if k not in ("ip", "jsonParam")}  # sin IP en el manifiesto
        receipt(path, url=ENDPOINT, source="ODEPA series de tiempo", method="POST",
                request_sha256=hashlib.sha256(json.dumps(query, sort_keys=True).encode()).hexdigest(),
                market_type_id=int(entry["market_type_id"]), product_id=int(entry["product_id"]),
                product=entry["product"], subsector=entry["subsector"], query=query,
                price_basis="nominal", vat_basis=VAT_BASIS.get(int(entry["market_type_id"]), "sin_iva"))
        return path


def parse_series(path: str | Path, entry: dict) -> pd.DataFrame:
    """Respuesta anual (año x 12 meses + promedio) a formato largo. No rellena meses vacíos."""
    document = json.loads(Path(path).read_bytes().decode("utf-8", errors="strict"))
    rows = []
    for record in document["resultSeriesTiempo"]:
        year, values = int(record[0]), record[1:13]
        for month, value in enumerate(values, start=1):
            if value is None:
                continue
            rows.append((pd.Timestamp(year=year, month=month, day=1), float(value)))
    frame = pd.DataFrame(rows, columns=["date", "price"])
    unit = entry["product"].rsplit("|", 1)[-1].strip() if "|" in entry["product"] else entry["product"].split("$", 1)[-1]
    unit = unit if unit.startswith(("US$", "$")) else "$" + unit.strip()
    frame["market_type_id"] = int(entry["market_type_id"])
    frame["market_type"] = entry["market_type"]
    frame["subsector"] = entry["subsector"]
    frame["product_id"] = int(entry["product_id"])
    frame["product"] = entry["product"]
    frame["unit"] = unit
    frame["currency"] = "USD" if unit.startswith("US$") else "CLP"
    frame["vat_basis"] = VAT_BASIS.get(int(entry["market_type_id"]), "sin_iva")
    frame["source"] = "ODEPA series de tiempo"
    frame["source_sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return frame


def download_all(client: OdepaSeriesClient, catalog: pd.DataFrame, ledger: str | Path, *, limit: int | None = None) -> dict:
    """Descarga todas las series del catálogo; un fallo se anota y no detiene el resto."""
    failures, done, skipped = [], 0, 0
    entries = catalog.to_dict("records")[:limit]
    for i, entry in enumerate(entries, start=1):
        existed = client.path_for(entry).exists()
        try:
            client.fetch(entry)
        except OdepaSeriesError as exc:
            failures.append({"market_type_id": entry["market_type_id"], "product_id": entry["product_id"],
                             "product": entry["product"], "error": str(exc)})
            print(f"[{i}/{len(entries)}] FALLO {entry['product']}: {exc}", flush=True)
            continue
        skipped += existed
        done += not existed
        if i % 25 == 0:
            print(f"[{i}/{len(entries)}] descargadas={done} ya_existían={skipped} fallos={len(failures)}", flush=True)
    summary = {"requested": len(entries), "downloaded": done, "already_present": skipped, "failed": len(failures),
               "failures": failures}
    write_json(ledger, summary)
    return summary
