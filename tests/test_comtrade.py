import json
import tempfile
import unittest
from pathlib import Path

import httpx
import pandas as pd

from materias_primas_chile import comtrade as ct

PAYLOAD = {"count": 2, "data": [
    {"refYear": 2024, "period": "2024", "reporterCode": 156, "flowCode": "M", "partnerCode": 152, "cmdCode": "080929", "netWgt": 438978878.0, "qty": 438978878.0, "primaryValue": 3575618941.0, "cifvalue": 3575618941.0, "fobvalue": None},
    {"refYear": 2024, "period": "2024", "reporterCode": 156, "flowCode": "M", "partnerCode": 604, "cmdCode": "080929", "netWgt": 0.0, "qty": 0.0, "primaryValue": 1000.0, "cifvalue": 1000.0, "fobvalue": None},
]}


class ParseTests(unittest.TestCase):
    def test_parse_keeps_fixed_columns_and_empty_payload_gives_empty_frame(self):
        frame = ct.parse_payload(PAYLOAD)
        self.assertEqual(list(frame.columns), ct.COLUMNS)
        self.assertEqual(len(frame), 2)
        empty = ct.parse_payload({"count": 0, "data": []})
        self.assertEqual(list(empty.columns), ct.COLUMNS)
        self.assertTrue(empty.empty)

    def test_kilos_never_invents_weight_when_it_is_not_declared(self):
        kg = ct.kilos(ct.parse_payload(PAYLOAD))
        self.assertEqual(kg.iloc[0], 438978878.0)
        self.assertTrue(pd.isna(kg.iloc[1]))  # peso 0 = no declarado

    def test_build_url_keeps_parameters(self):
        url = ct.build_url("A", {"reporterCode": 156, "period": 2024, "cmdCode": "080929", "flowCode": "M"})
        self.assertTrue(url.startswith("https://comtradeapi.un.org/public/v1/preview/C/A/HS?"))
        self.assertIn("cmdCode=080929", url)


class ClientTests(unittest.TestCase):
    def test_retries_on_429_then_saves_original_with_manifest(self):
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(429, json={"statusCode": 429})
            return httpx.Response(200, content=json.dumps(PAYLOAD).encode())

        with tempfile.TemporaryDirectory() as tmp:
            client = ct.Client(Path(tmp), pause=0, client=httpx.Client(transport=httpx.MockTransport(handler)))
            frame = client.fetch("prueba", "A", {"reporterCode": 156})
            self.assertEqual(len(frame), 2)
            self.assertEqual(calls["n"], 2)
            manifest = json.loads((Path(tmp) / "prueba.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["rows"], 2)
            self.assertEqual(len(manifest["sha256"]), 64)
            self.assertTrue((Path(tmp) / "prueba.json").exists())

    def test_waits_for_the_quota_message_and_retries(self):
        self.assertEqual(ct.quota_wait_seconds("Out of call volume quota. Quota will be replenished in 00:17:17."), 17 * 60 + 17)
        self.assertEqual(ct.quota_wait_seconds("sin tiempo"), 0.0)
        calls = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(403, text="Out of call volume quota. Quota will be replenished in 00:00:00.")
            return httpx.Response(200, content=json.dumps(PAYLOAD).encode())

        with tempfile.TemporaryDirectory() as tmp:
            client = ct.Client(Path(tmp), pause=0, quota_margin=0, client=httpx.Client(transport=httpx.MockTransport(handler)))
            self.assertEqual(len(client.fetch("q", "A", {})), 2)
            self.assertEqual(calls["n"], 2)

    def test_gives_up_after_repeated_429(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={})

        with tempfile.TemporaryDirectory() as tmp:
            client = ct.Client(Path(tmp), pause=0, retries=2, client=httpx.Client(transport=httpx.MockTransport(handler)))
            with self.assertRaises(RuntimeError):
                client.fetch("x", "A", {})


if __name__ == "__main__":
    unittest.main()
