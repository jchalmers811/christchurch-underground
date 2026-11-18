"""Export derived OSU data for the 3D viewer (web/).

Usage (from the pipeline/ folder):
    python -m chch_pipeline.export_web      # writes web/public/data/osu-sites.json

Only derived data goes out (ODC-BY, D-002): positions, soil behaviour type intervals
and groundwater depths. Positions are NZTM2000 metres, given relative to each site's
centre (x = east, y = north) so the viewer can work in a small local frame.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

from chch_pipeline.cpt import SBT_LABELS, classify, read_osu_cpt, to_intervals
from chch_pipeline.osu import LAYOUT_FILENAME, cpt_filename, read_layout
from chch_pipeline.page import REPO_ROOT, SITES, load_holes
from chch_pipeline.style import UNKNOWN_HEX, ZONE_COLOURS


def _num(v: float, ndigits: int = 2) -> float | None:
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else round(v, ndigits)


def build(raw_dir: Path) -> dict:
    layout = read_layout(raw_dir / "Avondale Playground" / LAYOUT_FILENAME)
    holes = load_holes(raw_dir)
    ground = layout.set_index(["site", "designation"])["rel_elev"]

    sites = []
    for site, (folder, anchor, caption) in SITES.items():
        here = holes[holes["site"] == site]
        origin_e, origin_n = here["easting"].mean(), here["northing"].mean()
        site_ground = layout.loc[layout["site"] == site, "rel_elev"]
        out_holes = []
        for h in here.itertuples():
            # S-9A and S-9B aren't in the layout file; they sit beside S-9, so use the
            # site's median ground level (the whole line varies by only a few cm).
            g = ground.get((site, h.designation), site_ground.median())
            rec = {
                "id": h.designation,
                "source": h.source,
                "kind": h.kind,
                "x": round(h.easting - origin_e, 2),
                "y": round(h.northing - origin_n, 2),
                "ground": round(float(g), 3),
                "depth": _num(h.depth),
                "gw": _num(h.gw_cpt) if pd.notna(h.gw_cpt) else _num(h.gw_measured),
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
            out_holes.append(rec)
        sites.append(
            {
                "id": anchor,
                "name": site,
                "caption": caption,
                "origin": [round(origin_e, 1), round(origin_n, 1)],
                "holes": out_holes,
            }
        )

    zones = {
        str(z): {
            "label": SBT_LABELS[z],
            "colour": UNKNOWN_HEX if z == 0 else ZONE_COLOURS[z],
        }
        for z in (7, 6, 5, 4, 3, 2, 0)
    }
    return {
        "crs": "EPSG:2193 (x, y relative to origin), metres; depths below ground",
        "source": "Stuedlein, Jana & Cary (2021), DesignSafe-CI, doi:10.17603/ds2-fy1v-hh47 "
        "(ODC-BY). Derived data only.",
        "zones": zones,
        "sites": sites,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, default=REPO_ROOT / "data" / "raw")
    parser.add_argument(
        "--out", type=Path, default=REPO_ROOT / "web" / "public" / "data" / "osu-sites.json"
    )
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(build(args.raw), separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {args.out} ({args.out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
