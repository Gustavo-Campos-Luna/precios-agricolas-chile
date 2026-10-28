"""Offline integration tests; synthetic observations never enter repository data."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from materias_primas_chile.cli import main


class CLITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = self.root / "snapshots"
        self.outputs = self.root / "curated"
        self.inputs.mkdir()

    def call(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(map(str, args)))
        return code, stdout.getvalue(), stderr.getvalue()

    def fixture(self):
        rows = []
        for month, date in enumerate(pd.date_range("2020-01-01", periods=36, freq="MS")):
            for series, product, unit, base in [
                ("synthetic_grape_kg", "Uva", "Kilo", 100),
                ("synthetic_grape_box", "Uva", "Caja 18 kg", 900),
            ]:
                for day, amount in [(1, base + month), (15, base + month + 20)]:
                    rows.append({
                        "date": date.replace(day=day), "series_id": series,
                        "price": float(amount), "market_region_code": "13",
                        "market_region": "Metropolitana", "market": "SYNTHETIC TEST",
                        "product": product, "variety": "test", "quality": "test", "unit": unit,
                        "origin": "test", "currency": "CLP", "market_level": "wholesale",
                        "source": "SYNTHETIC_FIXTURE", "source_resource_id": "fixture",
                        "source_snapshot_sha256": "synthetic_sha",
                        "source_record": f"{series}-{date.year}-{date.month}-{day}",
                    })
        return pd.DataFrame(rows)

    def build_fixture(self):
        self.fixture().to_csv(self.inputs / "fixture.csv", index=False)
        code, _, error = self.call("build", "--input", self.inputs, "--output", self.outputs)
        self.assertEqual(code, 0, error)
        return pd.read_csv(self.outputs / "monthly.csv")

    def test_build_deduplicates_identical_snapshot_and_keeps_units_separate(self):
        data = self.fixture()
        data.to_csv(self.inputs / "first.csv", index=False)
        data.to_csv(self.inputs / "same_snapshot_again.csv", index=False)
        code, _, error = self.call("build", "--input", self.inputs, "--output", self.outputs)
        self.assertEqual(code, 0, error)
        daily = pd.read_csv(self.outputs / "daily.csv")
        monthly = pd.read_csv(self.outputs / "monthly.csv")
        self.assertEqual(len(daily), 144)
        self.assertEqual(len(monthly), 72)
        self.assertTrue(monthly.n_observations.eq(2).all())
        first_month = monthly.loc[monthly.date == "2020-01-01"].set_index("series_id")
        self.assertEqual(first_month.at["synthetic_grape_kg", "price"], 110)
        self.assertEqual(first_month.at["synthetic_grape_box", "price"], 910)
        dimensions = pd.read_csv(self.outputs / "series.csv")
        self.assertEqual(set(dimensions.unit), {"Kilo", "Caja 18 kg"})
        report = json.loads((self.outputs / "quality.json").read_text())
        self.assertTrue(report["passed"])
        self.assertEqual(report["quarantine_rows"], 0)

    def test_build_quarantines_conflicting_daily_values_and_invalid_prices(self):
        clean = self.fixture()
        conflict = clean.iloc[[0]].copy()
        conflict["price"] += 500
        conflict["source_record"] = "conflicting-source-record"
        bad = clean.iloc[[1]].copy()
        bad["series_id"] = "invalid_test_series"
        bad["price"] = -10
        bad["source_record"] = "negative-price-record"
        pd.concat([clean, conflict, bad], ignore_index=True).to_csv(self.inputs / "fixture.csv", index=False)
        code, _, error = self.call("build", "--input", self.inputs, "--output", self.outputs)
        self.assertEqual(code, 0, error)
        quarantine = pd.read_csv(self.outputs / "quarantine.csv")
        self.assertEqual(len(quarantine), 3)
        self.assertEqual(quarantine.rejection_reason.str.contains("ambiguous_series_date").sum(), 2)
        self.assertEqual(quarantine.rejection_reason.str.contains("invalid_date_key_or_price").sum(), 1)
        accepted = pd.read_csv(self.outputs / "daily.csv")
        self.assertEqual(len(accepted), len(clean) - 1)
        self.assertFalse(accepted.duplicated(["series_id", "date"]).any())
        self.assertTrue(accepted.price.gt(0).all())

    def test_forecast_and_backtest_roundtrip_real_cli_paths_offline(self):
        monthly = self.build_fixture()
        model_output = self.root / "models"
        code, _, error = self.call("forecast", "--input", self.outputs / "monthly.csv",
                                   "--output", model_output, "--horizon", 12)
        self.assertEqual(code, 0, error)
        projected = pd.read_csv(model_output / "forecast.csv")
        self.assertEqual(len(projected), 24)
        self.assertTrue(projected.status.eq("ok").all())
        for series, group in projected.groupby("series_id"):
            last_year = monthly.loc[monthly.series_id.eq(series)].sort_values("date").tail(12)
            np.testing.assert_allclose(group.prediction, last_year.price)
        code, _, error = self.call("backtest", "--input", self.outputs / "monthly.csv",
                                   "--output", model_output, "--horizon", 3, "--stride", 3)
        self.assertEqual(code, 0, error)
        scored = pd.read_csv(model_output / "backtest_predictions.csv")
        metrics = pd.read_csv(model_output / "backtest_metrics.csv")
        self.assertEqual(set(scored.model), {"naive", "seasonal_naive", "ridge"})
        self.assertTrue((pd.to_datetime(scored.date) > pd.to_datetime(scored.cutoff)).all())
        self.assertEqual(set(metrics.horizon), {1, 2, 3})
        seasonal = metrics.loc[metrics.model.eq("seasonal_naive")]
        np.testing.assert_allclose(seasonal.mae, 12)
        self.assertTrue(metrics.n_scored.gt(0).all())

    def test_cli_rejects_duplicate_monthly_targets_instead_of_silent_average(self):
        monthly = self.build_fixture()
        bad = self.root / "bad_monthly.csv"
        pd.concat([monthly, monthly.iloc[[0]]]).to_csv(bad, index=False)
        code, _, error = self.call("forecast", "--input", bad, "--output", self.root / "rejected")
        self.assertEqual(code, 1)
        self.assertIn("unique monthly", error)
        self.assertFalse((self.root / "rejected" / "forecast.csv").exists())

    def test_cli_rejects_incomplete_climate_scenario(self):
        monthly = self.build_fixture()
        monthly["temperature"] = 15.0
        monthly_path = self.root / "monthly_climate.csv"
        monthly.to_csv(monthly_path, index=False)
        incomplete = pd.DataFrame({"date": ["2023-01-01"],
                                   "series_id": ["synthetic_grape_kg"], "temperature": [17.0]})
        scenario_path = self.root / "assumptions.csv"
        incomplete.to_csv(scenario_path, index=False)
        code, _, error = self.call("forecast", "--input", monthly_path, "--output", self.root / "scenario",
                                   "--model", "ridge", "--climate-columns", "temperature",
                                   "--scenario-csv", scenario_path, "--scenario-name", "synthetic_warm")
        self.assertEqual(code, 1)
        self.assertIn("Incomplete future climate", error)
        self.assertFalse((self.root / "scenario" / "forecast.csv").exists())

    def test_build_rejects_mixed_revisions_instead_of_quarantining_entire_history(self):
        first = self.fixture()
        second = first.copy()
        second["source_snapshot_sha256"] = "different_revision_sha"
        second["price"] += 1
        first.to_csv(self.inputs / "revision_a.csv", index=False)
        second.to_csv(self.inputs / "revision_b.csv", index=False)
        code, _, error = self.call("build", "--input", self.inputs, "--output", self.outputs)
        self.assertEqual(code, 1)
        self.assertTrue(error)
        self.assertFalse((self.outputs / "monthly.csv").exists())
        status = json.loads((self.outputs / "build_status.json").read_text())
        self.assertIn(status["status"], {"failed", "incomplete"})

    def test_failed_rebuild_prevents_forecasting_stale_curated_outputs(self):
        self.build_fixture()
        # The previous valid monthly artifact exists, but the replacement build fails.
        bad = self.fixture()
        bad["price"] = -1
        bad.to_csv(self.inputs / "fixture.csv", index=False)
        code, _, error = self.call("build", "--input", self.inputs, "--output", self.outputs)
        self.assertEqual(code, 1)
        self.assertTrue(error)
        status = json.loads((self.outputs / "build_status.json").read_text())
        self.assertIn(status["status"], {"failed", "incomplete"})
        for command in ("forecast", "backtest"):
            code, _, error = self.call(command, "--input", self.outputs / "monthly.csv",
                                       "--output", self.root / command)
            self.assertEqual(code, 1)
            self.assertTrue(error)
            self.assertFalse((self.root / command).exists())


if __name__ == "__main__":
    unittest.main()
