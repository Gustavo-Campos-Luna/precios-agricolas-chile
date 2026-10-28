"""Synthetic fixtures test temporal and spatial contracts, not predictive skill."""
import unittest

import numpy as np
import pandas as pd

from materias_primas_chile.features import build_features, future_assumptions


def climate():
    months = pd.date_range("2020-01-01", "2025-12-01", freq="MS")
    return pd.DataFrame({"location_id": "talca", "month": months,
                         "temperature_mean_c": months.month.astype(float),
                         "precipitation_mm": months.month.astype(float) * 10})


class FeatureTests(unittest.TestCase):
    def test_exact_origin_only_and_calendar_lag(self):
        prices = pd.DataFrame({"series_id": ["matched", "imported", "unmapped"],
                               "date": ["2020-04-01"] * 3, "price": [100, 200, 300]})
        metadata = pd.DataFrame({"series_id": ["matched", "imported", "unmapped"],
                                "origin": ["Región del Maule", "Perú", "Not declared"],
                                "market_region": ["elsewhere", "Maule", "Maule"]})
        mapping = pd.DataFrame({"origin": ["Región del Maule"], "location_id": ["talca"],
                                "mapping_role": ["city_point_proxy"]})
        output, report = build_features(prices, metadata, climate(), mapping)
        self.assertEqual(output.series_id.tolist(), ["matched"])
        self.assertEqual(output.temp_lag3.iloc[0], 1)
        self.assertEqual(output.climate_source_month.iloc[0], pd.Timestamp("2020-01-01"))
        self.assertEqual(report["unmapped_origin_rows"], 2)

    def test_duplicate_mapping_or_climate_rejected(self):
        prices = pd.DataFrame({"series_id": ["s"], "date": ["2020-04-01"], "price": [100]})
        metadata = pd.DataFrame({"series_id": ["s"], "origin": ["Maule"]})
        mapping = pd.DataFrame({"origin": ["Maule"], "location_id": ["talca"], "mapping_role": ["city_point_proxy"]})
        with self.assertRaises(ValueError):
            build_features(prices, metadata, climate(), pd.concat([mapping, mapping]))
        with self.assertRaises(ValueError):
            build_features(prices, metadata, pd.concat([climate(), climate().iloc[[0]]]), mapping)

    def test_scenario_ignores_unavailable_future_observations(self):
        locations = pd.DataFrame({"series_id": ["s"], "location_id": ["talca"]})
        original = climate()
        altered = original.copy()
        changed = altered.month > pd.Timestamp("2024-09-01")
        altered.loc[changed, "temperature_mean_c"] = 9999
        altered.loc[changed, "precipitation_mm"] = 9999
        first = future_assumptions(locations, original, "2024-12-01")
        second = future_assumptions(locations, altered, "2024-12-01")
        np.testing.assert_allclose(first[["temp_lag3", "precip_lag3"]], second[["temp_lag3", "precip_lag3"]])

    def test_scenario_cannot_change_weather_before_origin(self):
        locations = pd.DataFrame({"series_id": ["s"], "location_id": ["talca"]})
        baseline = future_assumptions(locations, climate(), "2025-12-01")
        warmer = future_assumptions(locations, climate(), "2025-12-01", temperature_delta_c=2, precipitation_factor=.8)
        np.testing.assert_allclose(warmer.temp_lag3.iloc[:3], baseline.temp_lag3.iloc[:3])
        np.testing.assert_allclose(warmer.precip_lag3.iloc[:3], baseline.precip_lag3.iloc[:3])
        np.testing.assert_allclose(warmer.temp_lag3.iloc[3:], baseline.temp_lag3.iloc[3:] + 2)
        np.testing.assert_allclose(warmer.precip_lag3.iloc[3:], baseline.precip_lag3.iloc[3:] * .8)
        self.assertFalse(warmer.anomaly_applied.iloc[:3].any())
        self.assertTrue(warmer.anomaly_applied.iloc[3:].all())

    def test_missing_climatology_fails_instead_of_inventing_values(self):
        locations = pd.DataFrame({"series_id": ["s"], "location_id": ["talca"]})
        with self.assertRaises(ValueError):
            future_assumptions(locations, climate().iloc[:2], "2025-12-01")
        with self.assertRaises(ValueError):
            future_assumptions(locations, climate(), "2025-12-01", precipitation_factor=-1)


if __name__ == "__main__":
    unittest.main()
