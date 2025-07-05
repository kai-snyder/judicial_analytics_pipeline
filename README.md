# Judicial Analytics Pipeline

A reproducible, Python-first data pipeline that fetches CourtListener
district-court dockets, transforms them into tidy parquet files, loads them into
PostgreSQL, and (optionally) serves a Streamlit dashboard.

|       Stage      |                  Script / Tool                  |                          What it does                         |
|------------------|-------------------------------------------------|---------------------------------------------------------------|
| **1. Fetch**     | `fetch_fd_slugs.sh`, `fetch_year_all_courts.sh` | Pull raw JSONL dockets + outcomes from CourtListener REST API |
| **2. Transform** | `python -m src.data.transform`                  | Normalize JSONL → parquet (`data/processed/…`)                |
| **3. Ingest**    | `python -m src.cli ingest`                      | Create schema, load parquet into Postgres                     |
| **4. Explore**   | `streamlit run dashboard/app.py`                | Interactive dashboard (optional)                              |

---

## Folder layout

```
├─ config/ # logging + settings templates
├─ data/ # <- ignored in Git
│ ├─ raw/ # raw JSONL from CourtListener
│ └─ processed/ # tidy parquet
├─ docker/ # Dockerfile + docker-compose.yml
├─ sql/ # schema.sql (DDL)
├─ src/ # Python package
│ ├─ data/ # fetch / transform / ingest helpers
│ └─ utils/ # small shared helpers
└─ dashboard/ # Streamlit app (optional)
```

---

## Quick-start (local)

```
# 0. Clone & install deps
git clone https://github.com/kai-snyder/judicial_analytics_pipeline.git
cd judicial_analytics_pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 1. Fetch a year of dockets + outcomes
./fetch_year_all_courts.sh 2015

# 2. Transform JSONL → parquet
python -m src.data.transform

# 3. Spin up Postgres in Docker
docker compose -f docker/docker-compose.yml up -d db

# 4. Load parquet into Postgres
python -m src.cli ingest

# 5. Explore
streamlit run dashboard/app.py            # optional
```

## Environment variables

Copy `.env.example` → `.env` and fill in as needed.

|      Var       |                             Default                                   | Purpose                                               |
|----------------|-----------------------------------------------------------------------|-------------------------------------------------------|
| `CL_API_KEY`   | _empty_                                                               | (Optional) CourtListener API key – higher rate limits |
| `DATABASE_URL` | `postgresql+psycopg2://postgres:postgres@localhost:5432/case_details` | SQLAlchemy URL used by the pipeline                   |
```

---

## Docker (one-liner)

> Great for demos / CI runs

```
make up          # builds image, launches Postgres, runs full ETL
make down        # stop + remove containers/volumes
```

## Development Tips

- **Work on one court at a time**  
  Edit `fetch_fd_slugs.sh` (or call `python -m src.data.fetch_courtlistener`) with a single `--court dcd` flag while prototyping.

- **Reset the processed layer**  
  Remove stale parquet files before re-running the transform step:  
  `rm -f data/processed/*.parquet`

- **Skip empty parquet files**  
  `ingest_sql.py` already ignores zero-row files, but you can verify with  
  `python - <<'PY'  
  import glob, pandas as pd, pathlib, sys  
  for p in pathlib.Path("data/processed").glob("*.parquet"):  
      if pd.read_parquet(p).empty: print("EMPTY →", p)  
  PY`

- **Quick ETL smoke test**  
  ```bash
  make db           # spin up Postgres only
  python -m src.cli transform
  python -m src.cli ingest
