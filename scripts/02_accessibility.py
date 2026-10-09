"""
Step 02 — Transit job accessibility for every NYC census tract (baseline).

Routes from each tract's residential-unit-weighted origin to every tract's
job-weighted destination on the OSM street network plus MTA subway and bus
GTFS, then counts jobs reachable within 30 / 45 / 60 minutes.

Outputs (data/processed):
  ttm_baseline.parquet       full origin x destination travel-time matrix
  access_baseline.csv        jobs_30, jobs_45, jobs_60, jobs_decay per tract
  02_access_log.txt          run settings and summary
"""
import time

import geopandas as gpd
import pandas as pd

from config import RAW, PROC
import routing

t0 = time.time()
GTFS = sorted((RAW / "gtfs").glob("gtfs_*.zip"))
OSM = PROC / "nyc_streets.osm.pbf"   # from 01b_osm_streets.py

base = PROC / "tracts_base.gpkg"
origins = gpd.read_file(base, layer="origins").rename(columns={"GEOID": "id"})
dest = gpd.read_file(base, layer="destinations").rename(columns={"GEOID": "id"})
print(f"{len(origins)} origins, {len(dest)} destinations, {len(GTFS)} GTFS feeds")

network = routing.build_network(OSM, GTFS)
print(f"Network built in {time.time() - t0:.0f}s")

ttm = routing.travel_time_matrix(network, origins, dest)
ttm.to_parquet(PROC / "ttm_baseline.parquet", index=False)
print(f"Matrix done in {time.time() - t0:.0f}s: {len(ttm):,} pairs, "
      f"{ttm.tt.notna().mean():.1%} reachable within {routing.MAX_TIME}")

acc = routing.cumulative_access(ttm, dest.set_index("id")["jobs"])
acc = acc.reindex(origins["id"]).fillna(0)
acc.index.name = "GEOID"
acc.to_csv(PROC / "access_baseline.csv")

total_jobs = dest["jobs"].sum()
summary = acc.describe(percentiles=[.1, .25, .5, .75, .9]).round(0)
lines = [
    f"Departure: {routing.DEPARTURE:%A %Y-%m-%d %H:%M} + {routing.TIME_WINDOW} window, "
    f"P{routing.PERCENTILE} travel time",
    f"Walk {routing.WALK_SPEED_KMH} km/h, max {routing.MAX_WALK} per leg, "
    f"max {routing.MAX_RIDES} rides, max trip {routing.MAX_TIME}",
    f"GTFS: {', '.join(g.name for g in GTFS)}",
    f"NYC jobs (LODES 2023): {total_jobs:,.0f}",
    "", summary.to_string(),
    f"\nRuntime {time.time() - t0:.0f}s",
]
(PROC / "02_access_log.txt").write_text("\n".join(lines))
print("\n".join(lines))
