"""Playwright + LLM agentic loop for FixtureBench.

Pattern: observe → LLM chooses action → Playwright executes → repeat.

Requires an OpenAI-compatible API key:

    export OPENAI_API_KEY=sk-...
    # optional:
    export OPENAI_BASE_URL=https://api.openai.com/v1
    export OPENAI_MODEL=gpt-4.1-mini

Run:

    PYTHONPATH=. fixturebench run \\
      --agent examples.playwright_agentic_agent:PlaywrightAgenticAgent \\
      --case v1_po_1042 --headed
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from playwright.sync_api import sync_playwright

from fixturebench.adapters.protocol import AgentRunResult, EvalTask


SYSTEM_PROMPT = """You drive a browser to complete a structured extraction task.
Reply with a single JSON object only (no markdown), matching this schema:
{
  "action": "click" | "type" | "press" | "wait" | "finish" | "fail",
  "selector": "CSS selector or text=... (for click/type)",
  "text": "string to type, key to press, or wait ms",
  "payload": {
    "buyer_name": "string|null",
    "po_number": "string",
    "order_date": "YYYY-MM-DD|null",
    "lines": [{"raw_description": str, "raw_sku": str|null, "quantity": number, "unit": str|null}]
  },
  "reason": "short explanation"
}
On finish, payload must match the extracted record. On empty-state goals, finish with payload null.
Prefer durable selectors: [data-testid=...], input[name=...], text=Exact Label.
"""


def complete_json(*, system: str, user: dict[str, Any]) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completions API and parse JSON."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set OPENAI_API_KEY to run PlaywrightAgenticAgent "
            "(or use examples.playwright_smoke_agent:PlaywrightSmokeAgent for a no-LLM demo)."
        )

    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    body = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user)},
        ],
    }
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
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LLM HTTP {exc.code}: {detail}") from exc

    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)


class PlaywrightAgenticAgent:
    """LLM-driven Playwright agent — observe → act loop."""

    @property
    def name(self) -> str:
        return "playwright-agentic"

    def run(self, task: EvalTask) -> AgentRunResult:
        started = time.perf_counter()
        steps = 0
        llm_ms = 0.0

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=task.headless)
                page = browser.new_page()
                page.goto(task.url, wait_until="domcontentloaded")

                for _ in range(task.max_steps):
                    steps += 1
                    observation = self._observe(page)

                    llm_started = time.perf_counter()
                    action = complete_json(
                        system=SYSTEM_PROMPT,
                        user={
                            "goal": task.goal,
                            "email": task.email,
                            "password": task.password,
                            "target_id": task.target_id,
                            "observation": observation,
                        },
                    )
                    llm_ms += (time.perf_counter() - llm_started) * 1000

                    kind = action.get("action")
                    if kind == "click":
                        page.click(action["selector"], timeout=5000)
                        page.wait_for_load_state("domcontentloaded")
                    elif kind == "type":
                        page.fill(action["selector"], str(action.get("text", "")), timeout=5000)
                    elif kind == "press":
                        page.keyboard.press(str(action.get("text", "Enter")))
                    elif kind == "wait":
                        page.wait_for_timeout(int(action.get("text") or 1000))
                    elif kind == "finish":
                        browser.close()
                        return AgentRunResult(
                            success=True,
                            payload=action.get("payload"),
                            step_count=steps,
                            llm_duration_ms=llm_ms,
                            total_duration_ms=(time.perf_counter() - started) * 1000,
                            metadata={"model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")},
                        )
                    elif kind == "fail":
                        browser.close()
                        return AgentRunResult(
                            success=False,
                            failure_reason=action.get("reason", "agent failed"),
                            step_count=steps,
                            llm_duration_ms=llm_ms,
                            total_duration_ms=(time.perf_counter() - started) * 1000,
                        )
                    else:
                        browser.close()
                        return AgentRunResult(
                            success=False,
                            failure_reason=f"unknown action: {kind!r}",
                            step_count=steps,
                            llm_duration_ms=llm_ms,
                            total_duration_ms=(time.perf_counter() - started) * 1000,
                        )

                browser.close()
                return AgentRunResult(
                    success=False,
                    failure_reason="max_steps exceeded",
                    step_count=steps,
                    llm_duration_ms=llm_ms,
                    total_duration_ms=(time.perf_counter() - started) * 1000,
                )
        except Exception as exc:  # noqa: BLE001 — surface in eval report
            return AgentRunResult(
                success=False,
                failure_reason=str(exc),
                step_count=steps,
                llm_duration_ms=llm_ms,
                total_duration_ms=(time.perf_counter() - started) * 1000,
            )

    def _observe(self, page) -> dict[str, Any]:
        links = []
        for anchor in page.locator("a").all()[:40]:
            try:
                links.append(
                    {
                        "text": (anchor.inner_text() or "")[:80].strip(),
                        "href": anchor.get_attribute("href"),
                    }
                )
            except Exception:
                continue

        inputs = []
        for inp in page.locator("input, button, textarea, summary").all()[:40]:
            try:
                inputs.append(
                    {
                        "tag": inp.evaluate("el => el.tagName.toLowerCase()"),
                        "type": inp.get_attribute("type"),
                        "name": inp.get_attribute("name"),
                        "testid": inp.get_attribute("data-testid"),
                        "text": (inp.inner_text() or "")[:80].strip(),
                    }
                )
            except Exception:
                continue

        return {
            "url": page.url,
            "title": page.title(),
            "text": page.inner_text("body")[:4000],
            "links": links,
            "controls": inputs,
        }
