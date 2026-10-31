# Guía de redacción de informes de mercado agrícola

Esta guía resume cómo se estructuran, explican y redactan los informes de precios agrícolas (ODEPA, FAO, USDA, Banco Mundial) y qué errores aparecieron al construir este informe. `report/build_report.py` hace cumplir parte de ella (citas verificadas, sin rayas largas, sin muletillas).


Guía destilada de cómo trabajan ODEPA (boletines de fruta y de cereales), FAO (Food Outlook, Food Price Index), USDA FAS GAIN, Banco Mundial (Commodity Markets Outlook), RaboResearch y el IPoM del Banco Central, más los errores que aparecieron al hacer un informe real. El objetivo no es describir un precio, es explicar **por qué se movió** y **qué podría cambiarlo**.

## 1. Estructura (20 a 30 páginas, lector no técnico)

1. **Portada con lo esencial a la vista**: título que afirma algo, cifras clave con su tendencia.
2. **Resumen de una página**: conclusión primero, cinco hallazgos con cifra, lo que no se sabe.
3. **Cómo leer**: precio FOB frente a precio al productor, mayorista o consumidor; temporada frente a año calendario; pesos reales frente a nominales.
4. **Panorama**: todos los productos en una misma vara (un gráfico).
5. **Un capítulo por rubro**: titular con conclusión, gráfico de precio, mecanismo (oferta, demanda, costos, mercado externo, tipo de cambio, clima), voces del sector, qué se espera y qué lo cambiaría.
6. **Factores comunes**: dólar, costos, clima, logística.
7. **Qué esperar**: escenarios con su supuesto explícito.
8. **Conclusiones, límites, referencias, anexo de datos**.

Los boletines institucionales (ODEPA, USDA) abren con la cifra total y encadenan valor, volumen y precio unitario. Los informes de bancos abren con una tesis completa y declaran de qué depende el pronóstico. Copie ese orden: tesis, evidencia, condiciones.

## 2. Cómo explicar un "por qué"

Cada explicación lleva cuatro piezas: **el dato**, **el mecanismo**, **la evidencia independiente** (otra fuente, otra serie) y **el grado de certeza**. Si falta la tercera, se escribe como hipótesis.

- Cadena de argumento típica: más volumen, entonces menos valor unitario, entonces menor retorno, entonces ajuste de huertos.
- Separe siempre **hecho** (los precios bajaron), **asociación** (coincide con el alza de oferta) y **causa** (solo si hay un mecanismo y descarta alternativas).
- Contraste cada hipótesis con lo que la contradice. Si una fuente desmiente la lectura, se dice.
- Pruebe la hipótesis rival antes de publicar: ¿el cambio es solo de mezcla (otro mercado, otra calidad)? ¿Hay un quiebre en la serie? ¿El punto final elegido decide el resultado?
- Las proyecciones llevan su supuesto ("si el clima es normal", "mientras no haya nuevas trabas").

## 3. Redacción

- **Titular**: sujeto, verbo y cifra. "La cereza vende más y recibe menos: USD 4,6 por kilo". Los gráficos también afirman algo.
- **Voz**: activa en lo propio; atribución clara en lo ajeno ("según ODEPA", "el USDA proyecta").
- **Párrafo**: una idea, la cifra en la primera o segunda oración, el matiz al final.
- **Vocabulario del sector**: retorno al productor, temporada, huerto, packing, FOB, liquidación, calibre, consignación. Evitar abstracciones ("dinámicas", "panorama").
- **Parafrasear**: cambie la estructura, no solo los sinónimos; cita textual solo para definiciones, y no más de 12 palabras seguidas. Todo lo parafraseado lleva cita.

### Tics de texto generado por IA que hay que sacar

- Aperturas y cierres de manual ("En el dinámico mundo de...", "En conclusión, es fundamental..."). Empiece por la cifra y termine con la pregunta abierta concreta.
- Adjetivos vacíos: crucial, clave, robusto, significativo, panorama complejo. Ponga el número.
- Triadas automáticas y la estructura "no solo X, sino también Y" repetida.
- Párrafos que parten igual ("Por otro lado", "Cabe destacar", "Es importante señalar").
- Metáforas gastadas (tormenta perfecta, montaña rusa) y verbos muletilla (evidenciar, jugar un rol, tener un impacto): use subir, bajar, pesar sobre.
- Rayas largas y dos puntos en cada oración; negritas por todos lados; listas de tres elementos en cada párrafo.
- Frases que explican lo que el lector acaba de leer.

## 4. Investigación y verificación (lo que salió mal y cómo evitarlo)

1. **Abra cada fuente y lea la cifra en la página**. Una nota de prensa puede estar mal rotulada (confundió una temporada con otra).
2. **Los agentes de investigación se equivocan.** Uno entregó "una alza de 10% en la urea absorbe 58,6% del margen del maíz"; al abrir el PDF esa cifra no existía (correspondía a otra cosa). Verifique por su cuenta toda cifra que sostenga una explicación central.
3. **Alinee las bases**: temporada contra año calendario, producción por año de cosecha contra año de embarque. Pruebe el desfase con los datos (por ejemplo, correlación de la producción con las exportaciones de la temporada).
4. **Busque quiebres de serie** antes de comparar (la serie chilena de FAOSTAT cambia de base antes de 2015; el catastro frutícola mide regiones distintas cada año; el código aduanero de la cereza cambió en 2012).
5. **No elija un solo punto final**: muestre la trayectoria (piso, recuperación) o el resultado depende del año que se escoja.
6. **Documente los vacíos**: si no existe un dato público (por ejemplo, ingreso semanal a packing), se escribe y se nombran los sustitutos.
7. Las fuentes que no se pudieron abrir se descartan y se dice.

## 5. Gráficos

- Sin doble eje. Dos magnitudes, dos paneles alineados.
- Precios en términos reales; el nominal solo para mostrar cuánto engaña.
- Etiquetas directas, color por producto constante en todo el informe, línea cortada donde faltan datos (nunca interpolada), tabla de datos para quien no lee el dibujo.
- Puente multiplicativo para descomponer un precio: dólares x tipo de cambio / inflación x prima local. Los factores deben cerrar exactamente el cambio observado.

## 6. Formato APA 7 en español

Autor. (Año, día de mes). *Título*. Medio. URL. Sin autor: el título pasa a la posición del autor. Datos que cambian: "Recuperado el 30 de octubre de 2026 de URL". Letras a, b, c consecutivas para el mismo autor y año. Alfabético por el autor tal como aparece (organizaciones por su nombre completo). El informe no debe construirse si una cita no existe o una referencia queda sin citar.

## 7. Lista de revisión final

- [ ] ¿La primera página dice qué pasó y por qué, con cifras?
- [ ] ¿Cada capítulo responde "¿por qué?" y "¿qué podría cambiarlo?"
- [ ] ¿Cada cifra externa se verificó en su página?
- [ ] ¿Se rotuló temporada frente a año calendario y real frente a nominal?
- [ ] ¿Se probó la explicación rival (mezcla, quiebre, punto final)?
- [ ] ¿Hay un apartado de límites y de lo que no se pudo medir?
- [ ] ¿Se leyó en voz alta sin encontrar frases de manual?
