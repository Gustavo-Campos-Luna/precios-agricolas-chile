"""Factores comunes, escenarios, conclusiones, límites y anexo."""
from __future__ import annotations

from types import SimpleNamespace

from helpers import caution_box, chapter, es, ficha, read_box, sg
from referencias import cite


def factors(X: SimpleNamespace) -> str:
    n, f = X.n, X.f
    cl = n["climate"]
    fx, w = n["fx_c"], n["bridge"]["Trigo"]
    a15, a24 = n["apple"]["area15"], n["apple"]["area24"]
    rows = [
        ("Cantidad plantada", "Cereza, manzana, uva de mesa, trigo", "Alta",
         f"Cereza: de 16 mil a 78 mil hectáreas. Manzana: {es(a15)} a {es(a24)} hectáreas. Trigo: 226 mil a 173 mil hectáreas sembradas. En los tres casos el precio se movió en sentido contrario a la cantidad."),
        ("Concentración del cliente", "Cereza; trigo y maíz", "Alta en cereza, media en cereales",
         "91% de la cereza va a China. En el trigo, el origen del grano importado cambió hacia Argentina y el margen local frente a EE.UU. cayó."),
        ("Dólar", "Todos", "Alta",
         f"Amortigua la caída de la cereza en pesos ({es(abs(fx.loc[2025, 'idx_usd'] / 100 - 1) * 100)}% en dólares frente a {es(abs(fx.loc[2025, 'idx_clp_real'] / 100 - 1) * 100)}% en pesos reales) y fue neutro en términos reales para el trigo, porque subió casi lo mismo que la inflación."),
        ("Costos (insumos, flete, jornales)", "Cereza; trigo y maíz", "Media",
         "El flete a Hong Kong pasó de 49% a 102% del retorno al productor. El fertilizante subió más que el trigo. Los jornales no se midieron."),
        ("Clima", "Cereza, vino, cereales", "Media en el calendario; baja en el rendimiento",
         "Inviernos cálidos adelantan y concentran la cosecha. Con datos de dos ciudades no se encontró un efecto estable sobre el rendimiento."),
    ]
    table = ("<table class='t'><thead><tr><th>Fuerza</th><th>Rubros</th><th>Evidencia</th><th>En qué se apoya</th></tr></thead><tbody>"
             + "".join(f"<tr><td><b>{a}</b></td><td>{b}</td><td>{c}</td><td>{d}</td></tr>" for a, b, c, d in rows) + "</tbody></table>")
    main = f"""
<p>Cada rubro tiene su historia, pero cinco fuerzas se repiten. La tabla resume cuánta evidencia respalda cada una; &laquo;alta&raquo; significa que concuerdan datos propios y fuentes independientes, no que esté probada la causa.</p>
{table}
<h3>El dólar: un colchón que no siempre sirve</h3>
<p>El dólar observado promedió ${es(n['usd']['y2005'])} en 2005 y ${es(n['usd']['y2025'])} en 2025 (Figura @@R:usd@@), y llegó a un récord de $1.009 el 12 de julio de 2022 {cite('castro2022')}. Para el exportador de cereza, eso suavizó la caída del precio en dólares. Para el productor de trigo, en cambio, el efecto fue neutro: entre 2015-2017 y 2022-2024 el dólar subió {es((w['fx'] - 1) * 100)}% y la inflación {es((w['cpi'] - 1) * 100)}%. El dólar alto no equivale a mejores ingresos: depende de qué se vende, qué se compra y en qué moneda se pagan los costos. A la vez, el productor chileno tiene poco control sobre él, y su efecto se mezcla con el del precio internacional.</p>
{f['usd']}
<h3>El clima: pesa en el calendario, no se pudo medir en el rendimiento</h3>
<p>El clima actúa por tres vías distintas, y solo una se pudo observar en los datos de precios.</p>
<ul class='plain'>
<li><b>El año de cosecha.</b> En la cereza, un invierno cálido puede reducir la floración, y con ella la cosecha, o adelantar la maduración y concentrar los embarques. La prensa china vincula la baja floración de 2023 con una cosecha menor y precios altos, y el adelanto de 2025/26 con envíos más concentrados {cite('chen2026', 'freshplaza2026b')}. Los datos de este informe son coherentes con el primer caso (en 2023/24 el volumen exportado no creció y el precio subió), pero un solo año no prueba un patrón.</li>
<li><b>El agua.</b> Entre 2010 y 2022 Chile vivió una megasequía y la mayoría de las cuencas semiáridas llegó a estrés hídrico alto o extremo. Un estudio publicado en 2025 concluye que, en el largo plazo, el estrés hídrico del centro del país ha subido sobre todo por el mayor consumo de agua y, en menor medida, por una menor disponibilidad; en un escenario climático adverso, condiciones similares a las de la megasequía podrían volverse permanentes hacia fines de siglo {cite('boisier2025')}.</li>
<li><b>El frío invernal.</b> Los frutales caducos necesitan horas de frío para brotar bien. Una proyección con quince modelos climáticos estima que la mayoría de los sitios del centro de Chile perderá entre 10 y 15 porciones de frío hacia 2050, con riesgo de no cumplir los requerimientos de algunas especies en el norte {cite('fernandez2020')}.</li>
</ul>
<p>Para ver si el clima ayuda a explicar el rendimiento del cerezo, se contrastó el rendimiento nacional de cada temporada, medido contra su media móvil para quitar el efecto del envejecimiento de los huertos, con indicadores de Talca y Rancagua entre 1994 y 2024: días con temperatura mínima de 2 grados o menos durante la floración y lluvia en la cosecha. El resultado no es concluyente: la correlación con los días fríos de floración es de {es(cl[0]['cold'], 2)} el mismo año y de {es(cl[1]['cold'], 2)} al año siguiente, es decir, cambia de signo; la lluvia de cosecha prácticamente no muestra relación ({es(cl[0]['rain'], 2)} y {es(cl[1]['rain'], 2)}). Hay razones para esperar que así sea: los dos puntos de reanálisis no representan a todas las zonas productoras, subestiman las heladas locales y el rendimiento nacional mezcla huertos de muy distinta edad.</p>
{caution_box("<p>Que esta prueba no encuentre un efecto del clima no significa que no exista: significa que estos datos no bastan para medirlo. Para hacerlo bien se necesitarían estaciones meteorológicas por huerto y cosechas por predio, que no son públicas.</p>")}
<h3>Lo que no se pudo medir</h3>
<p>El ingreso semanal de fruta a los packings, que muestra con anticipación cuánta fruta llega al mercado, no se publica en datos abiertos. Tampoco hay series públicas de costos de mano de obra por rubro, ni de precios al consumidor comparables con los mayoristas. Estas ausencias limitan la capacidad de anticipar cambios de corto plazo, y por eso las conclusiones de este informe son de tendencia.</p>"""
    aside = ("<p><strong>Cómo leer la tabla.</strong> &laquo;Alta&raquo; se usa cuando los datos propios y al menos una fuente independiente apuntan a lo mismo. No es una prueba de causa.</p>"
             "<p><strong>Clima.</strong> El módulo climático del repositorio usa NASA POWER (reanálisis) para Talca, Rancagua y Chillán; sus resultados son exploratorios, no una evaluación del clima de una región.</p>")
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
         f"El precio internacional casi se duplicó en dólares, el dólar y la inflación se anularon y el productor recibió {sg(w['total'] - 1)} porque el margen local frente al trigo estadounidense pasó de {es(w['premium_base'], 2)} a {es(w['premium_recent'], 2)}. Cambió el origen del grano importado y existe un sistema de rebajas arancelarias."),
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
