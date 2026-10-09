"""
Step 06c — IBX scenario effects: compare scenario access with the baseline,
and ask who gains (renter vulnerability, planning typology, neighbourhood).

Inputs: data/processed/ttm_ibx.parquet (06b), access_baseline.csv (02),
        equity.gpkg (05), tracts_analysis.gpkg (03)
Outputs: access_ibx.csv, ibx_effects.gpkg, outputs/tables/06_ibx_*.csv, log
"""
import geopandas as gpd
import numpy as np
import pandas as pd

from config import PROC, TAB

LOG = []


def log(m=""):
    print(m)
    LOG.append(str(m))


# cumulative_access lives in routing.py, which imports r5py on load; reuse the
# function without starting the JVM by loading only what we need
def cumulative_access(ttm, jobs, thresholds=(30, 45, 60)):
    t = ttm.merge(jobs.rename("jobs"), left_on="to_id", right_index=True)
    out = {f"jobs_{th}": t.loc[t.tt <= th].groupby("from_id")["jobs"].sum() for th in thresholds}
    beta = np.log(2) / 30.0
    t = t.dropna(subset=["tt"])
    out["jobs_decay"] = (t["jobs"] * np.exp(-beta * t["tt"])).groupby(t["from_id"]).sum()
    return pd.DataFrame(out).fillna(0)


base = PROC / "tracts_base.gpkg"
origins = gpd.read_file(base, layer="origins")
dest = gpd.read_file(base, layer="destinations")
ttm = pd.read_parquet(PROC / "ttm_ibx.parquet")
acc = cumulative_access(ttm, dest.set_index("GEOID")["jobs"]).reindex(origins["GEOID"]).fillna(0)
acc.index.name = "GEOID"
acc.to_csv(PROC / "access_ibx.csv")

# ---- compare with baseline -------------------------------------------------------
b = pd.read_csv(PROC / "access_baseline.csv", dtype={"GEOID": str}).set_index("GEOID")
d = acc.join(b, lsuffix="_ibx", rsuffix="_base")
for c in ["jobs_30", "jobs_45", "jobs_60", "jobs_decay"]:
    d[f"d_{c}"] = d[f"{c}_ibx"] - d[f"{c}_base"]
    d[f"pct_{c}"] = d[f"d_{c}"] / d[f"{c}_base"].replace(0, np.nan)

GAIN = 0.05          # a "meaningful" gain: at least +5% jobs reachable in 45 min

eq = gpd.read_file(PROC / "equity.gpkg", layer="equity")
tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
mg = gpd.read_file(PROC / "mgwr_local.gpkg", layer="mgwr")[["GEOID", "b_ln_jobs45", "sig_ln_jobs45"]]
g = (tr[["GEOID", "nta2020", "ntaname", "boroname", "pop", "renter_units", "in_sample", "geometry"]]
     .merge(d.reset_index(), on="GEOID", how="left")
     .merge(eq[["GEOID", "vulnerability", "typology", "rent", "burden50_share"]], on="GEOID", how="left")
     .merge(mg, on="GEOID", how="left"))
g["gain"] = g["pct_jobs_45"] >= GAIN
g["dln_access"] = np.log1p(g.jobs_45_ibx / 1000) - np.log1p(g.jobs_45_base / 1000)

# Illustrative rent pressure = capitalization rate x change in ln access.
# Cross-sectional rates describe how rents differ with access today; they are
# not a forecast. The IBX changes access without changing location, so three
# rates bracket the answer:
#   low  — the excess-access elasticity (M6): how today's market prices transit
#          that is better than a tract's location
#   mid  — the SAC total effect (own tract + spillovers), since gains are corridor-wide
#   high — each tract's local MGWR access coefficient (where significant),
#          converted back from standardized units
coef = pd.read_csv(TAB / "04_coefficients.csv")
rob = pd.read_csv(TAB / "04_robustness.csv")
b_excess = coef[coef.model.str.startswith("M6") & (coef.term == "excess_access")].coef.iat[0]
# corridor-wide gains: neighbours gain together, so the SAC total effect applies
b_sac = rob[rob.check.str.startswith("SAC (lag + error, GMM), total effect")].b_access.iat[0]
smp = tr[tr.in_sample]
sd_y, sd_x = smp.ln_rent.std(ddof=0), smp.ln_jobs45.std(ddof=0)
g["beta_local"] = np.where(g.sig_ln_jobs45.fillna(False).astype(bool),
                           g.b_ln_jobs45 * sd_y / sd_x, 0.0)
g["pressure_low_pct"] = np.expm1(b_excess * g.dln_access)
g["pressure_mid_pct"] = np.expm1(b_sac * g.dln_access)
g["pressure_local_pct"] = np.expm1(g.beta_local * g.dln_access)
log(f"Rent-pressure rates: excess-access {b_excess:.3f} (low), SAC {b_sac:.3f} (mid), "
    f"local MGWR where significant (high)")
g.to_file(PROC / "ibx_effects.gpkg", layer="ibx", driver="GPKG")

pw = lambda df, c: np.average(df[c].fillna(0), weights=df["pop"]) if df["pop"].sum() > 0 else np.nan
gg = g[g.gain]
log(f"\nTracts gaining >= {GAIN:.0%} in jobs within 45 min: {len(gg)} "
    f"(>= 10%: {(g.pct_jobs_45 >= 0.10).sum()}, >= 25%: {(g.pct_jobs_45 >= 0.25).sum()})")
log(f"Residents of those tracts: {gg['pop'].sum():,.0f}; renter households: {gg.renter_units.sum():,.0f}")
log(f"Population-weighted mean gain there: +{pw(gg, 'd_jobs_45'):,.0f} jobs "
    f"({pw(gg, 'pct_jobs_45'):.1%}); median tract +{gg.pct_jobs_45.median():.1%}")
# The 45-minute cut-off magnifies gains for tracts pushed across it; the 60-min
# and decay-weighted measures show the same tracts' gains without that cliff
log(f"Same tracts, other measures — median gain: jobs within 60 min "
    f"+{gg.pct_jobs_60.median():.1%}, decay-weighted +{gg.pct_jobs_decay.median():.1%}")
pd.DataFrame({"measure": ["jobs within 45 min", "jobs within 60 min", "decay-weighted jobs"],
              "median_pct_gain_in_gaining_tracts": [gg.pct_jobs_45.median(), gg.pct_jobs_60.median(),
                                                    gg.pct_jobs_decay.median()],
              "tracts_gaining_5pct": [int((g.pct_jobs_45 >= GAIN).sum()), int((g.pct_jobs_60 >= GAIN).sum()),
                                      int((g.pct_jobs_decay >= GAIN).sum())]}
             ).to_csv(TAB / "06_ibx_measures.csv", index=False)

# Who gains: renter vulnerability quartile and planning typology (sample tracts)
s = g[g.in_sample.astype(bool) & g.vulnerability.notna()].copy()
s["vul_q"] = pd.qcut(s.vulnerability, 4, labels=["Q1 (least)", "Q2", "Q3", "Q4 (most)"])


def who(x):
    xx = x[x.gain]
    return pd.Series({"tracts": len(x), "tracts_gaining_5pct": len(xx),
                      "share_gaining": len(xx) / len(x),
                      "renter_hh_in_gaining": xx.renter_units.sum(),
                      "pw_mean_pct_gain_all": pw(x, "pct_jobs_45")})


byq = s.groupby("vul_q", observed=True).apply(who, include_groups=False)
byq["share_of_all_sample_renter_hh"] = (s.groupby("vul_q", observed=True).renter_units.sum()
                                        / s.renter_units.sum())
byq["share_of_gaining_renter_hh"] = byq.renter_hh_in_gaining / byq.renter_hh_in_gaining.sum()
byq.to_csv(TAB / "06_ibx_by_vulnerability.csv")
top2 = byq.iloc[2:].sum()
log(f"Q3+Q4 share of renter households: {top2.share_of_gaining_renter_hh:.0%} in gaining tracts "
    f"vs {top2.share_of_all_sample_renter_hh:.0%} of all sample renter households")
bytype = s.groupby("typology").apply(who, include_groups=False)
bytype.to_csv(TAB / "06_ibx_by_typology.csv")
log("\nBy renter vulnerability quartile:\n" + byq.round(3).to_string())
log("\nBy typology:\n" + bytype.round(3).to_string())

# Where gains meet a market that already prices access (sample tracts)
sg = s[s.gain]
priced = sg[sg.beta_local > 0]
log(f"\nOf {len(sg)} gaining tracts in the rent sample, {len(priced)} "
    f"({len(priced) / max(len(sg), 1):.0%}) have a significant local access premium; "
    f"renter households {priced.renter_units.sum():,.0f}")
log(f"Illustrative rent pressure, median across gaining sample tracts: "
    f"low {sg.pressure_low_pct.median():.2%}, mid {sg.pressure_mid_pct.median():.2%}; "
    f"high (local MGWR, priced tracts only) {priced.pressure_local_pct.median():.1%} "
    f"(90th pct {priced.pressure_local_pct.quantile(.9):.1%})")
pd.DataFrame({"bound": ["low: excess-access elasticity", "mid: SAC total effect",
                        "high: local MGWR (priced tracts)"],
              "rate": [b_excess, b_sac, np.nan],
              "median_pct": [sg.pressure_low_pct.median(), sg.pressure_mid_pct.median(),
                             priced.pressure_local_pct.median()],
              "p90_pct": [sg.pressure_low_pct.quantile(.9), sg.pressure_mid_pct.quantile(.9),
                          priced.pressure_local_pct.quantile(.9)],
              "tracts": [len(sg), len(sg), len(priced)]}).to_csv(TAB / "06_ibx_pressure.csv", index=False)
# Precautionary screen: a gain, a local market that already prices access,
# above-median renter vulnerability, and not public-housing dominated
watch = sg[(sg.beta_local > 0) & (sg.vulnerability >= s.vulnerability.median())
           & ~sg.typology.astype(str).str.startswith("Public housing")]
log(f"Precautionary screen (gain + priced market + above-median vulnerability, excl. NYCHA-dominated): "
    f"{len(watch)} tracts, {watch.renter_units.sum():,.0f} renter households")
watch_nta = (watch.groupby(["boroname", "ntaname"]).agg(
    tracts=("GEOID", "size"), renter_hh=("renter_units", "sum"),
    median_gain=("pct_jobs_45", "median"), median_pressure_high=("pressure_local_pct", "median"),
    median_pressure_low=("pressure_low_pct", "median"))
    .sort_values("renter_hh", ascending=False))
watch_nta.to_csv(TAB / "06_ibx_watch_ntas.csv")
log(watch_nta.head(10).round(4).to_string())

# Largest gains by neighbourhood (populated tracts only)
top = (g[g.gain & (g["pop"] >= 500)].groupby(["boroname", "ntaname"])
       .apply(lambda x: pd.Series({"tracts": len(x), "residents": x["pop"].sum(),
                                   "pw_pct_gain": pw(x, "pct_jobs_45"),
                                   "pw_jobs_gain": pw(x, "d_jobs_45")}), include_groups=False)
       .query("residents >= 10000").sort_values("pw_pct_gain", ascending=False))
top.to_csv(TAB / "06_ibx_top_ntas.csv")
log("\nNeighbourhoods with the largest gains (>= 10,000 residents in gaining tracts):\n"
    + top.head(12).round(3).to_string())
(PROC / "06c_ibx_log.txt").write_text("\n".join(LOG))
