"""Maíz grano productor: informes semanales oficiales ODEPA/Cotrisa.

Conector acotado al Cuadro 1 de informes comparativos 2024/2025. Falla si
el diseño deja de ser reconocible; nunca interpreta un precio aislado como
precio del año actual. No mezclar estos datos con choclo mayorista.
"""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import pandas as pd

from .prices import fetch
from .storage import atomic_write, receipt

REPORT_2025_WEEK22 = "https://www.odepa.gob.cl/wp-content/uploads/2025/05/Informe-semana-del-26-de-mayo-al-01-de-junio-2025.pdf"
REGIONS = {"Metropolitana": "13", "O´Higgins": "06", "O'Higgins": "06",
           "O’Higgins": "06", "Maule": "07", "Ñuble": "16", "Biobío": "08",
           "Total nacional": "CL"}


def parse_report_text(text: str, *, period_start: str, report_url: str,
                      available_at: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Extrae precios actuales de filas con ambos años y variación explícita.

    `period_start` debe corresponder al lunes del período que identifica el
    informe; `available_at` es la fecha de consulta/publicación declarada por
    la fuente, posterior a la semana observada, necesaria para backtests.
    Retorna (datos, filas regionales ambiguas para revisión).
    """
    start = pd.Timestamp(period_start)
    available = pd.Timestamp(available_at)
    if start.weekday() != 0 or available < start + pd.Timedelta(days=6):
        raise ValueError("Fecha semanal/disponibilidad no válida")
    if "Cuadro 1" not in text or not re.search(r"quintal", text, re.I):
        raise ValueError("No se reconoce Cuadro 1 con unidad quintal")
    if not re.search(r"2024\s+2025", text):
        raise ValueError("Parser soporta únicamente comparación 2024/2025")
    if start.year != 2025:
        raise ValueError("El período actual del informe debe pertenecer a 2025")
    week = re.search(r"Semana\s+N[°ºo]?\s*(\d+)", text)
    if week is None or int(week.group(1)) != start.isocalendar().week:
        raise ValueError("La semana del informe no coincide con period_start")
    # Recortar antes del Cuadro2 para no capturar importación/precios USD.
    table = text.split("Cuadro 1", 1)[1].split("Cuadro 2", 1)[0]
    rows, rejected = [], []
    price_token = r"(\d{1,3}(?:\.\d{3})+)"
    pattern = re.compile(r"^\s*(" + "|".join(re.escape(r) for r in REGIONS) + r")\s+" + price_token + r"\s+" + price_token + r"\s+[-+]?\d+[,.]\d+\s*%\s*$")
    for line in table.splitlines():
        stripped = line.strip()
        region_name = next((region for region in REGIONS if stripped.startswith(region + " ")), None)
        if region_name is None:
            continue
        match = pattern.match(line)
        if match is None:
            rejected.append({"source_record": stripped, "reason": "ambiguous_or_missing_current_year_price"})
            continue
        region, previous_price, current_price = match.groups()
        code = REGIONS[region]
        price = int(current_price.replace(".", ""))
        if price <= 0:
            raise ValueError("Precio no positivo en informe")
        rows.append({"date": start, "period_end": start + pd.Timedelta(days=6),
                     "iso_year": start.isocalendar().year, "iso_week": start.isocalendar().week,
                     "available_at": available, "product": "Maíz grano", "market_level": "producer_reference",
                     "market_region_code": code, "market_region": region,
                     "geography_level": "national" if code == "CL" else "region",
                     "currency": "CLP", "unit": "quintal", "price": price,
                     "source": "ODEPA con información de Cotrisa", "source_url": report_url,
                     "source_record": stripped, "frequency": "weekly",
                     "series_id": f"cotrisa_maiz_grano_{code}_clp_quintal_weekly"})
    if not rows or len({row["series_id"] for row in rows}) != len(rows):
        raise ValueError("Sin filas inequívocas o regiones duplicadas en Cuadro 1")
    return pd.DataFrame(rows), pd.DataFrame(rejected, columns=["source_record", "reason"])


def ingest_report(root: str | Path, *, url: str = REPORT_2025_WEEK22,
                  period_start: str = "2025-05-26", available_at: str = "2025-06-04"):
    """Descarga PDF, guarda snapshot y devuelve datos/rechazos para curación."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Instala pypdf>=5 para extraer informes de maíz") from exc
    payload = fetch(url)
    if not payload.startswith(b"%PDF"):
        raise ValueError("La descarga no es PDF")
    digest = hashlib.sha256(payload).hexdigest()
    path = Path(root) / "odepa_cotrisa_maiz" / f"{digest}.pdf"
    atomic_write(path, payload)
    receipt(path, url=url, source="ODEPA/Cotrisa", period_start=period_start,
            source_available_at=available_at, parser="grains-cuadro1-2024-2025-v1")
    reader = PdfReader(io.BytesIO(payload))
    text = "\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
    atomic_write(path.with_suffix(".layout.txt"), text.encode())
    data, rejected = parse_report_text(text, period_start=period_start, report_url=url, available_at=available_at)
    data["source_sha256"] = digest
    data["source_path"] = str(path)
    return data, rejected
