import gzip
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from materias_primas_chile import compact as compact_module
from materias_primas_chile.compact import CompactionError, to_gzip, to_parquet


def sample_csv(directory: Path) -> Path:
    path = directory / "daily.csv"
    pd.DataFrame({
        "date": ["2026-01-02", "2026-01-03", "2026-01-04"], "series_id": ["a", "a", "b"],
        "market_region_code": ["13", "13", "05"], "price": [100.5, 110.0, 80.0], "volume": [10, 20, 30],
        "price_clp_kg": [None, 11.0, 8.0], "source_record": ['{"x": 1}'] * 3}).to_csv(path, index=False)
    return path


class CompactTests(unittest.TestCase):
    def test_parquet_roundtrip_keeps_values_types_and_drops_only_requested_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = sample_csv(Path(directory))
            result = to_parquet(csv, Path(directory) / "daily.parquet", drop=("source_record",), chunksize=2)
            back = pd.read_parquet(Path(directory) / "daily.parquet")
        self.assertEqual(result["rows"], 3)
        self.assertNotIn("source_record", back.columns)
        self.assertEqual(list(back.market_region_code), ["13", "13", "05"])  # los códigos siguen siendo texto
        self.assertEqual(back.price.sum(), 290.5)
        self.assertTrue(pd.isna(back.price_clp_kg.iloc[0]))                  # el faltante no se vuelve cero
        self.assertEqual(back.date.iloc[0], pd.Timestamp("2026-01-02"))

    def test_mismatch_aborts_without_creating_the_target(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = sample_csv(Path(directory))
            original = compact_module.pq.ParquetFile

            class Corrupt:
                def __init__(self, path):
                    self._inner = original(path)

                def iter_batches(self, **kwargs):
                    for batch in self._inner.iter_batches(**kwargs):
                        frame = batch.to_pandas()
                        frame["price"] = frame["price"] + 1  # simula corrupción
                        yield compact_module.pa.RecordBatch.from_pandas(frame)

            with patch.object(compact_module.pq, "ParquetFile", Corrupt):
                with self.assertRaises(CompactionError):
                    to_parquet(csv, Path(directory) / "daily.parquet")
            self.assertFalse((Path(directory) / "daily.parquet").exists())

    def test_gzip_is_byte_identical_when_decompressed(self):
        with tempfile.TemporaryDirectory() as directory:
            csv = sample_csv(Path(directory))
            original = csv.read_bytes()
            result = to_gzip(csv)
            self.assertEqual(gzip.open(result["target"], "rb").read(), original)
            self.assertTrue(csv.exists())  # compactar no borra; borrar es decisión del llamador tras verificar


if __name__ == "__main__":
    unittest.main()
