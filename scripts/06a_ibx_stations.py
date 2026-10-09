"""
Step 06a — Locate the 18 proposed IBX stations on the rail corridor.

The MTA has published station names and connecting lines but not coordinates
("exact station locations subject to change"). We place each station where
its named cross street meets the Bay Ridge Branch / Fremont Secondary in
OpenStreetMap, so the scenario follows the real right-of-way.

Station list: MTA IBX project map (ibx.mta.info/map), 18 stations, south→north.

Outputs (data/processed):
  ibx_corridor.gpkg   layers "rail" (corridor line) and "stations" (EPSG:2263)
"""
import re

import geopandas as gpd
import numpy as np
import osmium
import pandas as pd
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, unary_union, nearest_points

from config import RAW, PROC, CRS_NYC, CRS_WGS

OSM = RAW / "osm" / "nyc.osm.pbf"   # full extract: needs rail lines, not just streets

# name, regex for the OSM street name(s) that define the station, and an
# approximate location (lon, lat) used only to pick the right crossing when a
# street crosses the corridor more than once.
STATIONS = [
    ("Brooklyn Army Terminal", None,                         (-74.0225, 40.6440)),
    ("4 Av",                   r"^4th Avenue$",              (-74.0205, 40.6380)),
    ("8 Av",                   r"^8th Avenue$",              (-74.0117, 40.6350)),
    ("New Utrecht Av",         r"^New Utrecht Avenue$",      (-73.9966, 40.6262)),
    ("McDonald Av",            r"^McDonald Avenue$",         (-73.9765, 40.6275)),
    ("E 16 St",                r"^East 16th Street$",        (-73.9610, 40.6275)),
    ("Flatbush-Nostrand Av",   r"^(Flatbush|Nostrand) Avenue$", (-73.9476, 40.6326)),
    ("Utica Av",               r"^Utica Avenue$",            (-73.9290, 40.6375)),
    ("Remsen Av",              r"^Remsen Avenue$",           (-73.9170, 40.6460)),
    ("Linden Blvd",            r"^Linden Boulevard$",        (-73.8990, 40.6570)),
    ("Livonia Av",             r"^Livonia Avenue$",          (-73.9010, 40.6640)),
    ("Atlantic Av",            r"^Atlantic Avenue$",         (-73.9030, 40.6770)),
    ("Wilson Av",              r"^Wilson Avenue$",           (-73.9043, 40.6889)),
    ("Myrtle Av",              r"^Myrtle Avenue$",           (-73.8980, 40.7000)),
    ("Metropolitan Av",        r"^Metropolitan Avenue$",     (-73.8894, 40.7116)),
    ("Eliot Av",               r"^Eliot Avenue$",            (-73.8900, 40.7225)),
    ("Grand Av",               r"^Grand Avenue$",            (-73.8950, 40.7290)),
    ("Roosevelt Av",           r"^Roosevelt Avenue$",        (-73.8945, 40.7460)),
]


class Collector(osmium.SimpleHandler):
    """Collect railway lines and the named streets we need."""

    def __init__(self, street_re):
        super().__init__()
        self.street_re = street_re
        self.rail, self.streets = [], []
        self.wkb = osmium.geom.WKBFactory()

    def way(self, w):
        tags = w.tags
        try:
            if tags.get("railway") in ("rail", "disused", "abandoned") and \
                    tags.get("usage", "") != "industrial_spur":
                self.rail.append((w.id, tags.get("name", ""), tags.get("railway"),
                                  tags.get("service", ""), self._line(w)))
            elif "highway" in tags and self.street_re.search(tags.get("name", "")):
                self.streets.append((w.id, tags.get("name"), self._line(w)))
        except Exception:
            pass

    @staticmethod
    def _line(w):
        return LineString([(n.lon, n.lat) for n in w.nodes])


street_re = re.compile("|".join(s[1] for s in STATIONS if s[1]))
h = Collector(street_re)
h.apply_file(str(OSM), locations=True)
rail = gpd.GeoDataFrame(h.rail, columns=["osm_id", "name", "railway", "service", "geometry"],
                        crs=CRS_WGS).to_crs(CRS_NYC)
streets = gpd.GeoDataFrame(h.streets, columns=["osm_id", "name", "geometry"],
                           crs=CRS_WGS).to_crs(CRS_NYC)
print(f"Rail ways: {len(rail)}, named-street ways: {len(streets)}")
print(rail[rail.name != ""].name.value_counts().head(25).to_string())

# ---- corridor: OSM ways named for the Bay Ridge Branch / Fremont Secondary --
corr = rail[rail.name.str.contains("Bay Ridge|Fremont", case=False, regex=True)]
corr = corr[corr.service.isin(["", "main"])]
print("\nCorridor ways by name:\n" + corr.name.value_counts().to_string())
corridor = unary_union(corr.geometry.values)

# ---- place stations --------------------------------------------------------
rows = []
for name, pat, approx in STATIONS:
    ap = gpd.GeoSeries([Point(approx)], crs=CRS_WGS).to_crs(CRS_NYC).iat[0]
    pt, how = None, "snap_to_corridor"
    if pat:
        st = streets[streets.name.str.match(pat)]
        cand = []
        for g in st.geometry:
            x = g.intersection(corridor)
            if not x.is_empty:
                cand += list(getattr(x, "geoms", [x]))
        cand = [c if c.geom_type == "Point" else c.centroid for c in cand]
        if cand:
            pt = min(cand, key=lambda c: c.distance(ap))
            how = "street_crossing"
            if pt.distance(ap) > 2500:      # > ~0.5 mi from expected: reject
                pt, how = None, "snap_to_corridor (crossing too far)"
    if pt is None:
        pt = nearest_points(corridor, ap)[0]
    rows.append({"order": len(rows) + 1, "station": name, "method": how,
                 "offset_from_approx_ft": round(pt.distance(ap)), "geometry": pt})

stations = gpd.GeoDataFrame(rows, crs=CRS_NYC)

# Corridor line between the termini, for mapping
merged = linemerge(corridor) if corridor.geom_type == "MultiLineString" else corridor
rail_out = gpd.GeoDataFrame({"name": ["IBX corridor (Bay Ridge Branch + Fremont Secondary)"]},
                            geometry=[merged], crs=CRS_NYC)

# Spacing check along the station sequence
xy = np.array([[p.x, p.y] for p in stations.geometry])
stations["gap_to_next_mi"] = np.r_[np.hypot(*np.diff(xy, axis=0).T) / 5280, np.nan].round(2)
print("\n" + stations.drop(columns="geometry").to_string(index=False))
print(f"\nStraight-line sum of station gaps: {stations.gap_to_next_mi.sum():.1f} mi "
      "(MTA: route about 14 mi)")

out = PROC / "ibx_corridor.gpkg"
rail_out.to_file(out, layer="rail", driver="GPKG")
stations.to_file(out, layer="stations", driver="GPKG")
print(f"Saved {out}")
