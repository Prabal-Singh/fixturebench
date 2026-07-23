# FixtureBench

**Plug-and-play eval for browser agents.**

Drop in your agent. FixtureBench starts the environments, runs the cases, scores structured output against golden fixtures, and writes a report.

```
pip install -e ".[envs]"
fixturebench run --agent my_agent:MyAgent --tag smoke
```

No live websites. No LLM judges. No framework lock-in.

---

## Plug and play in 3 steps

### 1. Install

```bash
git clone https://github.com/Prabal-Singh/fixturebench.git
cd fixturebench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[envs,dev]"
```

### 2. Implement one method

```python
# my_agent.py
from fixturebench import AgentRunResult, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        # task.url        — environment URL (already running)
        # task.goal       — natural-language instruction
        # task.target_id  — record to find (e.g. PO-1042)
        # task.email / task.password / task.max_steps / task.headless
        ...
        return AgentRunResult(success=True, payload=extracted_record, step_count=7)
```

That's the whole contract: **`name` + `run(task)`**.

### 3. Run

```bash
# list cases
fixturebench list

# run smoke suite
fixturebench run --agent my_agent:MyAgent --tag smoke

# one case, headed browser
fixturebench run --agent my_agent:MyAgent --case v1_po_1042 --headed
```

Or from Python:

```python
from fixturebench import run
from my_agent import MyAgent

report = run(MyAgent(), tags=["smoke"])
print(report.summary.passed, "/", report.summary.total)
```

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

Swap Skyvern, Browser Use, Playwright+LLM, or a hand-rolled loop — same cases, same scores.

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
├── eval/cases.json          # Case registry
├── portals/                 # First env pack (structured extraction)
├── tests/fixtures/          # Golden outputs
├── src/fixturebench/
│   ├── cli.py               # `fixturebench` command
│   ├── api.py               # run(agent)
│   ├── adapters/            # BrowserAgent protocol
│   ├── agents/              # Built-in StubAgent
│   └── eval/                # Harness + scorer
└── docs/
```

---

## Status

**v0.3 — plug-and-play.** CLI, `run(agent)` API, packaged environments, generic `payload` / `url` / `target_id` aliases.

Roadmap:

- [ ] Reference Playwright agent adapter
- [ ] Second environment pack
- [ ] Write-back / state-mutation scoring
- [ ] GitHub Action for CI eval

---

## License

MIT
