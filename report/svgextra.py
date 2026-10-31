"""Gráficos adicionales: cascada (puente multiplicativo), dispersión con recta y miniaturas (sparklines).

Misma convención que ``svgcharts``: colores como variables CSS, descripción accesible y tabla de datos.
"""
from __future__ import annotations

from html import escape
from typing import Callable, Sequence

from svgcharts import W, _table, nice_ticks


def waterfall(steps: Sequence[dict], *, start_label: str = "Base", total_label: str = "Hoy", up: str = "var(--c-trigo)",
              down: str = "var(--c-neutral)", height: int = 330, y_title: str = "", alt: str = "") -> tuple[str, str]:
    """Puente de un índice base 100. steps: [{label, factor, note?}]. Cada barra va del valor previo al nuevo."""
    left, right, top, bottom = 58, 24, 44, 64
    levels = [100.0]
    for s in steps:
        levels.append(levels[-1] * s["factor"])
    hi_data = max(levels)
    ticks = nice_ticks(0, hi_data * 1.12, 5)
    hi = ticks[-1]
    pw, ph = W - left - right, height - top - bottom
    n = len(steps) + 2
    slot = pw / n
    bw = slot * 0.62
    sy = lambda v: top + (1 - v / hi) * ph
    out = [f"<svg class='chart' viewBox='0 0 {W} {height}' role='img' aria-label='{escape(alt)}' preserveAspectRatio='xMidYMid meet'>"]
    if y_title:
        out.append(f"<text class='ytitle' x='{left}' y='14'>{escape(y_title)}</text>")
    for t in ticks:
        out.append(f"<line class='grid' x1='{left}' x2='{W - right}' y1='{sy(t):.1f}' y2='{sy(t):.1f}'/>"
                   f"<text class='tick' x='{left - 8}' y='{sy(t) + 4:.1f}' text-anchor='end'>{t:,.0f}</text>")

    def bar(i: int, v0: float, v1: float, fill: str, label: str, note: str, title: str):
        x = left + i * slot + (slot - bw) / 2
        y0, y1 = sy(max(v0, v1)), sy(min(v0, v1))
        out.append(f"<rect x='{x:.1f}' y='{y0:.1f}' width='{bw:.1f}' height='{max(y1 - y0, 1):.1f}' rx='3' fill='{fill}'><title>{escape(title)}</title></rect>")
        out.append(f"<text class='val' x='{x + bw / 2:.1f}' y='{y0 - 8:.1f}' text-anchor='middle'>{escape(note)}</text>")
        words = label.split(" ")
        mid = (len(words) + 1) // 2
        lines = [" ".join(words[:mid]), " ".join(words[mid:])] if len(words) > 1 else [label]
        for k, line in enumerate(lines):
            out.append(f"<text class='lbl' x='{x + bw / 2:.1f}' y='{height - 40 + k * 15}' text-anchor='middle'>{escape(line)}</text>")

    bar(0, 0, 100, "var(--ink-2)", start_label, "100", f"{start_label}: 100")
    for i, s in enumerate(steps):
        v0, v1 = levels[i], levels[i + 1]
        bar(i + 1, v0, v1, up if s["factor"] >= 1 else down, s["label"], s.get("note", f"x{s['factor']:.2f}".replace(".", ",")),
            f"{s['label']}: {v0:.0f} a {v1:.0f}")
        # conector con la barra siguiente
        xc = left + (i + 1) * slot + (slot - bw) / 2 + bw
        out.append(f"<line class='lead' x1='{left + i * slot + (slot - bw) / 2 + bw:.1f}' x2='{xc - bw:.1f}' y1='{sy(v0):.1f}' y2='{sy(v0):.1f}' stroke-dasharray='3 3'/>")
    bar(n - 1, 0, levels[-1], "var(--ink)", total_label, f"{levels[-1]:.0f}", f"{total_label}: {levels[-1]:.0f}")
    out.append(f"<line class='axis' x1='{left}' x2='{W - right}' y1='{sy(0):.1f}' y2='{sy(0):.1f}'/></svg>")
    rows = [[start_label, "100", ""]] + [[s["label"], f"{levels[i + 1]:.0f}", f"x{s['factor']:.3f}".replace(".", ",")] for i, s in enumerate(steps)]
    return "".join(out), _table(["Paso", "Índice acumulado", "Multiplicador"], rows)


def scatter(points: Sequence[dict], *, color: str, x_title: str, y_title: str, x_fmt: Callable[[float], str] = lambda v: f"{v * 100:+.0f}%",
            y_fmt: Callable[[float], str] = lambda v: f"{v * 100:+.0f}%", slope_label: str = "", label_years: Sequence = (), alt: str = "",
            height: int = 330) -> tuple[str, str]:
    """points: [{x, y, label}]. Dibuja los puntos y la recta de mínimos cuadrados (solo descriptiva)."""
    left, right, top, bottom = 66, 30, 30, 50
    xs, ys = [p["x"] for p in points], [p["y"] for p in points]
    xt = nice_ticks(min(xs) * 1.1, max(xs) * 1.1, 5)
    yt = nice_ticks(min(ys) * 1.1, max(ys) * 1.1, 5)
    x0, x1, y0, y1 = xt[0], xt[-1], yt[0], yt[-1]
    pw, ph = W - left - right, height - top - bottom
    sx = lambda v: left + (v - x0) / (x1 - x0) * pw
    sy = lambda v: top + (1 - (v - y0) / (y1 - y0)) * ph
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx else 0.0
    icpt = my - slope * mx
    out = [f"<svg class='chart' viewBox='0 0 {W} {height}' role='img' aria-label='{escape(alt)}' preserveAspectRatio='xMidYMid meet'>"]
    for t in yt:
        out.append(f"<line class='grid' x1='{left}' x2='{W - right}' y1='{sy(t):.1f}' y2='{sy(t):.1f}'/><text class='tick' x='{left - 8}' y='{sy(t) + 4:.1f}' text-anchor='end'>{escape(y_fmt(t))}</text>")
    for t in xt:
        out.append(f"<line class='grid' x1='{sx(t):.1f}' x2='{sx(t):.1f}' y1='{top}' y2='{top + ph}'/><text class='tick' x='{sx(t):.1f}' y='{height - 28}' text-anchor='middle'>{escape(x_fmt(t))}</text>")
    if x0 < 0 < x1:
        out.append(f"<line class='zero' x1='{sx(0):.1f}' x2='{sx(0):.1f}' y1='{top}' y2='{top + ph}'/>")
    if y0 < 0 < y1:
        out.append(f"<line class='zero' x1='{left}' x2='{W - right}' y1='{sy(0):.1f}' y2='{sy(0):.1f}'/>")
    out.append(f"<text class='ytitle' x='{left}' y='14'>{escape(y_title)}</text>")
    out.append(f"<text class='ytitle' x='{W - right}' y='{height - 8}' text-anchor='end'>{escape(x_title)}</text>")
    xa, xb = max(x0, min(xs)), min(x1, max(xs))
    out.append(f"<line x1='{sx(xa):.1f}' y1='{sy(icpt + slope * xa):.1f}' x2='{sx(xb):.1f}' y2='{sy(icpt + slope * xb):.1f}' stroke='{color}' stroke-width='2' stroke-dasharray='6 4' opacity='.8'/>")
    for p in points:
        out.append(f"<circle cx='{sx(p['x']):.1f}' cy='{sy(p['y']):.1f}' r='5' fill='{color}' fill-opacity='.72' stroke='var(--paper)' stroke-width='1.5'><title>{escape(str(p['label']))}: {escape(x_fmt(p['x']))} / {escape(y_fmt(p['y']))}</title></circle>")
        if p["label"] in label_years:
            out.append(f"<text class='note' x='{sx(p['x']) + 8:.1f}' y='{sy(p['y']) - 7:.1f}'>{escape(str(p['label']))}</text>")
    if slope_label:
        out.append(f"<text class='lbl' x='{W - right - 4}' y='{top + 16}' text-anchor='end'>{escape(slope_label)}</text>")
    out.append("</svg>")
    rows = [[str(p["label"]), x_fmt(p["x"]), y_fmt(p["y"])] for p in points]
    return "".join(out), _table(["Año", x_title, y_title], rows)


def sparkline(values: Sequence[float], *, color: str, width: int = 150, height: int = 44, mark_last: bool = True) -> str:
    """Miniatura sin ejes para la portada. Los valores faltantes (NaN) cortan la línea."""
    pts = [(i, v) for i, v in enumerate(values) if v == v]
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    span = (hi - lo) or 1
    sx = lambda i: 3 + i / (len(values) - 1) * (width - 6)
    sy = lambda v: height - 4 - (v - lo) / span * (height - 10)
    path = " ".join(("M" if k == 0 or pts[k][0] - pts[k - 1][0] > 1 else "L") + f"{sx(i):.1f},{sy(v):.1f}" for k, (i, v) in enumerate(pts))
    last = f"<circle cx='{sx(pts[-1][0]):.1f}' cy='{sy(pts[-1][1]):.1f}' r='3' fill='{color}'/>" if mark_last else ""
    return (f"<svg class='spark' viewBox='0 0 {width} {height}' role='img' aria-hidden='true'>"
            f"<path d='{path}' fill='none' stroke='{color}' stroke-width='2' stroke-linejoin='round' stroke-linecap='round'/>{last}</svg>")
