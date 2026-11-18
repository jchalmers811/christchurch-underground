"""Build the public Phase 0 page: a map of the OSU sites and a cross-section of each line.

Usage (from the pipeline/ folder):
    python -m chch_pipeline.page            # writes site/index.html

The output contains only derived data from the OSU DesignSafe set (ODC-BY, see
docs/decisions.md D-002): positions, soil behaviour type intervals and groundwater depths.
Raw CPT traces are not included.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import pandas as pd

from chch_pipeline.cpt import SBT_LABELS, classify, read_osu_cpt, to_intervals
from chch_pipeline.ecan import read_wells
from chch_pipeline.osu import LAYOUT_FILENAME, cpt_filename, read_layout
from chch_pipeline.sites import read_summary
from chch_pipeline.style import ZONE_COLOURS

REPO_ROOT = Path(__file__).resolve().parents[3]
ECAN_WELLS = Path("Canterbury Maps Open Data Wells and Bores") / "Wells_&_Bores_-_Existing.geojson"


# Layout-file site name -> (folder, anchor id, caption).
SITES = {
    "Avondale Playground": (
        "Avondale Playground", "avondale", "Avondale, east · liquefied in 2010–11",
    ),
    "Shirley Intermediate School": (
        "Shirley Intermediate School", "shirley", "Shirley, north-east · liquefied in 2010–11",
    ),
    "Ti Rakau Reserve": (
        "Ti Rakau Reserve", "ti-rakau", "Woolston/Bromley, south-east · liquefied in 2010–11",
    ),
    "Meadows": ("38 Meadows", "meadows", "Papanui, north · did not liquefy (control site)"),
}


PX_PER_M = 30
COLUMN_WIDTH_M = 1.1
MAX_DEPTH_M = 16
MARGIN = {"left": 48, "right": 16, "top": 16, "bottom": 36}


def load_holes(raw_dir: Path) -> pd.DataFrame:
    """Every exploration at the four sites, with positions, from the summary tables."""
    frames = []
    for site, (folder, anchor, _) in SITES.items():
        path = next((raw_dir / folder).glob("Summary of Explorations - *.md"))
        df = read_summary(path, site)
        df["anchor"] = anchor
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _site_svg(site: str, layout: pd.DataFrame, holes: pd.DataFrame, raw_dir: Path) -> str:
    folder = SITES[site][0]
    rows = layout[layout["site"] == site]
    gw = holes[holes["site"] == site].set_index("designation")["gw_cpt"]
    span = rows["distance"].max() + COLUMN_WIDTH_M
    width = MARGIN["left"] + span * PX_PER_M + MARGIN["right"]
    height = MARGIN["top"] + MAX_DEPTH_M * PX_PER_M + MARGIN["bottom"]
    w = COLUMN_WIDTH_M * PX_PER_M

    def x(m: float) -> float:
        return MARGIN["left"] + m * PX_PER_M

    def y(elev: float) -> float:
        # elev is metres relative to the line datum; downwards is negative.
        return MARGIN["top"] - elev * PX_PER_M

    parts = [f'<svg viewBox="0 0 {width:.0f} {height:.0f}" role="img" aria-label="{site}">']
    for d in range(0, MAX_DEPTH_M + 1, 2):
        parts.append(
            f'<line class="grid" x1="{x(0) - 4}" x2="{x(span)}" y1="{y(-d)}" y2="{y(-d)}"/>'
            f'<text class="tick" x="{x(0) - 8}" y="{y(-d) + 4}" text-anchor="end">{d}</text>'
        )
    parts.append(
        f'<text class="axis" transform="translate(12 {y(-MAX_DEPTH_M / 2)}) rotate(-90)" '
        f'text-anchor="middle">depth (m)</text>'
    )

    for r in rows.itertuples():
        left = x(r.distance)
        if r.source == "nzgd":
            parts.append(
                f'<g class="nzgd"><title>{r.designation}: held in the NZGD, not available here'
                f'</title><rect x="{left}" y="{y(r.rel_elev)}" width="{w}" '
                f'height="{15 * PX_PER_M}"/>'
                f'<text transform="translate({left + w / 2 + 4} {y(-7.5)}) rotate(-90)" '
                f'text-anchor="middle">{r.designation} · NZGD</text></g>'
            )
            continue

        intervals = to_intervals(classify(read_osu_cpt(raw_dir / folder / cpt_filename(r.designation))))
        parts.append(f'<g class="cpt"><title>{r.designation}</title>')
        for iv in intervals.itertuples():
            tip = (
                f"{r.designation} · {iv.depth_top:.2f}–{iv.depth_bottom:.2f} m · "
                f"{SBT_LABELS[iv.sbt_zone]}"
            )
            parts.append(
                f'<rect x="{left}" y="{y(r.rel_elev - iv.depth_top):.2f}" width="{w}" '
                f'height="{(iv.depth_bottom - iv.depth_top) * PX_PER_M + 0.3:.2f}" '
                f'fill="{ZONE_COLOURS[iv.sbt_zone]}"><title>{html.escape(tip)}</title></rect>'
            )
        water = gw.get(r.designation)
        if water is not None and pd.notna(water):
            wy = y(r.rel_elev - water)
            parts.append(
                f'<g class="water"><title>{r.designation} · groundwater at {water:.2f} m '
                f"(from CPT)</title>"
                f'<line x1="{left - 2}" x2="{left + w + 2}" y1="{wy:.2f}" y2="{wy:.2f}"/>'
                f'<path d="M{left + w / 2 - 4},{wy - 7:.2f} h8 l-4,6 z"/></g>'
            )
        parts.append(
            f'<text class="col-label" x="{left + w / 2}" y="{y(-MAX_DEPTH_M) + 14}" '
            f'text-anchor="middle">{r.designation.removeprefix("OSU ")}</text></g>'
        )

    parts.append(
        f'<text class="axis" x="{x(span / 2)}" y="{height - 4}" text-anchor="middle">'
        f"distance along the line (m)</text></svg>"
    )
    return "\n".join(parts)


def _holes_json(holes: pd.DataFrame) -> str:
    cols = ["site", "anchor", "designation", "source", "kind", "lat", "lon", "depth",
            "gw_measured", "gw_cpt"]
    out = holes[cols].copy()
    out["date"] = holes["date"].map(lambda d: d.isoformat())
    out[["lat", "lon"]] = out[["lat", "lon"]].round(7)
    records = out.astype(object).where(out.notna(), None).to_dict(orient="records")
    return json.dumps(records, ensure_ascii=False).replace("</", "<\\/")


def _wells_json(wells: pd.DataFrame) -> str:
    """Compact rows: [lat, lon, well_no, depth, year, use, strata, initial_swl]."""
    cols = ["lat", "lon", "well_no", "depth", "year_drilled", "use", "strata", "initial_swl"]
    out = wells[cols].copy()
    out[["lat", "lon"]] = out[["lat", "lon"]].round(6)
    out[["depth", "initial_swl"]] = out[["depth", "initial_swl"]].round(2)
    rows = out.astype(object).where(out.notna(), None).values.tolist()
    return json.dumps(rows, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def render(raw_dir: Path) -> str:
    layout = read_layout(raw_dir / "Avondale Playground" / LAYOUT_FILENAME)
    holes = load_holes(raw_dir)
    wells = read_wells(raw_dir / ECAN_WELLS)
    legend = "".join(
        f'<li><span class="swatch" style="background:{ZONE_COLOURS[z]}"></span>'
        f"{html.escape(SBT_LABELS[z])}</li>"
        for z in (7, 6, 5, 4, 3, 2, 0)
    )
    panels = "".join(
        f'<section id="{anchor}"><h2>{html.escape(site)}</h2>'
        f'<p class="caption">{caption} · <a href="#map" data-zoom="{anchor}">show on map</a>'
        f' · <a href="3d/#{anchor}"><strong>view in 3D</strong></a></p>'
        f'<div class="scroll">{_site_svg(site, layout, holes, raw_dir)}</div></section>'
        for site, (_, anchor, caption) in SITES.items()
    )
    return (
        TEMPLATE.replace("{{legend}}", legend)
        .replace("{{panels}}", panels)
        .replace("{{holes}}", _holes_json(holes))
        .replace("{{wells}}", _wells_json(wells))
        .replace("{{n_wells}}", f"{len(wells):,}")
        .replace("{{n_logged}}", f"{(wells['strata'] > 0).sum():,}")
    )


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Christchurch Underground</title>
<meta name="description" content="Four lines of cone penetration tests across Christchurch,
drawn as soil cross-sections.">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='5' fill='%23e3c069'/%3E%3Crect y='5' width='16' height='5' fill='%235b7ea3'/%3E%3Crect y='10' width='16' height='6' fill='%23b8862b'/%3E%3C/svg%3E">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">
<style>
:root {
  --bg: #fbfaf7; --fg: #1f1d1a; --muted: #6b665e; --grid: #e4e0d8; --unknown: #d6d3cc;
  --card: #ffffff; --border: #e4e0d8; --accent: #c2562c; --water: #2f7fd1;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161513; --fg: #ece8e1; --muted: #9c968c; --grid: #2e2b27; --unknown: #3a3733;
    --card: #1e1c19; --border: #2e2b27; --accent: #e07a4f; --water: #5aa6f0;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--fg);
       font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 32px 16px 64px; }
h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: -0.01em; }
.lede { color: var(--muted); margin: 0 0 20px; max-width: 70ch; }
a { color: var(--accent); }
#map { height: 420px; border-radius: 10px; border: 1px solid var(--border); margin-bottom: 8px;
       z-index: 0; }
.map-note { color: var(--muted); font-size: 13px; margin: 0 0 28px; }
.map-note p { margin: 0 0 6px; max-width: 90ch; }
.depth-legend { margin: 0; font-size: 12px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.site-buttons { display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 10px; }
.site-buttons button { font: inherit; font-size: 13px; padding: 4px 10px; border-radius: 999px;
       border: 1px solid var(--border); background: var(--card); color: var(--fg); cursor: pointer; }
.site-buttons button:hover { border-color: var(--accent); }
.leaflet-tooltip.site-label { font-weight: 600; cursor: pointer; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; list-style: none; padding: 0;
          margin: 0 0 24px; font-size: 13px; }
.legend li { display: flex; align-items: center; gap: 6px; }
.swatch { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.swatch.water { background: none; border-top: 2px solid var(--water); height: 0; width: 16px; }
section { background: var(--card); border: 1px solid var(--border); border-radius: 10px;
          padding: 16px 16px 8px; margin-bottom: 20px; scroll-margin-top: 16px; }
h2 { font-size: 17px; margin: 0; }
.caption { color: var(--muted); margin: 0 0 8px; font-size: 13px; }
.scroll { overflow-x: auto; }
.scroll svg { display: block; min-width: 640px; width: 100%; height: auto; }
.scroll svg text { fill: var(--muted); font-size: 11px; }
.scroll svg .axis { font-size: 12px; }
.scroll svg .col-label { fill: var(--fg); }
.scroll svg .grid { stroke: var(--grid); stroke-width: 1; }
.scroll svg .nzgd rect { fill: none; stroke: var(--muted); stroke-dasharray: 4 3; }
.scroll svg .water line { stroke: var(--water); stroke-width: 2; }
.scroll svg .water path { fill: var(--water); }
.scroll svg .cpt:hover > rect { stroke: var(--fg); stroke-width: 0.4; }
footer { color: var(--muted); font-size: 12px; margin-top: 28px; max-width: 80ch; }
footer p { margin: 0 0 8px; }
</style>
</head>
<body>
<main>
<h1>Christchurch Underground</h1>
<p class="lede">What's under the ground in Christchurch, starting with four lines of cone
penetration tests (CPTs) from Oregon State University and {{n_wells}} water wells and bores
from Environment Canterbury. Three of the CPT sites liquefied in the 2010–11 earthquakes;
one didn't. Pick a site to see where it is, then scroll down to see the ground beneath it,
or <a href="3d/"><strong>explore the sites in 3D</strong></a>.</p>

<div class="site-buttons" id="site-buttons"></div>
<div id="map" role="region" aria-label="Map of the four test sites"></div>
<div class="map-note">
<p>Large orange dots are OSU CPTs; hollow dots are NZGD investigations on the same lines,
located by OSU. Small dots are ECan wells ({{n_logged}} of them have a logged soil profile),
coloured by depth. Use the layer button (top right) to show or hide them; click any dot for
details.</p>
<ul class="legend depth-legend">
<li><span class="dot" style="background:#a8dbd0"></span>under 10 m</li>
<li><span class="dot" style="background:#4fa3a5"></span>10–30 m</li>
<li><span class="dot" style="background:#2b6f8a"></span>30–100 m</li>
<li><span class="dot" style="background:#1b3a5c"></span>100 m or more</li>
<li><span class="dot" style="background:#9a958c"></span>depth not recorded</li>
</ul>
</div>

<ul class="legend">{{legend}}<li><span class="swatch water"></span>Groundwater (from CPT)</li></ul>
{{panels}}

<footer>
<p>Each column is one CPT, coloured by Robertson (2010) soil behaviour type. That's inferred
from how the soil resists the cone, not from samples, and uses the non-normalised index (no
groundwater or unit-weight correction). CPTs at each site are 1.5 m apart, so differences
between neighbours show how much the ground varies over very short distances. Dashed
outlines are NZGD investigations on the same line, which aren't available here.</p>
<p>Data: Stuedlein, A., A. Jana, J. Cary (2021). "Subsurface Investigation at Selected
Liquefaction Case History Sites, Christchurch, NZ", in Role of Spatial Variability in
Liquefaction Consequence Severity. DesignSafe-CI.
<a href="https://doi.org/10.17603/ds2-fy1v-hh47">doi:10.17603/ds2-fy1v-hh47</a>. Licensed
under the <a href="https://opendatacommons.org/licenses/by/">Open Data Commons Attribution
License</a>; this page shows derived data.</p>
<p>Wells: Environment Canterbury (Canterbury Regional Council), "Wells &amp; Bores –
Existing", via <a href="https://catalogue.data.govt.nz/dataset/wells-bores-existing3">data.govt.nz</a>,
licensed under <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. Owner
names and addresses are left out. Drilling dates are often approximate, and a well's log is a
driller's description, not a lab test. Map data © OpenStreetMap contributors.</p>
</footer>
</main>

<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
const holes = {{holes}};
const wells = {{wells}};
const map = L.map("map", { scrollWheelZoom: false });
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 21, maxNativeZoom: 19,
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
}).addTo(map);

const accent = getComputedStyle(document.documentElement).getPropertyValue("--accent").trim();
const fmt = (v, unit) => (v === null ? "n/a" : v + unit);
const esc = s => String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

// ECan wells: drawn on a canvas in a pane below the OSU markers (thousands of points).
map.createPane("wells").style.zIndex = 350;
const wellRenderer = L.canvas({ pane: "wells", padding: 0.3 });
const depthColour = d => d === null ? "#9a958c" : d < 10 ? "#a8dbd0" : d < 30 ? "#4fa3a5"
  : d < 100 ? "#2b6f8a" : "#1b3a5c";
const withLog = L.layerGroup(), withoutLog = L.layerGroup();
for (const [lat, lon, no, depth, year, use, strata, swl] of wells) {
  const logged = strata > 0;
  L.circleMarker([lat, lon], {
    renderer: wellRenderer, pane: "wells", radius: logged ? 1.8 : 1.35,
    stroke: false, fillColor: depthColour(depth), fillOpacity: logged ? 0.85 : 0.5
  }).bindPopup(
    `<strong>${esc(no)}</strong> · ECan well<br>` +
    `${depth === null ? "Depth not recorded" : depth + " m deep"}` +
    `${year === null ? "" : ` · drilled ${year} (dates are often approximate)`}<br>` +
    `${use ? "Use: " + esc(use) + "<br>" : ""}` +
    `${swl === null ? "" : `Water level when drilled: ${swl} m below the reference point<br>`}` +
    `${logged ? `Soil log: ${strata} layers` : "No soil log"} · ` +
    `<a href="https://www.ecan.govt.nz/data/well-search/welldetails/?WellNo=${encodeURIComponent(no)}" ` +
    `target="_blank" rel="noopener">ECan Well Search ↗</a>`
  ).addTo(logged ? withLog : withoutLog);
}
withLog.addTo(map);
// Small dots at city scale, bigger once zoomed in to a suburb.
const wellRadius = (logged, z) => (z <= 12 ? 1.8 : z <= 14 ? 3 : 5) * (logged ? 1 : 0.75);
map.on("zoomend", () => {
  const z = map.getZoom();
  withLog.eachLayer(m => m.setRadius(wellRadius(true, z)));
  withoutLog.eachLayer(m => m.setRadius(wellRadius(false, z)));
});

const osuLayer = L.layerGroup().addTo(map);
L.control.layers(null, {
  "OSU CPT lines": osuLayer,
  "ECan wells with a soil log": withLog,
  "ECan wells without a log": withoutLog,
}, { collapsed: true }).addTo(map);

const bySite = {};
for (const h of holes) {
  (bySite[h.anchor] ??= { name: h.site, points: [] }).points.push([h.lat, h.lon]);
  const osu = h.source === "osu";
  L.circleMarker([h.lat, h.lon], {
    radius: osu ? 5 : 6, color: osu ? accent : "#555", weight: osu ? 1 : 2,
    fillColor: accent, fillOpacity: osu ? 0.9 : 0
  }).bindPopup(
    `<strong>${esc(h.designation)}</strong> · ${esc(h.kind)} · ${osu ? "OSU" : "NZGD"}<br>` +
    `${esc(h.date)} · ${fmt(h.depth, " m")} deep<br>` +
    `Groundwater: ${fmt(h.gw_measured, " m")} measured, ${fmt(h.gw_cpt, " m")} from CPT<br>` +
    `<a href="#${h.anchor}">See the cross-section ↓</a> · <a href="3d/#${h.anchor}">View in 3D</a>`
  ).addTo(osuLayer);
}

const all = holes.map(h => [h.lat, h.lon]);
map.fitBounds(all, { padding: [40, 40] });  // labels need a map view before they render
const buttons = document.getElementById("site-buttons");
const zoomTo = anchor => map.flyToBounds(bySite[anchor].points, { maxZoom: 20, padding: [40, 40] });
for (const [anchor, s] of Object.entries(bySite)) {
  const centre = L.latLngBounds(s.points).getCenter();
  // Shirley and Avondale are ~2 km apart, so push their labels to opposite sides.
  const direction = { shirley: "left", avondale: "right" }[anchor] ?? "top";
  L.tooltip({ permanent: true, direction, className: "site-label", interactive: true,
              offset: direction === "top" ? [0, -8] : [direction === "left" ? -8 : 8, 0] })
    .setLatLng(centre).setContent(s.name).addTo(map)
    .getElement().addEventListener("click", () => zoomTo(anchor));
  const b = document.createElement("button");
  b.textContent = s.name;
  b.onclick = () => zoomTo(anchor);
  buttons.append(b);
}
const allButton = document.createElement("button");
allButton.textContent = "All sites";
allButton.onclick = () => map.flyToBounds(all, { padding: [40, 40] });
buttons.prepend(allButton);

document.querySelectorAll("[data-zoom]").forEach(a =>
  a.addEventListener("click", () => setTimeout(() => zoomTo(a.dataset.zoom), 300)));
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "site" / "index.html")
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(args.raw), encoding="utf-8")
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
