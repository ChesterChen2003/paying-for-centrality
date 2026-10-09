#!/usr/bin/env bash
# =============================================================================
# NYC Transit Access & Rent — Step 00: download all public source data
# Author: Wei Chen
#
# Run from the project folder on a Mac (needs only bash + curl, both built in):
#     bash 00_download_data.sh
# Re-running is safe: files that already exist are skipped.
# Everything lands in data/raw/, and data/raw/MANIFEST.tsv records the source
# URL, download time, size and SHA-256 of every file for reproducibility.
# Total download is roughly 300–500 MB.
# =============================================================================
set -o pipefail   # (no -u: macOS ships bash 3.2, which errors on empty arrays under -u)

ROOT="$(cd "$(dirname "$0")" && pwd)"
RAW="$ROOT/data/raw"
mkdir -p "$RAW"/{gtfs,osm,acs,pluto,lodes,boundaries}
MANIFEST="$RAW/MANIFEST.tsv"
[ -f "$MANIFEST" ] || printf "file\turl\tdownloaded_utc\tbytes\tsha256\n" > "$MANIFEST"
FAILED=()

valid () {  # valid <path> — reject empty files and HTML error pages saved as data
  [ -s "$1" ] || return 1
  case "$1" in
    *.json) head -c 1 "$1" | grep -q '\[' ;;
    *.geojson) head -c 200 "$1" | grep -q 'FeatureCollection' ;;
    *.csv) ! head -c 200 "$1" | grep -qi '<html' ;;
    *) ! head -c 200 "$1" | grep -qi '<html' ;;
  esac
}

dl () {  # dl <url> <output path>
  local url="$1" out="$2"
  if valid "$out"; then echo "  skip (exists)  $(basename "$out")"; return 0; fi
  echo "  downloading    $(basename "$out")"
  if curl -fL --retry 3 --retry-delay 5 --connect-timeout 30 -sS -o "$out.part" "$url" \
     && valid "$out.part"; then
    mv -f "$out.part" "$out"
    local bytes sha
    bytes=$(wc -c < "$out" | tr -d ' ')
    sha=$(shasum -a 256 "$out" | cut -d' ' -f1)
    printf "%s\t%s\t%s\t%s\t%s\n" "${out#$ROOT/}" "${url%%&key=*}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$bytes" "$sha" >> "$MANIFEST"
    return 0
  else
    [ -f "$out.part" ] && mv -f "$out.part" "$out.failed"
    echo "  !! failed      ${url%%&key=*}"; return 1
  fi
}

need () {  # like dl, but a failure is recorded in the final summary
  dl "$1" "$2" || FAILED+=("$1")
}

# --- 1. MTA static GTFS (subway incl. Staten Island Railway + all bus feeds) --
echo "[1/6] MTA GTFS"
GTFS_BASE="https://rrgtfsfeeds.s3.amazonaws.com"
for f in gtfs_subway gtfs_bx gtfs_b gtfs_m gtfs_q gtfs_si gtfs_busco; do
  need "$GTFS_BASE/$f.zip" "$RAW/gtfs/$f.zip"
done

# --- 2. OpenStreetMap street network --------------------------------------------
# BBBike's New York City extract (~100–200 MB). If it fails, fall back to the
# Geofabrik New York State file (~475 MB); if osmium-tool is installed it is
# then cropped to NYC. Coverage of the file is checked in the next step.
echo "[2/6] OpenStreetMap"
if ! dl "https://download.bbbike.org/osm/bbbike/NewYork/NewYork.osm.pbf" "$RAW/osm/nyc.osm.pbf"; then
  need "https://download.geofabrik.de/north-america/us/new-york-latest.osm.pbf" "$RAW/osm/new-york-latest.osm.pbf"
  if command -v osmium >/dev/null 2>&1 && [ -s "$RAW/osm/new-york-latest.osm.pbf" ]; then
    osmium extract -b -74.30,40.45,-73.65,40.96 --strategy complete_ways \
      "$RAW/osm/new-york-latest.osm.pbf" -o "$RAW/osm/nyc.osm.pbf" --overwrite \
      && echo "  cropped Geofabrik file to NYC"
  fi
fi

# --- 3. Census ACS 5-year, all NYC tracts ----------------------------------------
# Median gross rent, tenure, rent burden, renter housing age/size, income,
# poverty, population, transit commute share. One API call; the Census API
# needs a free key (https://api.census.gov/data/key_signup.html). Pass it as
#     CENSUS_API_KEY=yourkey bash 00_download_data.sh
# The key is never written to MANIFEST.tsv or any file.
echo "[3/6] ACS 5-year"
if [ -z "${CENSUS_API_KEY:-}" ]; then
  echo "  !! CENSUS_API_KEY is not set — the Census API will refuse the request."
fi
ACS_VARS="NAME,B25064_001E,B25064_001M,B25003_001E,B25003_003E,B25070_001E,B25070_007E,B25070_008E,B25070_009E,B25070_010E,B25070_011E,B25037_003E,B25021_003E,B19013_001E,B19013_001M,B01003_001E,B08301_001E,B08301_010E,B17001_001E,B17001_002E"
ACS_OK=0
for YEAR in 2024 2023; do
  URL="https://api.census.gov/data/$YEAR/acs/acs5?get=$ACS_VARS&for=tract:*&in=state:36&in=county:005,047,061,081,085&key=${CENSUS_API_KEY:-}"
  if dl "$URL" "$RAW/acs/acs5_${YEAR}_nyc_tracts.json"; then ACS_OK=1; break; fi
done
[ $ACS_OK -eq 1 ] || FAILED+=("Census ACS API (2024 and 2023)")

# --- 4. PLUTO tax lots (housing-stock controls + residential-unit weights) ------
echo "[4/6] PLUTO"
PLUTO_COLS="bbl,borough,bct2020,yearbuilt,unitsres,unitstotal,bldgclass,landuse,latitude,longitude,transitzone,version"
need "https://data.cityofnewyork.us/resource/64uk-42ks.csv?%24select=$PLUTO_COLS&%24limit=1000000" "$RAW/pluto/pluto_lots.csv"

# NYCHA-owned lots (public-housing control): owner name contains "HOUSING AUTH"
need "https://data.cityofnewyork.us/resource/64uk-42ks.csv?%24select=bbl,bct2020,unitsres,ownername&%24where=upper(ownername)%20like%20%27%25HOUSING%20AUTH%25%27&%24limit=50000" "$RAW/pluto/pluto_nycha_lots.csv"

# --- 5. LEHD LODES 2023 jobs by workplace block + block coordinates -------------
echo "[5/6] LODES"
need "https://lehd.ces.census.gov/data/lodes/LODES8/ny/wac/ny_wac_S000_JT00_2023.csv.gz" "$RAW/lodes/ny_wac_S000_JT00_2023.csv.gz"
need "https://lehd.ces.census.gov/data/lodes/LODES8/ny/ny_xwalk.csv.gz" "$RAW/lodes/ny_xwalk.csv.gz"

# --- 6. Boundaries: 2020 census tracts (shoreline-clipped, with NTA codes) + NTAs
echo "[6/6] Boundaries"
need "https://data.cityofnewyork.us/resource/63ge-mke6.geojson?%24limit=5000" "$RAW/boundaries/nyc_tracts_2020.geojson"
need "https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?%24limit=1000" "$RAW/boundaries/nyc_ntas_2020.geojson"
# Census 1:500k county boundaries (2019, from the Census Bureau's CitySDK repository):
# neighbouring land on the atlas beyond the OSM extract
need "https://raw.githubusercontent.com/uscensusbureau/citysdk/master/v2/GeoJSON/500k/2019/county.json" "$RAW/boundaries/cb_2019_us_county_500k.json"

# --- summary -------------------------------------------------------------------
echo
echo "Done. Contents of data/raw:"
du -sh "$RAW"/* 2>/dev/null
if [ ${#FAILED[@]} -gt 0 ]; then
  echo; echo "These downloads failed (re-run the script to retry):"
  printf '  %s\n' "${FAILED[@]}"
else
  echo; echo "All downloads succeeded."
fi
