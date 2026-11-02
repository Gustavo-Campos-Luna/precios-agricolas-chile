import unittest

import numpy as np
import pandas as pd

from materias_primas_chile import agroclimate as ag


def _daily(year: int = 2020, tmin: float = 8.0, tmax: float = 24.0, rain: float = 0.0) -> pd.DataFrame:
    idx = pd.date_range(f"{year}-01-01", f"{year + 1}-03-31", freq="D")
    return pd.DataFrame({"temperature_2m_min": tmin, "temperature_2m_max": tmax, "precipitation_sum": rain}, index=idx)


def _hourly(year: int = 2020, temp: float = 5.0) -> pd.Series:
    idx = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00", freq="h")
    return pd.Series(temp, index=idx)


class SeasonIndicesTests(unittest.TestCase):
    def test_counts_frost_days_and_chill_hours_in_their_own_windows(self):
        daily = _daily()
        daily.loc["2020-09-10":"2020-09-14", "temperature_2m_min"] = -1.0  # 5 días de helada en septiembre
        daily.loc["2020-07-01":"2020-07-03", "temperature_2m_min"] = -3.0  # helada de invierno: no cuenta
        r = ag.season_indices(daily, _hourly(temp=5.0), 2020)
        self.assertEqual(r["frost_days_0"], 5.0)
        self.assertEqual(r["frost_days_2"], 5.0)
        self.assertEqual(r["chill_hours"], 123 * 24)  # mayo a agosto, todas las horas entre 0 y 7,2 °C

    def test_chill_hours_exclude_warm_and_freezing_hours(self):
        hourly = _hourly(temp=5.0)
        hourly.loc["2020-06-01":"2020-06-10"] = 12.0  # 10 días cálidos
        hourly.loc["2020-07-01":"2020-07-02"] = -2.0  # 2 días bajo cero
        r = ag.season_indices(_daily(), hourly, 2020)
        self.assertEqual(r["chill_hours"], (123 - 12) * 24)

    def test_harvest_window_spans_two_calendar_years(self):
        daily = _daily(rain=0.0)
        daily.loc["2020-12-20", "precipitation_sum"] = 30.0
        daily.loc["2021-01-10", "precipitation_sum"] = 12.0
        daily.loc["2020-11-01", "precipitation_sum"] = 99.0  # antes del 15 de noviembre: fuera
        daily.loc["2020-12-25":"2020-12-26", "temperature_2m_max"] = 33.0
        r = ag.season_indices(daily, None, 2020)
        self.assertEqual(r["rain_harvest_mm"], 42.0)
        self.assertEqual(r["rainy_days_5"], 2.0)
        self.assertEqual(r["heat_days_30"], 2.0)
        self.assertTrue(np.isnan(r["chill_hours"]))  # sin horario no se inventa

    def test_incomplete_windows_return_nan_instead_of_partial_sums(self):
        daily = _daily().loc[:"2020-12-31"]  # la cosecha termina el 31 de enero: faltan 31 días
        r = ag.season_indices(daily, None, 2020)
        self.assertTrue(np.isnan(r["rain_harvest_mm"]))
        self.assertFalse(np.isnan(r["frost_days_0"]))


class BuildTests(unittest.TestCase):
    def test_build_and_regional_mean(self):
        a, b = _daily(tmin=-1.0), _daily(tmin=5.0)
        table = ag.build_indices({"a": a, "b": b}, {}, first=2020, last=2020)
        self.assertEqual(sorted(table["site"]), ["a", "b"])
        self.assertEqual(ag.regional_mean(table).loc[2020, "frost_days_0"], 30.5)  # (61 + 0) / 2


if __name__ == "__main__":
    unittest.main()
