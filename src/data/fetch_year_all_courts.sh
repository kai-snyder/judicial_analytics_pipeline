#!/usr/bin/env bash
set -euo pipefail

START="2015-01-01"
END="2016-01-01"

while read -r COURT; do
  echo "▶️  Fetching $COURT ($START → $END)" >&2
  python -m src.data.fetch_courtlistener \
         --start "$START" \
         --end   "$END"   \
         --court "$COURT" \
  || echo "⚠️  $COURT failed, continuing…" >&2
  sleep 0.5         # brief pause – be polite to the API
done < district_slugs.txt
