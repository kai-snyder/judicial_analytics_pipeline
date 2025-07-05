"""
Load transformed parquet into Postgres tables as defined in sql/schema.sql
Run after `python -m court_outcome_pred.data.transform`.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from src.utils.db import get_engine

logger = logging.getLogger(__name__)
PROC_DIR = Path("data/processed")


def ensure_schema() -> None:
    engine = get_engine()
    schema_sql = Path("sql/schema.sql").read_text()
    with engine.begin() as conn:
        conn.execute(text(schema_sql))
    logger.info("Schema checked/applied.")


def load_cases_parquet(engine) -> None:
    for pq in PROC_DIR.glob("dockets_*.parquet"):
        df = pd.read_parquet(pq)
        # ── skip files that have no rows or that somehow lost the case_id column ──
        if df.empty or "case_id" not in df.columns:
            logger.info("%s – empty parquet, skipping", pq.name)
            continue
        df = df.drop_duplicates(subset="case_id", keep="first")
        existing_ids = pd.read_sql('SELECT case_id FROM cases', engine)['case_id']
        df = df.loc[~df['case_id'].isin(existing_ids)].copy()
        df.to_sql("cases", engine, if_exists="append", index=False, method="multi", chunksize=1000)
        logger.info("Inserted %s rows from %s", len(df), pq.name)


def load_outcomes_parquet(engine) -> None:
    for pq in PROC_DIR.glob("outcomes_*.parquet"):
        df = pd.read_parquet(pq)
        df.to_sql("outcomes", engine,
                  if_exists="append",
                  index=False,
                  method="multi",
                  chunksize=1000)
        logger.info("Inserted %s rows from %s", len(df), pq.name)
        # copy win_bool into cases – one SQL is faster than pandas
        with engine.begin() as con:
            con.execute(text("""
                INSERT INTO cases (case_id)                      -- no orphan FK
                SELECT case_id FROM outcomes
                ON CONFLICT DO NOTHING;
                UPDATE cases   c
                SET    outcome_win = o.win_bool
                FROM   outcomes o
                WHERE  o.case_id = c.case_id
                  AND  c.outcome_win IS DISTINCT FROM o.win_bool;
            """))


def main() -> None:
    ensure_schema()
    engine = get_engine()
    load_cases_parquet(engine)
    load_outcomes_parquet(engine)



if __name__ == "__main__":
    main()
