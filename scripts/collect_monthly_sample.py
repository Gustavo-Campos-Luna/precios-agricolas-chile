"""Acquire two metadata-verified monthly candidates without inventing their schema.

Writes original query/JSON/manifests. Requested global catalog dates do not imply
that either product exists throughout that entire interval. No normalization or
conversion is attempted until the real annual-row response is inspected.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from materias_primas_chile.monthly import fetch_monthly_query
from materias_primas_chile.storage import write_json

# Exact identifiers discovered in the public metadata responses on 2026-10-28.
# Every run must verify them against its supplied probe before making a query.
TARGETS = (
    {"name": "poroto_tortola_minorista_1kg", "market_id": 7, "group_id": 12,
     "product_id": 370, "market_level": "retail", "expected_label": "Poroto Tórtola"},
    {"name": "maiz_amarillo_fob_argentino", "market_id": 5, "subsector_id": 1,
     "product_id": 315, "market_level": "international_reference", "expected_label": "Maíz Amarillo"},
)


def source_dates(probe: dict) -> tuple[str, str]:
    candidates = [request["response"] for request in probe["requests"]
                  if request["url"].split("?")[0].endswith("/min-max-date-precio")]
    if len(candidates) != 1:
        raise ValueError("Need one actual catalog date-range response")
    value = candidates[0]
    dates = [pd.to_datetime(value[key], format="%d/%m/%Y", errors="raise")
             for key in ("fechaInicio", "fechaTermino")]
    if dates[0] > dates[1]:
        raise ValueError("Invalid catalog date range")
    # Noon UTC stays on the same calendar date in mainland Chile and avoids a
    # midnight serialization falling into the previous month on the server.
    return tuple(date.strftime("%Y-%m-%dT12:00:00.000Z") for date in dates)


def source_ipc(probe: dict) -> dict:
    responses = [request["response"] for request in probe["requests"]
                 if request["url"].split("?")[0].endswith("/ipc")]
    if len(responses) != 1 or not isinstance(responses[0], list):
        raise ValueError("Need actual IPC catalog response for the observed form's idIPC field")
    candidates = []
    for item in responses[0]:
        if not isinstance(item, dict):
            continue
        # The published controller specifically reads ipc.valor, not ipc.id.
        value = str(item.get("valor", ""))
        if value.isdigit():
            candidates.append((int(value), item))
    if not candidates:
        raise ValueError("IPC metadata has no numeric valor; do not invent idIPC")
    value, record = max(candidates, key=lambda item: item[0])
    return {"idIPC": value, "observed_record": record,
            "selection": "largest numeric valor present in actual IPC metadata; query remains nominal"}


def verified_target(probe: dict, target: dict) -> dict:
    matches = []
    for item in probe["matches"]:
        if item.get("type") != "target_product" or str(item.get("market_id")) != str(target["market_id"]):
            continue
        container = "group_id" if "group_id" in target else "subsector_id"
        if str(item.get(container)) != str(target[container]):
            continue
        record = item["record"]
        if str(record.get("id")) != str(target["product_id"]):
            continue
        label = record.get("glosaFull", record.get("producto", record.get("glosa", "")))
        if target["expected_label"] not in label:
            raise ValueError(f"Observed product label changed for {target['name']}")
        matches.append(item)
    if len(matches) != 1:
        raise ValueError(f"Metadata must uniquely verify {target['name']}: found {len(matches)}")
    return matches[0]


def response_preview(document):
    if not isinstance(document, dict):
        return {"top_level_type": type(document).__name__, "first_item": document[0] if document else None}
    result = {"top_level_keys": list(document), "schema_status": "raw_response_not_normalized"}
    for key, value in document.items():
        if isinstance(value, list):
            result[key] = {"items": len(value), "first_item": value[0] if value else None}
        elif isinstance(value, (str, int, float, bool)) or value is None:
            result[key] = value
        else:
            result[key] = {"type": type(value).__name__, "keys": list(value) if isinstance(value, dict) else None}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", default="data/research/monthly_probe.json")
    parser.add_argument("--output", default="data/snapshots/monthly_candidates")
    args = parser.parse_args()
    probe = json.loads(Path(args.probe).read_text())
    start, end = source_dates(probe)
    ipc = source_ipc(probe)
    output = Path(args.output)
    report = {"catalog_requested_start": start, "catalog_requested_end": end, "ipc_form_metadata": ipc,
              "scope": "metadata-verified monthly queries; product-specific observed coverage pending parsing", "queries": []}
    for target in TARGETS:
        observed = verified_target(probe, target)
        form = {"periodoInicio": start, "periodoTermino": end, "tipoConsulta": "nominal",
                "idIPC": ipc["idIPC"], "tipoMercado": target["market_id"], "tipoSalida": "SA",
                "precioConIva": False, "subSector": target.get("group_id", target.get("subsector_id")),
                "producto": target["product_id"]}
        entry = {"target": target, "observed_metadata": observed, "form": form,
                 "requested_tax_flag": False, "geography_status": "not_inferred_from_application_name"}
        entry["attempts"] = []
        recent = dict(form)
        recent["periodoInicio"] = max(start, "2020-01-01T12:00:00.000Z")
        for label, query in (("full_catalog_range", form), ("recent_range_fallback", recent)):
            if label == "recent_range_fallback" and recent["periodoInicio"] == start:
                break
            attempt = {"range_label": label, "form": query}
            try:
                path = fetch_monthly_query(query, output)
                attempt.update(status="raw_response_acquired", path=str(path))
                entry["attempts"].append(attempt)
                entry.update(status="raw_response_acquired", path=str(path), successful_range_label=label,
                             response_preview=response_preview(json.loads(path.read_text())))
                break
            except (OSError, ValueError, RuntimeError) as exc:
                error = {"type": type(exc).__name__, "message": str(exc)}
                attempt.update(status="failed", error=error)
                entry["attempts"].append(attempt)
                entry.update(status="failed", error=error)
                if "HTTP 500" not in str(exc):
                    break
        report["queries"].append(entry)
        write_json(output / "collection_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if all(item["status"] == "failed" for item in report["queries"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
