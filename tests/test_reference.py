import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from materias_primas_chile.reference import annual_cpi, build_exports, deflate


class ReferenceTests(unittest.TestCase):
    def test_export_unit_value_is_weighted_by_kilos_not_an_average_of_ratios(self):
        rows = [
            ["2025-12-01", "08092900", "Cerezas", "RM", "China", "Kilo neto", 10000.0, 50000.0],   # 5,0 USD/kg
            ["2025-12-01", "08092900", "Cerezas", "RM", "Peru", "Kilo neto", 100.0, 1000.0],        # 10,0 USD/kg
            ["2025-12-01", "08092900", "Cerezas", "RM", "Peru", "Litro", 500.0, 900.0],             # no es kilo: excluido
            ["2025-12-01", "08092900", "Cerezas", "RM", "Chile", "Kilo neto", 0.0, 10.0],           # volumen cero: excluido
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exports.csv"
            pd.DataFrame(rows, columns=["date", "hs_code", "product", "region", "country", "unit", "volume", "value_usd"]).to_csv(path, index=False)
            out = build_exports(path)
        self.assertEqual(len(out), 1)
        self.assertAlmostEqual(out.fob_usd_per_kg.iloc[0], 51000 / 10100)  # 5,05; el promedio simple daría 7,5
        self.assertEqual(out.kilos.iloc[0], 10100)

    def test_annual_cpi_needs_twelve_months(self):
        cpi = pd.DataFrame({"date": pd.date_range("2025-01-01", "2026-06-01", freq="MS"), "cpi_index": 90.0})
        annual = annual_cpi(cpi).set_index("year")["cpi_index"]
        self.assertEqual(annual.loc[2025], 90.0)
        self.assertTrue(np.isnan(annual.loc[2026]))  # 2026 incompleto: no se extrapola

    def test_deflate_uses_annual_cpi_for_annual_rows(self):
        cpi = pd.DataFrame({"date": pd.date_range("2025-01-01", periods=12, freq="MS"), "cpi_index": np.linspace(80, 100, 12)})
        frame = pd.DataFrame({"date": pd.to_datetime(["2025-12-01", "2025-01-01"]), "value": [1000.0, 1000.0]})
        out = deflate(frame, "value", cpi, annual=pd.Series([False, True]))
        self.assertAlmostEqual(out.iloc[0], 1000.0)               # diciembre: IPC 100
        self.assertAlmostEqual(out.iloc[1], 1000 * 100 / 90.0)    # anual: promedio 90, no el IPC de enero


if __name__ == "__main__":
    unittest.main()
