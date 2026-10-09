"""
Step 05 — Where do transit access and rent diverge, and who lives there?

1. Bivariate local Moran's I (access vs. rent): tracts whose access is
   significantly high/low relative to their neighbours' rents.
2. Renter vulnerability index: mean z-score of severe rent burden (50%+),
   poverty rate, and renter share.
3. Planning typology (sample tracts, citywide medians as cut-points):
     Transit-rich, low-rent  + high vulnerability → "Displacement watch"
     Transit-poor, low-rent  + high vulnerability → "Service priority"
     Transit-rich, high-rent                      → "Established access premium"
     Transit-poor, high-rent                      → "Car-oriented / amenity premium"
     otherwise                                    → "Middle"
   Tracts where NYCHA owns at least half of the homes are classed separately
   ("Public housing"), because their rents are set by income.

Outputs: data/processed/equity.gpkg, outputs/tables/05_*.csv, log
"""
import geopandas as gpd
import libpysal
import numpy as np
import pandas as pd
from esda.moran import Moran_BV, Moran_Local_BV

from config import PROC, TAB

LOG = []


def log(m=""):
    print(m)
    LOG.append(str(m))


tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
org = gpd.read_file(PROC / "tracts_base.gpkg", layer="origins")[["GEOID", "geometry"]]
s = tr[tr.in_sample].copy().reset_index(drop=True)
pts = gpd.GeoSeries(s[["GEOID"]].merge(org, on="GEOID", how="left").geometry.values, crs=s.crs)
W = libpysal.weights.KNN.from_array(np.column_stack([pts.x, pts.y]), k=8)
W.transform = "r"

z = lambda v: (v - v.mean()) / v.std()
x = z(s["ln_jobs45"]).values
y = z(s["ln_rent"]).values

# --- 1. Bivariate LISA: access at i vs. spatially lagged rent ---------------
gbv = Moran_BV(x, y, W, permutations=999)
log(f"Global bivariate Moran's I (access vs. neighbours' rent): {gbv.I:.3f} (p={gbv.p_sim:.3f})")
lbv = Moran_Local_BV(x, y, W, permutations=999, seed=1)
lab = {1: "High access – High rent", 2: "Low access – High rent",
       3: "Low access – Low rent", 4: "High access – Low rent"}
s["bv_lisa"] = np.where(lbv.p_sim < 0.05, pd.Series(lbv.q).map(lab), "Not significant")
log(s["bv_lisa"].value_counts().to_string())
from esda import fdr  # noqa: E402
p_fdr = fdr(lbv.p_sim, 0.05)
s["bv_lisa_fdr"] = np.where(lbv.p_sim <= p_fdr, pd.Series(lbv.q).map(lab), "Not significant")
log(f"With a false-discovery-rate cut-off (p <= {p_fdr:.4f}):\n" + s["bv_lisa_fdr"].value_counts().to_string())

# --- 2. Renter vulnerability -------------------------------------------------
vul_vars = ["burden50_share", "poverty_rate", "renter_share"]
vz = s[vul_vars].apply(z)
s["vulnerability"] = vz.mean(axis=1, skipna=True)
s["vul_high"] = s["vulnerability"] >= s["vulnerability"].quantile(0.5)

# --- 3. Typology ---------------------------------------------------------------
acc_hi = s["ln_jobs45"] >= s["ln_jobs45"].median()
rent_hi = s["ln_rent"] >= s["ln_rent"].median()
# Tracts where most homes are NYCHA public housing get their own class: rents
# there are set by income, so market displacement does not apply
nycha_dom = s["nycha_share"].fillna(0) >= 0.5
s["typology"] = np.select(
    [nycha_dom,
     acc_hi & ~rent_hi & s.vul_high, ~acc_hi & ~rent_hi & s.vul_high,
     acc_hi & rent_hi, ~acc_hi & rent_hi],
    ["Public housing (NYCHA ≥ 50%)", "Displacement watch", "Service priority",
     "Established access premium", "Car-oriented / amenity premium"],
    default="Middle")

summ = s.groupby("typology").agg(
    tracts=("GEOID", "size"), renter_hh=("renter_units", "sum"), pop=("pop", "sum"),
    median_rent=("rent", "median"), median_jobs45=("jobs_45", "median"),
    burden50=("burden50_share", "median"), poverty=("poverty_rate", "median"),
    transit_commute=("transit_commute_share", "median"),
    nycha_share=("nycha_share", "mean")).round(3)
summ.to_csv(TAB / "05_typology_summary.csv")
log("\nTypology summary:\n" + summ.to_string())

# NTA roll-up for narrative: which neighbourhoods concentrate each priority type
nta = (s.groupby(["typology", "boroname", "ntaname"]).agg(
    tracts=("GEOID", "size"), renter_hh=("renter_units", "sum"))
    .reset_index().sort_values(["typology", "renter_hh"], ascending=[True, False]))
top = nta.groupby("typology").head(8)
top.to_csv(TAB / "05_typology_top_ntas.csv", index=False)
for t in ["Displacement watch", "Service priority", "Public housing (NYCHA ≥ 50%)"]:
    log(f"\n{t} — largest NTAs by renter households:\n" +
        top[top.typology == t][["boroname", "ntaname", "tracts", "renter_hh"]].to_string(index=False))

keep = ["GEOID", "nta2020", "ntaname", "boroname", "rent", "jobs_45", "ln_jobs45",
        "ln_rent", "burden50_share", "poverty_rate", "renter_share", "renter_units",
        "transit_commute_share", "nycha_share", "vulnerability", "bv_lisa", "bv_lisa_fdr", "typology",
        "geometry"]
s[keep].to_file(PROC / "equity.gpkg", layer="equity", driver="GPKG")
(PROC / "05_equity_log.txt").write_text("\n".join(LOG))
