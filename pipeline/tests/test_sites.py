"""Tests for the Summary of Explorations reader."""

import math
from datetime import date
from pathlib import Path

import pytest

from chch_pipeline.sites import dms_to_degrees, read_summary

SAMPLE = Path(__file__).parent / "fixtures" / "osu_summary_sample.md"


def test_dms_to_degrees():
    assert dms_to_degrees("43°30'29.28\"") == pytest.approx(43 + 30 / 60 + 29.28 / 3600)


def test_dms_rejects_garbage():
    with pytest.raises(ValueError):
        dms_to_degrees("43.5")


def test_reads_only_table_rows():
    df = read_summary(SAMPLE, "Sample")
    assert df["designation"].tolist() == [
        "OSU A-1", "OSU A-2", "SCPT 57354", "DPCH 57186", "BH 57217",
    ]


def test_kinds_and_sources():
    df = read_summary(SAMPLE, "Sample").set_index("designation")
    assert df.loc["OSU A-1", ["source", "kind"]].tolist() == ["osu", "cpt"]
    assert df.loc["SCPT 57354", ["source", "kind"]].tolist() == ["nzgd", "cpt"]
    assert df.loc["DPCH 57186", "kind"] == "dynamic probe"
    assert df.loc["BH 57217", "kind"] == "borehole"


def test_dates_are_us_format():
    df = read_summary(SAMPLE, "Sample").set_index("designation")
    assert df.loc["OSU A-1", "date"] == date(2020, 2, 17)


def test_missing_groundwater_is_nan():
    df = read_summary(SAMPLE, "Sample").set_index("designation")
    assert math.isnan(df.loc["OSU A-2", "gw_measured"])
    assert df.loc["OSU A-2", "gw_cpt"] == 2.13


def test_latitude_is_south_and_lands_at_avondale():
    a1 = read_summary(SAMPLE, "Sample").set_index("designation").loc["OSU A-1"]
    assert a1["lat"] < 0
    # Avondale line centre from docs/data-sources.md; A-1 is ~12 m from it.
    assert math.dist((a1["easting"], a1["northing"]), (1574712, 5182698)) < 30
