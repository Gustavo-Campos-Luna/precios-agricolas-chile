# Datos

Esta carpeta contiene los datos del proyecto. **Casi todo se genera localmente** y no se versiona, porque pesa unos 2,8 GB y se puede reconstruir desde las fuentes oficiales. Lo que sí está en Git es lo necesario para auditar el informe: las tablas de cada figura (en [`../report/data/`](../report/data)), los informes por producto y una muestra histórica.

| Carpeta | Qué contiene | En Git | Cómo se genera |
|---|---|---|---|
| `raw/` | Archivos tal como los entrega cada fuente, con su `.manifest.json` (URL, fecha UTC, SHA-256). Es la evidencia. | No | `mpchile ingest`, `series`, `datasets`, `faostat`, `pinksheet`, `cotrisa`, `bcch` |
| `processed/` | Series normalizadas por fuente (CSV comprimidos y Parquet) | No | Los mismos comandos |
| `curated/prices/` | Panel diario y mensual del mayorista ODEPA, con control de calidad y cuarentena | No | `mpchile build`, `volume` |
| `analysis/` | Tablas listas para analizar (Parquet) y sus reportes de calidad | No | `mpchile panel`, `supply`, `reference`, `compact` |
| `processed/faostat/crops_production.csv` | Superficie, producción y rendimiento de cultivos de Chile (1961 a 2024) | Sí (1 MB) | `mpchile faostat` |
| `processed/climate/` | Clima diario de Talca, Rancagua y Chillán (NASA POWER) para el experimento exploratorio | Sí (3 MB) | `docs/climate.md` |
| `processed/climate_era5/agroclimate_indices.csv` | Índices agroclimáticos por sitio y año (horas de frío, heladas, lluvia de cosecha, calor) desde ERA5 | Sí | `scripts/build_agroclimate.py` (datos de `chile-weather-forecasting`) |
| `processed/comtrade/` | Importaciones chinas de cereza, exportaciones de competidores e importaciones chilenas de trigo (UN Comtrade) | Sí | `scripts/download_comtrade.py` |
| `processed/ine/` | Índices de costo laboral y remuneraciones del INE, desde 2009 | Sí | `materias_primas_chile.ine.download` |
| `processed/odepa_fichas/` | Parámetros de la ficha técnico-económica de ODEPA para cerezo (O'Higgins, 2016-17) | Sí | `materias_primas_chile.fichas` |
| `analysis/reports/` | Informes por producto en Markdown | Sí | `scripts/analysis_*.py` |
| `research/` | Respuestas de ejemplo de las APIs usadas para investigar fuentes | Parcial | Manual |
| `snapshots/` | Muestra histórica de la primera carga real (2020 a 2025) | Sí | Histórico |

## Tablas analíticas principales

| Archivo | Una fila es | Detalle |
|---|---|---|
| `analysis/prices_monthly.parquet` | Una serie homogénea en un mes (producto, variedad, calidad, origen, unidad, mercado) | Precio real, precio por kilo (solo con peso declarado), volumen, variedad armonizada |
| `analysis/orchards.parquet` | Hectáreas por año, región, especie, variedad y año de plantación | Catastro frutícola (CIREN y ODEPA) |
| `analysis/exports_monthly.parquet` | Producto arancelario por mes | Valor unitario FOB ponderado por kilos (derivado) |
| `analysis/retail_monthly.parquet` | Producto, variedad, región y punto de venta por mes | Consumidor ODEPA |
| `analysis/external_prices_monthly.parquet` | Serie externa por mes | FAOSTAT, Pink Sheet, Cotrisa, ODEPA, en términos reales |

Cada columna está descrita en [`../docs/analysis_layer.md`](../docs/analysis_layer.md) y las reglas de uso (qué no se debe hacer con cada tabla) en la misma página.

## Reconstruir

```bash
mpchile ingest --start-year 1994 --end-year 2026 && mpchile build && mpchile volume
mpchile macro && mpchile panel && mpchile supply
mpchile datasets && mpchile faostat && mpchile pinksheet && mpchile cotrisa && mpchile reference
python scripts/download_comtrade.py          # comercio exterior (la API pública exige pausas; tarda y puede esperar cuota)
python scripts/build_agroclimate.py --era5 ../chile-weather-forecasting/data/raw/era5   # índices de clima
mpchile compact --delete     # opcional: convierte los CSV grandes a Parquet y verifica antes de borrar
```

`mpchile compact` deja `data/raw/` intacto. Un archivo solo se borra después de comprobar que su versión comprimida tiene las mismas filas, los mismos no nulos y las mismas sumas que el original.

## Compartir los datos procesados

Para entregar los datos sin que cada persona los reconstruya, lo recomendado es publicar `data/analysis/*.parquet` (unos 50 MB) como archivo adjunto de un *Release* de GitHub y no dentro del historial de Git.
