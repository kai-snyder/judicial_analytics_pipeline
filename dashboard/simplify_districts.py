import geopandas as gpd, pathlib, shutil, json

raw   = pathlib.Path("dashboard/shapefiles/district_courts/US_District_Court_Jurisdictions.shp")
out   = pathlib.Path("dashboard/shapefiles/district_courts/districts_simplified.geojson")

gdf = gpd.read_file(raw).to_crs(3857)                     # web‐mercator → metres
gdf["geometry"] = gdf.geometry.simplify(2500)             # keep vertices ≥ 2.5 km apart
gdf = gdf.to_crs(4326)[["NAME", "geometry"]]              # back to WGS84

gdf.to_file(out, driver="GeoJSON")
print(f"saved {out} → {out.stat().st_size/1_048_576:.1f} MB")
