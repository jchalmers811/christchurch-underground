# Decisions log

Each entry: what was decided, why, and what was rejected.

---

## D-001: Publish only derived NZGD data

- **Date:** 2026-11-10
- **Phase:** 0
- **Status:** Accepted (provisional until NZGD replies to the purpose email)

**Context.** The NZGD Terms of Use (version of 26/11/2024) allow users to download, store, copy, adapt, use and disclose geotechnical data for the NZGD's purposes (cl. 6.1). They forbid publishing it on another website "in unaltered form" (cl. 6.2) and forbid working around the portal's technical limits (cl. 5.3). If you register with an organisation's email address, you accept the terms on that organisation's behalf (cl. 3.2).

**Decision.**
1. Register with a personal email address.
2. Keep raw NZGD files in `data/raw/` (git-ignored). They are never committed, never stored as CI artefacts and never hosted.
3. Publish only derived data: classified soil intervals, layer tops and interpolated surfaces, each with the NZGD record ID.
4. No scraping. Download only through the portal's own features.
5. Show this notice in the app and README: "Includes data derived from the New Zealand Geotechnical Database (MBIE), accessed free of charge and provided without warranty as to accuracy or fitness for purpose."
6. Email NZGD/MBIE to confirm (a) that a public, non-commercial portfolio project fits the NZGD's purpose (cl. 2, 5.2), and (b) that a map of investigation locations counts as altered/derived data.

**Rejected.**
- *Republishing raw CPT traces*: forbidden by cl. 6.2.
- *Leaving NZGD out entirely*: it's by far the densest data source, and the terms explicitly allow adapting the data.

**Open.** NZGD's reply to the email in point 6 (record it here).

**Update 2026-11-18.** The first NZGD application was declined with a generic "not enough information" reply. Plan: reapply with a fuller description of the project and how it complies with the terms. Until then, nothing NZGD-derived is published.

---

## D-002: Publish derived OSU data under ODC-BY

- **Date:** 2026-11-18
- **Phase:** 0
- **Status:** Accepted

**Context.** The OSU DesignSafe dataset (PRJ-3352, doi:10.17603/ds2-fy1v-hh47) is licensed under the Open Data Commons Attribution License (ODC-BY), according to its DesignSafe project page. The DataCite record has no licence field. ODC-BY allows sharing and adapting the data as long as it's attributed. The NZGD application was declined for lack of information, so for now OSU is the only CPT source that can be published (see D-001).

**Decision.**
1. Publish the Phase 0 page (`site/index.html`) on GitHub Pages. It contains derived OSU data: positions, soil behaviour type intervals and groundwater depths.
2. Keep raw OSU files in `data/raw/` (git-ignored) anyway, so there's one rule for all raw data, and so a later NZGD download can't be committed by accident next to them.
3. Show DesignSafe's citation and the ODC-BY licence in the page footer.
4. The NZGD investigations on the OSU lines appear only as positions measured by OSU (from the OSU summary tables), never with NZGD data.

**Rejected.**
- *Committing the raw OSU CSVs*: allowed by ODC-BY, but it mixes licensed and restricted raw data in one place for no gain.
- *Building the page in CI*: CI doesn't have the raw files, so the generated page is committed instead. Rebuild it with `python -m chch_pipeline.page`.

---

## D-003: Publish ECan well locations, without owner details

- **Date:** 2026-11-18
- **Phase:** 0
- **Status:** Accepted

**Context.** ECan's "Wells & Bores – Existing" open data is licensed CC BY 4.0 on data.govt.nz. The Canterbury Maps website terms separately say the website's information can't be republished in "any substantial amount" without the councils' consent. They don't say whether that covers open-data downloads that carry their own licence. The download also includes `WELL_OWNER` (often a private person's name) and `ROAD_OR_STREET`.

**Decision.**
1. Publish wells inside the urban Christchurch box (NZTM E 1,562,000–1,582,000, N 5,172,000–5,190,000; 5,946 wells) on the public map, relying on the dataset's own CC BY 4.0 licence, with attribution in the page footer and README.
2. Publish only an allowlist of technical fields: well number, position, depth, year drilled, use, layer count and initial water level. **Owner names and street addresses are never read into the pipeline output.** A test checks this.
3. Link each well to ECan Well Search instead of copying its bore log image.

**Rejected.**
- *Publishing every field*: owner names are personal information and add nothing to the project.
- *Asking for consent before publishing anything*: the dataset is explicitly published as open data under CC BY 4.0. If ECan objects, removing the layer is one change.

**Open.** If the project later copies bore log text out of the Well Search PNGs, check the Well Search Terms of Use first.

---

## D-004: deck.gl for the 3D viewer, starting with an orbit view per site

- **Date:** 2026-11-18
- **Phase:** 1 (started early, before Phase 0 is finished)
- **Status:** Accepted

**Context.** The plan left deck.gl vs CesiumJS open until Phase 1. The first 3D view shows the four OSU sites: lines of CPTs about 25 m long and up to 20 m deep. The viewer has to look *under* the ground, and it's hosted as a static site.

**Decision.**
1. **deck.gl** (v9, `@deck.gl/core` + `@deck.gl/layers`) in a Vite + TypeScript app in `web/`.
2. An **OrbitView in a local Cartesian frame** (metres, NZTM2000 relative to the site centre, z up), not a globe or map view. The camera can go below the ground plane, and a vertical exaggeration slider scales z.
3. CPTs are drawn as stacked `ColumnLayer` slices, one per soil behaviour type interval. NZGD investigations appear as wireframes only.
4. The pipeline exports derived data to `web/public/data/osu-sites.json` (`python -m chch_pipeline.export_web`), which is committed. A contract test checks it in CI.
5. GitHub Pages builds `web/` and serves it at `/3d/`, beside the map page.

**Rejected.**
- *CesiumJS*: built for globes and terrain, and good at underground views, but it's a much bigger bundle and its terrain and imagery need a Cesium ion token. Overkill for site-scale scenes.
- *three.js*: full control, but more code for picking, tooltips and many instanced columns, which deck.gl already does.
- *deck.gl MapView with a basemap*: the camera can't go below the map, which is the whole point here.

**Revisit** when the area-wide model arrives. A MapView, or a basemap draped on the ground plane, may suit city scale better.

