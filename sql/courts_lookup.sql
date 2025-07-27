-- run once inside psql:
CREATE TABLE IF NOT EXISTS courts (
  court_slug TEXT PRIMARY KEY,
  district   TEXT,       -- 'California Northern', etc.
  state_usps TEXT
);

\copy courts FROM program '
  awk -F, "NR>1{print tolower($1) \",\" $2 \",\" $3}" \
      data/external/shapefiles/courts_lookup.csv
' WITH (FORMAT csv);
