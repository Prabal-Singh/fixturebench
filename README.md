# FixtureBench

**Deterministic eval environments for browser agents.**

Browser agents are shipping into production, but most teams still can't answer a basic question: *did my agent get better or worse?*

Live websites flake. Leaderboards use LLM judges that swing 20% on grader choice. Demos work on toy pages; production breaks on pagination, renamed columns, session expiry, and ambiguous UI.

FixtureBench is the missing middle layer:

```
Self-hosted environment  →  Your agent  →  Structured output  →  Golden fixture diff
```

Deterministic. Programmatic scoring. Agent-agnostic. CI-friendly.

---

## What it is

A **harness + environment packs** for evaluating any browser agent on structured web tasks:

| Layer | Role |
|-------|------|
| **Environments** | Self-hosted fake sites with graded failure modes |
| **Cases** | Declarative tasks (`eval/cases.json`) |
| **Harness** | Starts envs, runs cases, writes JSON reports |
| **Scorer** | Diffs agent output against golden fixtures |
| **Adapter** | Thin `BrowserAgent` protocol — plug in any agent |

The first shipped pack is **structured extraction** (fake buyer portals: login → navigate → extract records). That pack is an *example domain*, not the product. Bring your own sites, tasks, and fixtures for CRM, admin panels, dashboards, or anything else your agent has to operate.

---

## First environment pack: structured extraction

13 self-hosted sites, 15 cases. Same failure modes agents hit on real enterprise UIs — without live credentials or flaky third-party sites.

| Env | Challenge |
|-----|-----------|
| **v1** | Clean tables, baseline extraction |
| **v2** | Messy column headers / inconsistent labels |
| **v3** | Paginated lists — navigate before extracting |
| **v4** | Data only in CSV export |
| **v5** | Target record under a secondary tab |
| **v6** | Lines hidden in collapsed accordion |
| **v7** | Session expires mid-flow — re-login required |
| **v8** | Detail in a modal overlay |
| **v9** | Messy DOM, no stable test ids |
| **v10** | Search required among decoys |
| **v11** | Content inside an iframe |
| **v12** | Delayed JavaScript load |
| **v13** | Empty state — graceful no-op |

Full matrix: [docs/catalog.md](docs/catalog.md). How to add another pack: [docs/extending.md](docs/extending.md).

---

## Quick start

```bash
git clone https://github.com/Prabal-Singh/fixturebench.git
cd fixturebench
python -m venv .venv && source .venv/bin/activate
pip install -e ".[portal,dev]"

# Run unit tests (no agent required)
pytest

# List eval cases
python scripts/run_eval.py --list

# Run eval against your agent adapter
python scripts/run_eval.py --agent your_module:YourAgent
```

### Implement an agent adapter

```python
from fixturebench.adapters import AgentRunResult, BrowserAgent, EvalTask

class YourAgent:
    @property
    def name(self) -> str:
        return "your-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        # task.portal_url, task.goal, task.max_steps, ...
        return AgentRunResult(success=True, po=extracted_record, step_count=7)
```

See [`examples/stub_agent.py`](examples/stub_agent.py) for a minimal placeholder.

---

## Why this exists

Research benchmarks (WebArena, REAL, LexBench) optimize for leaderboard comparisons on consumer web tasks.

Teams shipping browser agents need something different:

- **Deterministic** — same input, same expected output, every CI run
- **Workflow-shaped** — login → navigate → extract / act on structured data
- **Programmatic scoring** — golden fixtures, not LLM-as-judge
- **Agent-agnostic** — compare frameworks and in-house loops on the same cases
- **Extensible** — environment packs are swappable; the harness stays shared

Started as an internal eval layer for a browser-agent product, then generalized into a standalone library.

---

## Project structure

```
fixturebench/
├── eval/cases.json              # Case registry (current pack)
├── portals/                     # First env pack: structured extraction
├── tests/fixtures/              # Golden expected outputs
├── docs/
│   ├── catalog.md               # Pack matrix
│   └── extending.md             # Add your own environments
├── src/fixturebench/
│   ├── adapters/                # BrowserAgent protocol
│   └── eval/                    # Harness, scorer, reports
└── scripts/run_eval.py          # CLI
```

---

## Status

**v0.2 — first environment pack.** Structured-extraction suite is complete; agent adapters are bring-your-own.

Roadmap:

- [ ] Reference Playwright agent adapter
- [ ] Generic result payload (less pack-specific schema on the adapter)
- [ ] Second environment pack (non-procurement structured UI)
- [ ] Write-back / state-mutation scoring cases
- [ ] GitHub Action for CI eval

---

## License

MIT
