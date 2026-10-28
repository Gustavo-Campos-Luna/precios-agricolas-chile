import unittest
from materias_primas_chile.grains import parse_report_text

# Extracto de diseño reducido; fixture de parser, no dataset histórico.
TEXT = """Informe Semanal
Semana N° 22
Cuadro 1. Precio promedio ($/quintal)
Región 2024 2025 Variación
Metropolitana 23.300
O´Higgins    21.800    22.500   3,2%
Maule        21.560    22.000   2,0%
Ñuble        21.000    23.000   9,5%
Biobío       21.400    22.850   6,8%
Total nacional 21.707 22.617 4,2%
Cuadro 2. Costo Alternativo de Importación
Maule 99.000 99.000 0,0%
"""


class GrainTests(unittest.TestCase):
    def parse(self, text=TEXT, **kwargs):
        return parse_report_text(text, period_start=kwargs.get("period_start", "2025-05-26"),
                                 report_url="https://www.odepa.gob.cl/report.pdf", available_at="2025-06-03")

    def test_2025_values_and_single_value_rejected(self):
        data, rejects = self.parse()
        self.assertEqual(len(data), 5)
        self.assertEqual(len(rejects), 1)
        self.assertEqual(data.loc[data.market_region_code == "CL", "price"].iloc[0], 22617)
        self.assertEqual(data["product"].unique().tolist(), ["Maíz grano"])
        self.assertEqual(data.unit.unique().tolist(), ["quintal"])

    def test_year_and_week_mismatch_fail(self):
        with self.assertRaises(ValueError):
            self.parse(period_start="2025-05-19")
        with self.assertRaises(ValueError):
            self.parse(TEXT.replace("2024 2025", "2023 2024"))

    def test_duplicate_region_fails(self):
        with self.assertRaises(ValueError):
            self.parse(TEXT.replace("Cuadro 2", "Maule 21.560 22.000 2,0%\nCuadro 2"))
