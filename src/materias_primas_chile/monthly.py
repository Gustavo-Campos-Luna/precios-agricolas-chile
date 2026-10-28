"""Public read-only monthly ODEPA query transport, separate from normalization.

The endpoint and form keys are observed in ODEPA's published AngularJS service
and controller. Callers must obtain product/market/subsector identifiers from
live metadata. This transport stores the actual JSON response; it does not
assume that monthly values have the wholesale-daily schema or national scope.
"""
from __future__ import annotations

import hashlib
import gzip
import json
import zlib
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .storage import atomic_write, receipt, write_json

ENDPOINT = "https://aplicativos.odepa.gob.cl/series-precios/results/series-tiempo"
REQUIRED = {"periodoInicio", "periodoTermino", "tipoConsulta", "idIPC", "tipoMercado",
            "tipoSalida", "precioConIva", "subSector", "producto"}


def _response_metadata(response):
    headers = getattr(response, "headers", None)
    charset = headers.get_content_charset() if headers is not None else None
    charset = charset if isinstance(charset, str) and charset else "utf-8"
    def header(name):
        value = headers.get(name, "") if headers is not None else ""
        return value if isinstance(value, str) else ""
    final_url = response.geturl()
    status = response.getcode()
    return {"declared_charset": charset, "content_encoding": header("Content-Encoding"),
            "content_type": header("Content-Type"),
            "final_url": final_url if isinstance(final_url, str) else ENDPOINT,
            "http_status": status if isinstance(status, int) else None}


def _decode_response(payload, metadata):
    encoding = metadata["content_encoding"].strip().lower()
    if encoding == "gzip":
        body = gzip.decompress(payload)
    elif encoding in ("", "identity"):
        body = payload
    else:
        raise ValueError(f"Unsupported declared content encoding: {encoding}")
    return body.decode(metadata["declared_charset"])


def _preserve_failure(payload, metadata, form, raw_root, query_hash, reason):
    directory = Path(raw_root) / "odepa_monthly" / "failures" / query_hash
    digest = hashlib.sha256(payload).hexdigest()
    original = directory / f"{digest}.response.bin"
    atomic_write(original, payload)
    write_json(directory / "query.json", form)
    try:
        preview = _decode_response(payload, metadata)
    except (ValueError, OSError, UnicodeError, LookupError, EOFError, zlib.error):
        # Diagnostic replacement decoding is never used to parse prices.
        preview = payload.decode("utf-8", errors="replace")
    atomic_write(directory / f"{digest}.preview.txt", preview[:2000].encode("utf-8"))
    receipt(original, url=ENDPOINT, source="ODEPA monthly lookup diagnostic", method="POST",
            request_sha256=query_hash, status="failed_not_normalized", reason=reason, **metadata)
    return original


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
            metadata = _response_metadata(response)
    except HTTPError as exc:
        metadata = _response_metadata(exc)
        path = _preserve_failure(exc.read(), metadata, form, raw_root, query_hash, f"HTTP {exc.code}")
        raise RuntimeError(f"ODEPA monthly price lookup returned HTTP {exc.code}; diagnostic: {path}") from exc
    try:
        decoded = _decode_response(payload, metadata)
        document = json.loads(decoded)
    except (ValueError, OSError, UnicodeError, LookupError, EOFError, zlib.error) as exc:
        path = _preserve_failure(payload, metadata, form, raw_root, query_hash, str(exc))
        raise ValueError(f"ODEPA monthly lookup did not return valid declared-charset JSON; diagnostic: {path}") from exc
    if not isinstance(document, (dict, list)) or not document:
        path = _preserve_failure(payload, metadata, form, raw_root, query_hash, "empty or unexpected JSON")
        raise ValueError(f"ODEPA monthly lookup returned empty or unexpected JSON; diagnostic: {path}")
    directory = Path(raw_root) / "odepa_monthly" / query_hash
    original_digest = hashlib.sha256(payload).hexdigest()
    original_path = directory / f"{original_digest}.response.bin"
    atomic_write(original_path, payload)
    receipt(original_path, url=ENDPOINT, source="ODEPA monthly original HTTP response",
            method="POST", request_sha256=query_hash, **metadata)
    utf8_payload = decoded.encode("utf-8")
    digest = hashlib.sha256(utf8_payload).hexdigest()
    path = directory / f"{digest}.json"
    atomic_write(path, utf8_payload)
    write_json(directory / "query.json", form)
    receipt(path, url=ENDPOINT, source="ODEPA monthly price lookup", method="POST",
            request_sha256=query_hash, market_id=form["tipoMercado"],
            product_id=form["producto"], subsector_id=form["subSector"],
            price_basis="nominal", requested_tax_flag=form["precioConIva"],
            tax_basis_status="must_be_validated_from_source_response_and_market_contract",
            original_response_path=str(original_path), original_response_sha256=original_digest,
            output_encoding="utf-8", **metadata,
            status="raw_response_requires_schema_validation")
    return path
