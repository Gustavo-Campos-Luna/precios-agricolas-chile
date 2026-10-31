"""Capítulos de cereales y de uva para vino."""
from __future__ import annotations

from types import SimpleNamespace

from helpers import MONTHS_FULL, caution_box, chapter, es, ficha, read_box, sg
from referencias import cite


def _bridge_table(n: dict) -> str:
    b = n["bridge"]
    rows = [("Precio internacional en dólares", "usd", False), ("Dólar", "fx", False), ("Inflación (se divide)", "cpi", True),
            ("Margen local frente al internacional", "premium", False), ("Cambio total del precio real al productor", "total", False)]
    body = ""
    for label, key, inv in rows:
        cells = "".join(f"<td class='r'>x{es(1 / b[g][key] if inv else b[g][key], 2)}</td>" for g in ("Trigo", "Maíz"))
        bold = " style='font-weight:700'" if key == "total" else ""
        body += f"<tr{bold}><td>{label}</td>{cells}</tr>"
    return ("<table class='t'><thead><tr><th>Factor (2015-2017 a 2022-2024)</th><th class='r'>Trigo</th><th class='r'>Maíz</th></tr></thead>"
            f"<tbody>{body}</tbody></table>")


def grains(X: SimpleNamespace) -> str:
    n, f = X.n, X.f
    w, m = n["bridge"]["Trigo"], n["bridge"]["Maíz"]
    grain = n["grain"]
    wh, inp, cot = n["wheat"], n["inputs"], n["cot"]
    lo, hi = n["wheat_ratio"]
    main = f"""
<h3>Quién se quedó con el alza</h3>
<p>Entre 2015/17 y 2022/24 el precio internacional del trigo se multiplicó por {es(w['usd'], 2)} en dólares. Al productor chileno le llegó un alza mucho menor: {es((w['total'] - 1) * 100)}% en pesos reales. La diferencia se puede repartir con exactitud entre cuatro factores que se multiplican (Figura @@R:bridge@@). El dólar subió {es((w['fx'] - 1) * 100)}% y la inflación {es((w['cpi'] - 1) * 100)}%, de modo que en términos reales el tipo de cambio quedó neutro. Lo que cambió fue el cuarto factor: la relación entre el precio que recibe el productor y el de referencia internacional, convertido a pesos reales, cayó de {es(w['premium_base'], 2)} a {es(w['premium_recent'], 2)}. En 2015-2017 el trigo chileno se pagaba {es((w['premium_base'] - 1) * 100)}% sobre esa paridad con el trigo estadounidense; en 2022-2024 se pagó {es((1 - w['premium_recent']) * 100)}% bajo ella. En el maíz ocurre lo mismo, más suave: ese margen pasó de {es(m['premium_base'], 2)} a {es(m['premium_recent'], 2)}.</p>
{f['bridge']}
{_bridge_table(n)}
<p>Esto contradice la idea corriente de que, como el trigo subió tanto en el mundo, el productor local se benefició en la misma proporción. Se benefició, pero con descuento, y el descuento creció.</p>

<h3>Por qué se achicó el margen local</h3>
<p>Los datos de precio no bastan para atribuir la causa, pero hay tres explicaciones que las fuentes permiten sostener, con distinto grado de certeza.</p>
<ol class='plain'>
<li><b>Cambió el origen del trigo importado (certeza media).</b> La referencia de este análisis es el trigo duro rojo de invierno de Estados Unidos, el que cotiza el Banco Mundial. Pero Chile compra cada vez menos allá: en la campaña 2024/25 las importaciones subieron 29,9%, a 1,26 millones de toneladas, y las de origen argentino pasaron de 104 mil a 558 mil toneladas, mientras las estadounidenses bajaron de 356 mil a 262 mil y las uruguayas de 183 mil a 35 mil {cite('usda2026')}. Si el trigo argentino llega más barato, el precio chileno sigue a ese y no al estadounidense, y frente a este último la &laquo;prima&raquo; cae. Es coherente con los datos; no se midió con precios argentinos.</li>
<li><b>El Estado acota el traspaso (certeza media).</b> Chile usa rebajas arancelarias para mantener los precios internos dentro de un margen razonable respecto de los internacionales. El decreto exento 285 de octubre de 2026 rebaja US$166,05 por tonelada los derechos ad valorem de varias clases de trigo, entre ellas el duro rojo de invierno, entre el 16 de octubre y el 15 de diciembre {cite('hacienda2026')}. En la práctica abarata la importación y limita cuánto del alza mundial llega al precio interno. No se midió cuánto de la caída del margen entre 2015-2017 y 2022-2024 se debe a este mecanismo.</li>
<li><b>El comprador es más concentrado (certeza baja).</b> La cadena del trigo reúne 17.444 productores que venden a 71 molinos {cite('soto2025')}. No se midió si eso pesó en el precio, pero es una asimetría de negociación que ayuda a entender por qué el productor no recupera el margen.</li>
</ol>

<h3>Menos hectáreas, aunque el precio subió</h3>
<p>Un precio más alto debería atraer más siembra. En el trigo pasó lo contrario. Según FAOSTAT, la superficie bajó de {es(wh['a15'])} hectáreas en 2015 a {es(wh['a24'])} en 2024, con un mínimo de {es(wh['a22'])} en 2022, justo el año en que el precio real al productor llegó a su máximo (Figura @@R:wheat_area@@). Las cifras de ODEPA para el trigo panadero y candeal van en la misma dirección: 226 mil hectáreas sembradas en 2020/21 y 173 mil en 2024/25, 12,7% menos que un año antes {cite('contreras_h2026')}. El rendimiento no explica la caída: se mantuvo cerca de {es(wh['y15'] / 1000, 1)} y {es(wh['y24'] / 1000, 1)} toneladas por hectárea. El USDA espera que la tendencia siga: para 2026/27 proyecta una producción de trigo de 1,15 millones de toneladas (1,7% menos) e importaciones de 1,30 millones (3,7% menos) {cite('usda2026')}.</p>
{f['wheat_area']}
<p>¿Por qué no siembra más el agricultor cuando el precio sube? Una parte de la respuesta está en los costos, y otra en la demanda. La urea depende de los precios de la energía, en particular del gas natural, y Chile depende de las importaciones, de modo que su precio interno queda expuesto al tipo de cambio, al flete marítimo y a los plazos de contratación {cite('causa2026')}. Los precios del Banco Mundial muestran que los fertilizantes se encarecieron más que el trigo: con base 100 en 2015-2017, la urea estaba en {es(inp['urea25'])} y el DAP en {es(inp['dap25'])} en 2025, mientras el trigo estaba en {es(inp['trigo25'])} (Figura @@R:inputs@@). Una tonelada de trigo compra hoy {es((1 - 1 / inp['ratio25']) * 100)}% menos urea que en 2015-2017; en el máximo de 2022 la relación era de {es(inp['ratio22'], 2)} y en 2025 es de {es(inp['ratio25'], 2)}. La demanda también pesa: la disponibilidad aparente de harina por habitante bajó de 80 a 69 kilos entre 2017 y 2024 (13% menos), una caída que ODEPA vincula con cambios en las preferencias de los consumidores {cite('soto2025')}.</p>
{f['inputs']}

<h3>El episodio de 2022 y el tramo reciente</h3>
<p>Tras la invasión de Ucrania, el índice de precios de cereales de la FAO subió 17,1% solo en marzo de 2022; Rusia y Ucrania concentraban cerca de 30% de las exportaciones mundiales de trigo y 20% de las de maíz {cite('fao2022')}. El Banco Mundial reportó que los precios de los alimentos estaban más de 80% sobre los de dos años antes, con los insumos (energía y fertilizantes) como causa principal {cite('baffes2022')}. En Chile, el trigo &laquo;intermedio país&raquo; pasó de 195 pesos por kilo en enero de 2021 a 401 en mayo de 2022 y a 238 en febrero de 2026, en valores nominales {cite('soto2026')}.</p>
{f['wheat']}
<p>La serie de Cotrisa, que informa desde 2024 el precio de compra por región, muestra el tramo reciente: el trigo real pasó de {es(cot['first'] / 1000)} mil pesos por tonelada al inicio de la serie a un mínimo cercano a {es(cot['min'] / 1000)} mil, y en {MONTHS_FULL[cot['last_date'].month - 1]} de {cot['last_date'].year} marcó {es(cot['last'] / 1000)} mil (Figura @@R:cotrisa@@). La FAO ubicó en septiembre de 2026 el trigo en su nivel más alto desde agosto de 2023 {cite('fao_fpi')}.</p>
{f['cotrisa']}
{f['maize']}
<p>El maíz se explica casi igual, con un peso aún mayor de las importaciones: el USDA proyecta para 2026/27 una producción de 525 mil toneladas (4,5% menos) frente a importaciones de 2,6 millones, cinco veces lo que se cosecha, para alimentar a las industrias porcina y avícola {cite('usda2026')}. En 2018, ODEPA estimaba que cerca de 60% del maíz consumido era importado, casi todo desde Argentina, junto con 39% del trigo y 55% del arroz elaborado {cite('laval2018')}.</p>
{read_box(f"<p>El precio interno de los cereales se parece más a un precio de importación que a un precio de oferta local. Por eso importan el dólar, el origen del trigo y el arancel. Entre 2015 y 2024 el cuociente entre el precio al productor chileno y el internacional en pesos osciló entre {es(lo, 2)} y {es(hi, 2)} para el trigo: ya no es un precio con prima, pero tampoco una desconexión.</p>", "En una frase")}"""
    aside = (ficha("Trigo en cifras", [
        ("Precio internacional (USD)", f"x{es(w['usd'], 2)}"),
        ("Precio real al productor", sg(w["total"] - 1)),
        ("Margen local", f"{es(w['premium_base'], 2)} a {es(w['premium_recent'], 2)}"),
        ("Superficie sembrada (ODEPA)", "226 a 173 mil ha"),
        ("Importaciones 2024/25", "1,26 Mt (+30%)"),
        ("Urea frente a trigo, 2025", f"x{es(inp['ratio25'], 2)}")], neg=(3, 5))
        + "<p><strong>Por qué solo desde 2015.</strong> La serie de precios de FAOSTAT para Chile cambia de base de medición antes de ese año; usarla completa inflaría los cambios.</p>"
          "<p><strong>Rebaja arancelaria.</strong> Es un mecanismo habitual para amortiguar el traspaso del precio mundial al interno; el decreto vigente rige hasta el 15 de diciembre de 2026.</p>")
    return chapter("cereales", "Capítulo 3 | Trigo y maíz", "Trigo y maíz: el precio lo fija el mundo, y al productor le llega cada vez menos del alza",
                   f"El trigo casi duplicó su precio internacional en dólares y al productor chileno le llegó {es((w['total'] - 1) * 100)}% más en pesos reales. La diferencia tiene explicaciones concretas.", main, aside, product="trigo")


def wine(X: SimpleNamespace) -> str:
    n, f = X.n, X.f
    wa, wy, wv = n["wine_all"], n["wine_year"], n["wine_var_df"]
    pais = float(wv[wv["variety"] == "paismissioncriolla"]["change"].iloc[0])
    finas = wv[wv["variety"] != "paismissioncriolla"]["change"]
    peak, floor, y25, y26 = wy.loc[2022, "median_real"], wy.loc[2024, "median_real"], wy.loc[2025, "median_real"], wy.loc[2026, "median_real"]
    main = f"""
<h3>Qué muestran los precios</h3>
<p>La mediana real de las cotizaciones de uva para vino pasó de {es(wa['before'])} a {es(wa['after'])} pesos entre 2020-2021 y 2024-2025 ({sg(wa['change'])}). Esa cifra de dos períodos oculta la trayectoria (Figura @@R:wine@@). La mediana real llegó a un máximo de {es(peak)} pesos en 2022, cayó {es((1 - floor / peak) * 100)}% hasta {es(floor)} en 2024 y subió {es((y25 / floor - 1) * 100)}% en 2025, a {es(y25)}. En 2026, con cotizaciones hasta abril, es de {es(y26)}. Es decir, en 2025 y 2026 el precio real sigue entre {es((1 - y25 / wa['before']) * 100)}% y {es((1 - y26 / wa['before']) * 100)}% por debajo de 2020-2021, pero lejos del piso de 2024. Un diario económico informó que la uva tinta se pagó cerca de $100 a $120 por kilo en 2024 y se acercaría a $220 a $240 en 2025 {cite('isla2025')}, lo que respalda la tendencia y la unidad (pesos por kilo), que ODEPA no declara.</p>
{f['wine']}
<p>La caída no fue pareja. Las variedades finas bajaron entre {es(abs(finas.max()) * 100)}% y {es(abs(finas.min()) * 100)}% entre 2020-2021 y 2024-2025, mientras que País, que ya se pagaba poco, bajó {es(abs(pais) * 100)}% (Figura @@R:wine_var@@). Las fuentes consultadas no explican esa diferencia, que queda como una pregunta abierta.</p>
{f['wine_var']}

<h3>Por qué: se bebe menos y sobra vino</h3>
<p>El consumo chileno de vino cayó 17,5% en 2025 y 39,5% en diez años {cite('vinetur2026')}. El fenómeno no es solo local: según la OIV, el consumo mundial fue de 208 millones de hectolitros en 2025, 2,7% menos que en 2024, mientras la producción llegó a 227 millones, una cifra apenas sobre el mínimo histórico del año anterior; la superficie mundial de viñedos bajó por sexto año consecutivo, a 7,0 millones de hectáreas {cite('oiv2026')}. Hay más vino disponible del que se consume, en Chile y en el mundo.</p>
<p>En Chile eso se tradujo en inventarios. Al 31 de diciembre de 2025 las bodegas guardaban 1.120,9 millones de litros, 13,3% menos que un año antes pero aún más que toda la vendimia de 2026 (949,5 millones de litros) {cite('buzzetti2026')}. Las exportaciones de enero a julio de 2026 fueron de 360,2 millones de litros, 13,3% menos en volumen y 10,6% menos en valor que en igual período de 2025 {cite('buzzetti2026')}. En 2025 el valor exportado total fue de USD 1.315 millones, 3,6% menos que en 2024 {cite('pelfort2026')}. La respuesta de la industria fue arrancar viñas: la superficie de viníferas cerró 2025 en 110.768 hectáreas, un 5,3% menos que en 2024 {cite('emol2026')}.</p>

<h3>Qué mirar ahora</h3>
<p>La recuperación de 2025 coincide con la salida de superficie y con una baja del inventario, pero el dato nuevo va en sentido contrario: la vendimia 2026 fue 13,2% mayor que la de 2025 {cite('buzzetti2026')}. Más uva en un año de ventas en retroceso presiona los precios de la próxima temporada, que todavía no aparecen en la base de ODEPA. Las señales a seguir son el nivel de existencias a diciembre de 2026, el volumen exportado y cuánta superficie adicional se arranca.</p>
{read_box("<p>Es una historia de demanda débil y de stock acumulado, distinta de la de la cereza, donde sobra fruta fresca para un solo cliente, y de la de la manzana, donde se achicó la oferta. El piso de 2024 no garantiza que el precio haya vuelto para quedarse.</p>", "En una frase")}
{caution_box("<p>ODEPA no declara la unidad del precio de la uva vinífera: se asume pesos por kilo con apoyo de una fuente periodística. Además hay pocas cotizaciones en 2020 (37 de 9 compradores) y la lista de compradores cambia entre años, de modo que parte del cambio puede deberse a quién informa. Es el resultado menos firme de este informe.</p>")}"""
    aside = (ficha("La uva vinífera en cifras", [
        ("Precio real 2020/21 a 2024/25", sg(wa["change"])),
        ("Piso de 2024 a 2025", sg(y25 / floor - 1)),
        ("Consumo en Chile, 2025", "−17,5%"),
        ("Existencias a dic. 2025", "1.121 M litros"),
        ("Vendimia 2026", "+13,2%"),
        ("Exportación ene-jul 2026", "−13,3% en litros")], neg=(0, 2, 5))
        + "<p><strong>Dato.</strong> El consumo mundial de vino también cae (2,7% en 2025, según la OIV), por lo que la crisis chilena no es solo local.</p>"
          "<p><strong>Lectura prudente.</strong> Con tan pocas cotizaciones en 2020, el cambio entre períodos debe leerse como un orden de magnitud.</p>")
    return chapter("vino", "Capítulo 4 | Uva para vino", "Uva para vino: el piso fue 2024, pero el vino sigue sobrando",
                   f"El precio real que pagan las viñas cayó {es(abs(wa['change']) * 100)}% entre 2020-21 y 2024-25. La vendimia 2026, 13% mayor, pone a prueba la recuperación.", main, aside, product="vino")
