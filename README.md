# FixtureBench

**Plug-and-play eval for browser agents.**

Drop in your agent. FixtureBench starts the environments, runs the cases, scores structured output against golden fixtures, and writes a report.

No live websites. No LLM judges. No framework lock-in.

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

### Plug in your own agent

Implement **one method**. FixtureBench handles the rest.

```python
# my_agent.py
from fixturebench import AgentRunResult, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        # task.url        — environment already running
        # task.goal       — natural-language instruction
        # task.target_id  — record to find (e.g. PO-1042)
        # task.email / task.password / task.max_steps / task.headless
        ...
        return AgentRunResult(success=True, payload=extracted_record, step_count=7)
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

Deterministic scripts solve the easy cases. Real agents need an **observe → reason → act** loop. Here's the shape — full file: [`examples/playwright_agentic_agent.py`](examples/playwright_agentic_agent.py).

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
                # 1. OBSERVE — cheap page snapshot for the model
                observation = {
                    "url": page.url,
                    "title": page.title(),
                    "text": page.inner_text("body")[:4000],
                    "links": [
                        {"text": a.inner_text()[:80], "href": a.get_attribute("href")}
                        for a in page.locator("a").all()[:40]
                    ],
                }

                # 2. REASON — LLM picks the next action
                action = complete_json(
                    system="You drive a browser. Reply with JSON only.",
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
                            "payload": "on finish: extracted record dict",
                            "reason": "short",
                        },
                    },
                )

                # 3. ACT — Playwright executes precisely
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

**Design rule:** the LLM chooses intent; Playwright executes. FixtureBench scores the structured `payload` against golden fixtures — not the LLM's prose.

Also shipped: [`examples/playwright_smoke_agent.py`](examples/playwright_smoke_agent.py) — no LLM, good for CI smoke.

---

## What FixtureBench handles for you

| Concern | You | FixtureBench |
|---------|-----|--------------|
| Browser agent logic | ✅ | |
| Start / stop environments | | ✅ |
| Case registry & filters | | ✅ |
| Credentials & goals | | ✅ |
| Golden-fixture scoring | | ✅ |
| JSON reports & metrics | | ✅ |

---

## Bundled environment pack

15 cases across 13 self-hosted sites covering real agent failure modes:

| Env | Challenge |
|-----|-----------|
| **v1** | Baseline extraction |
| **v2** | Messy headers / labels |
| **v3** | Pagination |
| **v4** | CSV-only data |
| **v5** | Secondary tab |
| **v6** | Collapsed accordion |
| **v7** | Session expiry |
| **v8** | Modal overlay |
| **v9** | Messy DOM / no test ids |
| **v10** | Search among decoys |
| **v11** | Iframe content |
| **v12** | Delayed JS load |
| **v13** | Empty state (graceful no-op) |

Full matrix: [docs/catalog.md](docs/catalog.md). Add your own pack: [docs/extending.md](docs/extending.md).

---

## Why this exists

Research benchmarks optimize for leaderboards on consumer web tasks. Production agent teams need CI-grade regression:

- **Deterministic** — same input → same expected output
- **Workflow-shaped** — login → navigate → extract / act
- **Programmatic scoring** — fixtures, not LLM-as-judge
- **Agent-agnostic** — one adapter method, any stack

Started as an internal eval layer, generalized into a standalone harness.

---

## Project structure

```
fixturebench/
├── eval/cases.json
├── portals/                 # First env pack
├── examples/
│   ├── playwright_smoke_agent.py      # deterministic demo
│   └── playwright_agentic_agent.py    # LLM + Playwright loop
├── src/fixturebench/
│   ├── cli.py               # `fixturebench` command
│   ├── api.py               # run(agent)
│   ├── adapters/
│   └── eval/
└── docs/
```

---

## Status

**v0.3 — plug-and-play.** CLI, `run(agent)` API, smoke + agentic Playwright examples.

Roadmap:

- [ ] Second environment pack
- [ ] Write-back / state-mutation scoring
- [ ] GitHub Action for CI eval

---

## License

MIT
