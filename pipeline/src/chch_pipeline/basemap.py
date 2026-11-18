"""A static OpenStreetMap image for the 3D city view's ground plane.

The 3D viewer works in a local NZTM2000 frame, so it can't use a normal web-map tile
layer. Instead this stitches a handful of OSM tiles into one image (fetched once, with
a generic user agent, well within OSM's tile usage policy), lightens it so the data
stands out, and records where its four corners fall in NZTM. Over ~20 km the
Web Mercator -> NZTM distortion is a few metres, so placing the image by its corners
is accurate enough.

Usage (from pipeline/, needs the `media` extra):
    python -m chch_pipeline.basemap     # writes web/public/data/city-basemap.webp + .json

© OpenStreetMap contributors (ODbL). Attribution is shown in the viewer.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import time
import urllib.request
from pathlib import Path

from chch_pipeline.crs import to_nztm, to_wgs84
from chch_pipeline.ecan import CHRISTCHURCH_BBOX
from chch_pipeline.page import REPO_ROOT

TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
USER_AGENT = "chch-underground-pipeline/0.1 (static portfolio basemap)"
TILE_SIZE = 256


def lonlat_to_tile(lon: float, lat: float, z: int) -> tuple[float, float]:
    """Fractional Web Mercator tile coordinates (x right, y down)."""
    n = 2**z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def tile_to_lonlat(x: float, y: float, z: int) -> tuple[float, float]:
    """Inverse of lonlat_to_tile."""
    n = 2**z
    lon = x / n * 360 - 180
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lon, lat


def tile_range(bbox_nztm: tuple[float, float, float, float], z: int):
    """Integer tile ranges (x0..x1, y0..y1 inclusive) covering an NZTM bounding box."""
    min_e, max_e, min_n, max_n = bbox_nztm
    corners = [to_wgs84(e, n) for e in (min_e, max_e) for n in (min_n, max_n)]
    xs, ys = zip(*(lonlat_to_tile(lon, lat, z) for lon, lat in corners), strict=True)
    return range(int(min(xs)), int(max(xs)) + 1), range(int(min(ys)), int(max(ys)) + 1)


def build(bbox_nztm, z: int, out_image: Path, out_meta: Path) -> None:
    from PIL import Image, ImageEnhance

    xr, yr = tile_range(bbox_nztm, z)
    mosaic = Image.new("RGB", (len(xr) * TILE_SIZE, len(yr) * TILE_SIZE))
    for i, x in enumerate(xr):
        for j, y in enumerate(yr):
            req = urllib.request.Request(
                TILE_URL.format(z=z, x=x, y=y), headers={"User-Agent": USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                tile = Image.open(io.BytesIO(resp.read())).convert("RGB")
            mosaic.paste(tile, (i * TILE_SIZE, j * TILE_SIZE))
            time.sleep(0.2)  # be gentle with the tile server

    # Light, low-contrast version so the wells and columns stand out on top.
    mosaic = ImageEnhance.Color(mosaic).enhance(0.35)
    mosaic = ImageEnhance.Contrast(mosaic).enhance(0.8)
    mosaic = ImageEnhance.Brightness(mosaic).enhance(1.08)
    out_image.parent.mkdir(parents=True, exist_ok=True)
    mosaic.save(out_image, "WEBP", quality=80)

    # Corners in NZTM, in deck.gl BitmapLayer order: bottom-left, top-left, top-right,
    # bottom-right.
    x0, x1, y0, y1 = xr.start, xr.stop, yr.start, yr.stop
    corners = [(x0, y1), (x0, y0), (x1, y0), (x1, y1)]
    nztm = [to_nztm(*tile_to_lonlat(x, y, z)) for x, y in corners]
    out_meta.write_text(
        json.dumps(
            {
                "image": out_image.name,
                "corners_nztm": [[round(e, 1), round(n, 1)] for e, n in nztm],
                "zoom": z,
                "attribution": "© OpenStreetMap contributors",
            }
        ),
        encoding="utf-8",
    )
    print(f"Wrote {out_image} ({mosaic.width}×{mosaic.height}) and {out_meta}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--zoom", type=int, default=13)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "web" / "public" / "data")
    args = parser.parse_args()
    build(CHRISTCHURCH_BBOX, args.zoom, args.out / "city-basemap.webp",
          args.out / "city-basemap.json")


if __name__ == "__main__":
    main()
