"""
Fetch CourtListener dockets JSONL and save to data/raw/.

Example
-------
python -m src.data.fetch_courtlistener \
       --start 2015-01-01 --end 2016-01-01 --court dcd
"""
from __future__ import annotations
import argparse, json, logging, random, time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, Iterator, Any

import requests
from tqdm import tqdm
from src.settings import api_key

# ────────────────────────────── constants ─────────────────────────────
RAW_DIR     = Path("data/raw")
REQ_PAUSE   = 1.0
MAX_RETRIES = 8
LOG         = logging.getLogger(__name__)

# ─────────────────────────── helpers ────────────────────────────────
def _safe_get(url: str, *, headers: Dict[str, str], params: Dict[str, Any]) -> requests.Response:
    """GET with exponential back-off on timeouts and 5xx."""
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(url, headers=headers, params=params, timeout=60)
            if r.status_code >= 500:
                raise requests.HTTPError(response=r)
            return r
        except (requests.ReadTimeout, requests.ConnectionError, requests.HTTPError) as err:
            wait = min(1.5 * 2 ** attempt + random.random(), 120)
            ra   = getattr(err.response, "headers", {}).get("Retry-After")
            if ra:
                wait = max(wait, float(ra))
            LOG.warning("⏳ %s – retrying in %.1fs", err, wait)
            time.sleep(wait)
    raise RuntimeError(f"Gave up after {MAX_RETRIES} retries → {url!s}")

def _request_stream(url: str, params: Dict[str, Any], session: requests.Session) -> Iterator[dict]:
    """Yield every docket JSON object for one date slice."""
    while url:
        resp = _safe_get(url, headers=session.headers, params=params)
        payload = resp.json()
        if "results" not in payload:
            LOG.warning("⚠️  non-JSON page at %s (status %s) – skipped", resp.url, resp.status_code)
            break
        yield from payload["results"]
        url    = payload.get("next")
        params = {}          # after first page
        time.sleep(REQ_PAUSE)

# ───────────────────────────── core logic ───────────────────────────
def _next_month_first(d: date) -> date:
    return date(d.year + (d.month // 12), d.month % 12 + 1, 1)

def main(start: str, end: str, court: str) -> None:
    """Write data/raw/dockets_<court>_<start>_<end>.jsonl (inclusive start, exclusive end)."""
    start_d, end_d = map(date.fromisoformat, (start, end))
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    out_path  = RAW_DIR / f"dockets_{court}_{start}_{end}.jsonl"
    url_base  = "https://www.courtlistener.com/api/rest/v4/dockets/"
    total_rows = 0

    session = requests.Session()
    session.headers.update({"Authorization": f"Token {api_key()}"})

    with out_path.open("w") as fh:
        slice_start = start_d
        while slice_start < end_d:
            slice_end = min(_next_month_first(slice_start) - timedelta(days=1),
                            end_d - timedelta(days=1))
            params = {
                "court": court,
                "date_filed__gte": slice_start.isoformat(),
                "date_filed__lte":  slice_end.isoformat(),
                "page_size": 100,
            }
            for docket in tqdm(_request_stream(url_base, params, session),
                               desc=f"{slice_start:%Y-%m}", leave=False):
                fh.write(json.dumps(docket) + "\n")
                total_rows += 1
            slice_start = slice_end + timedelta(days=1)

    LOG.info("✓ saved %s (%s rows)", out_path, total_rows)

# ─────────────────────────── CLI entry-point ────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD (inclusive)")
    parser.add_argument("--end",   required=True, help="YYYY-MM-DD (exclusive)")
    parser.add_argument("--court", required=True, help="e.g. dcd")
    args = parser.parse_args()
    main(args.start, args.end, args.court)
