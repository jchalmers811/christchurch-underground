"""Export data for the 3D viewer (web/).

Usage (from the pipeline/ folder):
    python -m chch_pipeline.export_web

Writes to web/public/data/:
- osu-sites.json      sites, positions, soil behaviour type intervals, groundwater, and
                      each line's axis (for the fence diagram). Loaded up front.
- sites/<id>.json     per-site detail, loaded on demand: CPT readings every 2 cm (for the
                      trace chart) and liquefaction terms (crr_m, csr_per_g; see
                      liquefaction.py). OSU readings are ODC-BY, so publishing them is
                      allowed (D-002, D-005).
- city-wells.json     ECan wells with a known depth, for the city view (D-003 allowlist).

Positions are NZTM2000 metres relative to an origin (x = east, y = north), so the
viewer can work in a small local frame.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from chch_pipeline.cpt import SBT_LABELS, classify, read_osu_cpt, to_intervals
from chch_pipeline.ecan import CHRISTCHURCH_BBOX, read_wells
from chch_pipeline.liquefaction import triggering
from chch_pipeline.osu import LAYOUT_FILENAME, cpt_filename, read_layout
from chch_pipeline.page import ECAN_WELLS, REPO_ROOT, SITES, load_holes
from chch_pipeline.style import UNKNOWN_HEX, ZONE_COLOURS

MW_FEB_2011 = 6.2
DEFAULT_PGA = 0.35  # g. A round scenario value; the viewer has a slider (D-005).
TRACE_STEP = 2  # keep every 2nd 1 cm reading


def _num(v, ndigits: int = 2) -> float | None:
    if v is None or (isinstance(v, float) and math.isnan(v)) or pd.isna(v):
        return None
    return round(float(v), ndigits)


def line_axis(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Unit vector along the main direction of a set of points (first principal axis).

    The sign is chosen so the axis points roughly east (or north for a N–S line), which
    keeps the fence's left/right order stable.
    """
    pts = np.column_stack([x - x.mean(), y - y.mean()])
    _, _, vt = np.linalg.svd(pts, full_matrices=False)
    ux, uy = vt[0]
    if ux < 0 or (abs(ux) < 1e-9 and uy < 0):
        ux, uy = -ux, -uy
    return float(ux), float(uy)


def _gw(h) -> float:
    return h.gw_cpt if pd.notna(h.gw_cpt) else h.gw_measured


def build_sites(raw_dir: Path) -> tuple[dict, dict[str, dict]]:
    layout = read_layout(raw_dir / "Avondale Playground" / LAYOUT_FILENAME)
    holes = load_holes(raw_dir)
    ground = layout.set_index(["site", "designation"])["rel_elev"]

    sites, details = [], {}
    for site, (folder, anchor, caption) in SITES.items():
        here = holes[holes["site"] == site]
        origin_e, origin_n = here["easting"].mean(), here["northing"].mean()
        x = here["easting"].to_numpy() - origin_e
        y = here["northing"].to_numpy() - origin_n
        ux, uy = line_axis(x, y)
        site_ground = layout.loc[layout["site"] == site, "rel_elev"]

        out_holes, detail_holes = [], {}
        for h, hx, hy in zip(here.itertuples(), x, y, strict=True):
            # S-9A and S-9B aren't in the layout file; they sit beside S-9, so use the
            # site's median ground level (the whole line varies by only a few cm).
            g = ground.get((site, h.designation), site_ground.median())
            gw = _gw(h)
            rec = {
                "id": h.designation,
                "source": h.source,
                "kind": h.kind,
                "x": round(float(hx), 2),
                "y": round(float(hy), 2),
                "s": round(float(hx * ux + hy * uy), 2),
                "ground": round(float(g), 3),
                "depth": _num(h.depth),
                "gw": _num(gw),
                "date": h.date.isoformat(),
            }
            if h.source == "osu":
                cpt = classify(read_osu_cpt(raw_dir / folder / cpt_filename(h.designation)))
                iv = to_intervals(cpt)
                rec["depth"] = round(float(cpt["depth"].iloc[-1]), 2)
                rec["intervals"] = [
                    [round(t, 2), round(b, 2), int(z)]
                    for t, b, z in iv[["depth_top", "depth_bottom", "sbt_zone"]].itertuples(
                        index=False
                    )
                ]
                liq = triggering(cpt, gw, MW_FEB_2011)
                rows = pd.DataFrame(
                    {
                        "depth": cpt["depth"].round(2),
                        "qc": cpt["qc"].round(2),
                        "fs": cpt["fs"].round(4),
                        "u2": cpt["u2"].round(4),
                        "isbt": cpt["isbt"].round(2),
                        "crr_m": liq["crr_m"].round(3),
                        "csr_per_g": liq["csr_per_g"].round(3),
                    }
                ).iloc[TRACE_STEP - 1 :: TRACE_STEP]
                rows = rows.replace([np.inf, -np.inf], np.nan)
                detail_holes[h.designation] = (
                    rows.astype(object).where(rows.notna(), None).values.tolist()
                )
            out_holes.append(rec)

        sites.append(
            {
                "id": anchor,
                "name": site,
                "caption": caption,
                "origin": [round(origin_e, 1), round(origin_n, 1)],
                "axis": [round(ux, 4), round(uy, 4)],
                "holes": out_holes,
            }
        )
        details[anchor] = {
            "id": anchor,
            "columns": ["depth", "qc", "fs", "u2", "isbt", "crr_m", "csr_per_g"],
            "units": ["m", "MPa", "MPa", "MPa", "", "", ""],
            "mw": MW_FEB_2011,
            "holes": detail_holes,
        }

    zones = {
        str(z): {"label": SBT_LABELS[z], "colour": UNKNOWN_HEX if z == 0 else ZONE_COLOURS[z]}
        for z in (7, 6, 5, 4, 3, 2, 0)
    }
    summary = {
        "crs": "EPSG:2193 (x, y relative to origin), metres; depths below ground",
        "source": "Stuedlein, Jana & Cary (2021), DesignSafe-CI, doi:10.17603/ds2-fy1v-hh47 "
        "(ODC-BY). Derived data only in this file.",
        "liquefaction": {"mw": MW_FEB_2011, "default_pga": DEFAULT_PGA},
        "zones": zones,
        "sites": sites,
    }
    return summary, details


def build_city(raw_dir: Path, sites: list[dict]) -> dict:
    min_e, max_e, min_n, max_n = CHRISTCHURCH_BBOX
    origin = ((min_e + max_e) / 2, (min_n + max_n) / 2)
    wells = read_wells(raw_dir / ECAN_WELLS).dropna(subset=["depth"])
    rows = [
        [
            round(w.easting - origin[0], 1),
            round(w.northing - origin[1], 1),
            round(float(w.depth), 1),
            int(w.strata),
            w.well_no,
            None if pd.isna(w.year_drilled) else int(w.year_drilled),
        ]
        for w in wells.itertuples()
    ]
    return {
        "crs": "EPSG:2193 relative to origin, metres",
        "origin": list(origin),
        "bbox": [min_e - origin[0], max_e - origin[0], min_n - origin[1], max_n - origin[1]],
        "columns": ["x", "y", "depth", "strata", "well_no", "year"],
        "source": 'Environment Canterbury, "Wells & Bores – Existing", CC BY 4.0',
        "wells": rows,
        "sites": [
            {
                "id": s["id"],
                "name": s["name"],
                "x": round(s["origin"][0] - origin[0], 1),
                "y": round(s["origin"][1] - origin[1], 1),
            }
            for s in sites
        ],
    }


def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {path} ({path.stat().st_size / 1024:.0f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "web" / "public" / "data")
    args = parser.parse_args()
    summary, details = build_sites(args.raw)
    _write(args.out / "osu-sites.json", summary)
    for site_id, detail in details.items():
        _write(args.out / "sites" / f"{site_id}.json", detail)
    _write(args.out / "city-wells.json", build_city(args.raw, summary["sites"]))


if __name__ == "__main__":
    main()
