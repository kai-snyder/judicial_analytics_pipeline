PYTHON=python -m   # module-as-script pattern
VENV?=venv

all: setup data ingest features train evaluate

setup:
	@echo "Creating virtual-env & installing deps..."
	test -d $(VENV) || python -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip && $(VENV)/bin/pip install -r requirements.txt
	pre-commit install

data:
	$(VENV)/bin/$(PYTHON) src.data.fetch_courtlistener --start 2024-01-01 --end 2024-01-07 --court dcd

transform:
	$(VENV)/bin/$(PYTHON) src.data.transform

ingest:
	$(VENV)/bin/$(PYTHON) src.data.ingest_sql

lint:
	$(VENV)/bin/ruff .

test:
	$(VENV)/bin/pytest -q
