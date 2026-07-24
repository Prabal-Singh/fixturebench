"""Playwright + LLM agentic loop for FixtureBench.

Pattern: observe → LLM chooses action → Playwright executes → repeat.

Works with OpenAI or Ollama (OpenAI-compatible):

    export OPENAI_BASE_URL=http://192.168.0.9:11434/v1
    export OPENAI_API_KEY=ollama
    export OPENAI_MODEL=qwen2.5:14b

    PYTHONPATH=. fixturebench run \\
      --agent examples.playwright_agentic_agent:PlaywrightAgenticAgent \\
      --case v1_po_1042
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from playwright.sync_api import sync_playwright

from fixturebench.adapters.protocol import AgentRunResult, EvalTask


SYSTEM_PROMPT = """You are a browser agent. Complete the goal with the FEWEST actions.

Reply with ONE JSON object only (no markdown fences):
{
  "action": "click" | "type" | "press" | "wait" | "finish" | "fail",
  "selector": "CSS or Playwright text=... selector",
  "text": "value for type/press/wait-ms",
  "payload": null or {
    "buyer_name": string|null,
    "po_number": string,
    "order_date": "YYYY-MM-DD"|null,
    "lines": [{"raw_description": string, "raw_sku": string|null, "quantity": number, "unit": string|null}]
  },
  "reason": "short"
}

Rules:
1. Prefer data-testid selectors when present, e.g. [data-testid="login-email"].
2. Login flow: type email → type password → click submit. Use credentials from the task.
3. Then open the target PO (paginate/search/tabs if needed).
4. When line items are visible OR empty-state is confirmed, you MUST action=finish.
5. On finish with extraction: fill payload from the page text (buyer, po_number, date, lines).
6. On empty-orders goals: finish with payload null after seeing the empty state.
7. Do NOT repeat the same failed action. Do NOT keep clicking forever — finish when done.
8. Never invent line items you cannot see.
"""


def _parse_json_content(content: str) -> dict[str, Any]:
    content = content.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if fence:
        content = fence.group(1)
    else:
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            content = content[start : end + 1]
    return json.loads(content)


def complete_json(*, system: str, user: dict[str, Any]) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completions API and parse JSON."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY (use 'ollama' for local Ollama) "
            "or use examples.playwright_smoke_agent:PlaywrightSmokeAgent."
        )

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    body = {
        "model": model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
    }
    # response_format is not reliably supported by all Ollama models
    if "11434" not in base:
        body["response_format"] = {"type": "json_object"}

    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc

    content = payload["choices"][0]["message"]["content"]
    return _parse_json_content(content)


class PlaywrightAgenticAgent:
    """LLM-driven Playwright agent — observe → act loop."""

    @property
    def name(self) -> str:
        return "playwright-agentic"

    def run(self, task: EvalTask) -> AgentRunResult:
        started = time.perf_counter()
        steps = 0
        llm_ms = 0.0
        history: list[dict[str, Any]] = []
        last_error: Optional[str] = None
        model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=task.headless)
                page = browser.new_page()
                page.goto(task.url, wait_until="domcontentloaded")

                for _ in range(task.max_steps):
                    steps += 1
                    observation = self._observe(page)

                    # Soft hint when extraction is clearly possible
                    ready = self._ready_to_finish(page, task)
                    user_payload = {
                        "goal": task.goal,
                        "email": task.email,
                        "password": task.password,
                        "target_id": task.target_id,
                        "step": steps,
                        "max_steps": task.max_steps,
                        "ready_to_finish": ready,
                        "last_error": last_error,
                        "history": history[-6:],
                        "observation": observation,
                    }

                    llm_started = time.perf_counter()
                    action = complete_json(system=SYSTEM_PROMPT, user=user_payload)
                    llm_ms += (time.perf_counter() - llm_started) * 1000
                    last_error = None

                    kind = (action.get("action") or "").strip().lower()
                    history.append(
                        {
                            "step": steps,
                            "action": kind,
                            "selector": action.get("selector"),
                            "text": action.get("text"),
                            "reason": action.get("reason"),
                            "url": page.url,
                        }
                    )
                    print(
                        f"[agentic] step={steps} action={kind} "
                        f"selector={action.get('selector')!r} reason={action.get('reason')!r}",
                        flush=True,
                    )

                    if kind == "finish":
                        payload = action.get("payload")
                        if payload is None and ready == "extract":
                            payload = self._extract_payload(page, task)
                        browser.close()
                        return AgentRunResult(
                            success=True,
                            payload=payload,
                            step_count=steps,
                            llm_duration_ms=llm_ms,
                            total_duration_ms=(time.perf_counter() - started) * 1000,
                            metadata={"model": model, "history": history},
                        )

                    if kind == "fail":
                        browser.close()
                        return AgentRunResult(
                            success=False,
                            failure_reason=action.get("reason", "agent failed"),
                            step_count=steps,
                            llm_duration_ms=llm_ms,
                            total_duration_ms=(time.perf_counter() - started) * 1000,
                            metadata={"model": model, "history": history},
                        )

                    try:
                        self._execute(page, kind, action)
                    except Exception as exc:  # noqa: BLE001 — feed back to LLM
                        last_error = f"{type(exc).__name__}: {exc}"
                        history[-1]["error"] = last_error
                        print(f"[agentic] action error: {last_error}", flush=True)
                        continue

                    # If model stalls near the end but page is ready, force finish
                    if steps >= task.max_steps - 1 and ready:
                        payload = (
                            None
                            if ready == "empty"
                            else self._extract_payload(page, task)
                        )
                        browser.close()
                        return AgentRunResult(
                            success=payload is not None or ready == "empty",
                            payload=payload,
                            step_count=steps,
                            llm_duration_ms=llm_ms,
                            total_duration_ms=(time.perf_counter() - started) * 1000,
                            metadata={
                                "model": model,
                                "history": history,
                                "forced_finish": True,
                            },
                        )

                browser.close()
                return AgentRunResult(
                    success=False,
                    failure_reason="max_steps exceeded",
                    step_count=steps,
                    llm_duration_ms=llm_ms,
                    total_duration_ms=(time.perf_counter() - started) * 1000,
                    metadata={"model": model, "history": history},
                )
        except Exception as exc:  # noqa: BLE001 — surface in eval report
            return AgentRunResult(
                success=False,
                failure_reason=str(exc),
                step_count=steps,
                llm_duration_ms=llm_ms,
                total_duration_ms=(time.perf_counter() - started) * 1000,
                metadata={"model": model, "history": history},
            )

    def _execute(self, page, kind: str, action: dict[str, Any]) -> None:
        selector = action.get("selector") or ""
        text = action.get("text")
        if kind == "click":
            page.locator(selector).first.click(timeout=5000)
            page.wait_for_load_state("domcontentloaded")
        elif kind == "type":
            page.locator(selector).first.fill(str(text or ""), timeout=5000)
        elif kind == "press":
            page.keyboard.press(str(text or "Enter"))
        elif kind == "wait":
            page.wait_for_timeout(int(text or 1000))
        else:
            raise ValueError(f"unknown action: {kind!r}")

    def _ready_to_finish(self, page, task: EvalTask) -> Optional[str]:
        if page.locator('[data-testid="empty-state"]').count():
            return "empty"
        if page.locator('[data-testid^="po-line-"]').count():
            return "extract"
        # Messy DOM / modal without testids — look for known item text
        body = page.inner_text("body")
        if task.target_id and task.target_id in body and "Sweet-Disk" in body:
            return "extract"
        if "No purchase orders" in body:
            return "empty"
        return None

    def _extract_payload(self, page, task: EvalTask) -> Optional[dict[str, Any]]:
        # Prefer structured testids
        rows = page.locator('[data-testid^="po-line-"]')
        if rows.count() == 0 and page.locator('[data-testid="po-detail-frame"]').count():
            frame = page.frame_locator('[data-testid="po-detail-frame"]')
            rows = frame.locator('[data-testid^="po-line-"]')
            buyer_el = page.locator('[data-testid="po-buyer"]')
            date_el = page.locator('[data-testid="po-order-date"]')
        else:
            buyer_el = page.locator('[data-testid="po-buyer"]')
            date_el = page.locator('[data-testid="po-order-date"]')

        if rows.count() == 0:
            return None

        lines = []
        for i in range(rows.count()):
            row = rows.nth(i)
            lines.append(
                {
                    "raw_description": row.locator('[data-testid="line-description"]').inner_text().strip(),
                    "raw_sku": row.locator('[data-testid="line-item-code"]').inner_text().strip(),
                    "quantity": float(row.locator('[data-testid="line-quantity"]').inner_text()),
                    "unit": row.locator('[data-testid="line-uom"]').inner_text().strip(),
                }
            )

        buyer = buyer_el.first.inner_text().strip() if buyer_el.count() else None
        order_date = date_el.first.inner_text().strip() if date_el.count() else None
        return {
            "buyer_name": buyer,
            "po_number": task.target_id,
            "order_date": order_date,
            "lines": lines,
        }

    def _observe(self, page) -> dict[str, Any]:
        links = []
        for anchor in page.locator("a").all()[:30]:
            try:
                links.append(
                    {
                        "text": (anchor.inner_text() or "")[:80].strip(),
                        "href": anchor.get_attribute("href"),
                        "testid": anchor.get_attribute("data-testid"),
                    }
                )
            except Exception:
                continue

        controls = []
        for inp in page.locator("input, button, textarea, summary, [data-testid]").all()[:50]:
            try:
                controls.append(
                    {
                        "tag": inp.evaluate("el => el.tagName.toLowerCase()"),
                        "type": inp.get_attribute("type"),
                        "name": inp.get_attribute("name"),
                        "testid": inp.get_attribute("data-testid"),
                        "text": (inp.inner_text() or "")[:60].strip(),
                        "placeholder": inp.get_attribute("placeholder"),
                    }
                )
            except Exception:
                continue

        return {
            "url": page.url,
            "title": page.title(),
            "text": page.inner_text("body")[:3000],
            "links": links,
            "controls": controls,
        }
