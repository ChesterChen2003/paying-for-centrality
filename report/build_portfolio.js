// Portfolio pages for "Paying for Centrality" (13.33 × 7.5 in, five pages).
// Layout follows a numbered-section portfolio format: a project number block,
// grey section tabs, text above figures, key numbers in a side column.
// Every number is read from outputs/tables/facts.json.
//   node report/build_portfolio.js  →  report/Paying_for_Centrality_Portfolio.pptx
const fs = require("fs");
const path = require("path");
const pptxgen = require("pptxgenjs");
// Optional: write the palette into the deck theme (helper from the pptx skill, if available)
let applyTheme = null;
try { ({ applyTheme } = require(path.join(process.env.PPTX_SKILL || "", "scripts/apply_theme.js"))); } catch (e) {}

const ROOT = path.resolve(__dirname, "..");
const F = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/tables/facts.json"), "utf8"));
const IMG = (n) => path.join(ROOT, "outputs/figures/portfolio", n);
const OUT = path.join(__dirname, "Paying_for_Centrality_Portfolio.pptx");
const PROJECT_NO = process.env.PROJECT_NO || "1";

const THEME = {
  name: "Paying for Centrality",
  headFontFace: "Arial",
  bodyFontFace: "Arial",
  colors: {
    dk1: "1D1D1F", lt1: "FFFFFF", dk2: "4A4A48", lt2: "F3F3F1",
    accent1: "2A6FC2", accent2: "C9581F", accent3: "16865C",
    accent4: "6E6E6E", accent5: "8A8A86", accent6: "EB6834",
    hlink: "2A6FC2", folHlink: "6E6E6E",
  },
};
const HEX = {
  ink: "1D1D1F", ink2: "3A3A39", muted: "6B6B68", hair: "D6D5D0", tab: "6E6E6E", chip: "F3F3F1",
  meas: "EEF2F6", measLine: "8496A9",
  rq1: "2A6FC2", rq1t: "EAF2FC", rq2: "C9581F", rq2t: "FDF0E8", rq3: "16865C", rq3t: "E8F6EF",
  blue: "3987E5", orange: "EB6834",
};

// ---- grid -----------------------------------------------------------------------------
const PW = 13.333, ML = 0.5, MT = 0.45;
const COL_W = 5.95, GUT = 0.433;
const A = ML, B = ML + COL_W + GUT;                 // column x
const TAB_H = 0.36, TEXT_Y = 0.95, FIG_Y = 2.05, MAP_W = 4.55, MAP_H = 4.95;
const BODY = 10.5, SMALL = 8.5;

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = "Wei Chen";
pres.title = "Paying for Centrality — portfolio pages";
pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
const C = pres.SchemeColor;
pres.defineSlideMaster({ title: "Portfolio page", background: { color: "FFFFFF" } });

let objN = 0;
const nm = (s) => `${s}-${++objN}`;

function tab(slide, x, y, label, w = 4.3) {
  slide.addText(label, {
    x, y, w, h: TAB_H, fill: { color: HEX.tab }, color: "FFFFFF", bold: true, fontSize: 12,
    margin: [9, 0, 0, 0], valign: "middle", isTextBox: true, objectName: nm("tab"),
  });
}

function body(slide, x, y, w, h, text, opts = {}) {
  slide.addText(text, {
    x, y, w, h, fontSize: BODY, color: HEX.ink2, valign: "top", margin: 0,
    lineSpacingMultiple: 1.12, paraSpaceAfter: 4, isTextBox: true, objectName: nm("text"), ...opts,
  });
}

function stat(slide, x, y, w, big, label, h = 0.95, bigSize = 20) {
  slide.addText([
    { text: big, options: { fontSize: bigSize, bold: true, color: HEX.ink, breakLine: true } },
    { text: label, options: { fontSize: SMALL, color: HEX.muted } },
  ], { x, y, w, h, margin: 0, valign: "top", lineSpacingMultiple: 1.05, isTextBox: true, objectName: nm("stat") });
}

function img(slide, file, x, y, w, h, alt, border = false) {
  slide.addImage({ path: IMG(file), x, y, w, h, altText: alt, objectName: nm("figure") });
  if (border) slide.addShape(pres.shapes.RECTANGLE, {
    x, y, w, h, fill: { type: "none" }, line: { color: HEX.hair, width: 0.75 }, objectName: nm("frame"),
  });
}

function line(slide, x, y, w, h, color = "6B6B68", arrow = false, dash = "solid") {
  slide.addShape(pres.shapes.LINE, {
    x, y, w, h, line: { color, width: 0.9, dashType: dash, ...(arrow ? { endArrowType: "triangle" } : {}) },
    objectName: nm("connector"),
  });
}

function box(slide, x, y, w, h, title, sub, fill, lineColor, titleColor = HEX.ink, bold = true) {
  slide.addText([
    { text: title, options: { bold, fontSize: 8.5, color: titleColor, breakLine: !!sub } },
    ...(sub ? [{ text: sub, options: { fontSize: 7.5, color: HEX.ink2 } }] : []),
  ], {
    shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.05, x, y, w, h,
    fill: { color: fill }, line: lineColor ? { color: lineColor, width: 0.75 } : { type: "none" },
    margin: [7, 6, 2, 2], valign: "middle", lineSpacingMultiple: 1.0, objectName: nm("box"),
  });
}

function label(slide, x, y, w, text, opts = {}) {
  slide.addText(text, {
    x, y, w, h: 0.2, fontSize: 7.5, bold: true, color: HEX.muted, charSpacing: 1, margin: 0,
    valign: "bottom", isTextBox: true, objectName: nm("label"), ...opts,
  });
}

pres.addSection({ title: "Paying for Centrality" });
const SEC = "Paying for Centrality";

// =========================================================================================
// Page 1 — introduction, research questions, study design
// =========================================================================================
{
  const s = pres.addSlide({ masterName: "Portfolio page", sectionTitle: SEC });
  s.addText(PROJECT_NO, {
    x: A, y: MT, w: 0.95, h: 0.95, fill: { color: "000000" }, color: "FFFFFF", bold: true,
    fontSize: 64, align: "right", valign: "bottom", margin: [0, 2, -6, 0], isTextBox: true,
    objectName: "project-number",
  });
  s.addText([
    { text: "Paying for Centrality", options: { fontSize: 19, bold: true, color: HEX.ink, breakLine: true } },
    { text: "Transit Job Access, Rent and the Interborough Express in New York City",
      options: { fontSize: 12, bold: true, color: HEX.ink, breakLine: true } },
    { text: "Independent research project, 2026 · rebuilt from my 2025 course project",
      options: { fontSize: 9.5, color: HEX.muted, breakLine: true } },
    { text: "Python (GeoPandas, r5py, PySAL, mgwr) · D3 web atlas",
      options: { fontSize: 9.5, color: HEX.muted } },
  ], { x: A + 1.12, y: MT - 0.04, w: COL_W - 1.12, h: 1.3, margin: 0, valign: "top",
       paraSpaceAfter: 2, isTextBox: true, objectName: "project-title" });

  s.addText("1 Introduction", { x: A, y: 1.95, w: COL_W, h: 0.3, fontSize: 13, bold: true,
    color: HEX.ink, margin: 0, isTextBox: true, objectName: "h-intro" });
  body(s, A, 2.3, COL_W, 1.3,
    `New York's subway and bus network puts ${F.share_1m} of the city's ${F.pop_total_m} million residents ` +
    "within 45 minutes of a million jobs. Planners often assume that access is priced into rent, which turns " +
    "every transit improvement into a question about who benefits. My 2025 version of this project correlated " +
    "a stop-density index with rent across about 165 neighborhoods. This version rebuilds it at the census-tract " +
    "level with schedule-based job accessibility, spatial econometrics and a scenario test of the proposed " +
    "Interborough Express (IBX).");

  s.addText("2 Research Questions", { x: A, y: 3.72, w: COL_W, h: 0.3, fontSize: 13, bold: true,
    color: HEX.ink, margin: 0, isTextBox: true, objectName: "h-rq" });
  const rqs = [
    ["RQ1", HEX.rq1, "Is transit job access priced into rent once housing stock and location are held constant?"],
    ["RQ2", HEX.rq2, "Where do access and rent diverge, and which renters live there?"],
    ["RQ3", HEX.rq3, "Who would gain access from the IBX, and where could gains turn into rent pressure?"],
  ];
  rqs.forEach(([k, col, q], i) => {
    const y = 4.08 + i * 0.46;
    s.addText(k, { x: A, y, w: 0.48, h: 0.24, fill: { color: col }, color: "FFFFFF", bold: true,
      fontSize: 8.5, align: "center", valign: "middle", margin: 0, isTextBox: true, objectName: nm("rq-key") });
    body(s, A + 0.6, y - 0.02, COL_W - 0.6, 0.4, q, { fontSize: 10 });
  });

  s.addText("What changed from the 2025 version", { x: A, y: 5.42, w: COL_W, h: 0.24, fontSize: 9.5,
    bold: true, color: HEX.ink, margin: 0, isTextBox: true, objectName: "h-changes" });
  const hb = { type: "solid", pt: 0.75, color: "8A8A86" }, hl = { type: "solid", pt: 0.5, color: HEX.hair },
        no = { type: "none" };
  const cell = (t, o = {}) => ({ text: t, options: { fontSize: 8, color: HEX.ink2, valign: "middle",
    margin: [0.02, 0.05, 0.02, 0], border: [no, no, hl, no], ...o } });
  const head = (t) => cell(t, { bold: true, color: HEX.ink, border: [no, no, hb, no] });
  s.addTable([
    [head(""), head("2025"), head("2026")],
    [cell("Unit", { bold: true }), cell("~165 NTAs"), cell(`${F.tracts_all} census tracts, EPSG:2263`)],
    [cell("Access", { bold: true }), cell("Stop density, 400 m buffers"), cell("Jobs within 45 min by transit (R5, GTFS, LODES)")],
    [cell("Model", { bold: true }), cell("Bivariate OLS"), cell("Hedonic OLS, spatial lag / error / SAC, MGWR")],
    [cell("Equity", { bold: true }), cell("—"), cell("Bivariate LISA, renter-vulnerability typology")],
    [cell("Scenario", { bold: true }), cell("—"), cell("IBX GTFS scenario, rent-pressure screen")],
  ], { x: A, y: 5.7, w: COL_W, colW: [0.85, 1.75, 3.35], rowH: 0.22, objectName: "table-changes" });

  // ---- 3 Study design (native diagram) ----
  tab(s, B, MT, "3 Study Design");
  const cw = (COL_W - 0.24) / 3, cx = (i) => B + i * (cw + 0.12), mid = (i) => cx(i) + cw / 2;
  label(s, B, 0.93, COL_W, "PUBLIC DATA");
  ["MTA GTFS, subway + bus", "OpenStreetMap", "LEHD LODES 2023 jobs",
   "ACS 2020–24, 5-year", "PLUTO 26v2", "DCP 2020 tracts"].forEach((t, i) => {
    box(s, cx(i % 3), 1.17 + Math.floor(i / 3) * 0.4, cw, 0.32, t, null, HEX.chip, null, HEX.ink, false);
  });
  line(s, B + COL_W / 2, 1.93, 0, 0.27, "6B6B68", true);
  label(s, B, 2.2, COL_W, `TRACT MEASURES · ${F.tracts_all} TRACTS`);
  [["Job accessibility", "R5 routing, 7–8 AM, 45 min"], ["Rent and housing stock", "ACS rent, PLUTO controls"],
   ["Renter vulnerability", "Burden, poverty, renter share"]].forEach(([t, u], i) => {
    box(s, cx(i), 2.44, cw, 0.56, t, u, HEX.meas, HEX.measLine);
    line(s, mid(i), 3.0, 0, 0.15);
  });
  line(s, mid(0), 3.15, mid(2) - mid(0), 0);
  const RQ = [
    ["RQ1  Capitalization", "Is access priced into rent?", HEX.rq1, HEX.rq1t, [
      ["Hedonic OLS", "Rent ~ access + stock + borough"], ["Spatial models", "LM tests; lag, error, SAC"],
      ["Centrality decomposition", "Location vs. excess access"], ["MGWR", "Local access premium"]]],
    ["RQ2  Spatial equity", "Where do access and rent diverge?", HEX.rq2, HEX.rq2t, [
      ["Bivariate LISA", "Access vs. neighbors' rent, FDR"], ["Planning typology", "Access × rent × vulnerability"]]],
    ["RQ3  IBX scenario", "Who would gain?", HEX.rq3, HEX.rq3t, [
      ["Scenario network", "18 stations, synthetic GTFS"], ["Re-route", "Change in jobs within 45 min"],
      ["Who gains", "By vulnerability and type"], ["Rent-pressure screen", "Bracketed by RQ1 rates"]]],
  ];
  const H0 = 3.4, HH = 0.52, SY = (k) => 4.12 + k * 0.68, SH = 0.5;
  RQ.forEach(([t, q, col, tint, steps], i) => {
    line(s, mid(i), 3.15, 0, H0 - 3.15, "6B6B68", true);
    s.addText([
      { text: t, options: { bold: true, fontSize: 9.5, color: "FFFFFF", breakLine: true } },
      { text: q, options: { fontSize: 7.5, color: "FFFFFF" } },
    ], { shape: pres.shapes.ROUNDED_RECTANGLE, rectRadius: 0.05, x: cx(i), y: H0, w: cw, h: HH,
         fill: { color: col }, line: { type: "none" }, margin: [7, 6, 2, 2], valign: "middle",
         objectName: nm("rq-head") });
    steps.forEach(([st, sub], k) => {
      line(s, mid(i), k === 0 ? H0 + HH : SY(k - 1) + SH, 0, k === 0 ? SY(0) - H0 - HH : SY(k) - SY(k - 1) - SH,
           "6B6B68", true);
      box(s, cx(i), SY(k), cw, SH, st, sub, tint, col);
    });
  });
  // links into the IBX stream
    line(s, mid(1), SY(1) + SH, 0, SY(2) + SH / 2 - SY(1) - SH, HEX.rq2);
  line(s, mid(1), SY(2) + SH / 2, cx(2) - mid(1), 0, HEX.rq2, true);
  line(s, cx(0) + cw, SY(3) + SH / 2, cx(2) - cx(0) - cw, 0, HEX.rq1, true);
  s.addText("capitalization rates", { x: cx(1), y: SY(3) + 0.02, w: cw, h: 0.2, fontSize: 7.5, italic: true,
    color: HEX.rq1, align: "center", margin: 0, isTextBox: true, objectName: "link-label" });
  s.addText("vulnerability, type", { x: mid(1) + 0.08, y: SY(2) + SH / 2 - 0.22, w: cx(2) - mid(1) - 0.12,
    h: 0.2, fontSize: 7.5, italic: true, color: HEX.rq2, align: "center", margin: 0, isTextBox: true,
    objectName: "link-label" });
}

// =========================================================================================
// Page 2 — access and rent
// =========================================================================================
{
  const s = pres.addSlide({ masterName: "Portfolio page", sectionTitle: SEC });
  const SX = A + MAP_W + 0.2, SW = COL_W - MAP_W - 0.2;
  tab(s, A, MT, "4 Transit Job Accessibility");
  body(s, A, TEXT_Y, COL_W, 1.0,
    "Accessibility counts the jobs a resident can reach by subway, bus and walking within 45 minutes. " +
    "Trips were routed with Conveyal R5 on MTA's October 2026 schedules and an OpenStreetMap walking " +
    "network, departing every minute from 7 to 8 AM on a weekday; the median of the 60 departures is used. " +
    "Origins are weighted by homes (PLUTO), destinations by LEHD LODES 2023 jobs.");
  img(s, "P1_job_access.png", A, FIG_Y, MAP_W, MAP_H, "Map of jobs reachable by transit within 45 minutes by census tract");
  stat(s, SX, FIG_Y, SW, F.pw_jobs45, "jobs within 45 min for the average resident", 1.0);
  stat(s, SX, FIG_Y + 1.1, SW, F.share_1m, "of residents reach at least a million jobs", 1.0);
  s.addText([
    { text: "Median tract", options: { bold: true, fontSize: SMALL, color: HEX.ink, breakLine: true } },
    ...[["Manhattan", F.med_j45_mn], ["Brooklyn", F.med_j45_bk], ["Queens", F.med_j45_qn],
        ["Bronx", F.med_j45_bx], ["Staten Island", F.med_j45_si]].map(([b, v], i, a) => (
      [{ text: `${b}  `, options: { fontSize: SMALL, color: HEX.muted } },
       { text: v, options: { fontSize: SMALL, bold: true, color: HEX.ink, breakLine: i < a.length - 1 } }])).flat(),
  ], { x: SX, y: FIG_Y + 2.2, w: SW, h: 1.2, margin: 0, valign: "top", lineSpacingMultiple: 1.2,
       isTextBox: true, objectName: "median-by-borough" });

  const SX2 = B + MAP_W + 0.2;
  tab(s, B, MT, "5 Rent");
  body(s, B, TEXT_Y, COL_W, 1.0,
    `Median gross rent (rent plus utilities) comes from the ACS 2020–24 five-year estimates for the ` +
    `${F.tracts_sample} tracts with at least 50 renter households. Rents peak below 96th Street and in ` +
    "brownstone Brooklyn, but northeastern and western Queens also top $2,000. The lowest rents sit in " +
    "public-housing tracts, where rent is set by income.");
  img(s, "P2_rent.png", B, FIG_Y, MAP_W, MAP_H, "Map of median gross rent by census tract");
  stat(s, SX2, FIG_Y, SW, F.median_rent, "median gross rent across sample tracts", 1.0);
  stat(s, SX2, FIG_Y + 1.1, SW, F.tracts_sample, "tracts in the rent models", 1.0);
  stat(s, SX2, FIG_Y + 2.2, SW, String(F.n_topcoded), "rents top-coded at $3,500+; handled with a Tobit check", 1.1);
}

// =========================================================================================
// Page 3 — capitalization and the centrality decomposition
// =========================================================================================
{
  const s = pres.addSlide({ masterName: "Portfolio page", sectionTitle: SEC });
  tab(s, A, MT, "6 Is Access Priced into Rent?");
  body(s, A, TEXT_Y, COL_W, 1.05,
    "A hedonic model regresses log rent on log 45-minute job access, controlling for renter-stock age, rooms, " +
    `the pre-1974 rent-stabilized share, NYCHA share and borough. OLS residuals cluster (Moran's I = ${F.moran_m3}) ` +
    "and both robust LM tests are significant, so the preferred model combines a spatial lag and a spatial error (SAC). " +
    `Doubling access goes with about ${F.pct_2x_sac} higher rent in the tract itself, ${F.pct_2x_sac_total} including spillovers.`);
  const hb = { type: "solid", pt: 0.75, color: "8A8A86" }, hl = { type: "solid", pt: 0.5, color: HEX.hair },
        no = { type: "none" };
  const c = (t, o = {}) => ({ text: t, options: { fontSize: 8.5, color: HEX.ink2, valign: "middle",
    margin: [0.02, 0.05, 0.02, 0], border: [no, no, hl, no], ...o } });
  const h = (t, al = "left") => c(t, { bold: true, color: HEX.ink, align: al, border: [no, no, hb, no] });
  const pref = { bold: true, color: HEX.ink };
  s.addTable([
    [h("Model"), h("Access elasticity (SE)", "right"), h("R²", "right"), h("Residual Moran's I", "right")],
    [c("OLS, access only"), c("0.051 (0.006)", { align: "right" }), c(F.r2_m1, { align: "right" }), c("0.40", { align: "right" })],
    [c("OLS + housing stock + borough"), c(`${F.b_m3} (0.006)`, { align: "right" }), c(F.r2_m3, { align: "right" }), c(F.moran_m3, { align: "right" })],
    [c("Spatial lag (ML)"), c("0.043 (0.005)", { align: "right" }), c("0.65", { align: "right" }), c("0.00", { align: "right" })],
    [c("Spatial error (ML)"), c(`${F.b_sem} (0.011)`, { align: "right" }), c("0.49", { align: "right" }), c("−0.03", { align: "right" })],
    [c("SAC (GMM), direct effect", pref), c(`${F.b_sac} (${F.se_sac})`, { align: "right", ...pref }), c("–", { align: "right" }), c("–", { align: "right" })],
    [c("SAC (GMM), total effect", pref), c(`${F.b_sac_total} (0.017)`, { align: "right", ...pref }), c("–", { align: "right" }), c("–", { align: "right" })],
  ], { x: A, y: 2.08, w: COL_W, colW: [2.45, 1.45, 0.75, 1.3], rowH: 0.235, objectName: "table-models" });
  s.addText(`n = ${F.tracts_sample} tracts. R² is pseudo-R² for the ML models; SAC ρ = ${F.rho_sac}. ` +
            "Bold: preferred model.", { x: A, y: 3.78, w: COL_W, h: 0.2, fontSize: 7.5,
    color: HEX.muted, margin: 0, isTextBox: true, objectName: "table-note" });
  s.addText("One citywide slope, five borough slopes: access is priced in Manhattan and Brooklyn",
    { x: A, y: 4.1, w: COL_W, h: 0.22, fontSize: SMALL, bold: true, color: HEX.ink, margin: 0, valign: "bottom",
      isTextBox: true, objectName: "fig-caption" });
  img(s, "P3_slopes.png", A, 4.38, COL_W, 2.62, "Scatter plots of rent against job access, citywide and by borough");

  const SX = B + MAP_W + 0.2, SW = COL_W - MAP_W - 0.2;
  tab(s, B, MT, "7 Centrality or Transit?");
  body(s, B, TEXT_Y, COL_W, 1.05,
    `Access and centrality are nearly the same variable: a within-borough spline in distance to the nearest CBD explains ${F.r2_dist_within} ` +
    "of the variation in access. Splitting access into the part location predicts and the remainder (excess access) " +
    "shows where the premium sits. Red tracts get more transit than their location delivers, at little or no extra rent: " +
    "Jamaica, the West Bronx and the Queens Boulevard corridor.");
  img(s, "P4_excess_access.png", B, FIG_Y, MAP_W, MAP_H, "Map of transit access relative to what location predicts");
  stat(s, SX, FIG_Y, SW, F.r2_dist_within, "of the variation in access explained by location", 1.0);
  stat(s, SX, FIG_Y + 1.1, SW, F.b_loc, "rent elasticity of location-predicted access", 1.0);
  stat(s, SX, FIG_Y + 2.2, SW, F.b_excess, `of access beyond location (p = ${F.p_excess}; ` +
       `${F.excess_min.replace("-", "−")} to ${F.excess_max} across four location models)`, 1.4);
}

// =========================================================================================
// Page 4 — local premium and equity typology
// =========================================================================================
{
  const s = pres.addSlide({ masterName: "Portfolio page", sectionTitle: SEC });
  const SX = A + MAP_W + 0.2, SW = COL_W - MAP_W - 0.2;
  tab(s, A, MT, "8 Where Is Access Priced?");
  body(s, A, TEXT_Y, COL_W, 1.05,
    "A multiscale geographically weighted regression (MGWR) lets each coefficient vary over its own bandwidth. " +
    `The access coefficient varies over about ${F.mgwr_bw} neighboring tracts, roughly ${F.mgwr_cd} community districts, ` +
    "so it compares places that share a broad location. Access carries a local premium in Manhattan and much of " +
    "Brooklyn, and none in the Bronx or on Staten Island.");
  img(s, "P5_mgwr.png", A, FIG_Y, MAP_W, MAP_H, "Map of the MGWR local access coefficient");
  s.addText("Tracts with a significant positive premium", { x: SX, y: FIG_Y, w: SW, h: 0.45, fontSize: SMALL,
    bold: true, color: HEX.ink, margin: 0, valign: "top", isTextBox: true, objectName: "bars-title" });
  const bars = [["Manhattan", F.mgwr_mn], ["Brooklyn", F.mgwr_bk], ["Queens", F.mgwr_qn], ["Bronx", F.mgwr_bx],
                ["Staten Island", F.mgwr_si]];
  bars.forEach(([b, v], i) => {
    const y = FIG_Y + 0.55 + i * 0.44, pct = parseFloat(v) / 100, bw = SW - 0.42;
    s.addText(b, { x: SX, y, w: SW, h: 0.17, fontSize: 7.5, color: HEX.ink2, margin: 0, isTextBox: true,
      objectName: nm("bar-label") });
    s.addShape(pres.shapes.RECTANGLE, { x: SX, y: y + 0.19, w: bw, h: 0.11, fill: { color: "EDECE8" },
      line: { type: "none" }, objectName: nm("bar-track") });
    if (pct > 0) s.addShape(pres.shapes.RECTANGLE, { x: SX, y: y + 0.19, w: bw * pct, h: 0.11,
      fill: { color: "D94C4C" }, line: { type: "none" }, objectName: nm("bar") });
    s.addText(v, { x: SX + bw + 0.04, y: y + 0.13, w: 0.38, h: 0.22, fontSize: 7.5, bold: true, color: HEX.ink,
      margin: 0, valign: "middle", isTextBox: true, objectName: nm("bar-value") });
  });
  stat(s, SX, FIG_Y + 2.95, SW, F.mgwr_r2, `MGWR R² (OLS: ${F.r2_m3})`, 1.0);

  tab(s, B, MT, "9 Equity Typology");
  body(s, B, TEXT_Y, COL_W, 1.05,
    "Crossing access and rent at their citywide medians with a renter-vulnerability index (severe rent burden, " +
    "poverty, renter share) gives six planning types. Displacement watch: high access, low rent, high vulnerability. " +
    "Service priority: low access, low rent, high vulnerability. A bivariate LISA (FDR-adjusted) finds " +
    `${F.lisa_hl_fdr} significant high-access, low-rent tracts.`);
  img(s, "P6_typology.png", B, FIG_Y, 3.55, MAP_H, "Map of the planning typology");
  const TX = B + 3.55 + 0.2, TW = COL_W - 3.55 - 0.2;
  const types = [
    ["EB6834", "Displacement watch", `${F.dw_tracts} tracts · ${F.dw_hh} renter HH`, `median rent ${F.dw_rent}, ${F.dw_pov} poverty`],
    ["2A78D6", "Service priority", `${F.sp_tracts} tracts · ${F.sp_hh} renter HH`, `${F.sp_bur} severely rent-burdened`],
    ["1BAF7A", "Established access premium", `${F.ea_tracts} tracts · 831k renter HH`, "high access, high rent"],
    ["7D7C77", "Public housing (NYCHA ≥ 50%)", `${F.ph_tracts} tracts · ${F.ph_hh} renter HH`, "rent set by income"],
    ["BDBCB6", "Car-oriented / amenity", `${F.co_tracts} tracts · 204k renter HH`, "low access, high rent"],
    ["DEDCD6", "Middle", `${F.mi_tracts} tracts · 210k renter HH`, "near the medians"],
  ];
  types.forEach(([col, t, a, b], i) => {
    const y = FIG_Y + i * 0.66;
    s.addShape(pres.shapes.RECTANGLE, { x: TX, y: y + 0.03, w: 0.16, h: 0.16, fill: { color: col },
      line: { type: "none" }, objectName: nm("swatch") });
    s.addText([
      { text: t, options: { bold: true, fontSize: SMALL, color: HEX.ink, breakLine: true } },
      { text: a, options: { fontSize: 7.5, color: HEX.ink2, breakLine: true } },
      { text: b, options: { fontSize: 7.5, color: HEX.muted } },
    ], { x: TX + 0.25, y, w: TW - 0.25, h: 0.62, margin: 0, valign: "top", lineSpacingMultiple: 1.05,
         isTextBox: true, objectName: nm("type") });
  });
  const ny = FIG_Y + types.length * 0.66 + 0.05;
  s.addShape(pres.shapes.RECTANGLE, { x: TX, y: ny + 0.02, w: 0.16, h: 0.16, fill: { color: "F1F0EC" },
    line: { color: HEX.hair, width: 0.5 }, objectName: "swatch-none" });
  s.addText("No residents, or not in the rent sample", { x: TX + 0.25, y: ny, w: TW - 0.25, h: 0.36,
    fontSize: 7.5, color: HEX.muted, margin: 0, valign: "top", isTextBox: true, objectName: "type-none" });
}

// =========================================================================================
// Page 5 — IBX scenario, implications, atlas
// =========================================================================================
{
  const s = pres.addSlide({ masterName: "Portfolio page", sectionTitle: SEC });
  const IW = 4.4, SX = A + IW + 0.2, SW = COL_W - IW - 0.2;
  tab(s, A, MT, "10 Interborough Express Scenario");
  body(s, A, TEXT_Y, COL_W, 1.05,
    "The IBX would run about 14 miles on the Bay Ridge Branch and Fremont Secondary, from Sunset Park to Jackson Heights. " +
    "I sited its 18 stations on the right-of-way in OpenStreetMap, wrote a synthetic GTFS feed with MTA's public " +
    "parameters (32 minutes end to end, trains every 5 minutes) and re-routed every tract with the baseline settings.");
  img(s, "P7_ibx.png", A, FIG_Y, IW, MAP_H, "Map of IBX scenario gains in 45-minute job access");
  stat(s, SX, FIG_Y, SW, F.ibx_pop, `residents in ${F.ibx_tracts} tracts gain ≥ 5% access`, 0.92);
  stat(s, SX, FIG_Y + 0.98, SW, `+${F.ibx_med}`, `median gain in gaining tracts (${F.ibx_med60} at 60 min)`, 0.92);
  stat(s, SX, FIG_Y + 1.96, SW, F.ibx_q34, `of their renters are in the two most vulnerable quartiles (${F.ibx_q34_base} citywide)`, 1.05);
  stat(s, SX, FIG_Y + 3.07, SW, "0.4–1.7%", `illustrative rent pressure, median (${F.press_high} where access is already priced)`, 1.05, 16);
  stat(s, SX, FIG_Y + 4.18, SW, `${F.watch_tracts} tracts`, `${F.watch_hh} renter HH flagged by the precautionary screen`, 0.8, 16);

  tab(s, B, MT, "11 Planning Implications");
  const imp = [
    ["Monitor before opening day ", "where gains meet priced markets: tenant services and rent-regulated preservation in Ocean Hill, Bushwick, East Flatbush, Flatbush and Ridgewood."],
    ["Protect transit-rich, low-rent neighborhoods ", "such as Upper Manhattan and the West Bronx; rezonings there need firm affordability requirements."],
    ["Target bus priority and frequency ", "at service-priority tracts such as Norwood, Soundview, Bensonhurst and Far Rockaway."],
    ["Report accessibility gains by renter vulnerability ", "alongside riders and travel-time savings in project evaluations."],
  ];
  s.addText(imp.flatMap(([b, t], i) => [
    { text: b, options: { bold: true, color: HEX.ink } },
    { text: t, options: { color: HEX.ink2, breakLine: i < imp.length - 1 } },
  ]), { x: B, y: TEXT_Y, w: COL_W, h: 1.95, fontSize: 10, margin: 0, valign: "top", paraSpaceAfter: 6,
        lineSpacingMultiple: 1.1, isTextBox: true, objectName: "implications" });

  s.addText([
    { text: "Interactive atlas  ", options: { bold: true, color: HEX.ink, fontSize: 10 } },
    { text: "chesterchen2003.github.io/paying-for-centrality", options: {
      color: HEX.rq1, fontSize: 9, hyperlink: { url: "https://chesterchen2003.github.io/paying-for-centrality/" } }, },
  ], { x: B, y: 3.0, w: COL_W, h: 0.22, margin: 0, isTextBox: true, objectName: "atlas-link" });
  s.addText([
    { text: "Code and data  ", options: { bold: true, color: HEX.ink, fontSize: 10 } },
    { text: "github.com/ChesterChen2003/paying-for-centrality", options: {
      color: HEX.rq1, fontSize: 9, hyperlink: { url: "https://github.com/ChesterChen2003/paying-for-centrality" } } },
  ], { x: B, y: 3.26, w: COL_W, h: 0.22, margin: 0, isTextBox: true, objectName: "repo-link" });
  img(s, "P8_atlas_crop.png", B, 3.6, COL_W, 3.4, "Screenshot of the interactive web atlas", true);
}

(async () => {
  await pres.writeFile({ fileName: OUT });
  if (applyTheme) await applyTheme(OUT, THEME);
  console.log("Wrote", OUT);
})();
