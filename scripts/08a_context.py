"""
Step 08a — Neighbouring land for the atlas basemap.

The atlas draws New Jersey, Westchester and Nassau in grey around the city so
the harbour, rivers and city line read as they do on the ground. Inside the
OSM extract the land is built from OpenStreetMap coastline (land lies to the
left of every coastline way) minus large inland water and minus the City of
New York; beyond the extract it comes from the Census Bureau's 1:500k
cartographic county boundaries. Writes data/processed/context_land.gpkg.
"""
import geopandas as gpd
import numpy as np
import osmium
import shapely
from shapely.geometry import box
from shapely.ops import polygonize, unary_union

from config import RAW, PROC, CRS_NYC, CRS_WGS

OSM = RAW / "osm" / "nyc.osm.pbf"
CB = RAW / "boundaries" / "cb_2019_us_county_500k.json"
CONTEXT_BOX = (-74.75, 40.25, -73.25, 41.20)       # lon/lat window drawn on the map
NYC_GEOID = {"36005", "36047", "36061", "36081", "36085"}
MIN_WATER_SQFT = 20 * 43560                       # inland water bodies ≥ 20 acres
MIN_PART_SQFT = 5 * 43560                         # drop islets and holes < 5 acres


def to_nyc(geoms):
    return gpd.GeoSeries(geoms, crs=CRS_WGS).to_crs(CRS_NYC)


# ---- 1. read coastline, inland water and the city boundary from OSM -------------
reader = osmium.io.Reader(str(OSM), osmium.osm.osm_entity_bits.NOTHING)
hb = reader.header().box()
reader.close()
ext = (hb.bottom_left.lon, hb.bottom_left.lat, hb.top_right.lon, hb.top_right.lat)
if not hb.valid():                                # e.g. a cropped Geofabrik file: use the crop box
    ext = (-74.30, 40.45, -73.65, 40.96)
inset = 0.003                                     # stay clear of ways cut at the extract edge
inner_wgs = box(ext[0] + inset, ext[1] + inset, ext[2] - inset, ext[3] - inset)

fab = osmium.geom.WKBFactory()
coast, water, nyc = [], [], []
fp = (osmium.FileProcessor(str(OSM)).with_locations()
      .with_areas(osmium.filter.KeyFilter("natural", "boundary"))
      .with_filter(osmium.filter.KeyFilter("natural", "boundary")))
for o in fp:
    try:
        if o.is_way() and o.tags.get("natural") == "coastline":
            coast.append(shapely.from_wkb(fab.create_linestring(o)))
        elif o.is_area() and o.tags.get("natural") == "water":
            water.append(shapely.from_wkb(fab.create_multipolygon(o)))
        elif (o.is_area() and o.tags.get("boundary") == "administrative"
              and o.tags.get("admin_level") == "5" and o.tags.get("name") == "New York"):
            nyc.append(shapely.from_wkb(fab.create_multipolygon(o)))
    except (RuntimeError, osmium.InvalidLocationError):
        continue                                  # incomplete geometry at the extract edge
assert nyc, "City of New York boundary not found in the OSM extract"
print(f"OSM: {len(coast)} coastline ways, {len(water)} water areas")

coast = to_nyc(coast)
inner = to_nyc([inner_wgs.segmentize(0.002)]).iat[0]
water = to_nyc(water)
water = water[water.area >= MIN_WATER_SQFT]
nyc = to_nyc(nyc).union_all()

# ---- 2. land = faces of (coastline ∪ box edge) that lie left of the coastline -------
# node the full coastline against the box edge (clipping first leaves endpoints a
# hair off the edge, which opens the rings), then keep the faces inside the box
faces = [f for f in polygonize(unary_union(list(coast) + [inner.exterior]))
         if inner.contains(f.representative_point())]
xy = [np.asarray(g.coords) for g in coast]
seg0 = np.vstack([c[:-1] for c in xy])
seg1 = np.vstack([c[1:] for c in xy])
d = seg1 - seg0
ln = np.hypot(d[:, 0], d[:, 1])
ok = ln > 1
mid, nrm = (seg0 + seg1)[ok] / 2, np.column_stack([-d[ok, 1], d[ok, 0]]) / ln[ok, None]
tree = shapely.STRtree(faces)
votes = np.zeros((len(faces), 2))
for side, pts in ((0, mid + 2 * nrm), (1, mid - 2 * nrm)):   # 0 = land (left), 1 = water
    i_pt, i_face = tree.query(shapely.points(pts), predicate="within")
    np.add.at(votes, (i_face, side), 1)
land_faces = [f for f, (l, w) in zip(faces, votes) if l > w]
undecided = int(((votes[:, 0] == 0) & (votes[:, 1] == 0)).sum())
print(f"faces: {len(faces)}, land: {len(land_faces)}, undecided: {undecided}")

land_in = unary_union(land_faces).difference(water.union_all()).difference(nyc)

# ---- 3. beyond the extract: Census 1:500k counties ------------------------------
cb = gpd.read_file(CB)
cb = cb[cb.STATEFP.isin(["09", "34", "36"]) & ~cb.GEOID.isin(NYC_GEOID)]
cb = cb.clip(box(*CONTEXT_BOX)).to_crs(CRS_NYC)
land_out = cb.union_all().difference(inner)

# ---- 4. clean and save -----------------------------------------------------------
land = unary_union([land_in, land_out])
parts = []
for p in getattr(land, "geoms", [land]):
    if p.geom_type != "Polygon" or p.area < MIN_PART_SQFT:
        continue
    holes = [h for h in p.interiors if shapely.Polygon(h).area >= MIN_PART_SQFT]
    parts.append(shapely.Polygon(p.exterior, holes))
out = gpd.GeoDataFrame({"part": range(len(parts))}, geometry=parts, crs=CRS_NYC)
out.to_file(PROC / "context_land.gpkg", layer="land", driver="GPKG")
print(f"Wrote {PROC / 'context_land.gpkg'} ({len(out)} polygons, "
      f"{out.area.sum() / 27878400:,.0f} sq mi)")
