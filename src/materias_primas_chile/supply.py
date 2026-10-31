"""Oferta: superficie plantada por especie, variedad, región y año de plantación (catastro CIREN-ODEPA).

Relaciona el precio con cuánta fruta puede haber. Dos advertencias que condicionan cualquier uso:
- El catastro se levanta por ZONAS distintas cada año. La superficie de dos años solo es comparable
  entre las mismas regiones; ``coverage`` indica qué regiones se midieron en cada año.
- La superficie plantada no es cosecha: depende de la edad del huerto (``planting_year``), del
  clima y del manejo. Es un indicador de capacidad, no de producción.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .tables import read_table
from .varieties import harmonize, load_aliases, load_species_map


def build_orchards(source: str | Path = "data/processed/odepa_datasets/catastro_fruticola.csv") -> tuple[pd.DataFrame, pd.DataFrame]:
    data = read_table(source, ["year", "region_id", "region", "species", "variety", "planting_year", "trees", "area_ha"])
    data = harmonize(data.fillna({"variety": ""}), "variety", load_aliases())
    species = load_species_map().rename(columns={"note": "species_note"})
    data = data.merge(species, on="species", how="left")  # especies sin contraparte en el mayorista quedan sin product
    keys = ["year", "region_id", "region", "species", "product", "market_use", "variety_key", "variety_canonical",
            "variety_group", "planting_year"]
    grouped = data.groupby(keys, dropna=False, observed=True).agg(
        area_ha=("area_ha", "sum"), trees=("trees", "sum"), n_blocks=("area_ha", "size")).reset_index()
    grouped["variety_display"] = grouped["variety_canonical"].astype(str)
    coverage = (data.groupby(["year", "region_id", "region"], dropna=False)
                .agg(area_ha=("area_ha", "sum"), n_blocks=("area_ha", "size")).reset_index())
    return grouped, coverage


def write_orchards(source: str | Path = "data/processed/odepa_datasets/catastro_fruticola.csv",
                   output: str | Path = "data/analysis") -> dict:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    orchards, coverage = build_orchards(source)
    orchards.to_parquet(output / "orchards.parquet", index=False, compression="zstd")
    coverage.to_csv(output / "orchards_coverage.csv", index=False)
    years = coverage.groupby("year").region_id.nunique()
    summary = {"rows": len(orchards), "years": [int(orchards.year.min()), int(orchards.year.max())],
               "regions_per_year": {int(k): int(v) for k, v in years.items()},
               "area_ha_unmapped_to_wholesale_product": round(float(orchards.loc[orchards["product"].isna(), "area_ha"].sum()), 0),
               "note": "Superficie comparable entre años solo dentro de las mismas regiones (ver orchards_coverage.csv)"}
    (output / "orchards.report.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    return summary
