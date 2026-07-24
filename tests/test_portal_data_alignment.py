"""Guardrails: portal data must stay aligned with fixtures and catalog claims."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_v2_portal_matches_messy_uom_fixture() -> None:
    portal = _load_json(ROOT / "portals/v2/data/orders.json")
    fixture = _load_json(ROOT / "tests/fixtures/expected_po_1042_v2.json")

    assert portal["buyer"]["name"] == "Pacific Retail Group"
    assert fixture["buyer_name"] == "Pacific Retail Group"

    order = next(o for o in portal["orders"] if o["po_number"] == "PO-1042")
    assert [line["uom"] for line in order["lines"]] == ["CASE", "each", "EA"]
    assert [line["unit"] for line in fixture["lines"]] == ["CASE", "each", "EA"]


def test_v3_portal_matches_pagination_fixture() -> None:
    portal = _load_json(ROOT / "portals/v3/data/orders.json")
    fixture = _load_json(ROOT / "tests/fixtures/expected_po_1042_v3.json")
    fixture_1039 = _load_json(ROOT / "tests/fixtures/expected_po_1039.json")

    assert portal["buyer"]["name"] == "National Grocers Alliance"
    assert fixture["buyer_name"] == "National Grocers Alliance"
    assert fixture_1039["buyer_name"] == "National Grocers Alliance"
    assert portal.get("page_size") == 2

    order_ids = [o["po_number"] for o in portal["orders"]]
    page_size = portal["page_size"]

    # PO-1042 on page 2 (index 2 → page 2 with page_size 2)
    idx_1042 = order_ids.index("PO-1042")
    assert idx_1042 // page_size + 1 == 2

    # PO-1039 on page 3
    idx_1039 = order_ids.index("PO-1039")
    assert idx_1039 // page_size + 1 == 3


def test_v3_page1_does_not_contain_target_po_1042() -> None:
    portal = _load_json(ROOT / "portals/v3/data/orders.json")
    page_size = portal["page_size"]
    page1 = [o["po_number"] for o in portal["orders"][:page_size]]
    assert "PO-1042" not in page1


def test_v17_decoy_rows_precede_real_po() -> None:
    portal = _load_json(ROOT / "portals/v17/data/orders.json")
    ids = [o["po_number"] for o in portal["orders"]]
    assert ids.index("PO-1042-DRAFT") < ids.index("PO-1042")
    assert ids.index("PO-1042A") < ids.index("PO-1042")
    real = next(o for o in portal["orders"] if o["po_number"] == "PO-1042")
    assert real["status"] == "Open"
    assert not real.get("is_decoy")
    decoys = [o for o in portal["orders"] if o.get("is_decoy")]
    assert len(decoys) >= 3


def test_hard_cases_are_tagged() -> None:
    suite = _load_json(ROOT / "eval/cases.json")
    hard_ids = {
        "v14_po_1042_lazy_accordion",
        "v15_po_1042_unlabeled",
        "v16_po_1042_nested_menu",
        "v17_po_1042_decoys",
        "v18_po_1042_interstitial",
        "v19_po_1042_acknowledge",
        "v20_po_1042_mfa",
        "v21_po_1042_virtualized",
    }
    by_id = {case["id"]: case for case in suite["cases"]}
    for case_id in hard_ids:
        assert case_id in by_id
        assert "hard" in by_id[case_id]["tags"]
