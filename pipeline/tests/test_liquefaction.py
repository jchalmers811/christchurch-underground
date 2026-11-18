"""Tests for the simplified CPT liquefaction triggering calculation."""

import numpy as np
import pandas as pd
import pytest

from chch_pipeline.liquefaction import (
    crr75,
    factor_of_safety,
    kc,
    lpi,
    magnitude_scaling,
    stress_reduction,
    triggering,
    unit_weight,
)


def profile(qc_mpa: float, fs_mpa: float, depth_to: float = 10.0, step: float = 0.05):
    depth = np.arange(step, depth_to + step / 2, step)
    return pd.DataFrame(
        {
            "depth": depth,
            "qc": qc_mpa,
            "fs": fs_mpa,
            "u2": 0.0,
            "in_soil": True,
        }
    )


# --- Building blocks, checked against the published formulas -----------------------------

def test_msf_is_about_one_at_magnitude_7_5():
    assert magnitude_scaling(7.5) == pytest.approx(1.0, abs=0.01)
    assert magnitude_scaling(6.2) == pytest.approx(1.62, abs=0.01)


def test_rd_values():
    assert stress_reduction(np.array([0.0, 5.0, 15.0])) == pytest.approx(
        [1.0, 1 - 0.00765 * 5, 1.174 - 0.0267 * 15]
    )


def test_crr_is_continuous_at_qtn_cs_50():
    low, high = crr75(np.array([49.999, 50.0]))
    assert low == pytest.approx(high, abs=1e-3)
    assert crr75(np.array([100.0]))[0] == pytest.approx(93 * 0.1**3 + 0.08)


def test_kc_is_one_for_clean_sand_and_grows_with_fines():
    assert kc(np.array([1.5]))[0] == 1.0
    assert kc(np.array([1.64]))[0] == pytest.approx(1.0, abs=0.02)
    assert kc(np.array([2.4]))[0] > 2


def test_unit_weight_is_plausible_and_clamped():
    g = unit_weight(np.array([10_000.0, 500.0, np.nan]), np.array([50.0, 20.0, 1.0]))
    assert 17 < g[0] < 21  # dense sand
    assert 14 <= g[1] <= 18  # soft, high-friction soil
    assert g[2] == 18.0  # undefined -> default


# --- Behaviour on simple profiles ----------------------------------------------------------

def test_loose_saturated_sand_liquefies_and_dense_sand_does_not():
    gw = 1.5
    loose = triggering(profile(qc_mpa=3.0, fs_mpa=0.02), gw)
    dense = triggering(profile(qc_mpa=25.0, fs_mpa=0.15), gw)
    deep_loose = factor_of_safety(loose, pga=0.35)[loose["depth"] > 3]
    assert (deep_loose < 1).all()
    # Dense sand is either non-liquefiable (NaN) or has FS > 1.
    fs_dense = factor_of_safety(dense, pga=0.35)
    assert ((fs_dense > 1) | fs_dense.isna()).all()


def test_nothing_liquefies_above_the_water_table():
    liq = triggering(profile(qc_mpa=3.0, fs_mpa=0.02), gw_depth=4.0)
    assert liq.loc[liq["depth"] <= 4.0, "crr_m"].isna().all()


def test_clay_like_soil_is_not_liquefiable():
    # qc 0.6 MPa with high friction -> Ic well above 2.6.
    liq = triggering(profile(qc_mpa=0.6, fs_mpa=0.04), gw_depth=1.0)
    assert (liq.loc[liq["depth"] > 2, "ic"] > 2.6).all()
    assert liq["crr_m"].isna().all()


def test_fs_scales_inversely_with_pga():
    liq = triggering(profile(qc_mpa=5.0, fs_mpa=0.03), gw_depth=1.0)
    fs1, fs2 = factor_of_safety(liq, 0.2), factor_of_safety(liq, 0.4)
    ok = fs1.notna()
    assert np.allclose(fs1[ok] / fs2[ok], 2.0)


def test_lpi_is_zero_without_liquefaction_and_grows_with_shaking():
    liq = triggering(profile(qc_mpa=3.0, fs_mpa=0.02, depth_to=15), gw_depth=1.5)
    assert lpi(liq, pga=0.01) == 0
    assert 0 < lpi(liq, pga=0.2) < lpi(liq, pga=0.5)
