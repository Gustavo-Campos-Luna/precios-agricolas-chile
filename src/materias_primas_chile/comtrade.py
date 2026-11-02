"""Comercio exterior desde UN Comtrade (API pública de vista previa, sin clave).

Sirve para contrastar la historia de la cereza y del trigo con una fuente independiente de las estadísticas chilenas:
lo que China declara haber importado, lo que exportan los competidores y de dónde importa Chile su trigo.

Límites de la API pública: hasta 500 filas por consulta y una tasa baja de llamadas (responde 429 si se excede), por lo
que se consulta de a un año y con pausas. Cada respuesta original se guarda con URL, fecha UTC y SHA-256.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pandas as pd

BASE = "https://comtradeapi.un.org/public/v1/preview/C"
COLUMNS = ["refYear", "period", "reporterCode", "flowCode", "partnerCode", "cmdCode", "netWgt", "qty", "primaryValue", "cifvalue", "fobvalue"]
REPORTERS = {156: "China", 152: "Chile", 604: "Perú", 32: "Argentina", 710: "Sudáfrica"}
PARTNERS = {0: "Mundo", 152: "Chile", 604: "Perú", 32: "Argentina", 710: "Sudáfrica", 842: "Estados Unidos", 124: "Canadá", 858: "Uruguay",
            156: "China", 344: "Hong Kong", 410: "Corea del Sur", 392: "Japón", 826: "Reino Unido", 528: "Países Bajos", 76: "Brasil"}


def build_url(freq: str, params: dict[str, Any]) -> str:
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{BASE}/{freq}/HS?{query}"


def parse_payload(payload: dict[str, Any]) -> pd.DataFrame:
    """Convierte la respuesta JSON en una tabla con columnas fijas; un resultado vacío da una tabla vacía con esas columnas."""
    rows = payload.get("data") or []
    frame = pd.DataFrame(rows)
    for column in COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[COLUMNS].copy()


def kilos(frame: pd.DataFrame) -> pd.Series:
    """Kilos netos; cuando el reportero no declara peso neto se deja el faltante (no se estima)."""
    weight = pd.to_numeric(frame["netWgt"], errors="coerce")
    return weight.where(weight > 0)


def quota_wait_seconds(message: str) -> float:
    """Segundos que indica el mensaje de cuota agotada ('Quota will be replenished in 00:17:17'); 0 si no se puede leer."""
    match = re.search(r"(\d{1,2}):(\d{2}):(\d{2})", message)
    return int(match[1]) * 3600 + int(match[2]) * 60 + int(match[3]) if match else 0.0


class Client:
    def __init__(self, raw_dir: Path, pause: float = 3.5, retries: int = 6, client: httpx.Client | None = None, quota_margin: float = 5.0) -> None:
        self.raw_dir, self.pause, self.retries, self.quota_margin = raw_dir, pause, retries, quota_margin
        self.http = client or httpx.Client(timeout=60, headers={"User-Agent": "precios-agricolas-chile (research; non-commercial)"})

    def fetch(self, name: str, freq: str, params: dict[str, Any]) -> pd.DataFrame:
        """Descarga una consulta (con reintentos ante 429) y guarda el original con su manifiesto."""
        url = build_url(freq, params)
        cached = self.raw_dir / f"{name}.json"
        if cached.exists():  # reanudar una descarga interrumpida sin repetir consultas
            return parse_payload(json.loads(cached.read_text(encoding="utf-8")))
        for attempt in range(self.retries):
            response = self.http.get(url)
            if response.status_code == 429:
                time.sleep(self.pause * (attempt + 2))
                continue
            if response.status_code == 403 and "quota" in response.text.lower():
                time.sleep(quota_wait_seconds(response.text) + self.quota_margin)  # la cuota se repone sola; se espera y se reintenta
                continue
            response.raise_for_status()
            payload = response.json()
            self._save(name, url, response.content, payload)
            time.sleep(self.pause)
            return parse_payload(payload)
        raise RuntimeError(f"Comtrade siguió respondiendo 429 tras {self.retries} intentos: {url}")

    def _save(self, name: str, url: str, content: bytes, payload: dict[str, Any]) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        (self.raw_dir / f"{name}.json").write_bytes(content)
        manifest = {"name": name, "url": url, "captured_utc": datetime.now(UTC).isoformat(timespec="seconds"), "sha256": hashlib.sha256(content).hexdigest(),
                    "rows": len(payload.get("data") or []), "count": payload.get("count")}
        (self.raw_dir / f"{name}.manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def collect(client: Client, plan: list[dict[str, Any]]) -> pd.DataFrame:
    """Ejecuta un plan [{name, freq, params}] y une los resultados con una columna ``query`` para rastrear el origen."""
    frames = []
    for item in plan:
        frame = client.fetch(item["name"], item["freq"], item["params"])
        frame["query"] = item["name"]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=[*COLUMNS, "query"])
