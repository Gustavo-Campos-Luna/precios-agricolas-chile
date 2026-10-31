# Informe: Qué subió y qué cayó en el campo chileno, y por qué

Informe de mercado (versión 2.0), no un artículo científico: plantea una pregunta, la responde con datos oficiales, explica las causas con prensa especializada, informes sectoriales y literatura académica (citados en APA 7) y declara sus límites. La estructura y el estilo siguen la guía [`../docs/guia_de_redaccion_informes.md`](../docs/guia_de_redaccion_informes.md).

## Salidas

| Archivo | Qué es |
|---|---|
| `dist/informe_precios_agricolas_chile.html` | Informe completo en un solo archivo, con tipografías incrustadas y sin recursos externos. Se puede enviar por correo o abrir sin conexión. Modo claro y oscuro automáticos. |
| `dist/informe_precios_agricolas_chile.pdf` | Versión impresa (A4), generada desde el mismo HTML. |
| `data/*.csv` | La tabla de cada figura y de cada análisis explicativo. Cualquier cifra del informe se puede auditar desde aquí. |

## Contenido

Portada con tablero de variaciones, resumen de una página, guía de lectura y glosario, visión de conjunto, cuatro capítulos por rubro (cereza; manzana y uva de mesa; trigo y maíz; uva para vino), un capítulo de factores comunes (cantidad, cliente, dólar, costos, clima), escenarios condicionales, conclusiones, límites, referencias y anexo de reproducibilidad.

## Construir

```bash
python report/build_report.py          # HTML y CSV
python report/build_report.py --pdf    # además el PDF (usa Microsoft Edge o Chrome en modo headless)
```

Requiere haber construido antes `data/analysis/` y `data/processed/` (ver [`../data/README.md`](../data/README.md)). Si no hay Edge ni Chrome, abra el HTML y use *Imprimir, Guardar como PDF*. El nombre del autor de la portada se define en `chapters_front.py` (`AUTHOR`); si queda vacío, se omite.

## Cómo está hecho

| Archivo | Función |
|---|---|
| `build_report.py` | Ensambla capítulos, incrusta las tipografías y verifica el resultado (citas, rayas largas, muletillas, marcadores sin resolver) |
| `ctx.py` | Calcula todas las cifras y construye todas las figuras |
| `drivers.py` | Análisis explicativos: puente multiplicativo del precio, oferta y precio, valor de exportación por temporada, ingreso por hectárea, insumos, clima |
| `report_data.py` | Series y tablas base; reutiliza las reglas de `scripts/analysis_*.py` |
| `chapters_front.py`, `chapters_fruit.py`, `chapters_grain.py`, `chapters_close.py` | Texto de cada capítulo |
| `helpers.py` | Formato chileno de números, cajas de lectura, fichas y maquetación de capítulos |
| `svgcharts.py`, `svgextra.py` | Gráficos SVG sin dependencias: líneas, barras, divergentes, mancuernas, cascada, dispersión y miniaturas |
| `referencias.py` | Referencias APA 7 y citas en el texto; el informe falla si una cita no existe o si una referencia no se cita |
| `style.css`, `fonts/` | Tipografía (Hanken Grotesk y Source Serif 4, licencia OFL), paleta, modo oscuro, impresión y A4 |

### Decisiones de diseño

- **Ninguna cifra del texto se escribe a mano**, salvo las de fuentes externas, que llevan su cita.
- **Paleta propia, sin azul ni naranja.** Cinco colores de producto validados contra daltonismo y contraste con el validador de la guía de visualización de datos, en modo claro y oscuro.
- **Sin doble eje.** Dos magnitudes distintas van en dos gráficos alineados o en índices sobre una misma base.
- **Accesibilidad.** Cada gráfico tiene descripción (`aria-label`), información al pasar el cursor y una tabla de datos plegable. Las líneas se cortan donde faltan datos: nunca se interpola.
- **Explicaciones con grado de certeza.** Cada "por qué" separa el dato, el mecanismo, la evidencia independiente y cuán firme es; lo que no se pudo medir se declara.
- **Verificaciones automáticas al construir:** numeración de figuras según el orden real del documento, referencias cruzadas válidas, citas y referencias consistentes, ausencia de rayas largas y de muletillas de la guía de redacción.

### Cómo agregar o cambiar una fuente

1. Abra la fuente y verifique cada cifra en la página original (los agentes de investigación se equivocan: una cifra de margen de la urea no existía en el PDF citado).
2. Agregue la entrada en `referencias.py` (clave, cita corta y referencia APA).
3. Cite con `cite("clave")` o `narrative("clave")` en el capítulo correspondiente. Si olvida citarla, o cita una clave inexistente, el informe no se construye.

## Fuentes de contexto

Las noticias, informes sectoriales y artículos académicos se abrieron y leyeron antes de citarse (30 de octubre de 2026) y sus cifras se parafrasean. Se descartaron las páginas que no se pudieron abrir. Cuando una nota y los datos oficiales difieren (por ejemplo, exportaciones por temporada y por año calendario), el informe usa ambas y las rotula. Los datos de ingreso semanal a packing no son públicos y el informe lo declara.

## Uso de IA

El procesamiento de datos y la redacción se hicieron con asistencia de Claude (Anthropic). El código del repositorio permite verificar cada cifra.
