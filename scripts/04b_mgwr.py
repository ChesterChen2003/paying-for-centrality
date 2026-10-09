"""
Step 04b — MGWR: does the access–rent relationship vary across the city?

ln_rent ~ ln_jobs45 + rental-stock controls, each coefficient with its own
bandwidth (NYCHA share held global). With a local bandwidth the access
coefficient compares tracts that share a broad location, so it is read as the
local access premium net of regional centrality. ~20 min on 2 cores.

Outputs: data/processed/mgwr_local.gpkg, outputs/tables/04_mgwr_bandwidths.csv,
         appends M8 to outputs/tables/04_model_fit.csv, data/processed/04b_mgwr_log.txt
"""
import time
import warnings

import geopandas as gpd
import numpy as np
import pandas as pd
from mgwr.gwr import MGWR
from mgwr.sel_bw import Sel_BW

from config import PROC, TAB

warnings.filterwarnings("ignore")
t0 = time.time()
LOG = []


def log(msg=""):
    print(msg, flush=True)
    LOG.append(str(msg))


tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
org = gpd.read_file(PROC / "tracts_base.gpkg", layer="origins")[["GEOID", "geometry"]]
s = tr[tr.in_sample].copy().reset_index(drop=True)
pt = gpd.GeoSeries(s[["GEOID"]].merge(org, on="GEOID", how="left").geometry.values)
coords = np.column_stack([pt.x, pt.y])
s["age_dec"] = s["renter_age"] / 10
s["rooms"] = s["renter_rooms_med"]
s["pre74_6plus"] = s["pre74_6plus_share"]
s["nycha"] = s["nycha_share"].fillna(0)
ACCESS = "ln_jobs45"
y = s[["ln_rent"]].values
xv = [ACCESS, "age_dec", "rooms", "pre74_6plus", "nycha"]
Z = s[xv].values
Zs = (Z - Z.mean(0)) / Z.std(0)
ys = (y - y.mean()) / y.std()
n = len(s)
# bandwidth search bounds per term: intercept + 4 local terms ≥ 75 neighbours;
# NYCHA share is zero across whole districts, so it is held (near-)global
bw_min = [75, 75, 75, 75, 75, n - 1]
bw_max = [n - 1] * 6
log(f"\nMGWR on {n} tracts — selecting bandwidths ...")
sel = Sel_BW(coords, ys, Zs, multi=True, n_jobs=2)
# init_multi: start backfitting from a 600-neighbour GWR (smaller common
# bandwidths make the NYCHA column constant in some neighbourhoods)
bws = sel.search(multi_bw_min=bw_min, multi_bw_max=bw_max, init_multi=600, verbose=True)
mg = MGWR(coords, ys, Zs, sel, n_jobs=2).fit()
mg_names = ["Intercept"] + xv
bw_tab = pd.DataFrame({"term": mg_names, "bandwidth_nn": bws, "share_of_sample": np.asarray(bws) / n})
bw_tab.to_csv(TAB / "04_mgwr_bandwidths.csv", index=False)
crit_t = mg.critical_tval()
filt = mg.filter_tvals(critical_t=crit_t)
loc = s[["GEOID", "nta2020", "ntaname", "boroname", "geometry"]].copy()
for j, nm in enumerate(mg_names):
    loc[f"b_{nm}"] = mg.params[:, j]
    loc[f"t_{nm}"] = mg.tvalues[:, j]
    loc[f"sig_{nm}"] = filt[:, j] != 0
gpd.GeoDataFrame(loc, geometry="geometry", crs=s.crs).to_file(
    PROC / "mgwr_local.gpkg", layer="mgwr", driver="GPKG")
fitdf = pd.read_csv(TAB / "04_model_fit.csv")
fitdf = fitdf[~fitdf.model.str.startswith("M8")]
fitdf = pd.concat([fitdf, pd.DataFrame([{
    "model": "M8 MGWR (standardized)", "n": mg.n, "r2": mg.R2, "adj_r2": mg.adj_R2,
    "aicc_standardized": mg.aicc}])])          # not comparable with the AICs above
fitdf.to_csv(TAB / "04_model_fit.csv", index=False)
acc_b = loc[f"b_{ACCESS}"]
sig = loc[f"sig_{ACCESS}"]
log("MGWR bandwidths (nearest neighbours):\n" + bw_tab.round(3).to_string(index=False))
log(f"MGWR R2={mg.R2:.3f} (AICc {mg.aicc:.1f}); local access coefficient (standardized): "
    f"min {acc_b.min():.2f}, median {acc_b.median():.2f}, max {acc_b.max():.2f}; "
    f"significant in {sig.mean():.0%} of tracts (critical |t| = {crit_t[1]:.2f}); "
    f"significant & positive {((acc_b > 0) & sig).mean():.0%}, "
    f"significant & negative {((acc_b < 0) & sig).mean():.0%}")
bb = loc.assign(pos=(acc_b > 0) & sig, neg=(acc_b < 0) & sig).groupby("boroname")[["pos", "neg"]].mean()
bb.to_csv(TAB / "04_mgwr_by_borough.csv")
log("Share of tracts with a significant local access coefficient, by borough:\n" + bb.round(3).to_string())
log(f"\nRuntime {time.time() - t0:.0f}s")
(PROC / "04b_mgwr_log.txt").write_text("\n".join(LOG))
