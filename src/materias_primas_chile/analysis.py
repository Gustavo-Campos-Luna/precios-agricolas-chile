"""Panel analítico mensual: precio, volumen, variedad armonizada, kilos, precio real y en USD.

Parte de ``monthly_with_volume.csv`` (precio mediano y ponderado por volumen del mes, por serie
homogénea) y agrega, sin alterar lo original:
- variedad armonizada (key / canonical / group), ver ``varieties.py``;
- conversión a CLP/kg SOLO cuando la etiqueta de la unidad declara peso (``units.py``);
- precio real = nominal * 100 / IPC (pesos de septiembre de 2026); el último mes con IPC publicado
  es la base y los meses posteriores quedan vacíos (no se extrapola inflación);
- precio en USD/kg con el dólar observado promedio mensual.
Una fila sigue siendo una serie homogénea (producto, variedad, calidad, origen, unidad, mercado).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .units import enrich_units
from .varieties import harmonize, load_aliases

SERIES_COLUMNS = ["series_id", "market_region_code", "market_region", "market", "product", "variety", "quality",
                  "origin", "unit", "currency", "market_level"]
MONTHLY_COLUMNS = ["series_id", "date", "price", "n_observations", "price_vwap", "volume_units",
                   "volume_basis", "n_days", "volume_max_day"]


def unit_factors(units: pd.Series) -> pd.DataFrame:
    """Factor precio-por-unidad -> CLP/kg (y CLP/pieza) a partir de la etiqueta; vacío si no declara peso."""
    table = pd.DataFrame({"unit": units.dropna().unique()})
    probe = enrich_units(table.assign(price=1.0, currency="CLP"))
    return pd.DataFrame({
        "unit": table["unit"], "kg_factor": probe["price_clp_kg"], "piece_factor": probe["price_clp_unit"],
        "weight_kg": probe["commercial_weight_kg"], "conversion_method": probe["unit_conversion_method"].astype(str)})


def build_panel(curated: str | Path = "data/curated/prices", macro: str | Path = "data/processed/bcch") -> pd.DataFrame:
    curated, macro = Path(curated), Path(macro)
    monthly = pd.read_csv(curated / "monthly_with_volume.csv", usecols=lambda c: c in MONTHLY_COLUMNS, parse_dates=["date"])
    series = pd.read_csv(curated / "series.csv", usecols=lambda c: c in SERIES_COLUMNS)
    cpi = pd.read_csv(macro / "cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    usd = pd.read_csv(macro / "usd_clp_monthly.csv", usecols=["date", "usd_clp"], parse_dates=["date"])

    series = harmonize(series, "variety", load_aliases())
    panel = monthly.merge(series, on="series_id", how="left", validate="many_to_one")
    panel = panel.merge(unit_factors(panel["unit"]), on="unit", how="left")
    panel = panel.merge(cpi, on="date", how="left").merge(usd, on="date", how="left")

    # Kilos vendidos con las MISMAS reglas de peso que el precio por kilo (volume.py usaba el parser anterior,
    # que no entendía bins, "granel" ni "empedrada"). Solo con peso declarado; nunca se estima un peso.
    panel["volume_kg_est"] = panel["volume_units"] * panel["weight_kg"]
    panel["volume_kg_basis"] = panel["weight_kg"].notna().map({True: "units_x_declared_package_weight", False: ""})
    panel["price_clp_kg"] = panel["price"] * panel["kg_factor"]
    panel["price_vwap_clp_kg"] = panel["price_vwap"] * panel["kg_factor"]
    panel["price_real"] = panel["price"] * 100 / panel["cpi_index"]
    panel["price_clp_kg_real"] = panel["price_clp_kg"] * 100 / panel["cpi_index"]
    panel["price_vwap_clp_kg_real"] = panel["price_vwap_clp_kg"] * 100 / panel["cpi_index"]
    panel["price_usd_kg"] = panel["price_clp_kg"] / panel["usd_clp"]
    panel["price_basis"] = "median_of_daily_prices_in_month"

    for column in ("market_region_code", "market_region", "market", "product", "variety", "variety_key",
                   "variety_canonical", "variety_group", "quality", "origin", "unit", "currency", "market_level",
                   "volume_basis", "volume_kg_basis", "conversion_method", "price_basis"):
        if column in panel:
            panel[column] = panel[column].astype("category")
    return panel.drop(columns=["kg_factor", "piece_factor"])


def report(panel: pd.DataFrame) -> dict:
    return {
        "rows": len(panel), "series": int(panel.series_id.nunique()),
        "first_month": str(panel.date.min().date()), "last_month": str(panel.date.max().date()),
        "share_with_clp_kg": round(float(panel.price_clp_kg.notna().mean()), 4),
        "share_with_real_price": round(float(panel.price_real.notna().mean()), 4),
        "share_with_usd_kg": round(float(panel.price_usd_kg.notna().mean()), 4),
        "months_without_cpi": sorted({str(d.date()) for d in panel.loc[panel.cpi_index.isna(), "date"].unique()})[-6:],
        "conversion_methods": {str(k): int(v) for k, v in panel.conversion_method.value_counts().items()},
        "canonical_varieties_with_aliases": int(panel.variety_canonical.nunique()),
        "note": "price_clp_kg solo existe con peso declarado en la etiqueta; price_real en pesos del último mes con IPC",
    }


def write_panel(curated: str | Path = "data/curated/prices", macro: str | Path = "data/processed/bcch",
                output: str | Path = "data/analysis") -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    panel = build_panel(curated, macro)
    panel.to_parquet(output / "prices_monthly.parquet", index=False, compression="zstd")
    summary = report(panel)
    summary["output"] = str(output / "prices_monthly.parquet")
    (output / "prices_monthly.report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
