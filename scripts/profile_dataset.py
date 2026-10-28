"""Publica snapshot analítico pequeño y perfil verificable; originales quedan en artefacto."""
from __future__ import annotations

import json
from pathlib import Path
import shutil

import pandas as pd

from materias_primas_chile.storage import write_json


def main():
    root = Path("data/snapshots/initial_2020_2025")
    root.mkdir(parents=True, exist_ok=True)
    daily = pd.read_csv("data/curated/prices/daily.csv")
    monthly = pd.read_csv("data/curated/prices/monthly.csv")
    series = pd.read_csv("data/curated/prices/series.csv")
    metrics = pd.read_csv("artifacts/models/backtest_metrics.csv")
    forecast = pd.read_csv("artifacts/models/forecast.csv")
    # Persist original-unit prices and dimensions as reusable analytical tables.
    for name, frame in [("daily", daily), ("monthly", monthly), ("series", series),
                        ("backtest_metrics", metrics), ("forecast", forecast)]:
        frame.to_parquet(root / f"{name}.parquet", index=False)
    for name in ("quarantine.csv", "quality.json", "build_status.json"):
        shutil.copyfile(Path("data/curated/prices") / name, root / name)
    climate_paths = sorted(Path("data/processed/climate").glob("*_monthly.csv"))
    if climate_paths:
        pd.concat([pd.read_csv(path) for path in climate_paths], ignore_index=True).to_parquet(root / "climate_monthly.parquet", index=False)
    grains_path = Path("data/processed/grains/maiz_grano_week22_2025.csv")
    if grains_path.exists():
        shutil.copyfile(grains_path, root / grains_path.name)
    provenance = root / "provenance"
    for manifest in Path("data/raw").rglob("*.manifest.json"):
        relative = manifest.relative_to("data/raw")
        target = provenance / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(manifest, target)
    shutil.copyfile("artifacts/odepa_resources.json", root / "odepa_resources.json")
    joined = daily.merge(series[["series_id"]].drop_duplicates(), on="series_id", validate="many_to_one")
    coverage = joined.groupby(["product", "market_region", "unit"], dropna=False).agg(
        observations=("price", "size"), first_date=("date", "min"), last_date=("date", "max"),
        series=("series_id", "nunique")
    ).reset_index()
    coverage.to_csv(root / "coverage.csv", index=False)
    daily.groupby("product", group_keys=False).head(10).to_csv(root / "observed_sample.csv", index=False)
    price_ranges = daily.groupby(["product", "unit"], dropna=False).price.agg(["min", "median", "max", "count"]).reset_index()
    price_ranges.to_csv(root / "price_ranges.csv", index=False)
    quality = json.loads((root / "quality.json").read_text())
    summary = {
        "snapshot": str(root), "source": "ODEPA mayoristas + NASA POWER",
        "first_date": str(daily.date.min()), "last_date": str(daily.date.max()),
        "valid_daily_observations": len(daily), "quarantine_observations": quality["quarantine_rows"],
        "monthly_series_observations": len(monthly), "distinct_series": int(series.series_id.nunique()),
        "products": daily.groupby("product").size().to_dict(),
        "market_regions": sorted(daily.market_region.dropna().unique().tolist()),
        "units": daily.groupby("unit").size().to_dict(),
        "backtest_prediction_rows": len(pd.read_csv("artifacts/models/backtest_predictions.csv")),
        "forecast_targets": len(forecast), "forecast_available": int(forecast.prediction.notna().sum()),
        "forecast_status": forecast.groupby("status").size().to_dict(),
        "daily_rows_with_explicit_clp_kg": int(daily.price_clp_kg.notna().sum()) if "price_clp_kg" in daily else 0,
        "daily_rows_with_explicit_clp_unit": int(daily.price_clp_unit.notna().sum()) if "price_clp_unit" in daily else 0,
        "producer_maize_report_available": grains_path.exists(),
        "origins": daily.origin.dropna().value_counts().head(30).to_dict(),
        "limitations": ["Precios nominales en unidad comercial original", "Mercado no equivale a origen productivo", "Clima histórico por tres puntos, sin asociación automática a cultivos", "Pronósticos base con abstención; ningún modelo comercial certificado", "Maíz grano y poroto seco no se consideran cubiertos por equivalencia con fresco"],
    }
    write_json(root / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
