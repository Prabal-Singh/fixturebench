# Extending FixtureBench

FixtureBench separates **harness** (run cases, score, report) from **environment packs** (fake sites + fixtures + case registry).

The first pack lives in `portals/` and exercises structured extraction. Add more packs without rewriting the agent adapter.

## Plug in an agent (30 seconds)

```python
from fixturebench import run, AgentRunResult, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        # task.url, task.goal, task.target_id, task.email, task.password
        return AgentRunResult(success=True, payload=extracted)

report = run(MyAgent(), tags=["smoke"])
```

Or CLI: `fixturebench run --agent my_agent:MyAgent --tag smoke`

## What you need for a new pack

1. **Environment(s)** — self-hosted site(s) under `portals/` or `environments/my_pack/`
2. **Golden fixtures** — expected structured outputs under `tests/fixtures/`
3. **Cases** — entries in `eval/cases.json`
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

Today `portal` / `po_number` naming reflects the first pack. Prefer adapter aliases:

- `task.url` (not only `portal_url`)
- `task.target_id` (not only `po_number`)
- `AgentRunResult(payload=...)` (not only `po=...`)

## Design rules for good environments

- **Deterministic** — no live third-party sites
- **One primary failure mode per env**
- **Programmatic expected state** — fixtures, not LLM judges
- **Realistic but small** — CI-friendly

## Contributing a pack

Open a PR with:

1. Self-hosted env + catalog section
2. At least one golden fixture + one case
3. A regression test locking the challenge invariant
