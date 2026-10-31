import io
import unittest

import pandas as pd

from materias_primas_chile.pinksheet import parse


def workbook(rows=None):
    rows = rows or [["World Bank Commodity Price Data"], ["monthly prices"], [""], ["Updated"],
                    [None, "Maize", "DAP **", "Wheat, US HRW"],
                    [None, "($/mt)", "($/mt)", "($/mt)"],
                    ["1960M01", 50.5, "…", 60.0],
                    ["1960M02", 51.0, 90.0, "…"]]
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name="Monthly Prices", header=False, index=False)
    return buffer.getvalue()


class PinkSheetTests(unittest.TestCase):
    def test_parses_wide_sheet_to_long_dropping_missing_markers(self):
        out = parse(workbook())
        self.assertEqual(len(out), 4)  # los dos "…" no son cero ni se rellenan
        self.assertEqual(list(out[out.commodity.eq("Maize")].price_usd), [50.5, 51.0])
        self.assertEqual(set(out.unit), {"$/mt"})
        self.assertIn("DAP", set(out.commodity))  # se limpian los asteriscos de nota
        self.assertEqual(out.date.min(), pd.Timestamp("1960-01-01"))

    def test_fails_when_format_changes(self):
        with self.assertRaises(ValueError):
            parse(workbook([["x"]] * 10))


if __name__ == "__main__":
    unittest.main()
