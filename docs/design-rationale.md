# Design rationale

FixtureBench portals encode real browser-agent failure modes observed in B2B procurement workflows — without requiring live Coupa/Ariba credentials.

## Why three variants?

| Portal | What it tests | Real-world analog |
|--------|---------------|-------------------|
| **v1** | Clean tables, stable selectors | Happy-path portal scrape |
| **v2** | Messy headers, inconsistent UOM labels | Buyer terminology drift |
| **v3** | Paginated order lists | Navigation before extraction |

## Scoring philosophy

FixtureBench scores **structured outputs** against golden fixtures — not LLM judges.

An agent passes when:

1. It reports task success (`AgentRunResult.success`)
2. Extracted data matches the expected PO fixture field-for-field

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

## Origins

Extracted from [Scruffy](https://github.com/Prabal-Singh/Scruffy) — agentic automation for B2B order ingestion — and generalized into an agent-agnostic eval library.
