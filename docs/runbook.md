# Ejecución

Desde la raíz del repositorio, con Python >=3.11:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,parquet]'
mpchile discover
mpchile ingest --start-year 2023 --end-year 2025
mpchile build
mpchile backtest --horizon 12
mpchile forecast --horizon 12 --model seasonal_naive
mpchile climate --start 2023-01-01 --end 2023-12-31
```

Primero probar un año y revisar el contrato. Para cargar más historia ampliar `--start-year` (catálogo mayorista desde1994). Los recursos anuales pueden ser voluminosos; normalización preserva `source_record` para trazabilidad y usa memoria proporcional al año. No ejecutar todo el catálogo sin revisar memoria y espacio. No hay transferencia nacional/regional automática ni unión precio-clima por región de mercado.

En un entorno sin instalar el paquete se puede usar `PYTHONPATH=src python -m materias_primas_chile.cli ...`. Pruebas sin dependencias de desarrollo adicionales: `PYTHONPATH=src python -m unittest discover -s tests -v`.

`build` conserva filas ambiguas en `quarantine.csv`, emite `quality.json`, `daily.csv`, `monthly.csv` y `series.csv`. Revisar cuarentena antes de interpretar resultados. No borra snapshots previos. Cuando existe más de una versión de un recurso, seleccionar explícitamente los CSV de la versión que se desea analizar en un directorio de entrada separado; no mezclar vintages. La detección de duplicados ambiguos impide elegir arbitrariamente entre correcciones.

La salida `monthly.csv` conserva precio en unidad comercial original, identificada en `series.csv`. Los modelos del CLI usan `value_col=price`; no renombran la columna a CLP/kg.

Para escenario climático se requiere una tabla mensual de entrenamiento ya asociada a zonas productoras verificadas, columnas climáticas explícitas y un CSV de supuestos futuros por `date,series_id`. Ejemplo (requiere archivos preparados y mapeo de origen validado):

```bash
mpchile forecast --input training_with_verified_origin_climate.csv --model ridge \
  --climate-columns temperature_mean_c,precipitation_mm \
  --scenario-csv future_assumptions.csv --scenario-name escenario_calido_seco
```

No se genera ese mapeo por defecto: el mercado comercial no identifica el origen de cultivo. Los escenarios producen asociaciones del modelo, no efectos causales demostrados. Consultar `docs/modeling.md` y `docs/climate.md`.

## Fallos

- Red denegada/timeout: la descarga falla; no sustituir por precios sintéticos. Revisar el proxy y permisos del entorno. TLS se mantiene verificado.
- Cambio de columnas ODEPA: normalización falla; guardar el recurso y actualizar contrato/tests tras inspección.
- Sin filas aceptadas: revisar cuarentena y números/fechas/unidades; no continuar pronóstico.
- Predicción faltante: revisar `status`, historia disponible y estacionalidad; no reemplazar automáticamente por cero.
- CI usa fixtures artificiales para comprobar lógica; una ejecución verde no certifica cobertura de fuentes ni precisión económica.
