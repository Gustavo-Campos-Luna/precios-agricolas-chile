"""Lectura uniforme de tablas en CSV, CSV comprimido o Parquet.

Los módulos de análisis piden ``foo.csv`` y reciben lo que exista: ``foo.csv``, ``foo.csv.gz`` o
``foo.parquet``. Así la compactación (``compact.py``) puede reemplazar CSV grandes sin romper nada.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pandas as pd


def resolve(path: str | Path) -> Path:
    path = Path(path)
    candidates = [path, Path(str(path) + ".gz"), path.with_suffix(".parquet")]
    if path.suffix == ".gz":
        candidates.append(path.with_suffix("").with_suffix(".parquet"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No existe {path} ni su versión comprimida/parquet; ejecutar el paso que lo genera")


def exists(path: str | Path) -> bool:
    try:
        resolve(path)
    except FileNotFoundError:
        return False
    return True


def read_table(path: str | Path, columns: list[str] | None = None) -> pd.DataFrame:
    real = resolve(path)
    if real.suffix == ".parquet":
        return pd.read_parquet(real, columns=columns)
    return pd.read_csv(real, usecols=columns)


def iter_chunks(path: str | Path, columns: list[str] | None = None, chunksize: int = 400_000) -> Iterator[pd.DataFrame]:
    """Recorre la tabla por trozos de memoria acotada, sea cual sea su formato."""
    real = resolve(path)
    if real.suffix == ".parquet":
        import pyarrow.parquet as pq
        for batch in pq.ParquetFile(real).iter_batches(batch_size=chunksize, columns=columns):
            yield batch.to_pandas()
    else:
        yield from pd.read_csv(real, usecols=columns, chunksize=chunksize)


def columns_of(path: str | Path) -> list[str]:
    real = resolve(path)
    if real.suffix == ".parquet":
        import pyarrow.parquet as pq
        return list(pq.ParquetFile(real).schema_arrow.names)
    return list(pd.read_csv(real, nrows=0).columns)


def read_date_range(path: str | Path, columns: list[str], start: pd.Timestamp, end: pd.Timestamp,
                    date_col: str = "date") -> pd.DataFrame:
    """Filas con start <= fecha < end. En Parquet filtra al leer; en CSV lee y filtra."""
    real = resolve(path)
    if real.suffix == ".parquet":
        filters = [(date_col, ">=", start), (date_col, "<", end)]
        return pd.read_parquet(real, columns=columns, filters=filters)
    frame = pd.read_csv(real, usecols=columns, parse_dates=[date_col])
    return frame[(frame[date_col] >= start) & (frame[date_col] < end)]
