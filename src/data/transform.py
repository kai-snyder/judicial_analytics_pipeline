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

# columns we ultimately want → {raw_key: new_name}
COLS = {
    "id"           : "case_id",
    "absolute_url" : "url",
    "court"        : "court_slug",
    "docket_number": "docket_number",
    "date_filed"   : "filing_date",
    "date_terminated": "closing_date",
    "disposition"  : "disposition",
    "win"          : "win_bool",
}

slug_re = re.compile(r"/courts/([^/]+)/?$")

def parse_file(path: Path) -> pd.DataFrame:
    """Return a *non-empty* DataFrame or an empty one if the file has no rows."""
    if path.stat().st_size == 0:
        return pd.DataFrame()              # truly empty file

    # ── read JSONL ────────────────────────────────────────────────
    records = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    if not records:
        return pd.DataFrame()

    df = pd.json_normalize(records)

    df["nature_of_suit"] = (
        df["nature_of_suit"]
        .fillna("Unknown")           # label the blanks
        .astype("string")
    )

    # ── guarantee every expected column exists ───────────────────
    for raw in COLS.keys():
        if raw not in df.columns:
            log.debug("%s: column %s missing – filling NA", path.name, raw)
            df[raw] = pd.NA

    # ── fix the `court` URL → slug ───────────────────────────────
    df["court"] = (
        df["court"]
        .astype("string")
        .str.extract(slug_re, expand=False)   # keep only the slug
    )

    # ── reorder / rename and drop duplicates ─────────────────────
    tidy = df[list(COLS.keys())].rename(columns=COLS).drop_duplicates()

    return tidy


def main() -> None:
    # ------------ dockets -------------
    for f in RAW_DIR.glob("dockets_*.jsonl"):
        log.info("Transforming %s", f.name)
        tidy = parse_file(f)
        out  = PROC_DIR / f"{f.stem}.parquet"
        tidy.to_parquet(out, index=False)
        log.info(" → %d rows → %s", len(tidy), out)

    # ------------ outcomes ------------
    for f in RAW_DIR.glob("outcomes_*.jsonl"):
        log.info("Transforming %s", f.name)
        df  = pd.read_json(f, lines=True)
        out = PROC_DIR / f"{f.stem}.parquet"
        df.to_parquet(out, index=False)
        log.info(" → %d rows → %s", len(df), out)


if __name__ == "__main__":
    main()
