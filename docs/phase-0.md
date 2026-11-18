# Phase 0: Data spike

> Parent: [plan.md](../plan.md) · Size: S · Status: not started

## 1. What this phase is for

Find out whether the data is usable before building anything. By the end you should know:

1. **Where** the data comes from, and whether you're allowed to show it on a public website.
2. **What it looks like**: file formats, column names, units and coordinate systems.
3. **Whether it fits together**: do the holes land in the right place on a map, and do their depths make sense against the ground surface?

**Done when** (from the plan):
- [ ] The records for one area plot on a map in the right places.
- [ ] One log's depth intervals parse into a clean, tested structure.
- [ ] The licence terms for each source are written down in `docs/decisions.md`.

This phase does **not** include: a 3D viewer, an API, cleaning every record, or interpolation.

---

## 2. Where to get the data

Each source below has a licence status. "Unverified" means I couldn't find the terms in writing, so reading them is a Phase 0 task.

### 2.1 CPTs and boreholes

| Source | What's in it | Access | Licence | Role |
|---|---|---|---|---|
| **New Zealand Geotechnical Database (NZGD)** | Tens of thousands of Christchurch CPTs, boreholes and test pits, mostly from after the 2010–11 earthquakes. Formerly the Canterbury Geotechnical Database. | Free account (individuals get Read Only access). Search by map and download. | **Terms of Use read (version of 26/11/2024).** Derived data can be published; raw data can't. See §2.3. | **Main source**, for derived data only |
| **Oregon State University CPT collection** (DesignSafe PRJ-3352, DOI [10.17603/ds2-fy1v-hh47](https://doi.org/10.17603/ds2-fy1v-hh47)) | CPTs at selected Christchurch liquefaction case-history sites, with GPS coordinates, dates and groundwater depths. | Public download from DesignSafe. | Probably an open licence (DesignSafe datasets usually are). Check the landing page. | **First test case**: small, clean and citable |
| **Environment Canterbury (ECan) Wells Database** | Water wells across Canterbury, many with bore logs (lithology by depth interval). Usually deeper than CPTs, often down into the gravels. | Canterbury Maps / data.govt.nz layers ("Wells & Bores"); ECan Well Search for single wells. | **Unverified.** ECan has a Terms of Use PDF. | **Backup and depth**: the best open source for the gravel layers |
| Christchurch City Council "Borelog Reading (OpenData)" | Soil material and moisture readings. | data.govt.nz | Check the catalogue record | Optional; look at it once |

**Suggested order:**
1. Download the **OSU DesignSafe** set first. It's small and documented, and you can start writing the parser while you wait to sort out the NZGD terms.
2. Register on **NZGD** with a **personal** email address (see §2.3), and email NZGD to confirm your intended use.
3. Pull the **ECan wells** layer for your area. This shows you how much deep, structured lithology data exists.

### 2.3 What the NZGD Terms of Use mean for this project

Based on the Terms of Use last updated 26/11/2024. This is my reading of them, not legal advice.

| Clause | What it says | What it means here |
|---|---|---|
| 3.2 | If you sign up with an organisation's email address, you accept the terms on that organisation's behalf. | **Register with a personal email**, not an employer's or university's address. |
| 2.4, 4.2 | The NZGD is "available to" engineering firms, government, academia and insurers. Individuals get Read Only access. | Individuals can register. Read Only access is all you need. |
| 5.2 + 2 | You may use it only for the NZGD's purposes: sharing geotechnical data and improving understanding of New Zealand's ground and scientific assessment. | A public, non-commercial visualisation of the ground fits reasonably well, but a portfolio project is a **grey area**. That's why it's worth asking NZGD by email. |
| 5.3 | You must not work around technical limitations in the NZGD. | **No scraping** and no automated bulk downloads that get around the portal's limits. Download through the portal, or use an export feature if it has one. |
| 5.4 | You must not copy or adapt the NZGD itself. | "NZGD" means the software and platform here. This clause is about the website, not the data. |
| 6.1 | You may download, store, copy, **adapt**, use and disclose the data (for the NZGD's purposes). | Local processing in the pipeline is fine. |
| **6.2** | **You must not publish or republish NZGD data on another website "in unaltered form".** | **The key rule.** The live app and the public repo may contain only **derived** data, such as classified soil intervals, interpreted layer depths and interpolated surfaces. Not raw CPT files or raw traces. |
| 6.3 | No charging. If the data goes into a wider product, tell users it came from the NZGD free of charge and without warranty. | Not commercial, but put that notice on the site anyway. It costs nothing. |
| 6.4–6.5 | No warranty on the data; you must take reasonable care. | Fits the "what this can't tell you" section. |

**Rules for the project** (also recorded in `docs/decisions.md`):
1. Keep raw NZGD files in `data/raw/`, which is **git-ignored**. They must never reach the public repo, CI artefacts or the hosted site.
2. Publish only derived data: soil-behaviour classes, merged intervals, layer tops and interpolated surfaces. Keep the NZGD record ID so people can look up the original themselves.
3. Log popups (Phase 1) and the GeoGuessr game (Phase 4) show **interpreted** soil columns, not raw `qc`/`fs`/`u2` traces. Raw-trace plots can come from OSU data, which has its own licence.
4. Put an attribution and no-warranty notice in the app footer and README, for example: *"Includes data derived from the New Zealand Geotechnical Database (MBIE), accessed free of charge and provided without warranty as to accuracy or fitness for purpose."*
5. **Email NZGD/MBIE** (through the NZGD Help Centre) describing the project. Ask whether (a) a public, non-commercial portfolio visualisation fits the NZGD's purpose, and (b) a map of investigation **locations** plus derived soil columns counts as "altered". Save the reply in `docs/decisions.md`.

Until they reply, you can carry on with Phase 0 locally. Don't publish NZGD-derived data, including the Phase 0 map, until you have an answer or have decided the risk is acceptable. If the answer is no, Phase 1 can be built on OSU + ECan data.

### 2.2 Ground surface (DEM)

| Source | What | Licence |
|---|---|---|
| **LINZ: Canterbury – Christchurch LiDAR 1m DEM (2020–2021)** | Bare-earth elevation, 1 m grid, NZTM2000, NZVD2016 heights | CC BY 4.0 |
| LINZ: Christchurch 1m DEM (2024–2025) | A newer survey of the same area | CC BY 4.0 |
| `s3://nz-elevation` (AWS Open Data) | The same LINZ DEMs as Cloud-Optimised GeoTIFFs. You can read just the window you need without downloading tiles. | CC BY 4.0 |

**Which survey to use:** most CPTs were done between 2011 and 2014, and some eastern areas have since sunk or been reworked. The 2020–21 survey is the safer default. Note the gap in the decisions log; it becomes one of your "what this can't tell you" points.

**Attribution (required):** "Sourced from the LINZ Data Service and licensed by Toitū Te Whenua Land Information New Zealand for re-use under CC BY 4.0."

---

## 3. Choosing the area

Pick a box of about **2 × 2 km**. Good areas have:
- **Dense data**: hundreds of CPTs and at least a few deep boreholes or wells.
- **Varied ground**: you want layers that change across the area, so the cross-sections are interesting.
- **A story**: the plan wants someone to "get it" within 30 seconds.

**Suggestion:** a strip from the **eastern central city out to Avonside/Dallington** (the Avon River red zone).
- Post-earthquake investigations make CPT coverage very dense here.
- The soft Christchurch Formation (sands, silts, peat) sits over the Riccarton Gravel, and the gravel gets deeper towards the east. That gives a cross-section with a visible trend.
- The liquefaction story is recognisable to anyone.

**How to decide:** open the NZGD map and the ECan wells layer side by side, count the records in two or three candidate boxes, and pick the one with the best mix of CPTs and deep logs. Write the bounding box (in NZTM2000) into `docs/decisions.md`.

---

## 4. How to map it

This is the part that trips people up, so here is the whole model.

### 4.1 Coordinate systems

| Purpose | System | EPSG | Units |
|---|---|---|---|
| Storage and maths (distances, cross-sections, interpolation) | **NZGD2000 / NZTM2000** | **2193** | metres (easting, northing) |
| Web maps (Leaflet, MapLibre, deck.gl) | WGS84 lat/lon | 4326 | degrees |
| Heights (DEM, ground levels) | **NZVD2016** | 7839 | metres |
| Older heights you may meet in logs | Lyttelton Vertical Datum 1937 (LVD37) | 5783 | metres |
| Council drawings/logs | Christchurch Drainage Datum (CDD) | none | metres, with a fixed offset from LVD37 (check the current CCC figure; it's roughly 9 m) |

**Rule of thumb:** convert everything to **EPSG:2193 + NZVD2016** as soon as you ingest it. Convert to 4326 only at the very end, for display. Use `pyproj` for horizontal transforms. For vertical datums, look up the LINZ offset for your area. Over a 2 km box it's close enough to a constant, but say so in the decisions log.

**Watch for:**
- Records that list lat/lon without saying the datum. NZGD2000 and WGS84 are within about a metre of each other, so treat them as the same and note it.
- Swapped axes (lat/lon vs lon/lat, easting/northing vs northing/easting). The usual sign is a point landing in the sea or in another country.
- Positions from handheld GPS, which can be ±5 m. That's fine for this project, but worth a line in "what this can't tell you".

### 4.2 Depth to elevation

The logs give **depth below ground**. The 3D model needs **elevation**. The conversion:

```
collar_elevation = ground level at the hole (in NZVD2016)
layer_top_elev    = collar_elevation − depth_top
layer_bottom_elev = collar_elevation − depth_bottom
```

Where does `collar_elevation` come from?
1. The log itself, if it records a ground level **and** the datum is known. Convert that datum to NZVD2016.
2. Otherwise, **sample the LiDAR DEM** at the hole's position.
3. Record which one you used for each hole (`collar_source = "log" | "dem"`). Where both exist, compare them. That's a good data-quality check, and differences of over 0.5 m are worth looking at (earthquake subsidence, fill, bad positions).

### 4.3 What a "clean" log looks like

Aim for these two structures. Keep them plain: dataclasses or pydantic for the code, then Parquet or GeoJSON for the files.

```python
@dataclass
class Hole:
    hole_id: str            # source-prefixed, e.g. "NZGD:CPT_12345", "ECAN:M35/1234"
    source: str             # "nzgd" | "osu" | "ecan"
    kind: str               # "cpt" | "borehole" | "well"
    easting: float          # EPSG:2193
    northing: float         # EPSG:2193
    collar_elev: float      # NZVD2016 metres
    collar_source: str      # "log" | "dem"
    final_depth: float      # metres below ground
    date: date | None
    licence: str            # carried with the record, not looked up later

@dataclass
class Interval:
    hole_id: str
    depth_top: float        # m below ground, top < bottom
    depth_bottom: float
    material: str           # normalised class: "gravel" | "sand" | "silt" | "clay" | "peat" | "fill" | "unknown"
    raw_description: str    # keep the original text
```

**CPTs don't come with intervals.** A CPT is a continuous trace (roughly every 1–2 cm: depth, cone resistance `qc`, sleeve friction `fs`, pore pressure `u2`). To get intervals you classify each reading (the standard method is the Robertson soil behaviour type index, `Ic`) and then merge neighbouring readings of the same class. For Phase 0:
- just parse **one CPT trace** into a clean table (depth, qc, fs, u2, with units in SI), **and**
- parse **one borehole or ECan bore log** into `Interval`s.

The `Ic` classification can wait for Phase 1, but write a stub test for it so it's on the list.

### 4.4 Tests that prove the parse is "clean"

- Depths go up monotonically, and `depth_top < depth_bottom`.
- No gaps or overlaps between intervals (or gaps are recorded explicitly as `unknown`).
- The last interval ends at `final_depth`.
- Units are SI (MPa, not kPa or tsf; metres, not feet).
- Every hole's coordinates fall inside the chosen bounding box.
- One **golden-file test**: a small saved input file plus the expected output.

---

## 5. Tasks

| # | Task | Output |
|---|---|---|
| 1 | ✅ Set up the monorepo skeleton (`pipeline/`, `docs/`) with Python, `pyproj`, `geopandas`, `rasterio`, `pytest`, and a CI workflow that runs the tests. Passes locally; CI goes green once the repo is pushed to GitHub. | Green CI |
| 2 | ✅ Download the OSU DesignSafe CPT set (all 4 sites, 64 CPTs); read its documentation; note the format, units and CRS. Licence (ODC-BY) and citation recorded. Still to do: download date, and whether downloading needed a login. | `docs/data-sources.md` entry |
| 3 | ~~Read the NZGD Terms of Use~~ ✅. Register with a personal email; email NZGD about the intended use (§2.3) | NZGD's reply in `docs/decisions.md` |
| 4 | ✅ Check the ECan Wells & Bores layer and count the bore logs in the candidate areas. Licence: CC BY 4.0 (D-003). The 5,946 wells in urban Christchurch are on the public map. Bore log text is only available as PNGs. | `docs/data-sources.md` entry |
| 5 | Choose the area; write down its bounding box in EPSG:2193 | `docs/decisions.md` entry |
| 6 | Download a few hundred CPT/borehole records for the area. For NZGD, use the portal's own download/export only; no scraping (cl. 5.3). Write down the steps. | `data/raw/` (git-ignored) + notes on the steps |
| 7 | Fetch the DEM window for the area from LINZ / `s3://nz-elevation` | `data/raw/dem.tif` |
| 8 | Write an index loader: every record → one row of `Hole` (ID, kind, position in 2193, collar elevation from the DEM) | `holes.parquet` |
| 9 | Plot the holes on a web map (a quick `folium` or MapLibre HTML page), coloured by kind, with the DEM as hillshade if easy. OSU half ✅: `python -m chch_pipeline.page` builds `site/index.html` (Leaflet map of the four OSU lines plus cross-sections). Still to do: the chosen area's records and the DEM hillshade. | **Map ✅** |
| 10 | Parse one CPT trace and one borehole/well log into clean structures, with tests. CPT half ✅ (`chch_pipeline.cpt`: reader, Robertson 2010 non-normalised SBT, intervals; drawn as cross-sections in `site/index.html`). Still to do: a borehole/well log. | **Parsed log ✅** |
| 11 | Write a short Phase 0 summary: what worked, what was messy, and what changes in the plan for Phase 1 | Update `plan.md` |

**Publish step** (guiding rule 1): put the map page on GitHub Pages and link it from the README. Until NZGD replies (§2.3), the public version shows only OSU + ECan points; NZGD points stay in a local-only build.

---

## 6. Decisions to record in `docs/decisions.md`

- [ ] Area and bounding box
- [x] NZGD: derived data only, raw files never published (see `decisions.md` D-001)
- [ ] NZGD: reply to the purpose and locations email
- [ ] OSU, ECan, LINZ: licence, attribution text, and whether republishing is allowed (OSU done: D-002)
- [ ] DEM survey used (2020–21 vs 2024–25) and why
- [ ] Vertical datum handling (the NZVD2016 conversion and the offsets used)
- [ ] Material classes for `Interval.material`, and how raw descriptions map onto them
- [ ] Storage format for the clean data (Parquet / GeoJSON / both)

## 7. Risks and open questions

| Risk | What to do |
|---|---|
| NZGD says a portfolio project doesn't fit its purpose | Fall back to OSU + ECan for anything public (see §2.3) |
| Raw NZGD data leaks into the public repo or site by accident | `data/raw/` is git-ignored from the first commit. Optionally, add a CI check that fails if raw-format files are tracked. |
| NZGD has no bulk download, so fetching hundreds of records by hand is slow | Check for an export feature first. Don't scrape (cl. 5.3). A smaller sample (e.g. 100) is acceptable for Phase 0. |
| CPT file formats vary a lot between consultants | Support 1–2 formats in Phase 0 and log the others in a backlog |
| Borehole logs are only PDFs | Prefer AGS files or ECan's structured bore logs. Leave PDF parsing out of scope. |
| Ground level has changed since the CPTs were done | Use the log's ground level where there is one, compare it with the DEM, and document the difference |
| CPTs refuse (stop) at the top of the gravel | That's useful in itself: the refusal depth is roughly the top of the gravel, which feeds Phase 2 |

## 8. Sources

- NZGD (Natural Hazards Commission / MBIE): https://www.naturalhazards.govt.nz/resilience-and-research/data-and-modelling/new-zealand-geotechnical-database
- GNS overview of the NZGD: https://www.gns.cri.nz/data-and-resources/new-zealand-geotechnical-database/
- OSU Christchurch CPTs, DesignSafe PRJ-3352: https://www.designsafe-ci.org/data/browser/public/designsafe.storage.published/PRJ-3352
- ECan Well Search: https://ecan.govt.nz/data/well-search
- ECan Wells & Bores (data.govt.nz): https://catalogue.data.govt.nz/dataset/wells-bores-existing3
- CCC Borelog Reading (OpenData): https://catalogue.data.govt.nz/dataset/borelog-reading-opendata
- LINZ elevation attribution: https://www.linz.govt.nz/products-services/data/licensing-and-using-data/attributing-elevation-or-aerial-imagery-data
- OpenTopography, Christchurch 2020–21 LiDAR: https://opentopography.org/node/3483
- NZ 1m DEM catalogue entry: https://catalogue.data.govt.nz/dataset/new-zealand-lidar-1m-dem1
