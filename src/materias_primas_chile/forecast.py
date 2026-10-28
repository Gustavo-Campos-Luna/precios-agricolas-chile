"""Monthly forecasts with explicit temporal boundaries and abstention on missing lags.

Inputs must already represent comparable prices at one monthly observation per
series. No resampling, spatial aggregation, inflation adjustment or imputation
is performed here. A scenario is an assumption, not a causal weather estimate.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

MODELS = ("naive", "seasonal_naive", "ridge")
SUPPORTED_MODELS = (*MODELS, "ridge_seasonal")
LAGS = (1, 2, 3, 12)


def _prepare(frame, date_col, series_col, value_col, climate_cols):
    required = [date_col, series_col, value_col, *climate_cols]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    data = frame[required].copy()
    if data.empty:
        raise ValueError("Monthly input is empty")
    data[date_col] = pd.to_datetime(data[date_col], errors="raise")
    if data[date_col].isna().any() or data[series_col].isna().any():
        raise ValueError("Null date or series identifier")
    data[date_col] = data[date_col].dt.to_period("M").dt.to_timestamp()
    if data.duplicated([series_col, date_col]).any():
        raise ValueError("Expected a unique monthly observation per series")
    for col in [value_col, *climate_cols]:
        data[col] = pd.to_numeric(data[col], errors="raise")
        if np.isinf(data[col].to_numpy(dtype=float)).any():
            raise ValueError(f"Infinite values in {col}")
    if (data[value_col].dropna() <= 0).any():
        raise ValueError("Observed prices must be strictly positive")
    return data.sort_values([series_col, date_col])


def _monthly(group, date_col, *, end=None):
    group = group.set_index(date_col).sort_index()
    return group.reindex(pd.date_range(group.index.min(), end if end is not None else group.index.max(), freq="MS"))


def _features(values, when, weather, *, lags=LAGS):
    lagged = [values.get(when - pd.DateOffset(months=lag), np.nan) for lag in lags]
    angle = 2 * np.pi * when.month / 12
    return np.asarray([*lagged, np.sin(angle), np.cos(angle), *weather], dtype=float)


def _predict(train, value_col, horizon, model, climate_cols, future_climate=None):
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Unknown model: {model}")
    observed = train[value_col]
    cutoff = train.index.max()
    future = pd.date_range(cutoff + pd.DateOffset(months=1), periods=horizon, freq="MS")
    values = observed.to_dict()
    fitted = None
    lags = (12,) if model == "ridge_seasonal" else LAGS
    if model in {"ridge", "ridge_seasonal"}:
        features, targets = [], []
        for when, value in observed.items():
            weather = train.loc[when, list(climate_cols)].to_numpy(dtype=float) if climate_cols else []
            row = _features(values, when, weather, lags=lags)
            if np.isfinite(row).all() and np.isfinite(value):
                features.append(row)
                targets.append(value)
        if len(targets) >= 12:
            fitted = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            fitted.fit(np.asarray(features), np.asarray(targets))
    climatology = train[list(climate_cols)].groupby(train.index.month).mean() if climate_cols else None
    output = []
    for when in future:
        if model == "naive":
            prediction = values.get(when - pd.DateOffset(months=1), np.nan)
        elif model == "seasonal_naive":
            prediction = values.get(when - pd.DateOffset(months=12), np.nan)
        elif fitted is None:
            prediction = np.nan
        else:
            weather = []
            for col in climate_cols:
                if future_climate is not None:
                    weather.append(future_climate.at[when, col])
                else:
                    weather.append(climatology.at[when.month, col] if when.month in climatology.index else np.nan)
            row = _features(values, when, weather, lags=lags)
            prediction = float(fitted.predict(row.reshape(1, -1))[0]) if np.isfinite(row).all() else np.nan
            # Linear predictions outside the price domain are abstentions, not clipped evidence.
            if prediction <= 0:
                prediction = np.nan
        values[when] = prediction
        output.append(prediction)
    return future, output


def backtest_monthly(
    frame: pd.DataFrame,
    *,
    date_col: str = "date",
    series_col: str = "series_id",
    value_col: str = "price_clp_kg",
    horizon: int = 12,
    min_train_months: int = 24,
    stride: int = 3,
    models: Sequence[str] = MODELS,
    climate_cols: Sequence[str] = (),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Expanding-window evaluation; every transform is fitted inside its fold.

    Overlapping horizons are retained and explicitly identified by cutoff.
    Climate-aware Ridge uses training-only monthly climatology for future
    weather, never the realized weather in the held-out period.
    """
    if horizon < 1 or min_train_months < 24 or stride < 1:
        raise ValueError("Require horizon >= 1, min_train_months >= 24 and stride >= 1")
    if not set(models).issubset(SUPPORTED_MODELS):
        raise ValueError(f"Models must be among {SUPPORTED_MODELS}")
    data = _prepare(frame, date_col, series_col, value_col, climate_cols)
    records = []
    for series, group in data.groupby(series_col, sort=True):
        monthly = _monthly(group, date_col)
        for end in range(min_train_months, len(monthly), stride):
            train = monthly.iloc[:end]
            if train[value_col].notna().sum() < min_train_months:
                continue
            for model in models:
                dates, estimates = _predict(train, value_col, min(horizon, len(monthly) - end), model, climate_cols)
                for step, (when, estimate) in enumerate(zip(dates, estimates), 1):
                    records.append({
                        "series_id": series, "cutoff": train.index[-1], "date": when,
                        "horizon": step, "model": model,
                        "actual": monthly.at[when, value_col], "prediction": estimate,
                    })
    predictions = pd.DataFrame(records, columns=["series_id", "cutoff", "date", "horizon", "model", "actual", "prediction"])
    metrics = []
    if not predictions.empty:
        for (series, model, step), group in predictions.groupby(["series_id", "model", "horizon"]):
            valid = group.dropna(subset=["actual", "prediction"])
            error = valid["prediction"] - valid["actual"]
            denominator = valid["actual"].abs() + valid["prediction"].abs()
            metrics.append({
                "series_id": series, "model": model, "horizon": step,
                "n_observed": int(group.actual.notna().sum()), "n_scored": len(valid),
                "mae": float(error.abs().mean()), "rmse": float(np.sqrt((error ** 2).mean())),
                "smape_pct": float((200 * error.abs() / denominator).mean()),
            })
    return predictions, pd.DataFrame(metrics, columns=["series_id", "model", "horizon", "n_observed", "n_scored", "mae", "rmse", "smape_pct"])


def forecast_monthly(
    frame: pd.DataFrame,
    *,
    date_col: str = "date",
    series_col: str = "series_id",
    value_col: str = "price_clp_kg",
    horizon: int = 12,
    model: str = "seasonal_naive",
    min_train_months: int = 24,
    climate_cols: Sequence[str] = (),
    future_climate: pd.DataFrame | None = None,
    scenario_name: str | None = None,
    forecast_origin: str | pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Forecast each series; optional future weather is explicitly conditional.

    future_climate must contain the same date/series names and all climate_cols,
    with exactly one supplied assumption for every projected month and series.
    The default origin is the latest month across the entire input, including
    stale series. An explicit origin must be at or after that month. Months
    after a stale series ends remain missing; no forward filling is performed.
    No confidence interval is fabricated from a single fit.
    """
    if horizon < 1 or min_train_months < 24:
        raise ValueError("Require horizon >= 1 and min_train_months >= 24")
    if model not in SUPPORTED_MODELS:
        raise ValueError(f"Unknown model: {model}")
    if future_climate is not None and (not climate_cols or model not in {"ridge", "ridge_seasonal"} or not scenario_name):
        raise ValueError("Future climate requires Ridge, climate columns and an explicit scenario_name")
    if scenario_name and future_climate is None:
        raise ValueError("A named scenario requires explicit future climate assumptions")
    data = _prepare(frame, date_col, series_col, value_col, climate_cols)
    latest_month = data[date_col].max()
    origin = latest_month
    if forecast_origin is not None:
        origin = pd.Timestamp(forecast_origin)
        if pd.isna(origin):
            raise ValueError("forecast_origin must be a valid month")
        origin = origin.to_period("M").to_timestamp()
        if origin < latest_month:
            raise ValueError("forecast_origin must be at or after the latest input month; use backtest for historical evaluation")
    assumptions = None
    if future_climate is not None:
        required = [date_col, series_col, *climate_cols]
        missing = set(required) - set(future_climate.columns)
        if missing:
            raise ValueError(f"Missing scenario columns: {sorted(missing)}")
        assumptions = future_climate[required].copy()
        assumptions[date_col] = pd.to_datetime(assumptions[date_col], errors="raise").dt.to_period("M").dt.to_timestamp()
        if assumptions[required].isna().any().any() or assumptions.duplicated([date_col, series_col]).any():
            raise ValueError("Scenario dates/series must be unique and assumptions complete")
        for col in climate_cols:
            assumptions[col] = pd.to_numeric(assumptions[col], errors="raise")
            if not np.isfinite(assumptions[col]).all():
                raise ValueError("Scenario assumptions must be finite")
    records = []
    for series, group in data.groupby(series_col, sort=True):
        train = _monthly(group, date_col, end=origin)
        supplied = None
        if assumptions is not None:
            supplied = assumptions.loc[assumptions[series_col] == series].set_index(date_col)
            needed = pd.date_range(train.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
            if not needed.isin(supplied.index).all():
                raise ValueError(f"Incomplete future climate assumptions for {series}")
        enough = train[value_col].notna().sum() >= min_train_months
        if enough:
            dates, estimates = _predict(train, value_col, horizon, model, climate_cols, supplied)
        else:
            dates = pd.date_range(train.index[-1] + pd.DateOffset(months=1), periods=horizon, freq="MS")
            estimates = [np.nan] * horizon
        for step, (when, estimate) in enumerate(zip(dates, estimates), 1):
            records.append({
                "series_id": series, "cutoff": train.index[-1], "date": when,
                "horizon": step, "model": model, "prediction": estimate,
                "scenario": scenario_name or ("training_climatology" if climate_cols and model in {"ridge", "ridge_seasonal"} else "baseline"),
                "status": "ok" if np.isfinite(estimate) else ("insufficient_history" if not enough else "missing_lag_or_training_data"),
            })
    return pd.DataFrame(records)
