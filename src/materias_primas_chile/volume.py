"""Volumen mensual por serie a partir del panel diario ODEPA, con memoria acotada.

``volume`` viene en UNIDADES COMERCIALES de la serie (cajas, bandejas, sacos, bins): en las
unidades de la propia serie, no en kilos. Evidencia: los bins de 400 kg tienen mediana ~16 y los
sacos de 25 kg ~1000; si fueran kilos serían del mismo orden. El diccionario oficial de ODEPA no
declara la unidad, por lo que es una inferencia a partir de los datos, no un hecho publicado.

Como cada serie tiene una sola unidad, sumar ``volume`` dentro de una serie es consistente.
Si la etiqueta de la unidad dice "(volumen en unidades)", el volumen son piezas sueltas y así
se marca en ``volume_basis``. Los mayores volúmenes diarios (millones) son productos por pieza
(choclo, zanahoria, ajo), no errores. Nunca se suman volúmenes entre series de unidades distintas. ``volume_kg_est`` solo existe
cuando el envase declara su peso explícito (``commercial_weight_kg``); para unidades sin peso
(bins sin peso, "cien", "docena", "unidad") queda vacío en vez de inventarse.
``price_vwap`` es el precio promedio ponderado por volumen del mes (distinto de la mediana).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .tables import iter_chunks

COLUMNS = ["series_id", "date", "price", "volume", "commercial_weight_kg"]


def aggregate(daily_csv: str | Path, *, chunksize: int = 500_000) -> pd.DataFrame:
    parts = []
    for chunk in iter_chunks(daily_csv, COLUMNS, chunksize):
        chunk = chunk[chunk.volume.gt(0) & chunk.price.gt(0)].copy()  # volumen o precio inválido no pondera
        chunk["month"] = pd.to_datetime(chunk["date"]).dt.strftime("%Y-%m-01")
        chunk["pv"] = chunk["price"] * chunk["volume"]
        parts.append(chunk.groupby(["series_id", "month"], as_index=False).agg(
            volume_units=("volume", "sum"), pv=("pv", "sum"), n_days=("volume", "size"),
            volume_max_day=("volume", "max"), weight=("commercial_weight_kg", "first")))
    if not parts:
        raise ValueError("daily.csv sin filas con precio y volumen positivos")
    total = pd.concat(parts, ignore_index=True)
    out = total.groupby(["series_id", "month"], as_index=False).agg(
        volume_units=("volume_units", "sum"), pv=("pv", "sum"), n_days=("n_days", "sum"),
        volume_max_day=("volume_max_day", "max"), weight=("weight", "first"))
    out["price_vwap"] = out["pv"] / out["volume_units"]
    out["volume_kg_est"] = (out["volume_units"] * out["weight"]).where(out["weight"].notna())
    out["volume_kg_basis"] = out["weight"].notna().map({True: "units_x_explicit_package_weight", False: ""})
    out = out.drop(columns=["pv", "weight"]).rename(columns={"month": "date"})
    return out


def build(curated: str | Path = "data/curated/prices") -> dict:
    curated = Path(curated)
    volume = aggregate(curated / "daily.csv")
    monthly = pd.read_csv(curated / "monthly.csv")
    merged = monthly.merge(volume, on=["series_id", "date"], how="left")
    units = pd.read_csv(curated / "series.csv", usecols=["series_id", "unit"]).drop_duplicates("series_id")
    merged = merged.merge(units, on="series_id", how="left", suffixes=("", "_series")) if "unit" not in merged else merged
    # Etiquetas como "$/mil (volumen en unidades)" declaran que el volumen son piezas sueltas.
    declared = merged["unit"].fillna("").str.contains("volumen en unidades", case=False)
    merged["volume_basis"] = declared.map({True: "items_declared_in_unit_label", False: "commercial_unit_inferred"})
    target = curated / "monthly_with_volume.csv"
    merged.to_csv(target, index=False)
    report = {
        "monthly_rows": len(merged), "rows_with_volume": int(merged.volume_units.notna().sum()),
        "rows_with_kg_estimate": int(merged.volume_kg_est.notna().sum()),
        "share_with_kg_estimate": round(float(merged.volume_kg_est.notna().mean()), 4),
        "volume_unit_note": "volume_units está en unidades comerciales de cada serie (inferido; ver docstring)",
        "largest_single_day_volumes": merged.nlargest(10, "volume_max_day")[["series_id", "date", "volume_max_day"]].to_dict("records"),
    }
    (curated / "volume_report.json").write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    report["output"] = str(target)
    return report
