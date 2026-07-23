# Design rationale

FixtureBench is a **generic eval harness** for browser agents: self-hosted environments, declarative cases, and programmatic scoring against golden fixtures.

The buyer-portal suite under `portals/` is the first **environment pack** — a concrete structured-extraction domain that stresses real UI failure modes (pagination, messy headers, session expiry, iframes, delayed loads). It is not the product boundary.

## Philosophy: benchmarks before solvers

The repo is intentionally **evaluation-first**. We define deterministic environments, golden fixtures, and scoring *before* shipping reference agents. That keeps scores honest and gives agent builders a shared target.

## Scoring philosophy

FixtureBench scores **structured outputs** against golden fixtures — not LLM judges.

For the current pack, an agent passes when:

1. It reports task success (`AgentRunResult.success`)
2. For `extract_po` cases: extracted data matches the expected fixture field-for-field
3. For `confirm_empty` cases: agent succeeds without inventing data

This keeps eval deterministic and CI-friendly. Other packs can plug in their own schemas and scorers — see [extending.md](extending.md).

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

The harness handles environment lifecycle, case selection, reporting, and scoring.

## Origins

Started as an internal eval layer for a browser-agent product, then generalized into an agent-agnostic library.
