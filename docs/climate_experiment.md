# Experimento de precio y clima por origen declarado

Este flujo comprueba que la biblioteca puede unir precios históricos y clima y
ejecutar escenarios condicionales. Es un experimento exploratorio; no certifica
efectos causales del clima sobre precios ni precisión comercial.

`config/origin_climate_map.csv` contiene cinco correspondencias **literales** del
campo `origin` a Rancagua, Talca o Chillán. Son puntos urbanos de referencia dentro
de las regiones de origen declaradas. No representan la superficie cultivada de
una región o provincia. Nunca se utiliza la región del mercado como origen.
Orígenes importados, desconocidos o sin correspondencia se excluyen y se cuentan
en `report.json`; no se geocodifican ni se asignan por cercanía automáticamente.

Se incorporan `temp_lag3` y `precip_lag3`: temperatura media y precipitación
acumulada del punto **tres meses antes** del mes de precio. Unir por mes calendario
con desplazamiento explícito evita trasladar filas cuando falta un mes. Ese
rezago permite una primera hipótesis conservadora de disponibilidad; no sustituye
un archivo histórico de fechas de publicación y revisiones de NASA POWER.

El script requiere los Parquet reales del snapshot inicial:

```bash
python -m pip install -e '.[parquet]'
python scripts/run_climate_experiment.py
```

La cohorte exige 24 observaciones mensuales de precio reales. Se evalúan naive,
seasonal naive, Ridge y el Ridge estacional opcional con cortes temporales. El
Ridge estacional conserva solo el rezago de precio anual, sin exigir meses
consecutivos de comercialización. Se abstiene cuando no hay precio el mismo mes
del año previo. No se declara ganador por su cobertura. Los escenarios usan
`ridge_seasonal`; requieren al menos 12 filas completas de ajuste además de 24
observaciones de precio. El backtest de Ridge sustituye el
clima futuro por climatología ajustada solo dentro de cada corte, nunca clima
realizado del período de evaluación. La falta de rezagos provoca abstención.
No se imputan precios de meses fuera de temporada.

Las dos tablas de supuestos contienen climatología histórica del punto y una
variación **ilustrativa** de +2 °C y −20% de precipitación sobre esos predictores
rezagados. Solo se usa clima de meses <= corte menos tres meses al construir las
climatologías. Esas filas futuras están marcadas como supuestos, no observaciones.
La anomalía se aplica al clima tres meses antes del objetivo, no al clima
contemporáneo de la cosecha. Para un corte diciembre de 2025 no cambia clima de
2025: los objetivos enero–marzo de 2026 mantienen la climatología de referencia y
la anomalía solo aparece desde abril de 2026, cuando el mes climático supuesto es
posterior al corte. No se interpreta como intervención causal ni como
pronóstico meteorológico. No se inventan intervalos de confianza.

Las salidas se guardan en `data/experiments/climate_proxy_v1`: entrenamiento,
backtest, métricas, supuestos explícitos, estimaciones condicionales y reporte de
cobertura. El precio conserva su unidad comercial original por serie. La fecha de
corte común del snapshot 2020–2025 es diciembre de 2025; los objetivos son 2026 y
no constituyen una proyección actualizada de 2027. Validar calendarios fenológicos,
polígonos agrícolas, disponibilidad temporal, variables de oferta/demanda y
desempeño fuera de muestra antes de cualquier uso operativo.
