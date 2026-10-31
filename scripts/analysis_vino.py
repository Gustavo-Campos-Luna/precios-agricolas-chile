"""Uva de vinificación: precio que pagan las viñas por variedad (ODEPA, 2020 en adelante).

Uso (desde la raíz): python scripts/analysis_vino.py
ADVERTENCIA DE UNIDAD: el CSV de ODEPA no declara la unidad del precio. Los valores (cientos de pesos) son compatibles con $/kg,
pero eso es una inferencia, no un dato publicado; por eso se comparan cambios relativos de cada variedad consigo misma y no se
mezclan con precios por kilo de otras fuentes. Precio en pesos de septiembre de 2026 (misma unidad no declarada).
Escribe data/analysis/reports/vino.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, "src")
from materias_primas_chile.varieties import harmonize, load_aliases  # noqa: E402

OUT = Path("data/analysis/reports")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    data = pd.read_parquet("data/processed/odepa_datasets/uva_vinificacion.parquet",
                           columns=["date", "region", "buyer", "variety", "price", "brix"]).dropna(subset=["date", "price"])
    cpi = pd.read_csv("data/processed/bcch/cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    data["month"] = data["date"].dt.to_period("M").dt.to_timestamp()
    data = data.merge(cpi.rename(columns={"date": "month"}), on="month", how="left")
    data["price_real"] = data["price"] * 100 / data["cpi_index"]
    data["year"] = data["date"].dt.year
    data = harmonize(data.fillna({"variety": ""}), "variety", load_aliases())
    named = data[data["variety_key"] != ""]
    lines = ["# Uva de vinificación: precio por variedad", "",
             "**Unidad no declarada por ODEPA** (valores compatibles con $/kg: inferencia). Pesos de septiembre de 2026. "
             f"{len(data):,} cotizaciones de {data['buyer'].nunique()} compradores, {data['date'].min():%Y-%m} a {data['date'].max():%Y-%m}.", ""]

    by_year = data.groupby("year").agg(cotizaciones=("price", "size"), mediana_nominal=("price", "median"), mediana_real=("price_real", "median"),
                                       compradores=("buyer", "nunique"))
    lines += ["## 1. Todas las variedades, por año", "", "| Año | Cotizaciones | Compradores | Mediana nominal | Mediana real |", "|---|---:|---:|---:|---:|"]
    for year, row in by_year.iterrows():
        real = f"{row.mediana_real:,.0f}" if pd.notna(row.mediana_real) else "n/d (sin IPC)"
        lines.append(f"| {year} | {int(row.cotizaciones)} | {int(row.compradores)} | {row.mediana_nominal:,.0f} | {real} |")

    early, late = (2020, 2021), (2024, 2025)
    def median_of(frame, years):
        return frame[frame["year"].isin(years)].groupby("variety_canonical").agg(
            precio=("price_real", "median"), n=("price", "size"), años=("year", "nunique"), compradores=("buyer", "nunique"))
    both = median_of(named, early).join(median_of(named, late), lsuffix="_antes", rsuffix="_ahora", how="inner")
    both = both[(both["n_antes"] >= 15) & (both["n_ahora"] >= 15)]
    both["variacion"] = both["precio_ahora"] / both["precio_antes"] - 1
    both = both.sort_values("n_ahora", ascending=False).head(12)
    lines += ["", f"## 2. Variedades principales: cambio real {early[0]}–{str(early[1])[-2:]} vs {late[0]}–{str(late[1])[-2:]}", "",
              "Solo variedades con al menos 15 cotizaciones en cada período.", "",
              "| Variedad | Real antes | Real ahora | Variación | Cotizaciones (ahora) | Compradores (ahora) |", "|---|---:|---:|---:|---:|---:|"]
    for name, row in both.iterrows():
        lines.append(f"| {name} | {row.precio_antes:,.0f} | {row.precio_ahora:,.0f} | {row.variacion:+.0%} | {int(row.n_ahora)} | {int(row.compradores_ahora)} |")
    if both.empty:
        lines.append("| (ninguna variedad cumple el mínimo) | | | | | |")

    reg = named[named["year"].isin(late)].groupby("region").agg(precio=("price_real", "median"), n=("price", "size")).query("n >= 15").sort_values("n", ascending=False)
    lines += ["", f"## 3. Por región ({late[0]}–{str(late[1])[-2:]}, mediana real de todas las variedades)", "", "| Región | Mediana real | Cotizaciones |", "|---|---:|---:|"]
    lines += [f"| {r} | {row.precio:,.0f} | {int(row.n)} |" for r, row in reg.iterrows()]

    lines += ["", "## Cómo leer esto", "",
              "- Son precios que informan las viñas compradoras, con fechas irregulares; no hay volumen asociado.",
              "- Una mediana por período mezcla compradores y regiones distintas; los cambios pueden reflejar quién informa y no solo el precio.",
              "- Con 7 años de historia no hay base para una tendencia de largo plazo."]
    (OUT / "vino.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
