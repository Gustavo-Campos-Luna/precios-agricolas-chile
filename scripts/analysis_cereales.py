"""Cereales y legumbres: precio al productor (FAOSTAT, Cotrisa) frente a la referencia internacional (Pink Sheet).

Uso (desde la raíz): python scripts/analysis_cereales.py
Todo en pesos de septiembre de 2026 por tonelada. FAOSTAT es anual (deflactado con el IPC anual, solo años completos);
Cotrisa es la campaña vigente (poder comprador por región, desde 2024); Pink Sheet es dólar internacional convertido al
dólar observado. Escribe data/analysis/reports/cereales.md.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path("data/analysis/reports")
FAO = {"Wheat": "Trigo", "Maize (corn)": "Maíz", "Oats": "Avena", "Barley": "Cebada", "Rice": "Arroz", "Beans, dry": "Poroto seco"}
PINK = {"Wheat, US HRW": "Trigo (EE.UU. HRW)", "Maize": "Maíz", "Barley": "Cebada", "Rice, Thai 5%": "Arroz (Tailandia 5%)"}
BASE, RECENT = (2014, 2015, 2016), (2022, 2023, 2024)
JUMP = 1.8  # salto anual (x1,8 o /1,8) en moneda local que no se explica por el dólar: se trata como quiebre de la fuente


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    ext = pd.read_parquet("data/analysis/external_prices_monthly.parquet")
    for column in ("source", "level", "product", "unit", "currency", "frequency"):
        ext[column] = ext[column].astype(str)
    cpi = pd.read_csv("data/processed/bcch/cpi_index.csv", usecols=["date", "cpi_index"], parse_dates=["date"])
    usd = pd.read_csv("data/processed/bcch/usd_clp_monthly.csv", usecols=["date", "usd_clp"], parse_dates=["date"])
    lines = ["# Cereales y legumbres: precio al productor y referencia internacional", "",
             "Pesos de septiembre de 2026 por tonelada. Precio **al productor/poder comprador**, no mayorista ni consumidor.", ""]

    # 1) FAOSTAT al productor, real, anual
    fao = ext[(ext.source == "FAOSTAT") & (ext["unit"] == "LCU/tonne") & (ext.frequency == "annual") & ext["product"].isin(FAO)].copy()
    fao["year"] = fao["date"].dt.year
    nominal = fao.pivot_table(index="year", columns="product", values="value").rename(columns=FAO)
    table = fao.pivot_table(index="year", columns="product", values="value_real_clp").rename(columns=FAO)
    breaks, start_year = {}, {}
    for name in nominal.columns:
        series = nominal[name].dropna()
        jump = series / series.shift(1)
        found = [int(y) for y, r in jump.dropna().items() if r > JUMP or r < 1 / JUMP]
        breaks[name] = found
        start_year[name] = max(found) if found else int(series.index.min())
        table.loc[table.index < start_year[name], name] = np.nan  # no se cruza un quiebre de la fuente
    lines += ["## 1. Precio real al productor (FAOSTAT, anual)", "", "| Año | " + " | ".join(table.columns) + " |", "|---|" + "---:|" * len(table.columns)]
    for year, row in table.tail(12).iterrows():
        lines.append(f"| {year} | " + " | ".join(f"{v:,.0f}" if pd.notna(v) else "n/d" for v in row) + " |")
    lines += ["", "| Producto | Promedio período base | Promedio 2022–24 | Variación | Último año disponible |", "|---|---:|---:|---:|---|"]
    for name in table.columns:
        s = table[name].dropna()
        base_years = tuple(range(max(2014, start_year[name]), max(2014, start_year[name]) + 3))
        b, r = s.loc[s.index.intersection(base_years)].mean(), s.loc[s.index.intersection(RECENT)].mean()
        last = f"{int(s.index.max())}: {s.iloc[-1]:,.0f}" if len(s) else "n/d"
        change = f"{r / b - 1:+.0%}" if np.isfinite(b) and np.isfinite(r) else "n/d"
        base_label = f"{base_years[0]}–{str(base_years[-1])[-2:]}"
        fmt = lambda v: f"{v:,.0f}" if np.isfinite(v) else "n/d"
        lines.append(f"| {name} | {fmt(b)} ({base_label}) | {fmt(r)} | {change} | {last} |")
    detected = {k: v for k, v in breaks.items() if v}
    lines += ["", "**Quiebres detectados en la serie de FAOSTAT** (salto anual mayor a x1,8 en pesos nominales). Los años anteriores al último "
              "quiebre se descartan de cada producto, porque la fuente parece cambiar de base de medición y el cambio se leería como "
              "una alza o baja que no ocurrió:", ""]
    lines += [f"- {k}: salto en {', '.join(map(str, v))}; se usa desde {start_year[k]}." for k, v in detected.items()] or ["- Ninguno."]
    lines += ["", "Años con IPC incompleto (el año en curso) quedan vacíos: no se extrapola la inflación.", ""]

    # 2) Pink Sheet internacional en pesos reales
    pink = ext[(ext.source == "World Bank Pink Sheet") & ext["product"].isin(PINK)][["date", "product", "value"]].copy()
    pink = pink.merge(usd, on="date", how="left").merge(cpi, on="date", how="left")
    pink["clp_t_real"] = pink["value"] * pink["usd_clp"] * 100 / pink["cpi_index"]
    pink["year"] = pink["date"].dt.year
    counts = pink.groupby(["product", "year"]).clp_t_real.count().unstack()
    annual = pink.groupby(["product", "year"]).clp_t_real.mean().unstack()
    annual = annual.where(counts >= 12)  # solo años completos
    lines += ["## 2. Referencia internacional en pesos reales (Pink Sheet × dólar observado)", "",
              "| Producto | Promedio 2014–16 | Promedio 2022–24 | Variación | USD nominal 2022–24 vs 2014–16 |", "|---|---:|---:|---:|---:|"]
    usd_nominal = pink.groupby(["product", "year"]).value.mean().unstack()
    for key, label in PINK.items():
        if key not in annual.index:
            continue
        s = annual.loc[key].dropna()
        b, r = s.loc[s.index.intersection(BASE)].mean(), s.loc[s.index.intersection(RECENT)].mean()
        n = usd_nominal.loc[key]
        nb, nr = n.loc[n.index.intersection(BASE)].mean(), n.loc[n.index.intersection(RECENT)].mean()
        lines.append(f"| {label} | {b:,.0f} | {r:,.0f} | {r / b - 1:+.0%} | {nr / nb - 1:+.0%} |")
    lines.append("")

    # 3) Relación productor chileno / internacional (trigo y maíz)
    lines += ["## 3. Precio chileno al productor frente al internacional", "",
              "Cuociente FAOSTAT (CLP/t real) ÷ Pink Sheet (CLP/t real). Cerca de 1 = el productor chileno recibe lo que vale afuera; "
              "mayor a 1 = recibe más (flete, calidad, protección); menor = descuento.", "",
              "| Año | Trigo | Maíz |", "|---|---:|---:|"]
    pairs = {"Wheat": "Wheat, US HRW", "Maize (corn)": "Maize"}
    ratios = {}
    for fao_key, pink_key in pairs.items():
        if fao_key in table.columns or FAO.get(fao_key) in table.columns:
            local = table[FAO[fao_key]]
            if pink_key in annual.index:
                ratios[FAO[fao_key]] = (local / annual.loc[pink_key]).dropna()
    years = sorted(set().union(*[set(r.index) for r in ratios.values()])) if ratios else []
    for year in years[-10:]:
        lines.append(f"| {year} | " + " | ".join(f"{ratios[k].get(year, np.nan):.2f}" if k in ratios and year in ratios[k].index else "n/d" for k in ("Trigo", "Maíz")) + " |")
    lines.append("")

    # 4) Cotrisa: campaña vigente por región
    cot = ext[ext.source == "Cotrisa"].copy()
    cot[["grain", "region"]] = cot["product"].str.split(" \\| ", n=1, expand=True)
    cot["tonnes_factor"] = 10.0  # $/qqm -> $/t (1 quintal métrico = 100 kg)
    cot["clp_t_real"] = cot["value_real_clp"] * cot["tonnes_factor"]
    cot["year"] = cot["date"].dt.year
    lines += ["## 4. Poder comprador Cotrisa (campaña vigente, $/t real)", "",
              "Solo desde 2024 (trigo) y 2025 (maíz); no hay historia previa en esta fuente.", "",
              "| Grano | Año | Mediana nacional (CLP/t real) | Regiones con precio | Meses |", "|---|---:|---:|---:|---:|"]
    for (grain, year), g in cot.dropna(subset=["clp_t_real"]).groupby(["grain", "year"]):
        lines.append(f"| {grain} | {year} | {g.clp_t_real.median():,.0f} | {g.region.nunique()} | {g.date.nunique()} |")
    latest = cot[cot["grain"] == "Trigo"].dropna(subset=["clp_t_real"])
    if not latest.empty:
        last_month = latest["date"].max()
        by_region = latest[latest["date"] == last_month].groupby("region").clp_t_real.median().sort_values(ascending=False)
        lines += ["", f"Trigo, último mes ({last_month:%Y-%m}), por región:", "", "| Región | CLP/t real |", "|---|---:|"]
        lines += [f"| {r} | {v:,.0f} |" for r, v in by_region.items()]

    lines += ["", "## Cómo leer esto", "",
              "- FAOSTAT define cada producto a su manera (sin variedad ni calidad) y tiene rezago anual; su último año puede ser estimado.",
              "- Cotrisa es poder comprador de la campaña vigente, con pocos meses; no sirve para tendencias de largo plazo.",
              "- El precio internacional en pesos mezcla dos efectos: el dólar y el precio en dólares. La última columna de la tabla 2 los separa.",
              "- Que dos series se muevan juntas no prueba causa."]
    (OUT / "cereales.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
