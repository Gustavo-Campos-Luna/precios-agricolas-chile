# Precios de materias primas agrícolas · Chile

Biblioteca y pipelines reproducibles para recolectar precios históricos oficiales, conservar su procedencia y evaluar pronósticos con escenarios climáticos.

## Estado

Primera carga real completada y versionada en [`data/snapshots/initial_2020_2025`](data/snapshots/initial_2020_2025): **63.528 observaciones válidas**, 51 en cuarentena, 16.635 observaciones mensuales y 3.786 series comerciales de cinco productos. Cobertura: enero de 2020 a diciembre de 2025, mercados de nueve regiones. Se incluyen cereza, uva, choclo, poroto verde y poroto granado. El maíz grano tiene una fuente independiente ODEPA/Cotrisa de una semana de 2025, insuficiente para pronosticarlo.

Clima histórico NASA POWER 2020–2025 para tres puntos de referencia; no representa todo Chile ni se asigna automáticamente a los cultivos. **51 pruebas offline aprobadas**; CI verifica Python 3.11 y 3.12 y construcción del paquete. Resultados y originales de las ejecuciones en [Actions](https://github.com/Gustavo-Campos-Luna/precios_materias_primas_chile/actions). Los ZIP de originales tienen retención de 30 días; las tablas analíticas, muestras observadas y manifests quedan versionados en Git.

Los pronósticos iniciales son referencias con corte común en diciembre de 2025, por lo que sus fechas objetivo corresponden a 2026; **no constituyen una proyección actualizada de 2027**. De 45.432 objetivos serie-mes, solo 538 tienen estimación y los demás registran abstención por historia o rezagos insuficientes. No hay un modelo climático comercial validado ni datos inventados.

## Diseño

- `src/materias_primas_chile/`: conectores, calidad, almacenamiento y modelos.
- `config/`: productos y ubicaciones explícitas.
- `data/raw/`: respuestas originales y manifiestos SHA-256.
- `data/processed/`: observaciones limpias y cuarentena.
- `data/curated/`: series mensuales comparables para modelado.
- `artifacts/`: resultados de evaluación y pronósticos.
- `docs/`: fuentes, contratos y limitaciones.
- `tests/`: pruebas offline de contratos y separación temporal.

Los datos voluminosos se regeneran con los pipelines y no se versionan en Git. Los datos de terceros mantienen sus licencias.

## Desarrollo

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,parquet]'
python -m pytest
```

Lectura de datos ya descargados (requiere el extra `parquet`):

```python
import pandas as pd

root = "data/snapshots/initial_2020_2025/"
prices = pd.read_parquet(root + "daily.parquet")
monthly = pd.read_parquet(root + "monthly.parquet")
series = pd.read_parquet(root + "series.parquet")
```

## Fuentes y comparabilidad

Documentación: [arquitectura](docs/architecture.md), [fuentes](docs/sources.md), [contrato](docs/data_contract.md), [ejecución](docs/runbook.md), [clima](docs/climate.md) y [modelos](docs/modeling.md).

```bash
mpchile discover
mpchile ingest --start-year 2020 --end-year 2025 --products cereza,uva,poroto,maiz,choclo
mpchile build
mpchile backtest --horizon 12
mpchile forecast --horizon 12
```

Ver [resumen verificable de la carga](data/snapshots/initial_2020_2025/summary.json), [cobertura por producto/región/unidad](data/snapshots/initial_2020_2025/coverage.csv) y [muestra de observaciones reales](data/snapshots/initial_2020_2025/observed_sample.csv).

El filtro selecciona subcadenas de nombres originales y no garantiza presencia de cada cultivo. Revisar `series.csv` y cobertura real. `monthly.csv` usa `price` en la unidad comercial original de cada serie. Los modelos se abstienen si falta historia o rezagos.

Se añaden `price_clp_kg` y `price_clp_unit` cuando la etiqueta declara una base
inequívoca. Un envase de 10 kilos permite precio por kilo; un precio ya cotizado
por kilo dentro de una bandeja no vuelve a dividirse. Se conservan precio original,
método de conversión y peso explícito; las series no se mezclan automáticamente.

La fuente inicial es [ODEPA, precios mayoristas de frutas y hortalizas](https://datos.odepa.gob.cl/es/dataset/precios-mayoristas-de-frutas-y-hortalizas), con recursos anuales publicados desde 1994. La cobertura pertenece a mercados observados, no a todos los productores del país. Maíz grano, choclo, poroto seco y poroto verde deben conservarse como productos distintos. Se mantienen mercado, origen, variedad, calidad y unidad; no se convierten cajas o unidades a kilogramos sin peso documentado.

Los escenarios climáticos son condicionales y no identifican por sí solos efectos causales. La evaluación utiliza cortes temporales, nunca particiones aleatorias.

## Experimento de escenarios climáticos

`python scripts/run_climate_experiment.py` ejecuta una unión explícita por origen
para cinco etiquetas de procedencia, con clima de puntos urbanos rezagado tres
meses. Compara climatología con un supuesto ilustrativo de +2 °C y −20% de
precipitación futura. El supuesto no modifica el clima del pasado. Consulta
[método y límites](docs/climate_experiment.md). Es una asociación experimental;
no certifica impactos regionales ni convierte esos puntos en clima representativo
de la superficie cultivada.
