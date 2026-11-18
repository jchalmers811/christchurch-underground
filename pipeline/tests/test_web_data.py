"""Contract tests for the committed 3D viewer data (web/public/data/osu-sites.json).

The raw files never reach CI, but the exported JSON does, so check it here.
Regenerate with `python -m chch_pipeline.export_web`.
"""

import json
from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[2] / "web" / "public" / "data" / "osu-sites.json"


@pytest.fixture(scope="module")
def data():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_four_sites_with_known_zones(data):
    assert [s["id"] for s in data["sites"]] == ["avondale", "shirley", "ti-rakau", "meadows"]
    assert set(data["zones"]) == {"0", "2", "3", "4", "5", "6", "7"}
    assert all(z["colour"].startswith("#") for z in data["zones"].values())


def test_all_64_osu_cpts_are_present(data):
    osu = [h for s in data["sites"] for h in s["holes"] if h["source"] == "osu"]
    assert len(osu) == 64


def test_intervals_are_contiguous_and_end_at_the_final_depth(data):
    for site in data["sites"]:
        for h in (h for h in site["holes"] if h["source"] == "osu"):
            iv = h["intervals"]
            assert iv[0][0] == 0, h["id"]
            assert iv[-1][1] == pytest.approx(h["depth"], abs=0.01), h["id"]
            for (_, bottom, _), (top, _, _) in zip(iv, iv[1:], strict=False):
                assert top == pytest.approx(bottom, abs=0.005), h["id"]
            assert all(t < b for t, b, _ in iv), h["id"]
            assert {str(z) for _, _, z in iv} <= set(data["zones"]), h["id"]


def test_positions_are_local_and_compact(data):
    # Each OSU line is ~25 m long, so every hole should sit within ~20 m of its site centre.
    for site in data["sites"]:
        for h in site["holes"]:
            assert abs(h["x"]) < 20 and abs(h["y"]) < 20, (site["id"], h["id"])
        e, n = site["origin"]
        assert 1_560_000 < e < 1_585_000 and 5_170_000 < n < 5_190_000


def test_no_raw_traces_are_exported(data):
    # D-002: derived data only. Raw qc/fs/u2 readings must never appear.
    text = DATA.read_text(encoding="utf-8")
    for key in ('"qc"', '"fs"', '"u2"'):
        assert key not in text
