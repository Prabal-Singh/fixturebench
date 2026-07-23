# FixtureBench

**Deterministic eval environments for browser agents.**

Browser agents are shipping into production, but most teams still can't answer a basic question: *did my agent get better or worse?*

Live websites flake. Benchmarks use LLM judges that swing 20% on grader choice. Demos work on toy pages; production breaks on pagination, renamed columns, and ambiguous UI.

FixtureBench is the missing middle layer:

```
Fake portal (controlled)  →  Your agent  →  Structured output  →  Golden fixture diff
```

Self-hosted. Programmatic scoring. Agent-agnostic.

---

## What's included

| Layer | What it is |
|-------|------------|
| **Environments** | 3 Coupa-style fake buyer portals with increasing difficulty |
| **Cases** | Declarative eval registry (`eval/cases.json`) |
| **Harness** | Starts portals, runs cases, writes JSON reports |
| **Scorer** | Field-level PO comparison against golden fixtures |
| **Adapter** | Thin `BrowserAgent` protocol — plug in any agent |

### Portal difficulty curve

| Portal | Challenge |
|--------|-----------|
| **v1** | Clean tables, baseline extraction |
| **v2** | Messy column headers, inconsistent UOM labels |
| **v3** | Paginated order list — must navigate before extracting |

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
        # task.portal_url, task.goal, task.po_number, task.max_steps, ...
        return AgentRunResult(success=True, po=extracted_po, step_count=7)
```

See [`examples/stub_agent.py`](examples/stub_agent.py) for a minimal placeholder.

---

## Why this exists

Research benchmarks (WebArena, REAL, LexBench) optimize for leaderboard comparisons on consumer web tasks.

Production teams need something different:

- **Deterministic** — same input, same expected output, every CI run
- **Workflow-shaped** — login → navigate → extract structured data
- **Programmatic scoring** — golden fixtures, not LLM-as-judge
- **Agent-agnostic** — compare Skyvern vs Browser Use vs your in-house loop on the same cases

FixtureBench started as the eval layer inside [Scruffy](https://github.com/Prabal-Singh/Scruffy) (B2B portal automation) and was extracted into a standalone library.

---

## Project structure

```
fixturebench/
├── eval/cases.json          # Eval case registry
├── portals/v1|v2|v3/        # Self-hosted fake buyer portals
├── tests/fixtures/          # Golden expected outputs
├── src/fixturebench/
│   ├── adapters/            # BrowserAgent protocol
│   └── eval/                # Harness, scorer, reports
└── scripts/run_eval.py      # CLI
```

---

## Status

**v0.1 — alpha.** Environments and harness are stable; agent adapters are bring-your-own.

Roadmap:

- [ ] Reference Playwright agent adapter
- [ ] Write-back / acknowledge cases (state mutation scoring)
- [ ] Session expiry and empty-state fixtures
- [ ] GitHub Action for CI eval

---

## License

MIT
