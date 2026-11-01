"""
Step 07c — Figure panels for the portfolio pages.

Same data and colours as 07_figures.py, drawn for placement on a 13.33 × 7.5 in
portfolio page: rendered at the exact size of their slot so type stays at 7–8 pt,
no titles or source lines (the page carries those), white water and grey
neighbouring land as in the web atlas.

Outputs: outputs/figures/portfolio/P*.png (300 dpi)
"""
import zipfile

import geopandas as gpd
import matplotlib as mpl
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import ListedColormap, TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import LineString, box

from config import RAW, PROC, FIG, CRS_NYC

OUT = FIG / "portfolio"
OUT.mkdir(parents=True, exist_ok=True)
FONT = "Liberation Sans"            # Arial metrics, matches the page type
mpl.rcParams.update({
    "font.family": FONT, "font.size": 7.5, "text.color": "#1d1d1f",
    "axes.edgecolor": "#bdbdb8", "axes.labelcolor": "#4a4a48", "xtick.color": "#4a4a48",
    "ytick.color": "#4a4a48", "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "pdf.fonttype": 42,
})
INK, INK2, MUTED = "#1d1d1f", "#4a4a48", "#8a8a86"
LAND, CITY, NODATA, EDGE = "#e7e7e4", "#f1f0ec", "#dedcd6", "#9a9a95"
BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
ORANGE = ["#fde3d6", "#f9c3a8", "#f4a07a", "#eb6834", "#c9501f", "#9e3c14", "#6f290c"]
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#3987e5", "#cde2fb", "#f0efec",
                                                "#f9c9c8", "#e34948", "#8f1d1d"])
DIV7 = ["#0d366b", "#3987e5", "#9ec5f4", "#f0efec", "#f6b3b2", "#e34948", "#8f1d1d"]
CAT = {"Displacement watch": "#eb6834", "Service priority": "#2a78d6",
       "Established access premium": "#1baf7a", "Public housing (NYCHA ≥ 50%)": "#7d7c77",
       "Car-oriented / amenity premium": "#bdbcb6", "Middle": "#dedcd6"}

# ---- data --------------------------------------------------------------------------
tr = gpd.read_file(PROC / "tracts_analysis.gpkg", layer="tracts")
s = tr[tr.in_sample].copy()
boro = tr.dissolve("boroname").reset_index()
ctx = gpd.read_file(PROC / "context_land.gpkg", layer="land")
with zipfile.ZipFile(RAW / "gtfs" / "gtfs_subway.zip") as z:
    shp = pd.read_csv(z.open("shapes.txt")).sort_values(["shape_id", "shape_pt_sequence"])
    trips = pd.read_csv(z.open("trips.txt"), usecols=["route_id", "shape_id"]).dropna()
lines = shp.groupby("shape_id").apply(
    lambda d: LineString(d[["shape_pt_lon", "shape_pt_lat"]].values), include_groups=False)
lines = gpd.GeoDataFrame(geometry=lines, crs="EPSG:4326").to_crs(CRS_NYC)
lines["len"] = lines.length
lines = lines.join(trips.drop_duplicates("shape_id").set_index("shape_id"))
subway = lines.sort_values("len").groupby("route_id").tail(2)


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=300)
    plt.close(fig)
    print("saved", name)


def map_panel(w, h, extent=None, pad=1500):
    """Axes filling a w × h in figure; NYC (or `extent`) fitted with the panel's aspect."""
    fig = plt.figure(figsize=(w, h))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_axis_off()
    x0, y0, x1, y1 = extent or boro.total_bounds
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    cx, cy, sx, sy = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
    if sx / sy > w / h:
        sy = sx * h / w
    else:
        sx = sy * w / h
    ax.set_xlim(cx - sx / 2, cx + sx / 2)
    ax.set_ylim(cy - sy / 2, cy + sy / 2)
    ax.set_autoscale_on(False)
    clip = box(cx - sx / 2, cy - sy / 2, cx + sx / 2, cy + sy / 2)
    ctx.clip(clip).plot(ax=ax, color=LAND, linewidth=0)
    tr.plot(ax=ax, color=CITY, linewidth=0)
    return fig, ax


def finish(ax, sub_lw=0.35, subway_on=True):
    boro.boundary.plot(ax=ax, color=EDGE, linewidth=0.45)
    if subway_on:
        subway.plot(ax=ax, color="#2b2b2a", linewidth=sub_lw, alpha=0.7)


def scalebar(ax, miles=5, where=(0.70, 0.045)):
    (xmin, xmax), (ymin, ymax) = ax.get_xlim(), ax.get_ylim()
    x0, y0 = xmin + where[0] * (xmax - xmin), ymin + where[1] * (ymax - ymin)
    L = miles * 5280
    ax.plot([x0, x0 + L], [y0, y0], color=INK, lw=0.9, solid_capstyle="butt")
    for xx in (x0, x0 + L):
        ax.plot([xx, xx], [y0, y0 + 0.008 * (ymax - ymin)], color=INK, lw=0.7)
    ax.text(x0 + L / 2, y0 + 0.014 * (ymax - ymin), f"{miles} mi", ha="center", va="bottom",
            fontsize=6.5, color=INK2)
    nx, ny = x0 + L + 0.05 * (xmax - xmin), y0
    ax.annotate("N", xy=(nx, ny + 0.055 * (ymax - ymin)), xytext=(nx, ny), ha="center",
                fontsize=7, fontweight="bold", arrowprops=dict(arrowstyle="-|>", color=INK, lw=0.8))


def legend(ax, colors, labels, title, extra=None, anchor=(0.025, 0.975)):
    handles = [Patch(facecolor=c, edgecolor="none", label=l) for c, l in zip(colors, labels)]
    leg = ax.legend(handles=handles + (extra or []), title=title, loc="upper left",
                    bbox_to_anchor=anchor, frameon=True, facecolor="white", edgecolor="none",
                    framealpha=0.9, fontsize=6.8, title_fontsize=7.2, alignment="left",
                    handlelength=1.3, handleheight=0.95, labelspacing=0.32, borderpad=0.55)
    leg.get_title().set_fontweight("bold")
    for t in leg.get_texts():
        t.set_color(INK2)
    return leg


MAP_W, MAP_H = 4.55, 4.95          # half-page map slot (in)

# ---- P1 transit job access -------------------------------------------------------------
fig, ax = map_panel(MAP_W, MAP_H)
cls = pd.cut(tr["jobs_45"] / 1e6, [0, 0.25, 0.5, 1.0, 1.5, 2.0, 2.5, np.inf], labels=False, right=False)
tr.assign(c=cls).dropna(subset=["c"]).plot(ax=ax, column="c", cmap=ListedColormap(BLUE),
                                           vmin=-0.5, vmax=6.5, linewidth=0)
finish(ax)
legend(ax, BLUE, ["< 0.25 M", "0.25–0.5 M", "0.5–1.0 M", "1.0–1.5 M", "1.5–2.0 M", "2.0–2.5 M", "≥ 2.5 M"],
       "Jobs within 45 min", extra=[Line2D([], [], color="#2b2b2a", lw=0.8, label="Subway")])
scalebar(ax)
save(fig, "P1_job_access")

# ---- P2 median gross rent ---------------------------------------------------------------
fig, ax = map_panel(MAP_W, MAP_H)
tr.plot(ax=ax, color=NODATA, linewidth=0)
cls = pd.cut(s["rent"], [0, 1250, 1500, 1750, 2000, 2500, 3000, np.inf], labels=False, right=False)
s.assign(c=cls).plot(ax=ax, column="c", cmap=ListedColormap(ORANGE), vmin=-0.5, vmax=6.5, linewidth=0)
finish(ax, subway_on=False)
legend(ax, ORANGE + [NODATA], ["< $1,250", "$1,250–1,499", "$1,500–1,749", "$1,750–1,999",
                               "$2,000–2,499", "$2,500–2,999", "$3,000+", "No estimate"],
       "Median gross rent")
scalebar(ax)
save(fig, "P2_rent")

# ---- P3 pooled vs within-borough slopes (3 × 2) ------------------------------------------
order = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
fig, axes = plt.subplots(2, 3, figsize=(5.95, 2.62), sharex=True, sharey=True)
fig.subplots_adjust(left=0.105, right=0.99, top=0.93, bottom=0.15, wspace=0.08, hspace=0.32)
xg = np.linspace(s.ln_jobs45.min(), s.ln_jobs45.max(), 50)
b_all = np.polyfit(s.ln_jobs45, s.ln_rent, 1)
for i, ax in enumerate(axes.flat):
    if i == 0:
        ax.scatter(s.ln_jobs45, s.ln_rent, s=2.5, color=BLUE[3], alpha=0.3, linewidths=0)
        ax.plot(xg, np.polyval(b_all, xg), color=INK, lw=1.2)
        ttl, txt = "All tracts", f"slope {b_all[0]:.2f}"
    else:
        b = order[i - 1]
        d = s[s.boroname == b]
        ax.scatter(s.ln_jobs45, s.ln_rent, s=2, color="#e0dfda", linewidths=0)
        ax.scatter(d.ln_jobs45, d.ln_rent, s=3, color=BLUE[4], alpha=0.55, linewidths=0)
        bb = np.polyfit(d.ln_jobs45, d.ln_rent, 1)
        xx = np.linspace(d.ln_jobs45.min(), d.ln_jobs45.max(), 20)
        ax.plot(xx, np.polyval(bb, xx), color=INK, lw=1.2)
        ttl, txt = b, f"slope {bb[0]:.2f}"
    ax.set_title(ttl, fontsize=7.5, fontweight="bold", loc="left", pad=2)
    ax.text(0.04, 0.93, txt, transform=ax.transAxes, fontsize=6.8, color=INK, va="top")
    ax.set_xticks(np.log1p(np.array([25, 250, 2500])), ["25k", "250k", "2.5M"])
    ax.set_yticks(np.log([1000, 2000, 3000]), ["$1k", "$2k", "$3k"])
    ax.tick_params(labelsize=6.5, length=2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(color="#efeeea", lw=0.4)
    ax.set_axisbelow(True)
fig.text(0.01, 0.54, "Median gross rent (log)", rotation=90, va="center", fontsize=6.8, color=INK2)
fig.text(0.55, 0.01, "Jobs within 45 min by transit (log)", ha="center", fontsize=6.8, color=INK2)
save(fig, "P3_slopes")

# ---- P4 excess access ------------------------------------------------------------------
dec = pd.read_csv(PROC / "access_decomposition.csv", dtype={"GEOID": str})
ex = s.merge(dec[["GEOID", "excess_access"]], on="GEOID")
fig, ax = map_panel(MAP_W, MAP_H)
tr.plot(ax=ax, color=NODATA, linewidth=0)
ex["c"] = pd.cut(ex.excess_access, [-np.inf, -0.75, -0.35, -0.10, 0.10, 0.35, 0.75, np.inf], labels=False)
ex.plot(ax=ax, column="c", cmap=ListedColormap(DIV7), vmin=-0.5, vmax=6.5, linewidth=0)
finish(ax, sub_lw=0.3)
legend(ax, DIV7, ["Much worse (< −0.75)", "Worse", "Slightly worse", "As predicted (±0.10)",
                  "Slightly better", "Better", "Much better (> 0.75)"],
       "Access vs. location (log pts)")
scalebar(ax)
save(fig, "P4_excess_access")

# ---- P5 MGWR local premium --------------------------------------------------------------
mg = gpd.read_file(PROC / "mgwr_local.gpkg", layer="mgwr")
col = [c for c in mg.columns if c.startswith("b_ln_jobs")][0]
sig = col.replace("b_", "sig_")
fig, ax = map_panel(MAP_W, MAP_H)
tr.plot(ax=ax, color=NODATA, linewidth=0)
lim = np.nanmax(np.abs(mg[col]))
mg[~mg[sig]].plot(ax=ax, color="#f0efec", linewidth=0)
mg[mg[sig]].plot(ax=ax, column=col, cmap=DIV, norm=TwoSlopeNorm(0, -lim, lim), linewidth=0)
finish(ax, sub_lw=0.3)
sm = plt.cm.ScalarMappable(cmap=DIV, norm=TwoSlopeNorm(0, -lim, lim))
cax = ax.inset_axes([0.045, 0.875, 0.30, 0.018])
cb = fig.colorbar(sm, cax=cax, orientation="horizontal")
cb.outline.set_visible(False)
cb.ax.tick_params(labelsize=6.5, length=2)
cax.set_title("Local access coefficient", fontsize=7.2, fontweight="bold", loc="left", pad=3)
ax.legend(handles=[Patch(facecolor="#f0efec", edgecolor="#cfcec9", lw=0.4, label="Not significant"),
                   Patch(facecolor=NODATA, edgecolor="none", label="Not in sample")],
          loc="upper left", bbox_to_anchor=(0.035, 0.835), frameon=False, fontsize=6.8,
          handlelength=1.3, handleheight=0.95, labelspacing=0.32)
scalebar(ax)
save(fig, "P5_mgwr")

# ---- P6 typology (legend lives in the page table) ------------------------------------------
eq = gpd.read_file(PROC / "equity.gpkg", layer="equity")
fig, ax = map_panel(3.55, MAP_H)
for k, c in CAT.items():
    d = eq[eq.typology == k]
    if len(d):
        d.plot(ax=ax, color=c, linewidth=0)
finish(ax, sub_lw=0.3)
scalebar(ax, where=(0.62, 0.04))
save(fig, "P6_typology")

# ---- P7 IBX scenario -------------------------------------------------------------------
ib = gpd.read_file(PROC / "ibx_effects.gpkg", layer="ibx")
stn = gpd.read_file(PROC / "ibx_corridor.gpkg", layer="stations").sort_values("order")
fig, ax = map_panel(4.4, 4.95, extent=(966000, 150000, 1040000, 226000), pad=0)
gb = [0.05, 0.10, 0.25, 0.50, 1.00, np.inf]
d = ib[(ib.pct_jobs_45 >= gb[0]) & (ib["pop"] >= 100)].copy()
d["c"] = pd.cut(d.pct_jobs_45, gb, labels=False, right=False)
d.plot(ax=ax, column="c", cmap=ListedColormap(BLUE[1:6]), vmin=-0.5, vmax=4.5, linewidth=0)
finish(ax, sub_lw=0.3)
xs = np.column_stack([stn.geometry.x, stn.geometry.y])
ax.plot(xs[:, 0], xs[:, 1], color=ORANGE[3], lw=2.0, zorder=5, solid_capstyle="round")
ax.scatter(xs[:, 0], xs[:, 1], s=11, color="white", edgecolor=ORANGE[4], lw=1.0, zorder=6)
halo = [pe.withStroke(linewidth=2.2, foreground="white")]
for nm, dx, dy, ha in [("Brooklyn Army Terminal", -1500, 2000, "left"), ("Flatbush-Nostrand Av", 1300, 0, "left"),
                       ("Atlantic Av", 1300, 0, "left"), ("Roosevelt Av", 1300, 0, "left")]:
    p = stn[stn.station == nm].geometry.iat[0]
    ax.text(p.x + dx, p.y + dy, nm, fontsize=6.8, color=INK, va="center", ha=ha, path_effects=halo, zorder=7)
legend(ax, BLUE[1:6], ["+5–10%", "+10–25%", "+25–50%", "+50–100%", "More than doubles"],
       "Gain in jobs within 45 min",
       extra=[Line2D([], [], color=ORANGE[3], lw=2.0, marker="o", ms=3.5, mfc="white",
                     mec=ORANGE[4], label="IBX (scenario)")])
scalebar(ax, miles=2, where=(0.70, 0.04))
save(fig, "P7_ibx")
