"""Tests for the basemap tile maths (no network)."""

import math

import pytest

from chch_pipeline.basemap import lonlat_to_tile, tile_range, tile_to_lonlat
from chch_pipeline.ecan import CHRISTCHURCH_BBOX


def test_tile_round_trip():
    x, y = lonlat_to_tile(172.6366, -43.5309, 13)
    assert tile_to_lonlat(x, y, 13) == pytest.approx((172.6366, -43.5309), abs=1e-9)


def test_matches_the_classic_mercator_formula():
    # The code uses asinh(tan φ); the textbook form is ln(tan(π/4 + φ/2)). Same thing,
    # written independently here. Cathedral Square, z13 (n = 8192).
    lon, lat, n = 172.6366, -43.5309, 2**13
    phi = math.radians(lat)
    expected_y = (1 - math.log(math.tan(math.pi / 4 + phi / 2)) / math.pi) / 2 * n
    expected_x = (lon + 180) / 360 * n  # ≈ 8024.4
    x, y = lonlat_to_tile(lon, lat, 13)
    assert x == pytest.approx(expected_x, abs=1e-6)
    assert y == pytest.approx(expected_y, abs=1e-6)
    assert int(x) == 8024


def test_tile_range_covers_the_city_box_with_a_small_mosaic():
    xr, yr = tile_range(CHRISTCHURCH_BBOX, 13)
    assert 4 <= len(xr) <= 8 and 4 <= len(yr) <= 8
