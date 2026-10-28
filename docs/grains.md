# Maíz grano: fuente adicional acotada

## Fuente comprobada

ODEPA publica informes semanales de avance de campaña con precios internos
aportados por poderes compradores a Cotrisa, complementados por ODEPA:
https://www.odepa.gob.cl/publicaciones/avance-de-la-campana-de-maiz-2024-25 .
La campaña 2024/25 tiene enlaces semanales de marzo a junio de 2025; la página
enlaza además la campaña 2023/24. No es una serie nacional diaria continua.

Informe utilizado para verificar el contrato, semana 22 (26 de mayo a 1 de junio):
https://www.odepa.gob.cl/wp-content/uploads/2025/05/Informe-semana-del-26-de-mayo-al-01-de-junio-2025.pdf .
Cuadro 1, páginas 2–3: referencia productor en pesos por quintal, columnas
2024 y 2025, regiones/empresas/contratos y promedio nacional. La fuente declara
consulta a Cotrisa el 3 de junio de 2025. Ese retraso importa al modelar con
información disponible históricamente. Los precios son nominales.
La página del informe declara publicación el 4 de junio: se usa esa fecha como
`available_at` conservador; fecha de consulta no implica publicación pública.

`grains.py` implementa una extracción conservadora para ese diseño 2024/2025:
solo acepta filas regionales con ambos años y variación explícita. No convierte
una única cifra en precio actual ni mezcla empresas con agregados regionales.
No interpreta el promedio nacional como promedio ponderado sin evidencia.
No convierte quintales a kg sin documentar la convención de peso fuente.

## Uso

Instalar `pypdf>=5`; después:

```python
from materias_primas_chile.grains import ingest_report
prices, rejected = ingest_report("data/raw")
prices.to_csv("data/processed/maiz_grano_week22_2025.csv", index=False)
rejected.to_csv("data/processed/maiz_grano_week22_2025_rejected.csv", index=False)
```

La descarga conserva PDF, SHA-256, manifest, texto layout y líneas originales.
El CLI `mpchile grains` ejecuta ese informe específico; instalar el extra `.[grains]`. La prueba
unitaria comprueba contrato con un extracto; no prueba una descarga de red.
Debe ejecutarse la extracción contra el PDF real antes de promover resultados.
Este único corte semanal no basta para entrenar pronósticos.

## Alternativas investigadas

- Cotrisa: https://www.cotrisa.cl/ y ruta de mercado maíz nacional. El navegador
  devolvió 403 o acceso no disponible. No se construyeron endpoints supuestos.
- ODEPA históricos mensuales: https://aplicativos.odepa.gob.cl/series-precios/series-tiempo .
  Página Angular con filtros y descarga, pero el navegador no ejecutó los filtros
  ni expuso un endpoint XLS/CSV verificable; no se implementa scraping a ciegas.
- Costos de internación incluyen maíz argentino y estadounidense; son referencias
  de importación y no sustituyen al precio doméstico pagado al productor.
- Las fichas de costos tienen XLS, pero corresponden a presupuestos por temporada;
  sus precios de referencia no constituyen una serie observada comparable.

Próximo trabajo: descubrir solicitudes de la aplicación mensual en un navegador
con JavaScript, validar IDs/unidades/IVA, y adquirir series largas. Mantener
`Maíz grano`, `Choclo`, maíz importado y contratos futuros como productos/mercados
distintos durante todo el flujo.
