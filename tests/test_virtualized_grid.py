"""Virtualized grid invariants: target PO absent until scrolled into view."""

from __future__ import annotations

import json
from pathlib import Path

from fixturebench.eval.cases import load_suite
from fixturebench.eval.portal import ManagedPortal, PORTAL_SPECS

ROOT = Path(__file__).resolve().parents[1]


def test_v21_target_is_deep_in_list() -> None:
    data = json.loads((ROOT / "portals/v21/data/orders.json").read_text(encoding="utf-8"))
    ids = [o["po_number"] for o in data["orders"]]
    idx = ids.index("PO-1042")
    assert idx == data["target_index"]
    assert idx >= 40
    assert data["viewport_rows"] <= 10


def test_v21_initial_orders_html_omits_target_po() -> None:
    with ManagedPortal("v21", ROOT) as portal_url:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{portal_url}/login")
            page.fill('[data-testid="login-email"]', "vendor@fixturebench.test")
            page.fill('[data-testid="login-password"]', "fixturebench123")
            page.click('[data-testid="login-submit"]')
            page.wait_for_selector('[data-testid="virtual-viewport"]')
            page.wait_for_timeout(300)

            html = page.content()
            assert 'data-testid="po-link-PO-1042"' not in html
            assert page.locator('[data-testid="po-link-PO-1042"]').count() == 0
            # First window should have some other PO mounted
            assert page.locator('[data-testid^="po-link-"]').count() > 0

            viewport = page.locator('[data-testid="virtual-viewport"]')
            # Scroll toward the bottom where PO-1042 lives
            for _ in range(20):
                viewport.evaluate("el => { el.scrollTop = el.scrollTop + el.clientHeight; }")
                page.wait_for_timeout(80)
                if page.locator('[data-testid="po-link-PO-1042"]').count():
                    break

            assert page.locator('[data-testid="po-link-PO-1042"]').count() == 1
            browser.close()


def test_portal_registry_includes_v21() -> None:
    assert "v21" in PORTAL_SPECS
    suite = load_suite(ROOT / "eval" / "cases.json")
    case = next(c for c in suite.cases if c.id == "v21_po_1042_virtualized")
    assert case.portal == "v21"
    assert "virtualized" in case.tags
    assert "hard" in case.tags
