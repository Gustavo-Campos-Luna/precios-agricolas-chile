.PHONY: install test check discover
install:
	python -m pip install -e '.[dev,parquet]'
test:
	python -m pytest
check:
	python -m compileall -q src tests
	python -m pytest
discover:
	mpchile discover
