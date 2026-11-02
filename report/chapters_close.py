"""Factores comunes, escenarios, conclusiones, límites y anexo."""
from __future__ import annotations

from types import SimpleNamespace

from helpers import caution_box, chapter, es, ficha, read_box, sg
from referencias import cite


def factors(X: SimpleNamespace) -> str:
    n, f = X.n, X.f
    cl = n["climate"]
    be0 = n["breakeven"][0.0]
    tb = cl["table"].set_index(["index", "outcome"])["spearman"]
    c_tmin, c_chill = tb[("tmin_spring", "Rendimiento nacional")], tb[("chill_hours", "Rendimiento nacional")]
    low = cl["low_chill"]
    low23 = float(low.loc[2023, "wholesale_change"])
    low_others = [float(low.loc[y, "wholesale_change"]) for y in (2006, 2005, 2016, 2001)]
    outs = ["Rendimiento nacional", "Exportación por hectárea", "Valor FOB por kilo", "Precio mayorista real"]
    from drivers import CLIMATE_LABELS
    body = ""
    for col, label in CLIMATE_LABELS.items():
        cells = ""
        for o in outs:
            v = tb[(col, o)]
            txt = es(v, 2)
            cells += f"<td class='r'>{'<b>' + txt + '</b>' if abs(v) >= cl['r_crit'] else txt}</td>"
        body += f"<tr><td>{label}</td>{cells}</tr>"
    clim_table = ("<table class='t'><thead><tr><th>Índice</th>" + "".join(f"<th class='r'>{o}</th>" for o in outs) + f"</tr></thead><tbody>{body}</tbody></table>")
    fx, w = n["fx_c"], n["bridge"]["Trigo"]
    a15, a24 = n["apple"]["area15"], n["apple"]["area24"]
    rows = [
        ("Cantidad plantada", "Cereza, manzana, uva de mesa, trigo", "Alta",
         f"Cereza: de 16 mil a 78 mil hectáreas. Manzana: {es(a15)} a {es(a24)} hectáreas. Trigo: 226 mil a 173 mil hectáreas sembradas. En los tres casos el precio se movió en sentido contrario a la cantidad."),
        ("Concentración del cliente", "Cereza; trigo y maíz", "Alta en cereza, media en cereales",
         "91% de la cereza va a China. En el trigo, el origen del grano importado cambió hacia Argentina desde 2024/25, pero el margen local frente a EE.UU. ya había caído antes."),
        ("Dólar", "Todos", "Alta",
         f"Amortigua la caída de la cereza en pesos ({es(abs(fx.loc[2025, 'idx_usd'] / 100 - 1) * 100)}% en dólares frente a {es(abs(fx.loc[2025, 'idx_clp_real'] / 100 - 1) * 100)}% en pesos reales) y fue neutro en términos reales para el trigo, porque subió casi lo mismo que la inflación."),
        ("Costos (insumos, flete, jornales)", "Cereza; trigo y maíz", "Media",
         f"El flete a Hong Kong pasó de 49% a 102% del retorno al productor. El costo laboral general subió {es((be0['labor_growth'] - 1) * 100)}% entre 2017 y 2025, frente a {es((be0['cpi_growth'] - 1) * 100)}% del IPC (no distingue la agricultura). El fertilizante subió más que el trigo. Con la ficha de ODEPA actualizada, la cereza de un huerto tipo se equilibra con un FOB de unos USD {es(be0['table'].set_index('season_start').loc[2025, 'breakeven_fob_usd_kg'], 1)} por kilo."),
        ("Clima", "Cereza, vino, cereales", "Media en el calendario; baja en el rendimiento",
         "Inviernos cálidos adelantan y concentran la cosecha. Con seis puntos de ERA5, solo dos de 24 correlaciones con el rendimiento superan el umbral del azar."),
    ]
    table = ("<table class='t'><thead><tr><th>Fuerza</th><th>Rubros</th><th>Evidencia</th><th>En qué se apoya</th></tr></thead><tbody>"
             + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows) + "</tbody></table>")
    main = f"""
<p>Cada rubro tiene su historia, pero cinco fuerzas se repiten. La tabla resume cuánta evidencia respalda cada una; &laquo;alta&raquo; significa que concuerdan datos propios y fuentes independientes, no que esté probada la causa.</p>
{table}
<h3>El dólar: un colchón que no siempre sirve</h3>
<p>El dólar observado promedió ${es(n['usd']['y2005'])} en 2005 y ${es(n['usd']['y2025'])} en 2025 (Figura @@R:usd@@), y llegó a un récord de $1.009 el 12 de julio de 2022 {cite('castro2022')}. Para el exportador de cereza, eso suavizó la caída del precio en dólares. Para el productor de trigo, en cambio, el efecto fue neutro: entre 2015-2017 y 2022-2024 el dólar subió {es((w['fx'] - 1) * 100)}% y la inflación {es((w['cpi'] - 1) * 100)}%. El dólar alto no equivale a mejores ingresos: depende de qué se vende, qué se compra y en qué moneda se pagan los costos. A la vez, el productor chileno tiene poco control sobre él, y su efecto se mezcla con el del precio internacional.</p>
{f['usd']}
<h3>El clima: mueve el calendario y deja indicios débiles en el rendimiento</h3>
<p>El clima actúa por tres vías distintas, y solo una se pudo observar en los datos de precios.</p>
<ul class='plain'>
<li><b>El año de cosecha.</b> En la cereza, un invierno cálido puede reducir la floración, y con ella la cosecha, o adelantar la maduración y concentrar los embarques. La prensa china vincula la baja floración de 2023 con una cosecha menor y precios altos, y el adelanto de 2025/26 con envíos más concentrados {cite('chen2026', 'freshplaza2026b')}. Los datos de este informe son coherentes con el primer caso (en 2023/24 el volumen exportado no creció y el precio subió), pero un solo año no prueba un patrón.</li>
<li><b>El agua.</b> Entre 2010 y 2022 Chile vivió una megasequía y la mayoría de las cuencas semiáridas llegó a estrés hídrico alto o extremo. Un estudio publicado en 2025 concluye que, en el largo plazo, el estrés hídrico del centro del país ha subido sobre todo por el mayor consumo de agua y, en menor medida, por una menor disponibilidad; en un escenario climático adverso, condiciones similares a las de la megasequía podrían volverse permanentes hacia fines de siglo {cite('boisier2025')}.</li>
<li><b>El frío invernal.</b> Los frutales caducos necesitan horas de frío para brotar bien. Una proyección con quince modelos climáticos estima que la mayoría de los sitios del centro de Chile perderá entre 10 y 15 porciones de frío hacia 2050, con riesgo de no cumplir los requerimientos de algunas especies en el norte {cite('fernandez2020')}.</li>
</ul>
<p>Para medirlo se calcularon seis índices agroclimáticos con ERA5 {cite('hersbach2020')} en seis puntos entre Rancagua y Chillán, y se contrastaron, para las temporadas 2000 a 2025, con cuatro resultados: el rendimiento nacional del cerezo y las toneladas exportadas por hectárea (ambos medidos contra su media móvil de cinco años, para quitar el envejecimiento de los huertos) y las variaciones anuales del valor de exportación y del precio mayorista real. Con {cl['n']} años, solo una correlación superior a {es(cl['r_crit'], 2)} (en valor absoluto) se distingue del azar al 5%. La tabla muestra la correlación de rangos de Spearman; en negrita, las que superan ese umbral.</p>
{clim_table}
<p>Dos de las {len(cl['table'])} combinaciones lo superan: la mínima media de primavera frente al rendimiento ({es(c_tmin, 2)}) y las horas de frío frente al rendimiento ({es(c_chill, 2)}). Con tantas pruebas, uno o dos resultados así aparecen por azar, de modo que no se afirma un efecto. Lo que les da verosimilitud es que el signo coincide con el mecanismo biológico (menos frío invernal y primaveras más cálidas, menor rendimiento) y con el caso de 2023, el tercer invierno con menos horas de frío de {len(cl['indices'].loc[2000:2025])}: ese año el volumen exportado se mantuvo y el precio mayorista real subió {es(low23 * 100)}%. Pero los otros cuatro inviernos más pobres en frío no repiten el patrón: el precio mayorista cambió {', '.join(f"{sg(v)}" for v in low_others)} en 2006, 2005, 2016 y 2001, y no hubo caída uniforme de la exportación por hectárea (Figura @@R:climate@@).</p>
{f['climate']}
{caution_box("<p>Que esta prueba no encuentre un efecto firme no significa que no exista. ERA5 es una reconstrucción de unos 25 kilómetros y, según el repositorio de clima del autor, detecta cerca de 23% de las heladas reales de Curicó, por lo que los índices de helada solo sirven para comparar años entre sí. Medir bien el efecto requeriría estaciones por huerto y cosechas por predio, que no son públicas.</p>")}
<h3>Lo que no se pudo medir</h3>
<p>El ingreso semanal de fruta a los packings, que muestra con anticipación cuánta fruta llega al mercado, no se publica en datos abiertos. Tampoco hay series públicas de costos de mano de obra por rubro, ni de precios al consumidor comparables con los mayoristas. Estas ausencias limitan la capacidad de anticipar cambios de corto plazo, y por eso las conclusiones de este informe son de tendencia.</p>"""
    aside = ("<p><strong>Cómo leer la tabla.</strong> &laquo;Alta&raquo; se usa cuando los datos propios y al menos una fuente independiente apuntan a lo mismo. No es una prueba de causa.</p>"
             "<p><strong>Clima.</strong> El clima viene de ERA5 (repositorio <code>chile-weather-forecasting</code>) para seis puntos entre Rancagua y Chillán; los resultados son exploratorios, no una evaluación del clima de una región.</p>")
    return chapter("factores", "Capítulo 5 | Factores comunes", "Qué mueve los precios: cinco fuerzas que cruzan los rubros",
                   "Cantidad, cliente, dólar, costos y clima. Dónde hay evidencia firme y dónde solo hipótesis.", main, aside)


def scenarios(X: SimpleNamespace) -> str:
    n = X.n
    se = n["se"]
    rows = [
        ("Cereza 2026/27", "Cosecha cercana a los 115 millones de cajas que proyecta la SNA y compra china sin cambios",
         f"Precio de exportación parecido al de 2025/26 (USD {es(se.loc[2025, 'fob_usd_kg'], 1)} por kilo)", "Valor unitario de la temporada, participación de China, arranques de huertos"),
        ("Cereza, si el clima recorta la cosecha", "Floración o fruta dañada por lluvia y granizo",
         f"Repunte de un año, como en 2023/24 (+{es((se.loc[2023, 'fob_usd_kg'] / se.loc[2022, 'fob_usd_kg'] - 1) * 100)}% en el valor de exportación), sin corregir el exceso de fondo", "Estimaciones de cajas en noviembre y diciembre"),
        ("Manzana", "La superficie sigue bajando cerca de 5% al año y los mercados nuevos (India) absorben la fruta",
         "Precio real alto, similar al actual", "Nuevas plantaciones, valor FOB por kilo, volumen a India"),
        ("Trigo y maíz", "El precio mundial se mantiene por sobre el de 2024 y el dólar no se debilita",
         "Alza parcial al productor, acotada por el origen argentino y las rebajas arancelarias", "Decretos de rebaja, importaciones por origen, precio del Pink Sheet"),
        ("Uva para vino", "Vendimia 2026 grande (+13%) con existencias aún altas y exportaciones a la baja",
         "Presión sobre el precio de la próxima temporada; recuperación solo si el inventario baja", "Existencias a diciembre de 2026, exportación de litros, hectáreas arrancadas"),
    ]
    table = ("<table class='t'><thead><tr><th>Caso</th><th>Supuesto</th><th>Qué pasaría con el precio</th><th>Qué vigilar</th></tr></thead><tbody>"
             + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows) + "</tbody></table>")
    main = f"""
<p>Un informe de precios sirve si ayuda a mirar hacia adelante, pero ningún dato de este informe permite pronosticar precios. Lo que sigue son escenarios condicionales: si se cumple el supuesto de la segunda columna, la dirección más probable es la de la tercera. No son recomendaciones de siembra ni de inversión.</p>
{table}
<p>Dos reglas de lectura. Primero, la oferta es lenta: lo que se planta hoy tarda años en producir a plena capacidad, por lo que la superficie actual de cerezo seguirá sumando fruta aunque nadie plante más. Segundo, el clima mueve un año, la superficie mueve una década. En el escenario de cosecha corta de la cereza, el alivio sería de un año si los huertos jóvenes siguen entrando en producción.</p>
<p>Para actualizar estas cifras basta con volver a ejecutar los comandos del anexo: los datos de ODEPA se publican a diario y el informe se reconstruye completo.</p>"""
    return chapter("escenarios", "Capítulo 6 | Hacia adelante", "Qué esperar: cinco escenarios y lo que conviene vigilar",
                   "Condicionales, no pronósticos: cada uno parte de un supuesto que se puede observar.", main, "", page_break=True)


def conclusions(X: SimpleNamespace) -> str:
    n = X.n
    w = n["bridge"]["Trigo"]
    se = n["se"]
    items = [
        ("La cantidad plantada explica más que cualquier otra cosa.",
         f"La cereza multiplicó casi por cinco su superficie y perdió precio; la manzana perdió casi un tercio de la suya y ganó precio. Lo plantado es lento de corregir, por eso el ajuste de la cereza vendrá más por arranques que por una buena cosecha."),
        ("Depender de un cliente pone en riesgo el precio, además del volumen.",
         f"Con 91% de la cereza hacia China, el valor por kilo cayó {es(abs(se.loc[2024, 'fob_usd_kg'] / se.loc[2023, 'fob_usd_kg'] - 1) * 100)}% en una temporada, de USD {es(se.loc[2023, 'fob_usd_kg'], 1)} a {es(se.loc[2024, 'fob_usd_kg'], 1)}, y no se recuperó al año siguiente."),
        ("El flete y la calidad deciden quién gana dentro de un mismo precio.",
         "Cuando el flete llega a 102% del retorno y solo cerca de 30% de la fruta cumple los calibres que se pagan, el precio promedio esconde productores con márgenes muy distintos."),
        ("Al trigo le llegó el alza mundial con descuento.",
         f"El precio internacional casi se duplicó en dólares, el dólar y la inflación se anularon y el productor recibió {sg(w['total'] - 1)} porque el margen local frente al trigo estadounidense pasó de {es(w['premium_base'], 2)} a {es(w['premium_recent'], 2)}. Las explicaciones disponibles (origen del grano, rebajas arancelarias, comprador concentrado) no se pudieron separar, y el margen ya había caído en 2022."),
        ("El vino toca fondo con inventario alto: la recuperación es frágil.",
         "El precio de la uva repuntó en 2025, pero la vendimia 2026 fue 13% mayor y las existencias superan una vendimia completa."),
        ("Lo que más falta no está en los precios: está en la oferta de corto plazo.",
         "Sin datos públicos de ingreso a packing ni de costos por rubro, las decisiones de corto plazo se toman con información privada, y eso limita lo que cualquier informe de precios, incluido este, puede anticipar."),
    ]
    body = "".join(f"<li><b>{a}</b> {b}</li>" for a, b in items)
    main = f"<ol class='verdict'>{body}</ol>"
    aside = "<p><strong>Para quien decide.</strong> Estas conclusiones describen tendencias de 10 años. Sirven para ordenar preguntas, no para fijar el precio de la próxima temporada.</p>"
    return chapter("conclusiones", "Conclusiones", "Seis conclusiones", "Lo que queda de los datos, en el orden en que importa.", main, aside, page_break=True)


def limits() -> str:
    main = """
<ul class='plain'>
<li><b>Cobertura del mayorista:</b> nueve regiones y solo días con transacciones. No es un censo nacional ni el precio que recibe el productor.</li>
<li><b>Kilos estimados:</b> el volumen de ODEPA viene en unidades de envase (cajas, bandejas, sacos). Se asume que así es, porque las medianas por tipo de envase lo respaldan, pero la fuente no lo declara. Se multiplica por el peso del envase solo cuando está escrito en la etiqueta.</li>
<li><b>Catastro frutícola:</b> mide regiones distintas cada año. Las superficies regionales se comparan solo entre las mismas regiones; para totales nacionales se usan ODEPA y FAOSTAT, que coinciden entre sí (76.447 y 77.766 hectáreas de cerezo).</li>
<li><b>FAOSTAT:</b> la serie de precios chilena cambia de base de medición antes de 2015; los cambios de largo plazo en cereales se miden desde ese año.</li>
<li><b>Valor unitario de exportación:</b> se calcula dividiendo el valor FOB por los kilos; no es un precio publicado ni distingue variedad. Las declaraciones recientes pueden ajustarse hasta seis meses después, por lo que 2025/26 es preliminar. El código aduanero cambió en 2012 y las series se empalman.</li>
<li><b>Ingreso por hectárea:</b> es ingreso bruto de exportación sobre la superficie de FAOSTAT, que incluye huertos sin producción plena; no descuenta costos.</li>
<li><b>Márgenes y costos:</b> las cifras de costos y retornos por kilo de cereza provienen de estimaciones del sector (GP Graders, Utilitas) que no se pudieron verificar con datos propios.</li>
<li><b>Causalidad:</b> las explicaciones propuestas son consistentes con los datos, no pruebas de causa. No se aisló el efecto del clima, de los jornales ni de los aranceles.</li>
<li><b>Fuentes de prensa:</b> son contexto. Cuando una nota y los datos oficiales difieren (por ejemplo, exportaciones por temporada y por año calendario), el informe usa ambas y las rotula.</li>
</ul>"""
    return chapter("limites", "Límites", "Lo que estos datos no permiten afirmar", "Nueve salvedades, con su efecto sobre la lectura.", main, "", page_break=False)


def annex() -> str:
    main = """
<p>Todo lo que aparece en este informe se puede reproducir. El repositorio separa el <b>código</b>, que está versionado, de los <b>datos descargados</b>, que pesan unos 2,8 GB y no se suben; en su lugar se versionan los resultados de cada figura como archivos CSV pequeños.</p>
<table class='t'><thead><tr><th>Qué</th><th>Dónde</th><th>Para qué</th></tr></thead><tbody>
<tr><td>Datos de cada figura</td><td><code>report/data/*.csv</code></td><td>Cada número del informe, auditable sin ejecutar nada</td></tr>
<tr><td>Informe HTML y PDF</td><td><code>report/dist/</code></td><td>Entregable final</td></tr>
<tr><td>Construcción del informe</td><td><code>report/*.py</code></td><td>Cifras, gráficos, texto y verificación de citas</td></tr>
<tr><td>Guía de redacción</td><td><code>docs/guia_de_redaccion_informes.md</code></td><td>Cómo se estructuran y redactan informes de mercado agrícola</td></tr>
<tr><td>Tablas analíticas</td><td><code>data/analysis/*.parquet</code></td><td>Panel mensual con precio real, kilos y variedad armonizada</td></tr>
<tr><td>Originales descargados</td><td><code>data/raw/</code></td><td>Evidencia con hash y manifiesto; no se versiona</td></tr>
<tr><td>Código del pipeline</td><td><code>src/materias_primas_chile/</code></td><td>Descarga, limpieza, conversión de unidades y análisis</td></tr>
</tbody></table>
<h3>Cómo reconstruir los datos y el informe</h3>
<pre>pip install -e ".[dev,parquet,grains,excel]"
mpchile ingest --start-year 1994 --end-year 2026
mpchile build
mpchile volume
mpchile macro
mpchile panel
mpchile supply
mpchile datasets
mpchile faostat
mpchile pinksheet
mpchile cotrisa
mpchile reference
python report/build_report.py --pdf</pre>
<p>El procesamiento de datos y la redacción se hicieron con asistencia de Claude (Anthropic). Las cifras provienen de las fuentes citadas y el código del repositorio permite verificarlas; las fuentes de prensa y los informes sectoriales fueron abiertos y leídos por separado antes de citarse. Los datos de ODEPA se publican con licencia Creative Commons Atribución; los de FAOSTAT con CC BY-IGO.</p>"""
    return chapter("anexo", "Anexo", "Datos y reproducibilidad", "Dónde están los datos y cómo reconstruir el informe.", main, "", page_break=True)
