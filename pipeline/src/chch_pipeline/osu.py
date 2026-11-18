"""OSU DesignSafe PRJ-3352 dataset: site layout and file discovery.

The "Horizontal Location & Elevation of CPTs.csv" file holds all four sites side by
side: one block of three columns per site (designation, distance along the line,
relative ground level), separated by an empty column. Row 0 holds the site names.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

LAYOUT_FILENAME = "Horizontal Location & Elevation of CPTs.csv"
BLOCK_WIDTH = 4  # 3 data columns + 1 empty separator


def read_layout(path: str | Path) -> pd.DataFrame:
    """Read the side-by-side layout file into one long table.

    Columns: site, designation, source ("osu" | "nzgd"), distance (m along the line),
    rel_elev (m, ground level relative to the line's datum).
    """
    raw = pd.read_csv(path, header=None, dtype=str)
    rows = []
    for start in range(0, raw.shape[1], BLOCK_WIDTH):
        site = str(raw.iat[0, start]).strip()
        block = raw.iloc[2:, start : start + 3].dropna(how="all")
        for designation, distance, rel_elev in block.itertuples(index=False):
            designation = designation.strip()
            rows.append(
                {
                    "site": site,
                    "designation": designation,
                    "source": "osu" if designation.startswith("OSU") else "nzgd",
                    "distance": float(distance),
                    "rel_elev": float(rel_elev),
                }
            )
    return pd.DataFrame(rows)


def cpt_filename(designation: str) -> str:
    """'OSU A-1' -> 'OSU-A1.csv'; 'OSU S-9A' -> 'OSU-S9A.csv'."""
    m = re.fullmatch(r"OSU ([A-Z])-(\w+)", designation.strip())
    if not m:
        raise ValueError(f"not an OSU CPT designation: {designation!r}")
    return f"OSU-{m[1]}{m[2]}.csv"
