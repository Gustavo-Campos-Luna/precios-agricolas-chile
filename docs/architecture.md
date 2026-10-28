# Arquitectura y operación

## Capas

1. **Raw / bronze**: copia del recurso publicado, metadatos del catálogo, fecha UTC de captura y SHA-256. No se modifica un original para limpiarlo. Los archivos se identifican por contenido o ejecución; los datasets anuales abiertos pueden corregirse retrospectivamente.
2. **Processed / silver**: normalización de fechas, valores y etiquetas, conservando valores originales y dimensiones. Filas inválidas van a cuarentena con motivo; no se imputan silenciosamente.
3. **Curated / gold**: panel mensual dentro de una serie comparable. Se conservan variedad, calidad, mercado, origen y unidad en la identidad; la mediana mensual no representa un promedio nacional ni precio de productor. Conteos de observaciones acompañan cada mes.
4. **Artifacts**: métricas de backtest por serie/modelo/horizonte, pronósticos con estado de abstención y escenarios explícitos. Se conserva el corte de entrenamiento.

La biblioteca Python es independiente del CLI. Los conectores se ejecutan bajo demanda; las pruebas offline usan fixtures sintéticos claramente identificados. CI prueba cambios de código sin depender de la disponibilidad de ODEPA o NASA.

## Identidad y grano

No unir por nombre de producto solamente. Una observación de precios exige fecha, producto, variedad, calidad, mercado, origen, unidad, moneda y tipo de precio. Debe conservar además fuente y recurso. Una fila anual puede distinguirse por dimensiones adicionales; inspeccionar el esquema real antes de fijar una clave primaria. La duplicación de claves falla en la capa mensual en vez de sumar precios.

`series_id` es una identidad estable de las dimensiones comerciales, excluye fecha y precio. Registrar la versión de normalización. Las etiquetas regionales describen el mercado cuando la fuente no acredita origen productivo. No asignar meteorología del mercado como si fuera meteorología del cultivo.

## Almacenamiento y entrega

CSV UTF-8 para interoperabilidad; Parquet opcional para uso analítico de mayor volumen. Git conserva código, contratos, documentación y fixtures pequeños; no datasets masivos. Para producción almacenar raw/processed/curated en un bucket versionado o filesystem respaldado, con manifests y catálogo. No es necesario introducir una base de datos transaccional para archivos anuales de consulta analítica.

Los manifests y los resultados de calidad son artefactos de cada ejecución. Se recomienda una retención de cada snapshot original que cambie de hash. El CLI no instala credenciales ni modifica permisos del servicio.

## Ruta de crecimiento

- Incorporar maíz grano con conector específico de precios a productor/importación; mantenerlo separado de choclo mayorista.
- Añadir índices de inflación y tipo de cambio con fecha de publicación antes de comparar precios reales o valores de exportación.
- Construir un mapa verificable de origen agrícola a estación/polígono climático. Mantener las ubicaciones sin correspondencia como faltantes.
- Incluir cosecha, volúmenes de oferta, exportaciones, calendario y precios internacionales; el clima por sí solo no explica el precio.
- Al incorporar tareas programadas: validar el snapshot, publicar resultados solo si pasa el contrato y alertar ante cambios de esquema o descargas vacías.

## Estado inicial

No se debe considerar un pronóstico validado hasta completar descargas reales, revisión de unidades y evaluación temporal. Una ejecución que falla por red no equivale a un dataset sin observaciones. Los tests sintéticos comprueban comportamiento del código, no rentabilidad ni precisión comercial.
