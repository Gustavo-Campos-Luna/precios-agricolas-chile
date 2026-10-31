"""Referencias del informe en formato APA 7 (español).

Cada entrada tiene: clave interna, cita en el texto (``short``), clave de orden alfabético y la referencia en HTML.
Las fuentes de contexto (noticias, boletines, informes) se abrieron y leyeron el 30 de octubre de 2026; las cifras que el
informe toma de ellas están parafraseadas. Los conjuntos de datos que cambian en el tiempo llevan fecha de recuperación.
"""
from __future__ import annotations

RETRIEVED = "Recuperado el 30 de octubre de 2026 de "


def a(url: str) -> str:
    return f"<a href='{url}'>{url}</a>"


REFS: list[dict] = [
    # ----- Conjuntos de datos -----
    dict(key="banco_central", short="Banco Central de Chile, 2026", sort="banco central de chile 2026",
         html=f"Banco Central de Chile. (2026). <i>Base de datos estadísticos</i> [Base de datos]. {RETRIEVED}{a('https://si3.bcentral.cl/')}"),
    dict(key="ciren_catastro", short="CIREN y ODEPA, 2025", sort="centro de informacion de recursos naturales 2025",
         html=f"Centro de Información de Recursos Naturales [CIREN] y Oficina de Estudios y Políticas Agrarias [ODEPA]. (2025). <i>Catastro frutícola</i> [Conjunto de datos]. {RETRIEVED}{a('https://datos.odepa.gob.cl/dataset/catastro-fruticola')}"),
    dict(key="cotrisa", short="Cotrisa, 2026", sort="comercializadora de trigo 2026",
         html=f"Comercializadora de Trigo S.A. [Cotrisa]. (2026). <i>Tabla de precios: trigo, maíz, arroz y avena</i> [Página web]. {RETRIEVED}{a('https://www.cotrisa.cl/publicaciones/precios/tabla-precios/')}"),
    dict(key="fao_fpi", short="FAO, 2026a", sort="organizacion de las naciones unidas fao 2026a food price index",
         html=f"Organización de las Naciones Unidas para la Alimentación y la Agricultura [FAO]. (2026a, 2 de octubre). <i>FAO Food Price Index</i> [Página web]. {RETRIEVED}{a('https://www.fao.org/worldfoodsituation/foodpricesindex/en/')}"),
    dict(key="faostat", short="FAO, 2026b", sort="organizacion de las naciones unidas fao 2026b faostat",
         html=f"Organización de las Naciones Unidas para la Alimentación y la Agricultura [FAO]. (2026b). <i>FAOSTAT: Precios al productor, Chile</i> [Conjunto de datos; distribuido por el Humanitarian Data Exchange, licencia CC BY-IGO]. {RETRIEVED}{a('https://data.humdata.org/dataset/chl-faostat-food-prices')}"),
    dict(key="odepa_comex", short="ODEPA, 2026a", sort="oficina 2026a comercio exterior",
         html=f"Oficina de Estudios y Políticas Agrarias [ODEPA]. (2026a). <i>Comercio exterior</i> [Conjunto de datos]. {RETRIEVED}{a('https://datos.odepa.gob.cl/dataset/comercio-exterior')}"),
    dict(key="odepa_uva", short="ODEPA, 2026b", sort="oficina 2026b precios de uva",
         html=f"Oficina de Estudios y Políticas Agrarias [ODEPA]. (2026b). <i>Precios de uva para vinificación</i> [Conjunto de datos]. {RETRIEVED}{a('https://datos.odepa.gob.cl/dataset/precios-uva-vinificacion')}"),
    dict(key="odepa_mayorista", short="ODEPA, 2026c", sort="oficina 2026c precios mayoristas",
         html=f"Oficina de Estudios y Políticas Agrarias [ODEPA]. (2026c). <i>Precios mayoristas de frutas y hortalizas</i> [Conjunto de datos]. {RETRIEVED}{a('https://datos.odepa.gob.cl/dataset/precios-mayoristas-de-frutas-y-hortalizas')}"),
    dict(key="pink_sheet", short="World Bank, 2026", sort="world bank 2026",
         html=f"World Bank. (2026). <i>Commodity price data (The Pink Sheet)</i> [Conjunto de datos]. {RETRIEVED}{a('https://www.worldbank.org/en/research/commodity-markets')}"),
    # ----- Noticias e investigaciones de contexto -----
    dict(key="aguirre2025", short="Aguirre, 2025", sort="aguirre 2025",
         html=f"Aguirre, G. (2025, 14 de enero). Precio de cerezas chilenas vive repunte tras caída por históricas exportaciones a China. <i>Cooperativa.cl</i>. {a('https://cooperativa.cl/noticias/economia/competitividad/precio-de-cerezas-chilenas-vive-repunte-tras-caida-por-historicas/2025-01-14/144120.html')}"),
    dict(key="baffes2022", short="Baffes y Temaj, 2022", sort="baffes 2022",
         html=f"Baffes, J. y Temaj, K. (2022, 25 de mayo). Food prices continued their two-year-long upward trajectory. <i>World Bank Data Blog</i>. {a('https://blogs.worldbank.org/en/opendata/food-prices-continued-their-two-year-long-upward-trajectory')}"),
    dict(key="castro2022", short="Castro, 2022", sort="castro 2022",
         html=f"Castro, M. (2022, 12 de julio). Dólar en Chile sigue indetenible y cierra por sobre los $1.000. <i>Bloomberg Línea</i>. {a('https://www.bloomberglinea.com/2022/07/12/dolar-en-chile-sigue-indetenible-y-cierra-por-sobre-los-1000/')}"),
    dict(key="emol2026", short='"Viñateros arrancan", 2026', sort="vinateros arrancan 2026",
         html=f"Viñateros arrancan más de 6 mil hectáreas de parras viníferas por crisis del vino. (2026, 2 de octubre). <i>Emol</i>. {a('https://www.emol.com/noticias/Economia/2026/10/02/1213019/arrancan-miles-hectareas-parras-viniferas.html')}"),
    dict(key="ernst2025", short="Ernst, 2025", sort="ernst 2025",
         html=f"Ernst, B. (2025, 14 de marzo). Cerezas 2024/2025: No todos los caminos conducen a China. <i>Portal Frutícola</i>. {a('https://www.portalfruticola.com/?p=592932')}"),
    dict(key="espinoza2026", short="Espinoza, 2026", sort="espinoza 2026",
         html=f"Espinoza, C. (2026, 20 de febrero). Chile recorta envíos de uva de mesa a EE.UU. en medio de sobreoferta. <i>Portal Frutícola</i>. {a('https://www.portalfruticola.com/noticias/2026/02/20/chile-uva-eeuu/')}"),
    dict(key="fao2022", short="FAO, 2022", sort="organizacion de las naciones unidas fao 2022",
         html=f"Organización de las Naciones Unidas para la Alimentación y la Agricultura [FAO]. (2022, 8 de abril). <i>FAO Food Price Index posts significant leap in March</i> [Comunicado de prensa]. {a('https://www.fao.org/newsroom/detail/fao-food-price-index-posts-significant-leap-in-march/en')}"),
    dict(key="freshplaza2026a", short="FreshPlaza, 2026a", sort="freshplaza 2026a",
         html=f"FreshPlaza. (2026a, 28 de octubre). <i>Apple exports from China, Chile, France, and Poland fall by 896,000 tons annually</i>. {a('https://www.freshplaza.com/article/9886931/apple-exports-from-china-chile-france-and-poland-fall-by-896-000-tons-annually/')}"),
    dict(key="freshplaza2026b", short="FreshPlaza, 2026b", sort="freshplaza 2026b",
         html=f"FreshPlaza. (2026b, 19 de febrero). <i>Chile cherry exports reach 113.8 million boxes as prices fall</i>. {a('https://www.freshplaza.com/europe/article/9812438/chile-cherry-exports-reach-113-8-million-boxes-as-prices-fall/')}"),
    dict(key="freshplaza2026c", short="FreshPlaza, 2026c", sort="freshplaza 2026c",
         html=f"FreshPlaza. (2026c, 17 de julio). <i>Chilean apple exports rise 5% in first half of 2026</i>. {a('https://www.freshplaza.com/north-america/article/9858342/chilean-apple-exports-rise-5-in-first-half-of-2026/')}"),
    dict(key="freshplaza2026d", short="FreshPlaza, 2026d", sort="freshplaza 2026d",
         html=f"FreshPlaza. (2026d, 3 de abril). <i>Chilean cherries face oversupply at 625,000 tons</i>. {a('https://www.freshplaza.com/north-america/article/9826208/chilean-cherries-face-oversupply-at-625-000-tons/')}"),
    # ----- Fuentes agregadas en la versión 2 (abiertas y contrastadas el 30 de octubre de 2026) -----
    dict(key="decofrut2025", short="Decofrut, 2025", sort="decofrut 2025",
         html=f"Decofrut. (2025, 17 de julio). Análisis temporada de cerezas: con altas exigencias. <i>Mundoagro</i>. {a('https://mundoagro.io/cl/analisis-temporada-de-cerezas-con-altas-exigencias/')}"),
    dict(key="inia2025", short="INIA, 2025", sort="instituto de investigaciones agropecuarias 2025",
         html=f"Instituto de Investigaciones Agropecuarias [INIA]. (2025, 27 de enero). <i>¿Qué factores provocaron la caída de precios de las cerezas de exportación en China?</i> {a('https://www.inia.cl/2025/01/27/que-factores-provocaron-la-caida-de-precios-de-las-cerezas-de-exportacion-en-china/')}"),
    dict(key="chen2026", short="Chen, 2026", sort="chen 2026",
         html=f"Chen, L. (2026, 16 de enero). Chilean cherries: why prices in China plunge every winter. <i>Sixth Tone</i>. {a('https://www.sixthtone.com/news/1018100/chilean-cherries:-why-prices-in-china-plunge-every-winter')}"),
    dict(key="mundomaritimo2025", short='"Exportadores frutícolas", 2025', sort="exportadores fruticolas 2025",
         html=f"Exportadores frutícolas de Chile esperan que mayor capacidad naviera disminuya tarifas de fletes en la temporada 2025-2026. (2025, 16 de septiembre). <i>MundoMarítimo</i>. {a('https://mundomaritimo.cl/noticias/exportadores-fruticolas-de-chile-esperan-que-mayor-capacidad-naviera-disminuya-tarifas-de-fletes-en-la-temporada-2025-2026')}"),
    dict(key="contreras_e2026", short="L. Contreras, 2026", sort="contreras espinoza 2026",
         html=f"Contreras Espinoza, L. (2026, 28 de octubre). Cerezas en Chile: SNA proyecta caída de 18% en producción por lluvias y granizo. <i>Pauta</i>. {a('https://www.pauta.cl/actualidad/2026/10/28/sna-advierte-fuerte-caida-en-produccion-de-cerezas-proyecta-25-millones-de-cajas-menos-esta-temporada.html')}"),
    dict(key="boisier2025", short="Boisier et al., 2025", sort="boisier 2025",
         html=f"Boisier, J. P., Alvarez-Garreton, C., Marinao, R. y Galleguillos, M. (2025). Increasing water stress in Chile revealed by novel datasets of water availability, land use and water use. <i>Hydrology and Earth System Sciences, 29</i>, 5185-5212. {a('https://doi.org/10.5194/hess-29-5185-2025')}"),
    dict(key="fernandez2020", short="Fernandez et al., 2020", sort="fernandez 2020",
         html=f"Fernandez, E., Whitney, C., Cuneo, I. F. y Luedeling, E. (2020). Prospects of decreasing winter chill for deciduous fruit production in Chile throughout the 21st century. <i>Climatic Change, 159</i>(3). {a('https://doi.org/10.1007/s10584-019-02608-1')}"),
    dict(key="agrolatam2025", short="AgroLatam Redacción, 2025", sort="agrolatam 2025",
         html=f"AgroLatam Redacción. (2025, 20 de agosto). La batalla por la uva de mesa: Perú gana ventaja con altos rendimientos frente a Chile y Sudáfrica. <i>AgroLatam.com</i>. {a('https://www.agrolatam.com/mercados-latam/uva-mesa-peru-chile-sudafrica-costos-rendimientos-2025/')}"),
    dict(key="buzzetti2026", short="Buzzetti, 2026", sort="buzzetti 2026",
         html=f"Buzzetti Horta, C. (2026, 26 de agosto). <i>Boletín del vino, pisco y mosto, agosto 2026</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/boletines/boletin-del-vino-pisco-y-mosto-agosto')}"),
    dict(key="contreras_h2026", short="P. Contreras, 2026", sort="contreras hurtado 2026",
         html=f"Contreras Hurtado, P. (2026, 2 de septiembre). <i>Boletín de cereales, agosto 2026</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/boletines/boletin-de-cereales-agosto-2026')}"),
    dict(key="causa2026", short="Causa, 2026", sort="causa 2026",
         html=f"Causa Ureta, K. (2026, 24 de agosto). Urea en Chile: del mercado internacional a los costos de la agricultura. <i>Artículos ODEPA</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/articulos/urea-en-chile-mercado-internacional-costos-agricultura-2015-2026')}"),
    dict(key="valenzuela2026", short="Valenzuela, 2026", sort="valenzuela 2026",
         html=f"Valenzuela Palma, A. (2026, 24 de febrero). <i>Boletín de fruta, febrero 2026</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/boletines/boletin-de-fruta-febrero2026')}"),
    dict(key="soto2025", short="Soto, 2025", sort="soto 2025",
         html=f"Soto N., S. (2025, 13 de octubre). Radiografía de la molienda de trigo en Chile 2017-2024: desafíos para la cadena trigo-harina-pan. <i>Artículos ODEPA</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/articulos/radiografia-de-la-molienda-de-trigo-en-chile-2017-2024-desafios-para-la-cadena-trigo-harina-pan')}"),
    dict(key="hacienda2026", short="Ministerio de Hacienda, 2026", sort="ministerio de hacienda 2026",
         html=f"Ministerio de Hacienda. (2026, 13 de octubre). <i>Decreto exento n.° 285: aplica rebajas de derechos de aduana para la importación de trigo y harina de trigo o de morcajo (tranquillón)</i>. Diario Oficial de la República de Chile, n.° 44.573 (14 de octubre de 2026). {a('https://www.diariooficial.interior.gob.cl/publicaciones/2026/10/14/44573/01/2886346.pdf')}"),
    dict(key="usda2026", short="Gonzalez, 2026", sort="gonzalez 2026",
         html=f"Gonzalez, S. (2026, 25 de marzo). <i>Grain and feed annual</i> (Informe n.° CI2026-0003). Servicio Agrícola Exterior del Departamento de Agricultura de los Estados Unidos [USDA FAS], Santiago. {a('https://apps.fas.usda.gov/newgainapi/api/Report/DownloadReportByFileName?fileName=Grain+and+Feed+Annual_Santiago_Chile_CI2026-0003.pdf')}"),
    dict(key="oiv2026", short="OIV, 2026", sort="organisation internationale de la vigne 2026",
         html=f"Organisation Internationale de la Vigne et du Vin [OIV]. (2026, 12 de mayo). <i>State of the world wine sector in 2025: tariffs, climate and consumer trends drive sector adaptation</i> [Comunicado de prensa]. {a('https://www.oiv.int/sites/default/files/2026-05/OIV_EN_Press_release_State-of_the_World-Wine_Sector.pdf')}"),
    dict(key="faostat_cultivos", short="FAO, 2026c", sort="organizacion de las naciones unidas fao 2026c faostat cultivos",
         html=f"Organización de las Naciones Unidas para la Alimentación y la Agricultura [FAO]. (2026c). <i>FAOSTAT: cultivos y productos de ganadería</i> [Conjunto de datos; superficie, producción y rendimiento, Chile, 1961-2024]. {RETRIEVED}{a('https://www.fao.org/faostat/en/#data/QCL')}"),
    dict(key="guzman2024", short="Guzmán, 2024", sort="guzman 2024",
         html=f"Guzmán, L. (2024, 16 de agosto). Competencia de Perú y sequía llevan a plantaciones de uva de mesa a su nivel más bajo desde que hay registros. <i>Diario Financiero</i>. {a('https://www.df.cl/empresas/industria/competencia-de-peru-y-sequia-llevan-a-plantaciones-de-uva-de-mesa-a-su')}"),
    dict(key="isla2025", short="Isla, 2025", sort="isla 2025",
         html=f"Isla, J. (2025, 16 de mayo). La estrategia de las viñas en su crisis más profunda ante la desaceleración del consumo. <i>Señal DF, Diario Financiero</i>. {a('https://www.df.cl/senal-df/la-estrategia-de-las-vinas-en-su-crisis-mas-profunda-ante-la-desaceleracion')}"),
    dict(key="laval2018", short="Laval y García, 2018", sort="laval 2018",
         html=f"Laval M., E. y García L., A. (2018, diciembre). <i>Boletín de cereales, diciembre 2018</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/wp-content/uploads/2018/12/Boletin-cereales-diciembre-2018.pdf')}"),
    dict(key="munoz2025", short="Muñoz, 2025", sort="munoz 2025",
         html=f"Muñoz Villagrán, M. (2025, 28 de abril). <i>Boletín de fruta, abril 2025</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/boletines/boletin-de-fruta-abril-2025')}"),
    dict(key="munoz2026", short="Muñoz, 2026", sort="munoz 2026",
         html=f"Muñoz Villagrán, M. (2026, 17 de septiembre). <i>Boletín de fruta, septiembre 2026</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/boletines/boletin-de-fruta-septiembre-2026')}"),
    dict(key="ovalle2026", short="Ovalle, 2026", sort="ovalle 2026",
         html=f"Ovalle R., J. (2026, 26 de agosto). Evolución del cultivo del cerezo en Chile: cambios varietales, tecnológicos y territoriales. <i>Artículos ODEPA</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/articulos/evolucion-cultivo-cerezo-chile-cambios-varietales-tecnologicos-territoriales')}"),
    dict(key="pelfort2026", short="Pelfort, 2026", sort="pelfort 2026",
         html=f"Pelfort L., S. (2026, 20 de marzo). Año amargo para el vino chileno: exportaciones retroceden y la industria entra en modo ajuste. <i>Diario Financiero</i>. {a('https://www.df.cl/empresas/industria/ano-amargo-para-el-vino-chileno-exportaciones-retroceden-y-la-industria')}"),
    dict(key="rabo2026", short="RaboResearch, 2026", sort="raboresearch 2026",
         html=f"RaboResearch. (2026, mayo). <i>Reporte de cerezas 2026</i>. SmartCherry. {a('https://smartcherry.cl/wp-content/uploads/2026/05/RaboResearch_Reporte-de-cerezas-2026_Salinas_May2026.pdf')}"),
    dict(key="soto2026", short="Soto, 2026", sort="soto 2026",
         html=f"Soto N., S. (2026, 20 de marzo). <i>Boletín de cereales, marzo 2026</i>. Oficina de Estudios y Políticas Agrarias. {a('https://www.odepa.gob.cl/publicaciones/boletines/boletin-de-cereales-marzo-2026')}"),
    dict(key="usda2025", short="Gonzalez, 2025", sort="gonzalez 2025",
         html=f"Gonzalez, S. (2025, 2 de diciembre). <i>Fresh deciduous fruit annual</i> (Informe n.° CI2025-0028). Servicio Agrícola Exterior del Departamento de Agricultura de los Estados Unidos [USDA FAS], Santiago. {a('https://agriexchange.apeda.gov.in/MarketReport/0607302062025122911477182.pdf')} (copia alojada)"),
    dict(key="vinetur2026", short="Vinetur, 2026", sort="vinetur 2026",
         html=f"Vinetur. (2026, 17 de octubre). <i>El consumo de vino en Chile cae un 17,5% en plena presión al sector</i>. {a('https://www.vinetur.com/es/20261017109176/chiles-wine-consumption-fell-175-the-steepest-drop-among-major-markets.html')}"),
]
BY_KEY = {r["key"]: r for r in REFS}
USED: set[str] = set()


def cite(*keys: str) -> str:
    """Cita parentética APA: (Autor, año; Autor, año), en orden alfabético."""
    for k in keys:
        if k not in BY_KEY:
            raise KeyError(f"Referencia inexistente: {k}")
        USED.add(k)
    parts = [BY_KEY[k]["short"] for k in sorted(keys, key=lambda k: BY_KEY[k]["sort"])]
    return "(" + "; ".join(parts) + ")"


def narrative(key: str) -> str:
    """Cita narrativa: Autor (año)."""
    USED.add(key)
    short = BY_KEY[key]["short"]
    name, year = short.rsplit(", ", 1)
    return f"{name} ({year})"


def reference_list() -> str:
    unused = set(BY_KEY) - USED
    if unused:
        raise ValueError(f"Referencias sin citar en el texto: {sorted(unused)}")
    ordered = sorted(REFS, key=lambda r: r["sort"])
    return "\n".join(f"<p>{r['html']}</p>" for r in ordered)
