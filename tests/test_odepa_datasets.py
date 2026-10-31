import unittest

import pandas as pd

from materias_primas_chile.odepa_datasets import normalize


def frame(columns, rows):
    return pd.DataFrame(rows, columns=columns, dtype=str)


class OdepaDatasetTests(unittest.TestCase):
    def test_consumer_keeps_unit_and_splits_legacy_compound_product(self):
        data = frame(["Anio", "Mes", "Semana", "Fecha inicio", "Fecha termino", "ID region", "Region", "Sector",
                      "Tipo de punto monitoreo", "Grupo", "Producto", "Unidad", "Precio minimo", "Precio maximo",
                      "Precio promedio"],
                     [["2008", "9", "36", "01/09/2008", "05/09/2008", "13", "Metropolitana", "Urbano", "Feria libre",
                       "Frutas", "Limón|Sin especificar|1a plateado", "$/kilo", "", "", "1190,500000"]])
        out = normalize("consumidor", data).iloc[0]
        self.assertEqual((out["product"], out.unit, out.price), ("Limón", "$/kilo", 1190.5))
        self.assertTrue(pd.isna(out.price_min))  # vacío = faltante, no cero
        self.assertEqual(out.date, pd.Timestamp("2008-09-01"))
        self.assertEqual((out.currency, out.price_kind), ("CLP", "published"))

    def test_wine_grape_declares_missing_unit_instead_of_assuming_kg(self):
        data = frame(["Anio", "Mes", "Fecha precio vigente", "ID region", "Region", "Comuna", "Poder comprador",
                      "Sucursal", "Variedad", "Precio", "Grado brix", "Fecha proximo precio", "Proximo precio",
                      "Observaciones"],
                     [["2026", "3", "2026-03-10", "7", "Maule", "Curicó", "Viña X", "Matriz", "Cabernet Sauvignon",
                       "350,000000", "22,5", "", "", ""]])
        out = normalize("uva_vinificacion", data).iloc[0]
        self.assertEqual((out.price, out.brix, out.unit), (350.0, 22.5, "no_declarada"))
        self.assertTrue(pd.isna(out.next_price))

    def test_export_unit_value_is_derived_only_for_kilo_rows(self):
        data = frame(["Anio", "Mes", "Codigo producto (SA)", "Producto", "ID region", "Region origen", "Pais destino",
                      "Unidad", "Volumen", "USD FOB"],
                     [["2025", "12", "08092900", "Cerezas", "13", "Metropolitana", "China", "Kilo neto", "1000,0", "7500,0"],
                      ["2025", "12", "22042100", "Vino", "7", "Maule", "Brasil", "Litro", "500,0", "900,0"],
                      ["2025", "12", "08092900", "Cerezas", "13", "Metropolitana", "Peru", "Kilo neto", "0", "10,0"]])
        out = normalize("comex_exportacion", data)
        self.assertEqual(out.unit_value_usd_per_kg.iloc[0], 7.5)
        self.assertTrue(out.unit_value_usd_per_kg.iloc[1:].isna().all())  # litro y volumen cero: sin valor inventado
        self.assertTrue(out.price_kind.eq("derived_unit_value").all())
        self.assertEqual(out.date.iloc[0], pd.Timestamp("2025-12-01"))


if __name__ == "__main__":
    unittest.main()
