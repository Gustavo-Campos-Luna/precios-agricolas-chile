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


CLIMATE_LABELS = {"chill_hours": "Horas de frío (mayo a agosto)", "frost_days_2": "Días con mínima de 2 °C o menos (sep. y oct.)",
                  "tmin_spring": "Mínima media de primavera", "rain_harvest_mm": "Lluvia de cosecha (15 nov. a 31 ene.)",
                  "heat_days_30": "Días de 30 °C o más en la cosecha", "rain_winter_mm": "Lluvia de invierno"}


def climate_cherry() -> dict:
    """¿Se relacionan los índices agroclimáticos de seis puntos de O'Higgins, Maule y Ñuble con la cosecha y el precio?

    Índices: promedio de seis sitios (ERA5, ``agroclimate_indices.csv``), por temporada que empieza en noviembre del año
    ``y``. Resultados, todos relativos para quitar la tendencia de la superficie: desvío del rendimiento FAOSTAT del año
    ``y + 1`` y de las toneladas exportadas por hectárea respecto de su media móvil de cinco años, y variaciones
    anuales del valor FOB y del precio mayorista real. La muestra es de 2000 a 2025 (el horario de ERA5 parte en 2000),
    unos 26 años: solo correlaciones superiores a ``r_crit`` se distinguen del azar al 5%.
    """
    from scipy import stats

    idx = pd.read_csv(PROCESSED / "climate_era5/agroclimate_indices.csv").groupby("year")[list(CLIMATE_LABELS)].mean()
    c = crop("Cherries")
    se = cherry_season_exports().set_index("season_start")
    ev = cherry_export_vs_wholesale().set_index("season_start")
    yld = c["yield_kg_ha"]
    per_ha = pd.Series({y: se.loc[y, "kt"] * 1e3 / c["area_ha"].get(y + 1, np.nan) for y in se.index})
    outcomes = {
        "Rendimiento nacional": (yld / yld.rolling(5, center=True, min_periods=3).mean() - 1).shift(-1),
        "Exportación por hectárea": per_ha / per_ha.rolling(5, center=True, min_periods=3).mean() - 1,
        "Valor FOB por kilo": np.log(se["fob_usd_kg"]).diff(),
        "Precio mayorista real": np.log(ev["price_real_clp_kg"]).diff(),
    }
    rows = []
    for col in CLIMATE_LABELS:
        for name, series in outcomes.items():
            j = pd.concat([idx[col], series.rename("o")], axis=1).dropna()
            j = j[(j.index >= 2000) & (j.index <= 2025)]
            rows.append({"index": col, "outcome": name, "pearson": float(j[col].corr(j["o"])), "spearman": float(j[col].corr(j["o"], method="spearman")), "n": len(j)})
    table = pd.DataFrame(rows)
    n = int(table["n"].min())
    t = stats.t.ppf(0.975, n - 2)
    low = idx.loc[2000:2025, "chill_hours"].nsmallest(5)
    events = pd.DataFrame({"chill_hours": low, "export_t_ha_dev": outcomes["Exportación por hectárea"].reindex(low.index),
                           "fob_change": se["fob_usd_kg"].pct_change().reindex(low.index), "wholesale_change": ev["price_real_clp_kg"].pct_change().reindex(low.index)})
    scatter = pd.concat([idx["tmin_spring"], outcomes["Rendimiento nacional"].rename("yield_dev")], axis=1).dropna().loc[2000:2025]
    return {"table": table, "r_crit": float(t / np.sqrt(n - 2 + t * t)), "n": n, "low_chill": events, "rank_2023": int(idx.loc[2000:2025, "chill_hours"].rank().loc[2023]),
            "indices": idx, "scatter": scatter}


def cherry_breakeven(cost_shock: float = 0.0) -> dict:
    """Ejercicio ilustrativo: ¿alcanza el valor de exportación para cubrir el costo de producción por kilo?

    Supuestos (todos explícitos, el resultado es un orden de magnitud y no una medición):

    1. Costo: la ficha de ODEPA de cerezo en O'Higgins, junio de 2017 (huerto en plena producción, Lapins, 8.000 kg/ha), se
       actualiza hasta cada año con el índice de costos laborales del INE para la mano de obra (59% del costo) y con el IPC
       para el resto, y se convierte a dólares con el dólar promedio del año. ``cost_shock`` suma o resta una fracción.
    2. Retorno: el precio de venta a productor de la ficha equivale a una fracción fija del valor FOB de la temporada
       2016/17 (``producer_share``, cerca de 48%); la fracción restante corresponde a embalaje, comisiones y costos de
       exportación. Se supone que esa fracción se mantiene en el tiempo.
    3. La temporada que parte en el año ``y`` usa los promedios del año ``y``.
    """
    ficha = pd.read_csv(PROCESSED / "odepa_fichas/cerezo_ohiggins.csv").iloc[-1]
    ine = pd.read_csv(PROCESSED / "ine/remuneraciones_costo_laboral.csv", parse_dates=["month"])
    icl = ine[ine["series"] == "costo_laboral_nominal"].set_index("month")["value"]
    icl = icl.groupby(icl.index.year).mean()
    macro = R.macro_annual().set_index("year")
    se = cherry_season_exports().set_index("season_start")
    share_labor = float(ficha["labor_share"])
    producer_share = float(ficha["producer_price_clp_kg"] / macro.loc[2017, "usd_clp"] / se.loc[2016, "fob_usd_kg"])
    rows = []
    for y in range(2010, 2026):
        growth = share_labor * icl[y] / icl[2017] + (1 - share_labor) * macro.loc[y, "cpi_index"] / macro.loc[2017, "cpi_index"]
        cost_usd = float(ficha["unit_cost_clp_kg"]) * growth * (1 + cost_shock) / macro.loc[y, "usd_clp"]
        fob = float(se.loc[y, "fob_usd_kg"])
        rows.append({"season_start": y, "fob_usd_kg": fob, "producer_equiv_usd_kg": producer_share * fob, "cost_usd_kg": cost_usd,
                     "margin_usd_kg": producer_share * fob - cost_usd, "breakeven_fob_usd_kg": cost_usd / producer_share})
    t = pd.DataFrame(rows)
    return {"table": t, "producer_share": producer_share, "labor_share": share_labor, "ficha": ficha,
            "labor_growth": float(icl[2025] / icl[2017]), "cpi_growth": float(macro.loc[2025, "cpi_index"] / macro.loc[2017, "cpi_index"]),
            "seasons_below": t.loc[t["margin_usd_kg"] < 0, "season_start"].tolist()}


def china_cherry() -> pd.DataFrame:
    """Importaciones chinas de cereza fresca (HS 080929) según UN Comtrade: total mundial y desde Chile, por año.

    Es la mirada del comprador: el valor es CIF (incluye flete y seguro), por lo que supera al FOB chileno. Las cifras de
    2016 y 2017 chocan con las aduanas chilenas (valor unitario de 4,6 dólares por kilo en 2016 y caída de 51% del volumen en
    2017); se muestran, pero no se interpretan.
    """
    d = pd.read_csv(PROCESSED / "comtrade/china.csv", low_memory=False)
    a = d[d["query"].str.fullmatch(r"china_imp_cereza_\d{4}")].copy()
    a["kg"], a["usd"] = pd.to_numeric(a["kg"], errors="coerce"), pd.to_numeric(a["primaryValue"], errors="coerce")
    world = a[a["partnerCode"] == 0].set_index("refYear")[["kg", "usd"]]
    chile = a[a["partnerCode"] == 152].set_index("refYear")[["kg", "usd"]]
    out = pd.DataFrame({"world_kt": world["kg"] / 1e6, "chile_kt": chile["kg"] / 1e6, "chile_share": chile["kg"] / world["kg"],
                        "usd_kg_world": world["usd"] / world["kg"], "usd_kg_chile": chile["usd"] / chile["kg"], "chile_value_musd": chile["usd"] / 1e6})
    return out.reset_index().rename(columns={"refYear": "year"})


def grape_competition() -> pd.DataFrame:
    """Exportaciones de uva de mesa (HS 080610) de Chile, Perú y Sudáfrica según UN Comtrade: miles de toneladas y USD por kilo.

    Son declaraciones de cada exportador; Sudáfrica no tiene dato de 2023 y se deja el faltante. Argentina exporta menos de
    50 mil toneladas y no se grafica.
    """
    c = pd.read_csv(PROCESSED / "comtrade/competencia.csv", low_memory=False)
    c["kg"], c["usd"] = pd.to_numeric(c["kg"], errors="coerce"), pd.to_numeric(c["primaryValue"], errors="coerce")
    c["rep"] = c["query"].str.extract(r"exp_(\d+)_uva_mesa_")[0]
    g = c[c["rep"].isin(["152", "604", "710"]) & (c["partnerCode"] == 0)].dropna(subset=["rep"])
    names = {"152": "chile", "604": "peru", "710": "sudafrica"}
    kt = g.pivot_table(index="refYear", columns="rep", values="kg").rename(columns=names) / 1e6
    price = g.assign(p=g["usd"] / g["kg"]).pivot_table(index="refYear", columns="rep", values="p").rename(columns=names)
    out = kt.add_suffix("_kt").join(price.add_suffix("_usd_kg"))
    return out.reset_index().rename(columns={"refYear": "year"})


def wheat_origin_prices() -> pd.DataFrame:
    """Valor unitario CIF (USD por tonelada) del trigo que Chile declara importar, por origen. Solo 2023 a 2025 traen el
    detalle completo por origen en las declaraciones de Chile; los años anteriores tienen origen faltante y no se usan."""
    t = pd.read_csv(PROCESSED / "comtrade/trigo.csv", low_memory=False)
    t = t[t["query"].str.fullmatch(r"chile_imp_trigo_\d{4}")].copy()
    t["kg"], t["usd"] = pd.to_numeric(t["kg"], errors="coerce"), pd.to_numeric(t["primaryValue"], errors="coerce")
    t = t[t["partnerCode"].isin([0, 32, 124, 842]) & t["refYear"].between(2023, 2025)]
    names = {0: "mundo", 32: "argentina", 124: "canada", 842: "eeuu"}
    p = t.assign(p=t["usd"] / t["kg"] * 1000).pivot_table(index="refYear", columns="partnerCode", values="p").rename(columns=names)
    k = t.pivot_table(index="refYear", columns="partnerCode", values="kg").rename(columns=names) / 1e6
    return p.add_suffix("_usd_t").join(k.add_suffix("_kt")).reset_index().rename(columns={"refYear": "year"})


def wheat_export_gap() -> pd.DataFrame:
    """Valor unitario de exportación de trigo de Argentina frente al de EE.UU. (UN Comtrade) y margen local de Chile.

    Contrasta la hipótesis de que el margen del trigo chileno cayó porque Chile pasó a comprar trigo argentino, más barato
    que el estadounidense que se usa como referencia: si la brecha de precio entre ambos orígenes fue estable, el cambio de
    origen no explica una caída anterior a él.
    """
    e = pd.read_csv(PROCESSED / "comtrade/trigo_exportadores.csv", low_memory=False)
    e["kg"], e["usd"] = pd.to_numeric(e["kg"], errors="coerce"), pd.to_numeric(e["primaryValue"], errors="coerce")
    e["rep"] = e["query"].str.extract(r"exp_(\d+)_")[0]
    p = e[e["partnerCode"] == 0].assign(p=lambda d: d["usd"] / d["kg"] * 1000).pivot_table(index="refYear", columns="rep", values="p")
    p = p.rename(columns={"32": "arg_usd_t", "842": "eeuu_usd_t"})[["arg_usd_t", "eeuu_usd_t"]]
    p["arg_sobre_eeuu"] = p["arg_usd_t"] / p["eeuu_usd_t"]
    real, _ = R.fao_real()
    pink = R.pink_real()
    p["margen_chile"] = (real["Trigo"] / pink["Trigo"]).reindex(p.index)
    return p.loc[2015:].reset_index().rename(columns={"refYear": "year"})
