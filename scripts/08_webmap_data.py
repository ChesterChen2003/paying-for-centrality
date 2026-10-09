"""
Step 08 — Compact data for the interactive web map.

Writes outputs/web/map_data.json and outputs/web/index.html (the page, with the
data inlined, from web/template.html). The JSON holds tract polygons (EPSG:2263, simplified to
~40 ft and rounded to 10 ft so the file stays small) with the attributes the
map shows, plus subway lines, the IBX corridor and the neighbouring land from
08a_context.py. The page draws them with
d3.geoIdentity, so no basemap tiles or projection library are needed.
"""
import json
import zipfile

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, box, mapping

from config import RAW, PROC, OUT, CRS_NYC

WEB = OUT / "web"
WEB.mkdir(parents=True, exist_ok=True)
Q = 10.0   # coordinate quantum, feet


def q(geom):
    """Round coordinates to Q feet, then express them in Q-foot units."""
    gj = mapping(geom)

    def rnd(c):
        if isinstance(c[0], (float, int)):
            return [int(round(c[0] / Q)), int(round(c[1] / Q))]
        return [rnd(x) for x in c]

    return {"type": gj["type"], "coordinates": rnd(gj["coordinates"])}


tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
eq = gpd.read_file(PROC / "equity.gpkg", layer="equity")[["GEOID", "typology", "vulnerability"]]
mg = gpd.read_file(PROC / "mgwr_local.gpkg", layer="mgwr")[["GEOID", "b_ln_jobs45", "sig_ln_jobs45"]]
ib = gpd.read_file(PROC / "ibx_effects.gpkg", layer="ibx")[["GEOID", "pct_jobs_45", "d_jobs_45"]]
dec = pd.read_csv(PROC / "access_decomposition.csv", dtype={"GEOID": str})[["GEOID", "excess_access"]]
d = (tr.merge(eq, on="GEOID", how="left").merge(mg, on="GEOID", how="left")
       .merge(ib, on="GEOID", how="left").merge(dec, on="GEOID", how="left"))
d = d[d["pop"] > 0].copy()          # drop parks, airports, cemeteries
d["geometry"] = d.geometry.simplify(40, preserve_topology=True)

TYPO = {"Displacement watch": 1, "Service priority": 2, "Established access premium": 3,
        "Car-oriented / amenity premium": 4, "Middle": 5, "Public housing (NYCHA ≥ 50%)": 6}


def r(v, k=0):
    return None if pd.isna(v) else (int(round(v)) if k == 0 else round(float(v), k))


feats = []
for _, x in d.iterrows():
    insample = bool(x.in_sample)
    feats.append({"type": "Feature", "geometry": q(x.geometry), "properties": {
        "id": x.GEOID, "nta": x.ntaname, "b": x.boroname,
        "pop": r(x["pop"]), "rh": r(x.renter_units),
        "j45": r(x.jobs_45), "j30": r(x.jobs_30), "j60": r(x.jobs_60),
        "rent": r(x.rent) if insample else None,
        "tc": bool(x.rent_topcoded) if insample else None,
        "bur": r(x.burden50_share, 3), "pov": r(x.poverty_rate, 3),
        "nycha": r(x.nycha_share, 3),
        "ex": r(x.excess_access, 3) if insample else None,
        "mg": r(x.b_ln_jobs45, 3) if insample and x.sig_ln_jobs45 == 1 else None,
        "mgs": None if not insample or pd.isna(x.sig_ln_jobs45) else bool(x.sig_ln_jobs45),
        "ty": TYPO.get(x.typology) if insample else None,
        "ibx": r(x.pct_jobs_45, 3), "ibxj": r(x.d_jobs_45),
    }})

# Subway: longest two shapes per route
with zipfile.ZipFile(RAW / "gtfs" / "gtfs_subway.zip") as z:
    shp = pd.read_csv(z.open("shapes.txt")).sort_values(["shape_id", "shape_pt_sequence"])
    trips = pd.read_csv(z.open("trips.txt"), usecols=["route_id", "shape_id"]).dropna()
lines = shp.groupby("shape_id").apply(
    lambda g: LineString(g[["shape_pt_lon", "shape_pt_lat"]].values), include_groups=False)
lines = gpd.GeoDataFrame(geometry=lines, crs="EPSG:4326").to_crs(CRS_NYC)
lines["len"] = lines.length
lines = lines.join(trips.drop_duplicates("shape_id").set_index("shape_id"))
lines = lines.sort_values("len").groupby("route_id").tail(2)
lines["geometry"] = lines.geometry.simplify(60)
subway = [{"type": "Feature", "geometry": q(g), "properties": {"r": rid}}
          for g, rid in zip(lines.geometry, lines.route_id)]

st = gpd.read_file(PROC / "ibx_corridor.gpkg", layer="stations").sort_values("order")
ibx_line = q(LineString([(p.x, p.y) for p in st.geometry]))
stations = [{"name": n, "xy": [int(round(p.x / Q)), int(round(p.y / Q))]}
            for n, p in zip(st.station, st.geometry)]

# Borough land (all tracts, incl. parks and airports): drawn as the city's base
# fill under the tracts and as the borough outline above them
borough = tr.dissolve("boroname").reset_index()
borough["geometry"] = borough.geometry.simplify(40)
boro = [{"type": "Feature", "geometry": q(g), "properties": {"b": b}}
        for g, b in zip(borough.geometry, borough.boroname)]

# Neighbouring land (08a_context.py) and basemap labels
ctx = gpd.read_file(PROC / "context_land.gpkg", layer="land")
ctx_geom = ctx.geometry.simplify(60).union_all()
CTX_BOX = (-74.60, 40.30, -73.40, 41.10)          # lon/lat window the map can pan over
ctx_box = gpd.GeoSeries([box(*CTX_BOX).segmentize(0.01)], crs="EPSG:4326").to_crs(CRS_NYC).iat[0]
ctx_geom = ctx_geom.intersection(ctx_box)


def edge(lon, lat):
    return gpd.GeoSeries(gpd.points_from_xy(lon, lat), crs="EPSG:4326").to_crs(CRS_NYC)


t_ = np.linspace(0, 1, 25)
lo_, la_ = CTX_BOX[0] + t_ * (CTX_BOX[2] - CTX_BOX[0]), CTX_BOX[1] + t_ * (CTX_BOX[3] - CTX_BOX[1])
ext = [int(v / Q) for v in (edge(np.full(25, CTX_BOX[0]), la_).x.max(),   # pan limit: largest
                            edge(lo_, np.full(25, CTX_BOX[1])).y.max(),   # rectangle inside
                            edge(np.full(25, CTX_BOX[2]), la_).x.min(),   # the projected box
                            edge(lo_, np.full(25, CTX_BOX[3])).y.min())]
LABELS = [  # name, lon, lat, kind, rotation (deg, screen)
    ("New Jersey", -74.185, 40.745, "land", 0), ("Westchester", -73.79, 40.926, "land", 0),
    ("Nassau", -73.635, 40.705, "land", 0),
    ("Hudson River", -73.993, 40.808, "water", -62), ("Upper Bay", -74.058, 40.662, "water", 0),
    ("Lower Bay", -74.04, 40.535, "water", 0), ("Atlantic Ocean", -73.86, 40.545, "water", 0),
    ("Long Island Sound", -73.715, 40.872, "water", 0),
]
lab_xy = gpd.GeoSeries(gpd.points_from_xy([l[1] for l in LABELS], [l[2] for l in LABELS]),
                       crs="EPSG:4326").to_crs(CRS_NYC)
labels = [{"t": l[0], "k": l[3], "r": l[4], "xy": [int(round(p.x / Q)), int(round(p.y / Q))]}
          for l, p in zip(LABELS, lab_xy)]

out = {"q": Q, "tracts": {"type": "FeatureCollection", "features": feats},
       "boroughs": {"type": "FeatureCollection", "features": boro},
       "context": q(ctx_geom), "labels": labels,
       "subway": {"type": "FeatureCollection", "features": subway},
       "ibx": {"line": ibx_line, "stations": stations},
       "meta": {"jobs_total": int(tr["jobs"].sum()), "tracts": len(feats),
                "sample": int(tr.in_sample.sum()), "ext": ext}}
p = WEB / "map_data.json"
p.write_text(json.dumps(out, separators=(",", ":")))
print(f"Wrote {p} ({p.stat().st_size / 1e6:.2f} MB, {len(feats)} tracts)")

# ---------------------------------------------------------------------------
# Facts: every number quoted in the page and the report, computed from the
# pipeline outputs so prose and results cannot drift apart
# ---------------------------------------------------------------------------
from config import TAB  # noqa: E402

T = lambda f: pd.read_csv(TAB / f)
coef, rob, typ = T("04_coefficients.csv"), T("04_robustness.csv"), T("05_typology_summary.csv")
mgb, bws = T("04_mgwr_by_borough.csv").set_index("boroname"), T("04_mgwr_bandwidths.csv").set_index("term")
byq, press, meas = T("06_ibx_by_vulnerability.csv"), T("06_ibx_pressure.csv"), T("06_ibx_measures.csv")
watch, top = T("06_ibx_watch_ntas.csv"), T("06_ibx_top_ntas.csv")
fitm = T("04_model_fit.csv")
ib = gpd.read_file(PROC / "ibx_effects.gpkg", layer="ibx")
mgl = gpd.read_file(PROC / "mgwr_local.gpkg", layer="mgwr")
smp = tr[tr.in_sample]
res = tr[tr["pop"] > 0]
cf = lambda m, t, c="coef": float(coef[coef.model.str.startswith(m) & (coef.term == t)][c].iat[0])
rb = lambda prefix, c="b_access": float(rob[rob.check.str.startswith(prefix)][c].iat[0])
tyr = typ.set_index("typology")
gain = ib[ib.pct_jobs_45 >= 0.05]
sg = ib[(ib.pct_jobs_45 >= 0.05) & ib.in_sample.astype(bool)]
q34 = byq.iloc[2:]
fmtM = lambda v: f"{v / 1e6:.2f}M"
AB = {"Bronx": "bx", "Brooklyn": "bk", "Manhattan": "mn", "Queens": "qn", "Staten Island": "si"}
fmtk = lambda v: f"{v / 1e3:,.0f}k"
pct0 = lambda v: "<1%" if 0 < v < 0.005 else f"{v * 100:.0f}%"
F = {
    "tracts_all": f"{len(tr):,}", "tracts_sample": f"{len(smp):,}",
    "pop_total_m": f"{tr['pop'].sum() / 1e6:.1f}",
    "share_1m": pct0(res.loc[res.jobs_45 >= 1e6, "pop"].sum() / res["pop"].sum()),
    "pw_jobs45": fmtM(np.average(res.jobs_45, weights=res["pop"])),
    **{f"med_j45_{AB[b]}": (fmtM(v) if v >= 1e6 else fmtk(v))
       for b, v in res.groupby("boroname").jobs_45.median().items()},
    "median_rent": f"${smp.rent.median():,.0f}",
    "n_topcoded": int(smp.rent_topcoded.sum()), "n_cv": int((~smp.rent_reliable).sum()),
    "b_m1": f"{cf('M1', 'ln_jobs45'):.3f}", "b_m2": f"{cf('M2', 'ln_jobs45'):.3f}",
    "b_m3": f"{cf('M3', 'ln_jobs45'):.3f}", "b_sem": f"{cf('M5', 'ln_jobs45'):.3f}",
    "b_sac": f"{rb('SAC (lag + error, GMM), direct'):.3f}", "se_sac": f"{rb('SAC (lag + error, GMM), direct', 'se'):.3f}",
    "b_sac_total": f"{rb('SAC (lag + error, GMM), total'):.3f}",
    "rho_sac": f"{float(T('04_sac_impacts.csv').rho.iat[0]):.2f}",
    "b_sac_coef": f"{float(T('04_sac_impacts.csv').coef.iat[0]):.3f}",
    "b_slm_total": f"{rb('Spatial lag (M4), total'):.3f}",
    "pct_10_m3": f"{(1.1 ** cf('M3', 'ln_jobs45') - 1) * 100:.1f}%",
    "pct_2x_sac": f"{(2 ** rb('SAC (lag + error, GMM), direct') - 1) * 100:.0f}%",
    "pct_2x_sac_total": f"{(2 ** rb('SAC (lag + error, GMM), total') - 1) * 100:.0f}%",
    "r2_m1": f"{fitm[fitm.model.str.startswith('M1')].r2.iat[0]:.2f}",
    "r2_m3": f"{fitm[fitm.model.str.startswith('M3')].r2.iat[0]:.2f}",
    "moran_m3": f"{fitm[fitm.model.str.startswith('M3')].resid_moran_I.iat[0]:.2f}",
    "nycha_pct": f"{(1 - np.exp(cf('M3', 'nycha'))) * 100:.0f}%",
    "b_pre74": f"{cf('M3', 'pre74_6plus'):.2f}",
    "b_loc": f"{cf('M6', 'access_loc'):.3f}", "b_excess": f"{cf('M6', 'excess_access'):.3f}",
    "p_excess": f"{cf('M6', 'excess_access', 'p'):.2f}",
    "b_excess_sem": f"{cf('M7', 'excess_access'):.3f}", "p_excess_sem": f"{cf('M7', 'excess_access', 'p'):.2f}",
    "excess_min": f"{rob[rob.check.str.startswith('Excess access')].b_access.min():.3f}",
    "excess_max": f"{rob[rob.check.str.startswith('Excess access')].b_access.max():.3f}",
    "loc_ratio": f"{cf('M6', 'access_loc') / max(cf('M6', 'excess_access'), 1e-9):.0f}",
    "b_dist": f"{rb('+ log distance'):.3f}",
    "b_drop_bottom": f"{rb('Drop tracts with ACS year built bottom-coded'):.3f}",
    "ci_drop_bottom": f"{rb('Drop tracts with ACS year built bottom-coded', 'ci_low'):.3f}–{rb('Drop tracts with ACS year built bottom-coded', 'ci_high'):.3f}",
    "n_bottom": int(smp.renter_age_bottomcoded.sum()),
    "bottom_j45": fmtM(smp.loc[smp.renter_age_bottomcoded, "jobs_45"].median()),
    "other_j45": fmtM(smp.loc[~smp.renter_age_bottomcoded, "jobs_45"].median()),
    "mgwr_r2": f"{float(fitm[fitm.model.str.startswith('M8')].r2.iat[0]):.2f}",
    "mgwr_bw": f"{bws.loc['ln_jobs45', 'bandwidth_nn']:.0f}",
    "mgwr_pos": pct0(((mgl.b_ln_jobs45 > 0) & mgl.sig_ln_jobs45.astype(bool)).mean()),
    "mgwr_neg": pct0(((mgl.b_ln_jobs45 < 0) & mgl.sig_ln_jobs45.astype(bool)).mean()),
    **{f"mgwr_{AB[b]}": pct0(mgb.loc[b, "pos"]) for b in mgb.index},
    **{f"mgwrneg_{AB[b]}": pct0(mgb.loc[b, "neg"]) for b in mgb.index},
    "dw_tracts": int(tyr.loc["Displacement watch", "tracts"]),
    "dw_hh": fmtk(tyr.loc["Displacement watch", "renter_hh"]),
    "dw_rent": f"${tyr.loc['Displacement watch', 'median_rent']:,.0f}",
    "dw_j45": fmtM(tyr.loc["Displacement watch", "median_jobs45"]),
    "dw_pov": pct0(tyr.loc["Displacement watch", "poverty"]),
    "sp_tracts": int(tyr.loc["Service priority", "tracts"]),
    "sp_hh": fmtk(tyr.loc["Service priority", "renter_hh"]),
    "sp_j45": fmtk(tyr.loc["Service priority", "median_jobs45"]),
    "sp_bur": pct0(tyr.loc["Service priority", "burden50"]),
    "ph_tracts": int(tyr.loc["Public housing (NYCHA ≥ 50%)", "tracts"]),
    "ph_hh": fmtk(tyr.loc["Public housing (NYCHA ≥ 50%)", "renter_hh"]),
    "ea_tracts": int(tyr.loc["Established access premium", "tracts"]),
    "co_tracts": int(tyr.loc["Car-oriented / amenity premium", "tracts"]),
    "mi_tracts": int(tyr.loc["Middle", "tracts"]),
    "ibx_tracts": f"{len(gain):,}", "ibx_tracts10": f"{(ib.pct_jobs_45 >= 0.10).sum():,}",
    "ibx_tracts25": f"{(ib.pct_jobs_45 >= 0.25).sum():,}",
    "ibx_pop": fmtM(gain["pop"].sum()), "ibx_rh": fmtk(gain.renter_units.sum()),
    "ibx_med": pct0(gain.pct_jobs_45.median()),
    "ibx_med60": pct0(float(meas.loc[meas.measure == "jobs within 60 min", "median_pct_gain_in_gaining_tracts"].iat[0])),
    "ibx_meddecay": pct0(float(meas.loc[meas.measure == "decay-weighted jobs", "median_pct_gain_in_gaining_tracts"].iat[0])),
    "ibx_q34": pct0(q34.share_of_gaining_renter_hh.sum()),
    "ibx_q34_base": pct0(q34.share_of_all_sample_renter_hh.sum()),
    "ibx_q4_avg": f"{byq.iloc[3].pw_mean_pct_gain_all * 100:.1f}%",
    "ibx_q1_avg": f"{byq.iloc[0].pw_mean_pct_gain_all * 100:.1f}%",
    "ibx_sample_gain": f"{len(sg):,}",
    "ibx_priced": f"{int(press.iloc[2].tracts):,}",
    "ibx_unpriced_share": pct0(1 - press.iloc[2].tracts / len(sg)),
    "press_low": f"{press.iloc[0].median_pct * 100:.2f}%", "press_mid": f"{press.iloc[1].median_pct * 100:.1f}%",
    "press_high": f"{press.iloc[2].median_pct * 100:.1f}%", "press_high90": f"{press.iloc[2].p90_pct * 100:.1f}%",
    "watch_tracts": f"{int(watch.tracts.sum()):,}",
    "watch_hh": fmtk(watch.renter_hh.sum()),
    "watch_ntas": ", ".join(watch.head(6).ntaname.tolist()),
}
# Share of access variation explained by location (sample tracts)
from patsy import dmatrix  # noqa: E402
sp = smp.reset_index(drop=True)


def r2(Z, v):
    Z = np.column_stack([np.ones(len(v)), Z])
    b, *_ = np.linalg.lstsq(Z, v, rcond=None)
    return 1 - np.var(v - Z @ b) / np.var(v)


spl = lambda d, df: np.asarray(dmatrix(f"cr(x, df={df}, constraints='center') - 1", {"x": d}))
pred = np.zeros(len(sp))
for _, d_ in sp.groupby("boroname"):
    Z = np.column_stack([np.ones(len(d_)), spl(d_.dist_cbd_mi, 4)])
    b_, *_ = np.linalg.lstsq(Z, d_.ln_jobs45.values, rcond=None)
    pred[d_.index] = Z @ b_
eqf = gpd.read_file(PROC / "equity.gpkg", layer="equity")
sem_k = rob[rob.check.str.startswith("Spatial error, ")].b_access
F.update({
    "r2_dist_alone": pct0(r2(spl(sp.dist_cbd_mi, 5), sp.ln_jobs45.values)),
    "r2_dist_within": pct0(1 - np.var(sp.ln_jobs45.values - pred) / np.var(sp.ln_jobs45.values)),
    "excess_share": pct0(cf("M6", "excess_access") / cf("M6", "access_loc")),
    "mgwr_cd": (lambda c: f"{int(np.floor(c))}–{int(np.ceil(c))}" if c % 1 > 0.25 else f"{c:.0f}")(
        bws.loc['ln_jobs45', 'bandwidth_nn'] / (len(tr) / 59)),
    "lisa_hl": int((eqf.bv_lisa == "High access – Low rent").sum()),
    "lisa_hl_fdr": int((eqf.bv_lisa_fdr == "High access – Low rent").sum()),
    "bottomcoded_share": pct0(smp.renter_age_bottomcoded.mean()),
    "sem_k_range": f"{sem_k.min():.3f}–{sem_k.max():.3f}",
})
(TAB / "facts.json").write_text(json.dumps(F, indent=1, default=str))
print(f"Wrote {TAB / 'facts.json'} ({len(F)} facts)")

# Render the self-contained page (data inlined) from the template
tpl = (OUT.parent / "web" / "template.html").read_text()
for k_, v_ in F.items():
    tpl = tpl.replace("{{" + k_ + "}}", str(v_))
missing = sorted(set(__import__("re").findall(r"\{\{(\w+)\}\}", tpl)))
if missing:
    raise SystemExit(f"template placeholders without a fact: {missing}")
html = tpl.replace("__DATA__", p.read_text())
(WEB / "index.html").write_text(html)
print(f"Wrote {WEB / 'index.html'} ({len(html) / 1e6:.2f} MB)")

# Standalone copy for GitHub Pages (Settings → Pages → main branch, /docs)
DOCS = OUT.parent / "docs"
DOCS.mkdir(exist_ok=True)
(DOCS / "index.html").write_text(
    '<!doctype html>\n<html lang="en" style="height:100%">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    '<meta name="description" content="Transit job access, rent and the Interborough Express across '
    'New York City census tracts. Wei Chen, Cornell MRP.">\n</head>\n'
    '<body style="margin:0;height:100%">\n' + html + "\n</body>\n</html>\n")
(DOCS / ".nojekyll").write_text("")
print(f"Wrote {DOCS / 'index.html'} (GitHub Pages)")
