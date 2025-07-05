#!/usr/bin/env bash
set -euo pipefail

base='https://www.courtlistener.com/api/rest/v4/courts/?jurisdiction=FD&page_size=100'
next="$base"

tmp=$(mktemp)                  # collect here first
> "$tmp"

while [[ -n "$next" && "$next" != "null" ]]; do
  echo "Fetching $next" >&2
  json=$(curl -s "$next")

  echo "$json" \
    | jq -r '
        .results[]
        | select(.end_date == null)           # active only
        | select(.id != "usdistct")           # drop umbrella record
        | .id' \
    >> "$tmp"

  next=$(echo "$json" | jq -r '.next')
done

sort -u "$tmp" > district_slugs.txt          # final, alphabetised, deduped
rm "$tmp"

echo "✔  wrote $(wc -l < district_slugs.txt) slugs to district_slugs.txt"
