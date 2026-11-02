"""Índices agroclimáticos anuales por sitio, calculados desde ERA5 diario y horario.

Los datos se descargan con el repositorio ``chile-weather-forecasting`` (Open-Meteo, reanálisis ERA5). Aquí solo se
resumen en un indicador por sitio y año de cosecha ``y`` (la temporada de cereza que empieza en noviembre de ``y``):

* ``chill_hours``: horas entre 0 y 7,2 °C de mayo a agosto de ``y`` (frío invernal, aproximación simple al modelo Utah).
* ``frost_days_0`` y ``frost_days_2``: días con mínima de 0 °C o menos, y de 2 °C o menos, entre septiembre y octubre.
* ``tmin_spring``: mínima media de septiembre y octubre.
* ``rain_harvest_mm`` y ``rainy_days_5``: lluvia total y días con 5 mm o más entre el 15 de noviembre y el 31 de enero.
* ``heat_days_30``: días con máxima de 30 °C o más en esa misma ventana.
* ``rain_winter_mm``: lluvia de junio a agosto.

Advertencia de uso: ERA5 es más cálido que las estaciones en las noches frías (en Curicó detecta cerca de 23% de las
heladas reales), por lo que los índices de helada subestiman el nivel y solo sirven para comparar años entre sí.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

INDEX_COLUMNS = ["chill_hours", "frost_days_0", "frost_days_2", "tmin_spring", "rain_harvest_mm", "rainy_days_5", "heat_days_30", "rain_winter_mm"]


def season_indices(daily: pd.DataFrame, hourly_temperature: pd.Series | None, year: int) -> dict[str, float]:
    """Índices de un sitio para la temporada que empieza en ``year``. Devuelve NaN donde falta la ventana completa."""
    nan = float("nan")

    def window(frame: pd.DataFrame | pd.Series, start: str, end: str):
        return frame.loc[start:end]

    spring = window(daily, f"{year}-09-01", f"{year}-10-31")
    harvest = window(daily, f"{year}-11-15", f"{year + 1}-01-31")
    winter = window(daily, f"{year}-06-01", f"{year}-08-31")
    complete = lambda w, days: len(w) >= days  # noqa: E731
    out = {c: nan for c in INDEX_COLUMNS}
    if complete(spring, 61):
        out["frost_days_0"] = float((spring["temperature_2m_min"] <= 0).sum())
        out["frost_days_2"] = float((spring["temperature_2m_min"] <= 2).sum())
        out["tmin_spring"] = float(spring["temperature_2m_min"].mean())
    if complete(harvest, 78):
        out["rain_harvest_mm"] = float(harvest["precipitation_sum"].sum())
        out["rainy_days_5"] = float((harvest["precipitation_sum"] >= 5).sum())
        out["heat_days_30"] = float((harvest["temperature_2m_max"] >= 30).sum())
    if complete(winter, 92):
        out["rain_winter_mm"] = float(winter["precipitation_sum"].sum())
    if hourly_temperature is not None:
        win = window(hourly_temperature, f"{year}-05-01", f"{year}-08-31")
        if len(win) >= 123 * 24:
            out["chill_hours"] = float(((win > 0) & (win <= 7.2)).sum())
    return out


def build_indices(daily_by_site: dict[str, pd.DataFrame], hourly_by_site: dict[str, pd.Series], first: int = 1991, last: int = 2025) -> pd.DataFrame:
    rows = []
    for site, daily in daily_by_site.items():
        for year in range(first, last + 1):
            rows.append({"site": site, "year": year, **season_indices(daily, hourly_by_site.get(site), year)})
    return pd.DataFrame(rows)


def load_era5(era5_dir: Path, sites: list[str]) -> tuple[dict[str, pd.DataFrame], dict[str, pd.Series]]:
    daily, hourly = {}, {}
    for site in sites:
        daily[site] = pd.read_parquet(era5_dir / "daily" / f"{site}.parquet")
        hourly[site] = pd.read_parquet(era5_dir / "hourly" / f"{site}.parquet", columns=["temperature_2m"])["temperature_2m"]
    return daily, hourly


def regional_mean(indices: pd.DataFrame) -> pd.DataFrame:
    """Promedio de los sitios por año: un índice regional para O'Higgins, Maule y Ñuble."""
    return indices.groupby("year")[INDEX_COLUMNS].mean()
