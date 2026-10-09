// Builds report/Paying_for_Centrality_WeiChen.docx from the figures and the
// numbers in outputs/tables. Run: node report/build_report.js
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell,
  WidthType, AlignmentType, HeadingLevel, BorderStyle, ShadingType, LevelFormat,
  Footer, PageNumber, TabStopType, VerticalAlign,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const FIG = (f) => path.join(ROOT, "outputs", "figures", f);
const FONT = "Calibri";
const INK = "1B2430", MUTED = "5B6670", ACCENT = "1C5CAB", RULE = "C9CED4", HEAD_FILL = "EEF2F6";

// ---------- helpers ----------
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 21, bold: o.bold, italics: o.italics, color: o.color || INK });
function P(parts, o = {}) {
  const children = (Array.isArray(parts) ? parts : [parts]).map((x) => (typeof x === "string" ? run(x, o) : x));
  return new Paragraph({ children, spacing: { after: o.after ?? 120, before: o.before ?? 0, line: 276 }, alignment: o.align, keepNext: o.keepNext });
}
const B = (t) => run(t, { bold: true });
const I = (t) => run(t, { italics: true });
function H1(t) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 280, after: 120 }, keepNext: true,
    children: [new TextRun({ text: t, font: FONT, size: 28, bold: true, color: INK })] });
}
function H2(t) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 80 }, keepNext: true,
    children: [new TextRun({ text: t, font: FONT, size: 23, bold: true, color: ACCENT })] });
}
function bullet(parts) {
  const children = (Array.isArray(parts) ? parts : [parts]).map((x) => (typeof x === "string" ? run(x) : x));
  return new Paragraph({ numbering: { reference: "bul", level: 0 }, children, spacing: { after: 80, line: 276 } });
}
function img(file, widthIn) {
  const buf = fs.readFileSync(FIG(file));
  const w = buf.readUInt32BE(16), h = buf.readUInt32BE(20);         // PNG IHDR
  const wpx = Math.round(widthIn * 96);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
    children: [new ImageRun({ type: "png", data: buf, transformation: { width: wpx, height: Math.round(wpx * h / w) } })] });
}
const caption = (t) => new Paragraph({ spacing: { after: 200 }, children: [run(t, { italics: true, size: 18, color: MUTED })] });

const cellBorder = { style: BorderStyle.SINGLE, size: 4, color: RULE };
const noBorder = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
function table(rows, widths, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: rows.map((r, i) => new TableRow({ tableHeader: i === 0, cantSplit: true,
      children: r.map((c, j) => new TableCell({
        width: { size: widths[j], type: WidthType.DXA },
        shading: i === 0 ? { type: ShadingType.CLEAR, color: "auto", fill: HEAD_FILL } : (o.hl && o.hl(i) ? { type: ShadingType.CLEAR, color: "auto", fill: "FBF3E9" } : undefined),
        borders: { top: i === 0 ? cellBorder : noBorder, bottom: cellBorder, left: noBorder, right: noBorder },
        margins: { top: 60, bottom: 60, left: 90, right: 90 }, verticalAlign: VerticalAlign.CENTER,
        children: [new Paragraph({ keepNext: i < rows.length - 1,      // keep the table on one page
          alignment: (Array.isArray(o.num) ? o.num.includes(j) : (j > 0 && o.num)) ? AlignmentType.RIGHT : AlignmentType.LEFT,
          children: [run(String(c), { size: 18, bold: i === 0 })] })],
      })) })),
  });
}
const spacer = () => new Paragraph({ spacing: { after: 60 }, children: [] });

// ---------- numbers from the pipeline ----------
function splitCsv(line) {            // handles "quoted, fields"
  const out = []; let cur = "", q = false;
  for (const ch of line) {
    if (ch === '"') q = !q;
    else if (ch === "," && !q) { out.push(cur); cur = ""; }
    else cur += ch;
  }
  out.push(cur);
  return out;
}
const csv = (f) => {
  const [hdr, ...lines] = fs.readFileSync(path.join(ROOT, "outputs", "tables", f), "utf8").trim().split(/\r?\n/);
  const cols = splitCsv(hdr);
  return lines.map((l) => { const v = splitCsv(l); return Object.fromEntries(cols.map((c, i) => [c, v[i]])); });
};
const fit = csv("04_model_fit.csv");
const coef = csv("04_coefficients.csv");
const f3 = (x) => Number(x).toFixed(3), f2 = (x) => Number(x).toFixed(2);
const pfmt = (x) => (Number(x) < 0.01 ? "<0.01" : f2(x));
const getCoef = (model, term) => coef.find((r) => r.model.startsWith(model) && r.term === term);
const getFit = (model) => fit.find((r) => r.model.startsWith(model));
const typ = csv("05_typology_summary.csv");
const byq = csv("06_ibx_by_vulnerability.csv");
const watch = csv("06_ibx_watch_ntas.csv");
const bws = csv("04_mgwr_bandwidths.csv");
const k = (x) => Math.round(Number(x)).toLocaleString("en-US");
const rob = csv("04_robustness.csv");
const lm = csv("04_lm_tests.csv");
const F = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs", "tables", "facts.json"), "utf8"));
function normCdf(x) { // Abramowitz-Stegun 7.1.26
  const t = 1 / (1 + 0.3275911 * x / Math.SQRT2), y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x / 2);
  return 0.5 * (1 + y);
}

// ---------- content ----------
const children = [];
children.push(
  new Paragraph({ spacing: { after: 60 }, children: [run("PORTFOLIO CASE STUDY · TRANSPORTATION PLANNING · SPATIAL ANALYSIS", { size: 16, color: ACCENT, bold: true })] }),
  new Paragraph({ spacing: { after: 80 }, children: [new TextRun({ text: "Paying for Centrality", font: FONT, size: 52, bold: true, color: INK })] }),
  P("Transit job access, rent, and who gains from the Interborough Express: a tract-level spatial analysis of New York City", { size: 26, color: MUTED, after: 160 }),
  P([run("Wei Chen", { bold: true }), run("  ·  Master of Regional Planning, Cornell University  ·  October 2026", { color: MUTED })], { after: 60 }),
  P("Independent academic work using public data. It is not affiliated with or endorsed by the MTA or any other agency.", { size: 17, italics: true, color: MUTED, after: 240 }),
);

children.push(H1("Summary"));
children.push(P(`New York's transit network puts ${F.share_1m} of the city's ${F.pop_total_m} million residents within 45 minutes of at least a million jobs. Do renters pay for that access, and who would gain if the network grew? This study measures transit job accessibility for every census tract with a schedule-based routing model, relates it to rents in the ${F.tracts_sample} tracts with usable rent estimates, and tests a scenario for the proposed Interborough Express (IBX).`));
children.push(
  bullet([B("A real but modest premium. "), run(`Holding rental-stock characteristics and borough constant, the elasticity of median gross rent with respect to jobs reachable within 45 minutes is ${F.b_m3} in OLS. In the preferred spatial model the direct effect is ${F.b_sac} (doubling access goes with about ${F.pct_2x_sac} higher rent in the tract itself) and the total effect, including spillovers to neighbouring rents, is ${F.b_sac_total}.`)]),
  bullet([B("Most of it is a centrality premium. "), run(`Access that location predicts carries an elasticity of ${F.b_loc}; access beyond what location delivers carries ${F.b_excess} (p = ${F.p_excess}), and between ${F.excess_min} and ${F.excess_max} across four ways of modelling location. Transit that outperforms its location is priced at a fraction of the rate, if at all.`)]),
  bullet([B("Access is priced in some markets and not others. "), run(`A multiscale geographically weighted regression (MGWR) finds a significant positive local access premium in ${F.mgwr_mn} of Manhattan tracts, ${F.mgwr_bk} in Brooklyn and ${F.mgwr_qn} in Queens, against ${F.mgwr_bx} in the Bronx and ${F.mgwr_si} on Staten Island.`)]),
  bullet([B("Two equity priorities. "), run(`${F.dw_hh} renter households live in high-access, low-rent, high-vulnerability tracts (displacement watch); ${F.sp_hh} live in low-access, low-rent, high-vulnerability tracts (service priority). Tracts mostly owned by NYCHA are classed separately.`)]),
  bullet([B("The IBX widens access mostly where it is not yet priced. "), run(`It raises 45-minute job access by at least 5% for ${F.ibx_pop} residents (median gain ${F.ibx_med}; ${F.ibx_med60} on a 60-minute basis). ${F.ibx_unpriced_share} of gaining tracts show no local access premium today. A precautionary screen flags ${F.watch_tracts} tracts (${F.watch_hh} renter households) where a gain, an already-priced market and high vulnerability coincide.`)]),
);

children.push(H1("1. Question and approach"));
children.push(P("The 2025 version of this project, written for a course on data management and programming for policy, found a positive correlation between a composite stop-density index and median rent across about 165 Neighborhood Tabulation Areas (NTAs). This version asks the same question with planning-grade methods, and adds two applied questions: where does access diverge from rent, and who would gain from a major transit investment?"));
children.push(P([B("Table 1. "), run("What changed from the 2025 version")], { keepNext: true, after: 60 }));
children.push(table([
  ["", "2025 version", "2026 version"],
  ["Unit", "~165 NTAs (duplicated join rows)", `${F.tracts_all} census tracts; ${F.tracts_sample} in the rent models`],
  ["Projection", "Web Mercator (areas inflated ~74% at NYC's latitude)", "NY State Plane Long Island, EPSG:2263"],
  ["Access", "Stop counts per km² and 400 m buffer coverage, weighted 30/35/35", "Jobs reachable within 45 min by subway, bus and walking (R5 on MTA GTFS)"],
  ["Rent", "NTA median gross rent", "ACS 2020–24 tract medians; top-coding and sampling error handled"],
  ["Model", "Bivariate OLS", "Hedonic OLS, spatial lag, error and combined models, centrality decomposition, MGWR"],
  ["Equity", "None", "Bivariate LISA, renter vulnerability index, planning typology"],
  ["Scenario", "None", "IBX GTFS scenario: who gains, and a bracketed rent-pressure screen"],
  ["Code", "Single R script", "12-script Python pipeline plus a download script, pinned environment, open data only"],
], [1500, 3700, 4160]));
children.push(spacer());

children.push(H1("2. Data and accessibility model"));
children.push(P([B("Table 2. "), run("Data sources")], { keepNext: true, after: 60 }));
children.push(table([
  ["Source", "Vintage", "Use"],
  ["MTA static GTFS: subway and five borough bus feeds, MTA Bus Co.", "Schedules in effect October 2026", "Transit service for routing"],
  ["OpenStreetMap (NYC extract)", "October 2026", "Walking network; IBX right-of-way"],
  ["LEHD LODES 8, workplace area characteristics", "2023", "4.59 million jobs by census block"],
  ["American Community Survey, 5-year", "2020–24", "Rent, tenure, rent burden, income, poverty, commute"],
  ["NYC DCP PLUTO", "26v2", "Residential units for trip origins; rental-stock and NYCHA controls"],
  ["NYC DCP census tracts and NTAs", "2020", "Geography (shoreline-clipped)"],
], [4300, 1900, 3160]));
children.push(spacer());
children.push(P("Accessibility is computed with Conveyal's R5 routing engine (through r5py). Each tract's trip starts at the centroid of its homes, weighted by PLUTO residential units, so a tract that contains a park starts where people live. Destinations are the job-weighted centroids of the 2,304 tracts with jobs. Trips depart every minute from 7:00 to 8:00 AM on Tuesday, October 20, 2026; the median travel time across those 60 departures is used, so results do not hinge on just catching a train. Walking runs at 3 mph with at most 20 minutes per walk leg, up to four transit rides and 90 minutes in total. The model evaluates 5.36 million origin–destination pairs."));
children.push(P(`The main measure counts jobs reachable within 45 minutes; 30- and 60-minute counts and a decay-weighted measure (30-minute half-life) are used as checks. The results reproduce the expected gradient: the median tract reaches ${F.med_j45_mn} jobs in Manhattan, ${F.med_j45_bk} in Brooklyn, ${F.med_j45_qn} in Queens, ${F.med_j45_bx} in the Bronx and ${F.med_j45_si} on Staten Island. Only three uninhabited island and park tracts have zero access, and access tracks the ACS transit commute share (Spearman 0.36).`));
children.push(P(`The rent models use the ${F.tracts_sample} tracts with an ACS median gross rent, at least 50 renter-occupied units and complete controls. ${F.n_topcoded} of them are top-coded at $3,500+ and ${F.n_cv} have a coefficient of variation above 0.30; both are handled as robustness checks.`));
children.push(img("F1_job_access_45min.png", 5.6));
children.push(caption("Figure 1. Jobs reachable by transit within 45 minutes, weekday AM peak."));
children.push(img("F2_median_gross_rent.png", 5.6));
children.push(caption("Figure 2. Median gross rent, ACS 2020–24."));

children.push(H1("3. Does transit access raise rent?"));
children.push(P("The hedonic model regresses log median gross rent on log jobs within 45 minutes. Controls describe the rental stock: the median age of renter-occupied housing, the median number of rooms, the share of residential units in privately owned pre-1974 rental buildings with six or more units (a proxy for rent stabilization; co-ops and condominiums excluded), and the share of units owned by NYCHA. Borough fixed effects absorb borough-wide differences."));
const fitRow = (lab, m, term = "ln_jobs45") => {
  const c = getCoef(m, term), f = getFit(m);
  const rl = f.rho_or_lambda && f.rho_or_lambda !== "" ? f2(f.rho_or_lambda) : "–";
  return [lab, `${f3(c.coef)} (${f3(c.se)})`, f2(f.r2), Math.round(Number(f.aic)).toLocaleString("en-US"), f2(f.resid_moran_I), rl];
};
const sacRow = rob.find((r) => r.check.startsWith("SAC (lag + error, GMM), direct"));
const sacTot = rob.find((r) => r.check.startsWith("SAC (lag + error, GMM), total"));
children.push(P([B("Table 3. "), run("Model ladder: elasticity of rent with respect to 45-minute job access")], { keepNext: true, after: 60 }));
children.push(table([
  ["Model", "Access (SE)", "R² / pseudo-R²", "AIC", "Residual Moran's I", "ρ / λ"],
  fitRow("M1 OLS, access only", "M1"),
  fitRow("M2 OLS + rental stock", "M2"),
  fitRow("M3 OLS + borough FE", "M3"),
  fitRow("M4 Spatial lag (coefficient)", "M4"),
  fitRow("M5 Spatial error", "M5"),
  ["SAC lag + error (preferred), direct effect", `${f3(sacRow.b_access)} (${f3(sacRow.se)})`, "–", "–", "–", F.rho_sac],
  ["SAC, total effect incl. spillovers", `${f3(sacTot.b_access)} (${f3(sacTot.se)})`, "–", "–", "–", F.rho_sac],
], [3000, 1450, 1300, 1050, 1460, 1100], { num: true, hl: (i) => i === 6 || i === 7 }));
children.push(caption(`Heteroskedasticity-robust SEs for OLS and SAC (GMM); maximum-likelihood SEs for the lag and error models. Spatial weights: 8 nearest tracts, row-standardized. The spatial-lag total effect of access, including spillovers through neighbours' rents, is ${F.b_slm_total}.`));
const lmv = (t) => Number(lm.find((r) => r.test === t).stat).toFixed(0);
children.push(P(`Access alone explains almost none of the variation in rent (R² ${F.r2_m1}), because public housing and rent-stabilized stock hold rents down in many of the best-connected places. With the rental-stock controls the access coefficient rises to ${F.b_m2}, and borough fixed effects bring it to ${F.b_m3} (R² ${F.r2_m3}): 10% more jobs within reach goes with ${F.pct_10_m3} higher rent. The controls behave as expected: a tract made up entirely of NYCHA units has a median rent about ${F.nycha_pct} lower, the rent-stabilization proxy lowers rent (${F.b_pre74} per unit share), and larger units raise it.`));
children.push(P(`The OLS residuals are strongly clustered (Moran's I ${F.moran_m3}). Both robust Lagrange multiplier tests are significant (${lmv("Robust LM-lag")} for a spatial lag, ${lmv("Robust LM-error")} for spatial error), so the preferred model includes both processes (SAC, estimated by GMM with heteroskedasticity-robust errors; ρ = ${F.rho_sac}). Because of the lag term its access coefficient (${F.b_sac_coef}) is not itself the elasticity: the direct effect on a tract's own rent is ${F.b_sac} (SE ${F.se_sac}), and the total effect, once higher rents spill over to neighbours, is ${F.b_sac_total}. Spatial-error models with 4 or 12 neighbours give ${F.sem_k_range}.`));
children.push(img("F3_pooled_vs_within_borough.png", 6.5));
children.push(caption("Figure 3. The pooled relationship hides very different borough slopes: steep in Manhattan, positive in Brooklyn, flat in Queens and negative in the Bronx and on Staten Island."));
const nonCent = rob.filter((r) => r.group !== "Centrality" && !r.check.startsWith("Baseline"));
const lo = Math.min(...nonCent.map((r) => Number(r.b_access))), hi = Math.max(...nonCent.map((r) => Number(r.b_access)));
children.push(P(`Across ${nonCent.length} alternative specifications that do not control for centrality, the elasticity stays between ${f3(lo)} and ${f3(hi)} (Figure 4). Top-coding barely matters (Tobit ${f3(rob.find((r) => r.check.startsWith("Tobit")).b_access)}), nor does replacing the ACS building-age measure, which is bottom-coded at 1939 in ${F.bottomcoded_share} of tracts, with PLUTO building age. Dropping the ${F.n_bottom} bottom-coded tracts altogether does lower the estimate, to ${F.b_drop_bottom} (95% CI ${F.ci_drop_bottom}), because those tracts are more central and better connected (median ${F.bottom_j45} jobs within 45 minutes, against ${F.other_j45} elsewhere). Leaving out Brooklyn lowers the estimate to ${f3(rob.find((r) => r.check === "Leave out Brooklyn").b_access)}, so Brooklyn's well-connected neighbourhoods carry much of the citywide relationship. Re-estimated at the NTA level, as in the 2025 design, the access-only elasticity is ${f3(rob.find((r) => r.check.startsWith("NTA level, access only")).b_access)}.`));
children.push(img("F4_robustness_forest.png", 6.5));
children.push(caption("Figure 4. Robustness of the access elasticity. Orange rows control for centrality."));

children.push(H1("4. Centrality or transit?"));
children.push(P(`In New York, access and centrality are nearly the same variable: tracts close to Midtown or Lower Manhattan reach more jobs whatever their transit. Log access correlates −0.74 with log distance to the nearest CBD; distance alone explains about ${F.r2_dist_alone} of the variation in access, and distance modelled within each borough explains ${F.r2_dist_within}. Adding distance directly to the rent model turns the access coefficient to ${F.b_dist}.`));
children.push(P("To separate the two, log access is split into the part that location predicts (a natural spline in distance to the nearest CBD, fitted within each borough) and the remainder, excess access: transit that is better or worse than a tract's location delivers. Both parts enter the rent model together."));
children.push(P([B("Table 4. "), run("Location-predicted versus excess access")], { keepNext: true, after: 60 }));
const g = (m, t) => { const c = getCoef(m, t); return `${f3(c.coef)} (${f3(c.se)})`; };
children.push(table([
  ["Model", "Location-predicted access", "Excess access", "p (excess)"],
  ["OLS + controls + borough FE", g("M6", "access_loc"), g("M6", "excess_access"), pfmt(getCoef("M6", "excess_access").p)],
  ["Spatial error", g("M7", "access_loc"), g("M7", "excess_access"), pfmt(getCoef("M7", "excess_access").p)],
  ...rob.filter((r) => r.check.startsWith("Excess access, citywide") || r.check.startsWith("Excess access, log-quadratic")).map((r) => {
    const z = Number(r.b_access) / Number(r.se), pv = 2 * (1 - normCdf(Math.abs(z)));
    return ["Alt. location model: " + r.check.replace("Excess access, ", ""), "–", `${f3(r.b_access)} (${f3(r.se)})`, pv < 0.01 ? "<0.01" : f2(pv)];
  }),
], [4160, 2000, 1800, 1400], { num: [1, 2, 3] }));
children.push(caption("Alternative rows residualize access on the stated location model and control for its full basis."));
children.push(P(`The premium follows location. Access that location predicts carries an elasticity of ${F.b_loc}; access beyond it carries ${F.b_excess} (p = ${F.p_excess}) in OLS and ${F.b_excess_sem} (p = ${F.p_excess_sem}) in the spatial error model, and the alternative location models put it between ${F.excess_min} and ${F.excess_max}. Transit that outperforms its location is priced at about ${F.excess_share} of the rate for location-driven access, if at all. The neighbourhoods where transit beats location (Figure 5) — Jamaica, the West Bronx around Fordham and Mount Hope, and the Queens Boulevard corridor through Forest Hills, Rego Park and Kew Gardens — offer job access at a discount. Where transit lags location — College Point, Whitestone, Throgs Neck, Soundview and Glendale — the gap is a service problem, not a market one.`));
children.push(P("Two cautions. ACS median rent mixes new leases with long-tenure and rent-regulated ones, so it registers market changes slowly; asking rents may price access more quickly. And excess access is a residual: measurement error in the access model ends up there and pulls its coefficient toward zero."));
children.push(img("F8_excess_access.png", 5.6));
children.push(caption("Figure 5. Transit access relative to location. Red tracts get more access than their location predicts."));

children.push(H1("5. Where is access priced? MGWR"));
children.push(P("A global model gives one coefficient for the whole city. Multiscale geographically weighted regression lets every coefficient vary over its own spatial scale. Variables are standardized; the NYCHA share is held global because it is zero across whole districts."));
children.push(P([B("Table 5. "), run("MGWR bandwidths (nearest tracts)")], { keepNext: true, after: 60 }));
const bwName = { Intercept: "Intercept", ln_jobs45: "Log jobs within 45 min", age_dec: "Rental-stock age", rooms: "Median rooms", pre74_6plus: "Pre-1974 6+ unit rental share", nycha: "NYCHA share" };
children.push(table([["Term", "Bandwidth", "Share of sample"], ...bws.map((r) => [bwName[r.term] || r.term, k(r.bandwidth_nn), (Number(r.share_of_sample) * 100).toFixed(0) + "%"])],
  [4360, 2500, 2500], { num: true }));
children.push(spacer());
children.push(P(`The model fits far better than the global one (R² ${F.mgwr_r2} against ${F.r2_m3}). The access coefficient operates over about ${F.mgwr_bw} neighbouring tracts, roughly ${F.mgwr_cd} community districts, so it compares places that share a broad location, although distance to the CBD still varies within that window. After correcting for multiple testing, the premium is significant and positive in ${F.mgwr_pos} of tracts and significant and negative in ${F.mgwr_neg}. It is positive in ${F.mgwr_mn} of Manhattan tracts, ${F.mgwr_bk} of Brooklyn tracts and ${F.mgwr_qn} of Queens tracts (with ${F.mgwrneg_qn} negative, around Flushing), against ${F.mgwr_bx} in the Bronx and ${F.mgwr_si} on Staten Island.`));
children.push(P("Access is priced where housing demand is strong and not where it is weak. In the Bronx, neighbourhoods with excellent subway access still rent at a discount; that makes them affordable access today, though this cross-section cannot say how they would respond if demand shifted."));
children.push(img("F5_mgwr_local_access.png", 5.6));
children.push(caption("Figure 6. MGWR local coefficient on log job access (standardized). Gray tracts are not significant."));

children.push(H1("6. Equity typology"));
children.push(P(`A renter vulnerability index averages z-scores of the severe rent burden share (50%+ of income on rent), the poverty rate and the renter share. Tracts are classified with citywide medians of access, rent and vulnerability; the ${F.ph_tracts} tracts where NYCHA owns at least half of the homes are classed separately, because their rents are set by income and market displacement does not apply. A bivariate local Moran's I gives a cluster view of the same pattern: ${F.lisa_hl_fdr} tracts are significant high-access, low-rent outliers after a false-discovery-rate correction (${F.lisa_hl} at p < 0.05).`));
const tyOrder = ["Displacement watch", "Service priority", "Established access premium", "Public housing (NYCHA ≥ 50%)", "Car-oriented / amenity premium", "Middle"];
const tyDef = { "Displacement watch": "High access, low rent, high vulnerability", "Service priority": "Low access, low rent, high vulnerability", "Established access premium": "High access, high rent", "Public housing (NYCHA ≥ 50%)": "NYCHA owns half or more of homes", "Car-oriented / amenity premium": "Low access, high rent", "Middle": "Other" };
children.push(P([B("Table 6. "), run("Planning typology")], { keepNext: true, after: 60 }));
children.push(table([["Type", "Definition", "Tracts", "Renter HH", "Median rent", "Jobs in 45 min", "Severe burden"],
  ...tyOrder.map((t) => { const r = typ.find((x) => x.typology === t); return [t, tyDef[t], r.tracts, k(r.renter_hh), "$" + k(r.median_rent), (Number(r.median_jobs45) / 1e6).toFixed(2) + "M", (Number(r.burden50) * 100).toFixed(0) + "%"]; })],
  [1800, 2160, 700, 1100, 1100, 1250, 1250], { num: [2, 3, 4, 5, 6], hl: (i) => i <= 2 }));
children.push(spacer());
children.push(P(`Displacement watch tracts are concentrated in Harlem, East Harlem, Washington Heights and the West Bronx (Concourse, Mount Hope, Mount Eden). Their residents reach a median ${F.dw_j45} jobs yet pay a median ${F.dw_rent}, and the median tract poverty rate is ${F.dw_pov}. Service priority tracts include Norwood, Belmont, Williamsbridge, Tremont, Soundview, Bensonhurst and Far Rockaway: renters there face the highest severe rent burden (${F.sp_bur}) and reach a median of only ${F.sp_j45} jobs.`));
children.push(img("F6_equity_typology.png", 5.6));
children.push(caption("Figure 7. Planning typology of transit access, rent and renter vulnerability."));

children.push(H1("7. Scenario: the Interborough Express"));
children.push(P("The IBX is a proposed light-rail line on the Bay Ridge Branch and Fremont Secondary freight right-of-way from Brooklyn Army Terminal in Sunset Park to Jackson Heights. The MTA has published 18 station names, a 32-minute end-to-end run time and 5-minute service, but not station coordinates or timetables. Each station was placed where its named cross street meets the corridor in OpenStreetMap; the stations span 14.1 miles against the MTA's stated 14. A synthetic GTFS feed runs trains every 5 minutes through the morning peak analysed here, with 30-second dwells and running time split by distance, and the routing model is re-run with it added to today's network. Jobs, housing and all other service are held fixed, and platform-to-street time at stations in the rail cut is not modelled."));
children.push(P(`The IBX raises 45-minute job access by at least 5% in ${F.ibx_tracts} tracts (${F.ibx_tracts10} by at least 10%, ${F.ibx_tracts25} by at least 25%), home to ${F.ibx_pop} residents and ${F.ibx_rh} renter households. The median gaining tract gains ${F.ibx_med}. The 45-minute cut-off magnifies gains for tracts pushed across it: the same tracts gain a median ${F.ibx_med60} in jobs within 60 minutes and ${F.ibx_meddecay} on the decay-weighted measure. The largest gains are mostly in neighbourhoods whose transit lags their location: Glendale, Middle Village, Flatlands, Canarsie and parts of East Flatbush.`));
children.push(img("F7_ibx_access_gain.png", 5.6));
children.push(caption("Figure 8. Change in jobs reachable within 45 minutes with the IBX scenario."));
children.push(P([B("Table 7. "), run("Who gains, by renter vulnerability quartile (sample tracts)")], { keepNext: true, after: 60 }));
children.push(table([["Vulnerability quartile", "Tracts gaining ≥5%", "Share of tracts", "Share of gaining renter HH", "Share of all renter HH", "Avg. gain, all tracts"],
  ...byq.map((r) => [r.vul_q, k(r.tracts_gaining_5pct), (Number(r.share_gaining) * 100).toFixed(0) + "%", (Number(r.share_of_gaining_renter_hh) * 100).toFixed(0) + "%", (Number(r.share_of_all_sample_renter_hh) * 100).toFixed(0) + "%", "+" + (Number(r.pw_mean_pct_gain_all) * 100).toFixed(1) + "%"])],
  [1800, 1500, 1300, 1700, 1500, 1560], { num: true }));
children.push(caption("Average gain is population-weighted over all tracts in the quartile, including those that do not gain."));
children.push(P(`Along the corridor the IBX reaches vulnerable renters slightly more than proportionally: the two most vulnerable quartiles hold ${F.ibx_q34} of renter households in gaining tracts, against ${F.ibx_q34_base} of renter households in the sample. Citywide, the most vulnerable quartile gains least on average (+${F.ibx_q4_avg.replace("%", "")}% against +${F.ibx_q1_avg.replace("%", "")}% for the least vulnerable), because many of its members live in the Bronx and Upper Manhattan, which the line does not serve.`));
children.push(P(`Will gains turn into rent pressure? The IBX raises access without changing location, so Section 4 suggests modest effects, and ${F.ibx_unpriced_share} of the ${F.ibx_sample_gain} gaining tracts in the rent sample show no significant local access premium today. Table 8 brackets the answer with three capitalization rates: the excess-access elasticity, the SAC total effect (appropriate because whole stretches of the corridor gain together) and each tract's local MGWR coefficient. They describe today's cross-sectional relationship, not a forecast, and ignore anticipation, rezoning and new supply.`));
children.push(P([B("Table 8. "), run("Illustrative rent pressure in gaining tracts")], { keepNext: true, after: 60 }));
const prs = csv("06_ibx_pressure.csv");
children.push(table([["Rate applied to the access gain", "Rate", "Tracts", "Median", "90th percentile"],
  ...prs.map((r) => [r.bound, r.rate ? f3(r.rate) : "local", k(r.tracts), (Number(r.median_pct) * 100).toFixed(2) + "%", (Number(r.p90_pct) * 100).toFixed(1) + "%"])],
  [3860, 1100, 1100, 1500, 1800], { num: [1, 2, 3, 4] }));
children.push(spacer());
children.push(P(`The upper bound matters only where the local market already prices access. A precautionary screen keeps tracts with a gain of at least 5%, a significant local access premium and above-median renter vulnerability, excluding NYCHA-majority tracts: ${F.watch_tracts} tracts with ${F.watch_hh} renter households.`));
children.push(P([B("Table 9. "), run("Precautionary screen: largest neighbourhoods")], { keepNext: true, after: 60 }));
children.push(table([["Neighbourhood (NTA)", "Borough", "Tracts", "Renter HH", "Median access gain", "Rent pressure, low–high"],
  ...watch.slice(0, 8).map((r) => [r.ntaname, r.boroname, r.tracts, k(r.renter_hh), "+" + (Number(r.median_gain) * 100).toFixed(0) + "%", `${(Number(r.median_pressure_low) * 100).toFixed(1)}–${(Number(r.median_pressure_high) * 100).toFixed(1)}%`])],
  [2800, 1100, 800, 1300, 1560, 1800], { num: [2, 3, 4, 5] }));
children.push(spacer());

children.push(H1("8. Planning implications"));
children.push(
  bullet([B("Monitor before opening day where gains meet priced markets. "), run(`Tenant legal services, preservation of rent-regulated buildings and eviction tracking in the screened tracts (${F.watch_ntas}) are inexpensive insurance, even though the expected rent effect is small in most of the corridor.`)]),
  bullet([B("Treat transit-rich, low-rent neighbourhoods as assets to protect. "), run("Upper Manhattan and the West Bronx offer some of the city's best access at its lowest rents. Rezonings there should carry firm affordability requirements, and the pre-1974 regulated stock that holds rents down deserves preservation finance.")]),
  bullet([B("Target bus investment at service priority tracts. "), run("Norwood, Williamsbridge, Soundview, Bensonhurst and Far Rockaway combine low access with the highest severe rent burden; bus priority and frequency are the fastest ways to raise access there.")]),
  bullet([B("Report accessibility gains by renter vulnerability. "), run("Project evaluations usually count riders and travel-time savings. Reporting who gains access, and whether those places already price it, puts equity and displacement risk into the same analysis.")]),
);

children.push(H1("9. Limitations"));
children.push(
  bullet("The models are cross-sectional and identify associations, not causal effects of transit on rent."),
  bullet("ACS medians pool five years, reflect in-place tenants (including regulated leases), carry sampling error and are top-coded at $3,500; ACS renter year built is bottom-coded at 1939."),
  bullet("Controls cover the rental stock and public housing but not other subsidized housing (LIHTC, Mitchell-Lama, Section 8) or neighbourhood amenities such as parks, waterfront, schools and safety."),
  bullet("Jobs are LODES 2023 jobs inside New York City; jobs in New Jersey, Long Island and Westchester are excluded, some employers report jobs at headquarters, and jobs are not matched to residents' skills or wages."),
  bullet("Access is schedule-based. It does not capture reliability, crowding or fares, and scheduled bus times can overstate real speeds. Excess access is a residual and absorbs measurement error."),
  bullet("The IBX scenario uses approximate station sites, uniform running speeds, no station access time and no feeder-bus changes; it is a sketch-planning test, not a ridership or rent forecast."),
  bullet("MGWR inference is corrected for multiple testing, but local estimates remain sensitive to bandwidth choice."),
);

children.push(H1("10. Reproducibility"));
children.push(P("Every step runs from public data with a pinned Python environment (GeoPandas, r5py, PySAL spreg and esda, mgwr). One script downloads all sources and records each file's URL, date and checksum; numbered scripts rebuild the analysis in about 70 minutes on a laptop, and every number quoted in this report and the web atlas is read from the pipeline's outputs.", { keepNext: true }));
children.push(table([
  ["Step", "Script", "What it does"],
  ["00", "00_download_data.sh", "Download GTFS, OSM, ACS, PLUTO, LODES, boundaries; write manifest"],
  ["01", "01_build_base.py, 01b_osm_streets.py", "Tract geography, PLUTO controls, home- and job-weighted points; trim OSM"],
  ["02", "02_accessibility.py", "Baseline travel-time matrix and job access (r5py)"],
  ["03", "03_assemble.py", "Join ACS and access; model variables; sample flags"],
  ["04", "04_models.py, 04b_mgwr.py", "OLS, spatial models, centrality decomposition, robustness; MGWR"],
  ["05", "05_equity.py", "Bivariate LISA, vulnerability index, typology"],
  ["06", "06a/06b/06c", "IBX stations, scenario GTFS and routing, who gains, rent-pressure bounds"],
  ["07–08", "07_figures.py, 08_webmap_data.py", "Figures, quoted facts and the interactive web atlas"],
], [900, 3300, 5160]));
children.push(spacer());
children.push(P("Interactive atlas: an accompanying web map lets readers explore every layer in this report tract by tract.", { italics: true, color: MUTED }));

// ---------- document ----------
const doc = new Document({
  creator: "Wei Chen", title: "Paying for Centrality", description: "NYC transit job access, rent and the IBX",
  styles: { default: { document: { run: { font: FONT, size: 21, color: INK } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 28, bold: true, color: INK }, paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { font: FONT, size: 23, bold: true, color: ACCENT }, paragraph: { spacing: { before: 200, after: 80 }, outlineLevel: 1 } },
    ] },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } } },
    footers: { default: new Footer({ children: [new Paragraph({ tabStops: [{ type: TabStopType.RIGHT, position: 9360 }],
      children: [run("Paying for Centrality · Wei Chen", { size: 16, color: MUTED }), run("\t", { size: 16 }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: MUTED })] })] }) },
    children,
  }],
});
const out = path.join(ROOT, "report", "Paying_for_Centrality_WeiChen.docx");
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(out, b); console.log("wrote", out); });
