import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from materias_primas_chile.bcch import BcchClient, load_credentials, parse_series

INFO = {"seriesId": "F076.IPM.PRE.M2101001.199206.I.M", "spanishTitle": "IPM Precio TRIGO", "frequency": "MONTHLY"}


class BcchTests(unittest.TestCase):
    def test_credentials_come_from_env_file_and_missing_ones_fail(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {}, clear=True):
            env = Path(directory) / ".env"
            self.assertRaises(ValueError, load_credentials, env)
            env.write_text("BCCH_USER=usuario@example.test\nBCCH_PASSWORD=a=b$c\n", encoding="utf-8")
            self.assertEqual(load_credentials(env), ("usuario@example.test", "a=b$c"))

    def test_selection_keeps_agricultural_families_and_drops_national_accounts(self):
        catalog = pd.DataFrame({
            "seriesId": ["F076.IPM.PRE.M2101001.199206.I.M", "F035.PIB.AGR.Z.2018.C.T", "F068.U23.INP.B11.0.C.Z.Z.Z.Z.Z.18.0.T",
                         "F076.IPM.IND.9999.200711.Z.M"],
            "spanishTitle": ["IPM Precio TRIGO", "PIB agropecuario-silvícola", "Índice de precios Exportaciones uva", "Cobre"],
        })
        selected = BcchClient.select_agricultural(catalog)
        self.assertEqual(list(selected.seriesId),
                         ["F076.IPM.PRE.M2101001.199206.I.M", "F068.U23.INP.B11.0.C.Z.Z.Z.Z.Z.18.0.T"])

    def test_parse_drops_missing_values_and_never_fills_zero(self):
        document = {"Codigo": 0, "Series": {"Obs": [
            {"indexDateString": "01-06-1992", "value": "100.5", "statusCode": "OK"},
            {"indexDateString": "01-07-1992", "value": "", "statusCode": "ND"},
            {"indexDateString": "01-08-1992", "value": "101.25", "statusCode": "OK"}]}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "series.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            frame = parse_series(path, INFO)
        self.assertEqual(list(frame.value), [100.5, 101.25])
        self.assertEqual(list(frame.date.dt.strftime("%Y-%m")), ["1992-06", "1992-08"])
        self.assertEqual(set(frame.series_id), {INFO["seriesId"]})



class MacroTests(unittest.TestCase):
    def test_cpi_chain_is_base_100_at_last_month_and_deflates_correctly(self):
        from materias_primas_chile.bcch import chain_cpi
        monthly = pd.DataFrame({"date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-03-01"]), "value": [1.0, 2.0, 0.5]})
        cpi = chain_cpi(monthly).set_index("date")
        self.assertAlmostEqual(cpi.loc["2025-03-01", "cpi_index"], 100.0)
        # febrero→marzo +0,5%: lo que en marzo vale 100 en febrero valía 100/1,005
        self.assertAlmostEqual(cpi.loc["2025-02-01", "cpi_index"], 100 / 1.005, places=6)
        self.assertAlmostEqual(cpi.loc["2025-01-01", "cpi_index"], 100 / 1.005 / 1.02, places=6)

    def test_cpi_chain_refuses_missing_months(self):
        from materias_primas_chile.bcch import chain_cpi
        monthly = pd.DataFrame({"date": pd.to_datetime(["2025-01-01", "2025-03-01"]), "value": [1.0, 1.0]})
        with self.assertRaises(ValueError):
            chain_cpi(monthly)

    def test_usd_monthly_mean_counts_days(self):
        from materias_primas_chile.bcch import monthly_mean
        daily = pd.DataFrame({"date": pd.to_datetime(["2025-01-02", "2025-01-03", "2025-02-03"]), "value": [900.0, 910.0, 950.0]})
        out = monthly_mean(daily).set_index("date")
        self.assertEqual((out.loc["2025-01-01", "usd_clp"], out.loc["2025-01-01", "n_days"]), (905.0, 2))

    def test_splice_rescales_old_base_on_overlap_and_ends_at_100(self):
        from materias_primas_chile.bcch import splice_cpi
        new = pd.DataFrame({"date": pd.date_range("2023-01-01", periods=4, freq="MS"), "value": [100.0, 101.0, 102.0, 103.0]})
        old = pd.DataFrame({"date": pd.date_range("2022-10-01", periods=6, freq="MS"),
                            "value": [48.0, 49.0, 49.5, 50.0, 50.5, 51.0]})  # base distinta: ×2 en el traslape (ene 50→100)
        out = splice_cpi([new, old]).set_index("date")["cpi_index"]
        self.assertEqual(len(out), 7)  # oct-22..abr-23 sin huecos
        self.assertAlmostEqual(out.iloc[-1], 100.0)
        self.assertAlmostEqual(out.loc["2022-12-01"] / out.loc["2023-04-01"], (99.0 / 103.0), places=6)  # 49,5*2 sobre 103

    def test_splice_refuses_bases_without_overlap(self):
        from materias_primas_chile.bcch import splice_cpi
        new = pd.DataFrame({"date": pd.date_range("2023-01-01", periods=4, freq="MS"), "value": [100.0, 101.0, 102.0, 103.0]})
        old = pd.DataFrame({"date": pd.date_range("2020-01-01", periods=4, freq="MS"), "value": [90.0, 91.0, 92.0, 93.0]})
        with self.assertRaises(ValueError):
            splice_cpi([new, old])


if __name__ == "__main__":
    unittest.main()
