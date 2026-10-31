import unittest

from materias_primas_chile.cotrisa import parse_price, parse_tables

HTML = """
<table>
<tr><th>Región</th><th>Comprador</th><th>Localidad</th><th>Precio ($/qqm) 17/03/2025</th>
    <th>Precio ($/qqm) 18/03/2025</th><th>Observaciones</th></tr>
<tr><td rowspan="2">Región de O'Higgins</td><td>Agrosuper</td><td>Lo Miranda</td><td>24000</td><td>23.000</td><td>Sin información</td></tr>
<tr><td>Copeval</td><td>Nancagua</td><td>Sin información</td><td>22500</td><td></td></tr>
</table>
<table>
<tr><th>Región</th><th>Comprador</th><th>Localidad</th><th>Precio ($/qqm) 17-03-2025</th><th>Observaciones</th></tr>
<tr><td>Región del Maule</td><td>Molino</td><td>Linares</td><td>21000</td><td></td></tr>
</table>
<table><tr><td>Otra tabla sin precios</td></tr></table>
"""


class CotrisaTests(unittest.TestCase):
    def test_price_parser_handles_thousands_separator_and_missing_markers(self):
        self.assertEqual(parse_price("24000"), 24000.0)
        self.assertEqual(parse_price("23.000"), 23000.0)
        self.assertEqual(parse_price("$ 22.600"), 22600.0)
        for missing in ("Sin información", "", "-", "0"):
            self.assertIsNone(parse_price(missing))

    def test_tables_expand_rowspan_and_split_daily_from_weekly(self):
        frame = parse_tables(HTML, "Maíz")
        daily = frame[frame.frequency.eq("daily")]
        weekly = frame[frame.frequency.eq("weekly")]
        self.assertEqual(len(daily), 3)  # 2 precios de Agrosuper + 1 de Copeval; "Sin información" omitido
        self.assertEqual(len(weekly), 1)
        copeval = daily[daily.buyer.eq("Copeval")].iloc[0]
        self.assertEqual(copeval.region, "Región de O'Higgins")  # heredada por rowspan
        self.assertEqual((copeval.price, copeval.unit, copeval.currency), (22500.0, "$/qqm", "CLP"))
        self.assertEqual(str(copeval.date.date()), "2025-03-18")
        self.assertTrue(frame.price.gt(0).all())

    def test_page_without_price_tables_returns_empty_frame(self):
        self.assertTrue(parse_tables("<table><tr><td>nada</td></tr></table>", "Trigo").empty)


if __name__ == "__main__":
    unittest.main()
