import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from materias_primas_chile.analysis import build_panel, unit_factors


def write_fixture(root: Path):
    curated, macro = root / "curated", root / "macro"
    curated.mkdir()
    macro.mkdir()
    pd.DataFrame({
        "series_id": ["a", "a", "b", "c"], "date": ["2026-08-01", "2026-09-01", "2026-09-01", "2026-09-01"],
        "price": [8000.0, 9000.0, 300.0, 40000.0], "n_observations": [5, 6, 4, 3], "price_vwap": [8500.0, 9500.0, 310.0, 41000.0],
        "volume_units": [100, 120, 50, 20], "volume_basis": ["x", "x", "y", "x"],
        "n_days": [5, 6, 4, 3], "volume_max_day": [30, 40, 20, 10]}).to_csv(curated / "monthly_with_volume.csv", index=False)
    pd.DataFrame({
        "series_id": ["a", "b", "c"], "market_region_code": [13, 13, 13], "market_region": ["RM"] * 3, "market": ["Lo Valledor"] * 3,
        "product": ["Cereza", "Choclo", "Manzana"], "variety": ["Sultanina", "Sin especificar", "Fuji"],
        "quality": ["Primera"] * 3, "origin": ["Curicó", "Maule", "Maule"],
        "unit": ["$/bandeja 10 kilos", "$/cien", "$/bins (400 kilos)"], "currency": ["CLP"] * 3, "market_level": ["wholesale"] * 3}).to_csv(curated / "series.csv", index=False)
    pd.DataFrame({"date": ["2026-08-01", "2026-09-01"], "cpi_index": [98.0, 100.0]}).to_csv(macro / "cpi_index.csv", index=False)
    pd.DataFrame({"date": ["2026-08-01", "2026-09-01", "2026-10-01"], "usd_clp": [900.0, 950.0, 960.0]}).to_csv(
        macro / "usd_clp_monthly.csv", index=False)
    return curated, macro


class AnalysisTests(unittest.TestCase):
    def test_unit_factors_give_kg_only_with_declared_weight(self):
        f = unit_factors(pd.Series(["$/bandeja 10 kilos", "$/cien", "$/bins (400 kilos)", "$/docena de atados"])).set_index("unit")
        self.assertAlmostEqual(f.loc["$/bandeja 10 kilos", "kg_factor"], 0.1)
        self.assertAlmostEqual(f.loc["$/bins (400 kilos)", "kg_factor"], 1 / 400)
        self.assertTrue(np.isnan(f.loc["$/cien", "kg_factor"]))  # por pieza: no se inventan kilos
        self.assertTrue(np.isnan(f.loc["$/docena de atados", "kg_factor"]))

    def test_panel_converts_deflates_and_harmonizes_without_inventing(self):
        with tempfile.TemporaryDirectory() as directory:
            curated, macro = write_fixture(Path(directory))
            panel = build_panel(curated, macro).set_index(["series_id", "date"])
        sep = panel.loc[("a", pd.Timestamp("2026-09-01"))]
        self.assertAlmostEqual(sep.price_clp_kg, 900.0)                       # 9000 por bandeja de 10 kg
        self.assertAlmostEqual(sep.price_real, 9000.0)                        # IPC septiembre = 100
        self.assertAlmostEqual(sep.price_usd_kg, 900.0 / 950.0)
        aug = panel.loc[("a", pd.Timestamp("2026-08-01"))]
        self.assertAlmostEqual(aug.price_real, 8000.0 * 100 / 98.0)          # agosto vale más en pesos de septiembre
        self.assertEqual(str(sep.variety_canonical), "thompsonseedless")      # Sultanina -> alias oficial
        self.assertEqual(sep.volume_kg_est, 1200.0)                           # 120 bandejas de 10 kg
        bins = panel.loc[("c", pd.Timestamp("2026-09-01"))]
        self.assertEqual(bins.volume_kg_est, 8000.0)                          # 20 bins de 400 kg: peso declarado en la etiqueta
        self.assertAlmostEqual(bins.price_clp_kg, 100.0)
        choclo = panel.loc[("b", pd.Timestamp("2026-09-01"))]
        self.assertTrue(np.isnan(choclo.volume_kg_est))                       # por pieza: no se inventan kilos
        self.assertTrue(np.isnan(choclo.price_clp_kg) and np.isnan(choclo.price_usd_kg))
        self.assertAlmostEqual(choclo.price_real, 300.0)                      # el precio por cien sí se deflacta
        self.assertEqual(str(choclo.variety_group), "")                       # "sin especificar" no es variedad

    def test_months_without_cpi_stay_empty_instead_of_extrapolating(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            curated, macro = write_fixture(root)
            monthly = pd.read_csv(curated / "monthly_with_volume.csv")
            monthly.loc[0, "date"] = "2026-10-01"                              # octubre: aún sin IPC publicado
            monthly.to_csv(curated / "monthly_with_volume.csv", index=False)
            panel = build_panel(curated, macro)
        october = panel[panel.date.eq(pd.Timestamp("2026-10-01"))].iloc[0]
        self.assertTrue(np.isnan(october.price_real))
        self.assertFalse(np.isnan(october.price_usd_kg))                       # el dólar de octubre sí existe


if __name__ == "__main__":
    unittest.main()
