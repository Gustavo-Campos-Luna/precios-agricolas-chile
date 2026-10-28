# Contrato analítico v0.1

## Precios

| Campo | Semántica |
|---|---|
| date | Fecha de observación, sin inventar fines de semana ni meses sin venta |
| series_id | Identificador estable de una combinación de dimensiones comerciales |
| product | Producto original y su equivalente normalizado cuando exista mapeo |
| variety / quality | Variedad y calidad; desconocidos se conservan explícitos |
| market / market_region | Mercado observado y su región, no origen productivo |
| origin | Origen publicado; no deducirlo del mercado |
| unit | Unidad de cotización original: caja, kilo, unidad, etc. |
| price / currency | Precio en unidad original, CLP solo si está acreditado |
| source / resource_id | Organismo y recurso descargado |
| retrieved_at_utc / sha256 | Procedencia del snapshot, en manifest asociado |

Un precio en CLP/caja no se transforma a CLP/kg salvo peso de caja documentado para esa observación. Un valor aduanero USD FOB/kg, un precio mayorista y un precio de productor son variables diferentes. No consolidarlos como una sola historia.

La normalización conserva además `price_clp_kg` cuando la etiqueta fuente declara
explícitamente el peso (`$/bandeja 10 kilos` divide por 10), o cuando ya cotiza por
kilo. `$/kilo (en bandeja de 18 kilos)` ya es precio por kilo y **no** se divide
por 18. `commercial_weight_kg` y `unit_conversion_method` auditan esa decisión.
Los envases con conteo explícito generan `price_clp_unit`, nunca un peso supuesto.
No se convierten quintales ni etiquetas ambiguas. La identidad de serie original
se mantiene: la conversión no autoriza mezclar variedades, calidades u orígenes.

## Panel mensual

Clave: `series_id`, `date` (inicio de mes). `price` es mediana de observaciones comparables del mes. `n_observations` permite observar densidad. Ausencia de precio es faltante, nunca cero. La primera implementación no produce un índice nacional ni un promedio ponderado por producción. Para cobertura mensual completa se reindexa dejando NA, sin interpolación automática.

## Clima

Se mantienen punto, latitud, longitud, proveedor, variable y unidad. Temperatura media en °C y precipitación acumulada mensual en mm son estadísticas diferentes: no promediar precipitación para llamarla acumulado. Meses parciales se marcan o excluyen. Las coordenadas de ciudades son referencias exploratorias y no pesos de superficie cultivada.

## Validación

- Rechazar fecha inválida, precio no numérico, cero, negativo o infinito.
- Detectar duplicados en la clave comercial real y conservar filas problemáticas para revisión.
- Mantener los productos estacionales sin rellenar su temporada ausente.
- Verificar continuidad por serie, moneda/unidad y cambios de esquema antes del modelado.
- Separar entrenamiento y evaluación por fecha; las transformaciones se ajustan dentro de cada fold.
- Escenarios climáticos futuros son supuestos del usuario, no observaciones ni inferencia causal.
