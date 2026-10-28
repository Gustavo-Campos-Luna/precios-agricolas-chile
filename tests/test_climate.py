"""Fixtures sintéticas exclusivamente para verificar transformaciones, no datos reales."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from materias_primas_chile.climate import (Location, PARAMETERS, aggregate_monthly,
    build_power_url, fetch_power, historical_features, parse_power)


class ClimateTests(unittest.TestCase):
    def setUp(self):
        self.location = Location("talca", -35.4264, -71.6554, "07")
        self.payload = {"header": {"fill_value": -999}, "properties": {"parameter": {
            p: {"20240101": 1, "20240102": -999} for p in PARAMETERS}}}

    def test_url_and_coordinate_validation(self):
        self.assertIn("time-standard=UTC", build_power_url(self.location, "2023-01-01", "2023-12-31"))
        with self.assertRaises(ValueError):
            Location("../bad", -35, -71)
        with self.assertRaises(ValueError):
            build_power_url(self.location, "2024-01-01", "2023-01-01")

    def test_missing_sentinel_is_not_rainfall(self):
        frame = parse_power(self.payload, self.location)
        self.assertTrue(pd.isna(frame.loc[1, "precipitation_mm"]))
        self.assertEqual(frame.loc[0, "spatial_scope"], "grid_point_proxy")
        self.payload["properties"]["parameter"]["PRECTOTCORR"]["20240101"] = -1
        with self.assertRaises(ValueError):
            parse_power(self.payload, self.location)

    def test_incomplete_month_never_becomes_total(self):
        daily = pd.DataFrame({"date": pd.date_range("2024-02-01", "2024-02-29"),
                              "location_id": "talca", **{c: 1.0 for c in PARAMETERS.values()}})
        result = aggregate_monthly(daily)
        self.assertEqual(result.iloc[0]["precipitation_mm"], 29)
        daily.loc[0, "precipitation_mm"] = float("nan")
        result = aggregate_monthly(daily)
        self.assertTrue(pd.isna(result.iloc[0]["precipitation_mm"]))
        self.assertEqual(result.iloc[0]["precipitation_mm_valid_days"], 28)
        with self.assertRaises(ValueError):
            aggregate_monthly(pd.concat([daily, daily.iloc[:1]]))

    def test_future_climate_excluded(self):
        monthly = pd.DataFrame({"month": ["2024-01-01", "2024-02-01", "2025-01-01"]})
        result = historical_features(monthly, "2024-04-01", release_lag_days=60)
        self.assertEqual(result["month"].tolist(), ["2024-01-01"])

    def test_cache_hash_and_query_verified(self):
        payload = json.dumps(self.payload).encode()
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self): return payload
        with tempfile.TemporaryDirectory() as directory:
            with patch("materias_primas_chile.climate.urlopen", return_value=Response()):
                fetch_power(self.location, "2024-01-01", "2024-01-02", directory)
            with patch("materias_primas_chile.climate.urlopen", side_effect=AssertionError("network")):
                self.assertEqual(len(fetch_power(self.location, "2024-01-01", "2024-01-02", directory)), 2)
            path = next(Path(directory).rglob("2024*.json"))
            path.write_bytes(b"corrupted")
            with self.assertRaises(ValueError):
                fetch_power(self.location, "2024-01-01", "2024-01-02", directory)


if __name__ == "__main__":
    unittest.main()
