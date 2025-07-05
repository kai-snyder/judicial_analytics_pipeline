START=2015-01-01
END=2016-01-01

cat district_slugs.txt | while read -r court; do
  echo "▶ Fetching $court ($START → $END)"
  python -m src.data.fetch_outcomes --start "$START" --end "$END" --court "$court"
done