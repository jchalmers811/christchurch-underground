# Data sources

One entry per source: where it is, the licence, and what the files actually look like. Raw files go in `data/raw/`, which is git-ignored.

---

## OSU: Christchurch liquefaction case-history CPTs (DesignSafe PRJ-3352)

| | |
|---|---|
| **Title** | Subsurface Investigation at Selected Liquefaction Case History Sites, Christchurch, NZ |
| **Authors** | Armin Stuedlein, Amalesh Jana, John Cary (Oregon State University) |
| **Published** | 2021, DesignSafe-CI |
| **DOI** | [10.17603/ds2-fy1v-hh47](https://doi.org/10.17603/ds2-fy1v-hh47) |
| **Licence** | **Open Data Commons Attribution License (ODC-BY)**, as shown on the DesignSafe project page (checked 2026-11-18). The DataCite record has no licence. Republishing is allowed with attribution; see D-002. |
| **Citation** | As DesignSafe gives it: Stuedlein, A., A. Jana, J. Cary (2021). "Subsurface Investigation at Selected Liquefaction Case History Sites, Christchurch, NZ", in Role of Spatial Variability in Liquefaction Consequence Severity. DesignSafe-CI. https://doi.org/10.17603/ds2-fy1v-hh47 |
| **Downloaded** | _TODO: date_ → `data/raw/<site name>/` (all four sites) |
| **Login needed?** | Not to view the project page or its licence. _TODO: confirm whether downloading needed a login._ |

**What it covers.** 64 OSU CPTs along four short test lines, run in February 2020 to measure how much the soil varies over short distances. Each line also has NZGD investigations from 2013–2016 (SCPT, CPT, BH, DPCH) that **weren't redistributed** on DesignSafe and have to come from the NZGD.

| Site | Folder | Area (approx.) | Liquefied 2010–11? | OSU CPTs | Depth | Line length / bearing | Centre (NZTM2000) |
|---|---|---|---|---|---|---|---|
| Avondale Playground | `Avondale Playground/` | Avondale (east) | Yes | 16 (A-1…A-16) | 15 m | 24 m / 185° (N→S) | E 1574712, N 5182698 |
| Shirley Intermediate School | `Shirley Intermediate School/` | Shirley (north-east) | Yes | 19 (S-1…S-18, no S-13, plus S-9A, S-9B) | 14 m (S-9, S-9A ~6.6 m) | 27 m / 299° (ESE→WNW) | E 1572677, N 5182449 |
| Ti Rakau Reserve | `Ti Rakau Reserve/` | South-east (Woolston/Bromley) | Yes | 16 (T-1…T-16) | 12 m | 23 m / 119° (WNW→ESE) | E 1575403, N 5178187 |
| 38 Meadow Street | `38 Meadows/` | Papanui (north) | **No** (control site) | 13 (M-1…M-13) | 10–14.7 m | 19 m / 13° (S→N) | E 1569216, N 5184476 |

**NZGD investigations at each site** (to request from the NZGD; see D-001):

| Site | SCPT | CPT | Borehole | Dynamic probe |
|---|---|---|---|---|
| Avondale | 57354 | 62768 | **57217** (15.65 m) | DPCH 57062 |
| Shirley | 57366 | – | **57258** (15.8 m) | DPCH 57203 |
| Ti Rakau | 57341 | – | **57236** (15.5 m) | DPCH 57186 |
| Meadows | 57339 | 32137 | **57222** (12.5 m) | DPCH 57143 |

**Note for Phase 0.** These are four tight clusters, not a few hundred holes across one area. Use them to **build and test the CPT parser**, and as close-spaced cross-sections. The area-wide dataset still has to come from the NZGD. Each site has a borehole beside its CPT line, which is ideal for checking CPT-based soil classes against real samples.

---

### File inspection (inspected 2026-11-10)

**Files per site folder**

| File | What |
|---|---|
| `OSU-<site><n>.csv` | One CPT per file, 0.01 m readings (about 650–1,500 rows). |
| `Horizontal Location & Elevation of CPTs.csv` | Along-line distance and relative ground level for **all four sites**. The four copies are byte-identical. |
| `Summary of Explorations - <site>.docx` | Dates, GPS coordinates, depths and groundwater depths. The table is an embedded image. |
| `Summary of Explorations - <site>.md` / `.png` | **Added by us:** the table transcribed by hand, plus a rendered image of it to check against. |

**CPT files (`OSU-*.csv`): format**
- Plain ASCII CSV with LF line endings and no BOM. **One header row**, no metadata block.
- All 64 files have the same columns, **except `38 Meadows/OSU-M1.csv`, which has no `Time (sec)` column**. Parse by column name, not position.

  | Column | Unit | Notes |
  |---|---|---|
  | `Sounding No` | n/a | Always `1`. Ignore. |
  | `Test Length (m)` | m | **Push length, not true vertical depth.** Starts at 0.01, steps of 0.01 m, strictly increasing, no gaps in any file. |
  | `Cone Resistance (MPa)` | MPa | `qc` |
  | `Local Friction (MPa)` | MPa | `fs` |
  | `Pore Pressure (MPa)` | MPa | `u2`. Slightly negative near the surface, as expected above the water table. |
  | `Speed (cm/s)` | cm/s | **Always empty.** |
  | `Inclination (Degrees)` | ° | 0–10.7° (highest in M-1 and M-2). |
  | `Time (sec)` | s | **Always empty.** Missing entirely in OSU-M1. |
- Units are already SI, so no conversion is needed.

**Missing-value markers: there are two**
- **`-7777`** appears only in `fs`, in the bottom 3–8 readings of nearly every file. That's what you'd expect if `fs` was shifted to line up with the cone tip's depth: the sleeve sits a few centimetres behind the tip, so the last few centimetres have no sleeve reading.
- **`-9999`** appears in `qc`, `fs` and `u2` for the **top 0.24 m of `Ti Rakau Reserve/OSU-T6.csv`** (no data at all).
- Parse both as `NaN`, never as numbers.

**Other things to know**
- **Hand-dug or empty start:** `OSU-T12` reads `qc` ≈ 0.01–0.02 MPa with `fs` = 0 for its top 0.14 m. Treat readings with `qc` < 0.1 MPa near the surface as "not in soil".
- **Early stops:** Shirley `S-9` (6.62 m) and `S-9A` (6.58 m) ended at very high `qc` (41 and 59 MPa), probably an obstruction or a gravel lens. `S-9B` beside them reached 14 m.
- **Isolated pore-pressure spikes:** one reading each in `S-1` (−0.96 MPa at 6.72 m) and `S-2` (−0.86 MPa at 11.54 m). They look like sensor glitches. Flag them; don't drop them.
- **Inclination:** up to 10.7°. True depth ≈ the sum of `Δlength × cos(θ)`. That's only centimetres over 15 m, but the parser should still compute it.
- **No coordinates in the CPT files.** The .docx notes say McMillan Drilling's NZTM eastings and northings are "found in the electronic CPT data files", but these CSVs don't have them. _TODO: check whether DesignSafe has another file format that does._

**Location and elevation CSV**
- Four blocks side by side (Avondale, Ti Rakau, Shirley, Meadows), separated by blank columns. Two header rows: site name, then column names.
- **The distance is measured along the test line**, from the CPT marked 0 (Avondale SCPT 57354; Ti Rakau SCPT 57341; Shirley OSU S-1; Meadows SCPT 57339).
- **Elevation is relative, not absolute.** It's probably relative to a local benchmark, with a spread of only about 0.1–0.2 m per site. To get absolute NZVD2016 heights, use the LiDAR DEM and, optionally, these offsets.
- Not listed: S-9A and S-9B (assume the S-9 position), and the boreholes and dynamic probes.

**GPS coordinates (summary .md files)**
- Degrees-minutes-seconds to 0.01" (about ±0.3 m). Datum not stated; treat it as WGS84 ≈ NZGD2000.
- **Cross-check passed:** distances between GPS points match the CSV's along-line distances to within ±0.3 m at Avondale and Meadows, and ±0.7 m at Shirley. At Ti Rakau they match within that range **except for a ~1.4 m offset at the start of the line** (SCPT 57341 to T-1). That's fine for this project, but use the GPS positions as the source of truth.

**Groundwater**
- Two values per hole: tape-measured, and deduced from the CPT. Either can be missing.
- Meadows has no CPT-deduced values. At Shirley, the CPT-deduced values for S-1 to S-7 (4.0–5.8 m) are much deeper than the measured values (about 2.4–2.8 m). Keep both, and record which one is used.

**Typos and mismatches in the source documents**

| Where | Issue | Resolution |
|---|---|---|
| Meadows .docx note | "CPT 32127", but the table and CSV say **32137** | Use 32137; confirm on the NZGD |
| Ti Rakau .docx table | "DPDH 57186", but the note says **DPCH** | Use DPCH |
| Shirley .docx table | S-9 depth 6.1 m, but the file goes to 6.62 m | Trust the file |
| Meadows M-3, M-7; Ti Rakau T-16 | Table depths are rounded (14.5 / 11.5 m; the files go to 14.52, 14.73 and 11.52 m) | Trust the file |
| IDs | Files `OSU-A1`, tables `CPT OSU A-1` / `OSU A-1` | Normalise to `OSU:A-1` |

**What this means for the parser**
1. Read the CSV by column name and rename the columns to `depth_length_m`, `qc_mpa`, `fs_mpa`, `u2_mpa`, `incl_deg`. Drop `Sounding No`, `Speed` and `Time` (if present).
2. Replace `-7777` and `-9999` with `NaN`.
3. Calculate the true vertical `depth_m` from length and inclination.
4. Normalise the ID: `OSU-A1`, `OSU A-1` and `CPT OSU A-1` all become `OSU:A-1`. Handle the suffixed IDs `S-9A` and `S-9B`.
5. Take positions from the summary GPS (→ EPSG:2193). Take collar elevation from the DEM, with `collar_source = "dem"`.
6. Validate: depths strictly increasing; `qc` ≥ 0; `fs` ≥ 0 or NaN; inclination < 15°. Flag (don't drop) `|u2|` > 0.5 MPa near the surface and `qc` < 0.1 MPa.
7. Test fixtures to include: `OSU-A1` (typical), `OSU-M1` (no Time column), `OSU-T6` (`-9999` block) and `OSU-S9A` (early stop).

---

## ECan: Wells database (Environment Canterbury)

| | |
|---|---|
| **What** | Every registered water well and bore in Canterbury, with construction details and (for many) a lithology log |
| **Service** | ArcGIS REST: `https://gis.ecan.govt.nz/arcgis/rest/services/Public/Groundwater/MapServer/1` ("Wells"). It also appears on data.govt.nz as "Wells & Bores". |
| **Single-well viewer** | https://ecan.govt.nz/data/well-search (search by well number, e.g. `M35/2420`) |
| **Licence** | **CC BY 4.0** for the open-data download "Wells & Bores – Existing" ([data.govt.nz catalogue](https://catalogue.data.govt.nz/dataset/wells-bores-existing3), checked 2026-11-18; author Canterbury Regional Council). The separate Canterbury Maps *website* terms say not to republish "any substantial amount" of the website's information without consent; see D-003 for how that's handled. _Still TODO: the Well Search Terms of Use PDF, which matters for the bore log PNGs._ |
| **Bore log text** | **Only as a PNG image per well**, from Well Search. The Wells layer gives only the number of layers, and the open-data service (`gis2.ecan.govt.nz/.../Data_WFS`) has no strata table (checked 2026-11-10). _TODO: ask ECan whether they'll supply a strata table on request._ |

**Useful fields in the Wells layer:** `WELL_NO` (e.g. `M35/2420`), `DEPTH` (m), `GROUND_RL` (0.0 seems to mean "unknown"; check this), `DATE_DRILLED`, `WELL_TYPE`, `DRILLER`, the `TOP_SCREEN_*`/`BOTTOM_SCREEN_*` depths, `INITIAL_SWL` (static water level), and **`STRATA` = the number of logged layers (0 = no log)**.

### Download: Canterbury Maps open data "Wells & Bores – Existing" (2026-11-10)

- File: `data/raw/Canterbury Maps Open Data Wells and Bores/Wells_&_Bores_-_Existing.geojson` (55 MB).
- **38,967 points across all of Canterbury.** Coordinates are CRS84 (WGS84 lon/lat). The file also has integer `NZTMX`/`NZTMY` columns (1 m precision) and older NZMG coordinates.
- **Same columns as the REST Wells layer, plus `Link`** (the Well Search URL for each well, e.g. `…/welldetails/?WellNo=J39/0891`). **No layer descriptions**: `STRATA` is still only a count (0–165).
- "Existing" means active, not used, capped or altered wells. `OBJECTID` goes up to 64,054, so roughly 25,000 wells (probably decommissioned) are **not** in this file.
- Things to watch:
  - `GROUND_RL` is 0 for 59% of wells, so treat 0 as unknown.
  - Water-level fields use `±999.99` as a no-data marker (595 values).
  - Water levels are negative numbers, measured below the reference point.
  - `DATE_DRILLED` is often a placeholder of 1 July in a round year (e.g. `1960-07-01`), so treat it as approximate.

**Counts in 2×2 km boxes** (centre in NZTM2000):

| Box | REST service: all wells / with a log | Download (Existing): wells / with a log / logged ≥ 20 m / logged ≥ 50 m | Most detailed deep logs (Existing) |
|---|---|---|---|
| Suggested: eastern central city → Avonside/Dallington (E 1573000, N 5181800) | 563 / 370 | 170 / 48 / 27 / 18 | BX24/2775 (27 m, 30 layers), M35/4518 (140 m, 21) |
| Central city / CBD (E 1570700, N 5180200) | 1,098 / 768 | **406 / 290 / 191 / 101** | BX24/1289 (129 m, 101 layers), BX24/1426 (130 m, 68) |
| Around Avondale OSU site | 355 / 213 | 129 / 45 / 24 / 21 | BX24/1711 (164 m, 57), BX24/1710 (150 m, 43) |
| Around Shirley OSU site | 532 / 373 | 154 / 46 / 27 / 22 | M35/2110 (119 m, 25) |
| Around Ti Rakau OSU site | 246 / 181 | 85 / 37 / 24 / 16 | M36/5838 (124 m, 47), M36/1056 (135 m, 46) |
| Around Meadows OSU site | 431 / 340 | 106 / 54 / 16 / 6 | M35/8087 (143 m, 60) |

**Takeaways**
- **Most logs in the eastern suburbs belong to wells that are no longer "existing"**, probably post-earthquake investigation bores that were later sealed. To see them, look for an "All" or "Decommissioned" version of the dataset, or use the REST service.
- The **CBD box has far more deep, detailed logs** than the suggested eastern box: 191 against 27 that are logged and ≥ 20 m. That matters if the model needs to reach the Riccarton Gravel and the layers below it. This feeds into task 5.
- The layer text is still only available as a PNG per well (see the `Link` field), so plan on copying out a few chosen logs by hand.
