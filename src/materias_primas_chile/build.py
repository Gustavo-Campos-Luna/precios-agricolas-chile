"""Consolidación de snapshots normalizados en dos pasadas, con memoria acotada.

Pasada 1 lee solo columnas de procedencia y claves (hashes de 64 bits) de todos los
archivos y decide globalmente qué filas son duplicados de un mismo snapshot y cuáles
son conflictos ambiguos de serie-fecha. Pasada 2 carga un archivo a la vez, aplica las
reglas fila a fila y escribe incrementalmente daily/monthly/series/quarantine.

Supuesto: cada archivo es un recurso anual de ODEPA, así que una serie-mes nunca
aparece en dos archivos. El build verifica ese supuesto al final y falla si no se cumple.
Los hashes de 64 bits pueden colisionar con probabilidad despreciable (~1e-7 para 4e6 filas).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .quality import monthly_panel

KEYS = ["series_id", "date"]
PROVENANCE = ["source_snapshot_sha256", "source_record"]
DIMENSIONS = ["series_id", "market_region_code", "market_region", "market", "product", "variety",
              "quality", "unit", "origin", "currency", "market_level", "source",
              "commercial_weight_kg", "unit_conversion_method"]


def _hash_rows(frame: pd.DataFrame) -> np.ndarray:
    return pd.util.hash_pandas_object(frame.astype(str), index=False).to_numpy(dtype=np.uint64)


def _scan(paths: list[Path]):
    """Pasada 1: revisiones, duplicados de snapshot y ambigüedad serie-fecha."""
    resource_shas: dict[str, set] = {}
    prov_hashes, key_hashes, sizes = [], [], []
    for path in paths:
        header = pd.read_csv(path, nrows=0).columns
        if not set(PROVENANCE).issubset(header):
            raise ValueError(f"{path.name}: faltan columnas de procedencia {PROVENANCE}")
        usecols = [c for c in ["source_resource_id", *PROVENANCE, *KEYS] if c in header]
        frame = pd.read_csv(path, usecols=usecols, dtype=str)
        if {"source_resource_id", "source_snapshot_sha256"}.issubset(frame):
            pairs = frame[["source_resource_id", "source_snapshot_sha256"]].dropna().drop_duplicates()
            for resource, sha in pairs.itertuples(index=False):
                resource_shas.setdefault(resource, set()).add(sha)
        dates = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d").fillna("NaT")
        prov_hashes.append(_hash_rows(frame[PROVENANCE]))
        key_hashes.append(_hash_rows(pd.DataFrame({"k": frame["series_id"].astype(str) + "|" + dates})))
        sizes.append(len(frame))
    multi = {r: s for r, s in resource_shas.items() if len(s) > 1}
    if multi:
        raise ValueError("Revisiones múltiples de un mismo recurso: seleccionar un snapshot por recurso "
                         f"en un directorio --input separado ({len(multi)} recursos)")

    prov_all = np.concatenate(prov_hashes)
    _, first = np.unique(prov_all, return_index=True)
    keep_all = np.zeros(len(prov_all), dtype=bool)
    keep_all[first] = True

    key_all = np.concatenate(key_hashes)[keep_all]
    _, inverse, counts = np.unique(key_all, return_inverse=True, return_counts=True)
    ambiguous_all = counts[inverse.reshape(-1)] > 1

    plan, pos, kept_pos = [], 0, 0
    for size in sizes:
        keep = keep_all[pos:pos + size]
        n_kept = int(keep.sum())
        plan.append((keep, ambiguous_all[kept_pos:kept_pos + n_kept]))
        pos += size
        kept_pos += n_kept
    return plan


def _row_reasons(frame: pd.DataFrame, ambiguous: np.ndarray) -> pd.Series:
    reasons = pd.Series("", index=frame.index)
    invalid = frame.date.isna() | frame.series_id.isna() | ~frame.price.between(0, float("inf"), inclusive="neither")
    reasons.loc[invalid] += "invalid_date_key_or_price;"
    for column in ["product", "market", "unit", "market_region_code"]:
        if column in frame:
            bad = frame[column].isna() | frame[column].astype(str).str.strip().eq("")
            reasons.loc[bad] += f"missing_{column};"
    for column, is_lower in [("price_min", True), ("price_max", False)]:
        if column in frame:
            bounds = pd.to_numeric(frame[column], errors="coerce")
            bad = bounds.notna() & (frame.price.lt(bounds) if is_lower else frame.price.gt(bounds))
            reasons.loc[bad] += "price_outside_source_bounds;"
    reasons.loc[pd.Series(ambiguous, index=frame.index)] += "ambiguous_series_date;"
    return reasons


class _Writer:
    """Escribe CSV incrementalmente y exige el mismo esquema de columnas en todas las partes."""

    def __init__(self):
        self.columns: dict[Path, list] = {}

    def append(self, frame: pd.DataFrame, path: Path) -> None:
        if path in self.columns:
            if list(frame.columns) != self.columns[path]:
                raise ValueError(f"Esquema distinto en {path.name}: {list(frame.columns)}")
            frame.to_csv(path, index=False, mode="a", header=False)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            self.columns[path] = list(frame.columns)
            frame.to_csv(path, index=False, mode="w", header=True)


def build_streaming(input_dir, output_dir) -> dict:
    """Construye daily/monthly/series/quarantine/quality desde snapshots anuales."""
    out = Path(output_dir)
    folder = Path(input_dir)
    paths = sorted([*folder.glob("*.csv"), *folder.glob("*.csv.gz")])
    if not paths:
        raise ValueError("No hay snapshots normalizados: ejecutar ingest primero")
    plan = _scan(paths)

    writer = _Writer()
    daily_path, monthly_path = out / "daily.csv", out / "monthly.csv"
    quarantine_path, series_path = out / "quarantine.csv", out / "series.csv"
    quarantine_columns: list | None = None
    series_parts: list[pd.DataFrame] = []
    monthly_keys: list[np.ndarray] = []
    input_rows = quarantine_rows = accepted_rows = 0
    null_counts: pd.Series | None = None
    min_date = max_date = None
    accepted_columns: list = []
    invalid_dates = invalid_prices = null_keys = duplicate_total = 0

    for path, (keep, ambiguous) in zip(paths, plan):
        frame = pd.read_csv(path)
        input_rows += len(frame)
        frame = frame.loc[keep].reset_index(drop=True)
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
        frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
        reasons = _row_reasons(frame, ambiguous)
        reject = reasons.ne("")

        quarantined = frame.loc[reject].copy()
        if len(quarantined):
            quarantined["rejection_reason"] = reasons[reject]
            quarantine_rows += len(quarantined)
            quarantine_columns = list(quarantined.columns)
            writer.append(quarantined, quarantine_path)

        accepted = frame.loc[~reject].copy()
        if not len(accepted):
            continue
        accepted_rows += len(accepted)
        accepted_columns = list(accepted.columns)
        invalid_dates += int(accepted.date.isna().sum())
        invalid_prices += int(accepted.price.isna().sum())
        null_keys += int(accepted[KEYS].isna().any(axis=1).sum())
        duplicate_total += int(accepted.duplicated(KEYS, keep=False).sum())
        counts = accepted.isna().sum()
        null_counts = counts if null_counts is None else null_counts + counts
        part_min, part_max = accepted.date.min(), accepted.date.max()
        min_date = part_min if min_date is None else min(min_date, part_min)
        max_date = part_max if max_date is None else max(max_date, part_max)

        writer.append(accepted, daily_path)
        monthly = monthly_panel(accepted)
        writer.append(monthly, monthly_path)
        month_keys = monthly["series_id"].astype(str) + "|" + monthly["date"].dt.strftime("%Y-%m")
        monthly_keys.append(_hash_rows(pd.DataFrame({"k": month_keys})))
        dims = [c for c in DIMENSIONS if c in accepted]
        series_parts.append(accepted[dims].drop_duplicates())

    if quarantine_path not in writer.columns:
        columns = (quarantine_columns or accepted_columns or list(frame.columns)) + ["rejection_reason"]
        quarantine_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(columns=columns).to_csv(quarantine_path, index=False)

    if monthly_keys:
        all_monthly = np.concatenate(monthly_keys)
        if len(np.unique(all_monthly)) != len(all_monthly):
            raise ValueError("Una serie-mes aparece en más de un snapshot: el build anual no es aditivo")

    if series_parts:
        series = pd.concat(series_parts, ignore_index=True).drop_duplicates()
        series.to_csv(series_path, index=False)

    null_rates = (null_counts / accepted_rows).to_dict() if null_counts is not None else {}
    quality = {
        "rows": accepted_rows, "columns": accepted_columns, "keys": KEYS,
        "duplicate_key_rows": duplicate_total, "invalid_date_rows": invalid_dates,
        "invalid_price_rows": invalid_prices, "null_key_rows": null_keys,
        "min_date": str(min_date), "max_date": str(max_date), "null_rates": null_rates,
        "passed": bool(accepted_rows and not (duplicate_total or invalid_dates or invalid_prices or null_keys)),
        "input_rows": input_rows, "quarantine_rows": quarantine_rows,
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "quality.json").write_text(json.dumps(quality, indent=2, default=str), encoding="utf-8")
    if not quality["passed"]:
        raise ValueError("Sin observaciones válidas; revisar quality.json y cuarentena")
    return {"accepted_rows": accepted_rows, "quarantine_rows": quarantine_rows,
            "input_files": [str(p) for p in paths]}
