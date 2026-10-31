import tempfile
import unittest
from pathlib import Path

import pandas as pd

from materias_primas_chile.source_index import build_index


class SourceIndexTests(unittest.TestCase):
    def test_summarizes_each_product_unit_pair_without_mixing_units(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "data/processed/faostat"
            target.mkdir(parents=True)
            pd.DataFrame({
                "date": ["1991-01-01", "1992-01-01", "1991-01-01", "1991-01-01"],
                "item": ["Wheat", "Wheat", "Wheat", "Maize (corn)"],
                "unit": ["LCU/tonne", "LCU/tonne", "USD/tonne", "LCU/tonne"],
                "currency": ["CLP", "CLP", "USD", "CLP"],
                "value": [63898.0, 68811.0, 181.5, None],  # el vacío no cuenta
            }).to_csv(target / "producer_prices.csv", index=False)
            index = build_index(root, "data/curated/source_index.csv")
            self.assertEqual(len(index), 2)  # trigo en CLP y trigo en USD, nunca mezclados
            clp = index[index.currency.eq("CLP")].iloc[0]
            self.assertEqual((clp["product"], clp.n_obs, clp.first_date, clp.last_date),
                             ("Wheat", 2, pd.Timestamp("1991-01-01"), pd.Timestamp("1992-01-01")))
            self.assertTrue((root / "data/curated/source_index.csv").exists())

    def test_fails_clearly_when_nothing_has_been_processed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_index(directory)


if __name__ == "__main__":
    unittest.main()
