"""Read CPT traces into clean tables and classify them into soil intervals.

A CPT (cone penetration test) is a continuous trace: every ~1 cm the cone records
tip resistance (qc), sleeve friction (fs) and pore pressure (u2). This module:

1. reads one OSU DesignSafe CPT file into a tidy DataFrame (SI units, NaN for missing),
2. classifies each reading with Robertson's soil behaviour type index, and
3. merges neighbouring readings of the same class into depth intervals.

File quirks handled here are documented in docs/data-sources.md (OSU section).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

# Source column -> clean column. Parse by name, not position: OSU-M1 has no "Time (sec)".
OSU_COLUMNS = {
    "Test Length (m)": "push_length",
    "Cone Resistance (MPa)": "qc",
    "Local Friction (MPa)": "fs",
    "Pore Pressure (MPa)": "u2",
    "Inclination (Degrees)": "inclination",
}
MEASUREMENTS = ["qc", "fs", "u2"]

# -7777: no sleeve reading in the last few cm (fs shifted to tip depth).
# -9999: no reading at all (top 0.24 m of OSU-T6).
MISSING_MARKERS = (-7777, -9999)

# qc below this near the surface means the cone isn't in soil yet (e.g. a hand-dug start).
NOT_IN_SOIL_QC = 0.1  # MPa

ATMOSPHERIC_PRESSURE = 0.1013  # MPa, Robertson's reference pressure p_a


def read_osu_cpt(path: str | Path) -> pd.DataFrame:
    """Read one OSU CPT CSV into a clean table.

    Columns: depth (true vertical, m), push_length (m), qc, fs, u2 (MPa),
    inclination (degrees), in_soil (bool).
    """
    raw = pd.read_csv(path)
    missing = set(OSU_COLUMNS) - set(raw.columns)
    if missing:
        raise ValueError(f"{path}: missing columns {sorted(missing)}")

    df = raw[list(OSU_COLUMNS)].rename(columns=OSU_COLUMNS).astype(float)
    df[MEASUREMENTS] = df[MEASUREMENTS].mask(df[MEASUREMENTS].isin(MISSING_MARKERS))

    steps = df["push_length"].diff()
    if (steps.iloc[1:] <= 0).any():
        raise ValueError(f"{path}: push length is not strictly increasing")

    # Push length is measured along the (possibly tilted) rod. True depth adds up
    # each step's vertical component: sum of Δlength × cos(θ).
    steps.iloc[0] = df["push_length"].iloc[0]
    tilt = np.radians(df["inclination"].fillna(0.0))
    df.insert(0, "depth", (steps * np.cos(tilt)).cumsum())

    # Leading readings with no qc, or qc too low to be soil, are "not in soil yet".
    soil_reached = (df["qc"] >= NOT_IN_SOIL_QC).cummax()
    df["in_soil"] = soil_reached
    return df


# --- Soil behaviour type (Robertson 2010, non-normalised) ---------------------------------
#
# Isbt = sqrt((3.47 − log10(qc/pa))² + (log10(Rf) + 1.22)²), with Rf = fs/qc × 100 (%).
# The non-normalised form needs no groundwater level or unit weight, which we don't
# have reliably yet. It uses qc rather than qt because the cone's area ratio isn't
# given in the OSU files; in sands the difference is small.

@dataclass(frozen=True)
class SbtZone:
    zone: int
    label: str
    lower: float  # Isbt lower bound (inclusive)
    upper: float  # Isbt upper bound (exclusive)


SBT_ZONES = [
    SbtZone(7, "Gravelly sand to dense sand", 0.0, 1.31),
    SbtZone(6, "Sand: clean to silty", 1.31, 2.05),
    SbtZone(5, "Sand mixtures: silty sand to sandy silt", 2.05, 2.60),
    SbtZone(4, "Silt mixtures: clayey silt to silty clay", 2.60, 2.95),
    SbtZone(3, "Clay: silty clay to clay", 2.95, 3.60),
    SbtZone(2, "Organic soil: clay to peat", 3.60, np.inf),
]
UNKNOWN_ZONE = 0
SBT_LABELS = {z.zone: z.label for z in SBT_ZONES} | {UNKNOWN_ZONE: "Unknown / no data"}


def sbt_index(qc: pd.Series, fs: pd.Series) -> pd.Series:
    """Robertson (2010) non-normalised soil behaviour type index. NaN where undefined."""
    qc = qc.where(qc > 0)
    rf = (fs / qc * 100).where(fs > 0)
    return np.sqrt((3.47 - np.log10(qc / ATMOSPHERIC_PRESSURE)) ** 2 + (np.log10(rf) + 1.22) ** 2)


def sbt_zone(isbt: pd.Series) -> pd.Series:
    """Map Isbt values to Robertson zone numbers (0 = unknown)."""
    zones = pd.Series(UNKNOWN_ZONE, index=isbt.index, dtype=int)
    for z in SBT_ZONES:
        zones[(isbt >= z.lower) & (isbt < z.upper)] = z.zone
    return zones


def classify(df: pd.DataFrame) -> pd.DataFrame:
    """Add isbt and sbt_zone columns to a clean CPT table. Not-in-soil readings are unknown."""
    out = df.copy()
    out["isbt"] = sbt_index(out["qc"], out["fs"]).where(out["in_soil"])
    out["sbt_zone"] = sbt_zone(out["isbt"])
    return out


def to_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """Merge consecutive readings of the same SBT zone into depth intervals.

    Each reading at depth d covers (previous depth, d], so the intervals are
    contiguous, start at 0 and end at the final depth.
    Columns: depth_top, depth_bottom, sbt_zone, label.
    """
    if "sbt_zone" not in df:
        df = classify(df)
    tops = df["depth"].shift(fill_value=0.0)
    run_id = (df["sbt_zone"] != df["sbt_zone"].shift()).cumsum()
    intervals = (
        pd.DataFrame({"top": tops, "bottom": df["depth"], "zone": df["sbt_zone"], "run": run_id})
        .groupby("run")
        .agg(
            depth_top=("top", "first"),
            depth_bottom=("bottom", "last"),
            sbt_zone=("zone", "first"),
        )
        .reset_index(drop=True)
    )
    intervals["label"] = intervals["sbt_zone"].map(SBT_LABELS)
    return intervals
