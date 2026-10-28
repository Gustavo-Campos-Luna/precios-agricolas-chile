import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from materias_primas_chile.prices import normalize_prices, read_csv, download_datastore


def record(**updates):
    row = {"Fecha": "31/01/2025", "ID region": "13", "Region": "Metropolitana",
           "Mercado": "Lo Valledor", "Producto": "Uva", "Variedad / Tipo": "Red globe",
           "Calidad": "Primera", "Unidad de comercializacion": "Caja 8 kilos",
           "Origen": "O'Higgins", "Precio promedio": "12.500,50"}
    row.update(updates)
    return row


class PricesTests(unittest.TestCase):
    def test_unit_origin_and_variety_define_series(self):
        data = normalize_prices(pd.DataFrame([record(), record(Origen="Maule"),
                    record(**{"Unidad de comercializacion": "Caja 10 kilos"})]))
        self.assertEqual(data.series_id.nunique(), 3)
        self.assertEqual(data.price.iloc[0], 12500.5)
        self.assertEqual(data.date.iloc[0], pd.Timestamp("2025-01-31"))
        self.assertEqual(data.unit.iloc[0], "Caja 8 kilos")

    def test_iso_dates_and_original_fields_preserved(self):
        data = normalize_prices(pd.DataFrame([record(Fecha="2025-12-03", Extra="valor")]))
        self.assertEqual(data.date.iloc[0], pd.Timestamp("2025-12-03"))
        self.assertIn('"Extra": "valor"', data.source_record.iloc[0])

    def test_schema_drift_fails(self):
        with self.assertRaises(ValueError):
            normalize_prices(pd.DataFrame([{"Fecha": "2025-01-01"}]))

    def test_latin1_semicolon_and_decimal_comma(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "datos.csv"
            path.write_bytes("Producto;Precio promedio\nMaíz;1,25\n".encode("latin-1"))
            data = read_csv(path)
            self.assertEqual(data.iloc[0, 0], "Maíz")
            self.assertEqual(data.iloc[0, 1], "1,25")

    def test_datastore_detects_changed_total(self):
        import json
        responses = [json.dumps({"success": True, "result": {"total": 2, "records": [{"x": 1}]}}).encode(),
                     json.dumps({"success": True, "result": {"total": 3, "records": [{"x": 2}]}}).encode()]
        with tempfile.TemporaryDirectory() as directory, patch("materias_primas_chile.prices.fetch", side_effect=responses):
            with self.assertRaises(ValueError):
                download_datastore({"id": "test"}, directory, page_size=1)


if __name__ == "__main__":
    unittest.main()
