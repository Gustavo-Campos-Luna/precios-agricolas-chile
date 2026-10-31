"""Precios al productor de Chile según FAOSTAT, publicados en HDX (Humanitarian Data Exchange).

Cubre cereales, legumbres, papa, leche y frutas (1991 en adelante) en moneda local nominal
(LCU/tonelada) y USD/tonelada, anual y mensual. Es la fuente de precio interno al productor
para trigo, maíz y avena que no existe en el portal de ODEPA. Limitaciones: rezago anual,
valores FAO (Flag A=oficial, E=estimado, I=imputado, X=otra fuente) y definición FAO del
producto, que no distingue variedad ni calidad comercial. ``SLC`` es moneda local estándar
(re-denominada) y se conserva separada de ``LCU``; no se mezclan elementos distintos.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pandas as pd

from .storage import atomic_write, receipt

PACKAGE = "https://data.humdata.org/api/3/action/package_show?id=chl-faostat-food-prices"
USER_AGENT = "MateriasPrimasChile/0.1 (agricultural price research; public data)"
ELEMENT_UNITS = {
    "Producer Price (LCU/tonne)": ("LCU/tonne", "CLP"),
    "Producer Price (USD/tonne)": ("USD/tonne", "USD"),
    "Producer Price (SLC/tonne)": ("SLC/tonne", "SLC"),
    "Producer Price Index (2014-2016 = 100)": ("index_2014_2016=100", "index"),
}


def discover_url() -> dict:
    meta = httpx.get(PACKAGE, timeout=60, headers={"User-Agent": USER_AGENT}).json()
    for resource in meta["result"]["resources"]:
        if resource.get("name", "").lower() == "chl_faostat_producer_prices.csv":
            return resource
    raise ValueError("HDX ya no publica chl_faostat_producer_prices.csv; revisar el dataset")


def download(raw_root: str | Path = "data/raw/faostat") -> Path:
    resource = discover_url()
    response = httpx.get(resource["url"], timeout=180, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    path = Path(raw_root) / f"{digest}.csv"
    if not path.exists():
        atomic_write(path, response.content)
    receipt(path, url=resource["url"], source="FAOSTAT via HDX", method="GET",
            resource_last_modified=resource.get("last_modified"))
    return path


def normalize(frame: pd.DataFrame, source_sha256: str = "") -> pd.DataFrame:
    unknown = set(frame["Element"]) - set(ELEMENT_UNITS)
    if unknown:
        raise ValueError(f"Elementos FAOSTAT no reconocidos: {sorted(unknown)}")
    unit = frame["Element"].map(lambda e: ELEMENT_UNITS[e][0])
    currency = frame["Element"].map(lambda e: ELEMENT_UNITS[e][1])
    out = pd.DataFrame({
        "date": pd.to_datetime(frame["StartDate"], errors="coerce"),
        "date_end": pd.to_datetime(frame["EndDate"], errors="coerce"),
        "frequency": frame["Months"].str.contains("annual", case=False).map({True: "annual", False: "monthly"}),
        "item": frame["Item"], "item_code": frame["Item Code"], "element": frame["Element"],
        "unit": unit, "currency": currency,
        "value": pd.to_numeric(frame["Value"], errors="coerce"), "flag": frame["Flag"],
    })
    out = out.dropna(subset=["date", "value"])  # nunca se rellena con ceros
    out["market_level"], out["source"] = "producer_price", "FAOSTAT (HDX)"
    out["source_sha256"] = source_sha256
    return out.reset_index(drop=True)


def build(raw_root: str | Path = "data/raw/faostat", output: str | Path = "data/processed/faostat") -> dict:
    path = download(raw_root)
    frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    data = normalize(frame, hashlib.sha256(path.read_bytes()).hexdigest())
    target = Path(output) / "producer_prices.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(target, index=False)
    return {"rows": len(data), "items": int(data["item"].nunique()), "output": str(target),
            "first_year": int(data.date.dt.year.min()), "last_year": int(data.date.dt.year.max())}


# --- Producción, superficie cosechada y rendimiento (FAOSTAT, Chile) ----------------------
PRODUCTION_PACKAGE = "https://data.humdata.org/api/3/action/package_show?id=chl-faostat-crops-livestock-production"
PRODUCTION_FILE = "chl_faostat_crops_livestock_products.csv"
CROP_ELEMENTS = {"Area harvested": "area_ha", "Production": "production_t", "Yield": "yield_kg_ha"}


def download_production(raw_root: str | Path = "data/raw/faostat_production") -> Path:
    meta = httpx.get(PRODUCTION_PACKAGE, timeout=60, headers={"User-Agent": USER_AGENT}).json()
    resource = next((r for r in meta["result"]["resources"] if r.get("name") == PRODUCTION_FILE), None)
    if resource is None:
        raise ValueError(f"HDX ya no publica {PRODUCTION_FILE}; revisar el dataset")
    response = httpx.get(resource["url"], timeout=300, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    digest = hashlib.sha256(response.content).hexdigest()
    path = Path(raw_root) / f"{digest}.csv"
    if not path.exists():
        atomic_write(path, response.content)
    receipt(path, url=resource["url"], source="FAOSTAT via HDX", method="GET",
            resource_last_modified=resource.get("last_modified"))
    return path


def normalize_production(frame: pd.DataFrame, source_sha256: str = "") -> pd.DataFrame:
    """Tabla ancha por cultivo y año: superficie cosechada, producción y rendimiento (solo cultivos agrícolas)."""
    data = frame[frame["Element"].isin(CROP_ELEMENTS)].copy()
    data["value"] = pd.to_numeric(data["Value"], errors="coerce")
    data = data.dropna(subset=["value"])  # nunca se rellena con ceros
    data["year"] = pd.to_numeric(data["Year"], errors="coerce").astype("Int64")
    data["measure"] = data["Element"].map(CROP_ELEMENTS)
    wide = data.pivot_table(index=["Item", "year"], columns="measure", values="value", aggfunc="first").reset_index()
    wide = wide.rename(columns={"Item": "item"})
    flags = data.pivot_table(index=["Item", "year"], columns="measure", values="Flag", aggfunc="first").reset_index()
    wide["flags"] = (flags[[c for c in CROP_ELEMENTS.values() if c in flags]].fillna("").agg("/".join, axis=1)).to_numpy()
    wide["source"], wide["source_sha256"] = "FAOSTAT (HDX)", source_sha256
    return wide


def build_production(raw_root: str | Path = "data/raw/faostat_production", output: str | Path = "data/processed/faostat") -> dict:
    path = download_production(raw_root)
    frame = pd.read_csv(path, dtype=str, encoding="utf-8-sig")
    data = normalize_production(frame, hashlib.sha256(path.read_bytes()).hexdigest())
    target = Path(output) / "crops_production.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(target, index=False)
    return {"rows": len(data), "crops": int(data["item"].nunique()), "first_year": int(data["year"].min()),
            "last_year": int(data["year"].max()), "output": str(target)}
