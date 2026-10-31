"""Análisis explicativos: por qué se movieron los precios.

Cada función responde una pregunta concreta y devuelve una tabla pequeña (que el informe guarda en ``report/data``).
Reglas: se usan solo series ya validadas, las alineaciones de años se explican en el docstring y los resultados
estadísticos son descriptivos (correlaciones de variaciones anuales), no pruebas de causa.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import report_data as R

PROCESSED = R.PROCESSED
ANALYSIS = R.ANALYSIS
CHERRY_CODES = ["08092000", "08092911", "08092919", "08092990"]


def crops() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "faostat/crops_production.csv")


def crop(item: str) -> pd.DataFrame:
    c = crops()
    return c[c["item"] == item].set_index("year")


def fx_cushion() -> pd.DataFrame:
    """Valor unitario de exportación de la cereza en dólares y en pesos reales (años calendario completos)."""
    e = R.cherry_exports().set_index("year")
    e = e[e["complete_year"]].join(R.macro_annual().set_index("year")[["usd_clp", "cpi_index"]], how="inner")
    e["fob_clp_real"] = e["fob_usd_kg"] * e["usd_clp"] * 100 / e["cpi_index"]
    base = e.loc[2013]
    e["idx_usd"] = e["fob_usd_kg"] / base["fob_usd_kg"] * 100
    e["idx_clp_real"] = e["fob_clp_real"] / base["fob_clp_real"] * 100
    return e.reset_index()[["year", "fob_usd_kg", "usd_clp", "fob_clp_real", "idx_usd", "idx_clp_real"]]


def bridge(grain: str, base: tuple[int, ...] = (2015, 2016, 2017), recent: tuple[int, ...] = (2022, 2023, 2024)) -> dict:
    """Puente multiplicativo del precio real al productor.

    precio_real = precio_USD x dólar x (100 / IPC) x prima, con prima = precio_real / precio internacional en pesos reales.
    La prima local es el residuo que cierra el cambio total observado; ``premium_direct`` la calcula por separado y
    debe quedar cerca (control de coherencia).
    """
    names = {"Trigo": "Wheat, US HRW", "Maíz": "Maize"}
    ext = R._external()
    pk = ext[(ext.source == "World Bank Pink Sheet") & (ext["product"] == names[grain])].copy()
    pk["year"] = pk["date"].dt.year
    usd_price = pk.groupby("year")["value"].mean()
    macro = R.macro_annual().set_index("year")
    real, _ = R.fao_real()
    dom = real[grain].dropna()
    intl_real = usd_price * macro["usd_clp"] * 100 / macro["cpi_index"]
    premium = (dom / intl_real).dropna()

    def avg(series: pd.Series, years: tuple[int, ...]) -> float:
        return float(series.loc[series.index.intersection(years)].mean())

    usd = avg(usd_price, recent) / avg(usd_price, base)
    fx = avg(macro["usd_clp"], recent) / avg(macro["usd_clp"], base)
    cpi = avg(macro["cpi_index"], recent) / avg(macro["cpi_index"], base)
    total = avg(dom, recent) / avg(dom, base)
    prem = total / (usd * fx / cpi)  # residuo: lo que el productor retuvo del cambio internacional (incluye efectos de promediar)
    direct = avg(premium, recent) / avg(premium, base)  # cálculo directo, solo como control de coherencia
    return {"grain": grain, "usd": usd, "fx": fx, "cpi": cpi, "premium": prem, "premium_direct": direct, "total": total,
            "base": base, "recent": recent, "premium_base": avg(premium, base), "premium_recent": avg(premium, recent)}


def supply_price(item: str, product: str, lag: int = 0) -> pd.DataFrame:
    """Producción y superficie nacionales (FAOSTAT) junto al precio real mayorista.

    Para la cereza la temporada Y/Y+1 corresponde al año FAOSTAT Y+1 (``lag=1``): con ese desfase la producción
    sigue mejor a las exportaciones de la temporada (correlación 0,98) que sin desfase (0,96).
    """
    c = crop(item)
    season = R.fruit_season(product).set_index("season_start")
    out = pd.DataFrame({"price_real_clp_kg": season["price_real_clp_kg"]})
    for name in ("production_t", "area_ha", "yield_kg_ha"):
        out[name] = [c[name].get(y + lag, np.nan) for y in out.index]
    return out.reset_index().rename(columns={"season_start": "year"})


def flexibility(frame: pd.DataFrame) -> dict:
    """Relación entre variaciones anuales (logaritmos) del precio y de la producción: pendiente y correlación."""
    d = np.log(frame.dropna(subset=["price_real_clp_kg", "production_t"]).set_index("year")[["price_real_clp_kg", "production_t"]]).diff().dropna()
    return {"n": int(len(d)), "corr": float(d["price_real_clp_kg"].corr(d["production_t"])),
            "slope": float(np.polyfit(d["production_t"], d["price_real_clp_kg"], 1)[0])}


def cherry_season_exports(last: int = 2025) -> pd.DataFrame:
    """Exportación de cereza fresca por temporada (noviembre a marzo siguiente): valor unitario FOB y miles de toneladas.

    La temporada ``last`` usa las declaraciones aduaneras disponibles (los valores pueden ajustarse hasta seis meses después
    por los informes de variación de valor), por lo que su cifra es preliminar.
    """
    x = pd.read_parquet(ANALYSIS / "exports_monthly.parquet", columns=["date", "hs_code", "kilos", "value_usd"])
    x["hs_code"] = x["hs_code"].astype(str)
    x = x[x["hs_code"].isin(CHERRY_CODES)].groupby("date").agg(kg=("kilos", "sum"), usd=("value_usd", "sum"))
    rows = []
    for y in range(1998, last + 1):
        w = x[(x.index >= f"{y}-11-01") & (x.index <= f"{y + 1}-03-31")]
        if w["kg"].sum() > 0:
            rows.append({"season_start": y, "fob_usd_kg": w["usd"].sum() / w["kg"].sum(), "kt": w["kg"].sum() / 1e6})
    return pd.DataFrame(rows)


def cherry_export_vs_wholesale() -> pd.DataFrame:
    """Valor unitario de exportación por temporada junto al precio mayorista real de la misma temporada."""
    s = cherry_season_exports().set_index("season_start")
    return s.join(R.fruit_season("cereza").set_index("season_start")[["price_real_clp_kg"]], how="inner").reset_index()


def tracking(frame: pd.DataFrame, a: str, b: str) -> dict:
    d = np.log(frame[[a, b]].dropna()).diff().dropna()
    return {"n": int(len(d)), "corr": float(d[a].corr(d[b]))}


def cherry_revenue_per_ha() -> pd.DataFrame:
    """Ingreso FOB por hectárea plantada (año calendario). La superficie incluye huertos jóvenes sin producción plena."""
    c = crop("Cherries")
    e = R.cherry_exports().set_index("year")[["kilos", "usd"]].join(c[["area_ha", "production_t", "yield_kg_ha"]])
    e = e.join(R.macro_annual().set_index("year")[["usd_clp", "cpi_index"]]).dropna(subset=["area_ha"])
    e = e[e.index <= 2024]
    e["usd_per_ha"] = e["usd"] / e["area_ha"]
    e["clp_real_per_ha"] = e["usd_per_ha"] * e["usd_clp"] * 100 / e["cpi_index"]
    return e.reset_index()[["year", "area_ha", "production_t", "yield_kg_ha", "usd", "usd_per_ha", "clp_real_per_ha"]]


def inputs_vs_wheat() -> pd.DataFrame:
    """Urea, DAP y trigo (Pink Sheet, USD nominales), índice 2015-17 = 100, y relación urea/trigo."""
    ext = R._external()
    pk = ext[(ext.source == "World Bank Pink Sheet") & ext["product"].isin(["Urea", "DAP", "Wheat, US HRW"])].copy()
    pk["year"] = pk["date"].dt.year
    counts = pk.groupby(["product", "year"])["value"].count().unstack(0)
    annual = pk.groupby(["product", "year"])["value"].mean().unstack(0).where(counts >= 12).dropna()
    idx = annual / annual.loc[2015:2017].mean() * 100
    idx = idx.rename(columns={"Urea": "urea", "DAP": "dap", "Wheat, US HRW": "trigo"})
    idx["urea_sobre_trigo"] = idx["urea"] / idx["trigo"]
    return idx.loc[2015:].reset_index()


def wheat_area_price() -> pd.DataFrame:
    w = crop("Wheat")[["area_ha", "production_t", "yield_kg_ha"]]
    real, _ = R.fao_real()
    return w.join(real["Trigo"].rename("price_real_clp_t")).reset_index()


def climate_cherry() -> dict:
    """Exploración: ¿se relaciona el rendimiento del cerezo con indicadores agroclimáticos de Talca y Rancagua?

    Los puntos son ciudades de referencia (reanálisis NASA POWER), no el promedio de las zonas productoras, y la
    temperatura mínima del reanálisis subestima las heladas locales. El rendimiento se mide contra su media móvil de
    cinco años para quitar la maduración de los huertos.
    """
    cl = pd.concat([pd.read_csv(PROCESSED / f"climate/{loc}_daily.csv", parse_dates=["date"]) for loc in ("talca", "rancagua")])
    rows = []
    for y in range(1994, 2025):
        flor = cl[(cl["date"] >= f"{y}-09-15") & (cl["date"] <= f"{y}-11-15")]
        cos = cl[(cl["date"] >= f"{y}-11-15") & (cl["date"] <= f"{y + 1}-01-31")]
        rows.append({"year": y, "cold_days_flowering": (flor["temperature_min_c"] <= 2).sum() / 2,
                     "rain_mm_harvest": cos["precipitation_mm"].sum() / 2})
    a = pd.DataFrame(rows).set_index("year")
    ch = crop("Cherries")[["yield_kg_ha"]].copy()
    ch["yield_dev"] = ch["yield_kg_ha"] / ch["yield_kg_ha"].rolling(5, center=True, min_periods=3).mean() - 1
    out = {}
    for lag in (0, 1):
        j = a.join(ch.shift(-lag), how="inner").dropna(subset=["yield_dev"])
        out[lag] = {"n": int(len(j)), "cold": float(j["cold_days_flowering"].corr(j["yield_dev"])),
                    "rain": float(j["rain_mm_harvest"].corr(j["yield_dev"]))}
    return out
