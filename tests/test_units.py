import unittest

import numpy as np
import pandas as pd

from materias_primas_chile.units import enrich_units


class UnitConversionTests(unittest.TestCase):
    def frame(self, labels, price=18000, currency="CLP"):
        return pd.DataFrame({"unit": labels, "price": price, "currency": currency,
                             "series_id": [f"synthetic_{i}" for i in range(len(labels))]})

    def test_observed_odepa_package_labels_use_only_explicit_kg(self):
        source = self.frame(["$/bandeja 10 kilos", "$/caja 18 kilos", "$/saco 25 kilos"])
        result = enrich_units(source)
        np.testing.assert_allclose(result.price_clp_kg, [1800, 1000, 720])
        np.testing.assert_allclose(result.commercial_weight_kg, [10, 18, 25])
        self.assertTrue(result.unit_conversion_method.eq("explicit_package_weight_kg").all())
        self.assertTrue(result.price_clp_unit.isna().all())

    def test_per_kilo_with_package_context_never_divides_by_package_weight(self):
        result = enrich_units(self.frame(["$/kilo", "$/kilo (en bandeja de 18 kilos)"]))
        np.testing.assert_allclose(result.price_clp_kg, [18000, 18000])
        self.assertTrue(pd.isna(result.commercial_weight_kg.iloc[0]))
        self.assertEqual(result.commercial_weight_kg.iloc[1], 18)
        self.assertTrue(result.unit_conversion_method.eq("already_per_kg").all())

    def test_item_counts_do_not_become_kilograms(self):
        result = enrich_units(self.frame(["$/malla 100 unidades", "$/unidad", "$/cien"]))
        np.testing.assert_allclose(result.price_clp_unit, [180, 18000, 180])
        self.assertTrue(result.price_clp_kg.isna().all())
        self.assertTrue(result.commercial_weight_kg.isna().all())

    def test_no_assumed_weight_for_unknown_or_ambiguous_labels(self):
        labels = ["$/quintal", "$/caja", "$/malla", "$/caja 18 a 20 kilos",
                  "$/caja 18/20 kilos", "$/caja 18 kilos o kilo", "$/caja 0 kilos",
                  "$/caja -18 kilos", "$/malla 0 unidades", "$/caja 18 toneladas",
                  "$/saco 1.000 kilos", "$/caja 18,500 kilos",
                  "$/kilo (en bandeja de 18 a 20 kilos)", "$/caja 18 kilos netos o 20 brutos"]
        result = enrich_units(self.frame(labels))
        self.assertTrue(result.price_clp_kg.isna().all())
        self.assertTrue(result.price_clp_unit.isna().all())
        self.assertTrue(result.unit_conversion_method.eq("unsupported_unit").all())

    def test_currency_and_invalid_prices_block_monetary_conversion(self):
        for currency in ["USD", None, ""]:
            with self.subTest(currency=currency):
                result = enrich_units(self.frame(["$/caja 18 kilos"], currency=currency))
                self.assertTrue(result.price_clp_kg.isna().all())
                self.assertTrue(result.unit_conversion_method.eq("unsupported_currency").all())
                self.assertEqual(result.commercial_weight_kg.iloc[0], 18)
        for price in [0, -1, float("inf"), float("nan"), "not-a-number", pd.NA]:
            with self.subTest(price=price):
                result = enrich_units(self.frame(["$/kilo"], price=price))
                self.assertTrue(result.price_clp_kg.isna().all())
                self.assertTrue(result.unit_conversion_method.eq("invalid_price").all())

    def test_decimal_weights_and_case_whitespace_preserve_original_fields(self):
        source = self.frame(["  CLP/CAJA de 18,5 KILOGRAMOS  ", "Caja 8 kilos", "$/malla 2.5 kg"])
        source.index = [9, 2, 100]
        pristine = source.copy(deep=True)
        result = enrich_units(source)
        np.testing.assert_allclose(result.price_clp_kg, [18000 / 18.5, 2250, 7200])
        pd.testing.assert_frame_equal(source, pristine)
        pd.testing.assert_frame_equal(result[source.columns], source)
        self.assertEqual(result.index.tolist(), [9, 2, 100])

    def test_missing_contract_columns_raise_and_empty_input_keeps_schema(self):
        with self.assertRaisesRegex(ValueError, "currency"):
            enrich_units(pd.DataFrame({"unit": ["$/kilo"], "price": [500]}))
        empty = enrich_units(self.frame([]))
        self.assertEqual(len(empty), 0)
        self.assertIn("price_clp_kg", empty)
        self.assertIn("unit_conversion_method", empty)


if __name__ == "__main__":
    unittest.main()
