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
