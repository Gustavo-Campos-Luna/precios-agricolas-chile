import json
import tempfile
import unittest
from pathlib import Path

from materias_primas_chile.odepa_series import OdepaSeriesClient, parse_series

INTERNATIONAL = dict(market_type_id=5, market_type="Precios internacionales", subsector_id=1, subsector="Cereales",
                     product_id=312, product="Maíz Yellow N° 2, FOB Golfo, USA | US$/tonelada")
RETAIL = dict(market_type_id=3, market_type="Precios a consumidor Supermercado", subsector_id=20,
              subsector="Abarrotes y otros", product_id=61, product="Arroz grano ancho grado 1 $/kilo")


def write_response(directory, rows):
    path = Path(directory) / "response.json"
    path.write_text(json.dumps({"resultSeriesTiempo": rows, "headerColumn": [], "fuente": "Fuente: ODEPA"}),
                    encoding="utf-8")
    return path


class OdepaSeriesTests(unittest.TestCase):
    def client(self, directory):
        client = OdepaSeriesClient(directory, pace=0)
        client._ip, client._ipc = "203.0.113.7", "6737"
        client._window = {"fechaInicio": "01/01/1975", "fechaTermino": "01/09/2026"}
        self.addCleanup(client.close)
        return client

    def test_form_replicates_official_contract_with_audit_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            form = self.client(directory)._form(INTERNATIONAL)
        self.assertEqual(form["ip"], "203.0.113.7")
        audit = json.loads(form["jsonParam"])["Parametros"]
        self.assertEqual(audit["IP"], "203.0.113.7")
        self.assertEqual(audit["Producto"], INTERNATIONAL["product"])
        self.assertEqual(audit["Fecha desde"], "01/1975")
        self.assertEqual(audit["Fecha hasta"], "09/2026")
        self.assertEqual((form["tipoMercado"], form["subSector"], form["producto"]), (5, 1, 312))
        self.assertEqual((form["tipoConsulta"], form["tipoSalida"], form["idIPC"]), ("nominal", "SA", 6737))
        self.assertIs(form["precioConIva"], False)

    def test_parse_keeps_gaps_as_missing_instead_of_zero(self):
        rows = [[2025, 10.0, 11.0, None, None, None, None, None, None, None, None, None, None, 10.5],
                [2026, None, 12.5] + [None] * 10 + [12.5]]
        with tempfile.TemporaryDirectory() as directory:
            frame = parse_series(write_response(directory, rows), INTERNATIONAL)
        self.assertEqual(list(frame.date.dt.strftime("%Y-%m")), ["2025-01", "2025-02", "2026-02"])
        self.assertEqual(list(frame.price), [10.0, 11.0, 12.5])
        self.assertTrue(frame.price.gt(0).all())

    def test_parse_separates_currency_unit_and_vat_basis(self):
        rows = [[2025, 1.0] + [None] * 11 + [1.0]]
        with tempfile.TemporaryDirectory() as directory:
            path = write_response(directory, rows)
            international = parse_series(path, INTERNATIONAL).iloc[0]
            retail = parse_series(path, RETAIL).iloc[0]
        self.assertEqual((international.unit, international.currency, international.vat_basis),
                         ("US$/tonelada", "USD", "no_aplica"))
        self.assertEqual((retail.unit, retail.currency, retail.vat_basis), ("$/kilo", "CLP", "con_iva"))
        self.assertEqual(len(international.source_sha256), 64)


if __name__ == "__main__":
    unittest.main()
