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
        from .quality import monthly_panel, profile
        write_json(Path(args.output) / "build_status.json", {"status": "incomplete", "reason": "Build iniciado; solo success autoriza uso posterior"})
        paths = sorted(Path(args.input).glob("*.csv"))
        if not paths:
            raise ValueError("No hay snapshots normalizados: ejecutar ingest primero")
        data = pd.concat([_load(path) for path in paths], ignore_index=True)
        if {"source_resource_id", "source_snapshot_sha256"}.issubset(data):
            revisions = data.groupby("source_resource_id").source_snapshot_sha256.nunique()
            if revisions.gt(1).any():
                raise ValueError("Revisiones múltiples de un mismo recurso: seleccionar un snapshot por recurso en un directorio --input separado")
        data["date"] = pd.to_datetime(data.date, errors="coerce")
        data["price"] = pd.to_numeric(data.price, errors="coerce")
        # Same snapshot ingested twice is an operational duplication, safely identified.
        if "source_snapshot_sha256" in data and "source_record" in data:
            data = data.drop_duplicates(["source_snapshot_sha256", "source_record"])
        keys = ["series_id", "date"]
        reasons = pd.Series("", index=data.index)
        invalid = data.date.isna() | data.series_id.isna() | ~data.price.between(0, float("inf"), inclusive="neither")
        reasons.loc[invalid] += "invalid_date_key_or_price;"
        for column in ["product", "market", "unit", "market_region_code"]:
            if column in data:
                bad = data[column].isna() | data[column].astype(str).str.strip().eq("")
                reasons.loc[bad] += f"missing_{column};"
        for column, is_lower in [("price_min", True), ("price_max", False)]:
            if column in data:
                bounds = pd.to_numeric(data[column], errors="coerce")
                bad = bounds.notna() & (data.price.lt(bounds) if is_lower else data.price.gt(bounds))
                reasons.loc[bad] += "price_outside_source_bounds;"
        duplicate = data.duplicated(keys, keep=False)
        reasons.loc[duplicate] += "ambiguous_series_date;"
        reject = reasons.ne("")
        quarantined = data.loc[reject].copy()
        quarantined["rejection_reason"] = reasons.loc[reject]
        accepted = data.loc[~reject].copy()
        _save(quarantined, Path(args.output) / "quarantine.csv")
        quality = profile(accepted, keys=keys)
        quality.update(input_rows=len(data), quarantine_rows=len(quarantined))
        write_json(Path(args.output) / "quality.json", quality)
        if not quality["passed"]:
            raise ValueError("Sin observaciones válidas; revisar quality.json y cuarentena")
        monthly = monthly_panel(accepted)
        _save(accepted, Path(args.output) / "daily.csv")
        _save(monthly, Path(args.output) / "monthly.csv")
        dimensions = [column for column in ["series_id", "market_region_code", "market_region", "market", "product", "variety", "quality", "unit", "origin", "currency", "market_level", "source"] if column in accepted]
        _save(accepted[dimensions].drop_duplicates(), Path(args.output) / "series.csv")
        write_json(Path(args.output) / "build_status.json", {"status": "success", "accepted_rows": len(accepted), "quarantine_rows": len(quarantined), "input_files": [str(path) for path in paths]})
        print(f"{len(accepted)} filas válidas; {len(quarantined)} en cuarentena; {len(monthly)} meses-serie")
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
            command.add_argument("--model", choices=["naive", "seasonal_naive", "ridge"], default="seasonal_naive")
            command.add_argument("--scenario-csv")
            command.add_argument("--scenario-name")
    climate = commands.add_parser("climate")
    climate.add_argument("--locations", default="config/locations.csv")
    climate.add_argument("--start", required=True)
    climate.add_argument("--end", required=True)
    climate.add_argument("--raw-root", default="data/raw/climate")
    climate.add_argument("--output", default="data/processed/climate")
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
