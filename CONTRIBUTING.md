# Cómo contribuir

Gracias por querer mejorar este proyecto. Las reglas de fondo están en [`AGENTS.md`](AGENTS.md): datos trazables, sin fabricar observaciones, sin mezclar productos distintos y con escenarios explícitos.

## Preparar el entorno

```bash
python -m venv .venv && source .venv/bin/activate     # en Windows: .venv\Scripts\activate
pip install -e ".[dev,parquet,grains,excel]"
make check         # compila y corre todas las pruebas (no requieren datos descargados)
```

## Flujo de trabajo

1. Cree una rama desde `main` con un nombre descriptivo (`fix/serie-faostat`, `feat/precios-palta`).
2. Haga cambios pequeños y con pruebas. Todo código nuevo con lógica de datos lleva una prueba offline en `tests/`.
3. Ejecute `make check` antes de abrir el pull request.
4. Describa en el pull request qué cambió, por qué y cómo se verificó.

Mensajes de commit: una línea en imperativo con prefijo (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`), por ejemplo `fix: respetar la codificación de la respuesta mensual`.

## Reglas de datos

- Conserve originales, URL, fecha de captura y checksum. Una corrección de la fuente es un nuevo snapshot, no un reemplazo silencioso.
- No junte productos distintos (maíz grano con choclo, poroto seco con verde, precio de exportación con mayorista).
- Un precio por kilo solo existe si la etiqueta declara el peso del envase.
- Las series estacionales conservan sus faltantes: no se rellenan con ceros.
- No suba credenciales ni archivos `.env`. El Banco Central se configura con `BCCH_USER` y `BCCH_PASSWORD`.
- Los datos descargados (`data/raw`, `data/processed`, `data/analysis/*.parquet`) no se versionan; solo los resultados pequeños que el informe necesita.

## Informe

- Las cifras del texto salen de `report/ctx.py` y `report/drivers.py`; no se escriben a mano.
- Una fuente nueva se agrega a `report/referencias.py` **después de abrirla y verificar la cifra en la página original**. El informe no se construye si hay una cita inexistente o una referencia sin citar.
- Siga [`docs/guia_de_redaccion_informes.md`](docs/guia_de_redaccion_informes.md): conclusión primero, mecanismo y evidencia independiente, y grado de certeza.
- Reconstruya con `make report` y revise el PDF antes de subir cambios en `report/dist/`.

## Reportar un problema

Abra una incidencia con la plantilla correspondiente. Si es un problema de datos, indique el producto, el período y la fuente.
