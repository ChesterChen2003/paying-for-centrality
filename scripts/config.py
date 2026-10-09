"""Shared paths and constants for the NYC Transit Access & Rent project."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "outputs"
FIG = OUT / "figures"
TAB = OUT / "tables"
for p in (PROC, FIG, TAB):
    p.mkdir(parents=True, exist_ok=True)

# NAD83 / New York Long Island (ftUS) — the city's standard projected CRS.
# All distances and areas are computed here (the 2025 version used Web
# Mercator, which inflates NYC areas by ~74% and shrinks a "400 m" buffer to ~303 m).
CRS_NYC = "EPSG:2263"
CRS_WGS = "EPSG:4326"
FT_PER_M = 3.280833333
SQFT_PER_KM2 = FT_PER_M ** 2 * 1e6

NYC_COUNTIES = {"005": "Bronx", "047": "Brooklyn", "061": "Manhattan",
                "081": "Queens", "085": "Staten Island"}
BOROCODE = {"1": "Manhattan", "2": "Bronx", "3": "Brooklyn",
            "4": "Queens", "5": "Staten Island"}

# Reference points for the distance-to-CBD robustness control (WGS84 lon, lat)
CBD_POINTS = {"Midtown (Grand Central)": (-73.9772, 40.7527),
              "Lower Manhattan (Fulton Center)": (-74.0090, 40.7104)}

# ACS top-codes median gross rent: the API reports 3501 for "$3,500 or more"
RENT_TOPCODE = 3500          # label value
RENT_TOPCODE_VALUE = 3501    # value that marks a censored estimate
