"""GET públicos de metadatos ODEPA para investigar precios mensuales.

No consulta precios ni ejecuta POST. Los IDs se obtienen de respuestas reales;
no se prueban números supuestos, URLs .local, autenticación ni rutas internas.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import urlencode

from materias_primas_chile.prices import fetch
from materias_primas_chile.storage import atomic_write, receipt, write_json

BASE = "https://aplicativos.odepa.gob.cl/series-precios/results/"
CONTROLLER = "https://aplicativos.odepa.gob.cl/resource/js/apps/controller/series-precios/series-tiempo.js"


def plain(value):
    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()


def records(value):
    """Localiza listas de objetos; no interpreta su semántica por posición."""
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
    elif isinstance(value, dict):
        for item in value.values():
            if isinstance(item, (dict, list)):
                yield from records(item)


def object_id(item, *, entity):
    # Nombres esperables de campos del contrato, nunca valores inventados.
    names = {"market": ["id", "codigo", "tipoMercado", "tmeCod", "tmeId"],
             "subsector": ["id", "codigo", "subSector", "subsector", "sseCod", "sseId"]}[entity]
    for name in names:
        if name in item and isinstance(item[name], (str, int)):
            return item[name], name
    return None, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="data/research/monthly_probe.json")
    args = parser.parse_args()
    output = Path(args.output)
    raw_root = output.parent / "monthly_probe_raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    result = {"requests": [], "matches": [], "controller_contract_contexts": [],
              "scope": "public GET metadata only; no monthly prices downloaded"}

    def get(endpoint, params=None):
        url = BASE + endpoint + (("?" + urlencode(params)) if params else "")
        payload = fetch(url)
        path = raw_root / (endpoint + ("_" + str(len(result["requests"])) if params else "") + ".json")
        atomic_write(path, payload)
        receipt(path, url=url, source="ODEPA monthly public metadata")
        value = json.loads(payload)
        result["requests"].append({"url": url, "path": str(path), "response": value})
        return value

    try:
        markets = get("tipos-mercados")
        get("min-max-date-precio")
        payload = fetch(CONTROLLER)
        path = raw_root / "series-tiempo.js"
        atomic_write(path, payload)
        receipt(path, url=CONTROLLER, source="ODEPA application form contract")
        javascript = payload.decode("utf-8", errors="replace")
        for match in re.finditer(r"series.tiempo|form\.|tipoMercado|subSector|producto|fechaInicio|fechaTermino|exportExcel|\$http|serialize", javascript, re.I):
            result["controller_contract_contexts"].append(javascript[max(0, match.start()-180):match.end()+250])
        result["controller_contract_contexts"] = list(dict.fromkeys(result["controller_contract_contexts"]))
        for market in records(markets):
            if "productor" not in plain(json.dumps(market, ensure_ascii=False)):
                continue
            identifier, field = object_id(market, entity="market")
            result["matches"].append({"type": "producer_market", "record": market, "id_field": field})
            if identifier is None:
                continue
            sectors = get("sub-sectores-by-tipo-mercado", {"tipoMercado": identifier})
            for sector in records(sectors):
                if not any(term in plain(json.dumps(sector, ensure_ascii=False)) for term in ("cereal", "legumbr", "legumin")):
                    continue
                sub_id, sub_field = object_id(sector, entity="subsector")
                result["matches"].append({"type": "cereal_or_legume_subsector", "record": sector, "id_field": sub_field})
                if sub_id is None:
                    continue
                products = get("productos-by-sub-sector", {"subSector": sub_id, "tipoMercado": identifier})
                for product in records(products):
                    if any(term in plain(json.dumps(product, ensure_ascii=False)) for term in ("maiz", "poroto")):
                        result["matches"].append({"type": "target_product", "record": product})
    except Exception as exc:
        result["error"] = {"type": type(exc).__name__, "message": str(exc)}
        write_json(output, result)
        raise
    write_json(output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
