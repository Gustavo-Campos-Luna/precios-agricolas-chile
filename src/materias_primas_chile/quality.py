"""Controles estructurales: fallar antes de mezclar precios no comparables."""
from __future__ import annotations

import pandas as pd


def profile(frame: pd.DataFrame, *, keys: list[str], date_col: str = "date", value_col: str = "price") -> dict:
    required = set(keys + [date_col, value_col])
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Columnas requeridas ausentes: {sorted(missing)}")
    dates = pd.to_datetime(frame[date_col], errors="coerce")
    values = pd.to_numeric(frame[value_col], errors="coerce")
    duplicates = int(frame.duplicated(keys, keep=False).sum())
    invalid_dates = int(dates.isna().sum())
    invalid_prices = int((values.isna() | ~values.between(0, float("inf"), inclusive="neither")).sum())
    null_keys = int(frame[keys].isna().any(axis=1).sum())
    return {
        "rows": len(frame), "columns": list(frame.columns), "keys": keys,
        "duplicate_key_rows": duplicates, "invalid_date_rows": invalid_dates,
        "invalid_price_rows": invalid_prices, "null_key_rows": null_keys,
        "min_date": str(dates.min()), "max_date": str(dates.max()),
        "null_rates": frame.isna().mean().to_dict(),
        "passed": bool(len(frame) and not (duplicates or invalid_dates or invalid_prices or null_keys)),
    }


def monthly_panel(frame: pd.DataFrame, *, value_col="price", date_col="date", series_col="series_id"):
    """Mediana mensual dentro de serie homogénea; no pondera volúmenes inexistentes."""
    data = frame.copy()
    data[date_col] = pd.to_datetime(data[date_col], errors="raise")
    check = profile(data, keys=[series_col, date_col], date_col=date_col, value_col=value_col)
    if not check["passed"]:
        raise ValueError(f"Datos no válidos para agregación: {check}")
    data[date_col] = data[date_col].dt.to_period("M").dt.to_timestamp()
    return data.groupby([series_col, date_col], as_index=False).agg(
        price=(value_col, "median"), n_observations=(value_col, "count")
    )
