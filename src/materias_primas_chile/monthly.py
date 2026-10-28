"""Public read-only monthly ODEPA query transport, separate from normalization.

The endpoint and form keys are observed in ODEPA's published AngularJS service
and controller. Callers must obtain product/market/subsector identifiers from
live metadata. This transport stores the actual JSON response; it does not
assume that monthly values have the wholesale-daily schema or national scope.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .storage import atomic_write, receipt, write_json

ENDPOINT = "https://aplicativos.odepa.gob.cl/series-precios/results/series-tiempo"
REQUIRED = {"periodoInicio", "periodoTermino", "tipoConsulta", "idIPC", "tipoMercado",
            "tipoSalida", "precioConIva", "subSector", "producto"}


def fetch_monthly_query(form: dict, raw_root: str | Path, *, timeout: float = 90) -> Path:
    """POST a public price lookup and preserve both query and response.

    Only nominal annual output is supported in this initial transport. Tax basis
    remains explicit. JSON dates must be copied from the inspected form contract;
    no product identifiers, weight units or date coverage are inferred here.
    No authenticated requests, identity/IP fields or credentials are accepted.
    """
    missing, extra = REQUIRED - set(form), set(form) - REQUIRED
    if missing or extra:
        raise ValueError(f"Monthly query contract mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    if form["tipoConsulta"] != "nominal" or form["tipoSalida"] != "SA":
        raise ValueError("Only nominal annual monthly-series queries are supported")
    if not isinstance(form["precioConIva"], bool):
        raise ValueError("precioConIva must be an explicit boolean")
    for key in ("tipoMercado", "subSector", "producto"):
        value = form[key]
        if isinstance(value, bool) or not isinstance(value, (str, int)) or str(value).strip() == "":
            raise ValueError(f"Explicit metadata-derived identifier required: {key}")
    for key in ("periodoInicio", "periodoTermino"):
        if not isinstance(form[key], str) or not form[key].strip():
            raise ValueError(f"Explicit serialized form date required: {key}")
    request_bytes = json.dumps(form, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()
    query_hash = hashlib.sha256(request_bytes).hexdigest()
    request = Request(ENDPOINT, data=request_bytes, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "User-Agent": "MateriasPrimasChile/0.1 official monthly price research",
    })
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        raise RuntimeError(f"ODEPA monthly price lookup returned HTTP {exc.code}") from exc
    try:
        document = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("ODEPA monthly lookup did not return valid JSON") from exc
    if not isinstance(document, (dict, list)) or not document:
        raise ValueError("ODEPA monthly lookup returned empty or unexpected JSON")
    digest = hashlib.sha256(payload).hexdigest()
    directory = Path(raw_root) / "odepa_monthly" / query_hash
    path = directory / f"{digest}.json"
    atomic_write(path, payload)
    write_json(directory / "query.json", form)
    receipt(path, url=ENDPOINT, source="ODEPA monthly price lookup", method="POST",
            request_sha256=query_hash, market_id=form["tipoMercado"],
            product_id=form["producto"], subsector_id=form["subSector"],
            price_basis="nominal", requested_tax_flag=form["precioConIva"],
            tax_basis_status="must_be_validated_from_source_response_and_market_contract",
            status="raw_response_requires_schema_validation")
    return path
