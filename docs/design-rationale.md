# Design rationale

FixtureBench is a **procurement-portal eval suite** for browser agents: self-hosted fake buyer/supplier portals, declarative cases, and programmatic scoring of purchase-order extraction against golden fixtures.

It is **not** a general-purpose web-agent benchmark. Those already exist (WebArena, Mind2Web, BrowserGym, and similar). FixtureBench targets the failure modes of **enterprise procurement UIs** — the kind of Coupa / Ariba / custom vendor portals that production procurement agents actually hit.

## Philosophy: benchmarks before solvers

The repo is intentionally **evaluation-first**. We define deterministic portals, golden PO fixtures, and scoring *before* shipping strong reference agents. That keeps scores honest and gives agent builders a shared regression target in this niche.

## Scoring philosophy

FixtureBench scores **structured PO outputs** against golden fixtures — not LLM judges.

An agent passes when:

1. It reports task success (`AgentRunResult.success`)
2. For `extract_po` cases: extracted fields match the expected fixture field-for-field
3. For `confirm_empty` cases: agent succeeds without inventing a PO

This keeps eval deterministic and CI-friendly. Write-back outcomes (`acknowledge_po`) also assert **portal server state** via a harness-only eval API — not only the JSON the agent returns.

## Agent adapter

Any browser agent can plug in by implementing `BrowserAgent` — the harness is agent-agnostic; the **task domain** is procurement:

```python
from fixturebench.adapters import AgentRunResult, BrowserAgent, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        ...
```

The harness handles portal lifecycle, case selection, reporting, and scoring.

## Origins

Started as an internal eval layer for a procurement browser-agent product, then opened as a standalone suite so others building the same class of agent can regression-test without live buyer portals.
