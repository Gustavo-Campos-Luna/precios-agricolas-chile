"""Análisis mayorista por producto: precio real por kilo, volumen y superficie por variedad.

Uso (desde la raíz): python scripts/analysis_frutas.py [producto ...]
Productos: cereza, uva, manzana, poroto_verde (por defecto todos). Escribe data/analysis/reports/<producto>.md.
Reglas: solo series con kilos declarados en la etiqueta; precio real en pesos de septiembre de 2026; promedio
ponderado por kilos estimados; temporada = año calendario o ventana que parte en `start_month`.
No se interpola ningún mes. Superficie: solo regiones medidas en ambos años del catastro.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/analysis/reports")
PRODUCTS = {
    "cereza": dict(product="Cereza", start_month=11, months=(11, 12, 1, 2), species=["Cerezo"]),
    "uva": dict(product="Uva", start_month=12, months=(12, 1, 2, 3, 4), species=["Vid de Mesa"]),
    "manzana": dict(product="Manzana", start_month=1, months=tuple(range(1, 13)), species=["Manzano Rojo", "Manzano Verde"]),
    "poroto_verde": dict(product="Poroto verde", start_month=1, months=tuple(range(1, 13)), species=[]),
}
BASE_YEARS, RECENT_YEARS = (2014, 2015, 2016), (2022, 2023, 2024)  # año en que parte la temporada


def season_start(date: pd.Series, start_month: int) -> pd.Series:
    return date.dt.year - (date.dt.month < start_month).astype(int)


def label(start: int, start_month: int) -> str:
    return str(start) if start_month == 1 else f"{start}/{str(start + 1)[-2:]}"


def weighted(group: pd.DataFrame, value="price_vwap_clp_kg_real", weight="volume_kg_est") -> float:
    w = group[weight]
    return float((group[value] * w).sum() / w.sum()) if w.sum() > 0 else np.nan


def load(spec: dict) -> pd.DataFrame:
    columns = ["date", "series_id", "variety_canonical", "quality", "market", "market_region", "price_vwap_clp_kg_real",
               "volume_kg_est", "volume_units"]
    data = pd.read_parquet("data/analysis/prices_monthly.parquet", columns=columns,
                           filters=[("product", "==", spec["product"])])
    data = data[data["date"].dt.month.isin(spec["months"])].copy()
    data["start"] = season_start(data["date"], spec["start_month"])
    for column in ("variety_canonical", "quality", "market", "market_region"):
        data[column] = data[column].astype(str)
    return data


def run(name: str, spec: dict) -> str:
    data = load(spec)
    usable = data.dropna(subset=["price_vwap_clp_kg_real", "volume_kg_est"])
    usable = usable[usable["volume_kg_est"] > 0]
    sm = spec["start_month"]
    lines = [f"# {spec['product']} en el mayorista: precio real, volumen y superficie", ""]
    if len(usable) < 200:
        lines += [f"Solo {len(usable)} series-mes tienen kilos declarados ({len(usable) / max(len(data), 1):.0%} de {len(data)}): "
                  "**no alcanza para un análisis por kilo.** Se necesitaría una equivalencia de peso documentada para su unidad.", ""]
        (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "\n".join(lines)
    lines += [f"Datos: {len(data):,} series-mes en la ventana de temporada; {len(usable):,} con kilos declarados "
              f"({len(usable) / len(data):.0%}). Precio en pesos de septiembre de 2026 por kilo, ponderado por kilos.", ""]

    nat = usable.groupby("start").apply(lambda g: pd.Series({
        "precio": weighted(g), "kilos": g["volume_kg_est"].sum() / 1e6, "series": g["series_id"].nunique()}), include_groups=False)
    nat = nat[nat["series"] >= 20]
    lines += ["## 1. Precio real por temporada", "", "| Temporada | CLP/kg real | Millones de kg | Series |", "|---|---:|---:|---:|"]
    for start, row in nat.tail(16).iterrows():
        lines.append(f"| {label(int(start), sm)} | {row.precio:,.0f} | {row.kilos:,.2f} | {int(row.series)} |")
    base = nat.loc[nat.index.intersection(BASE_YEARS), "precio"].mean()
    recent = nat.loc[nat.index.intersection(RECENT_YEARS), "precio"].mean()
    if np.isfinite(base) and np.isfinite(recent):
        lines += ["", f"Promedio {label(BASE_YEARS[0], sm)}–{label(BASE_YEARS[-1], sm)}: **{base:,.0f}** CLP/kg real. "
                      f"Promedio {label(RECENT_YEARS[0], sm)}–{label(RECENT_YEARS[-1], sm)}: **{recent:,.0f}** CLP/kg real. "
                      f"Variación: **{recent / base - 1:+.0%}**.", ""]

    def period(seasons):
        sub = usable[usable["start"].isin(seasons)]
        columns = ["precio", "kilos", "temporadas"]
        if sub.empty:
            return pd.DataFrame(columns=columns)
        return sub.groupby("variety_canonical").apply(lambda g: pd.Series({
            "precio": weighted(g), "kilos": g["volume_kg_est"].sum(), "temporadas": g["start"].nunique()}),
            include_groups=False).reindex(columns=columns)
    both = period(BASE_YEARS).join(period(RECENT_YEARS), lsuffix="_antes", rsuffix="_ahora", how="inner")
    both = both[(both["temporadas_antes"] >= 2) & (both["temporadas_ahora"] >= 2) & (both.index != "")]
    both["variacion"] = both["precio_ahora"] / both["precio_antes"] - 1
    both = both.sort_values("kilos_ahora", ascending=False).head(10)
    lines += ["## 2. Variedades principales: cambio del precio real", "",
              "Solo variedades presentes en al menos 2 temporadas de cada período.", "",
              "| Variedad | CLP/kg antes | CLP/kg ahora | Variación | Millones de kg (ahora) |", "|---|---:|---:|---:|---:|"]
    for variety, row in both.iterrows():
        lines.append(f"| {variety} | {row.precio_antes:,.0f} | {row.precio_ahora:,.0f} | {row.variacion:+.0%} | {row.kilos_ahora / 1e6:,.2f} |")
    if both.empty:
        lines.append("| (ninguna variedad cumple el mínimo) | | | | |")

    for title, column in (("3. Por región del mercado", "market_region"), ("4. Por calidad", "quality")):
        sub = usable[usable["start"].isin(RECENT_YEARS)]
        table = sub.groupby(column).apply(lambda g: pd.Series({"precio": weighted(g), "kilos": g["volume_kg_est"].sum() / 1e6}),
                                          include_groups=False).sort_values("kilos", ascending=False).head(7)
        lines += ["", f"## {title} (temporadas recientes)", "", f"| {column} | CLP/kg real | Millones de kg |", "|---|---:|---:|"]
        for key, row in table.iterrows():
            lines.append(f"| {key} | {row.precio:,.0f} | {row.kilos:,.2f} |")


    # Control de composición: ¿el cambio sobrevive si se fija el mercado y la calidad principales?
    recent_rows = usable[usable["start"].isin(RECENT_YEARS)]
    if not recent_rows.empty:
        top_market = recent_rows.groupby("market")["volume_kg_est"].sum().idxmax()
        top_quality = recent_rows.groupby("quality")["volume_kg_est"].sum().idxmax()
        fixed = usable[(usable["market"] == top_market) & (usable["quality"] == top_quality)]
        before_fixed = weighted(fixed[fixed["start"].isin(BASE_YEARS)])
        after_fixed = weighted(fixed[fixed["start"].isin(RECENT_YEARS)])
        lines += ["", "## 3b. Control de composición", "",
                  f"Mismo mercado (**{top_market}**) y misma calidad (**{top_quality}**) en ambos períodos, para descartar que el "
                  "cambio nacional sea solo un cambio de mezcla."]
        if np.isfinite(before_fixed) and np.isfinite(after_fixed):
            overall = f"{recent / base - 1:+.0%}" if np.isfinite(base) and np.isfinite(recent) else "n/d"
            lines += ["", f"| | CLP/kg real antes | CLP/kg real ahora | Variación |", "|---|---:|---:|---:|",
                      f"| Mercado y calidad fijos | {before_fixed:,.0f} | {after_fixed:,.0f} | **{after_fixed / before_fixed - 1:+.0%}** |",
                      f"| Todo el mayorista | {base:,.0f} | {recent:,.0f} | {overall} |"]
        else:
            lines.append("\nNo hay datos de ese mercado y calidad en ambos períodos.")

    lines += ["", "## 5. Superficie plantada (catastro)", ""]
    if spec["species"]:
        coverage = pd.read_csv("data/analysis/orchards_coverage.csv", dtype={"region_id": str})
        measured = coverage.groupby("year").region_id.apply(set)
        orchards = pd.read_parquet("data/analysis/orchards.parquet", columns=["year", "region_id", "species", "variety_canonical", "area_ha"],
                                   filters=[("species", "in", spec["species"])])
        orchards["region_id"] = orchards["region_id"].astype(str)
        by_region = orchards.groupby(["region_id", "year"]).area_ha.sum().unstack(fill_value=0)
        # Peso de cada región = su mayor superficie medida de esta especie en cualquier año: es el tamaño real
        # de su huella. Una comparación es representativa si las regiones medidas en ambos años concentran esa huella.
        footprint = by_region.max(axis=1)
        years = sorted(int(y) for y in measured.index)
        best = None
        for i, first in enumerate(years):
            for last in years[i + 1:]:
                if last - first < 4:
                    continue
                common = measured[first] & measured[last]
                share = float(footprint[footprint.index.isin(common)].sum() / footprint.sum()) if footprint.sum() > 0 else 0.0
                key = (round(share, 2), last - first, last)
                if best is None or key > best[0]:
                    best = (key, first, last, common, share)
        if best is None:
            lines.append("No hay dos años con al menos 4 años de distancia.")
        else:
            _, first, last, common, share = best
            lines.append(f"Mejor par de años comparables: {first} vs {last}. Las {len(common)} regiones medidas en ambos años concentran "
                         f"**{share:.0%}** de la superficie histórica de la especie.")
            if share < 0.7:
                lines += ["", "**No se compara:** esas regiones dejan fuera gran parte de donde se planta esta especie; el resultado no sería "
                              "representativo del país. Hace falta un par de años que midan las mismas regiones productoras."]
            else:
                sub = orchards[orchards["year"].isin([first, last]) & orchards["region_id"].isin(common)]
                total = sub.groupby("year").area_ha.sum()
                area = sub.groupby(["variety_canonical", "year"]).area_ha.sum().unstack().fillna(0).sort_values(last, ascending=False).head(8)
                lines += ["", f"Superficie en esas regiones: **{total[first]:,.0f} ha** -> **{total[last]:,.0f} ha** ({total[last] / total[first] - 1:+.0%}).",
                          "", f"| Variedad | {first} (ha) | {last} (ha) | Cambio |", "|---|---:|---:|---:|"]
                for variety, row in area.iterrows():
                    change = f"{row[last] / row[first] - 1:+.0%}" if row[first] > 0 else "no existía"
                    lines.append(f"| {variety or '(sin variedad)'} | {row[first]:,.0f} | {row[last]:,.0f} | {change} |")
    else:
        lines.append("El catastro frutícola no incluye esta especie (es hortaliza).")

    lines += ["", "## Cómo leer esto", "",
              "- Precio **mayorista** (9 regiones): no es el precio al productor ni el de exportación.",
              "- Los kilos son estimados desde envases con peso declarado; no son cosecha ni exportación.",
              "- La superficie es capacidad plantada, no producción.",
              "- Que el precio baje cuando sube la oferta **no prueba causa**: dólar, clima y demanda externa también influyen."]
    (OUT / f"{name}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    chosen = sys.argv[1:] or list(PRODUCTS)
    for name in chosen:
        text = run(name, PRODUCTS[name])
        print(f"\n===== {name} =====\n{text}\n")


if __name__ == "__main__":
    main()
