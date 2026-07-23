# Extending FixtureBench

FixtureBench separates **harness** (run cases, score, report) from **environment packs** (fake sites + fixtures + case registry).

The first pack lives in `portals/` and exercises structured extraction. Add more packs without rewriting the agent adapter protocol.

## What you need for a new pack

1. **Environment(s)** — self-hosted site(s) under something like `environments/my_pack/` (or keep using `portals/` for now)
2. **Golden fixtures** — expected structured outputs under `tests/fixtures/`
3. **Cases** — entries in a suite JSON (today: `eval/cases.json`)
4. **Scorer** — field-level compare for your schema (today: `compare_po` for the extraction pack)

## Minimal case shape

```json
{
  "id": "my_task_001",
  "portal": "v1",
  "po_number": "PO-1042",
  "expected_fixture": "tests/fixtures/expected_po_1042.json",
  "tags": ["smoke"]
}
```

Today `portal` / `po_number` naming reflects the first pack. The harness already supports:

- custom `goal` per case
- `outcome`: `extract_po` | `confirm_empty`
- tags, step budgets, managed env lifecycle

A future release will generalize field names (`environment`, `target_id`, `payload`) so packs are less procurement-shaped at the schema layer.

## Agent contract (stable)

Regardless of pack, agents implement:

```python
class BrowserAgent(Protocol):
    @property
    def name(self) -> str: ...
    def run(self, task: EvalTask) -> AgentRunResult: ...
```

`EvalTask` gives the agent a URL, goal, credentials, and step budget. Your adapter drives the browser; FixtureBench scores the structured result.

## Design rules for good environments

- **Deterministic** — no live third-party sites
- **One primary failure mode per env** — pagination *or* messy headers *or* session expiry
- **Programmatic expected state** — score against fixtures, not LLM judges
- **Realistic but small** — enough UI to break naive agents, small enough for CI

## Contributing a pack

Open a PR with:

1. Self-hosted env + README section in the pack catalog
2. At least one golden fixture + one case
3. A regression test that locks the challenge invariant (e.g. "target is on page 2")
