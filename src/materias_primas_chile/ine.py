"""Costo de la mano de obra y remuneraciones del INE, vía su servicio SDMX público (sin clave).

Se usan los índices nacionales empalmados (base 2023 = 100) de la Encuesta Mensual de Remuneraciones y Costos Laborales,
desde diciembre de 2009. No distinguen la agricultura: son un indicador general del costo de contratar en Chile. Los
índices por rama económica del INE parten en 2023 y no sirven para comparar con la década pasada.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pandas as pd

ENDPOINT = "https://sdmx.ine.gob.cl/rest/data/CL01,{flow},1.0/all"
FLOWS = {"DF_ICLEMP2023": "costo_laboral_nominal", "DF_IREMP2023": "remuneraciones_nominal", "DF_IRREALEMP2023": "remuneraciones_real"}


def parse_sdmx_csv(text: str, unit: str | None = "IX") -> pd.DataFrame:
    """Lee el CSV SDMX del INE y devuelve ``month`` (primer día del mes), ``value`` e ``indicator``.

    El servicio mezcla en un mismo flujo variaciones a 12 meses (``VAR12``) y niveles de índice (``IX``); por omisión se
    conservan solo los niveles. Las observaciones vacías se descartan en lugar de rellenarse.
    """
    frame = pd.read_csv(io.StringIO(text))
    if unit is not None and "UNIDAD" in frame.columns:
        frame = frame[frame["UNIDAD"] == unit]
    period = frame["TIME_PERIOD"].astype(str).str.extract(r"^(\d{4})-M(\d{2})$")
    out = pd.DataFrame({"month": pd.to_datetime(period[0] + "-" + period[1] + "-01", errors="coerce"),
                        "value": pd.to_numeric(frame["OBS_VALUE"], errors="coerce"), "indicator": frame["INDICADOR"]})
    return out.dropna(subset=["month", "value"]).sort_values("month").reset_index(drop=True)


def download(raw_dir: Path, flows: dict[str, str] | None = None, client: httpx.Client | None = None) -> dict[str, pd.DataFrame]:
    """Descarga cada flujo, guarda el original con su manifiesto y devuelve las tablas de nivel."""
    http = client or httpx.Client(timeout=90)
    raw_dir.mkdir(parents=True, exist_ok=True)
    tables = {}
    for flow, name in (flows or FLOWS).items():
        url = ENDPOINT.format(flow=flow)
        response = http.get(url, headers={"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"})
        response.raise_for_status()
        (raw_dir / f"{flow}.csv").write_bytes(response.content)
        manifest = {"flow": flow, "url": url, "captured_utc": datetime.now(UTC).isoformat(timespec="seconds"), "sha256": hashlib.sha256(response.content).hexdigest()}
        (raw_dir / f"{flow}.manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        tables[name] = parse_sdmx_csv(response.text, unit=None if flow == "DF_IRREALEMP2023" else "IX")
    return tables
