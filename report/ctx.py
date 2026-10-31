"""Cálculo de todas las cifras y construcción de todas las figuras del informe.

``build()`` devuelve un objeto con dos diccionarios: ``n`` (cifras que el texto cita) y ``f`` (figuras en HTML).
Ningún número del texto se escribe a mano si sale de los datos: se calcula aquí y se guarda en ``report/data``.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd

import drivers as D
import report_data as R
import svgcharts as S
import svgextra as SX
from helpers import COL, MONTHS, es, figure, save, season_x, sg, vname
from referencias import cite, narrative

SRC_ODEPA = f"Fuente: elaboración propia con datos de {narrative('odepa_mayorista')}"
TICKS_LONG = [1995, 2000, 2005, 2010, 2015, 2020, 2025]


def _seg(frame: pd.DataFrame, col: str, years: tuple[int, ...]) -> float:
    s = frame[col].dropna()
    return float(s.loc[s.index.intersection(years)].mean())


def _yearly(series: pd.Series, years: list[int]) -> list[float]:
    return [float(series[y]) if y in series.index and pd.notna(series[y]) else float("nan") for y in years]


def build() -> SimpleNamespace:
    n: dict = {}
    f: dict = {}

    # ------------------------------------------------------------------ datos base
    chg = {k: R.fruit_change(k) for k in ("cereza", "uva", "manzana", "poroto_verde")}
    season = {k: R.fruit_season(k) for k in ("cereza", "uva", "manzana")}
    season["manzana"] = season["manzana"][season["manzana"]["season_start"] <= 2025]  # 2026 incompleto
    var = {k: R.fruit_varieties(k) for k in ("cereza", "uva", "manzana")}
    real, _ = R.fao_real()
    pink = R.pink_real()
    cot = R.cotrisa_wheat()
    exports = R.cherry_exports()
    wine_year, wine_var = R.wine_tables()
    wine_all = R.wine_overall()
    macro = R.macro_annual()
    orch = R.cherry_orchards()
    apple_ha = R.apple_orchards().set_index("year")["area_ha"]
    base3 = (2015, 2016, 2017)
    n.update(chg=chg, wine_all=wine_all, orch=orch)

    for k, v in season.items():
        save(f"temporadas_{k}", v)
    for k, v in var.items():
        save(f"variedades_{k}", v)
    save("exportaciones_cereza_anual", exports)
    save("superficie_cerezo_regiones_comunes_2016_2024", orch)
    save("fao_productor_real_clp_t", real.reset_index())
    save("pinksheet_real_clp_t", pink.reset_index())
    save("cotrisa_trigo_mensual_real", cot)
    save("uva_vino_anual", wine_year)
    save("uva_vino_variedades", wine_var)
    save("macro_anual", macro)

    grain, intl = {}, {}
    for g in ("Trigo", "Maíz", "Arroz"):
        b, r_ = _seg(real, g, base3), _seg(real, g, R.RECENT_YEARS)
        grain[g] = {"base": b, "recent": r_, "change": r_ / b - 1}
        b, r_ = _seg(pink, g, base3), _seg(pink, g, R.RECENT_YEARS)
        intl[g] = {"base": b, "recent": r_, "change": r_ / b - 1}
    n.update(grain=grain, intl=intl)
    ratio = (real["Trigo"] / pink["Trigo"]).dropna()
    n["wheat_ratio"] = (float(ratio.min()), float(ratio.max()))

    sc = season["cereza"]
    n["cer"] = dict(base=R.period_mean(sc, R.BASE_YEARS), recent=R.period_mean(sc, R.RECENT_YEARS),
                    nom_base=R.period_mean(sc, R.BASE_YEARS, "price_nominal_clp_kg"), nom_recent=R.period_mean(sc, R.RECENT_YEARS, "price_nominal_clp_kg"),
                    kg_base=R.period_mean(sc, R.BASE_YEARS, "million_kg"), kg_recent=R.period_mean(sc, R.RECENT_YEARS, "million_kg"))
    n["cer"]["nom_change"] = n["cer"]["nom_recent"] / n["cer"]["nom_base"] - 1
    bys = sc.set_index("season_start")
    n["cer"]["last_price"], n["cer"]["last_season"] = float(bys["price_real_clp_kg"].iloc[-1]), str(bys["season"].iloc[-1])
    n["cer"]["by_season"] = bys

    # ------------------------------------------------------------------ exportación de cereza
    e = exports.set_index("year")
    n["ex"] = dict(y13=e.loc[2013], y19=e.loc[2019], y24=e.loc[2024], y25=e.loc[2025])
    se = D.cherry_season_exports().set_index("season_start")
    n["se"] = se
    n["fob_peak_seasons"] = (float(se.loc[2009:2023, "fob_usd_kg"].min()), float(se.loc[2009:2023, "fob_usd_kg"].max()))
    save("exportaciones_cereza_temporada", se.reset_index())
    wholesale_2425 = float(bys.loc[2024, "million_kg"])
    n["wholesale_share"] = wholesale_2425 / float(e.loc[2025, "thousand_t"])
    n["wholesale_2425"] = wholesale_2425

    # ------------------------------------------------------------------ figura: panorama
    items = [
        {"label": "Cereza (mayorista)", "value": chg["cereza"]["change"], "color": COL["cereza"], "note": "2014/17 vs 2022/25"},
        {"label": "Uva para vino", "value": wine_all["change"], "color": COL["uva"], "note": "2020/21 vs 2024/25"},
        {"label": "Poroto verde (mayorista)", "value": chg["poroto_verde"]["change"], "color": COL["neutro"], "note": "2014/17 vs 2022/25"},
        {"label": "Uva de mesa (mayorista)", "value": chg["uva"]["change"], "color": COL["uva"], "note": "2014/17 vs 2022/25"},
        {"label": "Arroz (productor)", "value": grain["Arroz"]["change"], "color": COL["neutro"], "note": "2015/17 vs 2022/24"},
        {"label": "Trigo (productor)", "value": grain["Trigo"]["change"], "color": COL["trigo"], "note": "2015/17 vs 2022/24"},
        {"label": "Maíz (productor)", "value": grain["Maíz"]["change"], "color": COL["maiz"], "note": "2015/17 vs 2022/24"},
        {"label": "Manzana (mayorista)", "value": chg["manzana"]["change"], "color": COL["manzana"], "note": "2014/16 vs 2022/24"},
    ]
    items.sort(key=lambda i: i["value"])
    svg, tab = S.diverging_bars(items, alt="Cambio del precio real de ocho productos agrícolas chilenos entre dos períodos")
    f["overview"] = figure("overview", "Descontada la inflación, la cereza y la uva para vino valen menos que hace diez años; la manzana y los cereales, más", svg, tab,
                           "<i>Nota.</i> Precios en pesos de septiembre de 2026. Los períodos comparados difieren según los datos disponibles (columna derecha). "
                           "La uva para vino es la mediana real de lo que pagan las viñas; la fuente no declara su unidad. "
                           f"{SRC_ODEPA}, {narrative('faostat')}, {narrative('cotrisa')} y {narrative('banco_central')}.")

    # ------------------------------------------------------------------ cómo leer: nominal frente a real
    xs = sc["season_start"].tolist()
    svg, tab = S.line_chart(
        [dict(name="En pesos de cada año", label="Pesos de cada año", color=COL["neutro"], x=xs, y=sc["price_nominal_clp_kg"].tolist(), dash=True),
         dict(name="En pesos de septiembre de 2026", label="Pesos de hoy", color=COL["cereza"], x=xs, y=sc["price_real_clp_kg"].tolist(), width=2.4)],
        height=290, y_title="Pesos por kilo de cereza en el mayorista (temporada nov-feb)", x_fmt=season_x, x_ticks=TICKS_LONG,
        alt="Precio de la cereza en pesos de cada año y en pesos de hoy", right=104)
    f["inflation"] = figure("inflation", "La inflación esconde parte de la caída: el mismo precio de la cereza, con y sin ajuste", svg, tab,
                            f"<i>Nota.</i> Promedio ponderado por kilos vendidos, series con kilos declarados. {SRC_ODEPA} y {narrative('banco_central')}.")

    # ------------------------------------------------------------------ cereza: precio y volumen mayorista
    years = list(range(int(sc["season_start"].min()), int(sc["season_start"].max()) + 1))
    svg_a, tab_a = S.line_chart([dict(name="Precio real", label="Precio real", color=COL["cereza"], x=years, y=_yearly(bys["price_real_clp_kg"], years), width=2.4)],
                                height=230, y_title="Pesos de sept. de 2026 por kilo", x_fmt=season_x, x_ticks=TICKS_LONG, xpad=0.5,
                                alt="Precio real de la cereza por temporada", right=104, show_x=False)
    svg_b, tab_b = S.bar_chart(years, _yearly(bys["million_kg"], years), color=COL["cereza"], height=170, y_title="Millones de kilos vendidos en el mayorista",
                               x_fmt=season_x, label_set=set(TICKS_LONG), right=104, alt="Kilos de cereza vendidos en el mayorista por temporada",
                               name="Millones de kg", y_fmt=lambda v: es(v, 0))
    f["cherry"] = figure("cherry", "En el mayorista, el precio real de la cereza bajó mientras subió el volumen que llega", svg_a + svg_b, tab_a + tab_b,
                         f"<i>Nota.</i> Temporada = noviembre a febrero. Solo series con peso de envase declarado y temporadas con al menos 20 series. {SRC_ODEPA}.")

    # ------------------------------------------------------------------ cereza: valor unitario de exportación por temporada
    sx = se.reset_index()
    svg_a, tab_a = S.bar_chart(sx["season_start"].tolist(), sx["kt"].tolist(), color=COL["cereza"], height=170, y_title="Miles de toneladas exportadas",
                               x_fmt=season_x, label_set={1998, 2003, 2008, 2013, 2018, 2023}, show_x=False, right=104,
                               alt="Toneladas de cereza fresca exportadas por temporada", name="Miles de t", y_fmt=lambda v: es(v, 0),
                               highlight={2025: COL["neutro"]})
    svg_b, tab_b = S.line_chart([dict(name="Valor unitario FOB", label="USD/kg", color=COL["cereza"], x=sx["season_start"].tolist(), y=sx["fob_usd_kg"].tolist(), width=2.4, dots=True)],
                                height=210, y_title="Valor unitario de exportación, USD por kilo", y_min=0, x_ticks=[1998, 2003, 2008, 2013, 2018, 2023],
                                xpad=0.5, x_fmt=season_x, y_fmt=lambda v: es(v, 1), alt="Valor unitario de exportación de la cereza por temporada", right=104)
    f["exports"] = figure("exports", f"Cereza de exportación: el valor por kilo cayó de USD {es(se.loc[2023, 'fob_usd_kg'], 1)} a USD {es(se.loc[2024, 'fob_usd_kg'], 1)} en la temporada 2024/25 y no se recuperó", svg_a + svg_b, tab_a + tab_b,
                          "<i>Nota.</i> Temporada = noviembre a marzo siguiente, para ser comparable con ODEPA. La temporada 2025/26 (gris) es preliminar: las exportaciones "
                          "no realizadas a firme pueden ajustarse hasta seis meses después de declaradas " + cite('valenzuela2026') + ". Valor unitario = USD FOB divididos por kilos netos, "
                          "un valor derivado y no un precio publicado. Hasta 2011 se usa el código aduanero 08092000 y desde 2012 los 080929xx. "
                          f"Fuente: elaboración propia con datos de {narrative('odepa_comex')}.")

    # ------------------------------------------------------------------ cereza: el dólar como amortiguador
    fx = D.fx_cushion()
    save("cereza_fob_dolar_y_pesos_reales", fx)
    n["fx_c"] = fx.set_index("year")
    fxx = fx[fx["year"] >= 2005]
    svg, tab = S.line_chart(
        [dict(name="En dólares", label="En dólares", color=COL["neutro"], x=fxx["year"].tolist(), y=fxx["idx_usd"].tolist(), width=2.4, dash=True),
         dict(name="En pesos de hoy", label="En pesos de hoy", color=COL["cereza"], x=fxx["year"].tolist(), y=fxx["idx_clp_real"].tolist(), width=2.6)],
        height=260, y_title="Valor unitario de exportación, índice 2013 = 100", y_min=0, x_ticks=[2005, 2010, 2015, 2020, 2025], alt="Valor unitario de exportación de la cereza en dólares y en pesos reales",
        right=124, y_fmt=lambda v: es(v, 0))
    f["fxcushion"] = figure("fxcushion", "El dólar alto amortigua en pesos una parte de la caída del precio de exportación", svg, tab,
                            f"<i>Nota.</i> Año calendario completo. Pesos reales = valor FOB en dólares x dólar observado promedio, deflactado por el IPC (septiembre de 2026 = 100). "
                            f"Elaboración propia con {narrative('odepa_comex')} y {narrative('banco_central')}.")

    # ------------------------------------------------------------------ cereza: ¿sigue el mayorista a la exportación?
    ev = D.cherry_export_vs_wholesale()
    save("cereza_exportacion_vs_mayorista", ev)
    d = np.log(ev.set_index("season_start")[["fob_usd_kg", "price_real_clp_kg"]]).diff().dropna()
    n["track"] = dict(n=len(d), corr=float(d["fob_usd_kg"].corr(d["price_real_clp_kg"])))
    pts = [{"x": float(np.expm1(r.fob_usd_kg)), "y": float(np.expm1(r.price_real_clp_kg)), "label": season_x(i)} for i, r in d.iterrows()]
    svg, tab = SX.scatter(pts, color=COL["cereza"], x_title="Variación anual del valor FOB por kilo", y_title="Variación anual del precio mayorista real",
                          label_years=("2023/24", "2024/25", "2022/23", "2025/26"), alt="Variación anual del precio mayorista de la cereza frente a la del precio de exportación")
    f["track"] = figure("track", "El precio del mayorista acompaña al de exportación, pero con mucho ruido propio", svg, tab,
                        f"<i>Nota.</i> Cada punto es una temporada. Las variaciones se calcularon en logaritmos y se muestran como porcentajes; la recta es solo descriptiva. "
                        f"Correlación: {es(n['track']['corr'], 2)} en {n['track']['n']} temporadas. Elaboración propia con {narrative('odepa_comex')} y {narrative('odepa_mayorista')}.")

    # ------------------------------------------------------------------ cereza: variedades y ficha de huertos
    vc = var["cereza"].head(8)
    dumb = [{"label": vname(r.variety), "before": r.price_before, "after": r.price_after, "change": r.change, "extra": f"{es(r.million_kg_after, 1)} M kg"} for r in vc.itertuples()]
    svg, tab = S.dumbbell(dumb, color=COL["cereza"], x_title="Pesos de sept. de 2026 por kilo", before_name="2014/15 a 2016/17", after_name="2022/23 a 2024/25",
                          alt="Precio real de las principales variedades de cereza, antes y ahora")
    f["cherry_var"] = figure("cherry_var", "Todas las variedades principales de cereza bajaron", svg, tab,
                             "<i>Nota.</i> Círculo vacío: promedio 2014/15 a 2016/17. Círculo lleno: promedio 2022/23 a 2024/25. A la derecha, el cambio y los millones de kilos vendidos en el período reciente. "
                             f"Variedades presentes en al menos 2 temporadas de cada período. {SRC_ODEPA}.")
    n["var_cer_range"] = (float(vc["change"].max()), float(vc["change"].min()))
    o = orch.set_index("variety")
    n["orch_tot"] = (float(orch["ha_2016"].sum()), float(orch["ha_2024"].sum()))
    rows = "".join(f"<tr><td>{vname(v)}</td><td class='r'>{es(o.loc[v, 'ha_2016'])}</td><td class='r'>{es(o.loc[v, 'ha_2024'])}</td>"
                   f"<td class='r'>{es(o.loc[v, 'ha_2024'] / o.loc[v, 'ha_2016'], 1)} veces</td></tr>" for v in ("santina", "regina", "lapins", "kordia"))
    n["orch_table"] = ("<table class='t'><thead><tr><th>Variedad</th><th class='r'>Hectáreas 2016</th><th class='r'>Hectáreas 2024</th><th class='r'>Multiplicador</th></tr></thead>"
                       f"<tbody>{rows}</tbody></table>")

    # ------------------------------------------------------------------ cereza: superficie, producción e ingreso por hectárea
    rv = D.cherry_revenue_per_ha()
    save("cereza_ingreso_por_hectarea", rv)
    n["rv"] = rv.set_index("year")
    rvx = rv[rv["year"] >= 2005]
    svg, tab = S.line_chart([dict(name="Ingreso FOB por hectárea", label="Millones de pesos", color=COL["cereza"], x=rvx["year"].tolist(),
                                  y=(rvx["clp_real_per_ha"] / 1e6).tolist(), width=2.6, dots=True)],
                            height=240, y_title="Millones de pesos de sept. de 2026 por hectárea plantada", y_min=0, x_ticks=[2005, 2010, 2015, 2020, 2024], xpad=0.5,
                            y_fmt=lambda v: es(v, 0), alt="Ingreso de exportación por hectárea plantada de cerezo, en pesos reales", right=104)
    f["revha"] = figure("revha", "Cada hectárea plantada de cerezo siguió generando ingresos de exportación similares, aunque el kilo vale menos", svg, tab,
                        "<i>Nota.</i> Ingreso bruto de exportación (FOB) dividido por la superficie de cerezo de FAOSTAT; no descuenta costos de cosecha, embalaje ni flete. "
                        "La superficie incluye huertos jóvenes que aún no producen a plena capacidad, lo que subestima el ingreso por hectárea productiva. "
                        f"Elaboración propia con {narrative('odepa_comex')}, {narrative('faostat_cultivos')} y {narrative('banco_central')}.")
    area25 = 77766.0  # hectáreas de cerezo 2025 según el catastro (Valenzuela, 2026)
    n["rev25_usd_ha"] = float(e.loc[2025, "usd"]) / area25
    n["area25"] = area25

    # ------------------------------------------------------------------ manzana y uva de mesa
    ap, uv = season["manzana"].set_index("season_start"), season["uva"].set_index("season_start")
    common = sorted(set(ap.index) & set(uv.index))
    svg, tab = S.line_chart(
        [dict(name="Manzana", color=COL["manzana"], x=common, y=[ap.loc[y, "price_real_clp_kg"] for y in common], width=2.4),
         dict(name="Uva de mesa", color=COL["uva"], x=common, y=[uv.loc[y, "price_real_clp_kg"] for y in common], width=2.4)],
        height=290, y_title="Pesos de sept. de 2026 por kilo en el mayorista", x_fmt=lambda v: str(int(v)), x_ticks=TICKS_LONG,
        alt="Precio real de la manzana y de la uva de mesa", right=104)
    f["apple_grape"] = figure("apple_grape", "Manzana y uva de mesa: precios reales al alza en la última década", svg, tab,
                              f"<i>Nota.</i> Manzana por año calendario; uva de mesa por temporada (diciembre a abril), ubicada en el año en que parte. Promedio ponderado por kilos. {SRC_ODEPA}.")

    sp = D.supply_price("Apples", "manzana", 0)
    save("manzana_produccion_y_precio", sp)
    spx = sp[(sp["year"] >= 2005) & (sp["year"] <= 2024)].set_index("year")
    b = spx.loc[2015:2017].mean()
    idx_p, idx_q = spx["price_real_clp_kg"] / b["price_real_clp_kg"] * 100, spx["production_t"] / b["production_t"] * 100
    svg, tab = S.line_chart(
        [dict(name="Precio real mayorista", label="Precio", color=COL["manzana"], x=idx_p.index.tolist(), y=idx_p.tolist(), width=2.6),
         dict(name="Producción nacional", label="Producción", color=COL["neutro"], x=idx_q.index.tolist(), y=idx_q.tolist(), width=2.4, dash=True)],
        height=270, y_title="Índice, promedio 2015-2017 = 100", y_min=0, x_ticks=[2005, 2010, 2015, 2020, 2024], x_fmt=lambda v: str(int(v)),
        alt="Producción de manzana y precio real en el mayorista", right=104, y_fmt=lambda v: es(v, 0))
    f["apple_idx"] = figure("apple_idx", "Manzana: cuando la producción nacional se achica, el precio real sube", svg, tab,
                            f"<i>Nota.</i> Producción: FAOSTAT {cite('faostat_cultivos')}. Precio: promedio anual ponderado del mayorista. "
                            f"Elaboración propia con {narrative('odepa_mayorista')}.")
    n["apple"] = dict(flex=D.flexibility(sp), prod15=float(spx.loc[2015, "production_t"]), prod24=float(spx.loc[2024, "production_t"]),
                      area15=float(spx.loc[2015, "area_ha"]), area24=float(spx.loc[2024, "area_ha"]),
                      p15=float(spx.loc[2015, "price_real_clp_kg"]), p24=float(spx.loc[2024, "price_real_clp_kg"]),
                      yield15=float(spx.loc[2015, "yield_kg_ha"]), yield24=float(spx.loc[2024, "yield_kg_ha"]))
    dd = np.log(sp.dropna(subset=["price_real_clp_kg", "production_t"]).set_index("year")[["production_t", "price_real_clp_kg"]]).diff().dropna()
    pts = [{"x": float(np.expm1(r.production_t)), "y": float(np.expm1(r.price_real_clp_kg)), "label": str(int(i))} for i, r in dd.iterrows()]
    svg, tab = SX.scatter(pts, color=COL["manzana"], x_title="Variación anual de la producción nacional", y_title="Variación anual del precio real mayorista",
                          label_years=("2024", "2010", "2016"), alt="Variación anual del precio de la manzana frente a la de la producción")
    f["apple_scatter"] = figure("apple_scatter", "Manzana: en los años con menos producción el precio subió, en promedio, casi lo mismo que cayó la cosecha", svg, tab,
                                f"<i>Nota.</i> Cada punto es un año. Correlación {es(n['apple']['flex']['corr'], 2)} y pendiente {es(n['apple']['flex']['slope'], 2)} (variaciones en logaritmos, {n['apple']['flex']['n']} años). "
                                f"Es una relación descriptiva: no aísla el efecto de la demanda ni de las exportaciones. Elaboración propia con {narrative('faostat_cultivos')} y {narrative('odepa_mayorista')}.")

    va = var["manzana"].head(6)
    svg_a, tab_a = S.dumbbell([{"label": vname(r.variety), "before": r.price_before, "after": r.price_after, "change": r.change, "extra": f"{es(r.million_kg_after, 0)} M kg"} for r in va.itertuples()],
                              color=COL["manzana"], x_title="Manzana: pesos de sept. de 2026 por kilo", before_name="2014 a 2016", after_name="2022 a 2024",
                              alt="Precio real de las principales variedades de manzana")
    vu = var["uva"].head(6)
    svg_b, tab_b = S.dumbbell([{"label": vname(r.variety), "before": r.price_before, "after": r.price_after, "change": r.change, "extra": f"{es(r.million_kg_after, 1)} M kg"} for r in vu.itertuples()],
                              color=COL["uva"], x_title="Uva de mesa: pesos de sept. de 2026 por kilo", before_name="2014/15 a 2016/17", after_name="2022/23 a 2024/25",
                              alt="Precio real de las principales variedades de uva de mesa")
    f["var2"] = figure("var2", "El alza se repite en las variedades principales de manzana y de uva de mesa", svg_a + svg_b, tab_a + tab_b,
                       f"<i>Nota.</i> Círculo vacío: período base. Círculo lleno: período reciente. {SRC_ODEPA}.")
    n["area_apple_ha"] = apple_ha

    # ------------------------------------------------------------------ cereales: puente del precio del trigo
    br = {g: D.bridge(g) for g in ("Trigo", "Maíz")}
    n["bridge"] = br
    save("puente_trigo_maiz", pd.DataFrame([{k: v for k, v in b.items() if k not in ("base", "recent")} for b in br.values()]))
    w = br["Trigo"]
    steps = [dict(label="Precio en dólares", factor=w["usd"], note=f"x{es(w['usd'], 2)}"),
             dict(label="Dólar", factor=w["fx"], note=f"x{es(w['fx'], 2)}"),
             dict(label="Inflación", factor=1 / w["cpi"], note=f"x{es(1 / w['cpi'], 2)}"),
             dict(label="Margen local", factor=w["premium"], note=f"x{es(w['premium'], 2)}")]
    svg, tab = SX.waterfall(steps, start_label="2015 a 2017", total_label="2022 a 2024", y_title="Precio real del trigo al productor, índice 2015-2017 = 100",
                            alt="Descomposición del cambio del precio real del trigo al productor entre 2015-2017 y 2022-2024")
    f["bridge"] = figure("bridge", f"Trigo: el precio internacional casi se duplicó en dólares, pero al productor chileno le llegó solo {es((w['total'] - 1) * 100)}% más", svg, tab,
                         "<i>Nota.</i> Los cuatro factores se multiplican y cierran exactamente el cambio observado. 'Margen local' es el residuo: la relación entre el precio al productor y el internacional "
                         f"en pesos reales (de {es(w['premium_base'], 2)} a {es(w['premium_recent'], 2)}); su cálculo directo da x{es(w['premium_direct'], 2)}, coherente con el residuo. "
                         f"Elaboración propia con {narrative('faostat')}, {narrative('pink_sheet')} y {narrative('banco_central')}.")

    def grain_chart(g: str, color: str, alt: str):
        dom, inter = real[g].dropna(), pink[g].dropna()
        return S.line_chart(
            [dict(name="Precio al productor en Chile", label="Productor Chile", color=color, x=dom.index.tolist(), y=dom.tolist(), width=2.6, dots=True),
             dict(name="Referencia internacional en pesos", label="Internacional", color=COL["neutro"], x=inter.loc[2015:].index.tolist(), y=inter.loc[2015:].tolist(), width=2.2, dash=True)],
            height=270, y_title="Miles de pesos de sept. de 2026 por tonelada", y_fmt=lambda v: es(v / 1000, 0), x_ticks=list(range(2015, 2026, 2)), alt=alt, right=124)
    svg, tab = grain_chart("Trigo", COL["trigo"], "Precio real del trigo al productor frente al internacional")
    f["wheat"] = figure("wheat", "Trigo: el precio al productor chileno sigue al internacional, con menos amplitud", svg, tab,
                        f"<i>Nota.</i> Productor: FAOSTAT {cite('faostat')}, solo desde 2015 porque la serie cambia de base antes. Internacional: trigo duro rojo de invierno de EE.UU. del Banco Mundial "
                        f"{cite('pink_sheet')}, convertido al dólar observado. Ambos deflactados por el IPC.")
    svg, tab = grain_chart("Maíz", COL["maiz"], "Precio real del maíz al productor frente al internacional")
    f["maize"] = figure("maize", "Maíz: la misma relación, con un salto en 2021 y 2022", svg, tab,
                        f"<i>Nota.</i> Productor: FAOSTAT {cite('faostat')}, desde 2015. Internacional: maíz del Banco Mundial {cite('pink_sheet')} al dólar observado. Ambos en pesos de septiembre de 2026.")

    cx = (cot["date"].dt.year + (cot["date"].dt.month - 1) / 12).tolist()
    svg, tab = S.line_chart([dict(name="Trigo, poder comprador (mediana nacional)", label="Trigo Cotrisa", color=COL["trigo"], x=cx, y=cot["clp_t_real"].tolist(), width=2.6, dots=True)],
                            height=250, y_title="Miles de pesos de sept. de 2026 por tonelada", y_fmt=lambda v: es(v / 1000, 0), zero=False,
                            x_ticks=[2024.25, 2024.75, 2025.25, 2025.75, 2026.25, 2026.75], x_fmt=lambda v: f"{MONTHS[int(round((v % 1) * 12)) % 12]} {int(v)}",
                            alt="Precio real del trigo según Cotrisa", right=104)
    f["cotrisa"] = figure("cotrisa", "Trigo: precio pagado por los compradores (Cotrisa), campaña 2024 a 2026", svg, tab,
                          f"<i>Nota.</i> Mediana de las regiones con precio informado cada mes, en pesos de septiembre de 2026. {narrative('cotrisa')} solo publica la campaña vigente.")
    n["cot"] = dict(first=float(cot["clp_t_real"].iloc[0]), last=float(cot["clp_t_real"].iloc[-1]), min=float(cot["clp_t_real"].min()), last_date=cot["date"].iloc[-1])

    wa = D.wheat_area_price()
    save("trigo_superficie_y_precio", wa)
    wx = wa[(wa["year"] >= 2015) & (wa["year"] <= 2024)].set_index("year")
    i15 = wx.loc[2015]
    svg, tab = S.line_chart(
        [dict(name="Superficie sembrada", label="Superficie", color=COL["trigo"], x=wx.index.tolist(), y=(wx["area_ha"] / i15["area_ha"] * 100).tolist(), width=2.6),
         dict(name="Precio real al productor", label="Precio", color=COL["neutro"], x=wx.index.tolist(), y=(wx["price_real_clp_t"] / i15["price_real_clp_t"] * 100).tolist(), width=2.4, dash=True)],
        height=250, y_title="Índice, 2015 = 100", y_min=0, x_ticks=list(range(2015, 2025, 3)) + [2024], x_fmt=lambda v: str(int(v)),
        alt="Superficie de trigo y precio real al productor", right=104, y_fmt=lambda v: es(v, 0))
    f["wheat_area"] = figure("wheat_area", "La superficie de trigo bajó aun cuando el precio subió: no se explica solo por el precio", svg, tab,
                             f"<i>Nota.</i> Superficie: FAOSTAT {cite('faostat_cultivos')}. Precio: FAOSTAT productor, deflactado {cite('faostat')}. Elaboración propia.")
    n["wheat"] = dict(a15=float(wx.loc[2015, "area_ha"]), a24=float(wx.loc[2024, "area_ha"]), a22=float(wx.loc[2022, "area_ha"]),
                      y15=float(wx.loc[2015, "yield_kg_ha"]), y24=float(wx.loc[2024, "yield_kg_ha"]),
                      pk=int(wx["price_real_clp_t"].idxmax()))

    inp = D.inputs_vs_wheat()
    save("insumos_urea_dap_trigo", inp)
    svg, tab = S.line_chart(
        [dict(name="Urea", label="Urea", color=COL["maiz"], x=inp["year"].tolist(), y=inp["urea"].tolist(), width=2.4),
         dict(name="Fosfato diamónico (DAP)", label="DAP", color=COL["neutro"], x=inp["year"].tolist(), y=inp["dap"].tolist(), width=2.2, dash=True),
         dict(name="Trigo", label="Trigo", color=COL["trigo"], x=inp["year"].tolist(), y=inp["trigo"].tolist(), width=2.6)],
        height=260, y_title="Precio internacional en dólares, índice 2015-2017 = 100", y_min=0, x_ticks=list(range(2015, 2026, 2)), x_fmt=lambda v: str(int(v)),
        alt="Precios internacionales de urea, DAP y trigo", right=104, y_fmt=lambda v: es(v, 0))
    f["inputs"] = figure("inputs", "Los fertilizantes subieron más que el trigo: en 2025 el cultivo recibe menos por cada dólar de insumo", svg, tab,
                         f"<i>Nota.</i> Promedios anuales de precios nominales en dólares, solo años con los doce meses. Banco Mundial {cite('pink_sheet')}; elaboración propia.")
    ix = inp.set_index("year")
    n["inputs"] = dict(urea25=float(ix.loc[2025, "urea"]), trigo25=float(ix.loc[2025, "trigo"]), ratio25=float(ix.loc[2025, "urea_sobre_trigo"]),
                       ratio22=float(ix.loc[2022, "urea_sobre_trigo"]), dap25=float(ix.loc[2025, "dap"]), urea22=float(ix.loc[2022, "urea"]))

    svg, tab = S.line_chart([dict(name="Dólar observado, promedio anual", label="Pesos por dólar", color=COL["neutro"], x=macro["year"].tolist(), y=macro["usd_clp"].tolist(), width=2.4)],
                            height=220, y_title="Pesos chilenos por dólar", y_min=0, x_ticks=TICKS_LONG, alt="Dólar observado promedio anual", right=104)
    f["usd"] = figure("usd", "El dólar subió casi sin pausa en veinte años y pesa en todo lo que se compara con el exterior", svg, tab,
                      f"<i>Nota.</i> Promedio de los doce meses de cada año. {narrative('banco_central')}.")
    n["usd"] = dict(y2005=float(macro.set_index("year").loc[2005, "usd_clp"]), y2025=float(macro.set_index("year").loc[2025, "usd_clp"]))

    # ------------------------------------------------------------------ uva para vino
    wy = wine_year.copy()
    svg, tab = S.bar_chart(wy["year"].tolist(), wy["median_real"].tolist(), color=COL["uva"], height=210, y_title="Mediana real, pesos de sept. de 2026 (unidad no declarada)",
                           label_every=1, right=104, alt="Mediana anual del precio real de la uva para vino", name="Mediana real", highlight={2026: COL["neutro"]}, x_fmt=lambda v: str(int(v)))
    f["wine"] = figure("wine", "Uva para vino: el precio real tocó fondo en 2024 y recuperó una parte en 2025", svg, tab,
                       f"<i>Nota.</i> Todas las variedades y compradores. 2026 (gris) solo incluye cotizaciones hasta abril y 2020 solo 37 cotizaciones de 9 compradores. Fuente: elaboración propia con datos de {narrative('odepa_uva')}.")
    wv = wine_var.head(7)
    svg, tab = S.dumbbell([{"label": vname(r.variety), "before": r.price_before, "after": r.price_after, "change": r.change, "extra": f"{int(r.n_after)} datos"} for r in wv.itertuples()],
                          color=COL["uva"], x_title="Pesos de sept. de 2026 (unidad no declarada)", before_name="2020 y 2021", after_name="2024 y 2025",
                          alt="Precio real de las principales variedades viníferas")
    f["wine_var"] = figure("wine_var", "Las variedades finas cayeron mucho más que País, que ya se pagaba poco", svg, tab,
                           f"<i>Nota.</i> Mediana real por variedad; al menos 15 cotizaciones en cada período. Fuente: elaboración propia con datos de {narrative('odepa_uva')}.")
    n["wine_var_range"] = (float(wv["change"].max()), float(wv["change"].min()))
    n["wine_var_df"] = wv
    n["wine_year"] = wy.set_index("year")

    # ------------------------------------------------------------------ clima (exploración)
    n["climate"] = D.climate_cherry()

    # ------------------------------------------------------------------ portada: tablero con miniaturas
    def spark(values, color):
        return SX.sparkline(values, color=color)

    yrs = list(range(2010, 2026))
    board = [
        ("Cereza", "precio mayorista real", chg["cereza"]["change"], COL["cereza"], spark(_yearly(bys["price_real_clp_kg"], list(range(2005, 2026))), COL["cereza"])),
        ("Manzana", "precio mayorista real", chg["manzana"]["change"], COL["manzana"], spark(_yearly(ap["price_real_clp_kg"], list(range(2005, 2026))), COL["manzana"])),
        ("Uva de mesa", "precio mayorista real", chg["uva"]["change"], COL["uva"], spark(_yearly(uv["price_real_clp_kg"], list(range(2005, 2026))), COL["uva"])),
        ("Trigo", "precio real al productor", grain["Trigo"]["change"], COL["trigo"], spark(_yearly(real["Trigo"], list(range(2015, 2025))), COL["trigo"])),
        ("Maíz", "precio real al productor", grain["Maíz"]["change"], COL["maiz"], spark(_yearly(real["Maíz"], list(range(2015, 2025))), COL["maiz"])),
        ("Uva para vino", "precio real que pagan las viñas", wine_all["change"], COL["uva"], spark(wine_year["median_real"].tolist(), COL["uva"])),
    ]
    n["board"] = board
    del yrs
    return SimpleNamespace(n=n, f=f)
