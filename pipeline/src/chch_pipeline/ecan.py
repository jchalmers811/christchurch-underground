"""ECan "Wells & Bores - Existing" open data (CC BY 4.0): read and clean one area.

The download covers all of Canterbury (~39,000 wells). This keeps one bounding box
and an allowlist of technical fields. Owner names and street addresses are dropped on
purpose (see docs/decisions.md D-003). Quirks are documented in docs/data-sources.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# Urban Christchurch, NZTM2000 metres: (min E, max E, min N, max N).
CHRISTCHURCH_BBOX = (1_562_000, 1_582_000, 5_172_000, 5_190_000)

WATER_LEVEL_MISSING = 999.99  # appears as +999.99 and -999.99


def _blank_to_none(v):
    return None if v is None or (isinstance(v, str) and not v.strip()) else v


def read_wells(path: str | Path, bbox: tuple[float, float, float, float] = CHRISTCHURCH_BBOX
               ) -> pd.DataFrame:
    """Read the ECan GeoJSON, keep wells inside bbox, and clean the fields we use.

    Columns: well_no, lon, lat, easting, northing, depth (m, NaN if unknown),
    year_drilled (int or NA; often a placeholder year), well_type, status, use,
    strata (number of logged layers; 0 = no log), initial_swl (m below the reference
    point, NaN if unknown), ground_rl (m, NaN if unknown), link.
    """
    with open(path, encoding="utf-8") as f:
        features = json.load(f)["features"]

    min_e, max_e, min_n, max_n = bbox
    rows = []
    for feat in features:
        p = feat["properties"]
        e, n = p.get("NZTMX"), p.get("NZTMY")
        if e is None or n is None or not (min_e <= e <= max_e and min_n <= n <= max_n):
            continue
        lon, lat = feat["geometry"]["coordinates"][:2]
        swl = p.get("INITIAL_SWL")
        date = _blank_to_none(p.get("DATE_DRILLED"))
        rows.append(
            {
                "well_no": p["WELL_NO"],
                "lon": lon,
                "lat": lat,
                "easting": float(e),
                "northing": float(n),
                # 0 depth / 0 ground level mean "not recorded", not a real value.
                "depth": p.get("DEPTH") or np.nan,
                "year_drilled": int(date[:4]) if date else pd.NA,
                "well_type": (_blank_to_none(p.get("WELL_TYPE_DESC")) or "").strip(),
                "status": (_blank_to_none(p.get("WELL_STATUS_DESC")) or "").strip(),
                "use": (_blank_to_none(p.get("USE_CODE_1_DESC")) or "").strip(),
                "strata": int(p.get("STRATA") or 0),
                # Water levels are stored as negative numbers below the reference point.
                "initial_swl": np.nan
                if swl is None or abs(swl) >= WATER_LEVEL_MISSING
                else -swl,
                "ground_rl": p.get("GROUND_RL") or np.nan,
                "link": p.get("Link"),
            }
        )
    df = pd.DataFrame(rows)
    if not df.empty:
        df["year_drilled"] = df["year_drilled"].astype("Int64")
    return df
