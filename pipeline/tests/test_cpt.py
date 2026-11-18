"""Tests for the CPT reader, soil behaviour type classification and interval merging."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from chch_pipeline.cpt import (
    UNKNOWN_ZONE,
    classify,
    read_osu_cpt,
    sbt_index,
    sbt_zone,
    to_intervals,
)

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE = FIXTURES / "osu_cpt_sample.csv"
NO_TIME = FIXTURES / "osu_cpt_no_time.csv"


# --- Reading -----------------------------------------------------------------------------

def test_missing_value_markers_become_nan():
    df = read_osu_cpt(SAMPLE)
    assert df.loc[0, ["qc", "fs", "u2"]].isna().all()  # -9999 row
    assert np.isnan(df.loc[7, "fs"])  # -7777 in fs only
    assert df.loc[7, "qc"] == 12.0
    assert not (df[["qc", "fs", "u2"]] < -1000).any().any()


def test_file_without_time_column_parses():
    df = read_osu_cpt(NO_TIME)
    assert len(df) == 3


def test_depth_corrects_for_inclination():
    df = read_osu_cpt(NO_TIME)
    # 1 m at 60° tilt = 0.5 m vertical; twice, then 1 m straight down.
    assert df["depth"].tolist() == pytest.approx([0.5, 1.0, 2.0])
    assert (df["depth"] <= df["push_length"]).all()


def test_depth_is_strictly_increasing():
    df = read_osu_cpt(SAMPLE)
    assert df["depth"].is_monotonic_increasing
    assert df["depth"].is_unique


def test_readings_before_the_cone_reaches_soil_are_flagged():
    df = read_osu_cpt(SAMPLE)
    # Row 0 has no data; row 1 has qc = 0.02 MPa (hand-dug start). Soil from row 2.
    assert df["in_soil"].tolist() == [False, False] + [True] * 6


def test_rejects_non_increasing_push_length(tmp_path):
    bad = tmp_path / "bad.csv"
    text = NO_TIME.read_text().replace("1,2.0,", "1,0.5,")
    bad.write_text(text)
    with pytest.raises(ValueError, match="strictly increasing"):
        read_osu_cpt(bad)


def test_rejects_missing_required_column(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text(NO_TIME.read_text().replace("Cone Resistance (MPa)", "Cone (MPa)"))
    with pytest.raises(ValueError, match="Cone Resistance"):
        read_osu_cpt(bad)


# --- Soil behaviour type -----------------------------------------------------------------

def test_sbt_index_matches_hand_calculation():
    # Hand-checked: qc = 10 MPa, fs = 0.05 MPa → Rf = 0.5 % → Isbt ≈ 1.738 (sand).
    isbt = sbt_index(pd.Series([10.0]), pd.Series([0.05]))
    assert isbt.iloc[0] == pytest.approx(1.7384, abs=1e-4)


def test_sbt_index_is_nan_where_undefined():
    isbt = sbt_index(pd.Series([10.0, 0.0, np.nan]), pd.Series([0.0, 0.05, 0.05]))
    assert isbt.isna().all()


@pytest.mark.parametrize(
    ("isbt", "zone"),
    [(1.0, 7), (1.31, 6), (2.04, 6), (2.05, 5), (2.7, 4), (3.0, 3), (3.6, 2), (np.nan, 0)],
)
def test_sbt_zone_boundaries(isbt, zone):
    assert sbt_zone(pd.Series([isbt])).iloc[0] == zone


# --- Intervals (golden test on the sample file) -------------------------------------------

def test_intervals_golden():
    intervals = to_intervals(classify(read_osu_cpt(SAMPLE)))
    expected = [
        (0.00, 0.02, UNKNOWN_ZONE),  # no data, then a hand-dug start
        (0.02, 0.04, 6),  # sand
        (0.04, 0.07, 3),  # clay
        (0.07, 0.08, UNKNOWN_ZONE),  # no sleeve reading at the bottom
    ]
    got = list(intervals[["depth_top", "depth_bottom", "sbt_zone"]].itertuples(index=False))
    assert len(got) == len(expected)
    for (top, bottom, zone), (e_top, e_bottom, e_zone) in zip(got, expected, strict=True):
        assert (top, bottom) == pytest.approx((e_top, e_bottom))
        assert zone == e_zone


def test_intervals_are_contiguous_and_cover_the_whole_hole():
    df = read_osu_cpt(SAMPLE)
    intervals = to_intervals(df)
    assert intervals["depth_top"].iloc[0] == 0
    assert intervals["depth_bottom"].iloc[-1] == pytest.approx(df["depth"].iloc[-1])
    assert (intervals["depth_top"] < intervals["depth_bottom"]).all()
    assert np.allclose(intervals["depth_top"].iloc[1:], intervals["depth_bottom"].iloc[:-1])
    assert (intervals["sbt_zone"] != intervals["sbt_zone"].shift()).all()  # runs are merged
