"""
Step 09 — Fill the README findings table from outputs/tables/facts.json, so the
README quotes exactly what the pipeline produced.
"""
import json
import re

from config import ROOT, TAB

F = json.loads((TAB / "facts.json").read_text())
table = f"""| | Result |
|---|---|
| **Access premium** | Holding rental stock and borough constant, the elasticity of median gross rent with respect to jobs reachable in 45 min is **{F['b_m3']}** (OLS). In the preferred spatial model (lag + error) the direct effect is **{F['b_sac']}**, so doubling access goes with about {F['pct_2x_sac']} higher rent, and the total effect including spillovers is **{F['b_sac_total']}**. |
| **Mostly centrality** | Location (distance to the nearest CBD, modelled within each borough) explains **{F['r2_dist_within']}** of the variation in access. Location-predicted access carries an elasticity of **{F['b_loc']}**; access beyond what location delivers carries **{F['b_excess']}** (p = {F['p_excess']}), and {F['excess_min']} to {F['excess_max']} across four location models. |
| **Where it is priced** | MGWR finds a significant positive local access premium in **{F['mgwr_mn']}** of Manhattan tracts, **{F['mgwr_bk']}** in Brooklyn, **{F['mgwr_qn']}** in Queens, and **{F['mgwr_bx']}** in the Bronx and on Staten Island (R² {F['mgwr_r2']}). |
| **Equity typology** | **{F['dw_hh']}** renter households live in high-access, low-rent, high-vulnerability tracts (displacement watch); **{F['sp_hh']}** in low-access, low-rent, high-vulnerability tracts (service priority); NYCHA-majority tracts ({F['ph_tracts']}) are classed separately. |
| **IBX scenario** | **{F['ibx_tracts']}** tracts and **{F['ibx_pop']}** residents gain ≥5% in 45-minute job access (median {F['ibx_med']}; {F['ibx_med60']} on a 60-minute basis). The two most vulnerable quartiles hold {F['ibx_q34']} of renter households in gaining tracts vs {F['ibx_q34_base']} across all sample tracts. Illustrative rent pressure in gaining tracts: median {F['press_low']} (excess-access rate) to {F['press_mid']} (SAC total effect); {F['press_high']} where the local market already prices access. A precautionary screen flags **{F['watch_tracts']}** tracts (**{F['watch_hh']}** renter households). |"""
p = ROOT / "README.md"
s = p.read_text()
s = re.sub(r"<!-- findings:start -->.*?<!-- findings:end -->",
           "<!-- findings:start -->\n" + table + "\n<!-- findings:end -->", s, flags=re.S)
p.write_text(s)
print("README findings updated")
