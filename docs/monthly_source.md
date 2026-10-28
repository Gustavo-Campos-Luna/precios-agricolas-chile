# Investigación de series mensuales ODEPA

## Resultado de esta entrega

Se identificaron y consultaron los metadatos públicos de la aplicación oficial
de [series de tiempo ODEPA](https://aplicativos.odepa.gob.cl/series-precios/series-tiempo).
**No se obtuvieron observaciones mensuales de precios utilizables.** Las consultas
de precios devolvieron primero HTTP 500 y, con el identificador IPC observado,
HTTP 200 con contenido HTML que indicaba un error de operación. HTTP 200 no
acredita una descarga de datos válida.

El último diagnóstico conservado muestra el mensaje «Ha ocurrido un error al
realizar la operación» para ambos productos probados. No se identificó una
solicitud de autenticación o CAPTCHA y no se intentó eludir controles. Se detuvo
la investigación de adquisición en este punto; no se rellenaron precios ni se
convirtieron los metadatos de productos en observaciones.

## Contrato público observado

Las rutas siguientes aparecen literalmente en los servicios JavaScript de la
aplicación. Los GET de metadatos se ejecutaron y sus respuestas quedaron en
[`data/research/monthly_probe.json`](../data/research/monthly_probe.json).
Base: `https://aplicativos.odepa.gob.cl/series-precios/results/`.

| Ruta | Método y uso |
|---|---|
| `tipos-mercados` | GET; tipos de precio y sus identificadores |
| `min-max-date-precio` | GET; rango global del catálogo, no cobertura por producto |
| `ipc` | GET; valores permitidos para el campo `idIPC` del formulario |
| `find/tipo-mercado?id=ID` | GET; metadatos de un tipo de precio |
| `sub-sectores-by-tipo-mercado?tipoMercado=ID` | GET; subsectores por tipo de precio |
| `pc-grupos?tipoMercado=ID` | GET; grupos de consumidor |
| `productos-by-pc-sm?grupo=ID` | GET; productos de un grupo de consumidor |
| `productos-by-sub-sector?subSector=ID&tipoMercado=ID` | GET; productos de otro subsector |
| `series-tiempo` | POST de consulta; la respuesta de precios no se validó |

Tipos observados: `7` consumidor minorista, `3` consumidor supermercado, `1`
productor, `5` internacional y `2` mayorista. La consulta de subsectores del tipo
productor devolvió carnes, lácteos y vinos, sin un subsector de cereales. La
existencia de una sección general de precios a productor no acredita una serie
mensual doméstica de maíz grano.

## Dos candidatos verificados únicamente como metadatos

| Identidad de consulta | Descripción publicada | Límite de interpretación |
|---|---|---|
| Mercado `7`, grupo `12`, producto `370` | Poroto Tórtola, `$/kilo (en envase de 1 kilo)` | Precio minorista; no se presume cobertura nacional ni origen agrícola |
| Mercado `5`, subsector `1`, producto `315` | Maíz Amarillo, FOB Puerto Argentino, `US$/tonelada` | Referencia internacional, distinta de maíz producido o comprado en Chile |

Los identificadores se comprobaron contra las respuestas reales antes de cada
consulta. No se sustituyeron por códigos largos de otra columna. Otros porotos
y maíces identificados en el catálogo siguen siendo candidatos de investigación,
no series históricas descargadas.

El rango global observado fue enero de 1975 a septiembre de 2026. Ese rango se
usó como solicitud y no como afirmación de cobertura de los dos productos.
También se probó un rango acotado desde enero de 2020 tras HTTP 500; los intentos
y sus formularios permanecen registrados.

## Formulario y bases monetarias

El controlador publicado asigna `periodoInicio`, `periodoTermino`, `tipoConsulta`,
`idIPC`, `tipoMercado`, `tipoSalida`, `precioConIva`, `subSector` y `producto`.
Se solicitaron precios nominales con salida anual `SA`, fechas ISO al mediodía
UTC y el valor IPC **6737**, obtenido del campo `valor` de una respuesta real del
catálogo. No se inventó un índice ni se aplicó una deflación a los precios.

`precioConIva=False` se registra como **`requested_tax_flag`**, no como prueba de
que los valores resultantes excluyan IVA. El controlador de consumidor muestra
una leyenda de precios con IVA independientemente de ese valor inicial. Como no
hay respuesta de precios válida, la base tributaria efectiva no se certifica.
Tampoco se convierten dólares a CLP ni toneladas a otra unidad a partir de un
catálogo de productos solamente.

No se consultaron servicios de identidad o autenticación ni se enviaron campos
IP inventados. El transporte no admite tokens ni credenciales en el formulario.

## Evidencia y herramientas reproducibles

- `scripts/discover_monthly_api.py`: descubre rutas presentes en HTML/JavaScript;
  una ruta hallada queda etiquetada como candidata hasta comprobar su respuesta.
- `scripts/probe_monthly.py`: conserva respuestas reales de metadatos y el
  contrato observado del formulario.
- `scripts/collect_monthly_sample.py`: verifica las identidades anteriores y
  registra cada intento de consulta.
- `src/materias_primas_chile/monthly.py`: conserva bytes HTTP originales,
  charset, tipo de contenido, compresión declarada, estado, URL final y SHA-256.
  Solo interpreta JSON tras decodificar con el charset declarado; no presupone
  Latin-1 cuando la fuente no lo declara.
- [`data/snapshots/monthly_candidates/collection_report.json`](../data/snapshots/monthly_candidates/collection_report.json):
  solicitudes, estados y rutas de los diagnósticos persistentes.
- Los subdirectorios `odepa_monthly/failures/` conservan cuerpos originales,
  consultas, manifiestos y vistas previas de hasta 2.000 caracteres. Se mantuvieron
  como evidencia del fallo, separados de las tablas de precios aceptadas.

Siete pruebas offline cubren contratos, metadatos, conservación de respuestas,
charset declarado, gzip y rechazo de HTML o JSON vacío. No sustituyen una
validación de precios reales. Ninguna respuesta de esta investigación se promovió
a las capas de precios limpios, panel mensual, entrenamiento o pronósticos.

## Condiciones para retomar

Antes de añadir un parser deben obtenerse una respuesta de precios válida y una
explicación verificable de `headerColumn` y `resultSeriesTiempo`. Habrá que
distinguir meses de promedios anuales, faltantes de ceros, unidades y monedas,
IVA, cobertura geográfica, revisiones y disponibilidad histórica. Una serie
minorista, una referencia FOB extranjera y un precio al productor chileno
permanecerán separados durante todo el proceso.
