"""
Convert raw outcomes_*.jsonl → Parquet with the columns we need.
"""
from pathlib import Path
import json, logging
import pandas as pd

RAW  = Path("data/raw")
PROC = Path("data/processed")
log  = logging.getLogger(__name__)

def transform_one(jf: Path) -> None:
    records = [json.loads(line) for line in jf.open()]
    df = (pd.json_normalize(records)
            .loc[:, ["case", "outcome", "disposition",
                     "date", "winner"]]
            .rename(columns={"case": "case_id",
                             "date": "outcome_date",
                             "winner": "win_bool"}) )
    df["case_id"] = df["case_id"].str.extract(r"/(?P<id>\d+)/?$").astype(int)
    PROC.mkdir(parents=True, exist_ok=True)
    out = PROC / jf.with_suffix(".parquet").name
    df.to_parquet(out, index=False)
    log.info("→ %s rows → %s", len(df), out)

def main() -> None:
    for jf in RAW.glob("outcomes_*.jsonl"):
        transform_one(jf)

if __name__ == "__main__":
    main()
