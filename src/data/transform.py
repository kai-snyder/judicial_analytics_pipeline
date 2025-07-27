"""
Convert raw JSONL into tidy parquet files under data/processed/.
"""

from __future__ import annotations
import json, logging, re
from pathlib import Path
import pandas as pd

log      = logging.getLogger(__name__)
RAW_DIR  = Path("data/raw")
PROC_DIR = Path("data/processed")
PROC_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────────── docket → case parquet ──────────────────────────
COLS = {
    "id"             : "case_id",
    "absolute_url"   : "url",
    "court"          : "court_slug",
    "docket_number"  : "docket_number",
    "date_filed"     : "filing_date",
    "date_terminated": "closing_date",
    "nature_of_suit" : "nature_of_suit",
    "nos_code"       : "nature_of_suit_numeric",
}

slug_re = re.compile(r"/courts/([^/]+)/?$")

def parse_docket_file(path: Path) -> pd.DataFrame:
    if path.stat().st_size == 0:
        return pd.DataFrame()

    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if not records:
        return pd.DataFrame()

    df = pd.json_normalize(records)

    df["nature_of_suit"] = (
        df["nature_of_suit"]
          .fillna("Unknown")
          .astype("string")
    )

    df["nos_code"] = (
        df["nature_of_suit"]
          .str.extract(r"^(\d{3})", expand=False)
          .astype("Int16")
    )

    for raw in COLS.keys():
        if raw not in df.columns:
            df[raw] = pd.NA

    df["court"] = (
        df["court"]
          .astype("string")
          .str.extract(slug_re, expand=False)
    )

    tidy = df[list(COLS.keys())].rename(columns=COLS).drop_duplicates()
    return tidy


def main() -> None:

    for f in RAW_DIR.glob("dockets_*.jsonl"):
        log.info("Transforming %s", f.name)
        tidy = parse_docket_file(f)
        out  = PROC_DIR / f"{f.stem}.parquet"
        tidy.to_parquet(out, index=False)
        log.info(" → %d rows → %s", len(tidy), out)


if __name__ == "__main__":
    main()
