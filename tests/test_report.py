import re
import sys
import unittest
from pathlib import Path

REPORT = Path(__file__).resolve().parents[1] / "report"
sys.path.insert(0, str(REPORT))

import referencias  # noqa: E402
import svgcharts as S  # noqa: E402


class AxisTests(unittest.TestCase):
    def test_ticks_always_cover_the_data_maximum(self):
        # Regresión: con máximo 7,6 las marcas terminaban en 5 y las barras se salían del gráfico.
        for hi in (7.6, 695.0, 2237.0, 0.93, 1.0, 100.0):
            ticks = S.nice_ticks(0, hi, 4)
            self.assertGreaterEqual(ticks[-1], hi, hi)
            self.assertLessEqual(ticks[0], 0)

    def test_ticks_are_evenly_spaced(self):
        ticks = S.nice_ticks(0, 695.0, 4)
        steps = {round(b - a, 6) for a, b in zip(ticks, ticks[1:])}
        self.assertEqual(len(steps), 1)


class ChartTests(unittest.TestCase):
    def test_line_is_broken_where_months_are_missing_instead_of_interpolated(self):
        x = [2024.0, 2024.083, 2024.167, 2024.25, 2025.0, 2025.083]  # faltan nueve meses entre 2024,25 y 2025
        svg, _ = S.line_chart([dict(name="S", color="var(--c-trigo)", x=x, y=[1, 2, 3, 4, 5, 6])], alt="t")
        path = re.search(r"<path d='([^']+)' fill='none'", svg).group(1)
        self.assertEqual(path.count("M"), 2)  # dos tramos: no se une lo que no se midió

    def test_bar_chart_skips_missing_values_and_keeps_alignment(self):
        svg, table = S.bar_chart([2000, 2001, 2002], [1.0, float("nan"), 3.0], color="var(--c-cereza)", label_every=1, alt="t")
        self.assertEqual(svg.count("<path"), 2)
        self.assertNotIn("2001", table)  # el año sin dato no aparece en la tabla

    def test_every_chart_exposes_an_accessible_description_and_a_data_table(self):
        svg, table = S.dumbbell([{"label": "A", "before": 10, "after": 5, "change": -0.5}], color="var(--c-cereza)", alt="Descripción")
        self.assertIn("role='img'", svg)
        self.assertIn("aria-label='Descripción'", svg)
        self.assertIn("<table", table)

    def test_diverging_bars_leave_room_for_the_largest_value_label(self):
        items = [{"label": "A", "value": -0.4, "color": "var(--c-cereza)"}, {"label": "B", "value": 0.62, "color": "var(--c-manzana)", "note": "x"}]
        svg, _ = S.diverging_bars(items, alt="t")
        self.assertIn("+62%", svg)
        self.assertIn("-40%", svg)


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        referencias.USED.clear()

    def test_citation_of_unknown_key_fails(self):
        with self.assertRaises(KeyError):
            referencias.cite("no_existe")

    def test_uncited_references_fail_the_build(self):
        referencias.cite("ovalle2026")
        with self.assertRaises(ValueError):
            referencias.reference_list()

    def test_parenthetical_citation_is_alphabetical_and_apa_shaped(self):
        self.assertEqual(referencias.cite("rabo2026", "aguirre2025"), "(Aguirre, 2025; RaboResearch, 2026)")
        self.assertEqual(referencias.narrative("ovalle2026"), "Ovalle (2026)")

    def test_same_author_year_suffixes_are_consecutive_letters(self):
        for author_prefix in ("ODEPA, 2026", "FAO, 2026"):
            letters = sorted(r["short"][-1] for r in referencias.REFS if r["short"].startswith(author_prefix))
            self.assertEqual(letters, [chr(ord("a") + i) for i in range(len(letters))], author_prefix)

    def test_every_reference_has_a_retrieval_date_or_a_publication_date(self):
        for r in referencias.REFS:
            self.assertTrue("Recuperado el" in r["html"] or re.search(r"\(\d{4}", r["html"]), r["key"])


class BuiltReportTests(unittest.TestCase):
    html_path = REPORT / "dist" / "informe_precios_agricolas_chile.html"

    @unittest.skipUnless(html_path.exists(), "el informe no está construido")
    def test_report_has_no_long_dashes_and_numbers_figures_in_order(self):
        html = self.html_path.read_text(encoding="utf-8")
        text = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
        self.assertNotIn("—", text)
        self.assertNotIn("–", text)
        numbers = [int(n) for n in re.findall(r"<p class='fig-n'>Figura (\d+)</p>", html)]
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertNotIn("@@", html)  # ningún marcador sin resolver

    @unittest.skipUnless(html_path.exists(), "el informe no está construido")
    def test_report_is_self_contained(self):
        html = self.html_path.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"<(script|link)[^>]+(src|href)=['\"]https?://", html))  # sin recursos externos
        self.assertIn("lang='es'", html)


class ExtraChartTests(unittest.TestCase):
    def test_waterfall_levels_multiply_and_close_on_the_total(self):
        import svgextra as SX
        steps = [dict(label="A", factor=1.9), dict(label="B", factor=1.3), dict(label="C", factor=0.7)]
        svg, table = SX.waterfall(steps, alt="t")
        total = 100 * 1.9 * 1.3 * 0.7
        self.assertIn(f">{total:.0f}<", svg)  # la barra final es el producto de los factores
        self.assertIn(f"{total:.0f}", table)
        self.assertIn("role='img'", svg)

    def test_scatter_draws_every_point_and_a_dashed_fit_line(self):
        import svgextra as SX
        pts = [{"x": v / 10, "y": -v / 12, "label": str(2000 + v)} for v in range(8)]
        svg, table = SX.scatter(pts, color="var(--c-manzana)", x_title="x", y_title="y", alt="t")
        self.assertEqual(svg.count("<circle"), 8)
        self.assertIn("stroke-dasharray", svg)
        self.assertEqual(table.count("<tr>"), 9)  # cabecera + 8 filas

    def test_sparkline_breaks_the_line_at_missing_values(self):
        import svgextra as SX
        svg = SX.sparkline([1, 2, float("nan"), float("nan"), 3, 4], color="var(--c-cereza)")
        self.assertEqual(svg.count("M"), 2)


class FormatTests(unittest.TestCase):
    def test_chilean_number_format_and_real_minus_sign(self):
        import helpers
        self.assertEqual(helpers.es(1234567.8, 1), "1.234.567,8")
        self.assertEqual(helpers.es(-0.59, 2), "−0,59")
        self.assertEqual(helpers.sg(0.62), "+62%")
        self.assertEqual(helpers.sg(-0.388, 1), "−38,8%")

    def test_figure_numbers_follow_document_order_and_reject_dangling_references(self):
        import helpers
        html, n = helpers.number_figures("<b>@@N:b@@</b> ver @@R:a@@ <b>@@N:a@@</b>")
        self.assertEqual((html, n), ("<b>1</b> ver 2 <b>2</b>", 2))
        with self.assertRaises(ValueError):
            helpers.number_figures("@@R:nada@@")
        with self.assertRaises(ValueError):
            helpers.number_figures("@@N:a@@ @@N:a@@")


class StyleGuardTests(unittest.TestCase):
    def test_banned_phrases_are_detected(self):
        import build_report
        with self.assertRaises(ValueError):
            build_report.check_text("<p>Cabe destacar que el precio bajó.</p>")
        with self.assertRaises(ValueError):
            build_report.check_text("<p>Subió — y mucho.</p>")
        build_report.check_text("<p>El precio bajó 39%.</p>")  # texto limpio: no falla

    def test_reference_keys_are_unique_and_sort_keys_are_ascii_lowercase(self):
        keys = [r["key"] for r in referencias.REFS]
        self.assertEqual(len(keys), len(set(keys)))
        for r in referencias.REFS:
            self.assertEqual(r["sort"], r["sort"].lower(), r["key"])
            self.assertTrue(r["sort"].isascii(), r["key"])

    @unittest.skipUnless(BuiltReportTests.html_path.exists(), "el informe no está construido")
    def test_built_report_embeds_fonts_and_every_figure_has_a_data_table(self):
        html = BuiltReportTests.html_path.read_text(encoding="utf-8")
        self.assertIn("@font-face", html)
        self.assertIn("font/woff2;base64", html)
        self.assertNotIn("{{FONTS}}", html)
        self.assertEqual(html.count("<figure "), html.count("<details class='tabla'>"))


class BridgeTests(unittest.TestCase):
    @unittest.skipUnless((REPORT.parent / "data/analysis/external_prices_monthly.parquet").exists(), "sin datos analíticos")
    def test_bridge_closes_the_total_and_the_residual_premium_matches_the_direct_estimate(self):
        import drivers
        for grain in ("Trigo", "Maíz"):
            b = drivers.bridge(grain)
            self.assertAlmostEqual(b["usd"] * b["fx"] / b["cpi"] * b["premium"], b["total"], places=9, msg=grain)
            self.assertLess(abs(b["premium"] / b["premium_direct"] - 1), 0.08, grain)  # el residuo no esconde un error de cálculo


if __name__ == "__main__":
    unittest.main()
