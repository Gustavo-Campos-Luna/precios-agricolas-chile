"""Precios internos de trigo, maíz, arroz y avena publicados por Cotrisa (tablas HTML).

Cotrisa publica, por región, comprador y localidad, el precio pagado al productor en
$/quintal métrico (qqm). Cada página trae una tabla diaria (cabeceras ``dd/mm/aaaa``) y
una semanal (``dd-mm-aaaa``). Son precios de poder comprador de la campaña vigente, no
un histórico largo: la fuente no ofrece descarga de series anteriores. Las celdas
"Sin información" y vacías se omiten; nunca se rellenan con ceros ni se interpolan.
"""
from __future__ import annotations

import hashlib
import re
import time
from html.parser import HTMLParser
from pathlib import Path

import httpx
import pandas as pd

from .storage import atomic_write, receipt

URL = "https://www.cotrisa.cl/publicaciones/precios/tabla-precios/tabla-de-precios-{slug}/"
PRODUCTS = {"trigo": "Trigo", "maiz": "Maíz", "arroz": "Arroz", "avena": "Avena"}
USER_AGENT = "MateriasPrimasChile/0.1 (agricultural price research; public data)"
HEADER_DATE = re.compile(r"Precio\s*\(([^)]+)\)\s*(\d{2})([/-])(\d{2})\3(\d{4})")
THOUSANDS = re.compile(r"^\d{1,3}(\.\d{3})+$")


class _TableParser(HTMLParser):
    """Extrae tablas como listas de filas, expandiendo celdas con rowspan/colspan."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._rows: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._span: tuple[int, int] = (1, 1)
        self._pending: dict[int, list] = {}  # columna -> [texto, filas restantes]
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table":
            self._depth += 1
            if self._depth == 1:
                self._rows, self._pending = [], {}
        elif tag == "tr" and self._rows is not None:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
            self._span = (_int(attrs.get("rowspan")), _int(attrs.get("colspan")))

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._fill_pending()
            text = " ".join("".join(self._cell).split())
            rowspan, colspan = self._span
            for _ in range(colspan):
                column = len(self._row)
                self._row.append(text)
                if rowspan > 1:
                    self._pending[column] = [text, rowspan - 1]
                self._fill_pending()
            self._cell = None
        elif tag == "tr" and self._row is not None and self._rows is not None:
            self._fill_pending()
            if self._row:
                self._rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._depth -= 1
            if self._depth == 0 and self._rows is not None:
                self.tables.append(self._rows)
                self._rows = None

    def _fill_pending(self):
        """Inserta celdas heredadas por rowspan que caen en la posición actual."""
        while self._row is not None and len(self._row) in self._pending:
            column = len(self._row)
            text, remaining = self._pending[column]
            self._row.append(text)
            if remaining > 1:
                self._pending[column][1] = remaining - 1
            else:
                del self._pending[column]


def _int(value) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def parse_price(text: str) -> float | None:
    """'24000' y '23.000' son pesos enteros; 'Sin información' y vacío son faltantes."""
    value = text.strip().replace("$", "").replace(" ", "")
    if not value or not re.search(r"\d", value):
        return None
    if THOUSANDS.match(value):
        value = value.replace(".", "")
    elif "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    try:
        number = float(value)
    except ValueError:
        return None
    return number if number > 0 else None


def parse_tables(html: str, product: str, *, source_sha256: str = "") -> pd.DataFrame:
    parser = _TableParser()
    parser.feed(html)
    records = []
    for rows in parser.tables:
        header = rows[0]
        dated = [(i, HEADER_DATE.search(cell)) for i, cell in enumerate(header)]
        dated = [(i, m) for i, m in dated if m]
        if not dated or len(header) < 4:
            continue
        columns = {h.strip().lower(): i for i, h in enumerate(header)}
        region_i, buyer_i, place_i = columns.get("región", 0), columns.get("comprador", 1), columns.get("localidad", 2)
        note_i = columns.get("observaciones")
        for row in rows[1:]:
            if len(row) < len(header):
                row = row + [""] * (len(header) - len(row))
            for i, match in dated:
                price = parse_price(row[i])
                if price is None:
                    continue
                unit, day, separator, month, year = match.groups()
                records.append({
                    "product": product, "region": row[region_i], "buyer": row[buyer_i], "locality": row[place_i],
                    "date": pd.Timestamp(year=int(year), month=int(month), day=int(day)), "price": price,
                    "unit": unit.strip(),
                    "frequency": "daily" if separator == "/" else "weekly",
                    "observation": row[note_i] if note_i is not None and note_i < len(row) else "",
                })
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    frame["currency"] = "CLP"
    frame["market_level"] = "producer_buyer_price"
    frame["source"] = "Cotrisa tabla de precios"
    frame["source_sha256"] = source_sha256
    return frame


def fetch_product(slug: str, raw_root: str | Path = "data/raw/cotrisa", *, timeout: float = 60) -> Path:
    url = URL.format(slug=slug)
    for attempt in range(4):
        try:
            response = httpx.get(url, timeout=timeout, follow_redirects=True, headers={"User-Agent": USER_AGENT})
            if response.status_code == 200:
                break
            reason = f"HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            reason = type(exc).__name__
        time.sleep(min(30, 3 * 2 ** attempt))
    else:
        raise RuntimeError(f"Cotrisa {slug}: {reason}")
    digest = hashlib.sha256(response.content).hexdigest()
    path = Path(raw_root) / slug / f"{digest}.html"
    atomic_write(path, response.content)
    receipt(path, url=url, source="Cotrisa tabla de precios", method="GET", product=PRODUCTS[slug])
    return path
