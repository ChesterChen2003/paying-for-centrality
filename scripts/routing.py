"""
Shared transit-routing helper (r5py / Conveyal R5).

Both the baseline accessibility run (step 02) and the IBX scenario (step 06)
call `travel_time_matrix()` so the two use identical routing settings.

Requirements: Java 21 and `pip install r5py`. On first use r5py downloads the
R5 routing engine (~60 MB) automatically; set R5_JAR to use a local copy.
"""
import datetime as dt
import os
import sys

# r5py reads its settings from the command line, so set them before importing.
_mem = os.environ.get("R5_MAX_MEMORY", "80%")
sys.argv += ["--max-memory", _mem]
if os.environ.get("R5_JAR"):
    sys.argv += ["--r5-classpath", os.environ["R5_JAR"]]

import r5py  # noqa: E402

# --- routing assumptions (documented in the README) -------------------------
# A typical school-term Tuesday inside every feed's calendar
DEPARTURE = dt.datetime(2026, 10, 20, 7, 0)
# Median travel time across every departure minute 7:00–8:00, so results don't
# hinge on catching (or just missing) a particular train
TIME_WINDOW = dt.timedelta(minutes=60)
PERCENTILE = 50
MAX_TIME = dt.timedelta(minutes=90)
MAX_WALK = dt.timedelta(minutes=20)    # per access / egress / transfer leg
WALK_SPEED_KMH = 4.8                   # 3 mph
MAX_RIDES = 4                          # up to 3 transfers


def build_network(osm_pbf, gtfs_files):
    return r5py.TransportNetwork(str(osm_pbf), [str(g) for g in gtfs_files])


def travel_time_matrix(network, origins, destinations):
    """origins / destinations: GeoDataFrames with an `id` column (any CRS)."""
    ttm = r5py.TravelTimeMatrix(
        network,
        origins=origins.to_crs("EPSG:4326"),
        destinations=destinations.to_crs("EPSG:4326"),
        departure=DEPARTURE,
        departure_time_window=TIME_WINDOW,
        percentiles=[PERCENTILE],
        transport_modes=[r5py.TransportMode.TRANSIT, r5py.TransportMode.WALK],
        access_modes=[r5py.TransportMode.WALK],
        egress_modes=[r5py.TransportMode.WALK],
        max_time=MAX_TIME,
        max_time_walking=MAX_WALK,
        speed_walking=WALK_SPEED_KMH,
        max_public_transport_rides=MAX_RIDES,
        snap_to_network=True,
    )
    import pandas as pd
    out = pd.DataFrame(ttm)[["from_id", "to_id", "travel_time"]]
    return out.rename(columns={"travel_time": "tt"})


def cumulative_access(ttm, jobs, thresholds=(30, 45, 60)):
    """Jobs reachable within each threshold, plus a decay-weighted measure.

    ttm  : DataFrame from_id, to_id, tt (minutes; NaN = not reachable in MAX_TIME)
    jobs : Series of job counts indexed by destination id
    """
    import numpy as np
    import pandas as pd

    t = ttm.merge(jobs.rename("jobs"), left_on="to_id", right_index=True)
    out = {}
    for th in thresholds:
        out[f"jobs_{th}"] = t.loc[t.tt <= th].groupby("from_id")["jobs"].sum()
    # Negative-exponential decay with a 30-minute half-life (weight 0.5 at 30
    # min, 0.25 at 60 min) — rewards nearer jobs without a hard cutoff
    beta = np.log(2) / 30.0
    t["w"] = t["jobs"] * np.exp(-beta * t["tt"])
    out["jobs_decay"] = t.dropna(subset=["tt"]).groupby("from_id")["w"].sum()
    res = pd.DataFrame(out).fillna(0)
    return res
