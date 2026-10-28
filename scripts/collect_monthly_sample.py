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
    return tuple(date.strftime("%Y-%m-%dT00:00:00.000Z") for date in dates)


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
    output = Path(args.output)
    report = {"catalog_requested_start": start, "catalog_requested_end": end,
              "scope": "metadata-verified monthly queries; product-specific observed coverage pending parsing", "queries": []}
    for target in TARGETS:
        observed = verified_target(probe, target)
        form = {"periodoInicio": start, "periodoTermino": end, "tipoConsulta": "nominal",
                "idIPC": None, "tipoMercado": target["market_id"], "tipoSalida": "SA",
                "precioConIva": False, "subSector": target.get("group_id", target.get("subsector_id")),
                "producto": target["product_id"]}
        entry = {"target": target, "observed_metadata": observed, "form": form,
                 "requested_tax_flag": False, "geography_status": "not_inferred_from_application_name"}
        try:
            path = fetch_monthly_query(form, output)
            entry.update(status="raw_response_acquired", path=str(path),
                         response_preview=response_preview(json.loads(path.read_text())))
        except (OSError, ValueError, RuntimeError) as exc:
            entry.update(status="failed", error={"type": type(exc).__name__, "message": str(exc)})
        report["queries"].append(entry)
        write_json(output / "collection_report.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if all(item["status"] == "failed" for item in report["queries"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
