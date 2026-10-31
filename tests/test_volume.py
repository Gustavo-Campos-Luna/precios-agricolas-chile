import tempfile
import unittest
from pathlib import Path

import pandas as pd

from materias_primas_chile.volume import aggregate


class VolumeTests(unittest.TestCase):
    def test_monthly_volume_is_summed_per_series_and_kg_only_with_explicit_weight(self):
        rows = [
            ["cereza_bandeja10", "2025-12-01", 7000.0, 100, 10.0],
            ["cereza_bandeja10", "2025-12-02", 8000.0, 300, 10.0],
            ["cereza_bandeja10", "2026-01-02", 9000.0, 50, 10.0],
            ["manzana_bins", "2025-12-01", 100000.0, 20, None],
            ["manzana_bins", "2025-12-02", 120000.0, 0, None],  # volumen cero: no pondera
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "daily.csv"
            pd.DataFrame(rows, columns=["series_id", "date", "price", "volume", "commercial_weight_kg"]).to_csv(path, index=False)
            out = aggregate(path, chunksize=2).set_index(["series_id", "date"])  # chunks pequeños: aditividad
        dec = out.loc[("cereza_bandeja10", "2025-12-01")]
        self.assertEqual((dec.volume_units, dec.n_days, dec.volume_max_day), (400, 2, 300))
        self.assertAlmostEqual(dec.price_vwap, (7000 * 100 + 8000 * 300) / 400)
        self.assertEqual((dec.volume_kg_est, dec.volume_kg_basis), (4000.0, "units_x_explicit_package_weight"))
        bins = out.loc[("manzana_bins", "2025-12-01")]
        self.assertEqual((bins.volume_units, bins.n_days), (20, 1))
        self.assertTrue(pd.isna(bins.volume_kg_est))  # sin peso explícito no se inventan kilos
        self.assertEqual(len(out), 3)


if __name__ == "__main__":
    unittest.main()
