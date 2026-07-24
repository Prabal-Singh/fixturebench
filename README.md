# FixtureBench

**Deterministic eval for browser agents that work buyer / supplier portals.**

Fake Coupa-style portals. Real failure modes (pagination, CSV export, session expiry, MFA, decoy POs). Score extracted purchase orders against golden fixtures — not LLM judges, not live websites.

Built for teams automating **procurement workflows** (login → find PO → extract / acknowledge). Not another generic web-agent leaderboard — those already exist.

---

## Getting started

### Install

```bash
git clone https://github.com/Prabal-Singh/fixturebench.git
cd fixturebench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[envs,dev]"
pip install playwright && playwright install chromium
```

### Run the smoke suite (60 seconds)

```bash
# list cases
fixturebench list

# deterministic Playwright demo agent — solves easy cases
PYTHONPATH=. fixturebench run \
  --agent examples.playwright_smoke_agent:PlaywrightSmokeAgent \
  --tag smoke

# watch the browser
PYTHONPATH=. fixturebench run \
  --agent examples.playwright_smoke_agent:PlaywrightSmokeAgent \
  --case v1_po_1042 --headed
```

You should see **4/4 PASS** on the smoke tag (v1, v2, v3, v13).

### Plug in your agent

Any browser stack works. Implement **one method**; FixtureBench starts portals, runs cases, and scores.

```python
# my_agent.py
from fixturebench import AgentRunResult, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        # task.url        — portal already running
        # task.goal       — e.g. open PO-1042 and extract lines
        # task.target_id  — PO number
        # task.email / task.password / task.max_steps / task.headless
        ...
        return AgentRunResult(success=True, payload=extracted_po, step_count=7)
```

```bash
PYTHONPATH=. fixturebench run --agent my_agent:MyAgent --tag smoke
```

Or from Python:

```python
from fixturebench import run
from my_agent import MyAgent

report = run(MyAgent(), tags=["smoke"])
print(report.summary.passed, "/", report.summary.total)
```

---

## Example: Playwright + agentic (LLM) loop

Deterministic scripts solve easy cases. Real portal agents need **observe → reason → act**. Shape below — full file: [`examples/playwright_agentic_agent.py`](examples/playwright_agentic_agent.py).

```python
import json
from playwright.sync_api import sync_playwright
from fixturebench import AgentRunResult, EvalTask

# Use any LLM client that returns JSON (OpenAI, Anthropic, Ollama, …)
from my_llm import complete_json

ACTIONS = ["click", "type", "press", "wait", "finish", "fail"]

class PlaywrightAgenticAgent:
    @property
    def name(self) -> str:
        return "playwright-agentic"

    def run(self, task: EvalTask) -> AgentRunResult:
        steps = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=task.headless)
            page = browser.new_page()
            page.goto(task.url)

            for _ in range(task.max_steps):
                steps += 1
                observation = {
                    "url": page.url,
                    "title": page.title(),
                    "text": page.inner_text("body")[:4000],
                    "links": [
                        {"text": a.inner_text()[:80], "href": a.get_attribute("href")}
                        for a in page.locator("a").all()[:40]
                    ],
                }

                action = complete_json(
                    system="You drive a buyer portal. Reply with JSON only.",
                    user={
                        "goal": task.goal,
                        "email": task.email,
                        "password": task.password,
                        "target_id": task.target_id,
                        "observation": observation,
                        "schema": {
                            "action": ACTIONS,
                            "selector": "css or text selector",
                            "text": "for type/press",
                            "payload": "on finish: extracted PO dict",
                            "reason": "short",
                        },
                    },
                )

                kind = action["action"]
                if kind == "click":
                    page.click(action["selector"])
                elif kind == "type":
                    page.fill(action["selector"], action["text"])
                elif kind == "press":
                    page.keyboard.press(action["text"])
                elif kind == "wait":
                    page.wait_for_timeout(int(action.get("text") or 1000))
                elif kind == "finish":
                    browser.close()
                    return AgentRunResult(
                        success=True,
                        payload=action.get("payload"),
                        step_count=steps,
                    )
                elif kind == "fail":
                    browser.close()
                    return AgentRunResult(
                        success=False,
                        failure_reason=action.get("reason", "agent failed"),
                        step_count=steps,
                    )

            browser.close()
            return AgentRunResult(
                success=False,
                failure_reason="max_steps exceeded",
                step_count=steps,
            )
```

```bash
export OPENAI_API_KEY=...   # or configure your LLM in the example file
PYTHONPATH=. fixturebench run \
  --agent examples.playwright_agentic_agent:PlaywrightAgenticAgent \
  --case v1_po_1042 --headed
```

**Design rule:** the LLM chooses intent; Playwright executes. FixtureBench scores the structured PO `payload` against golden fixtures.

Also shipped: [`examples/playwright_smoke_agent.py`](examples/playwright_smoke_agent.py) — no LLM, good for CI smoke.

---

## What FixtureBench handles for you

| Concern | You | FixtureBench |
|---------|-----|--------------|
| Browser agent logic | ✅ | |
| Start / stop fake portals | | ✅ |
| Case registry & filters | | ✅ |
| Credentials & goals | | ✅ |
| Golden-fixture PO scoring | | ✅ |
| JSON reports & metrics | | ✅ |

---

## Portal catalog

25 cases across 23 self-hosted buyer portals:

| Env | Challenge |
|-----|-----------|
| **v1** | Baseline PO extraction |
| **v2** | Messy headers / labels |
| **v3** | Pagination |
| **v4** | CSV-only line items |
| **v5** | Secondary tab |
| **v6** | Collapsed accordion |
| **v7** | Session expiry |
| **v8** | Modal overlay |
| **v9** | Messy DOM / no test ids |
| **v10** | Search among decoys |
| **v11** | Iframe content |
| **v12** | Delayed JS load |
| **v13** | Empty state (graceful no-op) |
| **v14** | Lazy accordion (DOM-absent until expand) |
| **v15** | Unlabeled / ambiguous fields |
| **v16** | Nested Actions → Export menu |
| **v17** | Near-duplicate decoy POs |
| **v18** | Anti-bot interstitial |
| **v19** | Acknowledge before reveal |
| **v20** | MFA / OTP handoff |
| **v21** | Virtualized order grid (scroll to mount) |
| **v22** | Multi-buyer PO ambiguity |
| **v23** | Stale cached detail until refresh |

Hard band (`--tags hard`): v14–v23.

Published baselines: [docs/scores.md](docs/scores.md).

Full matrix: [docs/catalog.md](docs/catalog.md). Add a portal variant: [docs/extending.md](docs/extending.md).

---

## Why this exists

Generic browser-agent benchmarks (WebArena, Mind2Web, BrowserGym, …) cover consumer and open-web tasks. Procurement agents fail on a different surface: enterprise supplier portals with ugly tables, exports, sessions, and acknowledgements.

FixtureBench is a **CI-grade regression suite for that niche**:

- **Deterministic** — fake portals, fixed data, same expected PO every run
- **Workflow-shaped** — login → navigate → extract / act on purchase orders
- **Programmatic scoring** — golden fixtures, not LLM-as-judge
- **Agent-agnostic** — one adapter method; bring Playwright, Stagehand, your stack

Started as an internal eval layer for a procurement browser-agent product.

---

## Project structure

```
fixturebench/
├── eval/cases.json          # PO extraction / empty-state cases
├── portals/                 # Fake buyer portals (v1–v23)
├── examples/
│   ├── playwright_smoke_agent.py
│   └── playwright_agentic_agent.py
├── src/fixturebench/
│   ├── cli.py
│   ├── api.py
│   ├── adapters/
│   └── eval/
└── docs/
```

---

## Status

**v0.7** — portal catalog complete (v1–v23), write-back scoring, CI smoke, Scruffy dogfood.

### Published scores

| Agent | Band | Score |
|-------|------|-------|
| `playwright-smoke` | smoke | **4/4** |
| `scruffy-deterministic` | smoke | **4/4** |

Details + reproduce steps: [docs/scores.md](docs/scores.md).

Roadmap (stays in procurement):

- [x] Write-back scoring (acknowledge → assert server state)
- [x] Virtualized order grid
- [x] Stale cache / multi-buyer PO ambiguity
- [x] GitHub Action for CI eval
- [x] Scruffy CI dogfood + published scores
- [ ] More write-backs (qty change / ASN)
- [ ] Publish stable agentic hard-band scores (Ollama)

---

## License

MIT
