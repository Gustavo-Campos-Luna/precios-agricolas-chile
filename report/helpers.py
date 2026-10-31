"""Utilidades de formato y piezas de maquetación compartidas por los capítulos del informe."""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

COL = {"cereza": "var(--c-cereza)", "uva": "var(--c-uva)", "manzana": "var(--c-manzana)", "trigo": "var(--c-trigo)",
       "maiz": "var(--c-maiz)", "neutro": "var(--c-neutral)"}
NAMES = {"santina": "Santina", "lapins": "Lapins", "rainier": "Rainier", "sweetheart": "Sweet Heart", "royaldawn": "Royal Dawn",
         "brooks": "Brooks", "earlyburlat": "Early Burlat", "bing": "Bing", "regina": "Regina", "kordia": "Kordia",
         "superiorseedless": "Superior Seedless", "redglobe": "Red Globe", "thompsonseedless": "Thompson (Sultanina)",
         "flameseedless": "Flame Seedless", "moscatelrosada": "Moscatel rosada", "crimsonseedless": "Crimson Seedless",
         "rosadapastilla": "Rosada pastilla", "ralliseedless": "Ralli Seedless", "grannysmith": "Granny Smith",
         "fujiroyal": "Fuji Royal", "pinklady": "Pink Lady", "royalgala": "Royal Gala", "scarlett": "Scarlett",
         "ambrosia": "Ambrosia", "richareddelicious": "Richared Delicious", "paismissioncriolla": "País (Mission)",
         "sauvignonblanc": "Sauvignon Blanc", "chardonnay": "Chardonnay", "merlot": "Merlot",
         "cabernetsauvignon": "Cabernet Sauvignon", "carmenere": "Carmenere", "syrah": "Syrah", "golden": "Golden"}
MONTHS_FULL = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def es(x: float, d: int = 0) -> str:
    """Formato chileno: miles con punto y decimales con coma."""
    out = f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return "−" + out[1:] if out.startswith("-") else out


def sg(x: float, d: int = 0) -> str:
    """Variación porcentual con signo (x es una razón: 0,25 = +25%)."""
    return ("+" if x >= 0 else "−") + es(abs(x) * 100, d) + "%"


def vname(key: str) -> str:
    return NAMES.get(key, key[:1].upper() + key[1:])


def season_x(v: float) -> str:
    return f"{int(v)}/{str(int(v) + 1)[-2:]}"


def save(name: str, frame: pd.DataFrame) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DATA / f"{name}.csv", index=False, encoding="utf-8")


def figure(key: str, title: str, svg: str, table: str, note: str) -> str:
    """El número se asigna al final según el orden real de aparición (marcador @@N:clave@@)."""
    return (f"<figure id='fig-{key}'><p class='fig-n'>Figura @@N:{key}@@</p><p class='fig-t'>{title}</p><div class='plot'>{svg}</div>"
            f"<figcaption class='note'>{note}</figcaption>"
            f"<details class='tabla'><summary>Ver los datos de esta figura</summary><div>{table}</div></details></figure>")


def number_figures(html: str) -> tuple[str, int]:
    order = re.findall(r"@@N:(\w+)@@", html)
    if len(order) != len(set(order)):
        raise ValueError("Una figura aparece dos veces en el documento")
    numbers = {k: i + 1 for i, k in enumerate(order)}
    for ref in set(re.findall(r"@@R:(\w+)@@", html)):
        if ref not in numbers:
            raise ValueError(f"Referencia a una figura inexistente: {ref}")
    html = re.sub(r"@@N:(\w+)@@", lambda m: str(numbers[m.group(1)]), html)
    html = re.sub(r"@@R:(\w+)@@", lambda m: str(numbers[m.group(1)]), html)
    return html, len(numbers)


def read_box(text: str, title: str = "Cómo leerlo") -> str:
    return f"<div class='read'><span class='bt'>{title}</span>{text}</div>"


def caution_box(text: str, title: str = "Ojo con esto") -> str:
    return f"<div class='caution'><span class='bt'>{title}</span>{text}</div>"


def voices_box(items: list[tuple[str, str]], title: str = "Lo que dice el sector") -> str:
    """items: [(texto parafraseado con su cita, quién habla)]."""
    body = "".join(f"<blockquote>{t}<cite>{who}</cite></blockquote>" for t, who in items)
    return f"<div class='voices'><span class='bt'>{title}</span>{body}</div>"


def ficha(title: str, rows: list[tuple[str, str]], neg: tuple[int, ...] = ()) -> str:
    """Cifras esenciales del capítulo, para la columna lateral. rows: [(etiqueta, valor)]."""
    body = "".join(f"<div class='row'><dt>{a}</dt><dd{' class=neg' if i in neg else ''}>{b}</dd></div>" for i, (a, b) in enumerate(rows))
    return f"<div class='ficha'><h4>{title}</h4><dl>{body}</dl></div>"


def chapter(sid: str, num: str, head: str, lead: str, main: str, aside: str = "", product: str = "", page_break: bool = True) -> str:
    cls = " ".join(c for c in (f"p-{product}" if product else "", "page-break" if page_break else "") if c)
    cls_attr = f" class='{cls}'" if cls else ""
    side = f"<aside>{aside}</aside>" if aside else ""
    one = "" if aside else " one"
    return (f"<section id='{sid}'{cls_attr}><div class='opener'><p class='num'>{num}</p><h2>{head}</h2><p class='lead'>{lead}</p></div>"
            f"<div class='cols{one}'><div class='main'>{main}</div>{side}</div></section>")
