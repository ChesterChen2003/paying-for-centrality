"""
Step 07 — Portfolio figures (PNG 300 dpi + PDF for InDesign/Illustrator).

Palette follows one rule per job: sequential = one hue light→dark (blue for
access, orange for rent), diverging = blue↔red with a gray midpoint,
categorical maps use at most three hues (others fold into neutral grays).
"""
import zipfile

import matplotlib.patheffects  # noqa: F401  (used via mpl.patheffects)

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import LineString

from config import RAW, PROC, FIG, TAB, CRS_NYC

# ---------------------------------------------------------------------------
# Style
# ---------------------------------------------------------------------------
mpl.rcParams.update({
    "font.family": "Inter", "font.size": 9, "axes.titlesize": 12,
    "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "axes.edgecolor": "#c3c2b7", "axes.labelcolor": "#52514e",
    "xtick.color": "#52514e", "ytick.color": "#52514e", "text.color": "#0b0b0b",
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "savefig.facecolor": "#fcfcfb", "pdf.fonttype": 42,
})
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8984"
NODATA, WATER_EDGE = "#e4e3df", "#b9b8b2"
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORANGE = ["#fde3d6", "#f9c3a8", "#f4a07a", "#eb6834", "#c9501f", "#9e3c14", "#6f290c"]
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#3987e5", "#cde2fb", "#f0efec",
                                                "#f9c9c8", "#e34948", "#8f1d1d"])
CAT3 = ["#2a78d6", "#eb6834", "#1baf7a"]
SRC = ("Sources: MTA GTFS (Oct 2026), OpenStreetMap, LEHD LODES 2023, "
       "ACS 2020–24 5-year, NYC DCP 2020 tracts, PLUTO 26v2. Analysis: Wei Chen.")


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(FIG / f"{name}.{ext}", dpi=300, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print("saved", name)


def base_ax(figsize=(7.2, 7.6)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_axis_off()
    return fig, ax


def frame(ax, gdf_all):
    gdf_all.plot(ax=ax, color=NODATA, linewidth=0)
    boro.boundary.plot(ax=ax, color=WATER_EDGE, linewidth=0.5)
    xmin, ymin, xmax, ymax = boro.total_bounds
    ax.set_xlim(xmin - 2000, xmax + 2000)
    ax.set_ylim(ymin - 2000, ymax + 2000)
    ax.set_autoscale_on(False)


def subway_overlay(ax, lw=0.45):
    subway.plot(ax=ax, color="#2b2b2a", linewidth=lw, alpha=0.75)


def scalebar_north(ax):
    (xmin, xmax), (ymin, ymax) = ax.get_xlim(), ax.get_ylim()
    x0, y0 = xmin + 0.66 * (xmax - xmin), ymin + 0.04 * (ymax - ymin)
    L = 5 * 5280                                   # 5 miles in feet
    ax.plot([x0, x0 + L], [y0, y0], color=INK, lw=1.2, solid_capstyle="butt")
    for xx in (x0, x0 + L / 2, x0 + L):
        ax.plot([xx, xx], [y0, y0 + 1200], color=INK, lw=0.8)
    ax.text(x0, y0 + 1700, "0", ha="center", fontsize=7, color=INK2)
    ax.text(x0 + L, y0 + 1700, "5 mi", ha="center", fontsize=7, color=INK2)
    nx, ny = xmin + 0.06 * (xmax - xmin), ymin + 0.90 * (ymax - ymin)
    ax.annotate("N", xy=(nx, ny + 5200), xytext=(nx, ny), ha="center", fontsize=9,
                fontweight="semibold", arrowprops=dict(arrowstyle="-|>", color=INK, lw=1))


def titles(ax, title, subtitle=None):
    """Title and subtitle stacked above the axes without overlapping."""
    ax.set_title("")
    ax.text(0, 1.045 if subtitle else 1.01, title, transform=ax.transAxes, fontsize=12,
            fontweight="semibold", color=INK, va="bottom", ha="left")
    if subtitle:
        ax.text(0, 1.01, subtitle, transform=ax.transAxes, fontsize=7.8, color=INK2,
                va="bottom", ha="left")


def footer(fig, text=SRC):
    fig.text(0.01, 0.005, text, fontsize=6.3, color=MUTED, ha="left", va="bottom")


def class_legend(ax, colors, labels, title, loc="upper left", extra=None):
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for c, l in zip(colors, labels)]
    if extra:
        handles += extra
    leg = ax.legend(handles=handles, title=title, loc=loc, frameon=True, fontsize=7.5,
                    facecolor="#fcfcfb", edgecolor="none", framealpha=0.92, borderpad=0.6,
                    title_fontsize=8, alignment="left", handlelength=1.2, handleheight=1.0,
                    bbox_to_anchor=(0.02, 0.86) if loc == "upper left" else None)
    leg.get_title().set_color(INK)
    for t in leg.get_texts():
        t.set_color(INK2)
    return leg


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
s = tr[tr.in_sample].copy()
boro = tr.dissolve("boroname").reset_index()

# Subway lines from GTFS shapes (longest shape per route)
with zipfile.ZipFile(RAW / "gtfs" / "gtfs_subway.zip") as z:
    shp = pd.read_csv(z.open("shapes.txt"))
    trips = pd.read_csv(z.open("trips.txt"), usecols=["route_id", "shape_id"]).dropna()
shp = shp.sort_values(["shape_id", "shape_pt_sequence"])
lines = shp.groupby("shape_id").apply(
    lambda d: LineString(d[["shape_pt_lon", "shape_pt_lat"]].values), include_groups=False)
lines = gpd.GeoDataFrame(geometry=lines, crs="EPSG:4326").to_crs(CRS_NYC)
lines["len"] = lines.length
lines = lines.join(trips.drop_duplicates("shape_id").set_index("shape_id"))
subway = lines.sort_values("len").groupby("route_id").tail(2)

# ---------------------------------------------------------------------------
# F1 — transit job access
# ---------------------------------------------------------------------------
fig, ax = base_ax()
frame(ax, tr)
v = tr["jobs_45"] / 1e6
brks = [0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, np.inf]
labels = ["< 0.25 M", "0.25–0.5 M", "0.5–1.0 M", "1.0–1.5 M", "1.5–2.0 M", "2.0–2.5 M", "≥ 2.5 M"]
cls = pd.cut(v, brks, labels=False, right=False)
tr.assign(c=cls).dropna(subset=["c"]).plot(ax=ax, column="c", cmap=ListedColormap(BLUE),
                                           vmin=-0.5, vmax=6.5, linewidth=0)
subway_overlay(ax)
total = tr["jobs"].sum()
titles(ax, "Jobs reachable by transit within 45 minutes",
       f"Weekday 7–8 AM departure, median of 60 departure minutes · "
        f"NYC total: {total / 1e6:.2f} M jobs")
class_legend(ax, BLUE, labels, "Jobs within 45 min",
             extra=[Line2D([], [], color="#2b2b2a", lw=0.8, label="Subway lines")])
scalebar_north(ax)
footer(fig)
save(fig, "F1_job_access_45min")

# ---------------------------------------------------------------------------
# F2 — median gross rent
# ---------------------------------------------------------------------------
fig, ax = base_ax()
frame(ax, tr)
rb = [0, 1250, 1500, 1750, 2000, 2500, 3000, np.inf]
rl = ["< $1,250", "$1,250–1,499", "$1,500–1,749", "$1,750–1,999", "$2,000–2,499",
      "$2,500–2,999", "$3,000+ (incl. top-coded)"]
cls = pd.cut(s["rent"], rb, labels=False, right=False)
s.assign(c=cls).plot(ax=ax, column="c", cmap=ListedColormap(ORANGE), vmin=-0.5, vmax=6.5, linewidth=0)
titles(ax, "Median gross rent",
       f"ACS 2020–24 5-year · {len(s):,} tracts with ≥ 50 renter households; "
        "gray = no estimate or too few renters")
class_legend(ax, ORANGE, rl, "Monthly rent + utilities")
scalebar_north(ax)
footer(fig)
save(fig, "F2_median_gross_rent")

# ---------------------------------------------------------------------------
# F3 — the pooled vs. within-borough relationship (small multiples)
# ---------------------------------------------------------------------------
order = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
fig, axes = plt.subplots(1, 6, figsize=(13, 2.9), sharey=True,
                         gridspec_kw={"width_ratios": [1.25, 1, 1, 1, 1, 1]})
xg = np.linspace(s.ln_jobs45.min(), s.ln_jobs45.max(), 50)
xt = np.log1p(np.array([25, 250, 2500]))
xtl = ["25k", "250k", "2.5M"]
yt = np.log([1000, 1500, 2000, 3000])
ytl = ["$1,000", "$1,500", "$2,000", "$3,000"]
b_all = np.polyfit(s.ln_jobs45, s.ln_rent, 1)
ax = axes[0]
ax.scatter(s.ln_jobs45, s.ln_rent, s=5, color=BLUE[3], alpha=0.35, linewidths=0)
ax.plot(xg, np.polyval(b_all, xg), color=INK, lw=1.6)
ax.set_title("All tracts (pooled)", fontsize=9.5)
ax.text(0.03, 0.95, f"slope {b_all[0]:.2f}", transform=ax.transAxes, fontsize=8, color=INK, va="top")
for ax, b in zip(axes[1:], order):
    d = s[s.boroname == b]
    ax.scatter(s.ln_jobs45, s.ln_rent, s=4, color="#d9d8d3", linewidths=0)
    ax.scatter(d.ln_jobs45, d.ln_rent, s=6, color=BLUE[4], alpha=0.6, linewidths=0)
    bb = np.polyfit(d.ln_jobs45, d.ln_rent, 1)
    xx = np.linspace(d.ln_jobs45.min(), d.ln_jobs45.max(), 20)
    ax.plot(xx, np.polyval(bb, xx), color=INK, lw=1.6)
    ax.set_title(b, fontsize=9.5)
    ax.text(0.03, 0.95, f"slope {bb[0]:.2f}  ·  n={len(d)}", transform=ax.transAxes,
            fontsize=8, color=INK, va="top")
for ax in axes:
    ax.set_xticks(xt, xtl)
    ax.set_yticks(yt, ytl)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(labelsize=7.5)
    ax.grid(color="#ecebe7", lw=0.5)
    ax.set_axisbelow(True)
axes[0].set_ylabel("Median gross rent (log scale)")
fig.supxlabel("Jobs reachable within 45 min by transit (log scale)", fontsize=8.5, color=INK2, y=-0.04)
fig.suptitle("One citywide slope, five different boroughs: access is priced in Manhattan and Brooklyn, not in the Bronx",
             x=0.01, ha="left", fontsize=12, fontweight="semibold", y=1.04)
save(fig, "F3_pooled_vs_within_borough")

# ---------------------------------------------------------------------------
# F4 — robustness of the access elasticity (forest plot, grouped)
# ---------------------------------------------------------------------------
rob = pd.read_csv(TAB / "04_robustness.csv")
# keep each group's rows together, groups in order of first appearance
rank = {g: i for i, g in enumerate(dict.fromkeys(rob.group))}
rob = rob.assign(_r=rob.group.map(rank)).sort_values("_r", kind="stable").reset_index(drop=True)
ypos, labels, ys_head = [], [], []
yv = 0
for grp, d in rob.groupby("group", sort=False):
    ys_head.append((yv, grp))
    yv += 1
    for _, r in d.iterrows():
        ypos.append(yv)
        labels.append(f"{r.check}  (n={r.n:,})")
        yv += 1
    yv += 0.4
rob["y"] = ypos
fig, ax = plt.subplots(figsize=(7.4, 0.26 * yv + 1.0))
ax.axvline(0, color=MUTED, lw=0.8)
b0 = rob.loc[rob.check.str.startswith("Baseline"), "b_access"].iat[0]
ax.axvline(b0, color=BLUE[3], lw=0.8, ls=(0, (3, 3)))
for _, r in rob.iterrows():
    base = r.check.startswith("Baseline")
    cen = r.group == "Centrality"
    col = ORANGE[3] if cen else (BLUE[5] if base else BLUE[3])
    if np.isfinite(r.se):
        ax.plot([r.ci_low, r.ci_high], [r.y, r.y], color=col, lw=2, solid_capstyle="round")
    ax.plot(r.b_access, r.y, "o", ms=6, color=col, mec="#fcfcfb", mew=1.2)
ax.set_yticks(rob.y, labels, fontsize=7.5)
for yh, g in ys_head:
    ax.text(-0.005, yh, g.upper(), transform=ax.get_yaxis_transform(), ha="right",
            fontsize=7, fontweight="semibold", color=INK, va="center")
ax.invert_yaxis()
ax.set_xlabel("Elasticity of median rent with respect to jobs reachable in 45 min (95% CI)")
ax.spines[["top", "right", "left"]].set_visible(False)
ax.tick_params(axis="y", length=0)
ax.grid(axis="x", color="#ecebe7", lw=0.5)
exc = rob[rob.check.str.startswith("Excess access")]
nsig = int(((exc.ci_low <= 0) & (exc.ci_high >= 0)).sum())
titles(ax, "Most of the access premium is a centrality premium",
       f"Dashed line = baseline ({b0:.3f}: doubling access ↔ ~{(2 ** b0 - 1) * 100:.0f}% higher rent). "
       f"Orange = centrality controls; access beyond what location predicts: {exc.b_access.min():.3f} "
       f"to {exc.b_access.max():.3f} ({nsig} of {len(exc)} intervals include zero).")
save(fig, "F4_robustness_forest")

# ---------------------------------------------------------------------------
# F5 — MGWR local access coefficient
# ---------------------------------------------------------------------------
mg = gpd.read_file(PROC / "mgwr_local.gpkg", layer="mgwr")
col = [c for c in mg.columns if c.startswith("b_ln_jobs")][0]
sig = col.replace("b_", "sig_")
fig, ax = base_ax()
frame(ax, tr)
lim = np.nanmax(np.abs(mg[col]))
mg[~mg[sig]].plot(ax=ax, color="#f0efec", linewidth=0)
mg[mg[sig]].plot(ax=ax, column=col, cmap=DIV, norm=TwoSlopeNorm(0, -lim, lim), linewidth=0)
subway_overlay(ax, lw=0.35)
titles(ax, "Where does transit access carry a rent premium?",
       "MGWR local coefficient on log(jobs within 45 min), standardized; "
        "light gray = not significant (corrected t-test)")
sm = plt.cm.ScalarMappable(cmap=DIV, norm=TwoSlopeNorm(0, -lim, lim))
cax = ax.inset_axes([0.04, 0.70, 0.26, 0.022])
cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
cb.outline.set_visible(False)
cb.ax.tick_params(labelsize=7)
cax.set_title("Local coefficient (− discount · + premium)", fontsize=7.5, loc="left", color=INK)
ax.legend(handles=[Patch(facecolor="#f0efec", edgecolor="#d6d5d0", lw=0.5, label="Not significant"),
                   Patch(facecolor=NODATA, edgecolor="none", label="Not in sample")],
          loc="upper left", bbox_to_anchor=(0.03, 0.665), frameon=False, fontsize=7.5)
scalebar_north(ax)
footer(fig)
save(fig, "F5_mgwr_local_access")

# ---------------------------------------------------------------------------
# F6 — planning typology
# ---------------------------------------------------------------------------
eq = gpd.read_file(PROC / "equity.gpkg", layer="equity")
cmap = {"Displacement watch": CAT3[1], "Service priority": CAT3[0],
        "Established access premium": CAT3[2],
        "Public housing (NYCHA ≥ 50%)": "#7d7c77",
        "Car-oriented / amenity premium": "#bdbcb6", "Middle": "#dedcd6"}
fig, ax = base_ax()
frame(ax, tr)
for k, c in cmap.items():
    d = eq[eq.typology == k]
    if len(d):
        d.plot(ax=ax, color=c, linewidth=0)
subway_overlay(ax, lw=0.35)
cnt = eq.typology.value_counts()
titles(ax, "Transit access, rent, and renter vulnerability",
       "Cut-points: citywide tract medians of access, rent, and vulnerability (severe rent burden, "
       "poverty, renter share); tracts mostly NYCHA-owned shown separately")
class_legend(ax, list(cmap.values()), [f"{k} ({cnt.get(k, 0)})" for k in cmap], "Tract type (count)")
scalebar_north(ax)
footer(fig)
save(fig, "F6_equity_typology")

# ---------------------------------------------------------------------------
# F8 — excess access: transit better / worse than location predicts
# ---------------------------------------------------------------------------
dec = pd.read_csv(PROC / "access_decomposition.csv", dtype={"GEOID": str})
ex = s.merge(dec[["GEOID", "excess_access"]], on="GEOID")
fig, ax = base_ax()
frame(ax, tr)
eb = [-np.inf, -0.75, -0.35, -0.10, 0.10, 0.35, 0.75, np.inf]
el = ["much worse (< −0.75)", "worse (−0.75 to −0.35)", "slightly worse", "as predicted (±0.10)",
      "slightly better", "better (0.35 to 0.75)", "much better (> 0.75)"]
DIV7 = ["#0d366b", "#3987e5", "#9ec5f4", "#f0efec", "#f6b3b2", "#e34948", "#8f1d1d"]
ex["c"] = pd.cut(ex.excess_access, eb, labels=False)
ex.plot(ax=ax, column="c", cmap=ListedColormap(DIV7), vmin=-0.5, vmax=6.5, linewidth=0)
subway_overlay(ax, lw=0.35)
titles(ax, "Transit access relative to location",
       "Residual of log(jobs within 45 min) after a within-borough spline in distance to the nearest CBD; "
        "red = more access than location alone delivers")
class_legend(ax, DIV7, el, "Access vs. location (log points)")
scalebar_north(ax)
footer(fig)
save(fig, "F8_excess_access")

# ---------------------------------------------------------------------------
# F7 — IBX scenario (only if step 06 has run)
# ---------------------------------------------------------------------------
ibx_path = PROC / "ibx_effects.gpkg"
if ibx_path.exists():
    ib = gpd.read_file(ibx_path, layer="ibx")
    stn = gpd.read_file(PROC / "ibx_corridor.gpkg", layer="stations")
    fig, ax = base_ax((7.2, 7.6))
    frame(ax, tr)
    gb = [0.05, 0.10, 0.25, 0.50, 1.00, np.inf]
    gl = ["+5–10%", "+10–25%", "+25–50%", "+50–100%", "more than doubles"]
    d = ib[(ib.pct_jobs_45 >= gb[0]) & (ib["pop"] >= 100)].copy()   # populated tracts only
    d["c"] = pd.cut(d.pct_jobs_45, gb, labels=False, right=False)
    d.plot(ax=ax, column="c", cmap=ListedColormap(BLUE[1:6]), vmin=-0.5, vmax=4.5, linewidth=0)
    subway_overlay(ax, lw=0.3)
    xs = np.column_stack([stn.geometry.x, stn.geometry.y])
    ax.plot(xs[:, 0], xs[:, 1], color=ORANGE[3], lw=2.2, zorder=5)
    ax.scatter(xs[:, 0], xs[:, 1], s=16, color="#fcfcfb", edgecolor=ORANGE[4], lw=1.2, zorder=6)
    for nm in ["Brooklyn Army Terminal", "Flatbush-Nostrand Av", "Atlantic Av", "Roosevelt Av"]:
        p = stn[stn.station == nm].geometry.iat[0]
        ax.text(p.x + 1500, p.y, nm, fontsize=7, color=INK, va="center",
                path_effects=[mpl.patheffects.withStroke(linewidth=2.5, foreground="#fcfcfb")])
    ax.set_xlim(975000, 1045000)
    ax.set_ylim(150000, 230000)
    titles(ax, "IBX scenario: change in jobs reachable within 45 minutes",
           "18 stations, 32 min end to end, 5-min peak headway (MTA public parameters); "
            "illustrative, station sites approximate")
    class_legend(ax, BLUE[1:6], gl, "Gain vs. today",
                 extra=[Line2D([], [], color=ORANGE[3], lw=2.2, marker="o", mfc="#fcfcfb",
                               mec=ORANGE[4], label="IBX (scenario)")])
    footer(fig)
    save(fig, "F7_ibx_access_gain")
