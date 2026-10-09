"""
Step 01 — Build the tract geography, housing-stock controls, and the
origin / destination points used for routing. (ACS is attached in step 03.)

Inputs (data/raw, from 00_download_data.sh):
  boundaries/nyc_tracts_2020.geojson   DCP shoreline-clipped 2020 tracts (with NTA codes)
  boundaries/nyc_ntas_2020.geojson     2020 NTAs (for display / aggregation)
  pluto/pluto_lots.csv                 PLUTO tax lots (selected columns)
  lodes/ny_wac_S000_JT00_2023.csv.gz   LODES jobs by workplace block
  lodes/ny_xwalk.csv.gz                LODES block crosswalk (block coordinates)

Outputs (data/processed):
  tracts_base.gpkg   layer "tracts"       polygons + housing-stock / jobs / location, EPSG:2263
                     layer "origins"      residential-unit-weighted tract points
                     layer "destinations" job-weighted tract points with job counts
  ntas.gpkg          NTA polygons, EPSG:2263
  01_build_log.txt   counts and data-quality notes
"""
import geopandas as gpd
import numpy as np
import pandas as pd

from config import RAW, PROC, CRS_NYC, CRS_WGS, SQFT_PER_KM2, NYC_COUNTIES, CBD_POINTS

log_lines = []


def log(msg=""):
    print(msg)
    log_lines.append(str(msg))


# ----------------------------------------------------------------------------
# 1. Boundaries
# ----------------------------------------------------------------------------
tracts = gpd.read_file(RAW / "boundaries" / "nyc_tracts_2020.geojson")
tracts = tracts.set_crs(CRS_WGS, allow_override=True).to_crs(CRS_NYC)
tracts["geometry"] = tracts.geometry.make_valid()
tracts = tracts.rename(columns={"geoid": "GEOID"})
tracts["GEOID"] = tracts["GEOID"].astype(str).str.zfill(11)
tracts["boroct2020"] = tracts["boroct2020"].astype(str)
tracts["land_km2"] = tracts.geometry.area / SQFT_PER_KM2
keep = ["GEOID", "boroct2020", "borocode", "boroname", "ctlabel", "nta2020",
        "ntaname", "cdta2020", "land_km2", "geometry"]
tracts = tracts[keep]
log(f"Tracts read: {len(tracts)}  (unique GEOID: {tracts.GEOID.nunique()})")

ntas = gpd.read_file(RAW / "boundaries" / "nyc_ntas_2020.geojson")
ntas = ntas.set_crs(CRS_WGS, allow_override=True).to_crs(CRS_NYC)
ntas["geometry"] = ntas.geometry.make_valid()
ntas["ntatype"] = ntas["ntatype"].astype(str)
ntas = ntas[["nta2020", "ntaname", "ntatype", "boroname", "cdta2020", "geometry"]]
ntas.to_file(PROC / "ntas.gpkg", layer="ntas", driver="GPKG")
log(f"NTAs read: {len(ntas)}  (residential ntatype=0: {(ntas.ntatype == '0').sum()})")

# ----------------------------------------------------------------------------
# 2. PLUTO — housing-stock controls and residential-unit-weighted origins
# ----------------------------------------------------------------------------
pl = pd.read_csv(RAW / "pluto" / "pluto_lots.csv", dtype={"bct2020": str, "bbl": str},
                 low_memory=False)
for c in ["yearbuilt", "unitsres", "unitstotal", "latitude", "longitude"]:
    pl[c] = pd.to_numeric(pl[c], errors="coerce")
pluto_version = pl["version"].dropna().astype(str).mode().iat[0] if "version" in pl else "?"
log(f"PLUTO lots: {len(pl):,}  (version {pluto_version})")
res = pl[(pl["unitsres"] > 0) & pl["bct2020"].notna()].copy()
res["bct2020"] = res["bct2020"].str.replace(r"\.0$", "", regex=True)

# Public housing: lots owned by the NYC Housing Authority (rents are set by
# income, not the market, so they need their own control)
nycha_path = RAW / "pluto" / "pluto_nycha_lots.csv"
if nycha_path.exists():
    ny = pd.read_csv(nycha_path, dtype={"bbl": str})
    log("NYCHA-candidate owner names (lots):\n" +
        ny["ownername"].value_counts().head(8).to_string())
    # keep the city housing authority only (drop e.g. state or other authorities)
    ny = ny[ny["ownername"].str.upper().str.contains(r"NYC\s+HOUSING AUTH|NEW YORK CITY HOUSING AUTH",
                                                     regex=True, na=False)]
    res["nycha"] = res["bbl"].isin(set(ny["bbl"]))
    log(f"NYCHA lots matched: {int(res['nycha'].sum()):,}, "
        f"units: {int(res.loc[res.nycha, 'unitsres'].sum()):,}")
else:
    log("!! pluto_nycha_lots.csv not found — public-housing control skipped")
    res["nycha"] = False
res["nycha_units"] = np.where(res["nycha"], res["unitsres"], 0)

# Rent-stabilization proxy: privately owned rental buildings built before 1974
# with 6+ units (the core of the Emergency Tenant Protection Act universe).
# Rental = walk-up (C), elevator (D) or mixed store/apartment (S) classes,
# excluding co-ops (C6, C8, D0, D4) and condominiums (R*).
cls = res["bldgclass"].fillna("").astype(str)
rental_class = cls.str[0].isin(["C", "D", "S"]) & ~cls.isin(["C6", "C8", "D0", "D4"])
res["pre74_6plus_units"] = np.where(
    (res["yearbuilt"] > 0) & (res["yearbuilt"] < 1974) & (res["unitsres"] >= 6)
    & rental_class & ~res["nycha"], res["unitsres"], 0)
hs = res.groupby("bct2020").agg(res_units=("unitsres", "sum"),
                                pre74_6plus_units=("pre74_6plus_units", "sum"),
                                nycha_units=("nycha_units", "sum"),
                                res_lots=("unitsres", "size")).reset_index()
hs["pre74_6plus_share"] = hs["pre74_6plus_units"] / hs["res_units"]
hs["nycha_share"] = hs["nycha_units"] / hs["res_units"]


# Unit-weighted median year built of all residential units (PLUTO) — an
# alternative to the ACS renter measure, which is bottom-coded at 1939
def wmedian(d):
    d = d[d.yearbuilt > 1800].sort_values("yearbuilt")
    if d.empty:
        return np.nan
    c = d.unitsres.cumsum()
    return float(d.yearbuilt.iloc[np.searchsorted(c, c.iloc[-1] / 2)])


yb = res.groupby("bct2020")[["yearbuilt", "unitsres"]].apply(wmedian).rename("pluto_yrbuilt_med")
hs = hs.merge(yb, left_on="bct2020", right_index=True, how="left")
tracts = tracts.merge(hs.rename(columns={"bct2020": "boroct2020"}),
                      on="boroct2020", how="left")
log(f"Tracts matched to PLUTO residential lots: {tracts['res_units'].notna().sum()}")

# Origins: centroid of residential lots weighted by residential units
geo = res.dropna(subset=["latitude", "longitude"])
geo = gpd.GeoDataFrame(geo, geometry=gpd.points_from_xy(geo.longitude, geo.latitude),
                       crs=CRS_WGS).to_crs(CRS_NYC)
geo["wx"] = geo.geometry.x * geo["unitsres"]
geo["wy"] = geo.geometry.y * geo["unitsres"]
w = geo.groupby("bct2020")[["wx", "wy", "unitsres"]].sum()
w["x"] = w["wx"] / w["unitsres"]
w["y"] = w["wy"] / w["unitsres"]
origins = tracts[["GEOID", "boroct2020", "geometry"]].merge(
    w[["x", "y"]], left_on="boroct2020", right_index=True, how="left")
fallback = origins["x"].isna()
rep = origins.geometry.representative_point()
origins["x"] = origins["x"].fillna(rep.x)
origins["y"] = origins["y"].fillna(rep.y)
origins = gpd.GeoDataFrame(origins[["GEOID"]].assign(
    origin_type=np.where(fallback, "representative_point", "unit_weighted")),
    geometry=gpd.points_from_xy(origins.x, origins.y), crs=CRS_NYC)
log(f"Origins: {len(origins)} ({fallback.sum()} use a polygon point, no residential lots)")

# ----------------------------------------------------------------------------
# 3. LODES — jobs per tract and job-weighted destination points
# ----------------------------------------------------------------------------
wac = pd.read_csv(RAW / "lodes" / "ny_wac_S000_JT00_2023.csv.gz",
                  usecols=["w_geocode", "C000"], dtype={"w_geocode": str})
xw = pd.read_csv(RAW / "lodes" / "ny_xwalk.csv.gz",
                 usecols=["tabblk2020", "trct", "blklatdd", "blklondd"],
                 dtype={"tabblk2020": str, "trct": str})
wac = wac.merge(xw, left_on="w_geocode", right_on="tabblk2020", how="left")
wac = wac[wac["trct"].str[2:5].isin(NYC_COUNTIES.keys())]
log(f"LODES 2023 NYC jobs: {wac['C000'].sum():,} in {len(wac):,} blocks")
bg = gpd.GeoDataFrame(wac, geometry=gpd.points_from_xy(wac.blklondd, wac.blklatdd),
                      crs=CRS_WGS).to_crs(CRS_NYC)
bg["wx"] = bg.geometry.x * bg["C000"]
bg["wy"] = bg.geometry.y * bg["C000"]
j = bg.groupby("trct")[["wx", "wy", "C000"]].sum()
j = j[j["C000"] > 0]
dest = gpd.GeoDataFrame({"GEOID": j.index, "jobs": j["C000"].values},
                        geometry=gpd.points_from_xy(j.wx / j.C000, j.wy / j.C000),
                        crs=CRS_NYC)
tracts = tracts.merge(dest[["GEOID", "jobs"]], on="GEOID", how="left")
tracts["jobs"] = tracts["jobs"].fillna(0)
log(f"Destination tracts with jobs: {len(dest)}  (jobs not matched to a DCP tract: "
    f"{dest.loc[~dest.GEOID.isin(tracts.GEOID), 'jobs'].sum():,})")

# ----------------------------------------------------------------------------
# 4. Location controls
# ----------------------------------------------------------------------------
cbd = gpd.GeoSeries(gpd.points_from_xy(*zip(*CBD_POINTS.values())),
                    crs=CRS_WGS).to_crs(CRS_NYC)
o = origins.set_index("GEOID").geometry
dist = np.column_stack([o.distance(p) for p in cbd]) / 5280.0     # miles
tracts = tracts.merge(pd.DataFrame({"GEOID": o.index,
                                    "dist_cbd_mi": dist.min(axis=1)}),
                      on="GEOID", how="left")

# ----------------------------------------------------------------------------
# 5. Save
# ----------------------------------------------------------------------------
out = PROC / "tracts_base.gpkg"
tracts.to_file(out, layer="tracts", driver="GPKG")
origins.to_file(out, layer="origins", driver="GPKG")
dest.to_file(out, layer="destinations", driver="GPKG")
(PROC / "01_build_log.txt").write_text(
    f"PLUTO version: {pluto_version}\n\n" + "\n".join(log_lines))
log(f"\nSaved {out}")
