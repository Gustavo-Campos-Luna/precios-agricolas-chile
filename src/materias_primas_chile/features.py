"""Explicit experimental origin-to-point climate features; no market geocoding."""
from __future__ import annotations

import numpy as np
import pandas as pd

CLIMATE_COLUMNS = ("temp_lag3", "precip_lag3")


def _month(values):
    return pd.to_datetime(values, errors="raise").dt.to_period("M").dt.to_timestamp()


def _climate(frame):
    columns = ["location_id", "month", "temperature_mean_c", "precipitation_mm"]
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing climate columns: {sorted(missing)}")
    data = frame[columns].copy()
    data["month"] = _month(data.month)
    if data[["location_id", "month"]].isna().any().any() or data.duplicated(["location_id", "month"]).any():
        raise ValueError("Climate location/month must be unique and non-null")
    for col in ("temperature_mean_c", "precipitation_mm"):
        data[col] = pd.to_numeric(data[col], errors="raise")
        if np.isinf(data[col].to_numpy(dtype=float)).any():
            raise ValueError("Infinite climate observation")
    if data.precipitation_mm.dropna().lt(0).any():
        raise ValueError("Negative precipitation")
    return data


def build_features(monthly, series, climate, mapping, *, lag_months=3):
    """Return matched monthly observations and coverage; preserve price gaps.

    Mapping is an explicit assertion of an exploratory city point inside a
    declared origin region. It does not establish agronomic representativeness.
    Three months is a conservative publication-lag assumption, not source vintage
    reconstruction. No market-region column is considered when matching origin.
    """
    if lag_months != 3:
        raise ValueError("This feature contract supports exactly a three-month lag")
    required = {"date", "series_id", "price"}
    if not required.issubset(monthly):
        raise ValueError("Monthly prices require date, series_id and price")
    metadata = series[["series_id", "origin"]].drop_duplicates()
    if metadata.series_id.isna().any() or metadata.series_id.duplicated().any():
        raise ValueError("Series must identify exactly one origin")
    map_columns = ["origin", "location_id", "mapping_role"]
    if not set(map_columns).issubset(mapping):
        raise ValueError("Mapping requires origin, location_id and mapping_role")
    selected = mapping[map_columns].copy()
    if selected.isna().any().any() or selected.origin.duplicated().any():
        raise ValueError("Origin mapping must be unique and non-null")
    if not selected.mapping_role.eq("city_point_proxy").all():
        raise ValueError("Only explicitly labeled city_point_proxy mappings are supported")
    data = monthly.copy()
    data["date"] = _month(data.date)
    if data.duplicated(["series_id", "date"]).any():
        raise ValueError("Monthly series/date must be unique")
    data = data.merge(metadata, on="series_id", how="left", validate="many_to_one")
    data = data.merge(selected, on="origin", how="left", validate="many_to_one")
    unmatched = data.location_id.isna()
    weather = _climate(climate).rename(columns={"month": "climate_source_month",
        "temperature_mean_c": "temp_lag3", "precipitation_mm": "precip_lag3"})
    weather["date"] = weather.climate_source_month + pd.DateOffset(months=lag_months)
    matched = data.loc[~unmatched].merge(weather, on=["location_id", "date"], how="left", validate="many_to_one")
    matched["spatial_scope"] = "city_point_proxy_not_region_average"
    matched["climate_lag_months"] = lag_months
    report = {"input_monthly_rows": len(data), "matched_origin_rows": len(matched),
        "unmapped_origin_rows": int(unmatched.sum()),
        "complete_climate_rows": int(matched[list(CLIMATE_COLUMNS)].notna().all(axis=1).sum()),
        "matched_series": int(matched.series_id.nunique()),
        "unmapped_origins": sorted(data.loc[unmatched, "origin"].dropna().unique().tolist()),
        "mapping_role": "city_point_proxy", "lag_months": lag_months,
        "interpretation": "Experimental conditional association; city points are not regional crop-weighted climate"}
    return matched, report


def future_assumptions(series_locations, climate, cutoff, *, horizon=12,
                       temperature_delta_c=0.0, precipitation_factor=1.0,
                       lag_months=3):
    """Explicit assumptions from past point climatology; never future observations.

    The temperature delta and precipitation multiplier apply to the climate
    feature three months before each target, not to contemporaneous weather.
    Only source months <= cutoff minus three months enter climatology.
    """
    if lag_months != 3 or horizon < 1:
        raise ValueError("Require three-month lag and positive horizon")
    if not np.isfinite(temperature_delta_c) or not np.isfinite(precipitation_factor) or precipitation_factor < 0:
        raise ValueError("Scenario changes must be finite and precipitation factor non-negative")
    identities = series_locations[["series_id", "location_id"]].drop_duplicates()
    if identities.isna().any().any() or identities.series_id.duplicated().any():
        raise ValueError("Each scenario series requires exactly one known location")
    cutoff = pd.Timestamp(cutoff).to_period("M").to_timestamp()
    if pd.isna(cutoff):
        raise ValueError("Invalid cutoff")
    historical = _climate(climate)
    historical = historical.loc[historical.month <= cutoff - pd.DateOffset(months=lag_months)]
    historical["target_month_number"] = (historical.month + pd.DateOffset(months=lag_months)).dt.month
    normal = historical.groupby(["location_id", "target_month_number"])[["temperature_mean_c", "precipitation_mm"]].mean()
    dates = pd.date_range(cutoff + pd.DateOffset(months=1), periods=horizon, freq="MS")
    rows = []
    for row in identities.itertuples(index=False):
        for when in dates:
            key = (row.location_id, when.month)
            if key not in normal.index or not np.isfinite(normal.loc[key].to_numpy(dtype=float)).all():
                raise ValueError(f"Insufficient historical point climatology for {key}")
            values = normal.loc[key]
            future_source_month = when - pd.DateOffset(months=lag_months)
            apply_change = future_source_month > cutoff and (temperature_delta_c != 0 or precipitation_factor != 1)
            rows.append({"series_id": row.series_id, "date": when,
                "temp_lag3": float(values.temperature_mean_c) + (temperature_delta_c if apply_change else 0.0),
                "precip_lag3": float(values.precipitation_mm) * (precipitation_factor if apply_change else 1.0),
                "climate_source_month_assumed": future_source_month,
                "anomaly_applied": apply_change,
                "assumption_role": "conditional_future_climate_feature_not_observation"})
    return pd.DataFrame(rows, columns=["series_id", "date", *CLIMATE_COLUMNS,
        "climate_source_month_assumed", "anomaly_applied", "assumption_role"])
