# Precios de materias primas agrícolas · Chile

Biblioteca y pipelines reproducibles para recolectar precios históricos oficiales, conservar su procedencia y evaluar pronósticos con escenarios climáticos.

## Estado

Implementación inicial con conectores y pruebas offline. La descarga masiva todavía no se ha completado: el entorno local restringió las conexiones de red. El workflow `initial official data collection` intenta recolectar datos oficiales en GitHub Actions y conserva resultados y procedencia como artefacto durante 30 días. Su estado y logs determinan si esa descarga se completó. No se incluyen observaciones inventadas ni pronósticos comerciales validados.

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

## Fuentes y comparabilidad

Documentación: [arquitectura](docs/architecture.md), [fuentes](docs/sources.md), [contrato](docs/data_contract.md), [ejecución](docs/runbook.md), [clima](docs/climate.md) y [modelos](docs/modeling.md).

```bash
mpchile discover
mpchile ingest --start-year 2020 --end-year 2025 --products cereza,uva,poroto,maiz,choclo
mpchile build
mpchile backtest --horizon 12
mpchile forecast --horizon 12
```

El filtro selecciona subcadenas de nombres originales y no garantiza presencia de cada cultivo. Revisar `series.csv` y cobertura real. `monthly.csv` usa `price` en la unidad comercial original de cada serie. Los modelos se abstienen si falta historia o rezagos.

La fuente inicial es [ODEPA, precios mayoristas de frutas y hortalizas](https://datos.odepa.gob.cl/es/dataset/precios-mayoristas-de-frutas-y-hortalizas), con recursos anuales publicados desde 1994. La cobertura pertenece a mercados observados, no a todos los productores del país. Maíz grano, choclo, poroto seco y poroto verde deben conservarse como productos distintos. Se mantienen mercado, origen, variedad, calidad y unidad; no se convierten cajas o unidades a kilogramos sin peso documentado.

Los escenarios climáticos son condicionales y no identifican por sí solos efectos causales. La evaluación utiliza cortes temporales, nunca particiones aleatorias.
