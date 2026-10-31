"""Tablas de referencia mensuales: consumidor, exportación y series externas (productor, internacional).

Cada una conserva su nivel de mercado, unidad y moneda; no se fusionan con el panel mayorista.
- Consumidor: mediana mensual por producto/variedad/calidad/región/punto de venta/unidad.
- Exportación: valor unitario = SUMA(USD FOB) / SUMA(kilos) del mes, nunca el promedio de cocientes
  (un envío chico a precio alto no puede pesar igual que uno grande). Solo filas en kilo neto.
- Externas: ODEPA series mensuales, FAOSTAT, Pink Sheet y Cotrisa con precio real cuando la moneda es CLP.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .tables import iter_chunks, read_date_range
from .varieties import harmonize, load_aliases


def load_macro(macro: str | Path = "data/processed/bcch") -> tuple[pd.DataFrame, pd.DataFrame]:
    macro = Path(macro)
    cpi = pd.read_csv(macro / "cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    usd = pd.read_csv(macro / "usd_clp_monthly.csv", usecols=["date", "usd_clp"], parse_dates=["date"])
    return cpi, usd


def annual_cpi(cpi: pd.DataFrame) -> pd.DataFrame:
    """IPC anual = promedio de los 12 meses; años incompletos quedan vacíos (no se extrapola)."""
    data = cpi.assign(year=cpi["date"].dt.year)
    out = data.groupby("year").agg(cpi_index=("cpi_index", "mean"), months=("cpi_index", "size")).reset_index()
    out.loc[out["months"] < 12, "cpi_index"] = np.nan
    return out[["year", "cpi_index"]]


def deflate(frame: pd.DataFrame, value: str, cpi: pd.DataFrame, *, annual: pd.Series | None = None) -> pd.Series:
    """Valor en pesos del último mes con IPC. ``annual`` (bool) marca filas anuales, deflactadas con el IPC anual."""
    monthly = frame[["date"]].merge(cpi, on="date", how="left")["cpi_index"].to_numpy()
    if annual is not None and annual.any():
        yearly = frame[["date"]].assign(year=frame["date"].dt.year).merge(annual_cpi(cpi), on="year", how="left")["cpi_index"].to_numpy()
        monthly = np.where(annual.to_numpy(), yearly, monthly)
    return pd.Series(frame[value].to_numpy() * 100 / monthly, index=frame.index)


def build_exports(source: str | Path = "data/processed/odepa_datasets/comex_exportacion.csv") -> pd.DataFrame:
    """Valor unitario FOB mensual ponderado por kilos, por producto arancelario."""
    cols = ["date", "hs_code", "product", "region", "country", "unit", "volume", "value_usd"]
    parts = []
    for chunk in iter_chunks(source, cols):
        kilos = chunk["unit"].str.lower().str.contains("kilo", na=False) & chunk["volume"].gt(0) & chunk["value_usd"].ge(0)
        chunk = chunk[kilos].dropna(subset=["date"])
        parts.append(chunk.groupby(["date", "hs_code", "product"], as_index=False)
                     .agg(value_usd=("value_usd", "sum"), kilos=("volume", "sum"), n_flows=("volume", "size")))
    data = pd.concat(parts, ignore_index=True).groupby(["date", "hs_code", "product"], as_index=False).sum()
    data["fob_usd_per_kg"] = data["value_usd"] / data["kilos"]
    data["price_kind"] = "derived_unit_value_weighted_by_kg"
    return data


def build_retail(source: str | Path = "data/processed/odepa_datasets/consumidor.csv",
                 macro: str | Path = "data/processed/bcch", first_year: int = 2007, last_year: int = 2027) -> pd.DataFrame:
    """Mediana mensual del precio semanal al consumidor. Se lee año por año: cada mes cae entero en un año."""
    cpi, _ = load_macro(macro)
    columns = ["date", "region", "point_type", "group", "product", "product_raw", "unit", "price"]
    aliases = load_aliases()
    keys = ["date", "product", "variety_key", "variety_canonical", "variety_group", "quality", "region", "point_type", "unit"]
    parts = []
    for year in range(first_year, last_year + 1):
        data = read_date_range(source, columns, pd.Timestamp(year, 1, 1), pd.Timestamp(year + 1, 1, 1))
        data = data.dropna(subset=["date", "price"])
        if data.empty:
            continue
        data["date"] = data["date"].dt.to_period("M").dt.to_timestamp()
        pieces = data["product_raw"].astype(str).str.split("|", expand=True).reindex(columns=range(3))
        data["variety"] = pieces[1].str.strip().fillna("")
        data["quality"] = pieces[2].str.strip().fillna("")
        data = harmonize(data, "variety", aliases)
        parts.append(data.groupby(keys, as_index=False, observed=True, dropna=False).agg(
            price=("price", "median"), n_prices=("price", "size")))
    out = pd.concat(parts, ignore_index=True)
    out["price_real"] = deflate(out, "price", cpi)
    out["price_basis"] = "median_of_weekly_prices_in_month"
    return out


def build_external(macro: str | Path = "data/processed/bcch", processed: str | Path = "data/processed") -> pd.DataFrame:
    processed = Path(processed)
    cpi, usd = load_macro(macro)
    frames = []
    odepa = pd.read_csv(processed / "odepa_series/monthly_series.csv", parse_dates=["date"])
    frames.append(pd.DataFrame({"source": "ODEPA series mensuales", "level": odepa["market_type"], "product": odepa["product"],
                                "unit": odepa["unit"], "currency": odepa["currency"], "frequency": "monthly",
                                "date": odepa["date"], "value": odepa["price"]}))
    fao = pd.read_csv(processed / "faostat/producer_prices.csv", parse_dates=["date"])
    fao = fao[fao["currency"].isin(["CLP", "USD"])]
    frames.append(pd.DataFrame({"source": "FAOSTAT", "level": "producer_price", "product": fao["item"], "unit": fao["unit"],
                                "currency": fao["currency"], "frequency": fao["frequency"], "date": fao["date"], "value": fao["value"]}))
    pink = pd.read_csv(processed / "pinksheet/monthly_prices.csv", parse_dates=["date"])
    frames.append(pd.DataFrame({"source": "World Bank Pink Sheet", "level": "international_reference", "product": pink["commodity"],
                                "unit": "USD/" + pink["unit"].str.replace("$/", "", regex=False), "currency": "USD",
                                "frequency": "monthly", "date": pink["date"], "value": pink["price_usd"]}))
    cotrisa = pd.read_csv(processed / "cotrisa/prices_long.csv", parse_dates=["date"])
    cotrisa["month"] = cotrisa["date"].dt.to_period("M").dt.to_timestamp()
    monthly = cotrisa.groupby(["month", "product", "region", "unit"], as_index=False).agg(value=("price", "median"))
    frames.append(pd.DataFrame({"source": "Cotrisa", "level": "producer_buyer_price", "product": monthly["product"] + " | " + monthly["region"],
                                "unit": monthly["unit"], "currency": "CLP", "frequency": "monthly", "date": monthly["month"],
                                "value": monthly["value"]}))
    data = pd.concat(frames, ignore_index=True)
    annual = data["frequency"].eq("annual")
    clp = data["currency"].eq("CLP")
    data["value_real_clp"] = np.where(clp, deflate(data, "value", cpi, annual=annual), np.nan)
    data = data.merge(usd, on="date", how="left")
    data["value_clp_equiv"] = np.where(data["currency"].eq("USD") & data["frequency"].eq("monthly"), data["value"] * data["usd_clp"], np.nan)
    return data.drop(columns=["usd_clp"])


def write_reference(output: str | Path = "data/analysis", macro: str | Path = "data/processed/bcch") -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    summary = {}
    for name, builder in (("exports_monthly", build_exports), ("retail_monthly", lambda: build_retail(macro=macro)),
                          ("external_prices_monthly", lambda: build_external(macro))):
        table = builder()
        for column in table.select_dtypes(include="object").columns:
            table[column] = table[column].astype("category")
        table.to_parquet(output / f"{name}.parquet", index=False, compression="zstd")
        summary[name] = {"rows": len(table), "first": str(table["date"].min().date()), "last": str(table["date"].max().date())}
    return summary
