"""Descarga el comercio exterior relevante desde UN Comtrade y escribe tablas pequeñas en data/processed/comtrade.

Uso:
    python scripts/download_comtrade.py                 # todo el plan (unos 20 minutos por la tasa de la API)
    python scripts/download_comtrade.py --only china    # solo un bloque: china | competencia | trigo | trigo_exportadores

Originales (con hash) en data/raw/comtrade/; tablas resultantes en data/processed/comtrade/*.csv.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from materias_primas_chile import comtrade as ct

CHERRY, TABLE_GRAPE, WHEAT = "080929", "080610", "1001"


def plans() -> dict[str, list[dict]]:
    china = [{"name": f"china_imp_cereza_{y}", "freq": "A", "params": dict(reporterCode=156, period=y, cmdCode=CHERRY, flowCode="M")} for y in range(2010, 2026)]
    # mensual: importaciones chinas de cereza desde el mundo y desde Chile, 2018 a 2026
    for y in range(2018, 2027):  # la vista previa admite un solo período por consulta
        for m in range(1, 13):
            if (y, m) > (2026, 8):
                break
            china.append({"name": f"china_imp_cereza_mensual_{y}{m:02d}", "freq": "M", "params": dict(reporterCode=156, period=f"{y}{m:02d}", cmdCode=CHERRY, flowCode="M", partnerCode="0,152")})
    competencia = []
    for rep in (152, 604, 32, 710):
        for cmd, label in ((TABLE_GRAPE, "uva_mesa"), (CHERRY, "cereza")):
            for y in range(2010, 2026):
                competencia.append({"name": f"exp_{rep}_{label}_{y}", "freq": "A", "params": dict(reporterCode=rep, period=y, cmdCode=cmd, flowCode="X", partnerCode=0)})
    trigo = [{"name": f"chile_imp_trigo_{y}", "freq": "A", "params": dict(reporterCode=152, period=y, cmdCode=WHEAT, flowCode="M")} for y in range(2010, 2026)]
    # valor unitario de exportación de trigo de los proveedores de Chile (proxy del precio de cada origen)
    exportadores = [{"name": f"exp_{rep}_trigo_{y}", "freq": "A", "params": dict(reporterCode=rep, period=y, cmdCode=WHEAT, flowCode="X", partnerCode=0)}
                    for rep in (32, 842, 124, 858) for y in range(2010, 2026)]
    return {"china": china, "competencia": competencia, "trigo": trigo, "trigo_exportadores": exportadores}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["china", "competencia", "trigo", "trigo_exportadores"])
    parser.add_argument("--raw", type=Path, default=Path("data/raw/comtrade"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/comtrade"))
    args = parser.parse_args()
    client = ct.Client(args.raw)
    args.out.mkdir(parents=True, exist_ok=True)
    for block, plan in plans().items():
        if args.only and args.only != block:
            continue
        frame = ct.collect(client, plan)
        frame["kg"] = ct.kilos(frame)
        path = args.out / f"{block}.csv"
        frame.to_csv(path, index=False, encoding="utf-8")
        print(f"{block}: {len(frame)} filas -> {path}", flush=True)


if __name__ == "__main__":
    main()
