"""Gráficos SVG sin dependencias: líneas, barras anuales, barras divergentes y mancuernas (antes/después).

Los colores se pasan como variables CSS (``var(--c-cereza)``), así el modo claro/oscuro y la impresión se resuelven en la
hoja de estilos. Cada gráfico devuelve ``(svg, tabla_html)``; la tabla acompaña al gráfico en un ``<details>`` para quien
no pueda o no quiera leer el dibujo. No hay doble eje: dos magnitudes distintas se dibujan en dos gráficos.
"""
from __future__ import annotations

import math
from html import escape
from typing import Callable, Sequence

W = 760
INK, MUTED = "var(--ink)", "var(--ink-2)"


def nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    if hi <= lo:
        hi = lo + 1
    raw = (hi - lo) / max(n - 1, 1)
    mag = 10 ** math.floor(math.log10(raw))
    step = next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw)
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while True:
        ticks.append(round(v, 10))
        if v >= hi - 1e-9:
            break
        v += step
    return ticks


def fmt_int(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


def fmt_pct(v: float, signed: bool = True) -> str:
    return f"{v * 100:+.0f}%".replace("+", "+") if signed else f"{v * 100:.0f}%"


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    head = "".join(f"<th scope='col'>{escape(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table class='data'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def _spread_labels(items: list[dict], min_gap: float = 14.0, lo: float = 0.0, hi: float = 1e9) -> list[dict]:
    """Separa etiquetas directas que quedarían encimadas (empuja hacia abajo y luego hacia arriba)."""
    items = sorted(items, key=lambda d: d["y"])
    for i in range(1, len(items)):
        if items[i]["y"] - items[i - 1]["y"] < min_gap:
            items[i]["y"] = items[i - 1]["y"] + min_gap
    overflow = items[-1]["y"] - hi if items else 0
    if overflow > 0:
        for it in items:
            it["y"] -= overflow
    for i in range(len(items) - 2, -1, -1):
        if items[i + 1]["y"] - items[i]["y"] < min_gap:
            items[i]["y"] = items[i + 1]["y"] - min_gap
    return items


def line_chart(series: list[dict], *, height: int = 300, y_title: str = "", y_fmt: Callable[[float], str] = fmt_int,
               x_ticks: Sequence[float] | None = None, x_fmt: Callable[[float], str] = lambda v: f"{v:.0f}",
               y_min: float | None = None, y_max: float | None = None, zero: bool = True,
               bands: Sequence[dict] = (), notes: Sequence[dict] = (), right: int = 118, label_ends: bool = True,
               alt: str = "", xpad: float = 0.0, show_x: bool = True) -> tuple[str, str]:
    """series: [{name, color, x[], y[], dash?, width?, label?, dots?}]. bands: [{x0,x1,text}]. notes: [{x,y,text,dx,dy}]."""
    left, top, bottom = 58, 40, (34 if show_x else 10)
    xs = [x for s in series for x in s["x"]]
    ys = [y for s in series for y in s["y"] if y == y]
    x0, x1 = min(xs) - xpad, max(xs) + xpad
    lo = y_min if y_min is not None else (0 if zero else min(ys))
    hi = y_max if y_max is not None else max(ys)
    ticks = nice_ticks(lo, hi * 1.04, 5)
    lo, hi = ticks[0], ticks[-1]
    pw, ph = W - left - right, height - top - bottom
    sx = lambda x: left + (x - x0) / (x1 - x0 or 1) * pw
    sy = lambda y: top + (1 - (y - lo) / (hi - lo or 1)) * ph
    out = [f"<svg class='chart' viewBox='0 0 {W} {height}' role='img' aria-label='{escape(alt)}' preserveAspectRatio='xMidYMid meet'>"]
    for b in bands:
        out.append(f"<rect class='band' x='{sx(b['x0']):.1f}' y='{top}' width='{sx(b['x1']) - sx(b['x0']):.1f}' height='{ph}'/>"
                   f"<text class='note' x='{sx(b['x0']) + 4:.1f}' y='{top + 12}'>{escape(b['text'])}</text>")
    for t in ticks:
        out.append(f"<line class='grid' x1='{left}' x2='{left + pw}' y1='{sy(t):.1f}' y2='{sy(t):.1f}'/>"
                   f"<text class='tick' x='{left - 8}' y='{sy(t) + 4:.1f}' text-anchor='end'>{escape(y_fmt(t))}</text>")
    for t in (x_ticks if x_ticks is not None else nice_ticks(x0, x1, 7)):
        if x0 <= t <= x1:
            if show_x:
                out.append(f"<text class='tick' x='{sx(t):.1f}' y='{height - 10}' text-anchor='middle'>{escape(x_fmt(t))}</text>")
            out.append(f"<line class='axis' x1='{sx(t):.1f}' x2='{sx(t):.1f}' y1='{top + ph}' y2='{top + ph + 4}'/>")
    out.append(f"<line class='axis' x1='{left}' x2='{left + pw}' y1='{top + ph}' y2='{top + ph}'/>")
    if y_title:
        out.append(f"<text class='ytitle' x='{left}' y='14'>{escape(y_title)}</text>")
    labels = []
    for s in series:
        pts = [(x, y) for x, y in zip(s["x"], s["y"]) if y == y]
        steps = sorted(b[0] - a[0] for a, b in zip(pts, pts[1:]))
        typical = steps[len(steps) // 2] if steps else 0
        # un hueco mayor a 1,9 veces el paso típico corta la línea: nunca se une con un tramo recto lo que no se midió
        path = " ".join(("M" if (i == 0 or (typical and x - pts[i - 1][0] > 1.9 * typical)) else "L") + f"{sx(x):.1f},{sy(y):.1f}"
                        for i, (x, y) in enumerate(pts))
        dash = " stroke-dasharray='5 4'" if s.get("dash") else ""
        out.append(f"<path d='{path}' fill='none' stroke='{s['color']}' stroke-width='{s.get('width', 2)}'{dash} stroke-linejoin='round' stroke-linecap='round'/>")
        for x, y in pts:
            title = f"{s['name']}: {y_fmt(y)} ({x_fmt(x)})"
            if s.get("dots"):
                out.append(f"<circle cx='{sx(x):.1f}' cy='{sy(y):.1f}' r='2.8' fill='{s['color']}' class='dot'/>")
            out.append(f"<circle cx='{sx(x):.1f}' cy='{sy(y):.1f}' r='8' fill='transparent' class='hit'><title>{escape(title)}</title></circle>")
        if pts:
            ex, ey = pts[-1]
            out.append(f"<circle cx='{sx(ex):.1f}' cy='{sy(ey):.1f}' r='4' fill='{s['color']}' stroke='var(--paper)' stroke-width='2'/>")
            if label_ends:
                labels.append({"y": sy(ey) + 4, "text": s.get("label", s["name"]), "color": s["color"], "x": sx(ex) + 10})
    for lab in _spread_labels(labels, lo=top + 8, hi=top + ph):
        out.append(f"<text class='lbl' x='{lab['x']:.1f}' y='{lab['y']:.1f}' fill='{INK}'><tspan fill='{lab['color']}'>&#9679;</tspan> {escape(lab['text'])}</text>")
    for n in notes:
        px, py = sx(n["x"]), sy(n["y"])
        tx, ty = px + n.get("dx", 14), py + n.get("dy", -22)
        out.append(f"<line class='lead' x1='{px:.1f}' y1='{py:.1f}' x2='{tx:.1f}' y2='{ty + 3:.1f}'/>"
                   f"<text class='note' x='{tx + 3:.1f}' y='{ty:.1f}'>{escape(n['text'])}</text>")
    out.append("</svg>")
    rows = []
    xs_sorted = sorted(set(xs))
    for x in xs_sorted:
        row = [x_fmt(x)]
        for s in series:
            lookup = dict(zip(s["x"], s["y"]))
            v = lookup.get(x)
            row.append("" if v is None or v != v else y_fmt(v))
        rows.append(row)
    return "".join(out), _table(["Período"] + [s["name"] for s in series], rows)


def bar_chart(xs: Sequence[float], ys: Sequence[float], *, color: str, height: int = 190, y_title: str = "",
              y_fmt: Callable[[float], str] = fmt_int, x_fmt: Callable[[float], str] = lambda v: f"{v:.0f}",
              label_every: int = 2, right: int = 118, highlight: dict[float, str] | None = None, alt: str = "",
              name: str = "Valor", label_set: set | None = None, show_x: bool = True) -> tuple[str, str]:
    left, top, bottom = 58, 36, (30 if show_x else 8)
    ticks = nice_ticks(0, max(y for y in ys if y == y) * 1.05, 4)
    hi = ticks[-1]
    pw, ph = W - left - right, height - top - bottom
    slot = pw / len(xs)
    bw = max(slot - 3, 2)
    sy = lambda y: top + (1 - y / hi) * ph
    out = [f"<svg class='chart' viewBox='0 0 {W} {height}' role='img' aria-label='{escape(alt)}' preserveAspectRatio='xMidYMid meet'>"]
    for t in ticks:
        out.append(f"<line class='grid' x1='{left}' x2='{left + pw}' y1='{sy(t):.1f}' y2='{sy(t):.1f}'/>"
                   f"<text class='tick' x='{left - 8}' y='{sy(t) + 4:.1f}' text-anchor='end'>{escape(y_fmt(t))}</text>")
    if y_title:
        out.append(f"<text class='ytitle' x='{left}' y='14'>{escape(y_title)}</text>")
    for i, (x, y) in enumerate(zip(xs, ys)):
        bx = left + i * slot + 1.5
        if show_x and ((x in label_set) if label_set is not None else i % label_every == 0):
            out.append(f"<text class='tick' x='{bx + bw / 2:.1f}' y='{height - 10}' text-anchor='middle'>{escape(x_fmt(x))}</text>")
        if y is None or y != y:
            continue
        h = max(ph * y / hi, 0.5)
        r = min(4, bw / 2, h)
        fill = (highlight or {}).get(x, color)
        out.append(f"<path d='M{bx:.1f},{top + ph:.1f} V{top + ph - h + r:.1f} Q{bx:.1f},{top + ph - h:.1f} {bx + r:.1f},{top + ph - h:.1f} "
                   f"H{bx + bw - r:.1f} Q{bx + bw:.1f},{top + ph - h:.1f} {bx + bw:.1f},{top + ph - h + r:.1f} V{top + ph:.1f} Z' fill='{fill}'>"
                   f"<title>{escape(name)}: {escape(y_fmt(y))} ({escape(x_fmt(x))})</title></path>")
    out.append(f"<line class='axis' x1='{left}' x2='{left + pw}' y1='{top + ph}' y2='{top + ph}'/></svg>")
    return "".join(out), _table(["Período", name], [[x_fmt(x), y_fmt(y)] for x, y in zip(xs, ys) if y == y])


def diverging_bars(items: list[dict], *, row: int = 30, alt: str = "", value_fmt: Callable[[float], str] = lambda v: fmt_pct(v)) -> tuple[str, str]:
    """items: [{label, value, color, note?}]. Barras que parten de cero: negativo a la izquierda, positivo a la derecha."""
    left, right, top = 150, 150, 14
    height = top + row * len(items) + 24
    vmin_, vmax_ = min(0.0, min(i["value"] for i in items)), max(0.0, max(i["value"] for i in items))
    ticks = nice_ticks(vmin_ * 1.35, vmax_ * 1.55, 6)
    lo, hi = ticks[0], ticks[-1]
    pw = W - left - right
    sx = lambda v: left + (v - lo) / (hi - lo) * pw
    out = [f"<svg class='chart' viewBox='0 0 {W} {height}' role='img' aria-label='{escape(alt)}' preserveAspectRatio='xMidYMid meet'>"]
    for t in ticks:
        out.append(f"<line class='grid' x1='{sx(t):.1f}' x2='{sx(t):.1f}' y1='{top}' y2='{top + row * len(items)}'/>"
                   f"<text class='tick' x='{sx(t):.1f}' y='{height - 6}' text-anchor='middle'>{escape(value_fmt(t))}</text>")
    out.append(f"<line class='zero' x1='{sx(0):.1f}' x2='{sx(0):.1f}' y1='{top}' y2='{top + row * len(items)}'/>")
    for i, it in enumerate(items):
        y = top + i * row
        x_end = sx(it["value"])
        bx, bw = min(sx(0), x_end), abs(x_end - sx(0))
        out.append(f"<text class='lbl' x='{left - 12}' y='{y + row / 2 + 4:.1f}' text-anchor='end' fill='{INK}'>{escape(it['label'])}</text>")
        out.append(f"<rect x='{bx:.1f}' y='{y + 6}' width='{max(bw, 1):.1f}' height='{row - 12}' rx='3' fill='{it['color']}'><title>{escape(it['label'])}: {escape(value_fmt(it['value']))}</title></rect>")
        anchor, tx = ("start", x_end + 6) if it["value"] >= 0 else ("end", x_end - 6)
        out.append(f"<text class='val' x='{tx:.1f}' y='{y + row / 2 + 4:.1f}' text-anchor='{anchor}' fill='{INK}'>{escape(value_fmt(it['value']))}</text>")
        if it.get("note"):
            note_x = W - right + 8
            out.append(f"<text class='note' x='{note_x}' y='{y + row / 2 + 4:.1f}'>{escape(it['note'])}</text>")
    out.append("</svg>")
    return "".join(out), _table(["Producto", "Cambio real", "Nota"], [[i["label"], value_fmt(i["value"]), i.get("note", "")] for i in items])


def dumbbell(items: list[dict], *, color: str, row: int = 28, x_title: str = "", x_fmt: Callable[[float], str] = fmt_int,
             before_name: str = "Antes", after_name: str = "Ahora", alt: str = "") -> tuple[str, str]:
    """items: [{label, before, after, change, extra?}]. Punto vacío = antes, punto lleno = ahora, a la derecha el cambio."""
    left, right, top = 150, 120, 26
    height = top + row * len(items) + 30
    vals = [v for i in items for v in (i["before"], i["after"])]
    ticks = nice_ticks(0, max(vals) * 1.08, 5)
    hi = ticks[-1]
    pw = W - left - right
    sx = lambda v: left + v / hi * pw
    out = [f"<svg class='chart' viewBox='0 0 {W} {height}' role='img' aria-label='{escape(alt)}' preserveAspectRatio='xMidYMid meet'>"]
    if x_title:
        out.append(f"<text class='ytitle' x='{left}' y='12'>{escape(x_title)}</text>")
    for t in ticks:
        out.append(f"<line class='grid' x1='{sx(t):.1f}' x2='{sx(t):.1f}' y1='{top}' y2='{top + row * len(items)}'/>"
                   f"<text class='tick' x='{sx(t):.1f}' y='{height - 8}' text-anchor='middle'>{escape(x_fmt(t))}</text>")
    for i, it in enumerate(items):
        cy = top + i * row + row / 2
        out.append(f"<text class='lbl' x='{left - 12}' y='{cy + 4:.1f}' text-anchor='end' fill='{INK}'>{escape(it['label'])}</text>")
        out.append(f"<line x1='{sx(it['before']):.1f}' x2='{sx(it['after']):.1f}' y1='{cy:.1f}' y2='{cy:.1f}' stroke='{color}' stroke-width='3' opacity='0.45' stroke-linecap='round'/>")
        out.append(f"<circle cx='{sx(it['before']):.1f}' cy='{cy:.1f}' r='5.5' fill='var(--paper)' stroke='{color}' stroke-width='2'><title>{escape(it['label'])}, {escape(before_name)}: {escape(x_fmt(it['before']))}</title></circle>")
        out.append(f"<circle cx='{sx(it['after']):.1f}' cy='{cy:.1f}' r='5.5' fill='{color}' stroke='var(--paper)' stroke-width='2'><title>{escape(it['label'])}, {escape(after_name)}: {escape(x_fmt(it['after']))}</title></circle>")
        out.append(f"<text class='val' x='{W - right + 14}' y='{cy + 4:.1f}' fill='{INK}'>{escape(fmt_pct(it['change']))}</text>")
        if it.get("extra"):
            out.append(f"<text class='note' x='{W - right + 58}' y='{cy + 4:.1f}'>{escape(it['extra'])}</text>")
    out.append("</svg>")
    rows = [[i["label"], x_fmt(i["before"]), x_fmt(i["after"]), fmt_pct(i["change"])] for i in items]
    return "".join(out), _table(["Variedad", before_name, after_name, "Cambio"], rows)
