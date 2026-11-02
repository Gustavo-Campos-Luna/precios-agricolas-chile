import unittest

import pandas as pd

from materias_primas_chile import fichas


def _sheet(drop: str | None = None) -> pd.DataFrame:
    rows = [
        ["Rendimiento (Kg/ha):", None, 8000, "Ingreso por hectárea (e)", None, None, 17600000],
        ["Precio de venta a productor ($/Kg): (1)", None, 2200, "Costos directos por hectárea (a+b+c)", None, None, 11086295.3],
        ["Costo jornada hombre ($/JH)", None, 15000, "Costos totales por hectárea (a+b+c+d)", None, None, 12036549.2],
        [None, None, None, "Margen neto por hectárea (e - (a+b+c+d))", None, None, 5563450.8],
        [None, None, None, "Costo unitario", None, None, 1504.57],
        ["Total mano de obra", None, None, None, None, None, 7122600],
        ["Total maquinaria", None, None, None, None, None, 1030000],
    ]
    frame = pd.DataFrame(rows)
    if drop:
        frame = frame[~frame[0].astype(str).str.contains(drop, regex=False)]
    return frame


class ParseTests(unittest.TestCase):
    def test_extracts_each_parameter_and_labor_share(self):
        f = fichas.parse_ficha(_sheet())
        self.assertEqual(f["yield_kg_ha"], 8000)
        self.assertEqual(f["producer_price_clp_kg"], 2200)
        self.assertAlmostEqual(f["total_cost_clp_ha"], 12036549.2)
        self.assertAlmostEqual(f["labor_share"], 7122600 / 12036549.2)

    def test_a_sheet_with_another_format_fails_instead_of_guessing(self):
        with self.assertRaises(ValueError):
            fichas.parse_ficha(_sheet(drop="Total mano de obra"))

    def test_accents_and_case_do_not_matter(self):
        sheet = _sheet()
        sheet.iloc[0, 3] = "INGRESO POR HECTÁREA (E)"
        self.assertEqual(fichas.parse_ficha(sheet)["revenue_clp_ha"], 17600000)


if __name__ == "__main__":
    unittest.main()
