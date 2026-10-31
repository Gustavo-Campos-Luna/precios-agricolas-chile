"""Series y tablas que alimentan los gráficos del informe.

Todo se calcula desde ``data/analysis`` (misma lógica que ``scripts/analysis_*.py``, que se importan para no duplicar
reglas). Cada función devuelve un DataFrame pequeño y legible: esos mismos DataFrames se guardan en ``report/data/``
como CSV, para que cualquier cifra del informe se pueda auditar sin correr el pipeline completo.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
ANALYSIS = ROOT / "data" / "analysis"
PROCESSED = ROOT / "data" / "processed"


def _load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


frutas = _load_script("analysis_frutas")
BASE_YEARS, RECENT_YEARS = frutas.BASE_YEARS, frutas.RECENT_YEARS


# --------------------------------------------------------------------------- frutas
def fruit_usable(name: str) -> pd.DataFrame:
    spec = frutas.PRODUCTS[name]
    data = frutas.load(spec)
    usable = data.dropna(subset=["price_vwap_clp_kg_real", "volume_kg_est"])
    return usable[usable["volume_kg_est"] > 0].copy()


def fruit_season(name: str) -> pd.DataFrame:
    """Precio real y nominal ponderado por kilos, y kilos vendidos, por temporada (mínimo 20 series)."""
    spec, usable = frutas.PRODUCTS[name], fruit_usable(name)
    nominal = pd.read_parquet(ANALYSIS / "prices_monthly.parquet", columns=["date", "series_id", "price_vwap_clp_kg"],
                              filters=[("product", "==", spec["product"])])
    usable = usable.merge(nominal, on=["date", "series_id"], how="left")
    rows = []
    for start, g in usable.groupby("start"):
        if g["series_id"].nunique() < 20:
            continue
        rows.append({"season_start": int(start), "season": frutas.label(int(start), spec["start_month"]),
                     "price_real_clp_kg": frutas.weighted(g),
                     "price_nominal_clp_kg": frutas.weighted(g, value="price_vwap_clp_kg"),
                     "million_kg": g["volume_kg_est"].sum() / 1e6, "series": g["series_id"].nunique()})
    return pd.DataFrame(rows)


def period_mean(frame: pd.DataFrame, years: tuple[int, ...], column: str = "price_real_clp_kg") -> float:
    sub = frame[frame["season_start"].isin(years)]
    return float(sub[column].mean()) if len(sub) else float("nan")


def fruit_change(name: str) -> dict:
    """Cambio del precio real entre períodos, nacional y con mercado y calidad fijos."""
    spec, usable = frutas.PRODUCTS[name], fruit_usable(name)
    season = fruit_season(name)
    base, recent = period_mean(season, BASE_YEARS), period_mean(season, RECENT_YEARS)
    recent_rows = usable[usable["start"].isin(RECENT_YEARS)]
    top_market = recent_rows.groupby("market")["volume_kg_est"].sum().idxmax()
    top_quality = recent_rows.groupby("quality")["volume_kg_est"].sum().idxmax()
    fixed = usable[(usable["market"] == top_market) & (usable["quality"] == top_quality)]
    b_fixed = frutas.weighted(fixed[fixed["start"].isin(BASE_YEARS)])
    r_fixed = frutas.weighted(fixed[fixed["start"].isin(RECENT_YEARS)])
    return {"product": spec["product"], "base": base, "recent": recent, "change": recent / base - 1,
            "fixed_market": top_market, "fixed_quality": top_quality,
            "fixed_change": r_fixed / b_fixed - 1 if np.isfinite(b_fixed) and np.isfinite(r_fixed) else float("nan")}


def fruit_varieties(name: str, top: int = 8) -> pd.DataFrame:
    usable = fruit_usable(name)

    def period(years):
        sub = usable[usable["start"].isin(years)]
        if sub.empty:
            return pd.DataFrame(columns=["price", "kilos", "seasons"])
        out = sub.groupby("variety_canonical").apply(lambda g: pd.Series({
            "price": frutas.weighted(g), "kilos": g["volume_kg_est"].sum(), "seasons": g["start"].nunique()}), include_groups=False)
        return out
    both = period(BASE_YEARS).join(period(RECENT_YEARS), lsuffix="_before", rsuffix="_after", how="inner")
    both = both[(both["seasons_before"] >= 2) & (both["seasons_after"] >= 2) & (both.index != "")]
    both["change"] = both["price_after"] / both["price_before"] - 1
    both = both.sort_values("kilos_after", ascending=False).head(top)
    both["million_kg_after"] = both["kilos_after"] / 1e6
    return both.reset_index().rename(columns={"variety_canonical": "variety"})[
        ["variety", "price_before", "price_after", "change", "million_kg_after"]]


def cherry_orchards() -> pd.DataFrame:
    """Hectáreas de cerezo por variedad en 2016 y 2024, solo regiones medidas en ambos años (no es cifra nacional)."""
    coverage = pd.read_csv(ANALYSIS / "orchards_coverage.csv", dtype={"region_id": str})
    measured = coverage.groupby("year").region_id.apply(set)
    common = measured[2016] & measured[2024]
    o = pd.read_parquet(ANALYSIS / "orchards.parquet", columns=["year", "region_id", "species", "variety_canonical", "area_ha"],
                        filters=[("species", "==", "Cerezo")])
    o["region_id"] = o["region_id"].astype(str)
    o = o[o["year"].isin([2016, 2024]) & o["region_id"].isin(common)]
    table = o.groupby(["variety_canonical", "year"]).area_ha.sum().unstack().fillna(0)
    table["regions_compared"] = len(common)
    return table.sort_values(2024, ascending=False).reset_index().rename(columns={2016: "ha_2016", 2024: "ha_2024", "variety_canonical": "variety"})


def apple_orchards() -> pd.DataFrame:
    coverage = pd.read_csv(ANALYSIS / "orchards_coverage.csv", dtype={"region_id": str})
    measured = coverage.groupby("year").region_id.apply(set)
    common = measured[2016] & measured[2024]
    o = pd.read_parquet(ANALYSIS / "orchards.parquet", columns=["year", "region_id", "species", "area_ha"],
                        filters=[("species", "in", ["Manzano Rojo", "Manzano Verde"])])
    o["region_id"] = o["region_id"].astype(str)
    o = o[o["year"].isin([2016, 2024]) & o["region_id"].isin(common)]
    return o.groupby("year").area_ha.sum().rename("area_ha").reset_index().assign(regions_compared=len(common))


# --------------------------------------------------------------------------- exportación de cereza
def cherry_exports() -> pd.DataFrame:
    """Cereza fresca dulce: 08092000 hasta 2011 empalmada con 080929xx desde 2012 (se excluyen guindas ácidas)."""
    x = pd.read_parquet(ANALYSIS / "exports_monthly.parquet", columns=["date", "hs_code", "kilos", "value_usd"])
    x["hs_code"] = x["hs_code"].astype(str)
    x = x[x["hs_code"].isin(["08092000", "08092911", "08092919", "08092990"])]
    annual = x.assign(year=x["date"].dt.year).groupby("year").agg(kilos=("kilos", "sum"), usd=("value_usd", "sum")).reset_index()
    annual["thousand_t"] = annual["kilos"] / 1e6
    annual["fob_usd_kg"] = annual["usd"] / annual["kilos"]
    annual["complete_year"] = annual["year"] < 2026  # 2026 solo tiene enero a septiembre
    return annual


# --------------------------------------------------------------------------- cereales
JUMP = 1.8


def _external() -> pd.DataFrame:
    ext = pd.read_parquet(ANALYSIS / "external_prices_monthly.parquet")
    for column in ("source", "level", "product", "unit", "currency", "frequency"):
        ext[column] = ext[column].astype(str)
    return ext


def fao_real() -> tuple[pd.DataFrame, dict]:
    """Precio real al productor FAOSTAT (CLP/t), solo el tramo posterior al último quiebre de la fuente."""
    names = {"Wheat": "Trigo", "Maize (corn)": "Maíz", "Rice": "Arroz"}
    ext = _external()
    fao = ext[(ext.source == "FAOSTAT") & (ext["unit"] == "LCU/tonne") & (ext.frequency == "annual") & ext["product"].isin(names)].copy()
    fao["year"] = fao["date"].dt.year
    real = fao.pivot_table(index="year", columns="product", values="value_real_clp").rename(columns=names)
    nominal = fao.pivot_table(index="year", columns="product", values="value").rename(columns=names)
    starts = {}
    for name in nominal.columns:
        s = nominal[name].dropna()
        jumps = [int(y) for y, r in (s / s.shift(1)).dropna().items() if r > JUMP or r < 1 / JUMP]
        starts[name] = max(jumps) if jumps else int(s.index.min())
        real.loc[real.index < starts[name], name] = np.nan
    return real, starts


def pink_real() -> pd.DataFrame:
    """Referencia internacional (Pink Sheet) en pesos reales por tonelada; solo años con 12 meses."""
    names = {"Wheat, US HRW": "Trigo", "Maize": "Maíz", "Rice, Thai 5%": "Arroz"}
    ext = _external()
    pink = ext[(ext.source == "World Bank Pink Sheet") & ext["product"].isin(names)][["date", "product", "value"]]
    cpi = pd.read_csv(PROCESSED / "bcch/cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    usd = pd.read_csv(PROCESSED / "bcch/usd_clp_monthly.csv", usecols=["date", "usd_clp"], parse_dates=["date"])
    pink = pink.merge(usd, on="date", how="left").merge(cpi, on="date", how="left")
    pink["clp_t_real"] = pink["value"] * pink["usd_clp"] * 100 / pink["cpi_index"]
    pink["year"] = pink["date"].dt.year
    pink["product"] = pink["product"].map(names)
    counts = pink.groupby(["product", "year"]).clp_t_real.count().unstack(0)
    annual = pink.groupby(["product", "year"]).clp_t_real.mean().unstack(0)
    return annual.where(counts >= 12)


def cotrisa_wheat() -> pd.DataFrame:
    ext = _external()
    c = ext[(ext.source == "Cotrisa") & ext["product"].str.startswith("Trigo")].copy()
    c["clp_t_real"] = c["value_real_clp"] * 10  # $/qqm a $/t
    return c.dropna(subset=["clp_t_real"]).groupby("date").agg(clp_t_real=("clp_t_real", "median"), regions=("product", "nunique")).reset_index()


# --------------------------------------------------------------------------- uva de vino
def wine_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    sys_path = str(ROOT / "src")
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    from materias_primas_chile.varieties import harmonize, load_aliases
    data = pd.read_parquet(PROCESSED / "odepa_datasets/uva_vinificacion.parquet", columns=["date", "region", "buyer", "variety", "price"]).dropna(subset=["date", "price"])
    cpi = pd.read_csv(PROCESSED / "bcch/cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    data["month"] = data["date"].dt.to_period("M").dt.to_timestamp()
    data = data.merge(cpi.rename(columns={"date": "month"}), on="month", how="left")
    data["price_real"] = data["price"] * 100 / data["cpi_index"]
    data["year"] = data["date"].dt.year
    data = harmonize(data.fillna({"variety": ""}), "variety", load_aliases())
    yearly = data.groupby("year").agg(quotes=("price", "size"), buyers=("buyer", "nunique"), median_nominal=("price", "median"),
                                      median_real=("price_real", "median")).reset_index()
    named = data[data["variety_key"] != ""]

    def med(years):
        return named[named["year"].isin(years)].groupby("variety_canonical").agg(price=("price_real", "median"), n=("price", "size"))
    both = med((2020, 2021)).join(med((2024, 2025)), lsuffix="_before", rsuffix="_after", how="inner")
    both = both[(both["n_before"] >= 15) & (both["n_after"] >= 15)]
    both["change"] = both["price_after"] / both["price_before"] - 1
    both = both.sort_values("n_after", ascending=False).head(8).reset_index().rename(columns={"variety_canonical": "variety"})
    return yearly, both


# --------------------------------------------------------------------------- macro
def macro_annual() -> pd.DataFrame:
    cpi = pd.read_csv(PROCESSED / "bcch/cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    usd = pd.read_csv(PROCESSED / "bcch/usd_clp_monthly.csv", usecols=["date", "usd_clp"], parse_dates=["date"])
    m = cpi.merge(usd, on="date", how="inner")
    m["year"] = m["date"].dt.year
    out = m.groupby("year").agg(cpi_index=("cpi_index", "mean"), usd_clp=("usd_clp", "mean"), months=("usd_clp", "size")).reset_index()
    return out[out["months"] == 12]


def wine_overall() -> dict:
    """Mediana real agrupada de todas las cotizaciones, 2020-21 frente a 2024-25 (unidad no declarada por ODEPA)."""
    data = pd.read_parquet(PROCESSED / "odepa_datasets/uva_vinificacion.parquet", columns=["date", "price"]).dropna()
    cpi = pd.read_csv(PROCESSED / "bcch/cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    data["month"] = data["date"].dt.to_period("M").dt.to_timestamp()
    data = data.merge(cpi.rename(columns={"date": "month"}), on="month", how="left")
    data["real"] = data["price"] * 100 / data["cpi_index"]
    data["year"] = data["date"].dt.year
    before = data[data["year"].isin((2020, 2021))]["real"].median()
    after = data[data["year"].isin((2024, 2025))]["real"].median()
    return {"before": float(before), "after": float(after), "change": float(after / before - 1)}
