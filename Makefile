PYTHON=python -m court_outcome_pred   # module-as-script pattern
VENV?=venv

all: setup data ingest features train evaluate

setup:
	@echo "Creating virtual-env & installing deps..."
	test -d $(VENV) || python -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip && $(VENV)/bin/pip install -r requirements.txt
	pre-commit install

data:
	$(VENV)/bin/$(PYTHON) data.fetch_courtlistener --start 2024-01-01 --end 2024-01-07 --court dcd

ingest:
	$(VENV)/bin/$(PYTHON) data.ingest_sql

features:
	$(VENV)/bin/$(PYTHON) features.build_features

train:
	$(VENV)/bin/$(PYTHON) models.train

evaluate:
	$(VENV)/bin/$(PYTHON) models.evaluate

lint:
	$(VENV)/bin/ruff .

test:
	$(VENV)/bin/pytest -q
