"""NASA POWER histórico por punto; nunca representa un promedio regional.

HTTP por urllib con proxy y TLS del entorno. Datos faltantes se conservan.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .storage import atomic_write, receipt

ENDPOINT = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = {"T2M": "temperature_mean_c", "T2M_MIN": "temperature_min_c",
              "T2M_MAX": "temperature_max_c", "PRECTOTCORR": "precipitation_mm"}


@dataclass(frozen=True)
class Location:
    location_id: str
    latitude: float
    longitude: float
    region_code: str = ""

    def __post_init__(self):
        if not self.location_id or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for c in self.location_id):
            raise ValueError("location_id debe ser slug ASCII minúsculo")
        if not (-90 <= self.latitude <= 90 and -180 <= self.longitude <= 180):
            raise ValueError("Coordenadas fuera de rango")


def build_power_url(location: Location, start: str, end: str) -> str:
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last or first < date(1981, 1, 1):
        raise ValueError("Rango NASA POWER inválido (inicio desde 1981)")
    return ENDPOINT + "?" + urlencode({
        "parameters": ",".join(PARAMETERS), "community": "AG",
        "latitude": location.latitude, "longitude": location.longitude,
        "start": first.strftime("%Y%m%d"), "end": last.strftime("%Y%m%d"),
        "format": "JSON", "time-standard": "UTC",
    })


def parse_power(payload: bytes | dict, location: Location) -> pd.DataFrame:
    document = json.loads(payload) if isinstance(payload, bytes) else payload
    series = document.get("properties", {}).get("parameter", {})
    missing = set(PARAMETERS) - set(series)
    if missing:
        raise ValueError(f"Respuesta NASA POWER incompleta: {sorted(missing)}")
    frame = pd.DataFrame({name: values for name, values in series.items() if name in PARAMETERS})
    if frame.empty:
        raise ValueError("Respuesta NASA POWER sin observaciones")
    frame.index = pd.to_datetime(frame.index, format="%Y%m%d", errors="raise")
    frame.index.name = "date"
    fill_value = document.get("header", {}).get("fill_value", -999)
    frame = frame.apply(pd.to_numeric, errors="raise").replace(fill_value, float("nan"))
    # Invalid precipitation is a source defect, not a drought observation.
    if (frame["PRECTOTCORR"].dropna() < 0).any():
        raise ValueError("Precipitación negativa distinta de missing sentinel")
    frame = frame.rename(columns=PARAMETERS).sort_index().reset_index()
    frame["location_id"] = location.location_id
    frame["latitude"] = location.latitude
    frame["longitude"] = location.longitude
    frame["region_code"] = location.region_code
    frame["spatial_scope"] = "grid_point_proxy"
    frame["source"] = "nasa_power"
    return frame


def fetch_power(location: Location, start: str, end: str,
                raw_root: str | Path = "data/raw/climate", *, timeout: float = 90,
                attempts: int = 3) -> pd.DataFrame:
    """Descarga una consulta auditable; errores no generan tablas falsas.

    La caché existente se lee sin volver a consultar. Para otra versión de fuente,
    usar un raw_root nuevo. Se recomienda una consulta por celda y año.
    """
    if attempts < 1:
        raise ValueError("attempts debe ser positivo")
    url = build_power_url(location, start, end)
    path = Path(raw_root) / location.location_id / f"{start}_{end}.json"
    if path.exists():
        manifest_path = path.with_suffix(path.suffix + ".manifest.json")
        if not manifest_path.exists():
            raise ValueError("Caché climática sin manifiesto; verificar procedencia")
        manifest = json.loads(manifest_path.read_text())
        import hashlib
        if manifest["url"] != url or manifest["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
            raise ValueError("Caché climática no coincide con coordenadas/consulta/hash")
        return parse_power(path.read_bytes(), location)
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "materias-primas-chile/0.1 research"})
            with urlopen(request, timeout=timeout) as response:
                payload = response.read()
            frame = parse_power(payload, location)
            atomic_write(path, payload)
            receipt(path, url=url, source="nasa_power", location_id=location.location_id,
                    latitude=location.latitude, longitude=location.longitude,
                    start=start, end=end, time_standard="UTC", spatial_scope="grid_point_proxy")
            return frame
        except (OSError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(min(2 ** attempt, 8))
    raise RuntimeError("Descarga climática no completada")


def aggregate_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Solo meses calendario completos producen medidas mensuales.

    No se imputan días faltantes ni se suman meses parciales. Se conserva
    cobertura por variable y punto para auditar exclusiones.
    """
    required = {"date", "location_id", *PARAMETERS.values()}
    if not required.issubset(daily.columns):
        raise ValueError(f"Columnas climáticas faltantes: {sorted(required - set(daily.columns))}")
    data = daily.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise").dt.normalize()
    if data.duplicated(["location_id", "date"]).any():
        raise ValueError("Días duplicados por punto climático")
    data["month"] = data["date"].dt.to_period("M").dt.to_timestamp()
    rows = []
    for (location_id, month), group in data.groupby(["location_id", "month"], sort=True):
        expected = month.days_in_month
        row = {"location_id": location_id, "month": month, "expected_days": expected,
               "observed_days": len(group), "spatial_scope": "grid_point_proxy"}
        for column in PARAMETERS.values():
            count = group[column].notna().sum()
            row[column + "_valid_days"] = int(count)
            row[column] = (group[column].sum() if column == "precipitation_mm" else group[column].mean()) if count == expected else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def historical_features(monthly: pd.DataFrame, forecast_origin: str, *, release_lag_days: int = 60) -> pd.DataFrame:
    """Excluye meses cuyo fin + lag es posterior al origen del pronóstico.

    Lag es una hipótesis conservadora configurable, no prueba de disponibilidad
    histórica. Backtests rigurosos requieren vintages almacenados de cada fuente.
    """
    if release_lag_days < 0:
        raise ValueError("release_lag_days debe ser no negativo")
    frame = monthly.copy()
    months = pd.to_datetime(frame["month"])
    frame["assumed_available_after"] = months + pd.offsets.MonthEnd(0) + pd.Timedelta(days=release_lag_days)
    return frame.loc[frame["assumed_available_after"] < pd.Timestamp(forecast_origin)].copy()
