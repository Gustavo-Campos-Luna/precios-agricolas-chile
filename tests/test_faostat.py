import unittest

import pandas as pd

from materias_primas_chile.faostat import normalize

COLUMNS = ["StartDate", "EndDate", "Item Code", "Item", "Element", "Months", "Value", "Flag"]


class FaostatTests(unittest.TestCase):
    def test_keeps_currencies_separate_and_drops_missing_values(self):
        frame = pd.DataFrame([
            ["1991-01-01", "1991-12-31", "15", "Wheat", "Producer Price (LCU/tonne)", "Annual value", "63898.0", "A"],
            ["1991-01-01", "1991-12-31", "15", "Wheat", "Producer Price (USD/tonne)", "Annual value", "181.5", "A"],
            ["1991-02-01", "1991-02-28", "15", "Wheat", "Producer Price (LCU/tonne)", "February", "", "E"],
        ], columns=COLUMNS)
        out = normalize(frame)
        self.assertEqual(len(out), 2)  # el valor vacío se omite, no se vuelve cero
        self.assertEqual(list(out.currency), ["CLP", "USD"])
        self.assertEqual(list(out.unit), ["LCU/tonne", "USD/tonne"])
        self.assertTrue(out.frequency.eq("annual").all())
        self.assertEqual(out.date.iloc[0], pd.Timestamp("1991-01-01"))

    def test_unknown_element_fails_loudly(self):
        frame = pd.DataFrame([["1991-01-01", "1991-12-31", "15", "Wheat", "Yield", "Annual value", "1", "A"]], columns=COLUMNS)
        with self.assertRaises(ValueError):
            normalize(frame)


if __name__ == "__main__":
    unittest.main()


class FaostatProductionTests(unittest.TestCase):
    def test_wide_table_keeps_missing_measures_empty_and_ignores_livestock_elements(self):
        from materias_primas_chile.faostat import normalize_production
        frame = pd.DataFrame([
            ["Cherries", "2024", "Area harvested", "76447", "A"],
            ["Cherries", "2024", "Production", "596967.55", "A"],
            ["Cherries", "2024", "Yield", "7808.9", "C"],
            ["Cherries", "2023", "Production", "520000", "A"],            # sin superficie ese año: queda vacía, no cero
            ["Cherries", "2024", "Stocks", "10", "A"],                    # elemento ajeno: se ignora
        ], columns=["Item", "Year", "Element", "Value", "Flag"])
        out = normalize_production(frame).set_index("year")
        self.assertEqual(out.loc[2024, "area_ha"], 76447)
        self.assertEqual(out.loc[2024, "yield_kg_ha"], 7808.9)
        self.assertTrue(pd.isna(out.loc[2023, "area_ha"]))
        self.assertNotIn("stocks", out.columns)
