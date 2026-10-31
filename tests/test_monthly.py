"""Monthly transport contracts use synthetic responses, never fabricated history."""
import importlib.util
from email.message import Message
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from materias_primas_chile.monthly import fetch_monthly_query


def form():
    return {"periodoInicio": "2020-01-01T00:00:00.000Z", "periodoTermino": "2021-12-01T00:00:00.000Z",
            "tipoConsulta": "nominal", "idIPC": None, "tipoMercado": 7, "tipoSalida": "SA",
            "precioConIva": False, "subSector": "synthetic_group", "producto": "synthetic_product"}


class MonthlyTests(unittest.TestCase):
    def test_original_json_query_and_requested_tax_flag_are_preserved(self):
        # Deliberately no price-shaped records: this test covers raw transport.
        payload = b'{"synthetic_fixture":"not observed prices"}'
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload
        with tempfile.TemporaryDirectory() as directory, patch(
            "materias_primas_chile.monthly.urlopen", return_value=response
        ) as mocked:
            path = fetch_monthly_query(form(), directory)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(json.loads((path.parent / "query.json").read_text()), form())
            manifest = json.loads(path.with_suffix(".json.manifest.json").read_text())
            self.assertFalse(manifest["requested_tax_flag"])
            self.assertNotIn("price_with_tax", manifest)
            self.assertEqual(manifest["status"], "raw_response_requires_schema_validation")
            request = mocked.call_args.args[0]
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(json.loads(request.data), form())

    def test_contract_rejects_identity_fields_and_unimplemented_price_bases(self):
        cases = [dict(form(), ip="synthetic_identity"), dict(form(), tipoConsulta="real"),
                 dict(form(), tipoSalida="TI"), dict(form(), precioConIva="false"),
                 dict(form(), producto=None)]
        with tempfile.TemporaryDirectory() as directory, patch("materias_primas_chile.monthly.urlopen") as mocked:
            for query in cases:
                with self.subTest(query=query), self.assertRaises(ValueError):
                    fetch_monthly_query(query, directory)
            mocked.assert_not_called()

    def test_html_or_empty_response_cannot_be_promoted_to_json_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            for payload in (b"<html>not a price API</html>", b"{}", b"[]"):
                response = MagicMock()
                response.__enter__.return_value.read.return_value = payload
                with self.subTest(payload=payload), patch(
                    "materias_primas_chile.monthly.urlopen", return_value=response
                ), self.assertRaises(ValueError):
                    fetch_monthly_query(form(), directory)
            originals = list(Path(directory).rglob("*.response.bin"))
            self.assertEqual(len(originals), 3)
            self.assertTrue(all("failures" in path.parts for path in originals))
            self.assertTrue(any("not a price API" in path.read_text()
                                for path in Path(directory).rglob("*.preview.txt")))

    def test_declared_latin1_is_decoded_without_losing_original_bytes(self):
        payload = '{"product":"Maíz, fixture sin precios"}'.encode("latin-1")
        response = MagicMock()
        entered = response.__enter__.return_value
        entered.read.return_value = payload
        entered.headers = Message()
        entered.headers["Content-Type"] = "application/json; charset=ISO-8859-1"
        entered.geturl.return_value = "https://example.test/public-monthly-response"
        entered.getcode.return_value = 200
        with tempfile.TemporaryDirectory() as directory, patch(
            "materias_primas_chile.monthly.urlopen", return_value=response
        ):
            path = fetch_monthly_query(form(), directory)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["product"], "Maíz, fixture sin precios")
            manifest = json.loads(path.with_suffix(".json.manifest.json").read_text())
            self.assertEqual(manifest["declared_charset"], "iso-8859-1")
            self.assertEqual(manifest["http_status"], 200)
            self.assertEqual(Path(manifest["original_response_path"]).read_bytes(), payload)

    def test_gzip_is_decoded_only_when_declared_and_original_is_preserved(self):
        text = '{"fixture":"gzip raw transport only"}'
        payload = gzip.compress(text.encode())
        response = MagicMock()
        entered = response.__enter__.return_value
        entered.read.return_value = payload
        entered.headers = Message()
        entered.headers["Content-Type"] = "application/json; charset=utf-8"
        entered.headers["Content-Encoding"] = "gzip"
        with tempfile.TemporaryDirectory() as directory, patch(
            "materias_primas_chile.monthly.urlopen", return_value=response
        ):
            path = fetch_monthly_query(form(), directory)
            self.assertEqual(path.read_text(), text)
            manifest = json.loads(path.with_suffix(".json.manifest.json").read_text())
            self.assertEqual(Path(manifest["original_response_path"]).read_bytes(), payload)
            self.assertEqual(manifest["content_encoding"], "gzip")

    def test_collection_requires_metadata_match_and_uses_global_dates_only_as_request(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "collect_monthly_sample.py"
        spec = importlib.util.spec_from_file_location("collect_monthly_sample", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        target = {"name": "synthetic", "market_id": 7, "group_id": 12,
                  "product_id": 370, "expected_label": "Synthetic product"}
        probe = {"requests": [{"url": "https://example.test/min-max-date-precio",
                               "response": {"fechaInicio": "01/01/1975", "fechaTermino": "01/09/2026"}}],
                 "matches": [{"type": "target_product", "market_id": 7, "group_id": 12,
                              "record": {"id": 370, "glosaFull": "Synthetic product per original unit"}}]}
        self.assertEqual(module.source_dates(probe), ("1975-01-01T12:00:00.000Z", "2026-09-01T12:00:00.000Z"))
        self.assertEqual(module.verified_target(probe, target)["record"]["id"], 370)
        probe["matches"][0]["record"]["id"] = 999
        with self.assertRaises(ValueError):
            module.verified_target(probe, target)

    def test_ipc_form_identifier_is_read_from_observed_valor_not_guessed_id(self):
        path = Path(__file__).resolve().parents[1] / "scripts" / "collect_monthly_sample.py"
        spec = importlib.util.spec_from_file_location("collect_monthly_ipc", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        probe = {"requests": [{"url": "https://example.test/ipc", "response": [
            {"id": 999, "valor": "2023", "glosa": "Synthetic IPC metadata"},
            {"id": 1000, "valor": "2024", "glosa": "Synthetic IPC metadata"}]}]}
        selected = module.source_ipc(probe)
        self.assertEqual(selected["idIPC"], 2024)
        self.assertEqual(selected["observed_record"]["id"], 1000)
        probe["requests"][0]["response"] = [{"id": 2025}]
        with self.assertRaises(ValueError):
            module.source_ipc(probe)


if __name__ == "__main__":
    unittest.main()
