# Reglas de trabajo del repositorio

Trabajar exclusivamente en este repositorio. El objetivo es una biblioteca de
datos agrícolas de Chile y evaluación de precios reproducible, con escenarios
climáticos explícitos. Se permite dividir tareas entre agentes cuando sean
independientes; coordinar propiedad de archivos y revisar integración.

- Preferir CSV, XLSX o API pública oficial antes de scraping de una interfaz.
- Conservar originales, URL, captura UTC, checksum y consulta exacta. Las
  correcciones de una fuente son otro snapshot, no un reemplazo silencioso.
- No fabricar observaciones ni presentar fixtures como datos descargados.
- Separar mercado comercial, región de origen y ubicación climática. Puntos de
  ciudades son proxies exploratorios, no clima representativo de una región.
- Conservar variedad, calidad, origen, unidad y moneda. Solo convertir pesos o
  conteos explícitos en la etiqueta, con método auditable. No juntar maíz grano
  con choclo, poroto seco con verde ni precios de exportación con mayoristas.
- Las series estacionales conservan sus faltantes. No rellenar con cero.
- Toda validación predictiva separa por tiempo. No usar clima futuro observado,
  normalización ajustada en todo el dataset ni revisiones futuras sin advertirlo.
- Escenarios son supuestos condicionales, no efectos causales demostrados.
- No publicar proyecciones como actuales si el corte de datos está desactualizado.
- Evitar secretos en código, manifiestos, queries y logs. Mantener TLS verificado.
- Los commits generados por Actions deben incorporar cambios remotos por rebase
  y fallar ante conflictos; nunca forzar actualizaciones de `main`.

Comprobación offline desde la raíz:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m compileall -q src tests scripts
```

Para CI/paquete usar `python -m pip install -e '.[dev,parquet,grains]'`,
`python -m pytest` y `python -m build`. Las pruebas de red se acreditan por los
workflows y manifests, separadas de los fixtures de las pruebas unitarias.
