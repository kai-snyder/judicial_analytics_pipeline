"""
Fetch raw CourtListener docket JSON and save to data/raw/.

Example
-------
python -m src.data.fetch_courtlistener \
       --start 2009-06-01 --end 2010-06-01 --court dcd
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterator, Any

import requests
from tqdm import tqdm

from src.settings import api_key  # ← your helper that returns the CL API token

# ──────────────────────────── constants ────────────────────────────
RAW_DIR     = Path("data/raw")
REQ_PAUSE   = 1.0               # seconds between successful pages
MAX_RETRIES = 8                 # for 5xx / network hiccups
MONTH       = timedelta(days=31)  # crude “one month” step
LOG         = logging.getLogger(__name__)

# ─────────────────────────── helpers ───────────────────────────────
def _safe_get(url: str,
              *,
              headers: Dict[str, str],
              params : Dict[str, Any]) -> requests.Response:
    """
    GET with exponential back-off on *any* timeout / connection error / HTTP 5xx.
    """
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=60)
            if r.status_code >= 500:
                raise requests.HTTPError(response=r)
            return r
        except (requests.ReadTimeout,
                requests.ConnectionError,
                requests.HTTPError) as err:
            wait = min(1.5 * 2 ** attempt + random.random(), 120)
            ra   = getattr(err.response, "headers", {}).get("Retry-After")
            if ra:
                wait = max(wait, float(ra))
            LOG.warning("⏳ %s – retrying in %.1fs", err, wait)
            time.sleep(wait)
    raise RuntimeError(f"Gave up after {MAX_RETRIES} retries → {url!s}")

def _request_stream(url: str, params: Dict[str, Any]) -> Iterator[dict]:
    """
    Cursor-paginate through *one* slice (≤ 1 month).  Yields raw JSON rows.
    Skips HTML/429/5xx pages gracefully instead of crashing.
    """
    headers = {"Authorization": f"Token {api_key()}"}
    while url:
        resp = _safe_get(url, headers=headers, params=params)
        payload = resp.json()

        # ── guard: if the page is not a normal dockets page ──────────
        if "results" not in payload:                     # HTML error, 429, 404 …
            LOG.warning("⚠️  non-JSON page at %s (status %s) – skipped",
                        resp.url, resp.status_code)
            break                                        # abort this slice

        for row in payload["results"]:
            yield row

        url    = payload.get("next")     # pagination cursor
        params = {}                      # only for first page
        time.sleep(REQ_PAUSE)

# ─────────────────────────── core logic ────────────────────────────
def _next_month_first(d: date) -> date:
    """Return the first day of the month following *d*."""
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)

def main(start: str, end: str, court: str) -> None:
    """
    Fetch dockets for the inclusive range [start, end) – *end* is exclusive.

    A single JSONL file is written:
      data/raw/dockets_<court>_<start>_<end>.jsonl
    """
    start_d = date.fromisoformat(start)
    end_d   = date.fromisoformat(end)          # exclusive
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    out_path = RAW_DIR / f"dockets_{court}_{start}_{end}.jsonl"
    url_base = "https://www.courtlistener.com/api/rest/v4/dockets/"
    total_rows = 0

    with out_path.open("w") as fh:
        slice_start = start_d
        while slice_start < end_d:
            slice_end = min(_next_month_first(slice_start) - timedelta(days=1),
                            end_d - timedelta(days=1))  # inclusive end
            params = {
                "court": court,
                "date_filed__gte": slice_start.isoformat(),
                "date_filed__lte":  slice_end.isoformat(),
                "page_size": 100,
            }
            for docket in tqdm(_request_stream(url_base, params),
                               desc=f"{slice_start:%Y-%m}",
                               leave=False):
                fh.write(json.dumps(docket) + "\n")
                total_rows += 1
            slice_start = slice_end + timedelta(days=1)

    LOG.info("✓ saved %s (%s rows)", out_path, total_rows)

# ──────────────────────────── CLI entry-point ───────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end",   required=True, help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--court", required=True, help="e.g. dcd")
    args = parser.parse_args()
    main(args.start, args.end, args.court)
