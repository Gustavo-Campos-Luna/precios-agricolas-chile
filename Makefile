.PHONY: install test check data macro panel report all discover

install:
	python -m pip install -e '.[dev,parquet,grains,excel]'

test:
	python -m pytest

check:
	python -m compileall -q src tests scripts report
	python -m pytest

discover:
	mpchile discover

# Descarga y construye todos los datos desde las fuentes oficiales (varias horas la primera vez).
# El Banco Central requiere credenciales en .env (ver README).
data:
	mpchile ingest --start-year 1994 --end-year 2026
	mpchile build
	mpchile volume
	mpchile macro
	mpchile panel
	mpchile supply
	mpchile datasets
	mpchile faostat
	mpchile pinksheet
	mpchile cotrisa
	mpchile reference

# Solo el análisis por producto (requiere data/analysis).
analysis:
	python scripts/analysis_frutas.py
	python scripts/analysis_cereales.py
	python scripts/analysis_vino.py

# Informe HTML y PDF, con las tablas de cada figura en report/data.
report:
	python report/build_report.py --pdf

all: data analysis report
