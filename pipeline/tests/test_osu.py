"""Tests for the OSU layout file reader."""

from pathlib import Path

import pytest

from chch_pipeline.osu import cpt_filename, read_layout

LAYOUT = Path(__file__).parent / "fixtures" / "osu_layout_sample.csv"


def test_layout_unpacks_side_by_side_blocks():
    df = read_layout(LAYOUT)
    assert df["site"].tolist() == ["Site One", "Site One", "Site Two", "Site Two", "Site Two"]
    assert df["designation"].tolist() == ["SCPT 57354", "OSU A-1", "OSU S-1", "OSU S-9A", "OSU S-2"]


def test_layout_tags_source_and_parses_numbers():
    df = read_layout(LAYOUT).set_index("designation")
    assert df.loc["SCPT 57354", "source"] == "nzgd"
    assert df.loc["OSU A-1", "source"] == "osu"
    assert df.loc["OSU S-9A", "distance"] == 1.5
    assert df.loc["OSU S-9A", "rel_elev"] == -0.010


def test_trailing_spaces_in_site_names_are_stripped():
    assert "Site Two" in set(read_layout(LAYOUT)["site"])


@pytest.mark.parametrize(
    ("designation", "filename"),
    [("OSU A-1", "OSU-A1.csv"), ("OSU S-9A", "OSU-S9A.csv"), ("OSU T-16", "OSU-T16.csv")],
)
def test_cpt_filename(designation, filename):
    assert cpt_filename(designation) == filename


def test_cpt_filename_rejects_nzgd_designations():
    with pytest.raises(ValueError):
        cpt_filename("SCPT 57354")
