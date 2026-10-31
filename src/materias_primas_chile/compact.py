"""Reduce el espacio en disco sin perder información de análisis.

- CSV grandes de análisis -> Parquet (zstd), con tipos fijos y verificación contra el original.
- CSV normalizados intermedios -> ``.csv.gz`` (misma columna, mismo contenido, verificado por SHA-256
  del flujo descomprimido).
Los originales descargados (``data/raw``) NO se tocan: son la evidencia con hash y manifiesto.
Un CSV solo se borra (``delete=True``) después de que su versión compacta pasó la verificación;
cualquier diferencia aborta sin borrar nada. ``source_record`` (JSON crudo de cada fila, ~430 bytes)
se omite del Parquet diario porque vive en ``data/raw`` y en los ``.csv.gz`` normalizados.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

NUMERIC = {"year", "month", "week", "planting_year", "price", "price_min", "price_max", "price_clp_kg",
           "price_clp_unit", "commercial_weight_kg", "volume", "value_usd", "unit_value_usd_per_kg", "trees",
           "area_ha", "brix", "next_price"}
DATES = {"date", "date_end", "next_price_date"}


class CompactionError(RuntimeError):
    pass


def _schema(columns: list[str]) -> pa.Schema:
    def kind(name: str):
        return pa.float64() if name in NUMERIC else pa.timestamp("ns") if name in DATES else pa.string()
    return pa.schema([(name, kind(name)) for name in columns])


def _typed(chunk: pd.DataFrame) -> pd.DataFrame:
    for name in chunk.columns:
        if name in NUMERIC:
            chunk[name] = pd.to_numeric(chunk[name], errors="raise").astype("float64")
        elif name in DATES:
            chunk[name] = pd.to_datetime(chunk[name], errors="raise")
    return chunk


class _Stats:
    def __init__(self):
        self.rows, self.nonnull, self.sums = 0, {}, {}

    def add(self, frame: pd.DataFrame):
        self.rows += len(frame)
        for name in frame.columns:
            self.nonnull[name] = self.nonnull.get(name, 0) + int(frame[name].notna().sum())
            if name in NUMERIC:
                self.sums[name] = self.sums.get(name, 0.0) + float(frame[name].sum())

    def as_dict(self):
        return {"rows": self.rows, "nonnull": self.nonnull, "sums": {k: round(v, 6) for k, v in self.sums.items()}}


def to_parquet(csv_path: str | Path, parquet_path: str | Path, *, drop: tuple[str, ...] = (), chunksize: int = 400_000) -> dict:
    csv_path, parquet_path = Path(csv_path), Path(parquet_path)
    columns = [c for c in pd.read_csv(csv_path, nrows=0).columns if c not in drop]
    schema = _schema(columns)
    temporary = parquet_path.with_suffix(".parquet.partial")
    before, writer = _Stats(), pq.ParquetWriter(temporary, schema, compression="zstd")
    try:
        for chunk in pd.read_csv(csv_path, usecols=columns, dtype=str, chunksize=chunksize):
            chunk = _typed(chunk)
            before.add(chunk)
            writer.write_table(pa.Table.from_pandas(chunk, schema=schema, preserve_index=False))
    finally:
        writer.close()
    after = _Stats()
    for batch in pq.ParquetFile(temporary).iter_batches(batch_size=chunksize):
        after.add(batch.to_pandas())
    if before.as_dict() != after.as_dict():
        temporary.unlink(missing_ok=True)
        raise CompactionError(f"{csv_path.name}: el Parquet no coincide con el CSV; no se reemplaza")
    temporary.replace(parquet_path)
    return {"source": str(csv_path), "target": str(parquet_path), "rows": before.rows,
            "csv_mb": round(csv_path.stat().st_size / 1e6, 1), "parquet_mb": round(parquet_path.stat().st_size / 1e6, 1)}


def _sha256_stream(handle, size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    while block := handle.read(size):
        digest.update(block)
    return digest.hexdigest()


def to_gzip(csv_path: str | Path) -> dict:
    csv_path = Path(csv_path)
    target = Path(str(csv_path) + ".gz")
    temporary = Path(str(target) + ".partial")
    with csv_path.open("rb") as source, gzip.open(temporary, "wb", compresslevel=6) as out:
        shutil.copyfileobj(source, out, 1 << 20)
    with csv_path.open("rb") as original, gzip.open(temporary, "rb") as packed:
        if _sha256_stream(original) != _sha256_stream(packed):
            temporary.unlink(missing_ok=True)
            raise CompactionError(f"{csv_path.name}: el gzip no reproduce el CSV; no se reemplaza")
    temporary.replace(target)
    return {"source": str(csv_path), "target": str(target), "csv_mb": round(csv_path.stat().st_size / 1e6, 1),
            "gz_mb": round(target.stat().st_size / 1e6, 1)}


def compact(root: str | Path = ".", *, delete: bool = False) -> dict:
    root = Path(root)
    jobs = [("parquet", root / "data/curated/prices/daily.csv", root / "data/curated/prices/daily.parquet", ("source_record",))]
    for name in ("consumidor", "comex_exportacion", "comex_importacion", "catastro_fruticola", "uva_vinificacion"):
        jobs.append(("parquet", root / f"data/processed/odepa_datasets/{name}.csv",
                     root / f"data/processed/odepa_datasets/{name}.parquet", ()))
    for path in sorted((root / "data/processed/prices").glob("*.csv")):
        jobs.append(("gzip", path, None, ()))
    done, saved = [], 0
    for kind, source, target, drop in jobs:
        if not source.exists():
            continue
        size = source.stat().st_size
        result = to_parquet(source, target, drop=drop) if kind == "parquet" else to_gzip(source)
        result["kind"] = kind
        if delete:
            source.unlink()
            result["original_deleted"] = True
            saved += size - Path(result["target"]).stat().st_size
        done.append(result)
    summary = {"files": len(done), "deleted_originals": delete, "saved_mb": round(saved / 1e6, 1), "details": done}
    report = root / "data/analysis/compact_report.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
