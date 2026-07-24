"""Invariants for multi-buyer ambiguity and stale-cache portals."""

from __future__ import annotations

import json
from pathlib import Path

from fixturebench.eval.cases import load_suite
from fixturebench.eval.portal import ManagedPortal, PORTAL_SPECS

ROOT = Path(__file__).resolve().parents[1]


def test_portal_registry_covers_v1_through_v23() -> None:
    expected = {f"v{i}" for i in range(1, 24)}
    assert set(PORTAL_SPECS) == expected


def test_v22_two_open_po_1042_different_buyers() -> None:
    data = json.loads((ROOT / "portals/v22/data/orders.json").read_text(encoding="utf-8"))
    matches = [o for o in data["orders"] if o["po_number"] == "PO-1042"]
    assert len(matches) == 2
    buyers = {o["buyer_name"] for o in matches}
    assert buyers == {"Midwest Foods Co-op", "Pacific Retail Group"}
    target = next(o for o in matches if o["is_target"])
    decoy = next(o for o in matches if not o["is_target"])
    assert target["buyer_name"] == "Midwest Foods Co-op"
    assert decoy["order_id"] != target["order_id"]
    # Decoy is listed first so naive first-match agents fail.
    ids = [o["order_id"] for o in data["orders"] if o["po_number"] == "PO-1042"]
    assert ids[0] == decoy["order_id"]


def test_v22_first_po_link_is_decoy_midwest_is_correct() -> None:
    with ManagedPortal("v22", ROOT) as portal_url:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{portal_url}/login")
            page.fill('[data-testid="login-email"]', "vendor@fixturebench.test")
            page.fill('[data-testid="login-password"]', "fixturebench123")
            page.click('[data-testid="login-submit"]')
            page.wait_for_selector('[data-testid="orders-table"]')

            links = page.locator('[data-testid="po-link-PO-1042"]')
            assert links.count() == 2
            assert links.first.get_attribute("data-buyer") == "Pacific Retail Group"
            midwest = page.locator(
                'a[data-testid="po-link-PO-1042"][data-buyer="Midwest Foods Co-op"]'
            )
            midwest.click()
            page.wait_for_load_state("domcontentloaded")
            assert page.locator('[data-testid="po-buyer"]').inner_text() == "Midwest Foods Co-op"
            assert page.locator('[data-testid="po-lines-table"] tbody tr').count() == 3
            browser.close()


def test_v23_default_detail_is_stale_until_refresh() -> None:
    with ManagedPortal("v23", ROOT) as portal_url:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{portal_url}/login")
            page.fill('[data-testid="login-email"]', "vendor@fixturebench.test")
            page.fill('[data-testid="login-password"]', "fixturebench123")
            page.click('[data-testid="login-submit"]')
            page.click('[data-testid="po-link-PO-1042"]')
            page.wait_for_load_state("domcontentloaded")

            assert page.locator('[data-testid="cache-status"]').inner_text().strip() == "stale"
            assert page.locator('[data-testid="stale-banner"]').count() == 1
            stale_qty = page.locator('[data-testid="line-quantity"]').first.inner_text()
            assert stale_qty == "10"

            page.click('[data-testid="refresh-from-source"]')
            page.wait_for_load_state("domcontentloaded")
            assert page.locator('[data-testid="cache-status"]').inner_text().strip() == "fresh"
            assert page.locator('[data-testid="line-quantity"]').first.inner_text() == "24"
            assert page.locator('[data-testid="po-lines-table"] tbody tr').count() == 3
            browser.close()


def test_suite_includes_v22_v23_hard_cases() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    by_id = {c.id: c for c in suite.cases}
    assert "multi-buyer" in by_id["v22_po_1042_multibuyer"].tags
    assert "stale-cache" in by_id["v23_po_1042_stale_cache"].tags
    assert "hard" in by_id["v22_po_1042_multibuyer"].tags
    assert "hard" in by_id["v23_po_1042_stale_cache"].tags
