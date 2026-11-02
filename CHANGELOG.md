# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## [2.1.0] - 2026-11-02

### Agregado
- Competencia en uva de mesa: Perú pasó de 149 mil a 715 mil toneladas exportadas entre 2012 y 2025 y supera a Chile desde 2023 (UN Comtrade).
- Comercio exterior con UN Comtrade (`comtrade.py`, `scripts/download_comtrade.py`): la aduana china confirma la caída del valor de la cereza chilena en 2025 y su participación de 98,7% en las importaciones chinas.
- Ejercicio de margen de la cereza: la ficha de ODEPA (2016-17) actualizada con el índice de costos laborales del INE (`ine.py`, `fichas.py`) da un costo cercano a USD 2,5 por kilo y un equilibrio de unos USD 5,2 de FOB; solo 2024/25 y 2025/26 quedan bajo él, con análisis de sensibilidad.
- Índices agroclimáticos por sitio y año desde ERA5 (`agroclimate.py`, `scripts/build_agroclimate.py`) y una prueba contra rendimiento, exportación y precio con 24 temporadas; los indicios son débiles y el informe lo declara.
- Pruebas para cada módulo nuevo.

### Cambiado
- La exploración climática del informe pasó de dos ciudades (NASA POWER) a seis puntos (ERA5) y de una correlación a una tabla de 24 combinaciones con umbral de significancia.
- El informe tiene ahora 25 figuras y 50 páginas.
- Corrección: el cambio de origen del trigo importado (hacia Argentina desde 2024/25) no explica la caída inicial del margen local, que ocurrió hasta 2022 con una brecha Argentina-EE.UU. estable; el informe lo reclasifica como explicación de certeza baja.

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
