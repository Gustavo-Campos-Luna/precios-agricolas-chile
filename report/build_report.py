"""Genera el informe HTML (un solo archivo, sin conexión) y los CSV de cada figura.

Uso, desde la raíz del repositorio:
    python report/build_report.py            # escribe report/dist/informe_precios_agricolas_chile.html y report/data/*.csv
    python report/build_report.py --pdf      # además crea el PDF con Microsoft Edge o Chrome en modo headless

Estructura:
    ctx.py              cifras y figuras (todo número del texto sale de los datos)
    chapters_*.py       texto de cada capítulo
    referencias.py      lista APA 7 con verificación de citas
    helpers.py          formato, cajas y maquetación

El script falla si una cita no existe en la lista de referencias, si hay referencias sin citar, si el texto contiene rayas
largas o medias, o si aparece alguna de las muletillas de la guía de redacción.
"""
from __future__ import annotations

import base64
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import chapters_close as CC  # noqa: E402
import chapters_front as CF  # noqa: E402
import chapters_fruit as CR  # noqa: E402
import chapters_grain as CG  # noqa: E402
import ctx  # noqa: E402
from helpers import number_figures  # noqa: E402
from referencias import reference_list  # noqa: E402

DIST = HERE / "dist"
OUT_HTML = DIST / "informe_precios_agricolas_chile.html"
OUT_PDF = DIST / "informe_precios_agricolas_chile.pdf"
BANNED = ["crucial", "robust", "significativ", "cabe destacar", "es importante señalar", "en conclusión", "tormenta perfecta",
          "montaña rusa", "jugar un rol", "panorama complejo", "dinámic", "evidenciar", "evidencian", "fundamental", "sin duda", "cabe mencionar",
          "en el mundo de", "no solo", "se destaca que"]


def font_css() -> str:
    def face(family: str, file: str, style: str, weight: str) -> str:
        data = base64.b64encode((HERE / "fonts" / file).read_bytes()).decode("ascii")
        return (f"@font-face{{font-family:'{family}';font-style:{style};font-weight:{weight};font-display:swap;"
                f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")
    return "".join([face("Hanken Grotesk", "HankenGrotesk.woff2", "normal", "100 900"),
                    face("Source Serif 4", "SourceSerif4-roman.woff2", "normal", "200 900"),
                    face("Source Serif 4", "SourceSerif4-italic.woff2", "italic", "200 900")])


def check_text(html: str) -> None:
    body = re.sub(r"<style>.*?</style>", "", html, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", body).lower()
    bad = [ch for ch in ("\u2014", "\u2013") if ch in body]
    if bad:
        raise ValueError(f"El informe contiene rayas largas o medias: {bad}")
    hits = {w: text.count(w) for w in BANNED if w in text}
    if hits:
        raise ValueError(f"Muletillas de la guía de redacción en el texto: {hits}")
    if "@@" in body:
        raise ValueError("Quedaron marcadores de figura sin resolver")


def main(make_pdf: bool = False) -> None:
    X = ctx.build()
    body = [
        CF.cover(X), CF.toc(), CF.summary(X), CF.guide(X), CF.overview(X),
        CR.cherry(X), CR.apple_grape(X), CG.grains(X), CG.wine(X),
        CC.factors(X), CC.scenarios(X), CC.conclusions(X), CC.limits(),
    ]
    refs = f"<section id='referencias' class='page-break'><div class='opener'><p class='num'>Referencias</p><h2>Fuentes citadas</h2></div><div class='refs'>{reference_list()}</div></section>"
    body += [refs, CC.annex(),
             f"<footer><span>Qué subió y qué cayó en el campo chileno</span><span>Versión 2.0, {CF.DATE_LONG}</span>"
             "<span>Código bajo licencia MIT; datos de terceros con sus licencias</span></footer>"]
    css = (HERE / "style.css").read_text(encoding="utf-8").replace("{{FONTS}}", font_css())
    html = ("<!doctype html><html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>Qué subió y qué cayó en el campo chileno</title>"
            "<meta name='description' content='Informe de mercado: cómo cambiaron, en pesos reales, los precios de cereza, manzana, uva, trigo y maíz en Chile y por qué.'>"
            f"<style>{css}</style></head><body><div class='sheet'>{''.join(body)}</div></body></html>")
    html, n_figures = number_figures(html)
    check_text(html)
    DIST.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"HTML: {OUT_HTML} ({OUT_HTML.stat().st_size / 1024:.0f} KB), {n_figures} figuras")
    if make_pdf:
        make_pdf_file()


def find_browser() -> str | None:
    for candidate in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                      r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        if Path(candidate).exists():
            return candidate
    return None


def make_pdf_file() -> None:
    browser = find_browser()
    if browser is None:
        print("No se encontró Edge ni Chrome: se omite el PDF (abra el HTML y use Imprimir > Guardar como PDF).")
        return
    cmd = [browser, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={OUT_PDF}", OUT_HTML.as_uri()]
    subprocess.run(cmd, check=True, timeout=240, capture_output=True)
    print(f"PDF: {OUT_PDF} ({OUT_PDF.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main(make_pdf="--pdf" in sys.argv)
