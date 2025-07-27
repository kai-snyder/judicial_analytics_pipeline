"""
Load transformed parquet into Postgres tables as defined in sql/schema.sql
Run after `python -m src.data.transform`.
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
        # new – idempotent index to guard against duplicate loads
    logger.info("Schema checked/applied.")


def load_cases_parquet(engine) -> None:
    """
    Read every dockets_*.parquet and append only *new* rows to the cases table.
    """
    wanted_cols = [
        "case_id", "url", "court_slug", "docket_number",
        "filing_date", "closing_date",
        "nature_of_suit", "nature_of_suit_numeric",
        # columns like win_bool / disposition stay nullable – fine to omit
    ]

    for pq in PROC_DIR.glob("dockets_*.parquet"):
        df = pd.read_parquet(pq)
        if df.empty or "case_id" not in df.columns:
            logger.info("%s – empty or malformed parquet, skipping", pq.name)
            continue

        df = (
            df.rename(columns={"nos_code": "nature_of_suit_numeric"})
              .reindex(columns=wanted_cols)
        )

        df = df.drop_duplicates(subset="case_id", keep="first")
        existing = pd.read_sql("SELECT case_id FROM cases", engine)["case_id"]
        df = df[~df["case_id"].isin(existing)].copy()

        if not df.empty:
            df.to_sql(
                "cases",
                engine,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=1000,
            )
        logger.info("Inserted %s rows from %s", len(df), pq.name)


def main() -> None:
    ensure_schema()
    engine = get_engine()
    load_cases_parquet(engine)
    with engine.begin() as conn:
        conn.execute(
            text("REFRESH MATERIALIZED VIEW CONCURRENTLY judge_win_rates")
        )
    logger.info("Materialized view judge_win_rates refreshed.")



if __name__ == "__main__":
    main()
