"""Investigation locations from the OSU "Summary of Explorations" tables.

The tables (hand-transcribed into Markdown from the .docx files) give each exploration's
date, latitude/longitude in degrees-minutes-seconds, depth and groundwater depths. They
include the NZGD investigations on each line, located by OSU's own GPS, so those
positions come from the ODC-BY-licensed OSU dataset, not from the NZGD.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from chch_pipeline.crs import to_nztm

DMS = re.compile(r"""(\d+)°(\d+)'([\d.]+)\"""")
KINDS = {"CPT": "cpt", "SCPT": "cpt", "BH": "borehole", "DPCH": "dynamic probe"}
COLUMNS = [
    "designation", "date", "lat_dms", "lon_dms", "depth", "gw_measured", "gw_cpt",
]


def dms_to_degrees(text: str) -> float:
    """'43°30'29.28"' -> 43.508133. Sign is applied by the caller (latitudes are south)."""
    m = DMS.fullmatch(text.strip())
    if not m:
        raise ValueError(f"not a degrees-minutes-seconds value: {text!r}")
    d, mins, secs = (float(g) for g in m.groups())
    return d + mins / 60 + secs / 3600


def _number(text: str) -> float:
    text = text.strip()
    return np.nan if text.upper() in {"N/A", ""} else float(text)


def _us_date(text: str) -> date:
    """OSU dates are month/day/year: 2/17/2020 is 17 February 2020."""
    return datetime.strptime(text.strip(), "%m/%d/%Y").date()


def _clean_designation(text: str) -> str:
    """'CPT OSU A-1' -> 'OSU A-1'; 'SCPT 57354²' -> 'SCPT 57354'."""
    text = re.sub(r"[¹²³*]", "", text).strip()
    # Ti Rakau's table says "DPDH 57186" but its footnote says "DPCH 57186". Every
    # other site uses DPCH, so treat DPDH as a typo.
    text = text.replace("DPDH ", "DPCH ")
    return text.removeprefix("CPT ") if text.startswith("CPT OSU") else text


def read_summary(path: str | Path, site: str) -> pd.DataFrame:
    """Read one Summary of Explorations table.

    Columns: site, designation, source, kind, date, lat, lon, easting, northing (EPSG:2193),
    depth (m), gw_measured (m), gw_cpt (m).
    """
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != len(COLUMNS) or not DMS.search(cells[2]):
            continue  # header, separator or prose
        rec = dict(zip(COLUMNS, cells, strict=True))
        designation = _clean_designation(rec["designation"])
        is_osu = designation.startswith("OSU")
        lat = -dms_to_degrees(rec["lat_dms"])  # south
        lon = dms_to_degrees(rec["lon_dms"])  # east
        easting, northing = to_nztm(lon, lat)
        rows.append(
            {
                "site": site,
                "designation": designation,
                "source": "osu" if is_osu else "nzgd",
                "kind": "cpt" if is_osu else KINDS[designation.split()[0]],
                "date": _us_date(rec["date"]),
                "lat": lat,
                "lon": lon,
                "easting": easting,
                "northing": northing,
                "depth": _number(rec["depth"]),
                "gw_measured": _number(rec["gw_measured"]),
                "gw_cpt": _number(rec["gw_cpt"]),
            }
        )
    if not rows:
        raise ValueError(f"{path}: no exploration rows found")
    return pd.DataFrame(rows)
