# Clima histórico: alcance y ejecución

## Fuente implementada

NASA POWER Daily API, punto geográfico, comunidad agroclimatológica `AG`, JSON y días en UTC. Documentación verificada: https://power.larc.nasa.gov/docs/services/api/temporal/daily/ . El servicio documenta disponibilidad meteorológica desde 1981 y datos hasta tiempo casi real; verificar fechas efectivas en cada descarga. Variables solicitadas: `T2M`, `T2M_MIN`, `T2M_MAX` (temperatura a 2 m, °C) y `PRECTOTCORR` (precipitación diaria corregida, mm/día). Sumada durante un mes completo, la precipitación se expresa en mm/mes.

`config/locations.csv` contiene tres **puntos de referencia urbanos aproximados**: Rancagua, Talca y Chillán. Son coordenadas semilla explícitas para probar el conector; no corresponden a polígonos ni a promedios de zonas productivas. Los códigos regionales se guardan como texto. No asociar un precio de mercado a este clima automáticamente: hace falta identificar origen productivo, calendario fenológico y ponderaciones de superficie/producción.

## Uso reproducible

```python
from materias_primas_chile.climate import Location, fetch_power, aggregate_monthly
punto = Location('talca', -35.4264, -71.6554, '07')
diario = fetch_power(punto, '2023-01-01', '2023-12-31')
mensual = aggregate_monthly(diario)
mensual.to_csv('data/processed/climate_talca_2023_monthly.csv', index=False)
```

Para 2023–2025, ejecutar una consulta por año y punto. No duplicar consultas por la misma celda de la grilla: NASA advierte que solicitudes repetidas pueden bloquearse. La caché conserva respuesta original con SHA256, URL completa, coordenadas, fechas y hora UTC de recuperación en un manifiesto. Una nueva versión de la fuente debe escribirse en otro directorio para conservar el vintage anterior. La caché valida hash y consulta antes de reutilizar datos.

## Contratos y disponibilidad

Los sentinels faltantes se convierten en null; nunca cero. Temperatura y precipitación mensual solo se calculan cuando **todos los días del mes** tienen observación válida para esa variable. Los días faltantes, parciales y duplicados no se esconden. La salida conserva conteos de cobertura y grano punto–mes; `spatial_scope=grid_point_proxy` impide confundirlo con clima regional.

`historical_features(monthly, forecast_origin, release_lag_days=60)` elimina meses cuyo fin más el retardo supera el origen del pronóstico. Los 60 días son una hipótesis conservadora configurable, **no una garantía del tiempo de publicación NASA**. Un backtest con históricos revisados no demuestra que esas observaciones estuvieron disponibles en el pasado; se requieren vintages por fecha de corte. Para escenarios del próximo año, introducir trayectorias climáticas explícitamente etiquetadas como escenarios, nunca clima realizado futuro. Correlación clima–precio no acredita causalidad.

## Estado de descarga en esta sesión

La primera descarga local quedó bloqueada por permisos de red. Posteriormente se ejecutó con éxito en GitHub Actions: datos diarios reales de 2020–2025 para Rancagua, Talca y Chillán, con originales y manifests en el artefacto de ejecución y tabla mensual en `data/snapshots/initial_2020_2025/climate_monthly.parquet`. TLS se mantuvo verificado. Los tests usan fixtures sintéticos separados; la descarga real se acredita con manifests y logs, no con los tests.

## Segunda opción investigada: DMC

El portal de la Dirección Meteorológica de Chile (https://climatologia.meteochile.gob.cl/) publica servicios JSON históricos y permite uso público citando a la DMC. Se verificó su catálogo: https://climatologia.meteochile.gob.cl/application/index/menuTematicoJson .

Las páginas oficiales documentan dos servicios que requieren `usuario` y una API key personal:

- Temperatura diaria por estación y año: https://climatologia.meteochile.gob.cl/application/documentacion/getDocumento/18 .
- Precipitación diaria histórica por estación: https://climatologia.meteochile.gob.cl/application/documentacion/getDocumento/21 . Distingue suma parcial, total con observaciones completas y trazas menores a 0,1 mm.

No se usó una credencial inventada ni se declara descarga DMC implementada. Antes de añadir el conector, configurar credenciales mediante secretos del entorno; nunca guardar URLs con token en los manifiestos. Mantener TLS verificado aunque algunos ejemplos del portal lo desactiven. Validar identificadores, unidades, traslados de estación y faltantes antes de contrastar la estación con POWER. Una estación tampoco es un promedio regional.
