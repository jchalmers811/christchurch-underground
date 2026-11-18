"""Coordinate reference systems used by the pipeline.

Everything is stored and processed in NZTM2000 (EPSG:2193). WGS84 (EPSG:4326)
is used only at the edges: reading lat/lon from source files and writing
coordinates for the web map. See docs/phase-0.md §4.1.
"""

from pyproj import Transformer

NZTM2000 = "EPSG:2193"
WGS84 = "EPSG:4326"

# always_xy=True means (lon, lat) and (easting, northing) order, whatever the CRS's axis order.
_to_nztm = Transformer.from_crs(WGS84, NZTM2000, always_xy=True)
_to_wgs84 = Transformer.from_crs(NZTM2000, WGS84, always_xy=True)


def to_nztm(lon: float, lat: float) -> tuple[float, float]:
    """Convert WGS84 lon/lat (degrees) to NZTM2000 easting/northing (metres)."""
    return _to_nztm.transform(lon, lat)


def to_wgs84(easting: float, northing: float) -> tuple[float, float]:
    """Convert NZTM2000 easting/northing (metres) to WGS84 lon/lat (degrees)."""
    return _to_wgs84.transform(easting, northing)
