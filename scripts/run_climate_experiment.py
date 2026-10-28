"""Illustrative conditional climate experiment on verified historical snapshots."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from materias_primas_chile.features import CLIMATE_COLUMNS, build_features, future_assumptions
from materias_primas_chile.forecast import MODELS, backtest_monthly, forecast_monthly
from materias_primas_chile.storage import write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default="data/snapshots/initial_2020_2025")
    parser.add_argument("--mapping", default="config/origin_climate_map.csv")
    parser.add_argument("--output", default="data/experiments/climate_proxy_v1")
    args = parser.parse_args()
    root, output = Path(args.snapshot), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    monthly = pd.read_parquet(root / "monthly.parquet")
    series = pd.read_parquet(root / "series.parquet")
    climate = pd.read_parquet(root / "climate_monthly.parquet")
    mapping = pd.read_csv(args.mapping)
    features, report = build_features(monthly, series, climate, mapping)
    cutoff = pd.to_datetime(monthly.date).max().to_period("M").to_timestamp()
    report.update(cutoff_month=str(cutoff.date()),
        target_start=str((cutoff + pd.DateOffset(months=1)).date()),
        scope="illustrative conditional association, not validated regional climate impact")
    if features.empty:
        report.update(status="no_origin_matches", eligible_series=0)
        write_json(output / "report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    counts = features.groupby("series_id").price.count()
    eligible = counts[counts >= 24].index
    training = features.loc[features.series_id.isin(eligible)].copy()
    report["eligible_series"] = int(len(eligible))
    training.to_csv(output / "training.csv", index=False)
    if training.empty:
        report["status"] = "insufficient_price_history"
        write_json(output / "report.json", report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return
    predictions, metrics = backtest_monthly(training, value_col="price", climate_cols=CLIMATE_COLUMNS,
                                           horizon=12, stride=12, models=(*MODELS, "ridge_seasonal"))
    predictions.to_csv(output / "backtest_predictions.csv", index=False)
    metrics.to_csv(output / "backtest_metrics.csv", index=False)
    locations = training[["series_id", "location_id"]].drop_duplicates()
    forecasts = []
    for name, delta, factor in [("point_climatology_lag3", 0.0, 1.0),
                                ("illustrative_temp_plus2C_precip_minus20pct_lag3", 2.0, 0.8)]:
        assumptions = future_assumptions(locations, climate, cutoff, temperature_delta_c=delta,
                                         precipitation_factor=factor)
        assumptions.to_csv(output / f"{name}_assumptions.csv", index=False)
        forecast = forecast_monthly(training, value_col="price", model="ridge_seasonal", climate_cols=CLIMATE_COLUMNS,
                                    future_climate=assumptions, scenario_name=name, forecast_origin=cutoff)
        forecast["spatial_scope"] = "city_point_proxy_not_region_average"
        forecasts.append(forecast)
    combined = pd.concat(forecasts, ignore_index=True)
    combined.to_csv(output / "conditional_forecasts.csv", index=False)
    report.update(status="completed_experimental_not_production_validated", training_rows=len(training),
        backtest_rows=len(predictions), backtest_scored_rows=int(predictions[["actual", "prediction"]].notna().all(axis=1).sum()),
        conditional_forecast_targets=len(combined), conditional_estimates=int(combined.prediction.notna().sum()),
        value_basis="CLP per original commercial unit, separate series", scenario_note="+2C and -20% precipitation are illustrative assumptions on three-month-lag point climate features, not observations or causal estimates")
    write_json(output / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
