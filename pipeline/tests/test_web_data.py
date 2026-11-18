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


# --- Per-site detail files (traces + liquefaction terms) -----------------------------------

SITE_DIR = DATA.parent / "sites"
CITY = DATA.parent / "city-wells.json"


@pytest.fixture(scope="module")
def details(data):
    return {
        s["id"]: json.loads((SITE_DIR / f"{s['id']}.json").read_text(encoding="utf-8"))
        for s in data["sites"]
    }


def test_every_osu_cpt_has_detail_rows(data, details):
    for site in data["sites"]:
        osu = {h["id"] for h in site["holes"] if h["source"] == "osu"}
        assert set(details[site["id"]]["holes"]) == osu


def test_detail_rows_are_well_formed(details):
    for d in details.values():
        assert d["columns"] == ["depth", "qc", "fs", "u2", "isbt", "crr_m", "csr_per_g"]
        for hole_id, rows in d["holes"].items():
            depths = [r[0] for r in rows]
            assert depths == sorted(depths) and len(set(depths)) == len(depths), hole_id
            for _, qc, _, _, _, crr, csr in rows:
                assert qc is None or 0 <= qc < 100, hole_id
                # CRR (with MSF) is between ~0.05 and ~0.7 for Qtn,cs < 160.
                assert crr is None or 0.04 < crr < 0.8, hole_id
                assert csr is None or 0 < csr < 2, hole_id


def test_liquefaction_is_only_possible_below_groundwater(data, details):
    for site in data["sites"]:
        for h in (h for h in site["holes"] if h["source"] == "osu"):
            for depth, *_, crr, _ in details[site["id"]]["holes"][h["id"]]:
                if crr is not None:
                    assert depth > h["gw"], (h["id"], depth)


# --- City wells ------------------------------------------------------------------------------

def test_city_wells_are_inside_the_box_and_have_no_personal_fields():
    city = json.loads(CITY.read_text(encoding="utf-8"))
    x0, x1, y0, y1 = city["bbox"]
    assert len(city["wells"]) > 5000
    for x, y, depth, strata, well_no, _ in city["wells"]:
        assert x0 <= x <= x1 and y0 <= y <= y1, well_no
        assert depth > 0 and strata >= 0
    assert city["columns"] == ["x", "y", "depth", "strata", "well_no", "year"]
    assert "OWNER" not in CITY.read_text(encoding="utf-8").upper()
