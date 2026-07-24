"""Deterministic Playwright agent for FixtureBench smoke demos.

Handles the baseline extraction flow (login → open target → read lines).
Not meant to solve hard cases (CSV, iframe, session expiry, etc.).
"""

from __future__ import annotations

import time
from datetime import date
from typing import Optional

from playwright.sync_api import sync_playwright

from fixturebench.adapters.protocol import AgentRunResult, EvalTask
from fixturebench.models.po import RawPOLine, RawPurchaseOrder


class PlaywrightSmokeAgent:
    """Simple Playwright agent for baseline / smoke cases."""

    @property
    def name(self) -> str:
        return "playwright-smoke"

    def run(self, task: EvalTask) -> AgentRunResult:
        started = time.perf_counter()
        steps = 0

        if not task.target_id:
            # Empty-state cases: login and confirm no orders.
            return self._run_empty(task, started)

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=task.headless)
                page = browser.new_page()
                page.goto(f"{task.url}/login", wait_until="domcontentloaded")
                steps += 1

                page.fill('[data-testid="login-email"], input[name="email"]', task.email)
                page.fill('[data-testid="login-password"], input[name="password"]', task.password)
                page.click('[data-testid="login-submit"], button[type="submit"]')
                page.wait_for_load_state("domcontentloaded")
                steps += 1

                # Pagination / search / tabs — best-effort for smoke demos
                self._reveal_target(page, task.target_id)
                steps += 1

                link = page.locator(
                    f'[data-testid="po-link-{task.target_id}"], a:has-text("{task.target_id}")'
                ).first
                link.click()
                page.wait_for_load_state("domcontentloaded")
                steps += 1

                # Accordion / delayed load
                expand = page.locator('[data-testid="expand-line-items"]')
                if expand.count():
                    expand.first.click()
                    steps += 1

                # v19 write-back: acknowledge before lines unlock
                ack = page.locator('[data-testid="acknowledge-button"]')
                if ack.count():
                    ack.first.click()
                    page.wait_for_load_state("domcontentloaded")
                    steps += 1

                page.wait_for_timeout(1600)  # covers v12 delayed load

                po = self._extract_po(page, task)
                browser.close()

                if po is None or not po.lines:
                    return AgentRunResult(
                        success=False,
                        failure_reason="Could not extract PO line items",
                        step_count=steps,
                        total_duration_ms=(time.perf_counter() - started) * 1000,
                    )

                return AgentRunResult(
                    success=True,
                    payload=po,
                    step_count=steps,
                    total_duration_ms=(time.perf_counter() - started) * 1000,
                )
        except Exception as exc:  # noqa: BLE001 — surface to eval report
            return AgentRunResult(
                success=False,
                failure_reason=str(exc),
                step_count=steps,
                total_duration_ms=(time.perf_counter() - started) * 1000,
            )

    def _run_empty(self, task: EvalTask, started: float) -> AgentRunResult:
        steps = 0
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=task.headless)
                page = browser.new_page()
                page.goto(f"{task.url}/login", wait_until="domcontentloaded")
                steps += 1
                page.fill('[data-testid="login-email"], input[name="email"]', task.email)
                page.fill('[data-testid="login-password"], input[name="password"]', task.password)
                page.click('[data-testid="login-submit"], button[type="submit"]')
                page.wait_for_load_state("domcontentloaded")
                steps += 1
                empty = page.locator('[data-testid="empty-state"]')
                ok = empty.count() > 0
                browser.close()
                return AgentRunResult(
                    success=ok,
                    payload=None,
                    failure_reason=None if ok else "Empty state not found",
                    step_count=steps,
                    total_duration_ms=(time.perf_counter() - started) * 1000,
                )
        except Exception as exc:  # noqa: BLE001
            return AgentRunResult(
                success=False,
                failure_reason=str(exc),
                step_count=steps,
                total_duration_ms=(time.perf_counter() - started) * 1000,
            )

    def _reveal_target(self, page, target_id: str) -> None:
        # v5 tabs
        if page.locator('[data-testid="tab-all"]').count():
            if page.locator(f'[data-testid="po-link-{target_id}"]').count() == 0:
                page.click('[data-testid="tab-all"]')
                page.wait_for_load_state("domcontentloaded")

        # v10 search
        if page.locator('[data-testid="search-input"]').count():
            if page.locator(f'[data-testid="po-link-{target_id}"]').count() == 0:
                page.fill('[data-testid="search-input"]', target_id)
                page.click('[data-testid="search-submit"]')
                page.wait_for_load_state("domcontentloaded")

        # v21 virtualized grid — scroll until the target row mounts
        viewport = page.locator('[data-testid="virtual-viewport"]')
        if viewport.count():
            for _ in range(30):
                if page.locator(f'[data-testid="po-link-{target_id}"]').count():
                    return
                viewport.evaluate("el => { el.scrollTop = el.scrollTop + el.clientHeight; }")
                page.wait_for_timeout(60)

        # v3 pagination — click next until found or exhausted
        for _ in range(5):
            if page.locator(f'[data-testid="po-link-{target_id}"], a:has-text("{target_id}")').count():
                return
            nxt = page.locator('[data-testid="orders-next"]')
            if not nxt.count() or not nxt.first.is_enabled():
                return
            nxt.first.click()
            page.wait_for_load_state("domcontentloaded")

    def _extract_po(self, page, task: EvalTask) -> Optional[RawPurchaseOrder]:
        # Prefer iframe (v11)
        frame = page.frame_locator('[data-testid="po-detail-frame"]')
        scope = page
        try:
            if page.locator('[data-testid="po-detail-frame"]').count():
                # Use frame content for lines
                lines = self._read_lines_from_frame(page)
                buyer = page.locator('[data-testid="po-buyer"]').first.inner_text(timeout=1000)
            else:
                lines = self._read_lines(page)
                buyer_el = page.locator('[data-testid="po-buyer"]')
                buyer = buyer_el.first.inner_text() if buyer_el.count() else None
        except Exception:
            lines = self._read_lines(page)
            buyer_el = page.locator('[data-testid="po-buyer"]')
            buyer = buyer_el.first.inner_text() if buyer_el.count() else None

        if not lines:
            # Modal (v8) — already on same page
            lines = self._read_lines(page)

        order_date = None
        date_el = page.locator('[data-testid="po-order-date"]')
        if date_el.count():
            try:
                order_date = date.fromisoformat(date_el.first.inner_text().strip())
            except ValueError:
                order_date = None

        if not lines:
            return None

        return RawPurchaseOrder(
            buyer_name=buyer.strip() if buyer else None,
            po_number=task.target_id,
            order_date=order_date,
            lines=lines,
        )

    def _read_lines(self, page) -> list[RawPOLine]:
        rows = page.locator('[data-testid^="po-line-"]')
        count = rows.count()
        lines: list[RawPOLine] = []
        for i in range(count):
            row = rows.nth(i)
            sku = row.locator('[data-testid="line-item-code"]').inner_text()
            desc = row.locator('[data-testid="line-description"]').inner_text()
            qty = float(row.locator('[data-testid="line-quantity"]').inner_text())
            uom = row.locator('[data-testid="line-uom"]').inner_text()
            lines.append(
                RawPOLine(raw_description=desc.strip(), raw_sku=sku.strip(), quantity=qty, unit=uom.strip())
            )
        return lines

    def _read_lines_from_frame(self, page) -> list[RawPOLine]:
        frame = page.frame_locator('[data-testid="po-detail-frame"]')
        rows = frame.locator('[data-testid^="po-line-"]')
        # wait briefly for frame content
        page.wait_for_timeout(300)
        count = rows.count()
        lines: list[RawPOLine] = []
        for i in range(count):
            row = rows.nth(i)
            sku = row.locator('[data-testid="line-item-code"]').inner_text()
            desc = row.locator('[data-testid="line-description"]').inner_text()
            qty = float(row.locator('[data-testid="line-quantity"]').inner_text())
            uom = row.locator('[data-testid="line-uom"]').inner_text()
            lines.append(
                RawPOLine(raw_description=desc.strip(), raw_sku=sku.strip(), quantity=qty, unit=uom.strip())
            )
        return lines
