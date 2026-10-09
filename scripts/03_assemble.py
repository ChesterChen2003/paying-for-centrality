"""
Step 03 — Assemble the tract analysis dataset.

Joins ACS 5-year estimates and the step-02 accessibility results onto the
tract geography from step 01, builds model variables and sample flags.

Output: data/processed/tracts_analysis.gpkg (layer "tracts"), plus
        data/processed/03_assemble_log.txt
"""
import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

from config import RAW, PROC, RENT_TOPCODE, RENT_TOPCODE_VALUE

log_lines = []


def log(msg=""):
    print(msg)
    log_lines.append(str(msg))


tracts = gpd.read_file(PROC / "tracts_base.gpkg", layer="tracts")

# ----------------------------------------------------------------------------
# 1. ACS 5-year
# ----------------------------------------------------------------------------
acs_files = sorted((RAW / "acs").glob("acs5_*_nyc_tracts.json"))
if not acs_files:
    sys.exit("No ACS file found in data/raw/acs — run 00_download_data.sh")
acs_path = acs_files[-1]                      # newest year available
acs_year = acs_path.name.split("_")[1]
raw = json.loads(acs_path.read_text())
acs = pd.DataFrame(raw[1:], columns=raw[0])
acs["GEOID"] = acs["state"] + acs["county"] + acs["tract"]
num_cols = [c for c in acs.columns if c[:1] == "B"]
acs[num_cols] = acs[num_cols].apply(pd.to_numeric, errors="coerce")
# Census "jam values" (e.g. -666666666 = not computable) are negative → missing
acs[num_cols] = acs[num_cols].where(acs[num_cols] >= 0)
log(f"ACS {acs_year} 5-year rows: {len(acs)}")

a = pd.DataFrame({"GEOID": acs["GEOID"]})
a["rent"] = acs["B25064_001E"]
a["rent_moe"] = acs["B25064_001M"]
a["rent_cv"] = (a["rent_moe"] / 1.645) / a["rent"]
a["rent_topcoded"] = a["rent"] >= RENT_TOPCODE_VALUE
a["occ_units"] = acs["B25003_001E"]
a["renter_units"] = acs["B25003_003E"]
a["renter_share"] = a["renter_units"] / a["occ_units"]
burden_den = acs["B25070_001E"] - acs["B25070_011E"]      # exclude "not computed"
a["burden30_share"] = acs[["B25070_007E", "B25070_008E", "B25070_009E",
                           "B25070_010E"]].sum(axis=1, min_count=4) / burden_den
a["burden50_share"] = acs["B25070_010E"] / burden_den
a["renter_yrbuilt_med"] = acs["B25037_003E"]
a["renter_rooms_med"] = acs["B25021_003E"]
a["hh_income_med"] = acs["B19013_001E"]
a["pop"] = acs["B01003_001E"]
a["transit_commute_share"] = acs["B08301_010E"] / acs["B08301_001E"]
a["poverty_rate"] = acs["B17001_002E"] / acs["B17001_001E"]
a = a.replace([np.inf, -np.inf], np.nan)

tracts = tracts.merge(a, on="GEOID", how="left")
log(f"Tracts matched to ACS: {tracts['occ_units'].notna().sum()} of {len(tracts)}")
log(f"Tracts with a median gross rent estimate: {tracts['rent'].notna().sum()}")
tracts["pop_density_km2"] = tracts["pop"] / tracts["land_km2"]

# ----------------------------------------------------------------------------
# 2. Accessibility (step 02)
# ----------------------------------------------------------------------------
acc_path = PROC / "access_baseline.csv"
if not acc_path.exists():
    sys.exit("access_baseline.csv not found — run 02_accessibility.py first")
acc = pd.read_csv(acc_path, dtype={"GEOID": str})
tracts = tracts.merge(acc, on="GEOID", how="left")
total_jobs = tracts["jobs"].sum()
for c in ["jobs_30", "jobs_45", "jobs_60"]:
    tracts[c.replace("jobs_", "jobshare_")] = tracts[c] / total_jobs
# log access, in thousands of jobs; +1 guards the few tracts with zero access
tracts["ln_jobs45"] = np.log1p(tracts["jobs_45"] / 1000)
tracts["ln_jobs_decay"] = np.log1p(tracts["jobs_decay"] / 1000)

# ----------------------------------------------------------------------------
# 3. Model variables and sample
# ----------------------------------------------------------------------------
tracts["ln_rent"] = np.log(tracts["rent"])
tracts["renter_age"] = 2024 - tracts["renter_yrbuilt_med"]   # median age of rental stock (ACS; bottom-coded at 1939)
tracts["renter_age_bottomcoded"] = tracts["renter_yrbuilt_med"] <= 1939
tracts["pluto_age"] = 2024 - tracts["pluto_yrbuilt_med"]      # all residential units (PLUTO)
tracts["in_sample"] = (tracts["rent"].notna() & (tracts["renter_units"] >= 50)
                       & tracts[["renter_rooms_med", "renter_yrbuilt_med",
                                 "pre74_6plus_share", "jobs_45"]].notna().all(axis=1))
tracts["rent_reliable"] = tracts["rent_cv"] <= 0.30

s = tracts[tracts.in_sample]
log("")
log("Analysis sample: tracts with an ACS median gross rent, >= 50 renter-occupied")
log(f"units and complete controls: {len(s)}")
log(f"  top-coded at ${RENT_TOPCODE:,}+: {int(s.rent_topcoded.sum())}")
log(f"  ACS renter year built bottom-coded at 1939: {int(s.renter_age_bottomcoded.sum())}")
log(f"  rent CV > 0.30 (low reliability): {int((~s.rent_reliable).sum())}")
log("  by borough:\n" + s.groupby("boroname").size().to_string())
dropped = tracts[~tracts.in_sample]
log(f"Excluded: {len(dropped)} (no rent estimate: {dropped.rent.isna().sum()}, "
    f"<50 renter units: {((dropped.renter_units < 50) & dropped.rent.notna()).sum()})")

tracts.to_file(PROC / "tracts_analysis.gpkg", layer="tracts", driver="GPKG")
(PROC / "03_assemble_log.txt").write_text(f"ACS year: {acs_year}\n" + "\n".join(log_lines))
log(f"\nSaved {PROC / 'tracts_analysis.gpkg'}")
