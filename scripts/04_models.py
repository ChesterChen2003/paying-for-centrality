"""
Step 04 — Is transit job access capitalized into rents? Hedonic + spatial models.

Unit: census tract; y = ln(median gross rent).

A. Model ladder
   M1  OLS  ln_rent ~ ln_jobs45
   M2  OLS  + rental-stock controls (age, rooms, pre-1974 6+ unit share, NYCHA share)
   M3  OLS  + borough fixed effects
   M4  Spatial lag (ML) on M3            → direct / indirect / total effects (simulated SEs)
   M5  Spatial error (ML) on M3
B. Centrality vs. access
   Job access and distance to the CBD are two views of the same geography.
   "Excess access" = the part of ln_jobs45 not predicted by distance to the
   nearest CBD within the tract's borough — transit that is better or worse
   than a tract's location alone would deliver.
   M6  OLS  ln_rent ~ access_loc + excess_access + controls + borough FE
            (access_loc = access predicted by a within-borough distance spline)
   M7  Spatial error on M6
C. Robustness of the access elasticity (top-coding, reliability, cut-offs,
   leave-one-borough-out, NTA-level MAUP replication of the 2025 design)
D. MGWR: ln_rent ~ ln_jobs45 + controls, every coefficient with its own
   spatial scale (NYCHA share held global). With a local bandwidth, the access
   coefficient compares tracts that share a broad location.

Outputs: outputs/tables/04_*.csv, data/processed/access_decomposition.csv,
         data/processed/mgwr_local.gpkg, data/processed/04_models_log.txt
"""
import time
import warnings

import geopandas as gpd
import libpysal
import numpy as np
import pandas as pd
import spreg
from esda.moran import Moran
from patsy import dmatrix
from scipy import optimize, stats

from config import PROC, TAB, RENT_TOPCODE

warnings.filterwarnings("ignore")
t0 = time.time()
LOG = []
rng = np.random.default_rng(42)


def log(msg=""):
    print(msg, flush=True)
    LOG.append(str(msg))


# ----------------------------------------------------------------------------
# Data
# ----------------------------------------------------------------------------
tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
org = gpd.read_file(PROC / "tracts_base.gpkg", layer="origins")[["GEOID", "geometry"]]
s = tr[tr.in_sample].copy().reset_index(drop=True)
s["pt"] = s[["GEOID"]].merge(org, on="GEOID", how="left").geometry.values

s["age_dec"] = s["renter_age"] / 10                  # median rental-stock age, decades
s["rooms"] = s["renter_rooms_med"]                   # median rooms, renter-occupied units
s["pre74_6plus"] = s["pre74_6plus_share"]            # rent-stabilization proxy (share)
s["nycha"] = s["nycha_share"].fillna(0)              # public-housing unit share
CONTROLS = ["age_dec", "rooms", "pre74_6plus", "nycha"]
BORO = {"Bronx": "b_bx", "Brooklyn": "b_bk", "Queens": "b_qn",
        "Staten Island": "b_si"}                       # Manhattan = reference
for b, c in BORO.items():
    s[c] = (s["boroname"] == b).astype(float)
BFE = list(BORO.values())
ACCESS = "ln_jobs45"
s["ln_dist"] = np.log(s["dist_cbd_mi"])
log(f"Analysis sample: {len(s)} tracts; controls: {CONTROLS}")

# Spatial weights: 8 nearest neighbours between tract origin points, row-standardized
coords = np.column_stack([s.pt.x, s.pt.y])
W = libpysal.weights.KNN.from_array(coords, k=8, silence_warnings=True)
W.transform = "r"
y = s[["ln_rent"]].values

rows, fit = [], []


def ols(xvars, data=s, w=None, name=""):
    return spreg.OLS(data[["ln_rent"]].values, data[xvars].values, w=w,
                     spat_diag=w is not None, robust="white" if w is None else None,
                     name_y="ln_rent", name_x=xvars, name_ds=name)


def coef_table(m, label, xnames):
    stat = getattr(m, "z_stat", None) or getattr(m, "t_stat")
    return [{"model": label, "term": n, "coef": float(m.betas[i][0]),
             "se": float(m.std_err[i]), "stat": float(stat[i][0]), "p": float(stat[i][1])}
            for i, n in enumerate(["CONSTANT"] + xnames)]


def record_fit(label, m, resid, r2=None, extra=None):
    I = Moran(resid.flatten(), W, permutations=999)
    d = {"model": label, "n": m.n, "k": m.k, "r2": r2 if r2 is not None else m.r2,
         "aic": m.aic, "loglik": m.logll, "resid_moran_I": I.I, "resid_moran_p": I.p_sim}
    d.update(extra or {})
    fit.append(d)
    return I


# ----------------------------------------------------------------------------
# A. Model ladder
# ----------------------------------------------------------------------------
specs = {"M1 OLS: access only": [ACCESS],
         "M2 OLS: + rental stock": [ACCESS] + CONTROLS,
         "M3 OLS: + borough FE": [ACCESS] + CONTROLS + BFE}
ols_models = {}
for label, xv in specs.items():
    m = ols(xv, name=label)
    ols_models[label] = m
    rows += coef_table(m, label, xv)
    I = record_fit(label, m, m.u, extra={"adj_r2": m.ar2})
    log(f"{label}: b_access={m.betas[1][0]:.3f} (se {m.std_err[1]:.3f}), "
        f"R2={m.r2:.3f}, residual Moran's I={I.I:.3f} (p={I.p_sim:.3f})")

m3x = specs["M3 OLS: + borough FE"]
diag = ols(m3x, w=W, name="M3 diagnostics")
lm = pd.DataFrame({
    "test": ["LM-lag", "Robust LM-lag", "LM-error", "Robust LM-error", "LM-SARMA"],
    "stat": [diag.lm_lag[0], diag.rlm_lag[0], diag.lm_error[0], diag.rlm_error[0], diag.lm_sarma[0]],
    "p": [diag.lm_lag[1], diag.rlm_lag[1], diag.lm_error[1], diag.rlm_error[1], diag.lm_sarma[1]]})
lm.to_csv(TAB / "04_lm_tests.csv", index=False)
log("\nLagrange-multiplier tests on M3 residuals:\n" + lm.round(3).to_string(index=False))

X3 = s[m3x].values
slm = spreg.ML_Lag(y, X3, w=W, name_y="ln_rent", name_x=m3x, spat_impacts="simple")
rows += coef_table(slm, "M4 Spatial lag", m3x + ["rho"])
record_fit("M4 Spatial lag", slm, slm.u,
           r2=slm.pr2, extra={"rho_or_lambda": slm.rho})
# Impacts with simulated standard errors (draw beta, rho from their joint normal)
# Direct effect = beta * mean(diag((I - rho W)^-1)); total = beta / (1 - rho)
# for row-standardized W (LeSage & Pace 2009). SEs by simulation from the
# joint normal of (beta, rho).
Wd = W.full()[0]
Minv = np.linalg.inv(np.eye(len(s)) - slm.rho * Wd)
dfac = np.trace(Minv) / len(s)
draws = rng.multivariate_normal(slm.betas.flatten(), slm.vm, size=5000)
rho_d = draws[:, -1]
imp_rows = []
for i, n in enumerate(m3x, start=1):
    b = draws[:, i]
    tot = b / (1 - rho_d)
    direct = slm.betas[i][0] * dfac
    imp_rows.append({"term": n, "direct": float(direct),
                     "total": float(np.mean(tot)), "total_se": float(np.std(tot)),
                     "indirect": float(np.mean(tot) - direct)})
imp = pd.DataFrame(imp_rows)
imp.to_csv(TAB / "04_slm_impacts.csv", index=False)

sem = spreg.ML_Error(y, X3, w=W, name_y="ln_rent", name_x=m3x)
rows += coef_table(sem, "M5 Spatial error", m3x + ["lambda"])
record_fit("M5 Spatial error", sem, sem.e_filtered, r2=sem.pr2, extra={"rho_or_lambda": sem.lam})
ti = imp.loc[imp.term == ACCESS].iloc[0]
log(f"\nM4 SLM: b_access={slm.betas[1][0]:.3f}, rho={slm.rho:.3f}, AIC={slm.aic:.1f}; "
    f"total effect {ti.total:.3f} (se {ti.total_se:.3f})")
log(f"M5 SEM: b_access={sem.betas[1][0]:.3f} (se {sem.std_err[1]:.3f}), "
    f"lambda={sem.lam:.3f}, AIC={sem.aic:.1f}")

# ----------------------------------------------------------------------------
# B. Centrality vs. access
# ----------------------------------------------------------------------------
# Location model: within each borough, a natural cubic spline (4 df) in
# distance to the nearest CBD. Its prediction is the access a tract "should"
# have given where it sits; the residual is excess access (transit better or
# worse than location delivers). ln_jobs45 = access_loc + excess_access.
# Two less flexible location models are reported as robustness checks.
def spline(d, df):
    return np.asarray(dmatrix(f"cr(x, df={df}, constraints='center') - 1", {"x": d},
                              return_type="matrix"))


def fit_predict(Z, v):
    Z = np.column_stack([np.ones(len(v)), Z])
    b, *_ = np.linalg.lstsq(Z, v, rcond=None)
    return Z @ b


s["access_loc"] = np.nan
for bname, d in s.groupby("boroname"):
    s.loc[d.index, "access_loc"] = fit_predict(spline(d.dist_cbd_mi, 4), d[ACCESS].values)
s["excess_access"] = s[ACCESS] - s["access_loc"]
r2_c = 1 - s.excess_access.var() / s[ACCESS].var()
log(f"\nCorrelation ln_jobs45 vs ln distance to CBD: {s[[ACCESS, 'ln_dist']].corr().iat[0, 1]:.3f}; "
    f"within-borough distance splines explain {r2_c:.1%} of the variation in access")

m6x = ["access_loc", "excess_access"] + CONTROLS + BFE
m6 = ols(m6x, name="M6")
rows += coef_table(m6, "M6 OLS: location-predicted + excess access", m6x)
record_fit("M6 OLS: location-predicted + excess access", m6, m6.u, extra={"adj_r2": m6.ar2})
sem6 = spreg.ML_Error(y, s[m6x].values, w=W, name_y="ln_rent", name_x=m6x)
rows += coef_table(sem6, "M7 Spatial error: location-predicted + excess access", m6x + ["lambda"])
record_fit("M7 Spatial error: location-predicted + excess access", sem6, sem6.e_filtered,
           r2=sem6.pr2, extra={"rho_or_lambda": sem6.lam})
for lab, mm, st in [("M6 OLS", m6, m6.t_stat), ("M7 SEM", sem6, sem6.z_stat)]:
    log(f"{lab}: location-predicted access {mm.betas[1][0]:.3f} (se {mm.std_err[1]:.3f}); "
        f"excess access {mm.betas[2][0]:.3f} (se {mm.std_err[2]:.3f}, p={st[2][1]:.3f})")


# Alternative location models: residualize access, then regress rent on the
# residual + the full location basis + controls (plain least squares, HC1;
# pinv tolerates near-collinear basis columns that spreg's diagnostics reject)
def excess_premium(design):
    ex = s[ACCESS].values - fit_predict(design, s[ACCESS].values)
    X = np.column_stack([np.ones(len(s)), ex, design, s[CONTROLS].values])
    XtXi = np.linalg.pinv(X.T @ X)
    bb = XtXi @ X.T @ y[:, 0]
    e = y[:, 0] - X @ bb
    V = XtXi @ (X.T * e ** 2) @ X @ XtXi * len(s) / (len(s) - np.linalg.matrix_rank(X))
    return bb[1], float(np.sqrt(V[1, 1])), len(s)


alt_loc = {
    "citywide spline + borough": excess_premium(
        np.column_stack([spline(s.dist_cbd_mi, 5), s[BFE].values])),
    "log-quadratic distance + borough": excess_premium(
        np.column_stack([s.ln_dist, s.ln_dist ** 2, s[BFE].values])),
}
s[["GEOID", "dist_cbd_mi", "access_loc", "excess_access"]].to_csv(
    PROC / "access_decomposition.csv", index=False)

coef = pd.DataFrame(rows)
coef.to_csv(TAB / "04_coefficients.csv", index=False)
# keep the MGWR row written by 04b, if present, so the two steps can run in either order
_fit = pd.DataFrame(fit)
if (TAB / "04_model_fit.csv").exists():
    _old = pd.read_csv(TAB / "04_model_fit.csv")
    _fit = pd.concat([_fit, _old[_old.model.str.startswith("M8")]], ignore_index=True)
_fit.to_csv(TAB / "04_model_fit.csv", index=False)

# ----------------------------------------------------------------------------
# C. Robustness of the access elasticity (M3 spec unless noted)
# ----------------------------------------------------------------------------
def tobit(yv, X, cens):
    """Right-censored (top-coded) Tobit by maximum likelihood."""
    X = np.column_stack([np.ones(len(X)), X])
    b0 = np.linalg.lstsq(X, yv, rcond=None)[0]
    s0 = np.log(np.std(yv - X @ b0))

    def nll(theta):
        b, ls = theta[:-1], theta[-1]
        z = (yv - X @ b) / np.exp(ls)
        return -np.where(cens, stats.norm.logsf(z), stats.norm.logpdf(z) - ls).sum()

    r = optimize.minimize(nll, np.r_[b0, s0], method="BFGS")
    # standard errors from a central-difference Hessian at the optimum (the
    # BFGS inverse-Hessian approximation is not reliable for inference)
    th, k = r.x, len(r.x)
    H = np.zeros((k, k))
    h = 1e-4 * np.maximum(np.abs(th), 1.0)
    for i in range(k):
        for j in range(i, k):
            ei, ej = np.zeros(k), np.zeros(k)
            ei[i], ej[j] = h[i], h[j]
            H[i, j] = H[j, i] = (nll(th + ei + ej) - nll(th + ei - ej)
                                 - nll(th - ei + ej) + nll(th - ei - ej)) / (4 * h[i] * h[j])
    return th[1], float(np.sqrt(np.linalg.inv(H)[1, 1]))


rob = []


def add(group, label, b, se, n):
    rob.append({"group": group, "check": label, "b_access": b, "se": se,
                "ci_low": b - 1.96 * se, "ci_high": b + 1.96 * se, "n": n})


m = ols_models["M3 OLS: + borough FE"]
add("Model", "Baseline: M3 OLS with borough FE", m.betas[1][0], m.std_err[1], m.n)
add("Model", "Spatial lag (M4), total effect", ti.total, ti.total_se, slm.n)
add("Model", "Spatial error (M5)", sem.betas[1][0], sem.std_err[1], sem.n)
mm = ols_models["M1 OLS: access only"]
add("Model", "No controls (M1)", mm.betas[1][0], mm.std_err[1], mm.n)
d = s[~s.rent_topcoded]
mm = ols(m3x, data=d)
add("Rent data", f"Drop top-coded rents (${RENT_TOPCODE:,}+)", mm.betas[1][0], mm.std_err[1], mm.n)
bt, st = tobit(s["ln_rent"].values, s[m3x].values, s["rent_topcoded"].values)
add("Rent data", "Tobit: top-code as right-censored", bt, st, len(s))
d = s[s.rent_reliable]
mm = ols(m3x, data=d)
add("Rent data", "Drop low-reliability rents (CV > 0.30)", mm.betas[1][0], mm.std_err[1], mm.n)

# Spatial specification: other neighbour counts, and a combined lag + error (SAC) model
for kk in (4, 12):
    Wk = libpysal.weights.KNN.from_array(coords, k=kk, silence_warnings=True)
    Wk.transform = "r"
    mk = spreg.ML_Error(y, X3, w=Wk)
    add("Spatial specification", f"Spatial error, {kk} nearest neighbours", mk.betas[1][0], mk.std_err[1], mk.n)
sac = spreg.GM_Combo_Het(y, X3, w=W, name_x=m3x)
# SAC has a spatial-lag term, so its access coefficient is not the elasticity:
# report the direct (own-tract) and total (incl. spillover) effects, with SEs
# simulated from the joint distribution of (beta_access, rho)
rho_s = float(np.ravel(sac.rho)[0])
k_rho = len(m3x) + 1                                  # betas: const, X..., W_y, lambda
idx = [1, k_rho]
V2 = np.asarray(sac.vm)[np.ix_(idx, idx)]
dr = rng.multivariate_normal([sac.betas[1][0], rho_s], V2, size=5000)
Minv_s = np.linalg.inv(np.eye(len(s)) - rho_s * Wd)
dfac_s = np.trace(Minv_s) / len(s)
sac_direct = sac.betas[1][0] * dfac_s
sac_total = sac.betas[1][0] / (1 - rho_s)
direct_d = dr[:, 0] * dfac_s                           # trace factor held at the point estimate
total_d = dr[:, 0] / (1 - dr[:, 1])
add("Spatial specification", "SAC (lag + error, GMM), direct effect", sac_direct, float(np.std(direct_d)), sac.n)
add("Spatial specification", "SAC (lag + error, GMM), total effect", sac_total, float(np.std(total_d)), sac.n)
pd.DataFrame([{"model": "SAC (GM_Combo_Het)", "coef": sac.betas[1][0], "se": sac.std_err[1],
               "rho": rho_s, "lambda": float(sac.betas[-1][0]),
               "direct": sac_direct, "direct_se": float(np.std(direct_d)),
               "total": sac_total, "total_se": float(np.std(total_d))}]).to_csv(TAB / "04_sac_impacts.csv", index=False)
log(f"SAC (GM_Combo_Het): access coef {sac.betas[1][0]:.3f} (se {sac.std_err[1]:.3f}), rho={rho_s:.3f}, "
    f"lambda={float(sac.betas[-1][0]):.3f}; direct effect {sac_direct:.3f}, total effect {sac_total:.3f}")

# Building-age measure: ACS renter year built is bottom-coded at 1939 in ~30% of tracts
s["pluto_age_dec"] = s["pluto_age"] / 10
d = s.dropna(subset=["pluto_age_dec"])
xa = [ACCESS, "pluto_age_dec", "rooms", "pre74_6plus", "nycha"] + BFE
mm = ols(xa, data=d)
add("Rent data", "PLUTO building age instead of ACS renter age", mm.betas[1][0], mm.std_err[1], mm.n)
d = s[~s.renter_age_bottomcoded]
mm = ols(m3x, data=d)
add("Rent data", "Drop tracts with ACS year built bottom-coded", mm.betas[1][0], mm.std_err[1], mm.n)
for alt, lab in [("jobs_30", "30 min"), ("jobs_60", "60 min"), ("jobs_decay", "DECAY")]:
    s["_acc"] = np.log1p(s[alt] / 1000)
    mm = ols(["_acc"] + m3x[1:])
    name = "Decay-weighted jobs (30-min half-life)" if lab == "DECAY" else f"Jobs within {lab}"
    add("Access measure", name, mm.betas[1][0], mm.std_err[1], mm.n)
s["ln_inc"] = np.log(s["hh_income_med"])
d = s.dropna(subset=["ln_inc"])
mm = ols(m3x + ["ln_inc"], data=d)
add("Added control", "+ log median household income", mm.betas[1][0], mm.std_err[1], mm.n)
mm = ols(m3x + ["ln_dist"])
add("Centrality", "+ log distance to nearest CBD", mm.betas[1][0], mm.std_err[1], mm.n)
add("Centrality", "Excess access, within-borough spline (M6)", m6.betas[2][0], m6.std_err[2], m6.n)
add("Centrality", "Excess access, spatial error (M7)", sem6.betas[2][0], sem6.std_err[2], sem6.n)
for lab, (bb, se, nn) in alt_loc.items():
    add("Centrality", f"Excess access, {lab}", bb, se, nn)
for b in ["Manhattan"] + list(BORO):
    d = s[s.boroname != b]
    ref_drop = "b_bk" if b == "Manhattan" else BORO[b]   # keep one borough as reference
    xv = [ACCESS] + CONTROLS + [c for c in BFE if c != ref_drop]
    mm = ols(xv, data=d)
    add("Sample", f"Leave out {b}", mm.betas[1][0], mm.std_err[1], mm.n)

# NTA-level replication (MAUP): renter-weighted tract means within NTAs
g = s.assign(wt=s.renter_units)
nta = g.groupby("nta2020").apply(lambda x: pd.Series({
    "ln_rent": np.average(x.ln_rent, weights=x.wt),
    ACCESS: np.average(x[ACCESS], weights=x.wt),
    **{c: np.average(x[c], weights=x.wt) for c in CONTROLS},
    "boroname": x.boroname.iat[0]}), include_groups=False).reset_index()
for b, c in BORO.items():
    nta[c] = (nta.boroname == b).astype(float)
mm = ols([ACCESS], data=nta)
add("Scale (MAUP)", "NTA level, access only (2025 design)", mm.betas[1][0], mm.std_err[1], mm.n)
mm = ols(m3x, data=nta)
add("Scale (MAUP)", "NTA level, full M3 spec", mm.betas[1][0], mm.std_err[1], mm.n)

robdf = pd.DataFrame(rob)
robdf.to_csv(TAB / "04_robustness.csv", index=False)
log("\nRobustness of the access elasticity:\n" +
    robdf.drop(columns="group").round(3).to_string(index=False))

log(f"\nRuntime {time.time() - t0:.0f}s")
(PROC / "04_models_log.txt").write_text("\n".join(LOG))
