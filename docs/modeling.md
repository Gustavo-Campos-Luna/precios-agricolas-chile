# Pronósticos y escenarios climáticos

El objetivo es pronosticar precios comparables de una serie concreta, no mezclar
productos o mercados para producir una cifra nacional artificial. Una serie debe
mantener producto, variedad, calidad, unidad, tipo de precio y geografía de
cotización. El mercado donde se vende no identifica necesariamente el lugar de
cultivo. Los modelos de este módulo reciben precios mensuales ya consolidados;
no convierten unidades ni agregan observaciones por su cuenta.

## Contrato de entrada

`date`, `series_id`, `price_clp_kg` por defecto (nombres configurables), con una
observación por mes y serie. Fechas se normalizan al inicio de mes y duplicados
mensuales provocan error. Precios observados deben ser positivos y finitos;
valores faltantes se preservan. Los huecos de calendario se hacen explícitos y
no se interpolan. Valores monetarios son nominales, salvo que el pipeline de
entrada los deflacte expresamente y cambie su identificación/unidad.

No sustituir un precio por caja, malla o bandeja por CLP/kg sin un peso documentado.
Si la unidad es distinta, `value_col` permite modelarla separadamente sin una
conversión ficticia.

El pronóstico utiliza un origen común: último mes de todo el dataset, o un
`forecast_origin` explícito igual o posterior. Las series que terminaron antes
se reindexan con meses faltantes y se abstienen si faltan rezagos. Nunca se
presenta como futuro actual un año posterior únicamente al último dato de una
serie antigua. El snapshot inicial tiene corte diciembre de 2025 y objetivos
2026: actualizar fuentes y revisar meses parciales antes de pronosticar 2027.

## Alternativas que se comparan

1. `naive`: último mes, recursivo; es una referencia de persistencia.
2. `seasonal_naive`: mismo mes del año anterior; conserva la estacionalidad anual.
3. `ridge`: regresión regularizada con rezagos 1, 2, 3 y 12, seno/coseno del mes y
   variables climáticas opcionales. Estandarización y ajuste ocurren dentro de
   cada ventana de entrenamiento. Alfa es fijo en 10, sin optimización sobre test.

El modelo **opcional** `ridge_seasonal` utiliza únicamente el rezago anual 12,
seno/coseno del mes y las covariables climáticas declaradas. No requiere precio
del mes inmediatamente anterior, de modo que puede evaluar cultivos con meses
sin comercialización. Conserva el mínimo de 24 observaciones reales y 12 filas
completas para ajuste. Si el mes del año anterior no tiene precio, se abstiene;
no estima un precio fuera de temporada ni rellena un hueco. Su mejor cobertura
no demuestra mejor precisión. El backtest debe comparar cobertura y errores
con las mismas series y horizontes. `MODELS` conserva los tres modelos originales;
solicitar el cuarto explícitamente mediante `models` o `model`.

El mínimo operativo es 24 observaciones mensuales reales por serie. Ridge exige
además al menos 12 filas de entrenamiento con todos los rezagos disponibles.
Estos mínimos permiten una evaluación inicial; no garantizan precisión. Series
de cereza o uva con pocos meses de comercialización pueden no cumplirlos. La
ausencia fuera de temporada no significa precio cero. Si un rezago requerido
falta o una predicción lineal resulta no positiva, el modelo se abstiene y deja
`prediction` vacía con un `status` explicativo.

## Evaluación temporal

```python
from materias_primas_chile.forecast import backtest_monthly, forecast_monthly

predictions, metrics = backtest_monthly(monthly_prices, horizon=12, stride=3)
forecast = forecast_monthly(monthly_prices, horizon=12, model="seasonal_naive")
```

El backtest usa ventanas expansivas y separa el desempeño por serie, modelo y
horizonte. No hay división aleatoria. Las salidas registran fecha de corte, mes
objetivo, valor observado y predicción. Se calculan MAE, RMSE, sMAPE, número de
objetivos observados y número de predicciones efectivamente puntuadas. Comparar
errores entre modelos exige revisar también su cobertura: un modelo que se
abstiene con frecuencia no debe ganar por evaluar solamente los meses fáciles.
Las ventanas pueden solaparse; no son réplicas independientes. No se declara
ganador automáticamente ni se presenta el error promedio como garantía futura.

El corte se interpreta como disponibilidad inmediata de los datos de ese mes.
Cuando existan fechas de publicación/vintages deben aplicarse sus rezagos antes
del entrenamiento. Esta primera implementación no reconstruye revisiones
históricas de fuentes, y por eso el backtest es seudorreal y no una reproducción
perfecta de la información disponible en cada fecha.

## Clima y escenarios

En el backtest de Ridge con clima, los meses futuros usan únicamente medias
climáticas por mes de calendario calculadas en el entrenamiento de cada corte.
Nunca se usan las temperaturas o precipitaciones realizadas del período test.
Para un pronóstico condicionado se exige un DataFrame `future_climate` completo
(fecha, serie, variables) y un `scenario_name` explícito. Ejemplo:

```python
conditional = forecast_monthly(
    monthly_prices_with_climate, model="ridge", climate_cols=["temperature"],
    future_climate=explicit_monthly_assumptions, scenario_name="temperatura_mas_2C",
)
```

Sin supuestos explícitos, Ridge climático usa `training_climatology` y lo etiqueta
en la salida. Una temperatura futura observada todavía no disponible no es un
supuesto admisible para evaluar capacidad predictiva. El módulo no consulta clima
futuro automáticamente.

Un escenario describe una asociación condicional del modelo. No demuestra que
un cambio de clima cause una variación de precio: influyen producción, stocks,
costos, tipo de cambio, comercio exterior y otros mercados. Los puntos climáticos
deben representar zonas productoras y su calendario fenológico, no asignarse al
mercado mayorista como si fuera el origen. Ridge con clima contemporáneo es una
primera referencia; requiere validación agronómica y comparación con rezagos
fenológicos antes de interpretar escenarios. Esta versión no genera intervalos
de confianza a partir de una única estimación ni publica probabilidades
inventadas. Para intervalos, se necesita calibración fuera de muestra por
horizonte, suficiente historia y un análisis explícito de cobertura.

## Extensiones priorizadas

- Calendarios productivos por cultivo, región de origen y ventana fenológica.
- Rezagos de publicación, vintages y revisiones de datos.
- Inflación/tipo de cambio como covariables de disponibilidad conocida.
- Modelos estacionales de mayor capacidad cuando superen referencias en test.
- Intervalos calibrados por horizonte, con control de cobertura y tamaño muestral.
- Validación contra shock climático y cambios de régimen, con datos suficientes.
