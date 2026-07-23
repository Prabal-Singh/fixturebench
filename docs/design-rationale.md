# Design rationale

FixtureBench portals encode real browser-agent failure modes observed in B2B procurement workflows — without requiring live Coupa/Ariba credentials.

## Philosophy: benchmarks before solvers

The repo is intentionally **evaluation-first**. We define deterministic environments, golden fixtures, and programmatic scoring *before* shipping reference agents. That keeps scores honest and gives agent builders a shared target.

## Scoring philosophy

FixtureBench scores **structured outputs** against golden fixtures — not LLM judges.

An agent passes when:

1. It reports task success (`AgentRunResult.success`)
2. For `extract_po` cases: extracted data matches the expected PO fixture field-for-field
3. For `confirm_empty` cases: agent succeeds without inventing PO data

This keeps eval deterministic and CI-friendly.

## Agent adapter

Any browser agent can plug in by implementing `BrowserAgent`:

```python
from fixturebench.adapters import AgentRunResult, BrowserAgent, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        ...
```

The harness handles portal lifecycle, case selection, reporting, and programmatic scoring.

See [catalog.md](catalog.md) for the full portal and case matrix.

## Origins

Extracted from [Scruffy](https://github.com/Prabal-Singh/Scruffy) — agentic automation for B2B order ingestion — and generalized into an agent-agnostic eval library.
