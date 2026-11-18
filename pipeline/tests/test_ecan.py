"""Tests for the ECan wells reader."""

import math
from pathlib import Path

import pandas as pd

from chch_pipeline.ecan import read_wells

SAMPLE = Path(__file__).parent / "fixtures" / "ecan_wells_sample.geojson"


def test_keeps_only_wells_inside_the_box():
    # J39/0891 is near Timaru; M35/0003 has no NZTM coordinates.
    assert read_wells(SAMPLE)["well_no"].tolist() == ["M35/0001", "M35/0002"]


def test_owner_and_street_are_never_carried_through():
    df = read_wells(SAMPLE)
    assert not {"WELL_OWNER", "ROAD_OR_STREET", "owner", "street"} & set(df.columns)
    assert "Private Person" not in df.to_csv()


def test_cleans_values():
    w = read_wells(SAMPLE).set_index("well_no")
    good, blank = w.loc["M35/0001"], w.loc["M35/0002"]
    assert good["depth"] == 27.5
    assert good["initial_swl"] == 1.85  # stored as -1.85: 1.85 m below the reference point
    assert good["year_drilled"] == 1960
    assert good["strata"] == 12
    assert math.isnan(blank["depth"])  # 0 means unknown
    assert math.isnan(blank["ground_rl"])  # 0 means unknown
    assert math.isnan(blank["initial_swl"])  # -999.99 means unknown
    assert pd.isna(blank["year_drilled"])
    assert blank["use"] == "" and blank["status"] == ""


def test_coordinates_come_from_the_geometry():
    w = read_wells(SAMPLE).set_index("well_no").loc["M35/0001"]
    assert (w["lon"], w["lat"]) == (172.6866, -43.5081)
