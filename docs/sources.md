# Fuentes y decisiones de comparabilidad

Verificación web: 28 de octubre de 2026. Este catálogo describe recursos encontrados;
no garantiza cobertura uniforme entre productos. Después de esa investigación se
completó la carga real 2020–2025 mediante GitHub Actions: consultar
`data/snapshots/initial_2020_2025/summary.json` y manifests de cada recurso.

## Fuente primaria implementada: ODEPA mayoristas

- Catálogo: https://datos.odepa.gob.cl/es/dataset/precios-mayoristas-de-frutas-y-hortalizas
- API CKAN: https://datos.odepa.gob.cl/api/3/action/package_show?id=precios-mayoristas-de-frutas-y-hortalizas
- Recursos CSV anuales publicados: 1994–2026. La existencia de cada recurso no garantiza
  continuidad de cada producto o mercado durante todos esos años.
- Frecuencia declarada: días hábiles. Precios y volúmenes de transacciones mayoristas;
  no equivalen a precios al productor, exportación ni venta al consumidor.
- Mercados de Arica y Parinacota, Coquimbo, Valparaíso, Metropolitana, Maule, Ñuble,
  Biobío, La Araucanía y Los Lagos. No constituye un censo nacional de precios.
- Dimensiones: fecha, región del mercado y código, mercado, subsector, producto,
  variedad/tipo, calidad, unidad comercial, origen. Medidas: volumen y precios mínimo,
  máximo y promedio. El diccionario identifica el promedio como ponderado por volumen.
- Moneda: pesos chilenos; mantener unidad comercial original. No convertir cajas,
  bandejas o sacos a CLP/kg sin equivalencia de peso documentada.
- `Region` es la localización del mercado; `Origen` identifica procedencia del producto.
  El clima del mercado no representa automáticamente el clima de cultivo.
- Licencia de catálogo: CC BY; conservar atribución a ODEPA y trazabilidad.

Ejemplo verificado de metadatos (2026): recurso `580beca0-e87e-4dd4-9e8a-0bd92773f4a6`,
CSV de aproximadamente 31,5 MiB según su ficha. URL:
https://datos.odepa.gob.cl/dataset/33f10516-acbe-4446-b633-68244b9b6b26/resource/580beca0-e87e-4dd4-9e8a-0bd92773f4a6/download/precio_mayorista_fruta-hortaliza_2026.csv

El catálogo indica DataStore activo; una segunda ruta de adquisición es
`/api/3/action/datastore_search?resource_id=UUID&limit=...&offset=...`.
Se prefiere CSV anual para reproducir archivos completos y verificar SHA-256.
El navegador rechazó el CSV por tipo de contenido y no pudo recuperar DataStore.
La descarga CSV completa sí se verificó posteriormente en GitHub Actions; la
muestra de observaciones en el snapshot procede de esos archivos reales.

## Otras opciones y separación de mercados

1. Interfaz oficial histórica ODEPA:
   https://www.odepa.gob.cl/precios/mayoristas-frutas-y-hortalizas
   Es la fuente declarada por el catálogo. Usar como referencia y verificación;
   evitar scraping HTML cuando el mismo organismo entrega CSV/API estructurados.
2. Maíz grano y poroto seco requieren revisar catálogos específicos de precios al
   productor/cereales. Choclo fresco y poroto verde mayorista no son sustitutos
   de esas materias primas. El conector descubre productos sin forzar equivalencias.
3. Cereza y uva mayoristas locales no equivalen a precios FOB de exportación.
   Crear fuentes separadas para comercio exterior y controlar moneda, calidad,
   variedad y composición de destinos antes de comparar.
4. Series mensuales históricas de ODEPA desde 1975 (según sección oficial;
   disponibilidad específica por producto pendiente de inspección):
   https://www.odepa.gob.cl/precios/series-de-precios . Incluye categorías
   productor, mayorista, consumidor, insumos e internacionales. Es una alternativa
   para maíz grano; no debe concatenarse automáticamente a las series diarias.
5. Catálogo oficial de consumidor:
   https://datos.odepa.gob.cl/dataset/precios-consumidor . Incluye legumbres y
   cereales además de frutas/hortalizas. Es pertinente para poroto seco de venta
   minorista, con un conector y `market_level=retail` propios aún pendientes.
6. Maíz productor: los informes oficiales de avance de campaña describen precios
   domésticos por poderes compradores de Cotrisa complementados por ODEPA:
   https://www.odepa.gob.cl/publicaciones/avance-de-la-campana-de-maiz-2024-25/attachment/informe-semana-del-26-de-mayo-al-01-de-junio-2025 .
   No equivale a precio spot observado en cada predio. Descarga histórica y
   contrato histórico amplio pendientes. El conector `grains.py` ya descarga y
   valida el informe de semana 22 de 2025, separado del mayorista fresco.

La investigación posterior identificó contratos públicos de la aplicación
mensual, productos concretos e IPC de la interfaz. Las consultas de poroto seco
minorista y maíz FOB argentino fallaron con errores HTTP/HTML, por lo que no se
promovieron como datos. Véase `docs/monthly_source.md` y los diagnósticos
versionados en `data/snapshots/monthly_candidates/`.

## Criterios de ingestión

Preferir autoridad pública y descarga estructurada; descubrimiento dinámico de
recursos evita construir URLs supuestas. Guardar recurso original, metadatos CKAN,
hora de recuperación, URL y checksum. La normalización falla si faltan columnas
del contrato y conserva todos los campos originales en `source_record`.
No rellenar días sin transacción, productos fuera de temporada o períodos faltantes
como precio cero. Una misma fecha con distintas variedades/unidades es otra serie.
No publicar pronósticos hasta que exista descarga verificable y evaluación temporal.

## Estado de fuentes implementadas (actualizado 30 de octubre de 2026)

Todas se ejecutan localmente con `python -m materias_primas_chile.cli <comando>`; los datos
originales quedan en `data/raw/` con hash y manifiesto, y los normalizados en `data/processed/`.

| Comando | Fuente | Qué trae | Unidad / límite de interpretación |
|---|---|---|---|
| `ingest` + `build` | ODEPA mayoristas frutas y hortalizas (CKAN) | Diario 1994–2026, 86 productos, 9 regiones | CLP por unidad comercial original; no es precio al productor |
| `series` | ODEPA series de tiempo mensuales (1975–2026) | Productor, mayorista, consumidor, insumos, internacional (trigo, maíz, arroz, avena FOB en US$/t) | Nominal; consumidor y supermercado con IVA, resto sin IVA. Internacional es referencia, no precio chileno |
| `bcch` | Banco Central, API Siete (requiere `.env`) | IPM trigo/maíz/cebada/arroz 1992–2011, IPC, exportaciones | Mayoría son índices o valores en USD, no precios en pesos |
| `cotrisa` | Cotrisa tablas HTML | Precio al productor de trigo, maíz, arroz y avena por región, comprador y localidad | $/qqm, solo campaña vigente (trigo desde 2024-03, maíz desde 2025-03) |
| `faostat` | FAOSTAT vía HDX | Precio al productor anual/mensual 1991–2025 en CLP/t y USD/t: cereales, legumbres, papa, frutas, leche | Definición FAO del producto, sin variedad ni calidad; rezago anual |
| `datasets` | ODEPA CKAN: consumidor semanal, uva de vinificación, comercio exterior | Consumidor 2008–2026 por región y punto de venta; exportaciones/importaciones con USD FOB/CIF y volumen | Uva sin unidad declarada (`no_declarada`); valor unitario de exportación es DERIVADO (USD FOB / kilo neto) |
| `macro` | Banco Central: IPC general empalmado (1928–2026) y dólar observado mensual (1982–2026) | Deflactar a pesos de septiembre de 2026 y pasar a USD | El IPC se empalma desde 5 bases oficiales por sus meses de traslape; el último mes con IPC es la base |
| `pinksheet` | Banco Mundial, Pink Sheet | 71 commodities mensuales desde 1960 (fertilizantes, energía, cereales, banano, naranja) | USD nominales, referencia internacional, no precios chilenos |
| `supply` | ODEPA-CIREN catastro frutícola | Hectáreas y árboles por especie, variedad, región y año de plantación (2008–2025) | Zonas distintas cada año: comparar solo regiones medidas en ambos años |
| `volume` | ODEPA mayorista | Volumen mensual por serie en unidades comerciales | La unidad del volumen es inferida (ver `volume.py`) |
| `panel` | Panel mayorista | Variedad armonizada, CLP/kg, precio real, USD/kg | Ver `docs/analysis_layer.md` |
| `reference` | Consumidor, exportación y series externas | Consumidor mensual por variedad; FOB ponderado por kilos; series externas en términos reales | Exportación es valor unitario derivado, no precio publicado |
| `compact` | — | CSV grandes a Parquet/gzip con verificación previa a borrar | `data/raw` no se toca |
| `index` | — | `data/curated/source_index.csv`: fuente, producto, unidad, moneda, cobertura y N° de observaciones | No mezcla unidades |

### Por qué fallaba la serie mensual de ODEPA (HTTP 500)

La aplicación oficial envía, además de los filtros, dos campos de auditoría: `ip` (la IP pública de
quien consulta, obtenida de `api.ipify.org`) y `jsonParam` (registro de los filtros elegidos). El
transporte anterior (`monthly.py`) los omitía a propósito y el servidor respondía 500. El cliente
`odepa_series.py` los envía con valores verdaderos y reproduce exactamente la respuesta del
navegador (comprobado byte a byte para el maíz Yellow N° 2, 1975–2026). La IP no se guarda en los
manifiestos. Las consultas de consumidor tardan unos 15 s por serie; el cliente espera y reintenta
con pausas crecientes ante 403/429/5xx.

### Vacíos conocidos

- Precio interno al productor de trigo/maíz/avena **anterior a 2024–2025**: solo FAOSTAT (anual/mensual, CLP/t).
- Precios de exportación **por caja o variedad**: no publicados; solo el valor unitario derivado de comercio exterior.
- Lo Valledor, ASOEX, Fedefruta, FAO API y Aduanas (portal antiguo) no responden o no ofrecen descarga; ODEPA ya consolida los mercados mayoristas.
- INE no publica IPC por producto descargable; la vía viable es el Banco Central.
- Volúmenes: la columna `volume` del mayorista y de comercio exterior existe, pero aún no está validada ni analizada.

### Quiebres estructurales conocidos (cuidado al comparar años)

- **Exportaciones, 2012:** el Sistema Armonizado cambió los códigos de fruta fresca. Antes de 2012 la cereza fresca está en
  "Cerezas frescas"; desde 2012, en 08092919 ("Las demás cerezas dulces frescas"). Para series largas hay que empalmar ambos códigos.
- **Catastro frutícola:** la cobertura regional cambia cada año (de 1 a 9 regiones). Antes de comparar dos años, intersectar regiones.
- **Mayorista, variedades:** la cobertura de variedades nombradas crece con el tiempo; "Lapins" aparece desde diciembre de 2007.
- **Consumidor semanal 2008:** el producto viene compuesto con "|" (producto|variedad|calidad) y sin precio mínimo ni máximo.
