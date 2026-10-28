import numpy as np
import pandas as pd
import unittest

from materias_primas_chile.forecast import backtest_monthly, forecast_monthly


def monthly(n=60):
    dates = pd.date_range("2018-01-01", periods=n, freq="MS")
    return pd.DataFrame({
        "date": dates, "series_id": "uva_rm",
        "price_clp_kg": 100 + np.arange(n) * 0.2 + 10 * np.sin(2 * np.pi * dates.month / 12),
        "temperature": 15 + 4 * np.sin(2 * np.pi * dates.month / 12),
    })


class ForecastTests(unittest.TestCase):
    def test_seasonal_forecast_repeats_last_year(self):
        data = monthly()
        result = forecast_monthly(data)
        np.testing.assert_allclose(result.prediction, data.price_clp_kg.iloc[-12:])
        assert result.date.min() > data.date.max()
        assert result.horizon.tolist() == list(range(1, 13))


    def test_backtest_does_not_read_heldout_prices_or_weather(self):
        original = monthly()
        cutoff = pd.Timestamp("2021-01-01")
        altered = original.copy()
        future = altered.date > cutoff
        altered.loc[future, "price_clp_kg"] *= 10
        altered.loc[future, "temperature"] += 100
        first, _ = backtest_monthly(original, stride=1, climate_cols=["temperature"])
        second, _ = backtest_monthly(altered, stride=1, climate_cols=["temperature"])
        a = first.loc[first.cutoff == cutoff, "prediction"].to_numpy()
        b = second.loc[second.cutoff == cutoff, "prediction"].to_numpy()
        assert len(a) > 0
        np.testing.assert_allclose(a, b, equal_nan=True)


    def test_missing_month_is_not_interpolated(self):
        data = monthly().drop(index=50)
        result = forecast_monthly(data)
        # Forecast March depends on the missing March in the previous year.
        march = result.loc[result.date.dt.month == 3]
        assert march.prediction.isna().all()
        assert march.status.eq("missing_lag_or_training_data").all()


    def test_short_history_abstains(self):
        result = forecast_monthly(monthly(18))
        assert result.prediction.isna().all()
        assert result.status.eq("insufficient_history").all()

    def test_stale_series_uses_common_origin_and_abstains_without_forward_fill(self):
        current = monthly(96)
        current["series_id"] = "current_2025"
        stale = monthly(36)
        stale["series_id"] = "stale_2020"
        data = pd.concat([current, stale], ignore_index=True)
        for model in ("naive", "seasonal_naive", "ridge"):
            with self.subTest(model=model):
                result = forecast_monthly(data, model=model)
                self.assertTrue(result.cutoff.eq(pd.Timestamp("2025-12-01")).all())
                self.assertTrue(result.date.gt(data.date.max()).all())
                self.assertTrue(result.date.dt.year.eq(2026).all())
                old = result.loc[result.series_id.eq("stale_2020")]
                self.assertTrue(old.prediction.isna().all())
                self.assertTrue(old.status.eq("missing_lag_or_training_data").all())
                recent = result.loc[result.series_id.eq("current_2025")]
                self.assertTrue(recent.prediction.notna().all())

    def test_explicit_origin_cannot_relabel_historical_targets_as_forecasts(self):
        data = monthly()
        with self.assertRaisesRegex(ValueError, "latest input month"):
            forecast_monthly(data, forecast_origin="2021-12-01")
        with self.assertRaisesRegex(ValueError, "valid month"):
            forecast_monthly(data, forecast_origin=pd.NaT)
        result = forecast_monthly(data, forecast_origin="2024-12-15")
        self.assertTrue(result.cutoff.eq(pd.Timestamp("2024-12-01")).all())
        self.assertTrue(result.date.dt.year.eq(2025).all())
        self.assertTrue(result.prediction.isna().all())


    def test_duplicate_month_is_rejected(self):
        data = monthly()
        extra = data.iloc[[0]].copy()
        extra["date"] += pd.Timedelta(days=2)
        with self.assertRaisesRegex(ValueError, "unique monthly"):
            forecast_monthly(pd.concat([data, extra]))


    def test_scenario_requires_explicit_complete_assumptions(self):
        data = monthly()
        future = pd.DataFrame({"date": pd.date_range("2023-01-01", periods=12, freq="MS"),
                               "series_id": "uva_rm", "temperature": 20.0})
        with self.assertRaisesRegex(ValueError, "scenario_name"):
            forecast_monthly(data, model="ridge", climate_cols=["temperature"], future_climate=future)
        result = forecast_monthly(data, model="ridge", climate_cols=["temperature"],
                                  future_climate=future, scenario_name="warm_assumption")
        assert result.scenario.eq("warm_assumption").all()
        assert result.prediction.notna().all()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            forecast_monthly(data, model="ridge", climate_cols=["temperature"],
                             future_climate=future.iloc[:-1], scenario_name="warm_assumption")


    def test_metrics_report_scored_observations_and_exact_naive_error(self):
        data = monthly(36)
        data["price_clp_kg"] = np.arange(1, 37, dtype=float)
        predictions, metrics = backtest_monthly(data, horizon=2, stride=1, models=["naive"])
        assert (predictions.prediction - predictions.actual).abs().eq(predictions.horizon).all()
        self.assertAlmostEqual(metrics.loc[metrics.horizon == 1, "mae"].iloc[0], 1)
        self.assertAlmostEqual(metrics.loc[metrics.horizon == 2, "mae"].iloc[0], 2)
        assert (metrics.n_scored <= metrics.n_observed).all()

    def test_optional_seasonal_ridge_predicts_season_without_imputing_offseason(self):
        dates = pd.date_range("2020-01-01", "2025-12-01", freq="MS")
        dates = dates[dates.month <= 4]
        data = pd.DataFrame({"date": dates, "series_id": "synthetic_seasonal",
            "price_clp_kg": 100 + dates.year - 2020 + dates.month * 2,
            "temperature": 15 + dates.month.astype(float)})
        future = pd.DataFrame({"date": pd.date_range("2026-01-01", periods=12, freq="MS"),
            "series_id": "synthetic_seasonal", "temperature": 20.0})
        original = forecast_monthly(data, model="ridge", climate_cols=["temperature"],
            future_climate=future, scenario_name="synthetic", forecast_origin="2025-12-01")
        self.assertTrue(original.prediction.isna().all())
        result = forecast_monthly(data, model="ridge_seasonal", climate_cols=["temperature"],
            future_climate=future, scenario_name="synthetic", forecast_origin="2025-12-01")
        self.assertTrue(result.loc[result.date.dt.month <= 4, "prediction"].gt(0).all())
        self.assertTrue(result.loc[result.date.dt.month > 4, "prediction"].isna().all())
        self.assertTrue(result.cutoff.eq(pd.Timestamp("2025-12-01")).all())
        stale = forecast_monthly(data, model="ridge_seasonal", climate_cols=["temperature"],
                                 forecast_origin="2027-12-01")
        self.assertTrue(stale.prediction.isna().all())

    def test_optional_seasonal_ridge_backtest_excludes_future_prices_and_climate(self):
        data = monthly(96)
        changed = data.copy()
        cutoff = pd.Timestamp("2021-12-01")
        changed.loc[changed.date > cutoff, "price_clp_kg"] *= 10
        changed.loc[changed.date > cutoff, "temperature"] += 100
        first, _ = backtest_monthly(data, models=["ridge_seasonal"], climate_cols=["temperature"], stride=1)
        second, _ = backtest_monthly(changed, models=["ridge_seasonal"], climate_cols=["temperature"], stride=1)
        a = first.loc[first.cutoff.eq(cutoff), "prediction"]
        b = second.loc[second.cutoff.eq(cutoff), "prediction"]
        self.assertGreater(len(a), 0)
        np.testing.assert_allclose(a, b, equal_nan=True)

if __name__ == "__main__":
    unittest.main()
