"""Cliente de la API Siete del Banco Central de Chile para series agrícolas.

Las credenciales se leen de variables de entorno BCCH_USER / BCCH_PASSWORD o de un
archivo ``.env`` (ignorado por git). Nunca se escriben en manifiestos, URLs guardadas
ni mensajes de error. Las series de este banco son sobre todo ÍNDICES, valores de
exportación (USD) o variaciones; solo algunas son precios en pesos. Cada fila conserva
el título, la frecuencia y el tipo para no mezclarlas con los precios ODEPA.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

import httpx
import pandas as pd

from .storage import atomic_write, receipt

BASE = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
FREQUENCIES = ["MONTHLY", "QUARTERLY", "ANNUAL"]
KEYWORDS = re.compile(
    r"trigo|ma[ií]z|cereza|\buvas?\b|poroto|frijol|arroz|avena|cebada|lenteja|garbanzo|\bpapas?\b|cereal|"
    r"vino|leche|harina|\bpan\b|fruta|hortaliza|verdura|legumbre|az[uú]car|duraznos|carozos|agropecuari|"
    r"agr[ií]cola", re.I)
# Familias de interés (prefijo del código). Se excluyen cuentas nacionales (PIB, inversión, etc.).
FAMILIES = ("F076.IPM", "F075.IPP", "F068.U23", "F068.B1", "F068.U1", "F074.IPC", "F074.IPCFV",
            "F019.PPBA", "F034", "F061")


def load_credentials(env_path: str | Path = ".env") -> tuple[str, str]:
    user, password = os.environ.get("BCCH_USER"), os.environ.get("BCCH_PASSWORD")
    path = Path(env_path)
    if (not user or not password) and path.exists():
        values = dict(line.rstrip("\r\n").split("=", 1) for line in path.read_text(encoding="utf-8").splitlines()
                      if "=" in line and not line.lstrip().startswith("#"))
        user, password = user or values.get("BCCH_USER"), password or values.get("BCCH_PASSWORD")
    if not user or not password:
        raise ValueError("Faltan BCCH_USER y BCCH_PASSWORD (variables de entorno o archivo .env)")
    return user, password


class BcchError(RuntimeError):
    pass


class BcchClient:
    def __init__(self, raw_root: str | Path = "data/raw/bcch", *, pace: float = 0.4, timeout: float = 90,
                 env_path: str | Path = ".env"):
        self._user, self._password = load_credentials(env_path)
        self.raw_root = Path(raw_root)
        self.pace = pace
        self._client = httpx.Client(timeout=timeout)
        self._last = 0.0

    def close(self) -> None:
        self._client.close()

    def _call(self, attempts: int = 4, **params) -> dict:
        query = {"user": self._user, "pass": self._password, **params}
        last = "sin respuesta"
        for attempt in range(attempts):
            delay = self.pace - (time.monotonic() - self._last)
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()
            try:
                response = self._client.get(BASE, params=query)
                if response.status_code == 200:
                    document = json.loads(response.content.decode("latin-1"))
                    if document.get("Codigo") == 0:
                        return document
                    last = f"Codigo {document.get('Codigo')}: {document.get('Descripcion')}"
                    if document.get("Codigo") in (-1, -2, -3):  # credenciales o parámetros: no tiene sentido reintentar
                        break
                else:
                    last = f"HTTP {response.status_code}"
            except (httpx.HTTPError, ValueError) as exc:
                last = type(exc).__name__  # sin str(exc): podría incluir la URL con la contraseña
            time.sleep(min(30, 3 * 2 ** attempt))
        raise BcchError(f"{params.get('function')} {params.get('timeseries', '')} falló: {last}")

    def catalog(self) -> pd.DataFrame:
        rows = []
        for frequency in FREQUENCIES:
            for info in self._call(function="SearchSeries", frequency=frequency).get("SeriesInfos") or []:
                rows.append({**info, "frequency": frequency})
        return pd.DataFrame(rows).drop_duplicates("seriesId")

    @staticmethod
    def select_agricultural(catalog: pd.DataFrame) -> pd.DataFrame:
        title = catalog["spanishTitle"].fillna("")
        in_family = catalog["seriesId"].str.startswith(FAMILIES)
        return catalog[in_family & title.str.contains(KEYWORDS)].reset_index(drop=True)

    def path_for(self, series_id: str) -> Path:
        return self.raw_root / f"{series_id}.json"

    def fetch(self, info: dict, *, force: bool = False) -> Path:
        path = self.path_for(info["seriesId"])
        if path.exists() and not force:
            return path
        first = pd.to_datetime(info["firstObservation"], format="%d-%m-%Y").strftime("%Y-%m-%d")
        last = pd.to_datetime(info["lastObservation"], format="%d-%m-%Y").strftime("%Y-%m-%d")
        document = self._call(function="GetSeries", timeseries=info["seriesId"], firstdate=first, lastdate=last)
        payload = json.dumps(document, ensure_ascii=False).encode("utf-8")
        atomic_write(path, payload)
        receipt(path, url=BASE, source="Banco Central de Chile API Siete", method="GET",
                series_id=info["seriesId"], title=info["spanishTitle"], frequency=info["frequency"],
                query={"function": "GetSeries", "timeseries": info["seriesId"], "firstdate": first, "lastdate": last})
        return path


def parse_series(path: str | Path, info: dict) -> pd.DataFrame:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    observations = (document.get("Series") or {}).get("Obs") or []
    frame = pd.DataFrame(observations)
    if frame.empty:
        return pd.DataFrame(columns=["date", "value", "series_id", "title", "frequency", "status"])
    frame = frame.rename(columns={"indexDateString": "date", "statusCode": "status"})
    frame["date"] = pd.to_datetime(frame["date"], format="%d-%m-%Y", errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna(subset=["date", "value"])  # nunca se rellena con ceros
    frame["series_id"] = info["seriesId"]
    frame["title"] = info["spanishTitle"]
    frame["frequency"] = info["frequency"]
    frame["source"] = "Banco Central de Chile (Siete)"
    frame["source_sha256"] = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    return frame[["date", "value", "series_id", "title", "frequency", "status", "source", "source_sha256"]]


# --- Macro: IPC y dólar para deflactar y convertir precios -----------------------------
MACRO_SERIES = {
    "cpi_mom_pct": "F074.IPC.VAR.Z.Z.C.M",     # IPC general histórico, variación mensual % (1928–)
    "cpi_base_2023": "F074.IPC.IND.Z.2023.C.M",   # IPC general por base oficial; se empalman por sus traslapes
    "cpi_base_2018": "F074.IPC.IND.Z.2018.C.M",
    "cpi_base_2013": "F074.IPC.IND.Z.2013.C.M",
    "cpi_base_2009": "F074.IPC.IND.Z.2009.C.M",
    "cpi_base_2008": "F074.IPC.IND.Z.200812.C.M",
    "usd_clp_daily": "F073.TCO.PRE.Z.D",         # dólar observado, CLP por USD (1982–)
}


def fetch_ids(client: BcchClient, ids: dict[str, str], first: str = "1900-01-01", last: str | None = None) -> dict:
    """Descarga series por código (sin pasar por el catálogo) y las guarda con manifiesto."""
    last = last or pd.Timestamp.today().strftime("%Y-%m-%d")
    paths = {}
    for name, series_id in ids.items():
        path = client.path_for(series_id)
        if not path.exists():
            document = client._call(function="GetSeries", timeseries=series_id, firstdate=first, lastdate=last)
            atomic_write(path, json.dumps(document, ensure_ascii=False).encode("utf-8"))
            receipt(path, url=BASE, source="Banco Central de Chile API Siete", method="GET", series_id=series_id,
                    query={"function": "GetSeries", "timeseries": series_id, "firstdate": first, "lastdate": last})
        paths[name] = path
    return paths


def _month_number(dates: pd.Series) -> pd.Series:
    return dates.dt.year * 12 + dates.dt.month


def chain_cpi(monthly_pct: pd.DataFrame) -> pd.DataFrame:
    """Índice encadenado desde variaciones mensuales; base: último mes = 100.

    Solo sirve como control: las variaciones publicadas vienen redondeadas a 0,1 % y el
    error se acumula. Exige meses consecutivos: un hueco rompería la cadena.
    """
    data = monthly_pct.sort_values("date")[["date", "value"]].reset_index(drop=True)
    numbers = _month_number(data["date"])
    if (numbers.diff().dropna() != 1).any():
        raise ValueError("La variación mensual del IPC tiene meses faltantes; no se puede encadenar")
    level = (1 + data["value"] / 100).cumprod()
    data["cpi_index"] = 100 * level / level.iloc[-1]
    data["base_month"] = data["date"].iloc[-1].strftime("%Y-%m")
    return data.rename(columns={"value": "cpi_mom_pct"})


def splice_cpi(bases: list[pd.DataFrame]) -> pd.DataFrame:
    """Empalma índices oficiales de bases distintas usando sus meses de traslape.

    ``bases`` va de la base más reciente a la más antigua. Cada base antigua se reescala con el
    cuociente medio de los meses en que coincide con lo ya empalmado; luego aporta solo los
    meses anteriores. Si no hay traslape no se empalma (error). Base final: último mes = 100.
    """
    spliced = bases[0].set_index("date")["value"].astype(float)
    for older in bases[1:]:
        old = older.set_index("date")["value"].astype(float)
        overlap = spliced.index.intersection(old.index)
        if len(overlap) < 3:
            raise ValueError(f"Sin traslape suficiente para empalmar IPC ({len(overlap)} meses)")
        scale = float((spliced.loc[overlap] / old.loc[overlap]).mean())
        spliced = pd.concat([old.loc[old.index < spliced.index.min()] * scale, spliced]).sort_index()
    numbers = _month_number(spliced.index.to_series())
    if (numbers.diff().dropna() != 1).any():
        raise ValueError("El IPC empalmado tiene meses faltantes")
    out = (100 * spliced / spliced.iloc[-1]).rename("cpi_index").reset_index()
    out["base_month"] = out["date"].iloc[-1].strftime("%Y-%m")
    return out


def monthly_mean(daily: pd.DataFrame) -> pd.DataFrame:
    data = daily.assign(date=daily["date"].dt.to_period("M").dt.to_timestamp())
    out = data.groupby("date", as_index=False).agg(usd_clp=("value", "mean"), n_days=("value", "size"))
    return out


def build_macro(raw_root: str | Path = "data/raw/bcch", output: str | Path = "data/processed/bcch") -> dict:
    client = BcchClient(raw_root)
    try:
        paths = fetch_ids(client, MACRO_SERIES)
    finally:
        client.close()
    frames = {}
    for name, series_id in MACRO_SERIES.items():
        info = {"seriesId": series_id, "spanishTitle": name, "frequency": "macro"}
        frames[name] = parse_series(paths[name], info)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    bases = [frames[f"cpi_base_{b}"] for b in ("2023", "2018", "2013", "2009", "2008")]
    cpi = splice_cpi(bases)
    chained = chain_cpi(frames["cpi_mom_pct"]).set_index("date")["cpi_index"]
    both = pd.concat([cpi.set_index("date")["cpi_index"], chained], axis=1, keys=["spliced", "chained"]).dropna()
    ratio = both["spliced"] / both["chained"]
    drift = float(ratio.max() / ratio.min() - 1)  # diferencia entre el empalme oficial y el encadenado redondeado
    cpi.to_csv(output / "cpi_index.csv", index=False)
    usd = monthly_mean(frames["usd_clp_daily"])
    usd.to_csv(output / "usd_clp_monthly.csv", index=False)
    summary = {"cpi_months": len(cpi), "cpi_first": str(cpi.date.min().date()), "cpi_last": str(cpi.date.max().date()),
               "cpi_base_month": cpi.base_month.iloc[0], "cpi_vs_rounded_chain_max_spread": round(drift, 6),
               "usd_months": len(usd), "usd_first": str(usd.date.min().date()), "usd_last": str(usd.date.max().date())}
    (output / "macro_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
