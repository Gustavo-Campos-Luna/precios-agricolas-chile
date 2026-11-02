"""Fichas técnico-económicas de ODEPA (costos de producción por hectárea).

Cada ficha es una planilla ``.xls`` con un huerto tipo: rendimiento, precio de venta a productor, costo de la jornada y los
costos por grupo (mano de obra, maquinaria, insumos). Aquí se extraen solo los parámetros que el informe usa; los valores
están en pesos de la fecha de la ficha (para la ficha 2016-17, junio de 2017) y describen un huerto tipo, no un promedio.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

URL = "https://www.odepa.gob.cl/fichas_de_costo/fichas_xls/{name}.xls"
# etiqueta (expresión regular sin tildes ni mayúsculas) -> nombre del parámetro
LABELS = {
    "yield_kg_ha": r"^rendimiento \(kg/ha\)",
    "producer_price_clp_kg": r"^precio de venta a productor",
    "day_labor_clp": r"^costo jornada hombre",
    "revenue_clp_ha": r"^ingreso por hectarea",
    "direct_cost_clp_ha": r"^costos directos por hectarea",
    "total_cost_clp_ha": r"^costos totales por hectarea",
    "unit_cost_clp_kg": r"^costo unitario",
    "labor_clp_ha": r"^total mano de obra",
    "machinery_clp_ha": r"^total maquinaria",
    "net_margin_clp_ha": r"^margen neto por hectarea",
}


def _plain(text: object) -> str:
    table = str.maketrans("áéíóúüñ", "aeiouun")
    return re.sub(r"\s+", " ", str(text).lower().translate(table)).strip()


def parse_ficha(sheet: pd.DataFrame) -> dict[str, float]:
    """Busca cada etiqueta en la hoja y toma el primer número que la sigue en su fila.

    Falla con ``ValueError`` si falta algún parámetro: una ficha con otro formato no se interpreta a medias.
    """
    found: dict[str, float] = {}
    for _, row in sheet.iterrows():
        cells = list(row)
        for i, cell in enumerate(cells):
            if not isinstance(cell, str):
                continue
            text = _plain(cell)
            for key, pattern in LABELS.items():
                if key in found or not re.search(pattern, text):
                    continue
                numbers = [pd.to_numeric(c, errors="coerce") for c in cells[i + 1:]]
                numbers = [float(n) for n in numbers if pd.notna(n)]
                if numbers:
                    found[key] = numbers[0]
    missing = sorted(set(LABELS) - set(found))
    if missing:
        raise ValueError(f"La ficha no tiene los parámetros esperados: {missing}")
    found["labor_share"] = found["labor_clp_ha"] / found["total_cost_clp_ha"]
    return found


def read_ficha(path: Path, sheet: str | int = 0) -> dict[str, float]:
    return parse_ficha(pd.read_excel(path, sheet_name=sheet, header=None))
