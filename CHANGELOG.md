# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [2.0.0] - 2026-10-31

### Agregado
- Informe de mercado **v2.0**, "Qué subió y qué cayó en el campo chileno, y por qué": 43 páginas, 21 figuras, 50 referencias APA 7, portada con tablero, resumen de una página, glosario, escenarios condicionales, conclusiones y límites.
- Análisis explicativos (`report/drivers.py`): puente multiplicativo del precio real (dólares, tipo de cambio, inflación y margen local), oferta y precio de la manzana, valor de exportación de la cereza por temporada, ingreso por hectárea, fertilizantes frente a trigo y exploración climática.
- Gráficos de cascada, dispersión y miniaturas (`report/svgextra.py`).
- Guía de redacción de informes de mercado agrícola (`docs/guia_de_redaccion_informes.md`).
- Verificaciones automáticas al construir el informe: citas y referencias consistentes, rayas largas y muletillas prohibidas, marcadores de figura sin resolver.
- Datos curados pequeños versionados: cultivos de FAOSTAT y clima diario de NASA POWER.
- Documentación de repositorio: `CONTRIBUTING.md`, índice de `docs/`, plantillas de incidencias y de cambios.

### Cambiado
- El informe se reorganizó en módulos (`ctx.py`, `chapters_*.py`, `helpers.py`); `build_report.py` solo ensambla.
- Tipografías incrustadas (Hanken Grotesk y Source Serif 4, licencia OFL); el HTML sigue siendo un solo archivo sin recursos externos.
- El repositorio pasó de `precios_materias_primas_chile` a `precios-agricolas-chile`. El paquete Python y el comando `mpchile` conservan su nombre.

### Corregido
- La cifra de cereza ya no se presenta como caída lineal: el valor de exportación por temporada muestra un escalón en 2024/25.
- Las cifras de vino distinguen el piso de 2024 de la recuperación de 2025 y 2026.

## [1.0.0] - 2026-10-30

### Agregado
- Primera versión del informe (23 páginas) y del pipeline de descarga, limpieza, conversión de unidades, panel mensual en pesos reales y análisis por producto.

## [0.1.0]

- Biblioteca inicial de datos agrícolas trazables y evaluación temporal de precios.
