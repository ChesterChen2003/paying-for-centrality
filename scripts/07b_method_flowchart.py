"""
Step 07b — Methodology flowchart (journal style).

Draws the study design from data to outputs: six sources, the tract-level
measures built from them, the three analysis streams (capitalization, spatial
equity, IBX scenario) with the links between them, and the outputs.
Double-column width (180 mm), Arial-metric sans serif, ≥ 6 pt at print size.

Outputs: outputs/figures/F0_methodology_flowchart.{pdf,svg,png,tif}
"""
import json
import re

import geopandas as gpd
import matplotlib as mpl
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

from config import FIG, PROC, TAB

F = json.loads((TAB / "facts.json").read_text())
JOBS_M = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts", ignore_geometry=True)["jobs"].sum() / 1e6

# ---- style -----------------------------------------------------------------------
FONT = "Liberation Sans"            # metric-compatible with Arial; SVG text asks for Arial first
mpl.rcParams.update({
    "font.family": FONT, "mathtext.fontset": "custom", "mathtext.rm": FONT,
    "mathtext.it": f"{FONT}:italic", "mathtext.bf": f"{FONT}:bold", "mathtext.sf": FONT,
    "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
})
PT = 25.4 / 72                      # mm per point
TS, BS, SS = 7.0, 6.2, 6.0          # title / body / small sizes (pt)
INK, INK2, MUTED = "#1d2125", "#3d4247", "#6b7178"
ARROW = "#3d4247"
LW = 0.55                           # box outline, pt
STY = {  # fill, stroke, header
    "data": ("#f3f3f1", "#8c8c88", None),
    "meas": ("#eef2f6", "#5f7286", None),
    "rq1": ("#eaf2fc", "#2a6fc2", "#2a6fc2"),
    "rq2": ("#fdf0e8", "#c9581f", "#c9581f"),
    "rq3": ("#e8f6ef", "#16865c", "#16865c"),
    "out": ("#ffffff", "#4a4f55", None),
}

W = 180.0                           # figure width, mm (double column)
X0, X1 = 10.0, 178.0                # content area (left strip holds stage labels)
PAD = 1.6                           # inner padding, mm
STEP_B, STEP_M = 1.32 * BS * PT, 1.62 * BS * PT   # line step: plain / with math


def line_step(s):
    return STEP_M if "$" in s and re.search(r"[_^]|\\frac|\\sum|\\hat", s) else STEP_B


def box_h(title, lines):
    return PAD + 1.25 * TS * PT + 0.6 + sum(line_step(s) for s in lines) + PAD - 0.4


# ---- layout ----------------------------------------------------------------------
data = [
    ("D1", "MTA GTFS", ["Subway + 6 bus feeds", "Schedules, Oct 2026"]),
    ("D2", "OpenStreetMap", ["Pedestrian network", "Rail right-of-way (IBX)"]),
    ("D3", "LEHD LODES 8", [f"Jobs by workplace block", f"$E_j$: {JOBS_M:.2f} M jobs, 2023"]),
    ("D4", "ACS 2020–24", ["5-year: gross rent, rent", "burden, poverty, tenure"]),
    ("D5", "PLUTO 26v2", ["Units, year built, class;", "NYCHA-owned lots"]),
    ("D6", "DCP boundaries", ["2020 census tracts", "and NTAs"]),
]
meas = [
    ("Analysis units", "D3, D5, D6", 37.0, [
        f"{F['tracts_all']} tracts ({F['tracts_sample']} in rent sample)",
        "Origins: residential-unit-",
        "weighted points",
        "Destinations: job-weighted points"]),
    ("Transit job accessibility", "D1–D3", 51.0, [
        "Conveyal R5 (r5py): walk + transit",
        "Tue 7–8 AM, median of 60 departures",
        "Walk 3 mph, ≤ 20 min per leg, ≤ 4 rides",
        r"$A_i=\Sigma_j\,E_j\,\mathbf{1}[t_{ij}\leq 45]$; also 30, 60 min, decay"]),
    ("Rent and housing controls", "D4, D5", 42.0, [
        r"$\ln\,R_i$: median gross rent (top-coded)",
        "Renter-stock age; rooms",
        "Pre-1974 6+ unit rental share",
        "NYCHA share; borough fixed effects"]),
    ("Renter vulnerability", "D4", 29.0, [
        r"$V_i$ = mean z-score of",
        "severe rent burden,",
        "poverty rate and",
        "renter share"]),
]
cols = [
    ("rq1", "RQ1  Capitalization", "Is transit job access priced into rent?", [
        ("Hedonic OLS (M1–M3)", [r"$\ln\,R_i=\beta\,\ln\,A_i+\mathbf{x}_i\gamma+\delta_b+\varepsilon_i$",
                                 "Controls added stepwise (M1 → M3)"]),
        ("Spatial diagnostics", ["Moran's I of OLS residuals", "LM and robust LM tests; KNN weights, k = 8"]),
        ("Spatial econometric models", ["Lag and error (ML); SAC (GMM, preferred)",
                                        r"$y=\rho Wy+X\beta+u,\;u=\lambda Wu+\varepsilon$",
                                        "Direct, indirect and total effects"]),
        ("Centrality decomposition", [r"$\ln\,A_i=\hat{f}_b(d_i)+e_i$,  $d_i$: distance to CBD",
                                      "Within-borough spline: location-",
                                      "predicted vs. excess access ($e_i$)"]),
        ("MGWR", ["Covariate-specific bandwidths",
                  r"Local access premium $\beta_1(u_i,v_i)$"]),
        ("Robustness", ["Variants of M3–M7: Tobit for top-coding;",
                        "ACS reliability filter; k = 4, 12 weights;",
                        "30/60 min and decay access; income and",
                        "distance controls; location models;",
                        "leave-one-borough-out; NTA level (MAUP)"]),
    ]),
    ("rq2", "RQ2  Spatial equity", "Where do access and rent diverge, for whom?", [
        ("Bivariate local Moran's I", [r"Access vs. spatially lagged rent",
                                       "999 permutations; FDR-adjusted"]),
        ("Planning typology", ["Access × rent at citywide medians,",
                               r"crossed with vulnerability $V_i$",
                               "Displacement watch · Service priority",
                               "· Established premium · Car-oriented",
                               "· Middle; NYCHA ≥ 50% kept apart"]),
    ]),
    ("rq3", "RQ3  IBX scenario", "Who would gain from the Interborough Express?", [
        ("Scenario network", ["18 stations sited on the Bay Ridge",
                              "Branch / Fremont Secondary (OSM)",
                              "Synthetic GTFS: 32 min, 5-min headways"]),
        ("Scenario routing", ["Same R5 settings as the baseline",
                              r"$\Delta\ln\,A_i$ for 45, 60 min and decay"]),
        ("Distribution of gains", ["Tracts gaining ≥ 5%: residents, renters",
                                   "by vulnerability quartile and type"]),
        ("Rent-pressure bracket", [r"$\Delta R_i/R_i=\exp(b\,\Delta\ln\,A_i)-1$",
                                   "b: excess access (low), SAC total",
                                   "(mid), local MGWR (high)"]),
        ("Precautionary screen", ["Gain ≥ 5%, local premium > 0,",
                                  "vulnerability ≥ median; no NYCHA"]),
    ]),
]
outs = {
    "rq1": ["Access elasticities (direct, total)", "Location vs. excess premium", "Local premium surface"],
    "rq2": ["Cluster and typology maps", "Renter households by type"],
    "rq3": ["Gain maps and equity shares", "Rent-pressure bounds", "Screened tracts and NTAs"],
}

# vertical positions
GAP_ROW, GAP_COL = 3.2, 6.0
y = 3.0
DATA_Y = y
data_h = max(box_h(t, l) for _, t, l in data)
y += data_h
BUS1_Y = y + 4.2
y = BUS1_Y + 4.6
MEAS_Y = y
meas_h = max(box_h(t, l) for t, _, _, l in meas) + STEP_B
y += meas_h
BUS2_Y = y + 4.2
y = BUS2_Y + 4.6
HEAD_Y, HEAD_H = y, 8.6
y += HEAD_H + 2.6
COL_Y = y
col_w = (X1 - X0 - 2 * GAP_COL) / 3
col_x = [X0 + i * (col_w + GAP_COL) for i in range(3)]

# RQ columns: stack boxes; RQ3 boxes 4–5 aligned with RQ1 boxes 4–5 where they link
pos = {}
for ci, (key, _, _, boxes) in enumerate(cols):
    yy = COL_Y
    for bi, (t, l) in enumerate(boxes):
        h = box_h(t, l)
        pos[(key, bi)] = [col_x[ci], yy, col_w, h]
        yy += h + GAP_ROW
for bi in (3, 4):                    # align rent-pressure / screen with decomposition / MGWR
    want = pos[("rq1", bi)][1]
    if pos[("rq3", bi)][1] < want:
        shift = want - pos[("rq3", bi)][1]
        for bj in range(bi, 5):
            pos[("rq3", bj)][1] += shift
COL_END = max(p[1] + p[3] for p in pos.values())
OUT_Y = COL_END + 6.0
out_h = max(box_h("Outputs", l) for l in outs.values())
NOTE_Y = OUT_Y + out_h + 3.0
NOTE_H = 6.2
H = NOTE_Y + NOTE_H + 2.5

# ---- drawing helpers ----------------------------------------------------------------
fig = plt.figure(figsize=(W / 25.4, H / 25.4))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.axis("off")
TEXTS = []


def text(x, y, s, size=BS, weight="normal", color=INK, **kw):
    t = ax.text(x, y, s, fontsize=size, fontweight=weight, color=color, **kw)
    TEXTS.append(t)
    return t


def draw_box(x, y, w, h, title, lines, kind, tag=None, dashed=False, foot=None):
    fill, stroke, _ = STY[kind]
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=fill, ec=stroke, lw=LW, ls=(0, (2.2, 1.4)) if dashed else "-",
                                joinstyle="round", zorder=2))
    text(x + PAD, y + PAD, title, size=TS, weight="bold", va="top", zorder=3)
    if tag:
        text(x + w - PAD, y + PAD + 0.15, tag, size=SS, color=MUTED, va="top", ha="right", zorder=3)
    yy = y + PAD + 1.25 * TS * PT + 0.6
    for s in lines:
        st = line_step(s)
        text(x + PAD, yy + (st - STEP_B) * 0.35, s, size=BS, color=INK2, va="top", zorder=3)
        yy += st
    if foot:
        text(x + PAD, y + h - PAD + 0.3, foot, size=SS, color=MUTED, va="bottom", zorder=3)
    return x, y, w, h


def arrow(x0, y0, x1, y1, dashed=False, z=4):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), zorder=z,
                arrowprops=dict(arrowstyle="-|>,head_length=0.32,head_width=0.16", lw=0.6,
                                color=ARROW, shrinkA=0, shrinkB=0,
                                ls=(0, (2.2, 1.4)) if dashed else "-"))


def poly(pts, dashed=False, head=True):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] if head else xs, ys[:-1] if head else ys, color=ARROW, lw=0.6,
            ls=(0, (2.2, 1.4)) if dashed else "-", solid_capstyle="butt", zorder=4)
    if head:
        arrow(xs[-2], ys[-2], xs[-1], ys[-1], dashed=dashed)


def dot(x, y):
    ax.plot([x], [y], "o", ms=1.6, color=ARROW, zorder=5)


# ---- stage bands -----------------------------------------------------------------
bands = [("Data", DATA_Y - 1.5, BUS1_Y), ("Measures", BUS1_Y + 2.4, BUS2_Y),
         ("Analysis", BUS2_Y + 2.4, COL_END + 1.5), ("Outputs", OUT_Y - 1.5, H - 1.0)]
for i, (lab, a, b) in enumerate(bands):
    if i:
        ax.plot([1.5, W - 1.5], [a - 1.4] * 2, color="#d9d9d5", lw=0.4, zorder=1)
    text(4.6, (a + b) / 2, lab, size=TS, weight="bold", color=MUTED, rotation=90,
         ha="center", va="center")

# data row
dw = (X1 - X0 - 5 * 2.6) / 6
for i, (tag, t, l) in enumerate(data):
    x = X0 + i * (dw + 2.6)
    draw_box(x, DATA_Y, dw, data_h, t, l, "data", tag=tag)
    ax.plot([x + dw / 2] * 2, [DATA_Y + data_h, BUS1_Y], color=ARROW, lw=0.6, zorder=1)
ax.plot([X0 + dw / 2, X1 - dw / 2], [BUS1_Y] * 2, color=ARROW, lw=0.6)
text((X0 + X1) / 2, BUS1_Y - 0.8, "Spatial join and aggregation to 2020 census tracts  ·  "
     "NAD83 / New York Long Island (EPSG:2263)", size=SS, color=MUTED, ha="center", va="bottom",
     bbox=dict(fc="white", ec="none", pad=0.6))

# measures row
gap_m = (X1 - X0 - sum(m[2] for m in meas)) / (len(meas) - 1)
x = X0
for t, tag, w, l in meas:
    arrow(x + w / 2, BUS1_Y, x + w / 2, MEAS_Y)
    draw_box(x, MEAS_Y, w, meas_h, t, l, "meas", foot=f"Inputs: {tag}")
    ax.plot([x + w / 2] * 2, [MEAS_Y + meas_h, BUS2_Y], color=ARROW, lw=0.6, zorder=1)
    x += w + gap_m
ax.plot([X0 + meas[0][2] / 2, X1 - meas[-1][2] / 2], [BUS2_Y] * 2, color=ARROW, lw=0.6)
text((X0 + X1) / 2, BUS2_Y - 0.8, f"Tract-level analysis dataset  ·  n = {F['tracts_all']} "
     f"(access), {F['tracts_sample']} (rent models)", size=SS, color=MUTED, ha="center",
     va="bottom", bbox=dict(fc="white", ec="none", pad=0.6))

# analysis columns
for ci, (key, head, q, boxes) in enumerate(cols):
    cx = col_x[ci]
    arrow(cx + col_w / 2, BUS2_Y, cx + col_w / 2, HEAD_Y)
    ax.add_patch(FancyBboxPatch((cx, HEAD_Y), col_w, HEAD_H, boxstyle="round,pad=0,rounding_size=0.9",
                                fc=STY[key][2], ec="none", zorder=2))
    text(cx + PAD, HEAD_Y + 1.35, head, size=TS + 0.4, weight="bold", color="white", va="top", zorder=3)
    text(cx + PAD, HEAD_Y + 1.35 + 1.3 * (TS + 0.4) * PT, q, size=BS, color="white", va="top", zorder=3)
    for bi, (t, l) in enumerate(boxes):
        bx, by, bw, bh = pos[(key, bi)]
        draw_box(bx, by, bw, bh, t, l, key, dashed=(key == "rq1" and t == "Robustness"))
        if bi == 0:
            arrow(cx + col_w / 2, HEAD_Y + HEAD_H, cx + col_w / 2, by)
        else:
            pb = pos[(key, bi - 1)]
            arrow(cx + col_w / 2, pb[1] + pb[3], cx + col_w / 2, by)

# cross-links into the IBX stream (white halo = line jump where they cross)
HALO = [pe.withStroke(linewidth=2.6, foreground="white")]
g1 = col_x[0] + col_w + GAP_COL * 0.5          # gap between RQ1 and RQ2
g2 = col_x[1] + col_w + GAP_COL * 0.5          # gap between RQ2 and RQ3
rq2_end = max(pos[("rq2", i)][1] + pos[("rq2", i)][3] for i in range(2))
sac, dec, mg = pos[("rq1", 2)], pos[("rq1", 3)], pos[("rq1", 4)]
rp, sc, dist = pos[("rq3", 3)], pos[("rq3", 4)], pos[("rq3", 2)]
y_rates, y_mg = dec[1] + dec[3] / 2, mg[1] + mg[3] / 2
assert y_rates > rq2_end + 2, "rate link would cross the RQ2 column"


def link(pts, head=True):
    xs, ys = zip(*pts)
    ax.plot(xs[:-1] + (xs[-1] - 0.6 * (xs[-1] > xs[-2]),) if head else xs, ys, color=ARROW, lw=0.6,
            solid_capstyle="butt", zorder=6, path_effects=HALO)
    if head:
        arrow(xs[-2], ys[-2], xs[-1], ys[-1], z=7)


y_rp1, y_rp2 = rp[1] + rp[3] * 0.36, rp[1] + rp[3] * 0.72
xa, xb = g2 - 1.0, g2 + 1.0
# SAC total effect + excess-access elasticity -> rent-pressure (low, mid)
link([(sac[0] + sac[2], sac[1] + sac[3] / 2), (g1, sac[1] + sac[3] / 2), (g1, y_rates)], head=False)
link([(dec[0] + dec[2], y_rates), (xa, y_rates), (xa, y_rp1), (rp[0], y_rp1)])
dot(g1, y_rates)
text((g1 + xa) / 2, y_rates - 0.7, "capitalization rates b (SAC total; excess access)", size=SS,
     color=MUTED, ha="center", va="bottom", style="italic", zorder=7,
     bbox=dict(fc="white", ec="none", pad=0.4))
# MGWR local premium -> rent-pressure (high) and screen
link([(mg[0] + mg[2], y_mg), (xb, y_mg)], head=False)
link([(xb, y_mg), (xb, y_rp2), (rp[0], y_rp2)])
link([(xb, y_mg), (xb, sc[1] + sc[3] / 2), (sc[0], sc[1] + sc[3] / 2)])
dot(xb, y_mg)
text((g1 + xa) / 2, y_mg - 0.7, "local access premium (MGWR)", size=SS, color=MUTED, ha="center",
     va="bottom", style="italic", zorder=7, bbox=dict(fc="white", ec="none", pad=0.4))
# tract type and vulnerability -> distribution of gains
ty = pos[("rq2", 1)]
lo, hi = max(ty[1], dist[1]) + 1.5, min(ty[1] + ty[3], dist[1] + dist[3]) - 1.5
if lo < hi:
    y_ty = (lo + hi) / 2
    link([(ty[0] + ty[2], y_ty), (dist[0], y_ty)])
else:
    y_ty = ty[1] + ty[3] / 2
    link([(ty[0] + ty[2], y_ty), (g2, y_ty), (g2, dist[1] + dist[3] / 2), (dist[0], dist[1] + dist[3] / 2)])

# outputs
for ci, (key, *_rest) in enumerate(cols):
    cx = col_x[ci]
    last = max((pos[(key, i)] for i in range(len(cols[ci][3]))), key=lambda p: p[1] + p[3])
    arrow(cx + col_w / 2, last[1] + last[3], cx + col_w / 2, OUT_Y)
    draw_box(cx, OUT_Y, col_w, out_h, "Outputs", outs[key], "out")
ax.add_patch(Rectangle((X0, NOTE_Y), X1 - X0, NOTE_H, fc="#f3f3f1", ec="none", zorder=1))
text(X0 + PAD, NOTE_Y + NOTE_H / 2, "Reproducibility:  every reported value is computed once into a "
     "single facts file that feeds the report, figures and interactive atlas; scripts 00–09 rerun "
     "the full pipeline.", size=SS, color=INK2, va="center")

# ---- checks and export --------------------------------------------------------------
fig.canvas.draw()
inv = ax.transData.inverted()
bad = []
for p in ax.patches:
    if not isinstance(p, FancyBboxPatch):
        continue
    bb = p.get_bbox()
    for t in TEXTS:
        e = t.get_window_extent()
        (ex0, ey1), (ex1, ey0) = inv.transform([[e.x0, e.y0], [e.x1, e.y1]])
        cx, cy = (ex0 + ex1) / 2, (ey0 + ey1) / 2
        if bb.x0 < cx < bb.x1 and bb.y0 < cy < bb.y1 and (ex1 > bb.x1 - 0.5 or ey1 > bb.y1 - 0.2):
            bad.append((t.get_text()[:40], round(ex1 - bb.x1, 2), round(ey1 - bb.y1, 2)))
if bad:
    print("Text overflow:", *bad, sep="\n  ")

out = FIG / "F0_methodology_flowchart"
fig.savefig(out.with_suffix(".pdf"))
fig.savefig(out.with_suffix(".png"), dpi=600)
fig.savefig(out.with_suffix(".tif"), dpi=600, pil_kwargs={"compression": "tiff_lzw"})
fig.savefig(out.with_suffix(".svg"))
svg = out.with_suffix(".svg")
svg.write_text(re.sub(r"font-family:\s*'Liberation Sans'",
                      "font-family: Arial, Helvetica, 'Liberation Sans', sans-serif", svg.read_text()))
print(f"Wrote {out}.pdf/.svg/.png/.tif ({W:.0f} × {H:.0f} mm)")
