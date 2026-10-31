"""Conservative unit enrichment from explicit ODEPA commercial labels.

Never replaces the quoted price, commercial unit or series identity. A known
package weight allows CLP/kg comparison; it does not authorize pooling series.
"""
from __future__ import annotations

import math
import re
import unicodedata

import pandas as pd

_PREFIX = r"(?:(?:\$|clp)\s*/\s*)?"
_KG = r"(?:kg|kilos?|kilogramos?)"
_PACKAGE = r"(?:bandejas?|cajas?|sacos?|mallas?|bins?|cunas?|envases?)"
_NUMBER = r"(?:\d+(?:[.,]\d+)?)"
_PACK_STYLE = r"(?:\s+(?:a\s+granel|granel|empedradas?|embaladas?))?"
_WEIGHT = rf"{_PACKAGE}\s+(?:de\s+)?(?P<weight>{_NUMBER})\s*{_KG}{_PACK_STYLE}"
_PER_KG = re.compile(rf"{_PREFIX}{_KG}")
_PER_KG_PACKAGED = re.compile(rf"{_PREFIX}{_KG}\s*\(\s*en\s+{_WEIGHT}\s*\)")
_PER_PACKAGE_WEIGHT = re.compile(rf"{_PREFIX}{_WEIGHT}")
_PER_PACKAGE_PAREN = re.compile(rf"{_PREFIX}{_PACKAGE}\s*\(\s*(?P<weight>{_NUMBER})\s*{_KG}\s*\)")
_PER_PACKAGE_COUNT = re.compile(rf"{_PREFIX}{_PACKAGE}\s+(?:de\s+)?(?P<count>\d+)\s+unidades?")
_PER_UNIT = re.compile(rf"{_PREFIX}unidad")
_PER_HUNDRED = re.compile(rf"{_PREFIX}cien")


def _normalize(value: object) -> str:
    if pd.isna(value):
        return ""
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return " ".join(text.lower().split())


def _explicit_weight(text: str) -> float | None:
    # E.g. 1.000 / 1,000 can mean one or a thousand; do not guess a locale.
    if re.fullmatch(r"[1-9]\d{0,2}[.,]\d{3}", text):
        return None
    weight = float(text.replace(",", "."))
    return weight if math.isfinite(weight) and weight > 0 else None


def _label_details(label: str) -> tuple[str, float | None, int | None]:
    """Full-match only; descriptions with multiple or ranged bases are unknown."""
    if _PER_KG.fullmatch(label):
        return "already_per_kg", None, None
    packaged_kg = _PER_KG_PACKAGED.fullmatch(label)
    if packaged_kg:
        weight = _explicit_weight(packaged_kg["weight"])
        if weight is not None:
            return "already_per_kg", weight, None
        return "unsupported_unit", None, None
    weighted = _PER_PACKAGE_WEIGHT.fullmatch(label) or _PER_PACKAGE_PAREN.fullmatch(label)
    if weighted:
        weight = _explicit_weight(weighted["weight"])
        if weight is not None:
            return "explicit_package_weight_kg", weight, None
        return "unsupported_unit", None, None
    counted = _PER_PACKAGE_COUNT.fullmatch(label)
    if counted and int(counted["count"]) > 0:
        return "explicit_unit_count", None, int(counted["count"])
    if _PER_UNIT.fullmatch(label):
        return "already_per_unit", None, 1
    if _PER_HUNDRED.fullmatch(label):
        return "explicit_unit_count", None, 100
    return "unsupported_unit", None, None


def enrich_units(frame: pd.DataFrame) -> pd.DataFrame:
    """Add explicit CLP/kg and CLP/item conversions without changing originals.

    Required columns: ``price``, ``unit``, ``currency``. Only finite positive
    CLP prices are converted. Known package weights are metadata even when the
    currency is unsupported. Counts are items, never inferred kilograms.
    ``commercial_weight_kg`` can describe packaging around a per-kg quote and
    therefore is not necessarily the denominator of the quoted price.
    """
    missing = {"price", "unit", "currency"} - set(frame.columns)
    if missing:
        raise ValueError(f"Missing columns for unit enrichment: {sorted(missing)}")
    output = frame.copy()
    converted_kg, package_weights, methods, converted_units = [], [], [], []
    for price, unit, currency in zip(frame["price"], frame["unit"], frame["currency"]):
        method, weight, count = _label_details(_normalize(unit))
        kg_price = item_price = float("nan")
        package_weights.append(float(weight) if weight is not None else float("nan"))
        if _normalize(currency) != "clp":
            method = "unsupported_currency"
        else:
            numeric = pd.to_numeric(price, errors="coerce")
            if pd.isna(numeric) or not math.isfinite(float(numeric)) or numeric <= 0:
                method = "invalid_price"
            elif method == "already_per_kg":
                kg_price = float(numeric)
            elif method == "explicit_package_weight_kg":
                kg_price = float(numeric) / weight
            elif method in {"already_per_unit", "explicit_unit_count"}:
                item_price = float(numeric) / count
        converted_kg.append(kg_price)
        converted_units.append(item_price)
        methods.append(method)
    output["price_clp_kg"] = pd.Series(converted_kg, index=frame.index, dtype=float)
    output["commercial_weight_kg"] = pd.Series(package_weights, index=frame.index, dtype=float)
    output["unit_conversion_method"] = pd.Series(methods, index=frame.index, dtype="string")
    output["price_clp_unit"] = pd.Series(converted_units, index=frame.index, dtype=float)
    return output
