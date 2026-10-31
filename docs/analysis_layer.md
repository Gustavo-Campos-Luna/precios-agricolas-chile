# Capa analítica: tablas listas para análisis

Todo se genera localmente y se puede reconstruir desde `data/raw/` (los originales con hash y manifiesto).
Nada de esto se versiona en Git. Parquet se lee con `pd.read_parquet(...)`.

## Orden de construcción

```
ingest → build → volume → macro → panel → supply → (pinksheet, faostat, series, bcch, cotrisa, datasets) → index → compact
```

`compact` va al final: convierte los CSV grandes a Parquet o gzip, verifica cada archivo contra el original
(filas, no nulos y sumas) y solo entonces borra el CSV. `data/raw/` no se toca.

## Tablas

| Archivo | Una fila es | Para qué sirve |
|---|---|---|
| `data/analysis/prices_monthly.parquet` | Una serie homogénea en un mes (producto, variedad, calidad, origen, unidad, mercado) | Panel principal mayorista 1994–2026 |
| `data/curated/prices/daily.parquet` | Un precio diario por serie (sin `source_record`) | Detalle diario; el JSON crudo está en `data/raw` |
| `data/analysis/orchards.parquet` | Superficie plantada por año, región, especie, variedad y año de plantación | Oferta: cuántas hectáreas hay de cada variedad |
| `data/analysis/orchards_coverage.csv` | Año × región medido por el catastro | Saber qué años son comparables |
| `data/processed/bcch/cpi_index.csv` | Mes (1928–2026-09), índice IPC con último mes = 100 | Deflactar |
| `data/processed/bcch/usd_clp_monthly.csv` | Mes, dólar observado promedio | Pasar a USD |
| `data/processed/pinksheet/monthly_prices.csv` | Mes × commodity internacional, USD | Fertilizantes, energía y cereales internacionales |
| `data/curated/source_index.csv` | Fuente × producto × unidad | Qué hay y con qué cobertura |

## Columnas clave de `prices_monthly.parquet`

- `price`, `price_vwap`: precio mediano del mes y precio ponderado por volumen, **en la unidad de la serie** (`unit`).
- `price_clp_kg`, `price_vwap_clp_kg`: solo si la etiqueta declara el peso del envase (76% de las filas). Nunca se estima un peso.
- `price_real`, `price_clp_kg_real`: pesos de septiembre de 2026 (precio × 100 / IPC). El último mes con IPC es la base;
  octubre de 2026 queda vacío porque aún no hay IPC. No se extrapola.
- `price_usd_kg`: `price_clp_kg` ÷ dólar observado promedio del mes (nominal).
- `variety_key` / `variety_canonical` / `variety_group`: ver `varieties.py`. Canonical corrige tipeos y sinónimos
  (Sultanina = Thompson Seedless). Group junta clones (Royal Gala, Brookfield, Galaxy → gala). Usar canonical para análisis
  fino y group para agregado.
- `volume_units`: suma del mes en **unidades comerciales de la serie** (cajas, bandejas, sacos, bins). Inferido, no declarado
  por ODEPA. `volume_kg_est` solo con peso explícito. `volume_basis` marca las unidades por pieza.

## Reglas de uso (lo que NO se debe hacer)

1. **No sumar ni promediar entre series de unidades distintas.** Una bandeja de 10 kg y una caja de 18 kg se comparan solo
   en `price_clp_kg`, y únicamente si ambas lo tienen.
2. **No tratar `price_clp_kg` ausente como cero.** Choclo, lechuga, ajo y similares se venden por pieza: comparar en `price`
   o `price_real` dentro de la misma unidad.
3. **Comparar años con precios reales**, no nominales. El nominal sobreestima las alzas de largo plazo.
4. **Superficie del catastro:** el catastro mide regiones distintas cada año, y los años con "9 regiones" miden sobre todo el sur
   (casi sin uva ni cereza). Compararla entre años solo dentro de las mismas regiones, y solo si esas regiones concentran al menos
   el 70% de la superficie histórica de la especie (lo que calcula `scripts/analysis_frutas.py`). Con menos, el resultado vale para
   esas regiones, no para el país. Es capacidad plantada, no cosecha.
5. **Cobertura mayorista:** 9 regiones, solo días con transacción. No es un censo nacional de precios ni precio al productor.
6. **Meses sin datos quedan sin datos.** Los productos de temporada no se rellenan.

## Fuentes de contexto (no mezclar con el panel mayorista)

Precio al productor (FAOSTAT, Cotrisa), consumidor (ODEPA semanal), exportación (valor unitario derivado de USD FOB ÷ kilo neto)
y referencia internacional (ODEPA, Pink Sheet) viven en sus propias tablas, con nivel de mercado, unidad y moneda explícitos.
Ver `docs/sources.md` y `data/curated/source_index.csv`.

## Informes de análisis (`data/analysis/reports/`)

Se regeneran con los scripts de `scripts/`; cada uno declara sus reglas y límites al inicio del archivo.

| Informe | Script | Qué responde |
|---|---|---|
| `cereza.md`, `uva.md`, `manzana.md`, `poroto_verde.md` | `analysis_frutas.py` | Precio real por kilo, por variedad, región y calidad; control de composición (mercado y calidad fijos); superficie solo si es comparable |
| `cereales.md` | `analysis_cereales.py` | Trigo, maíz, avena, cebada, arroz y poroto seco: productor (FAOSTAT, Cotrisa) frente a la referencia internacional |
| `vino.md` | `analysis_vino.py` | Uva de vinificación por variedad y región (unidad no declarada) |

### Quiebres de FAOSTAT detectados

La serie chilena de FAOSTAT cambia de base de medición: maíz, arroz y trigo saltan entre 2014 y 2015 (por ejemplo el trigo pasa de
79.448 a 170.879 CLP/t) y también hay saltos en 2012. Como el dólar no explica el cambio, se tratan como quiebre de la fuente:
`analysis_cereales.py` los detecta (salto anual mayor a x1,8) y usa solo el tramo posterior al último quiebre. Cruzar el quiebre
daría alzas falsas (el arroz, por ejemplo, pasaría de +29% a +86%).
