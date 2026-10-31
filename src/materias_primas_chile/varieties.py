"""Armoniza nombres de variedad entre fuentes (mayorista, consumidor, catastro, exportaciones).

Tres niveles, de menos a más agresivo, para no fusionar lo que no se pueda justificar:
- ``variety_key``: minúsculas, sin tildes, sin paréntesis, sin espacios ni signos ("Red Globe" == "Redglobe").
- ``variety_canonical``: aplica alias explícitos (errores de tipeo y sinónimos) de ``config/variety_aliases.csv``.
- ``variety_group``: agrupa clones de una misma familia (Gala, Fuji, Red Delicious...). Es una decisión
  hortícola explícita y revisable; el análisis puede usar canonical (fino) o group (agregado).
"No especificado" y variantes quedan con clave vacía: nunca se agrupan como si fueran una variedad.
"""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

import pandas as pd

UNSPECIFIED = {"", "sinespecificar", "sininformacion", "sinespecificado", "nan", "none"}


def variety_key(raw: object) -> str:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return ""
    text = unicodedata.normalize("NFKD", str(raw)).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\(.*?\)", " ", text)
    key = re.sub(r"[^a-z0-9]+", "", text)
    return "" if key in UNSPECIFIED else key


class Aliases:
    def __init__(self, table: pd.DataFrame):
        required = {"policy", "match", "pattern", "target"}
        if not required <= set(table.columns):
            raise ValueError(f"variety_aliases.csv debe tener {sorted(required)}")
        exact = table[table.match.eq("exact") & table.pattern.ne(table.target)]
        self.canonical = dict(zip(exact.pattern, exact.target))
        families = table[table.policy.eq("family") & table.match.eq("regex")]
        self.families = [(re.compile(row.pattern), row.target) for row in families.itertuples()]

    def canonical_of(self, key: str) -> str:
        return self.canonical.get(key, key)

    def group_of(self, canonical: str) -> str:
        if not canonical:
            return ""
        for pattern, target in self.families:
            if pattern.search(canonical):
                return target
        return canonical


def load_aliases(path: str | Path = "config/variety_aliases.csv") -> Aliases:
    return Aliases(pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8"))


def harmonize(frame: pd.DataFrame, column: str = "variety", aliases: Aliases | None = None) -> pd.DataFrame:
    """Agrega variety_key, variety_canonical y variety_group sin tocar la columna original."""
    aliases = aliases or load_aliases()
    out = frame.copy()
    unique = pd.Series(out[column].unique())
    keys = unique.map(variety_key)
    canonical = keys.map(aliases.canonical_of)
    mapping = pd.DataFrame({"raw": unique, "variety_key": keys, "variety_canonical": canonical,
                            "variety_group": canonical.map(aliases.group_of)})
    merged = out[[column]].merge(mapping, left_on=column, right_on="raw", how="left")
    for name in ("variety_key", "variety_canonical", "variety_group"):
        out[name] = merged[name].to_numpy()
    return out


def load_species_map(path: str | Path = "config/species_product_map.csv") -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
