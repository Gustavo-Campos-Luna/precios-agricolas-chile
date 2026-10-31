"""CLI reproducible: ingesta, consolidación, evaluación y escenarios."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata

import pandas as pd

from .storage import write_json


def _save(frame, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        frame.to_parquet(path, index=False)
    else:
        frame.to_csv(path, index=False)


def _load(path):
    return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path)


def run(args):
    from . import prices
    if args.command == "discover":
        resources = prices.discover_resources()
        write_json(args.output, resources)
        print(f"{len(resources)} recursos encontrados; catálogo: {args.output}")
    elif args.command == "ingest":
        resources = prices.discover_resources()
        selected = []
        for resource in resources:
            years = re.findall(r"\b(?:19|20)\d{2}\b", resource.get("name", "") + " " + resource.get("url", ""))
            if any(args.start_year <= int(year) <= args.end_year for year in years):
                selected.append(resource)
        if not selected:
            raise ValueError("No hay recursos para el rango solicitado; revisar catálogo")
        for resource in selected:
            if args.transport == "datastore":
                path = prices.download_datastore(resource, args.raw_root)
                frame = pd.DataFrame(json.loads(path.read_text()))
            else:
                try:
                    path = prices.download_resource(resource, args.raw_root)
                    frame = prices.read_csv(path)
                except (OSError, RuntimeError):
                    if args.transport != "auto":
                        raise
                    path = prices.download_datastore(resource, args.raw_root)
                    frame = pd.DataFrame(json.loads(path.read_text()))
            if args.products:
                def plain(value):
                    return unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
                product_columns = [col for col in frame if plain(col).strip() == "producto"]
                if len(product_columns) != 1:
                    raise ValueError("No se identifica columna Producto para filtro")
                wanted = [plain(product).strip() for product in args.products.split(",") if product.strip()]
                labels = frame[product_columns[0]].map(plain)
                keep = labels.map(lambda label: any(product in label for product in wanted))
                frame = frame.loc[keep].copy()
            clean = prices.normalize_prices(frame, source_resource_id=resource["id"])
            clean["source_snapshot_sha256"] = path.stem
            output = Path(args.output) / f"{resource['id']}_{path.stem[:12]}.csv"
            _save(clean, output)
            print(f"Normalizadas {len(clean)} observaciones: {output}")
    elif args.command == "build":
        from .build import build_streaming
        write_json(Path(args.output) / "build_status.json", {"status": "incomplete", "reason": "Build iniciado; solo success autoriza uso posterior"})
        summary = build_streaming(args.input, args.output)
        write_json(Path(args.output) / "build_status.json", {"status": "success", **summary})
        print(f"{summary['accepted_rows']} filas válidas; {summary['quarantine_rows']} en cuarentena")
    elif args.command == "series":
        from .odepa_series import OdepaSeriesClient, download_all, parse_series
        output = Path(args.output)
        markets = [int(m) for m in args.markets.split(",") if m.strip()] or None
        client = OdepaSeriesClient(args.raw_root, pace=args.pace)
        try:
            catalog = client.catalog(markets)
            # Un catálogo por corrida: evita que procesos paralelos se pisen el mismo archivo.
            _save(catalog, output / ("catalog_" + ("-".join(map(str, markets)) if markets else "all") + ".csv"))
            full = pd.concat([pd.read_csv(f) for f in sorted(output.glob("catalog*.csv"))] + [catalog])
            full = full.drop_duplicates(["market_type_id", "product_id"], keep="last").reset_index(drop=True)
            print(f"{len(catalog)} series en esta corrida; {len(full)} en el catálogo acumulado", flush=True)
            summary = download_all(client, catalog, output / "download_ledger.json", limit=args.limit)
        finally:
            client.close()
        entries = [e for e in full.to_dict("records") if client.path_for(e).exists()]
        if not entries:
            raise ValueError("No se descargó ninguna serie; revisar download_ledger.json")
        monthly = pd.concat([parse_series(client.path_for(e), e) for e in entries], ignore_index=True)
        _save(monthly, output / "monthly_series.csv")
        print(f"{len(monthly)} observaciones mensuales de {len(entries)} series; "
              f"{summary['failed']} fallos (ver download_ledger.json)")
    elif args.command == "bcch":
        from .bcch import BcchClient, BcchError, parse_series as parse_bcch
        output = Path(args.output)
        client = BcchClient(args.raw_root, pace=args.pace)
        failures = []
        try:
            selected = client.select_agricultural(client.catalog())
            _save(selected, output / "catalog_selected.csv")
            print(f"{len(selected)} series agrícolas seleccionadas", flush=True)
            entries = selected.to_dict("records")[:args.limit]
            for i, info in enumerate(entries, start=1):
                try:
                    client.fetch(info)
                except BcchError as exc:
                    failures.append({"series_id": info["seriesId"], "error": str(exc)})
                if i % 50 == 0:
                    print(f"[{i}/{len(entries)}] fallos={len(failures)}", flush=True)
        finally:
            client.close()
        write_json(output / "download_ledger.json", {"requested": len(entries), "failed": len(failures), "failures": failures})
        frames = [parse_bcch(client.path_for(e["seriesId"]), e) for e in entries if client.path_for(e["seriesId"]).exists()]
        if not frames:
            raise ValueError("No se descargó ninguna serie del Banco Central")
        long = pd.concat([f for f in frames if len(f)], ignore_index=True)
        _save(long, output / "series_long.csv")
        print(f"{len(long)} observaciones de {long.series_id.nunique()} series; {len(failures)} fallos")
    elif args.command == "cotrisa":
        import hashlib
        from .cotrisa import PRODUCTS, fetch_product, parse_tables
        frames = []
        for slug, product in PRODUCTS.items():
            path = fetch_product(slug, args.raw_root)
            html = path.read_bytes().decode("utf-8")
            frame = parse_tables(html, product, source_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            print(f"{product}: {len(frame)} observaciones" + (f" ({frame.date.min().date()} a {frame.date.max().date()})" if len(frame) else ""), flush=True)
            frames.append(frame)
        data = pd.concat([f for f in frames if len(f)], ignore_index=True)
        _save(data, Path(args.output) / "prices_long.csv")
        print(f"{len(data)} observaciones Cotrisa en total")
    elif args.command == "datasets":
        from .odepa_datasets import DATASETS, build_dataset
        keys = [k for k in args.keys.split(",") if k.strip()] or list(DATASETS)
        unknown = set(keys) - set(DATASETS)
        if unknown:
            raise ValueError(f"Datasets desconocidos: {sorted(unknown)}; válidos: {sorted(DATASETS)}")
        for key in keys:
            summary = build_dataset(key, args.raw_root, args.output)
            print(f"{key}: {summary['rows']} filas de {summary['files']} archivos -> {summary['output']}", flush=True)
    elif args.command == "faostat":
        from .faostat import build as build_faostat, build_production
        summary = build_faostat(args.raw_root, args.output)
        production = build_production(args.raw_root + "_production", args.output)
        print(f"Producción: {production['rows']} filas de {production['crops']} cultivos ({production['first_year']}-{production['last_year']}) -> {production['output']}")
        print(f"{summary['rows']} filas de {summary['items']} productos ({summary['first_year']}-{summary['last_year']}) -> {summary['output']}")
    elif args.command == "index":
        from .source_index import build_index
        index = build_index(".", args.output)
        print(index.groupby("source").agg(series=("product", "size"), obs=("n_obs", "sum")).to_string())
        print(f"-> {args.output}")
    elif args.command == "volume":
        from .volume import build as build_volume
        report = build_volume(args.curated)
        print(f"{report['rows_with_volume']} de {report['monthly_rows']} meses-serie con volumen; "
              f"{report['rows_with_kg_estimate']} con kilos estimados -> {report['output']}")
    elif args.command == "macro":
        from .bcch import build_macro
        print(json.dumps(build_macro(args.raw_root, args.output), indent=2, ensure_ascii=False))
    elif args.command == "pinksheet":
        from .pinksheet import build as build_pinksheet
        print(json.dumps(build_pinksheet(args.raw_root, args.output), indent=2, ensure_ascii=False))
    elif args.command == "panel":
        from .analysis import write_panel
        print(json.dumps(write_panel(args.curated, args.macro, args.output), indent=2, ensure_ascii=False))
    elif args.command == "supply":
        from .supply import write_orchards
        print(json.dumps(write_orchards(args.source, args.output), indent=2, ensure_ascii=False))
    elif args.command == "compact":
        from .compact import compact
        summary = compact(".", delete=args.delete)
        print(f"{summary['files']} archivos compactados; ahorro {summary['saved_mb']} MB; "
              f"originales borrados: {summary['deleted_originals']}")
    elif args.command == "reference":
        from .reference import write_reference
        print(json.dumps(write_reference(args.output, args.macro), indent=2, ensure_ascii=False))
    elif args.command in {"backtest", "forecast"}:
        from .forecast import backtest_monthly, forecast_monthly
        status_path = Path(args.input).parent / "build_status.json"
        if status_path.exists() and json.loads(status_path.read_text()).get("status") != "success":
            raise ValueError("Build incompleto: no se permite usar tablas anteriores; ejecutar build y revisar errores")
        frame = _load(args.input)
        climate_cols = args.climate_columns.split(",") if args.climate_columns else []
        if args.command == "backtest":
            predictions, metrics = backtest_monthly(frame, value_col=args.value_column, horizon=args.horizon, stride=args.stride, climate_cols=climate_cols)
            _save(predictions, Path(args.output) / "backtest_predictions.csv")
            _save(metrics, Path(args.output) / "backtest_metrics.csv")
            print(f"{len(predictions)} predicciones de evaluación; {len(metrics)} métricas")
        else:
            scenario = _load(args.scenario_csv) if args.scenario_csv else None
            output = forecast_monthly(frame, value_col=args.value_column, horizon=args.horizon, model=args.model, climate_cols=climate_cols, future_climate=scenario, scenario_name=args.scenario_name)
            _save(output, Path(args.output) / "forecast.csv")
            print(f"{len(output)} objetivos; {int(output.prediction.notna().sum())} estimaciones disponibles")
    elif args.command == "climate":
        from .climate import Location, aggregate_monthly, fetch_power
        locations = pd.read_csv(args.locations, dtype={"region_code": str})
        for row in locations.itertuples():
            location = Location(row.location_id, row.latitude, row.longitude, row.region_code)
            daily = fetch_power(location, args.start, args.end, raw_root=args.raw_root)
            _save(daily, Path(args.output) / f"{location.location_id}_daily.csv")
            _save(aggregate_monthly(daily), Path(args.output) / f"{location.location_id}_monthly.csv")
            print(f"Clima {location.location_id}: {len(daily)} días")
    elif args.command == "grains":
        from .grains import ingest_report
        data, rejected = ingest_report(args.raw_root)
        _save(data, Path(args.output) / "maiz_grano_week22_2025.csv")
        _save(rejected, Path(args.output) / "maiz_grano_week22_2025_rejected.csv")
        print(f"Maíz grano: {len(data)} referencias regionales/nacional; {len(rejected)} filas ambiguas")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    discover = commands.add_parser("discover", help="Descubrir catálogo oficial ODEPA")
    discover.add_argument("--output", default="artifacts/odepa_resources.json")
    ingest = commands.add_parser("ingest", help="Descargar y normalizar snapshots anuales")
    ingest.add_argument("--start-year", type=int, default=2015)
    ingest.add_argument("--end-year", type=int, default=2025)
    ingest.add_argument("--raw-root", default="data/raw")
    ingest.add_argument("--output", default="data/processed/prices")
    ingest.add_argument("--transport", choices=["auto", "csv", "datastore"], default="auto")
    ingest.add_argument("--products", default="", help="Subcadenas separadas por coma; vacío conserva todos")
    build = commands.add_parser("build", help="Consolidar precios comparables y cuarentena")
    build.add_argument("--input", default="data/processed/prices")
    build.add_argument("--output", default="data/curated/prices")
    for name in ("backtest", "forecast"):
        command = commands.add_parser(name)
        command.add_argument("--input", default="data/curated/prices/monthly.csv")
        command.add_argument("--output", default="artifacts/models")
        command.add_argument("--value-column", default="price")
        command.add_argument("--horizon", type=int, default=12)
        command.add_argument("--climate-columns", default="")
        if name == "backtest":
            command.add_argument("--stride", type=int, default=6)
        else:
            command.add_argument("--model", choices=["naive", "seasonal_naive", "ridge", "ridge_seasonal"], default="seasonal_naive")
            command.add_argument("--scenario-csv")
            command.add_argument("--scenario-name")
    climate = commands.add_parser("climate")
    climate.add_argument("--locations", default="config/locations.csv")
    climate.add_argument("--start", required=True)
    climate.add_argument("--end", required=True)
    climate.add_argument("--raw-root", default="data/raw/climate")
    climate.add_argument("--output", default="data/processed/climate")
    series = commands.add_parser("series", help="Descargar series mensuales ODEPA (1975 en adelante)")
    series.add_argument("--markets", default="", help="IDs de tipo de precio separados por coma; vacío descarga todos")
    series.add_argument("--raw-root", default="data/raw/odepa_series")
    series.add_argument("--output", default="data/processed/odepa_series")
    series.add_argument("--pace", type=float, default=2.0, help="Segundos mínimos entre solicitudes")
    series.add_argument("--limit", type=int, default=None, help="Máximo de series (pruebas)")
    bcch = commands.add_parser("bcch", help="Descargar series agrícolas del Banco Central (requiere .env)")
    bcch.add_argument("--raw-root", default="data/raw/bcch")
    bcch.add_argument("--output", default="data/processed/bcch")
    bcch.add_argument("--pace", type=float, default=0.4)
    bcch.add_argument("--limit", type=int, default=None)
    cotrisa = commands.add_parser("cotrisa", help="Precios internos de trigo, maíz, arroz y avena (Cotrisa)")
    cotrisa.add_argument("--raw-root", default="data/raw/cotrisa")
    cotrisa.add_argument("--output", default="data/processed/cotrisa")
    datasets = commands.add_parser("datasets", help="Consumidor, uva de vinificación y comercio exterior (CKAN ODEPA)")
    datasets.add_argument("--keys", default="", help="consumidor,uva_vinificacion,comex_exportacion,comex_importacion; vacío = todos")
    datasets.add_argument("--raw-root", default="data/raw")
    datasets.add_argument("--output", default="data/processed/odepa_datasets")
    faostat = commands.add_parser("faostat", help="Precios al productor FAOSTAT para Chile (HDX)")
    faostat.add_argument("--raw-root", default="data/raw/faostat")
    faostat.add_argument("--output", default="data/processed/faostat")
    index = commands.add_parser("index", help="Índice maestro de fuentes, productos, unidades y cobertura")
    index.add_argument("--output", default="data/curated/source_index.csv")
    volume = commands.add_parser("volume", help="Volumen mensual por serie (unidades comerciales y kilos estimados)")
    volume.add_argument("--curated", default="data/curated/prices")
    macro = commands.add_parser("macro", help="IPC encadenado y dólar mensual (Banco Central) para deflactar")
    macro.add_argument("--raw-root", default="data/raw/bcch")
    macro.add_argument("--output", default="data/processed/bcch")
    pinksheet = commands.add_parser("pinksheet", help="Precios internacionales mensuales del Banco Mundial (insumos, cereales)")
    pinksheet.add_argument("--raw-root", default="data/raw/pinksheet")
    pinksheet.add_argument("--output", default="data/processed/pinksheet")
    panel = commands.add_parser("panel", help="Panel mensual con variedad armonizada, kilos, precio real y USD")
    panel.add_argument("--curated", default="data/curated/prices")
    panel.add_argument("--macro", default="data/processed/bcch")
    panel.add_argument("--output", default="data/analysis")
    supply = commands.add_parser("supply", help="Superficie plantada por especie y variedad (catastro frutícola)")
    supply.add_argument("--source", default="data/processed/odepa_datasets/catastro_fruticola.csv")
    supply.add_argument("--output", default="data/analysis")
    compact = commands.add_parser("compact", help="Convierte CSV grandes a Parquet/gzip, verificando antes de borrar")
    compact.add_argument("--delete", action="store_true", help="Borra cada CSV solo después de verificar su versión compacta")
    reference = commands.add_parser("reference", help="Consumidor mensual, exportación ponderada y series externas (reales)")
    reference.add_argument("--output", default="data/analysis")
    reference.add_argument("--macro", default="data/processed/bcch")
    grains = commands.add_parser("grains", help="Extraer informe productor maíz grano, semana22 de2025")
    grains.add_argument("--raw-root", default="data/raw")
    grains.add_argument("--output", default="data/processed/grains")
    args = parser.parse_args(argv)
    if args.command == "ingest" and args.start_year > args.end_year:
        parser.error("start-year debe ser <= end-year")
    try:
        run(args)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
