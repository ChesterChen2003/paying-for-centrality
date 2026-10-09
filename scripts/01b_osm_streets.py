"""
Step 01b — Trim the OSM extract to NYC's street network.

R5 only needs walkable ways for transit access/egress; the full extract also
carries buildings, land use and a large part of New Jersey, which pushes the
routing engine past 6 GB of memory. This keeps every `highway=*` way with at
least one node inside the NYC bounding box (plus a ~1 km margin), and the
nodes those ways reference. Result: data/processed/nyc_streets.osm.pbf
"""
import osmium

from config import RAW, PROC

SRC = RAW / "osm" / "nyc.osm.pbf"
DST = PROC / "nyc_streets.osm.pbf"
# NYC extent (Tottenville to Riverdale/Bronx, Hudson to the Nassau line) + margin
W, S, E, N = -74.27, 40.49, -73.69, 40.92

# Pass 1: ways tagged highway=* touching the box
way_ids = set()
need_nodes = set()
for w in (osmium.FileProcessor(str(SRC))
          .with_locations()
          .with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
          .with_filter(osmium.filter.KeyFilter("highway"))):
    if w.tags.get("area") == "yes":
        continue
    inside = False
    for n in w.nodes:
        loc = n.location
        if loc.valid() and W <= loc.lon <= E and S <= loc.lat <= N:
            inside = True
            break
    if inside:
        way_ids.add(w.id)
        need_nodes.update(n.ref for n in w.nodes)
print(f"Ways kept: {len(way_ids):,}; nodes referenced: {len(need_nodes):,}")

# Pass 2: write the referenced nodes, then the kept ways (no relations needed)
if DST.exists():
    DST.unlink()
with osmium.SimpleWriter(str(DST)) as writer:
    for obj in osmium.FileProcessor(str(SRC), osmium.osm.NODE | osmium.osm.WAY):
        if obj.is_node() and obj.id in need_nodes:
            writer.add_node(obj)
        elif obj.is_way() and obj.id in way_ids:
            writer.add_way(obj)
print(f"Wrote {DST} ({DST.stat().st_size / 1e6:.1f} MB)")
