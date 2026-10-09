#!/usr/bin/env bash
# Run the full pipeline in order. Total ~60–75 min on a laptop, most of it
# routing (02, 06b) and MGWR (04b). Requires Python deps (requirements.txt)
# and Java 21 for r5py. Data must already be in data/raw (00_download_data.sh).
set -euo pipefail
cd "$(dirname "$0")/scripts"
export R5_MAX_MEMORY="${R5_MAX_MEMORY:-5G}"

python 01_build_base.py        # tract geography, PLUTO controls, routing points
python 01b_osm_streets.py      # trim OSM to NYC streets
python 02_accessibility.py     # baseline transit job access (r5py)
python 03_assemble.py          # join ACS + access, build model variables
python 04_models.py            # OLS / spatial lag / spatial error / centrality
python 04b_mgwr.py             # MGWR local coefficients
python 05_equity.py            # bivariate LISA + planning typology
python 06a_ibx_stations.py     # place the 18 IBX stations on the corridor
python 06b_ibx_scenario.py     # build IBX GTFS + route with it (r5py)
python 06c_ibx_effects.py      # who gains, rent-pressure screen
python 07_figures.py           # portfolio figures
python 08_webmap_data.py       # quoted facts + data and page for the interactive atlas
python 09_readme_findings.py   # README findings table from the facts
cd .. && node report/build_report.js   # case-study .docx (needs: npm i docx)
