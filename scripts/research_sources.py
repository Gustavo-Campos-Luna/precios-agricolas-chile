"""Inspección reproducible del catálogo ODEPA sin descargar CSV completos."""
import json
from materias_primas_chile.prices import discover_resources

if __name__ == "__main__":
    print(json.dumps(discover_resources(), ensure_ascii=False, indent=2))
