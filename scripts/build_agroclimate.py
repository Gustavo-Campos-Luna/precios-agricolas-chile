"""Calcula los índices agroclimáticos anuales a partir de ERA5 (repositorio chile-weather-forecasting).

Uso:
    python scripts/build_agroclimate.py --era5 ../chile-weather-forecasting/data/raw/era5

Escribe ``data/processed/climate_era5/agroclimate_indices.csv`` (un renglón por sitio y año, 35 años, 6 sitios).
"""
from __future__ import annotations

import argparse
from pathlib import Path

from materias_primas_chile import agroclimate as ag

SITES = ["rancagua", "san_fernando", "curico", "talca", "linares", "chillan"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--era5", type=Path, required=True, help="carpeta data/raw/era5 del repositorio de clima")
    parser.add_argument("--out", type=Path, default=Path("data/processed/climate_era5/agroclimate_indices.csv"))
    args = parser.parse_args()
    daily, hourly = ag.load_era5(args.era5, SITES)
    table = ag.build_indices(daily, hourly)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    table.round(3).to_csv(args.out, index=False, encoding="utf-8")
    print(f"{len(table)} renglones -> {args.out}")


if __name__ == "__main__":
    main()
