"""Otros datasets de precios del portal CKAN de ODEPA (consumidor, uva de vinificación, comercio exterior).

Cada dataset se descarga como CSV inmutable (hash + manifiesto) y se normaliza archivo por
archivo, para no cargar décadas de datos en memoria. Reglas:
- Se conserva la unidad original; no se convierte a CLP/kg sin peso explícito.
- ``unit_value_usd_per_kg`` en comercio exterior es un valor DERIVADO (USD FOB / kilo neto),
  no un precio publicado; se marca ``price_kind='derived_unit_value'``.
- La uva de vinificación no declara unidad en el CSV: se registra ``unit='no_declarada'``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .prices import _key, _number, discover_resources, download_resource, read_csv
from .storage import write_json

DATASETS = {
    "consumidor": {"dataset": "precios-consumidor", "kind": "consumer"},
    "uva_vinificacion": {"dataset": "precios-uva-vinificacion", "kind": "wine_grape"},
    "comex_exportacion": {"dataset": "comercio-exterior", "kind": "export", "name_hint": "xport"},
    "comex_importacion": {"dataset": "comercio-exterior", "kind": "import", "name_hint": "mport"},
    "catastro_fruticola": {"dataset": "catastro-fruticola", "kind": "orchard"},
}


def select_resources(key: str) -> list[dict]:
    spec = DATASETS[key]
    resources = discover_resources(spec["dataset"])
    hint = spec.get("name_hint")
    if hint:
        resources = [r for r in resources if hint in (r.get("name", "") + r.get("url", "")).lower()]
    if not resources:
        raise ValueError(f"Sin recursos CSV para {key}")
    return resources


def download_dataset(key: str, raw_root: str | Path = "data/raw") -> list[Path]:
    """Descarga los CSV de un dataset; omite recursos sin cambios desde la última descarga."""
    paths = []
    for resource in select_resources(key):
        folder = Path(raw_root) / "odepa" / resource["id"]
        known = sorted(folder.glob("*.csv")) if folder.exists() else []
        meta = folder / "resource.json"
        unchanged = known and meta.exists() and \
            json.loads(meta.read_text(encoding="utf-8")).get("last_modified") == resource.get("last_modified")
        paths.append(known[-1] if unchanged else download_resource(resource, raw_root))
    return paths


def _col(frame: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in frame:
            return frame[name]
    raise ValueError(f"Falta una de las columnas {names}; hay {list(frame.columns)}")


def _optional(frame: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in frame:
            return frame[name]
    return pd.Series("", index=frame.index)


def _dates(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series.str.strip(), errors="coerce", dayfirst=True, format="mixed")


def normalize(key: str, frame: pd.DataFrame, source: str = "") -> pd.DataFrame:
    data = frame.rename(columns={c: _key(c) for c in frame.columns})
    kind = DATASETS[key]["kind"]
    out = pd.DataFrame(index=data.index)
    if kind == "consumer":
        product_raw = _col(data, "producto")
        out["date"] = _dates(_col(data, "fecha_inicio"))
        out["date_end"] = _dates(_col(data, "fecha_termino"))
        out["year"], out["month"], out["week"] = (pd.to_numeric(_col(data, c), errors="coerce") for c in ("anio", "mes", "semana"))
        out["region_id"], out["region"] = _optional(data, "id_region"), _optional(data, "region")
        out["sector"], out["point_type"] = _optional(data, "sector"), _optional(data, "tipo_de_punto_monitoreo")
        out["group"], out["product_raw"] = _optional(data, "grupo"), product_raw
        out["product"] = product_raw.str.split("|").str[0].str.strip()  # formato 2008: Producto|Variedad|Calidad
        out["unit"] = _col(data, "unidad")
        for name, column in (("price_min", "precio_minimo"), ("price_max", "precio_maximo"), ("price", "precio_promedio")):
            out[name] = _optional(data, column).map(_number)
        out["currency"], out["price_kind"], out["market_level"] = "CLP", "published", "retail"
    elif kind == "wine_grape":
        out["date"] = _dates(_col(data, "fecha_precio_vigente"))
        out["region_id"], out["region"] = _optional(data, "id_region"), _optional(data, "region")
        out["commune"], out["buyer"] = _optional(data, "comuna"), _optional(data, "poder_comprador")
        out["branch"], out["variety"] = _optional(data, "sucursal"), _optional(data, "variedad")
        out["price"] = _col(data, "precio").map(_number)
        out["brix"] = _optional(data, "grado_brix").map(_number)
        out["next_price_date"] = _dates(_optional(data, "fecha_proximo_precio"))
        out["next_price"] = _optional(data, "proximo_precio").map(_number)
        out["observation"] = _optional(data, "observaciones")
        out["unit"], out["currency"] = "no_declarada", "CLP"
        out["price_kind"], out["market_level"] = "published", "producer_buyer_price"
    elif kind == "orchard":
        # Censo CIREN-ODEPA: se levanta por zonas distintas cada año; la superficie de dos años solo es
        # comparable dentro de las mismas regiones.
        out["year"] = pd.to_numeric(_col(data, "anio"), errors="coerce")
        out["region_id"], out["region"] = _optional(data, "id_region"), _optional(data, "region")
        out["province"], out["commune"] = _optional(data, "provincia"), _optional(data, "comuna")
        out["producer_type"] = _optional(data, "tipo_productor")
        out["species"], out["variety"] = _col(data, "especie"), _optional(data, "variedad")
        out["planting_year"] = pd.to_numeric(_optional(data, "anio_plantacion"), errors="coerce")
        out["irrigation"] = _optional(data, "metodo_de_riego")
        out["trees"] = _optional(data, "numero_de_arboles").map(_number)
        out["area_ha"] = _col(data, "superficie_ha").map(_number)
        out["unit"], out["price_kind"] = "ha", "not_a_price"
    else:  # export / import
        value_col = "usd_fob" if kind == "export" else "usd_cif"
        out["year"], out["month"] = (pd.to_numeric(_col(data, c), errors="coerce") for c in ("anio", "mes"))
        out["date"] = pd.to_datetime(dict(year=out.year, month=out.month, day=1), errors="coerce")
        out["hs_code"], out["product"] = _col(data, "codigo_producto_sa", "codigo_producto"), _col(data, "producto")
        out["region_id"] = _optional(data, "id_region")
        out["region"] = _optional(data, "region_origen", "region")
        out["country"] = _optional(data, "pais_destino", "pais_origen")
        out["unit"] = _col(data, "unidad")
        out["volume"] = _col(data, "volumen").map(_number)
        out["value_usd"] = _col(data, value_col).map(_number)
        kilos = out.unit.str.lower().str.contains("kilo") & out.volume.gt(0)
        out["unit_value_usd_per_kg"] = (out.value_usd / out.volume).where(kilos)  # derivado; faltante si no es kilo
        out["currency"], out["price_kind"] = "USD", "derived_unit_value"
        out["flow"] = "export_fob" if kind == "export" else "import_cif"
    out["source"] = f"ODEPA CKAN {DATASETS[key]['dataset']}"
    out["source_file"] = source
    return out


def build_dataset(key: str, raw_root: str | Path = "data/raw", output: str | Path = "data/processed/odepa_datasets") -> dict:
    """Descarga, normaliza archivo por archivo y escribe un CSV consolidado en modo append."""
    paths = download_dataset(key, raw_root)
    target = Path(output) / f"{key}.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.unlink(missing_ok=True)
    rows, first, columns = 0, True, None
    for path in sorted(paths):
        frame = normalize(key, read_csv(path), source=path.parent.name)
        if columns is not None and list(frame.columns) != columns:
            raise ValueError(f"{path.name}: esquema distinto al de los archivos anteriores")
        columns = list(frame.columns)
        frame.to_csv(target, mode="w" if first else "a", header=first, index=False)
        first, rows = False, rows + len(frame)
    summary = {"dataset": key, "files": len(paths), "rows": rows, "output": str(target)}
    write_json(Path(output) / f"{key}.summary.json", summary)
    return summary
