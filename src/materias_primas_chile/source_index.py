"""Índice maestro: qué precio hay, de qué fuente, con qué unidad y qué cobertura.

No mezcla series: cada fila resume UNA combinación fuente/nivel de mercado/producto/unidad.
Sirve para decidir qué se puede comparar y detectar vacíos antes de analizar.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .tables import columns_of, exists, iter_chunks

# fuente -> (archivo, columnas a leer, mapeo a campos del índice, constantes)
SPECS = {
    "ODEPA mayorista diario": dict(
        path="data/curated/prices/monthly.csv", series="data/curated/prices/series.csv",
        join="series_id", value="price", date="date", product="product", unit="unit",
        constants=dict(market_level="wholesale", currency="CLP", frequency="monthly(median of daily)")),
    "ODEPA series mensuales": dict(
        path="data/processed/odepa_series/monthly_series.csv", value="price", date="date", product="product",
        unit="unit", currency="currency", level="market_type", constants=dict(frequency="monthly")),
    "Banco Central": dict(
        path="data/processed/bcch/series_long.csv", value="value", date="date", product="title",
        constants=dict(market_level="index_or_value", currency="varía", unit="ver título", frequency="varía")),
    "Cotrisa": dict(
        path="data/processed/cotrisa/prices_long.csv", value="price", date="date", product="product",
        unit="unit", currency="currency", constants=dict(market_level="producer_buyer_price", frequency="daily/weekly")),
    "FAOSTAT": dict(
        path="data/processed/faostat/producer_prices.csv", value="value", date="date", product="item",
        unit="unit", currency="currency", constants=dict(market_level="producer_price", frequency="annual/monthly")),
    "ODEPA consumidor semanal": dict(
        path="data/processed/odepa_datasets/consumidor.csv", value="price", date="date", product="product",
        unit="unit", currency="currency", constants=dict(market_level="retail", frequency="weekly")),
    "ODEPA uva vinificación": dict(
        path="data/processed/odepa_datasets/uva_vinificacion.csv", value="price", date="date", product="variety",
        unit="unit", currency="currency", constants=dict(market_level="producer_buyer_price", frequency="irregular")),
    "ODEPA exportaciones": dict(
        path="data/processed/odepa_datasets/comex_exportacion.csv", value="unit_value_usd_per_kg", date="date",
        product="product", currency="currency", constants=dict(market_level="export_fob_derived", unit="USD/kg (derivado)",
                                                               frequency="monthly")),
}


def _partial(data: pd.DataFrame, spec: dict, dims: pd.DataFrame | None):
    if dims is not None:  # el panel mensual ODEPA guarda las dimensiones en otro archivo
        data = data.drop(columns=[c for c in (spec["product"], spec["unit"]) if c in data]).merge(dims, on=spec["join"], how="left")
    data[spec["date"]] = pd.to_datetime(data[spec["date"]], errors="coerce")
    data = data.dropna(subset=[spec["value"], spec["date"]])
    keys = {"product": spec["product"]}
    for field, column in (("unit", "unit"), ("currency", "currency"), ("market_level", "level")):
        if column in spec and spec[column] in data:
            keys[field] = spec[column]
    grouped = data.groupby(list(keys.values()), dropna=False).agg(
        first_date=(spec["date"], "min"), last_date=(spec["date"], "max"), n_obs=(spec["value"], "size")).reset_index()
    return grouped.rename(columns={v: k for k, v in keys.items()})


def summarize(name: str, spec: dict, root: Path, *, chunksize: int = 400_000) -> pd.DataFrame | None:
    """Agrega por producto/unidad en trozos: min/max/suma son aditivos entre trozos."""
    path = root / spec["path"]
    if not exists(path):
        return None
    wanted = {spec["value"], spec["date"], spec["product"]} | {spec[k] for k in ("unit", "currency", "level", "join") if k in spec}
    dims = None
    if "series" in spec:
        dims = pd.read_csv(root / spec["series"], usecols=[spec["join"], spec["product"], spec["unit"]]).drop_duplicates(spec["join"])
    columns = [c for c in columns_of(path) if c in wanted]
    parts = [_partial(chunk, spec, dims) for chunk in iter_chunks(path, columns, chunksize)]
    parts = [p for p in parts if len(p)]
    if not parts:
        return None
    combined = pd.concat(parts, ignore_index=True)
    keys = [c for c in ("product", "unit", "currency", "market_level") if c in combined]
    out = combined.groupby(keys, dropna=False).agg(
        first_date=("first_date", "min"), last_date=("last_date", "max"), n_obs=("n_obs", "sum")).reset_index()
    for field, value in spec.get("constants", {}).items():
        if field not in out:
            out[field] = value
    out.insert(0, "source", name)
    return out


def build_index(root: str | Path = ".", output: str | Path = "data/curated/source_index.csv") -> pd.DataFrame:
    root = Path(root)
    parts = [p for name, spec in SPECS.items() if (p := summarize(name, spec, root)) is not None]
    if not parts:
        raise ValueError("No hay datos procesados; ejecutar ingest/build, series, bcch, cotrisa, faostat y datasets")
    index = pd.concat(parts, ignore_index=True)
    columns = ["source", "market_level", "product", "unit", "currency", "frequency", "first_date", "last_date", "n_obs"]
    index = index.reindex(columns=columns)
    target = root / output
    target.parent.mkdir(parents=True, exist_ok=True)
    index.to_csv(target, index=False)
    return index
