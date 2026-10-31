"""World Bank Commodity Price Data (The Pink Sheet): precios internacionales mensuales desde 1960.

Sirve de contexto de insumos (fertilizantes, energía) y de referencia internacional de cereales.
Todo en dólares nominales; no son precios chilenos. Las celdas "…" (sin dato) quedan como faltantes.
Requiere openpyxl (extra ``excel``).
"""
from __future__ import annotations

import hashlib
import io
import re
from pathlib import Path

import httpx
import pandas as pd

from .storage import atomic_write, receipt

PAGE = "https://www.worldbank.org/en/research/commodity-markets"
FALLBACK = ("https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/"
            "CMO-Historical-Data-Monthly.xlsx")
HEADERS = {"User-Agent": "Mozilla/5.0 (agricultural price research; public data)"}
DATE = re.compile(r"^(\d{4})M(\d{2})$")
LINK = re.compile(r"https://[^\"']+CMO-Historical-Data-Monthly\.xlsx")


def discover_url() -> str:
    try:
        page = httpx.get(PAGE, timeout=60, follow_redirects=True, headers=HEADERS).text
        links = LINK.findall(page)
        if links:
            return sorted(set(links))[-1]
    except httpx.HTTPError:
        pass
    return FALLBACK


def download(raw_root: str | Path = "data/raw/pinksheet") -> Path:
    url = discover_url()
    response = httpx.get(url, timeout=180, follow_redirects=True, headers=HEADERS)
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    path = Path(raw_root) / f"{digest}.xlsx"
    if not path.exists():
        atomic_write(path, response.content)
    receipt(path, url=url, source="World Bank Pink Sheet", method="GET")
    return path


def parse(workbook: bytes | str | Path, source_sha256: str = "") -> pd.DataFrame:
    sheet = pd.read_excel(io.BytesIO(workbook) if isinstance(workbook, bytes) else workbook,
                          sheet_name="Monthly Prices", header=None)
    names, units = sheet.iloc[4], sheet.iloc[5]
    first = next((i for i in range(6, len(sheet)) if DATE.match(str(sheet.iat[i, 0]).strip())), None)
    if first is None:
        raise ValueError("Pink Sheet: no se encontraron fechas tipo 1960M01; cambió el formato")
    rows = []
    for column in range(1, sheet.shape[1]):
        name = str(names.iloc[column]).strip()
        if name in ("nan", ""):
            continue
        unit = str(units.iloc[column]).strip()
        for i in range(first, len(sheet)):
            match = DATE.match(str(sheet.iat[i, 0]).strip())
            if not match:
                continue
            value = pd.to_numeric(sheet.iat[i, column], errors="coerce")  # "…" -> faltante, no cero
            if pd.notna(value):
                rows.append((pd.Timestamp(int(match[1]), int(match[2]), 1), name.rstrip(" *"), unit.strip("()"), float(value)))
    out = pd.DataFrame(rows, columns=["date", "commodity", "unit", "price_usd"])
    out["source"], out["source_sha256"] = "World Bank Pink Sheet", source_sha256
    return out


def build(raw_root: str | Path = "data/raw/pinksheet", output: str | Path = "data/processed/pinksheet") -> dict:
    path = download(raw_root)
    data = parse(path, hashlib.sha256(path.read_bytes()).hexdigest())
    target = Path(output) / "monthly_prices.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(target, index=False)
    return {"rows": len(data), "commodities": int(data.commodity.nunique()), "first": str(data.date.min().date()),
            "last": str(data.date.max().date()), "output": str(target)}
