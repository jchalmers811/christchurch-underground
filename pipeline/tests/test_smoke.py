"""Smoke tests: the geospatial stack imports and the CRS helpers behave."""

import pytest

from chch_pipeline.crs import to_nztm, to_wgs84

# Cathedral Square, central Christchurch (approximate).
CATHEDRAL_SQ_LON, CATHEDRAL_SQ_LAT = 172.6366, -43.5309


def test_geospatial_stack_imports():
    import geopandas  # noqa: F401
    import pyproj  # noqa: F401
    import rasterio  # noqa: F401


def test_christchurch_lands_in_christchurch_in_nztm():
    e, n = to_nztm(CATHEDRAL_SQ_LON, CATHEDRAL_SQ_LAT)
    # Loose box around Christchurch in NZTM2000. Catches swapped axes or the wrong EPSG code.
    assert 1_560_000 < e < 1_585_000
    assert 5_170_000 < n < 5_190_000


def test_round_trip_is_lossless():
    e, n = to_nztm(CATHEDRAL_SQ_LON, CATHEDRAL_SQ_LAT)
    lon, lat = to_wgs84(e, n)
    assert lon == pytest.approx(CATHEDRAL_SQ_LON, abs=1e-8)
    assert lat == pytest.approx(CATHEDRAL_SQ_LAT, abs=1e-8)
