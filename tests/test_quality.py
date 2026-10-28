import tempfile
import unittest
from pathlib import Path

import pandas as pd

from materias_primas_chile.quality import monthly_panel, profile
from materias_primas_chile.storage import atomic_write, receipt


class QualityTests(unittest.TestCase):
    def test_invalid_values_do_not_enter_monthly_panel(self):
        for value in [0, -1, float("inf"), float("nan")]:
            frame = pd.DataFrame({"date": ["2024-01-01"], "series_id": ["synthetic"], "price": [value]})
            self.assertFalse(profile(frame, keys=["date", "series_id"])["passed"])
            with self.assertRaises(ValueError):
                monthly_panel(frame)

    def test_duplicate_daily_key_rejected(self):
        frame = pd.DataFrame({"date": ["2024-01-01"] * 2, "series_id": ["synthetic"] * 2,
                              "price": [100, 200]})
        with self.assertRaises(ValueError):
            monthly_panel(frame)

    def test_monthly_preserves_series_and_counts(self):
        frame = pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-01"],
                              "series_id": ["synthetic_a", "synthetic_a", "synthetic_b"],
                              "price": [100, 300, 900]})
        result = monthly_panel(frame).set_index("series_id")
        self.assertEqual(result.loc["synthetic_a", "price"], 200)
        self.assertEqual(result.loc["synthetic_a", "n_observations"], 2)
        self.assertEqual(result.loc["synthetic_b", "price"], 900)

    def test_receipt_detects_content_not_name(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "example.bin"
            atomic_write(path, b"first")
            first = receipt(path, url="https://example.org/fixture", source="synthetic_test")
            atomic_write(path, b"second")
            second = receipt(path, url="https://example.org/fixture", source="synthetic_test")
            self.assertNotEqual(first["sha256"], second["sha256"])
            self.assertTrue(path.with_suffix(".bin.manifest.json").exists())

    def test_explicit_unit_enrichment_survives_monthly_without_pooling(self):
        from materias_primas_chile.units import enrich_units
        data = pd.DataFrame({"date": ["2024-01-01", "2024-01-02", "2024-01-01"],
                             "series_id": ["box", "box", "item"], "price": [1000, 3000, 100],
                             "unit": ["$/caja 10 kilos", "$/caja 10 kilos", "$/unidad"],
                             "currency": ["CLP"] * 3})
        panel = monthly_panel(enrich_units(data)).set_index("series_id")
        self.assertEqual(panel.loc["box", "price_clp_kg"], 200)
        self.assertEqual(panel.loc["box", "price_clp_kg_observations"], 2)
        self.assertTrue(pd.isna(panel.loc["item", "price_clp_kg"]))
        self.assertEqual(panel.loc["item", "price_clp_unit"], 100)


if __name__ == "__main__":
    unittest.main()
