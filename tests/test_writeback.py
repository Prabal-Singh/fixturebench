"""Write-back scoring: acknowledge mutates portal state; harness asserts it."""

from __future__ import annotations

import json
from pathlib import Path

from fixturebench.adapters.protocol import AgentRunResult
from fixturebench.eval.cases import build_goal, load_expected_state, load_suite
from fixturebench.eval.models import EvalDefaults
from fixturebench.eval.portal import ManagedPortal
from fixturebench.eval.runner import EvalRunner
from fixturebench.eval.scorer import compare_portal_state, fetch_portal_state
from fixturebench.models.po import RawPurchaseOrder

ROOT = Path(__file__).resolve().parents[1]


class _AckExtractAgent:
    """Logs in, acknowledges PO-1042, extracts lines via DOM heuristics."""

    def __init__(self, *, acknowledge: bool = True) -> None:
        self._acknowledge = acknowledge

    @property
    def name(self) -> str:
        return "ack-extract-test"

    def run(self, task):
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{task.url}/login", wait_until="domcontentloaded")
            page.fill('[data-testid="login-email"]', task.email)
            page.fill('[data-testid="login-password"]', task.password)
            page.click('[data-testid="login-submit"]')
            page.wait_for_load_state("domcontentloaded")
            page.click(f'[data-testid="po-link-{task.target_id}"]')
            page.wait_for_load_state("domcontentloaded")
            if self._acknowledge:
                page.click('[data-testid="acknowledge-button"]')
                page.wait_for_load_state("domcontentloaded")

            buyer = page.locator('[data-testid="po-buyer"]').inner_text()
            order_date = page.locator('[data-testid="po-order-date"]').inner_text()
            rows = page.locator('[data-testid="po-lines-table"] tbody tr')
            lines = []
            for i in range(rows.count()):
                row = rows.nth(i)
                lines.append(
                    {
                        "raw_description": row.locator('[data-testid="line-description"]').inner_text(),
                        "raw_sku": row.locator('[data-testid="line-item-code"]').inner_text(),
                        "quantity": float(row.locator('[data-testid="line-quantity"]').inner_text()),
                        "unit": row.locator('[data-testid="line-uom"]').inner_text(),
                    }
                )
            browser.close()

            if not lines:
                return AgentRunResult(success=False, failure_reason="no lines", step_count=4)

            po = RawPurchaseOrder.model_validate(
                {
                    "buyer_name": buyer,
                    "po_number": task.target_id,
                    "order_date": order_date,
                    "lines": lines,
                }
            )
            return AgentRunResult(success=True, payload=po, step_count=5 if self._acknowledge else 4)


def test_compare_portal_state_pass_and_fail() -> None:
    expected = {"po_number": "PO-1042", "acknowledged": True, "status": "Acknowledged"}
    ok = compare_portal_state(dict(expected), expected)
    assert ok.passed
    bad = compare_portal_state(
        {"po_number": "PO-1042", "acknowledged": False, "status": "Open"},
        expected,
    )
    assert not bad.passed
    assert any("acknowledged" in m for m in bad.mismatches)


def test_v19_eval_state_endpoint_reflects_acknowledge() -> None:
    with ManagedPortal("v19", ROOT) as portal_url:
        before = fetch_portal_state(portal_url, "PO-1042")
        assert before["acknowledged"] is False
        assert before["status"] == "Open"

        # Drive acknowledge through the real form flow.
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{portal_url}/login")
            page.fill('[data-testid="login-email"]', "vendor@fixturebench.test")
            page.fill('[data-testid="login-password"]', "fixturebench123")
            page.click('[data-testid="login-submit"]')
            page.click('[data-testid="po-link-PO-1042"]')
            page.click('[data-testid="acknowledge-button"]')
            page.wait_for_load_state("domcontentloaded")
            browser.close()

        after = fetch_portal_state(portal_url, "PO-1042")
        assert after["acknowledged"] is True
        assert after["status"] == "Acknowledged"


def test_acknowledge_case_fails_without_write_back() -> None:
    runner = EvalRunner(_AckExtractAgent(acknowledge=False), root=ROOT)
    report = runner.run(case_ids=["v19_po_1042_acknowledge"], write_results=False)
    assert report.summary.total == 1
    result = report.cases[0]
    assert result.passed is False
    assert result.state_pass is False


def test_acknowledge_case_passes_with_write_back_and_extract() -> None:
    runner = EvalRunner(_AckExtractAgent(acknowledge=True), root=ROOT)
    report = runner.run(case_ids=["v19_po_1042_acknowledge"], write_results=False)
    result = report.cases[0]
    assert result.extraction_pass is True
    assert result.state_pass is True
    assert result.passed is True
    assert result.state_comparison is not None
    assert result.state_comparison.passed


def test_acknowledge_case_loads_expected_state() -> None:
    suite = load_suite(ROOT / "eval" / "cases.json")
    case = next(c for c in suite.cases if c.id == "v19_po_1042_acknowledge")
    assert case.outcome == "acknowledge_po"
    state = load_expected_state(ROOT, case)
    assert state == {
        "po_number": "PO-1042",
        "acknowledged": True,
        "status": "Acknowledged",
    }
    goal = build_goal(case, EvalDefaults())
    assert "Acknowledge" in goal


def test_expected_state_fixture_on_disk() -> None:
    path = ROOT / "tests/fixtures/expected_state_po_1042_acked.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["acknowledged"] is True
