import importlib.util
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analysis_frutas.py"
spec = importlib.util.spec_from_file_location("analysis_frutas", SCRIPT)
frutas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(frutas)


class FruitAnalysisHelpers(unittest.TestCase):
    def test_season_starts_in_the_configured_month(self):
        # solo meses de la ventana (nov-feb): marzo se descarta antes de asignar temporada
        dates = pd.Series(pd.to_datetime(["2024-11-15", "2024-12-31", "2025-01-10", "2025-02-28"]))
        self.assertEqual(list(frutas.season_start(dates, 11)), [2024, 2024, 2024, 2024])
        self.assertEqual(list(frutas.season_start(pd.Series(pd.to_datetime(["2025-11-01"])), 11)), [2025])  # cambia en noviembre
        self.assertEqual(frutas.label(2024, 11), "2024/25")
        self.assertEqual(frutas.label(2024, 1), "2024")  # año calendario

    def test_weighted_price_uses_kilos_as_weights_and_ignores_missing_weight(self):
        frame = pd.DataFrame({"price_vwap_clp_kg_real": [1000.0, 500.0, 9999.0], "volume_kg_est": [100.0, 300.0, 0.0]})
        self.assertAlmostEqual(frutas.weighted(frame), (1000 * 100 + 500 * 300) / 400)
        self.assertTrue(np.isnan(frutas.weighted(frame.iloc[[2]])))  # sin kilos no hay precio ponderado

    def test_each_configured_product_has_a_season_window_that_contains_its_start_month(self):
        for name, config in frutas.PRODUCTS.items():
            self.assertIn(config["start_month"], config["months"], name)


if __name__ == "__main__":
    unittest.main()
