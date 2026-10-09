"""
Step 06b — IBX scenario: who gains job access, and are they vulnerable renters?

Builds an illustrative GTFS feed for the Interborough Express from public MTA
parameters, re-runs the step-02 routing with it added to the baseline feeds,
and compares access tract by tract.

Public parameters used (MTA IBX materials, 2025–26):
  18 stations, Brooklyn Army Terminal ↔ Roosevelt Av, ~32 min end to end,
  trains every 5 minutes in the peak (10 off-peak). Station positions come from
  06a; running time between stations is proportional to distance.

This is a sketch-planning scenario, not a ridership forecast: it holds jobs,
housing and the rest of the network fixed and assumes MTA's stated service.

Outputs: data/processed/gtfs_ibx.zip, ttm_ibx.parquet (06c compares it with
         the baseline; kept separate so the routing JVM's memory is released first)
"""
import io
import time
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd

from config import RAW, PROC, TAB

t0 = time.time()
LOG = []


def log(m=""):
    print(m)
    LOG.append(str(m))


END_TO_END_MIN = 32.0
DWELL_SEC = 30
PEAK_HEADWAY = 5          # minutes, 06:00–10:00 and 15:00–19:00
OFFPEAK_HEADWAY = 10      # minutes, otherwise 05:00–24:00

st = gpd.read_file(PROC / "ibx_corridor.gpkg", layer="stations").sort_values("order")
ll = st.to_crs("EPSG:4326")

# ---- running times ---------------------------------------------------------------
xy = np.column_stack([st.geometry.x, st.geometry.y])
seg_ft = np.hypot(*np.diff(xy, axis=0).T)
n_dw = len(st) - 2                                     # intermediate stops dwell
run_total = END_TO_END_MIN * 60 - n_dw * DWELL_SEC
seg_sec = run_total * seg_ft / seg_ft.sum()
log(f"IBX: {len(st)} stations, {seg_ft.sum() / 5280:.1f} mi between stations, "
    f"{END_TO_END_MIN:.0f} min end to end → avg {seg_ft.sum() / 5280 / (END_TO_END_MIN / 60):.1f} mph")


def departures():
    t, out = 5 * 3600, []
    while t < 24 * 3600:
        out.append(t)
        h = t / 3600
        peak = 6 <= h < 10 or 15 <= h < 19
        t += (PEAK_HEADWAY if peak else OFFPEAK_HEADWAY) * 60
    return out


def hms(s):
    s = int(round(s))
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


stops = pd.DataFrame({"stop_id": [f"IBX{o:02d}" for o in st["order"]],
                      "stop_name": [f"IBX {n}" for n in st["station"]],
                      "stop_lat": ll.geometry.y.round(6).values,
                      "stop_lon": ll.geometry.x.round(6).values})
trips, stop_times = [], []
for direction, seq in [(0, list(range(len(st)))), (1, list(range(len(st)))[::-1])]:
    segs = seg_sec if direction == 0 else seg_sec[::-1]
    for k, dep in enumerate(departures()):
        tid = f"IBX_{direction}_{k:03d}"
        trips.append({"route_id": "IBX", "service_id": "WKDY", "trip_id": tid,
                      "direction_id": direction})
        t = dep
        for i, idx in enumerate(seq):
            arr = t
            dep_t = arr + (DWELL_SEC if 0 < i < len(seq) - 1 else 0)
            stop_times.append({"trip_id": tid, "arrival_time": hms(arr),
                               "departure_time": hms(dep_t),
                               "stop_id": stops.stop_id.iat[idx], "stop_sequence": i + 1})
            if i < len(seq) - 1:
                t = dep_t + segs[i]

feed = {
    "agency.txt": pd.DataFrame([{"agency_id": "IBX", "agency_name": "IBX scenario (illustrative)",
                                 "agency_url": "https://ibx.mta.info", "agency_timezone": "America/New_York"}]),
    "routes.txt": pd.DataFrame([{"route_id": "IBX", "agency_id": "IBX", "route_short_name": "IBX",
                                 "route_long_name": "Interborough Express (scenario)", "route_type": 0}]),
    "stops.txt": stops,
    "trips.txt": pd.DataFrame(trips),
    "stop_times.txt": pd.DataFrame(stop_times),
    "calendar.txt": pd.DataFrame([{"service_id": "WKDY", "monday": 1, "tuesday": 1, "wednesday": 1,
                                   "thursday": 1, "friday": 1, "saturday": 0, "sunday": 0,
                                   "start_date": "20260901", "end_date": "20261231"}]),
}
gtfs_path = PROC / "gtfs_ibx.zip"
# Fixed timestamps keep the zip byte-identical across runs, so r5py can reuse
# its cached network instead of rebuilding it (~10 min)
with zipfile.ZipFile(gtfs_path, "w", zipfile.ZIP_DEFLATED) as z:
    for name, df in feed.items():
        info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, df.to_csv(index=False))
log(f"Wrote {gtfs_path.name}: {len(trips)} trips, {len(stop_times)} stop times")

# ---- routing with IBX ---------------------------------------------------------
import routing  # noqa: E402  (imports r5py; keep after the light work above)

GTFS = sorted((RAW / "gtfs").glob("gtfs_*.zip")) + [gtfs_path]
OSM = PROC / "nyc_streets.osm.pbf"
base = PROC / "tracts_base.gpkg"
origins = gpd.read_file(base, layer="origins").rename(columns={"GEOID": "id"})
dest = gpd.read_file(base, layer="destinations").rename(columns={"GEOID": "id"})
network = routing.build_network(OSM, GTFS)
log(f"Network with IBX built in {time.time() - t0:.0f}s")
ttm = routing.travel_time_matrix(network, origins, dest)
ttm.to_parquet(PROC / "ttm_ibx.parquet", index=False)
log(f"Matrix saved ({len(ttm):,} pairs) in {time.time() - t0:.0f}s — run 06c_ibx_effects.py next")
(PROC / "06b_ibx_log.txt").write_text("\n".join(LOG))
