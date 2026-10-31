"""Portada, resumen, guía de lectura y panorama."""
from __future__ import annotations

from types import SimpleNamespace

from helpers import caution_box, chapter, es, ficha, read_box, sg
from referencias import cite

AUTHOR = "Gustavo Felipe Campos Luna"  # nombre del autor para la portada; vacío = se omite
DATE_LONG = "31 de octubre de 2026"


def thesis_text(X: SimpleNamespace) -> str:
    n = X.n
    chg, grain = n["chg"], n["grain"]
    cer_drop = abs(chg["cereza"]["change"]) * 100
    return (
        f"<p class='thesis'>En los últimos diez años el campo chileno se partió en dos. Donde llegó más fruta de la que el mercado paga (cereza) o donde la gente compra menos "
        f"(vino), el precio real cayó cerca de {es(cer_drop)}%. Donde la oferta se achicó (manzana, uva de mesa) o donde el precio lo fija el mercado mundial (trigo, maíz), "
        f"subió entre {es(min(chg['uva']['change'], grain['Trigo']['change']) * 100)}% y {es(chg['manzana']['change'] * 100)}%. Casi nunca hubo una sola causa: casi siempre se sumaron cantidad, "
        f"cliente, dólar y costos.</p>")


def cover(X: SimpleNamespace) -> str:
    rows = []
    for name, sub, change, color, spark in X.n["board"]:
        rows.append(f"<li style='--k:{color}'><span class='nm'>{name}<small>{sub}</small></span><span class='pc'>{sg(change)}</span>{spark}</li>")
    who = f"<p><b>Autor</b><br>{AUTHOR}</p>" if AUTHOR else ""
    return (
        "<header class='cover'><div><p class='kicker'>Informe de mercado &nbsp;|&nbsp; Octubre de 2026</p>"
        "<h1>Qué subió y qué cayó en el campo chileno, y por qué</h1>"
        "<p class='sub'>Precios reales de cereza, manzana, uva, trigo y maíz, medidos en pesos de hoy, y las razones detrás de cada movimiento.</p>"
        f"<div class='byline'>{who}<p><b>Fecha</b><br>{DATE_LONG}</p>"
        "<p><b>Datos</b><br>ODEPA, Banco Central, FAOSTAT, Cotrisa, Banco Mundial</p>"
        "<p><b>Repositorio</b><br><code>precios-agricolas-chile</code></p></div></div>"
        "<div class='board'><h2>Cambio del precio real en la última década</h2><ol>" + "".join(rows) + "</ol></div></header>"
        f"<div class='abstract'>{thesis_text(X)}</div>")


def toc() -> str:
    items = [("resumen", "Lo esencial"), ("guia", "Cómo leer"), ("panorama", "Visión de conjunto"), ("cereza", "Cereza"), ("manzana", "Manzana y uva de mesa"),
             ("cereales", "Trigo y maíz"), ("vino", "Uva para vino"), ("factores", "Qué mueve los precios"), ("escenarios", "Qué esperar"),
             ("conclusiones", "Conclusiones"), ("limites", "Límites"), ("referencias", "Referencias"), ("anexo", "Anexo")]
    return "<nav class='toc' aria-label='Contenido'>" + "".join(f"<a href='#{a}'>{b}</a>" for a, b in items) + "</nav>"


def summary(X: SimpleNamespace) -> str:
    n = X.n
    chg, grain, ex, se, bridge = n["chg"], n["grain"], n["ex"], n["se"], n["bridge"]["Trigo"]
    cer_drop = abs(chg["cereza"]["change"]) * 100
    p15, p24, q15, q24 = n["apple"]["p15"], n["apple"]["p24"], n["apple"]["prod15"], n["apple"]["prod24"]
    items = f"""<ol class='findings'>
<li><div><span class='h'>La cereza vende más que nunca y recibe menos por cada kilo.</span>
<p>En el mayorista el precio real bajó {es(cer_drop)}% entre 2014/17 y 2022/25. En la exportación, el valor por kilo se movió entre USD {es(n['fob_peak_seasons'][0], 1)} y {es(n['fob_peak_seasons'][1], 1)} en todas las temporadas de 2009 a 2023 y cayó a USD {es(se.loc[2024, 'fob_usd_kg'], 2)} en 2024/25, nivel en que se mantuvo en 2025/26 (cifra aún preliminar). La causa principal es de oferta: las hectáreas se multiplicaron casi por cinco desde 2013 y cerca de nueve de cada diez cajas van a un solo país {cite('decofrut2025', 'inia2025', 'valenzuela2026')}. El flete agravó el cuadro: enviar un kilo a Hong Kong pasó de absorber 49% del retorno libre al productor en 2017/18 a 102% en 2024/25 {cite('mundomaritimo2025')}.</p></div></li>
<li><div><span class='h'>En la manzana y la uva de mesa pasa lo contrario: se cosecha menos y se paga más.</span>
<p>La producción nacional de manzana bajó {es((1 - q24 / q15) * 100)}% entre 2015 y 2024 y el precio real mayorista subió {es(chg['manzana']['change'] * 100)}% (promedios de 2014/16 y 2022/24). En los treinta años de datos, un año con menos cosecha tendió a traer un precio más alto en casi la misma proporción (correlación {es(n['apple']['flex']['corr'], 2)}). La uva de mesa tocó en 2023/24 su superficie más baja desde 1999 {cite('guzman2024')}.</p></div></li>
<li><div><span class='h'>Al trigo chileno le llegó solo una parte del alza mundial, y esa parte se ha ido reduciendo.</span>
<p>Entre 2015/17 y 2022/24 el precio internacional del trigo casi se duplicó en dólares, pero el pago al productor chileno subió {es((bridge['total'] - 1) * 100)}% en pesos reales: el dólar y la inflación se compensaron casi por completo y el margen local cayó de {es(bridge['premium_base'], 2)} a {es(bridge['premium_recent'], 2)} veces el precio de referencia. Es consistente con un mercado que desde la campaña 2024/25 compra mucho más trigo argentino y con un sistema de rebajas arancelarias que acota el precio interno {cite('usda2026', 'hacienda2026')}.</p></div></li>
<li><div><span class='h'>La uva para vino es una crisis de demanda con inventario alto, y 2024 fue el piso.</span>
<p>El consumo chileno cayó 17,5% en 2025 {cite('vinetur2026')}, las bodegas cerraron ese año con 1.121 millones de litros guardados y las exportaciones de enero a julio de 2026 bajaron 13,3% en volumen {cite('buzzetti2026')}. El precio real de la uva recuperó una parte en 2025, pero la vendimia 2026 fue 13,2% mayor que la anterior y el peso de esa oferta aún no aparece en los datos de precio {cite('buzzetti2026')}.</p></div></li>
<li><div><span class='h'>El dólar amortiguó, los costos apretaron y el clima movió el calendario.</span>
<p>Con el dólar a $951 en 2025 frente a $495 en 2013, la caída en pesos del valor de exportación de la cereza fue menor que en dólares. Pero el fertilizante subió más que el trigo y el flete más que la fruta. El clima pesó sobre todo en el calendario: inviernos cálidos adelantaron la cosecha y concentraron los embarques {cite('chen2026', 'freshplaza2026b')}. Con datos climáticos de dos ciudades no se pudo medir un efecto claro sobre el rendimiento.</p></div></li>
</ol>"""
    unknown = read_box(
        "<p>No existe un dato público del ingreso semanal de fruta a los packings, que sería la medida más directa de la oferta que viene. Este informe la reemplaza con las hectáreas plantadas, "
        "la producción anual y las exportaciones mes a mes. Sirven para entender la tendencia, no para anticipar una semana puntual de la temporada.</p>", "Lo que no se pudo medir")
    aside = (ficha("En una mirada", [("Precio real cereza", sg(chg["cereza"]["change"])), ("Precio real manzana", sg(chg["manzana"]["change"])),
                                     ("Trigo al productor", sg(grain["Trigo"]["change"])), ("Uva para vino", sg(n["wine_all"]["change"]))], neg=(0, 3))
             + "<p><strong>Cómo se mide.</strong> Todos los precios están en pesos de septiembre de 2026, es decir, descontada la inflación.</p>"
               "<p><strong>Qué no es.</strong> No es una recomendación de siembra ni de inversión: describe lo que muestran los datos y las fuentes citadas.</p>")
    return chapter("resumen", "Lo esencial", "Dos grupos, cinco explicaciones", "Si solo tiene un minuto, lea esta página.", items + unknown, aside, page_break=True)


def guide(X: SimpleNamespace) -> str:
    n = X.n
    cer = n["cer"]
    main = f"""
<p>Un precio agrícola puede significar cosas muy distintas según dónde se mida y en qué pesos. Antes de los resultados conviene fijar cuatro distinciones, porque la mayoría de las discusiones sobre &laquo;cuánto vale la cereza&raquo; mezclan varias de ellas.</p>
<h3>Pesos de hoy, no pesos de cada año</h3>
<p>Un precio que sube 40% en diez años puede valer menos que antes si la inflación acumulada fue mayor. Todos los precios de este informe están expresados en pesos de septiembre de 2026, ajustados mes a mes con el IPC del Banco Central {cite('banco_central')}. El ajuste cambia la lectura: el precio mayorista de la cereza bajó {es(abs(cer['nom_change']) * 100)}% medido en pesos de cada año y {es(abs(n['chg']['cereza']['change']) * 100)}% medido en pesos de hoy (Figura @@R:inflation@@).</p>
{X.f['inflation']}
<h3>Cuatro niveles de precio</h3>
<table class='t'><thead><tr><th>Nivel</th><th>Qué es</th><th>Quién lo informa</th></tr></thead><tbody>
<tr><td><b>Productor</b></td><td>Lo que recibe quien cultiva, por lo general después de descontar embalaje, flete y comisiones.</td><td>FAOSTAT, Cotrisa, ODEPA (uva para vino)</td></tr>
<tr><td><b>FOB</b></td><td>Valor de la fruta puesta en el barco, antes del flete internacional. Incluye embalaje y logística local.</td><td>Aduanas, vía ODEPA</td></tr>
<tr><td><b>Mayorista</b></td><td>Precio de venta en mercados como Lo Valledor, para el consumo interno.</td><td>ODEPA</td></tr>
<tr><td><b>Consumidor</b></td><td>Precio de góndola o feria. Este informe no lo mide.</td><td>INE, ODEPA</td></tr>
</tbody></table>
<h3>Temporada y año calendario</h3>
<p>La cereza se cosecha entre noviembre y febrero, de modo que una temporada cruza dos años. ODEPA la rotula &laquo;2024/25&raquo;. Las cifras de exportación y de producción por año calendario no coinciden con las de temporada: en este informe cada gráfico dice cuál usa.</p>
<h3>Dos períodos, no un punto</h3>
<p>Cada comparación enfrenta el promedio de tres temporadas al inicio de la década pasada con el promedio de tres temporadas recientes. Así el resultado no depende de que un año haya sido especialmente bueno o malo. Cuando el año escogido cambia la conclusión, el informe lo dice.</p>
<h3>De dónde salen los datos</h3>
<table class='t'><thead><tr><th>Fuente</th><th>Qué aporta</th><th>Nivel</th><th>Cobertura</th></tr></thead><tbody>
<tr><td>ODEPA, precios mayoristas {cite('odepa_mayorista')}</td><td>Precio y volumen por variedad, calidad y origen</td><td>Mayorista, 9 regiones</td><td>1994 a 2026</td></tr>
<tr><td>ODEPA, comercio exterior {cite('odepa_comex')}</td><td>Valor y kilos exportados, mes a mes</td><td>FOB</td><td>1998 a 2026</td></tr>
<tr><td>ODEPA y CIREN, catastro {cite('ciren_catastro')}</td><td>Hectáreas por especie y variedad</td><td>Oferta</td><td>2008 a 2025</td></tr>
<tr><td>ODEPA, uva para vinificación {cite('odepa_uva')}</td><td>Precio que pagan las viñas</td><td>Productor</td><td>2020 a 2026</td></tr>
<tr><td>FAOSTAT, precios {cite('faostat')}</td><td>Precio anual al productor de cereales</td><td>Productor</td><td>2015 a 2024 (comparable)</td></tr>
<tr><td>FAOSTAT, cultivos {cite('faostat_cultivos')}</td><td>Superficie, producción y rendimiento</td><td>Oferta</td><td>1961 a 2024</td></tr>
<tr><td>Cotrisa {cite('cotrisa')}</td><td>Precio de compra de trigo por región</td><td>Productor</td><td>Desde 2024</td></tr>
<tr><td>Banco Mundial, Pink Sheet {cite('pink_sheet')}</td><td>Precios internacionales de granos y fertilizantes</td><td>Internacional</td><td>1960 a 2026</td></tr>
<tr><td>Banco Central {cite('banco_central')}</td><td>IPC y dólar observado</td><td>Macroeconomía</td><td>1928 a 2026</td></tr>
</tbody></table>
<h3>Palabras del sector</h3>
<table class='t'><thead><tr><th>Término</th><th>Significado</th></tr></thead><tbody>
<tr><td><b>Packing</b></td><td>Planta donde se selecciona, embala y enfría la fruta antes de exportarla.</td></tr>
<tr><td><b>Consignación</b></td><td>Venta en que el exportador despacha la fruta sin precio fijado y liquida al productor lo que logra en destino, menos costos.</td></tr>
<tr><td><b>IVV</b></td><td>Informe de variación de valor: ajuste posterior al valor declarado de una exportación, hasta seis meses después del embarque.</td></tr>
<tr><td><b>Calibre</b></td><td>Diámetro del fruto en milímetros; para la cereza de exportación importan los de 28 mm o más.</td></tr>
<tr><td><b>Retorno al productor</b></td><td>Lo que queda para el huerto después de embalaje, flete, comisiones y otros costos de comercialización.</td></tr>
</tbody></table>
<p>Los resultados se calcularon con un procesamiento reproducible de los datos oficiales; la noticia y los informes sectoriales se usan como contexto y para explicar causas, siempre citados. El anexo detalla cómo reconstruir todo.</p>"""
    aside = ("<p><strong>La regla de lectura.</strong> Antes de comparar dos precios, pregunte tres cosas: ¿en qué moneda?, ¿en qué punto de la cadena? y ¿en qué período?</p>"
             "<p><strong>Fuentes de contexto.</strong> Las notas de prensa y los informes sectoriales se abrieron y leyeron antes de citarlas; las cifras que se toman de ellas se parafrasean y llevan su cita.</p>")
    return chapter("guia", "Cómo leer este informe", "Cuatro distinciones antes de empezar", "Un precio sin su moneda, su nivel y su período dice poco.", main, aside, page_break=True)


def overview(X: SimpleNamespace) -> str:
    n = X.n
    chg, grain = n["chg"], n["grain"]
    main = f"""
{X.f['overview']}
<p>Los ocho productos se agrupan por la razón que mejor explica su movimiento, no por su especie:</p>
<ul class='plain'>
<li><b>Más oferta que mercado: cereza.</b> El precio real bajó {es(abs(chg['cereza']['change']) * 100)}% en el mayorista mientras el volumen mayorista se duplicó y la exportación se multiplicó. El problema es de cantidad y de dependencia de un cliente.</li>
<li><b>Menos demanda y mucho inventario: uva para vino.</b> Bajó {es(abs(n['wine_all']['change']) * 100)}% entre 2020/21 y 2024/25. El consumo cae y las bodegas guardan más vino del que venden.</li>
<li><b>Menos oferta local: manzana y uva de mesa.</b> Subieron {es(chg['manzana']['change'] * 100)}% y {es(chg['uva']['change'] * 100)}%. Hay menos huertos, y la fruta que queda se vende mejor.</li>
<li><b>Precio fijado afuera: trigo, maíz y arroz.</b> Siguen al mercado internacional y al dólar. El trigo y el maíz subieron {es(grain['Trigo']['change'] * 100)}% y {es(grain['Maíz']['change'] * 100)}%, pero menos que la referencia mundial.</li>
</ul>
<p>La cereza y la manzana son, en cierto sentido, el mismo problema visto desde lados opuestos. En una se plantó mucho más rápido de lo que el mercado creció; en la otra se arrancó, por baja rentabilidad, casi una quinta parte de las hectáreas en tres años {cite('munoz2025', 'usda2025')}. Los capítulos siguientes explican cada caso con sus causas y con lo que podría cambiarlas.</p>"""
    aside = ("<p><strong>Lectura rápida.</strong> Las barras a la derecha del cero son productos que hoy valen más en pesos reales; las de la izquierda, que valen menos.</p>"
             "<p><strong>Ojo.</strong> Los períodos no son idénticos entre productos: dependen de cuántos años de datos comparables existen.</p>")
    return chapter("panorama", "Visión de conjunto", "Ocho precios, una misma vara", "La comparación en pesos de hoy ordena el campo en cuatro grupos.", main, aside, page_break=True)
