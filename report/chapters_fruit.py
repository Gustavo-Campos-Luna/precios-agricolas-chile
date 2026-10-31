"""Capítulos de fruta: cereza, manzana y uva de mesa."""
from __future__ import annotations

from types import SimpleNamespace

from helpers import caution_box, chapter, es, ficha, read_box, sg, voices_box
from referencias import cite


def cherry(X: SimpleNamespace) -> str:
    n, f = X.n, X.f
    chg, cer, se, fx, rv = n["chg"], n["cer"], n["se"], n["fx_c"], n["rv"]
    ex = n["ex"]
    fob = lambda y: se.loc[y, "fob_usd_kg"]  # noqa: E731
    drop_2425 = fob(2024) / fob(2023) - 1
    vol_mult = se.loc[2023, "kt"] / se.loc[2009, "kt"]
    last = cer["last_price"]
    usd13, usd25 = fx.loc[2013, "usd_clp"], fx.loc[2025, "usd_clp"]
    idx_usd, idx_clp = fx.loc[2025, "idx_usd"] / 100 - 1, fx.loc[2025, "idx_clp_real"] / 100 - 1
    ha_lo, ha_hi = rv.loc[2018:2023, "usd_per_ha"].min(), rv.loc[2018:2023, "usd_per_ha"].max()
    # hechos de la temporada 2023/24: volumen estable, precio al alza (la temporada ODEPA 2023 arranca en noviembre de 2023)
    vol_2223, vol_2324 = se.loc[2022, "kt"], se.loc[2023, "kt"]
    fob_2223, fob_2324 = fob(2022), fob(2023)
    w_2223, w_2324 = cer["by_season"].loc[2022, "price_real_clp_kg"], cer["by_season"].loc[2023, "price_real_clp_kg"]
    main = f"""
<h3>Lo que pasó con el precio</h3>
<p>En el mayorista, el precio real de la cereza pasó de {es(cer['base'])} a {es(cer['recent'])} pesos por kilo entre 2014/15 a 2016/17 y 2022/23 a 2024/25: una baja de {es(abs(chg['cereza']['change']) * 100)}%. Si se compara solo el mismo mercado ({chg['cereza']['fixed_market']}) y la misma calidad ({chg['cereza']['fixed_quality']}), la baja es de {es(abs(chg['cereza']['fixed_change']) * 100)}%, así que no es un cambio de mezcla. En el mismo lapso, el volumen que llega a ese mercado pasó de {es(cer['kg_base'], 1)} a {es(cer['kg_recent'], 1)} millones de kilos por temporada. La última temporada completa (2025/26) subió a {es(last)} pesos, {es((last / cer['recent'] - 1) * 100)}% sobre ese promedio reciente y aún {es((1 - last / cer['base']) * 100)}% bajo el inicial (Figura @@R:cherry@@).</p>
{f['cherry']}
<p>El mayorista chileno, sin embargo, es un mercado pequeño: en 2024/25 recibió {es(n['wholesale_2425'], 1)} millones de kilos, cerca de {es(n['wholesale_share'] * 100, 1)}% de lo que se exportó en 2025. Lo que define el negocio es el precio de exportación, y ahí la lectura correcta es por temporada, no por año calendario. Entre 2009/10 y 2023/24 el valor por kilo osciló entre USD {es(n['fob_peak_seasons'][0], 1)} y {es(n['fob_peak_seasons'][1], 1)}, sin una tendencia clara, mientras el volumen exportado se multiplicaba por {es(vol_mult, 0)}. Durante quince años, entonces, el precio resistió la mayor oferta. El quiebre es reciente: en 2024/25 se exportaron {es(se.loc[2024, 'kt'])} mil toneladas, {es((se.loc[2024, 'kt'] / se.loc[2023, 'kt'] - 1) * 100)}% más que en la temporada anterior, y el valor por kilo cayó {es(abs(drop_2425) * 100)}%, de USD {es(fob(2023), 2)} a {es(fob(2024), 2)}. En 2025/26 no se recuperó: USD {es(fob(2025), 2)} con las declaraciones aduaneras disponibles (Figura @@R:exports@@), cifra en línea con los USD 4,56 por kilo que ODEPA calcula para los envíos a China entre septiembre y enero {cite('valenzuela2026')}.</p>
{f['exports']}
<p>El escalón de 2024/25 fue transversal. Decofrut describe una temporada con cotizaciones por debajo de las de años anteriores de principio a fin, solo comparables con las de 2020/21, cuando China aún tenía restricciones por la pandemia {cite('decofrut2025')}. La prensa del sector siguió el mismo hilo: en enero de 2025 informaba de un repunte tras la caída provocada por las exportaciones récord a China {cite('aguirre2025')} y en marzo titulaba que no todos los caminos conducían a ese mercado {cite('ernst2025')}. RaboResearch agrega que los retornos al productor no se recuperaron en una segunda temporada, aun con menos volumen exportado en 2025/26 {cite('rabo2026')}.</p>

<h3>Por qué: más huertos de los que el mercado absorbe</h3>
<p>La explicación de fondo es de cantidad. Un economista de INIA Quilamapu calcula que la superficie de cerezos pasó de 16 mil hectáreas en 2013 a más de 39 mil en 2020 y a unas 70 mil en 2024, y atribuye la caída de precios a una oferta que superó la capacidad de la demanda {cite('inia2025')}. El catastro de ODEPA y CIREN llega a 77.766 hectáreas en 2025, 38 mil más que cinco años antes {cite('valenzuela2026')}. Los datos de FAOSTAT dan la misma magnitud: de 16.243 hectáreas en 2013 a 76.447 en 2024, casi cinco veces {cite('faostat_cultivos')}.</p>
<p>Lo que ya está plantado seguirá presionando. De las 76.881 hectáreas que estimaba el catastro de 2024, solo 23% estaba en plena producción: 47% en producción creciente, 29% en formación y apenas 1% en producción decreciente {cite('decofrut2025')}. Dicho de otra forma, tres de cada cuatro hectáreas aún no entregan todo lo que van a entregar. ODEPA estima que 78% de los huertos tiene menos de diez años {cite('ovalle2026')}. GP Graders estima que, con esos huertos jóvenes en producción, la oferta exportable podría llegar a 800 mil toneladas, frente a las 625 mil de 2025 {cite('freshplaza2026d')}.</p>
{f['cherry_var']}
<p>La baja no se concentra en una variedad: las principales cayeron entre {es(abs(n['var_cer_range'][0]) * 100)}% y {es(abs(n['var_cer_range'][1]) * 100)}% (Figura @@R:cherry_var@@). Tres variedades concentran casi tres cuartos de la superficie: Santina (37,3%), Lapins (22,5%) y Regina (14,6%) {cite('decofrut2025')}. El catastro propio, para las regiones medidas en 2016 y 2024, lo confirma por variedad:</p>
{n['orch_table']}
{caution_box(f"<p>La tabla suma {es(n['orch_tot'][0])} hectáreas en 2016 y {es(n['orch_tot'][1])} en 2024 porque solo incluye las {int(n['orch']['regions_compared'].iloc[0])} regiones que se midieron en ambos años. Sirve para ver cómo cambió la mezcla de variedades, no como cifra nacional; para el total del país se usan las cifras de ODEPA.</p>")}

<h3>Un cliente que compra casi todo</h3>
<p>China recibió 91% del volumen exportado en 2024/25 {cite('decofrut2025')} y 87% en lo que va de 2025/26 {cite('valenzuela2026')}. INIA calcula que entre 2022 y 2024 fue destino de 88% del tonelaje y 91% del valor, y lo califica de comprador dominante y riesgoso, en la forma de un monopsonio {cite('inia2025')}. Cuando hay un solo comprador relevante, un año de mala demanda allá se traduce directamente en un mal año aquí.</p>
<p>Dos rasgos del mercado chino ayudan a entender por qué la presión se concentra en pocas semanas. Primero, la cereza importada se abarata cada invierno de forma previsible: en el mercado mayorista de Guangzhou, el precio cayó entre 70% y 80% entre noviembre y enero en cada uno de los últimos tres años, en parte porque los primeros envíos llegan por avión (USD 13,2 por kilo en octubre, casi el doble que el envío marítimo de noviembre) y después el volumen llega por mar {cite('chen2026')}. Segundo, el calendario manda: en 2025/26 un clima más cálido adelantó la cosecha entre siete y diez días y desplazó toda la curva de precios hacia atrás {cite('chen2026')}, y el adelanto concentró los embarques en los primeros días de enero, antes del Año Nuevo Chino {cite('freshplaza2026b')}.</p>
{voices_box([
    ("El presidente de Frutas de Chile atribuyó la temporada 2025/26 sobre todo a la concentración de la oferta: hasta el 20 de enero había llegado más fruta a China que un año antes.", "Iván Marambio, Frutas de Chile, vía FreshPlaza (2026b)"),
    ("El presidente de Fedefruta anticipó retornos muy ajustados por el menor poder de compra en China, una situación que ya se notaba durante el último año.", "Víctor Catan, Fedefruta, vía FreshPlaza (2026b)"),
    ("El gerente general de una agrícola dio por terminado el ciclo de precios históricamente altos y advirtió que quienes obtienen menos de 10 a 12 toneladas por hectárea deberán revisar si les conviene seguir.", "Patricio Bravo, Agrícola Don Fortunato, vía FreshPlaza (2026b)"),
])}

<h3>El flete y la calidad también restan</h3>
<p>Según Utilitas, enviar un kilo de cereza a Hong Kong absorbía 48,6% del retorno libre al productor en la temporada 2017/18 y 102,3% en 2024/25; en la semana 49 de esa temporada el flete (USD 1,77 por kilo) superó al retorno del productor (USD 1,73) {cite('mundomaritimo2025')}. Un ejecutivo de Greenvic proyectó que, si se concretaba la mayor capacidad de naves, el flete podía bajar entre 20% y 25% {cite('mundomaritimo2025')}. Si eso ocurrió o no, los datos disponibles aún no lo permiten verificar.</p>
<p>La calidad se suma al problema. El mercado paga calibres de 28 a 32 milímetros y solo cerca de 30% de la producción los cumple; el viaje puede tomar hasta 40 días desde la cosecha hasta el comercio minorista, con efectos sobre firmeza y sabor {cite('freshplaza2026d')}. Decofrut anotó para 2024/25 abundancia de calibres pequeños y poca coloración y dulzor {cite('decofrut2025')}. La estructura comercial ayuda poco: unos 300 exportadores y 900 marcas, venta casi siempre en consignación y financiamiento previo de los compradores que se ha reducido {cite('freshplaza2026d')}.</p>

<h3>Qué amortigua y qué no</h3>
<p>El dólar actuó como colchón. Entre 2013 y 2025 el valor unitario de exportación bajó {es(abs(idx_usd) * 100)}% en dólares, pero solo {es(abs(idx_clp) * 100)}% en pesos reales, porque el dólar pasó de unos ${es(usd13)} a ${es(usd25)} (Figura @@R:fxcushion@@). Para quien gasta en pesos (jornales, fertilizantes locales), el golpe fue menor que lo que muestran los dólares; para quien debe importar insumos o paga fletes en dólares, no.</p>
{f['fxcushion']}
<p>Tampoco se ve un desplome del ingreso por hectárea. Con la superficie de FAOSTAT, el ingreso bruto de exportación se movió entre USD {es(ha_lo / 1000)} mil y {es(ha_hi / 1000)} mil por hectárea de 2018 a 2023, subió a USD {es(rv.loc[2024, 'usd_per_ha'] / 1000)} mil en 2024 y, con la superficie de 2025 de ODEPA, habría sido de unos USD {es(n['rev25_usd_ha'] / 1000)} mil en 2025 (Figura @@R:revha@@). Cada hectárea produce más fruta que antes, lo que compensó en parte el menor precio por kilo. Este es un ingreso bruto: no descuenta embalaje, cosecha, flete ni comisiones, y es lo que se aprieta. GP Graders estima que en 2024 el costo de producción promedio rondó USD 2 por kilo frente a retornos de unos USD 1 {cite('freshplaza2026d')}; es una estimación del sector que este informe no pudo verificar con datos propios. Sí es un hecho que el rendimiento nacional promedio, de {es(rv.loc[2024, 'yield_kg_ha'] / 1000, 1)} toneladas por hectárea en 2024 según FAOSTAT, está por debajo de las 10 a 12 toneladas bajo las cuales el productor citado arriba aconseja revisar la viabilidad, aunque ese promedio incluye huertos jóvenes.</p>
{f['revha']}
<p>Por último, ¿sigue el precio del mercado interno al de exportación? En parte. Las variaciones anuales de ambos se mueven en la misma dirección, con una correlación de {es(n['track']['corr'], 2)} en {n['track']['n']} temporadas, pero con mucho movimiento propio (Figura @@R:track@@). La lectura práctica es que el mayorista sirve como señal, no como sustituto del precio de exportación.</p>
{f['track']}

<h3>Qué podría cambiar el rumbo</h3>
<p>La señal más reciente es de clima. El presidente de la SNA proyectó para 2026/27 unos 115 millones de cajas, frente a los 140 millones que se esperaban al inicio; las lluvias afectaron la polinización y el desarrollo de los frutos, el granizo causó pérdidas totales en algunos predios y nuevas lluvias podrían dañar la fruta madura {cite('contreras_e2026')}. Dos precisiones ayudan a no sobreinterpretar. Primero, 115 millones de cajas equivalen a lo exportado en 2025/26 (113,8 millones) {cite('freshplaza2026b')}: es un recorte respecto de la proyección, no respecto de la temporada pasada. Segundo, hay un precedente: en 2023/24, con un invierno cálido que redujo la floración {cite('chen2026')}, el volumen exportado fue prácticamente el mismo que el de la temporada anterior ({es(vol_2324)} mil toneladas) a pesar de más superficie, y el precio subió: {es((fob_2324 / fob_2223 - 1) * 100)}% el valor de exportación y {es((w_2324 / w_2223 - 1) * 100)}% el precio mayorista real. Una cosecha corta por clima levanta el precio un año, pero no corrige el exceso estructural.</p>
<p>El ajuste de fondo vendría por otro lado. Según el sector, para restablecer el equilibrio el volumen exportado tendría que bajar cerca de 30%, a unas 400 mil toneladas {cite('freshplaza2026d')}, lo que en la práctica significa menos hectáreas. RaboResearch anticipa que la superficie ya habría llegado a su máximo y que vendrán arranques {cite('rabo2026')}. Mientras no ocurran, los huertos jóvenes seguirán sumando fruta.</p>
{read_box("<p>La cereza no tiene un problema de demanda que se haya desplomado de golpe: tiene más fruta de la que un solo cliente paga a los precios anteriores, un viaje largo que encarece y deteriora, y una cosecha que, por el clima, llega cada vez más junta. El dólar alto amortigua en pesos; el flete y los costos comerciales no.</p>", "En una frase")}"""
    aside = (ficha("La cereza en cifras", [
        ("Superficie 2013 a 2025", "16 mil a 78 mil ha"),
        ("Exportación 2024/25", f"{es(se.loc[2024, 'kt'])} mil t"),
        ("FOB 2023/24 a 2024/25", f"USD {es(fob(2023), 1)} a {es(fob(2024), 1)}"),
        ("Participación de China", "91% (87% en 2025/26)"),
        ("Precio mayorista real", sg(chg["cereza"]["change"])),
        ("Flete sobre retorno", "49% a 102%")], neg=(2, 4, 5))
        + "<p><strong>Temporada y año.</strong> ODEPA mide por temporada (625 mil t en 2024/25); el gráfico de ingreso por hectárea usa año calendario.</p>"
          "<p><strong>Dato de la prensa china.</strong> El abaratamiento entre noviembre y enero en Guangzhou es habitual: no toda caída de precio en el destino es mala noticia sobre demanda.</p>")
    return chapter("cereza", "Capítulo 1 | Cereza", "Cereza: más fruta que mercado, y casi todo hacia un solo cliente",
                   f"El valor de exportación por kilo cayó de USD {es(fob(2023), 1)} a USD {es(fob(2024), 1)} en una temporada, y el mayorista paga {es(abs(chg['cereza']['change']) * 100)}% menos que hace una década.", main, aside, product="cereza")


def apple_grape(X: SimpleNamespace) -> str:
    n, f = X.n, X.f
    chg, ap = n["chg"], n["apple"]
    q15, q24, a15, a24 = ap["prod15"], ap["prod24"], ap["area15"], ap["area24"]
    main = f"""
<h3>Manzana: la cosecha cayó una cuarta parte y el precio subió dos tercios</h3>
<p>Según FAOSTAT, la producción chilena de manzana bajó de {es(q15 / 1e6, 2)} a {es(q24 / 1e6, 2)} millones de toneladas entre 2015 y 2024 ({sg(q24 / q15 - 1)}), y la superficie de {es(a15)} a {es(a24)} hectáreas ({sg(a24 / a15 - 1)}) {cite('faostat_cultivos')}. El rendimiento por hectárea subió, de {es(ap['yield15'] / 1000, 1)} a {es(ap['yield24'] / 1000, 1)} toneladas, pero no alcanzó a compensar la menor superficie. En el mismo período, el precio real mayorista pasó de {es(ap['p15'])} a {es(ap['p24'])} pesos por kilo ({sg(ap['p24'] / ap['p15'] - 1)} entre esos dos años y {sg(chg['manzana']['change'])} con promedios de tres años). Si se fija el mercado y la calidad, el alza es de {es(chg['manzana']['fixed_change'] * 100)}% (Figura @@R:apple_idx@@).</p>
{f['apple_idx']}
<p>La relación no es una casualidad de esos años. En los {ap['flex']['n']} años con datos, las variaciones anuales de la producción y del precio real se mueven en sentidos opuestos (correlación de {es(ap['flex']['corr'], 2)}), con una pendiente de {es(ap['flex']['slope'], 2)}: en promedio, un año con 10% menos de cosecha vino acompañado de un precio cerca de 10% más alto (Figura @@R:apple_scatter@@). Es una asociación descriptiva; no separa lo que hizo la oferta de lo que hicieron la demanda y las exportaciones.</p>
{f['apple_scatter']}
<p>¿Por qué se achicó la oferta? ODEPA registra que el manzano bajó de 30.967 hectáreas en 2021 a 24.994 en 2024, 19% menos {cite('munoz2025')}, y el USDA atribuye el retroceso a baja rentabilidad, huertos envejecidos y reconversión hacia cerezos y nogales {cite('usda2025')}. El catastro de 2025 confirma la tendencia de largo plazo: el manzano perdió 7.351 hectáreas en cinco años, a razón de 5% al año {cite('valenzuela2026')}.</p>
<p>La exportación entrega una verificación independiente del precio. Las ventas al exterior promediaron unas 532 mil toneladas en 2023 a 2025, frente a 753 mil en 2016 a 2018 {cite('freshplaza2026a')}. En el primer semestre de 2026 se despacharon 318,8 mil toneladas, 5% más que un año antes, con un valor FOB de USD 1,11 por kilo según datos de ODEPA, el más alto de la última década; la nota lo asocia a una mayor proporción de variedades premium y a mercados con más poder de compra, e India pasó a ser el primer destino, con 16% del volumen {cite('freshplaza2026c')}. Un precio de exportación en su máximo en diez años es coherente con un precio mayorista alto: el mercado paga bien una fruta más escasa.</p>

<h3>Uva de mesa: la menor superficie en 25 años y un competidor más barato en el norte</h3>
<p>El precio real de la uva de mesa en el mayorista subió {es(chg['uva']['change'] * 100)}% entre los mismos períodos ({es(chg['uva']['fixed_change'] * 100)}% con mercado y calidad fijos). En la oferta, las plantaciones llegaron en 2023/24 a 39.931 hectáreas, el mínimo desde 1999, tras trece años de caída por la competencia de Perú y la sequía {cite('guzman2024')}. El catastro de ODEPA muestra que la uva de mesa es la especie que más superficie perdió entre 2020 y 2025: 14.164 hectáreas, a razón de 7% al año {cite('valenzuela2026')}.</p>
<p>Una comparación de costos de Sensonomic, recogida por AgroLatam, ubica la diferencia en el rendimiento: Chile obtiene unas 2.700 cajas por hectárea con un costo de USD 27.300, lo que fija su precio de equilibrio en USD 10,11 por caja. Perú logra 3.500 cajas con un costo mayor, de USD 34.100 por hectárea, pero su equilibrio es más bajo: USD 9,74. Sudáfrica produce más barato por hectárea (USD 23.100), pero con solo 2.200 cajas llega a USD 10,50 {cite('agrolatam2025')}. En esas condiciones, quien ofrece más cajas por hectárea puede venderlas a menos precio y aun así ganar.</p>
<p>En la temporada 2025/26 el volumen exportado de uva de mesa cayó 14,3% y el valor unitario subió 7,9%, de USD 1,77 a USD 1,90 por kilo {cite('munoz2026')}. A la vez, los exportadores chilenos recortaron envíos a Estados Unidos en medio de una sobreoferta {cite('espinoza2026')}. La menor oferta sostiene el precio, pero el mercado de destino sigue exigente.</p>
{f['apple_grape']}
{f['var2']}
{read_box("<p>Es el espejo de la cereza. Cuando una especie se planta sin freno, el precio cede; cuando se arranca por falta de rentabilidad, lo que queda se vende mejor. La señal de precios funciona, pero con rezago de años, porque un huerto tarda mucho en plantarse y en arrancarse.</p>", "En una frase")}
{caution_box("<p>Ninguna de las fuentes consultadas mide el precio mayorista real de la manzana, así que ese resultado proviene del análisis propio de los datos de ODEPA. Lo respaldan la menor producción y el máximo decenal del valor de exportación, pero no es una cifra publicada por terceros.</p>")}"""
    aside = (ficha("Manzana y uva de mesa", [
        ("Producción de manzana", f"{sg(q24 / q15 - 1)}"),
        ("Precio real manzana", sg(chg["manzana"]["change"])),
        ("FOB manzana 1S 2026", "USD 1,11/kg"),
        ("Superficie uva de mesa", "39.931 ha (2023/24)"),
        ("Precio real uva de mesa", sg(chg["uva"]["change"])),
    ], neg=(0,))
        + "<p><strong>Dato.</strong> La superficie de uva de mesa en 2023/24 fue la menor desde 1999 (Guzmán, 2024).</p>"
          "<p><strong>Ojo con el año.</strong> La manzana se mide por año calendario; la uva de mesa, por temporada de diciembre a abril.</p>")
    return chapter("manzana", "Capítulo 2 | Manzana y uva de mesa", "Manzana y uva de mesa: menos fruta, mejor precio",
                   "Cuando se cosecha menos, el precio real sube. Los huertos arrancados por falta de rentabilidad explican buena parte del alza.", main, aside, product="manzana")
