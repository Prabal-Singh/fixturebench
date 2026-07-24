# Extending FixtureBench

FixtureBench is a **buyer-portal / PO workflow** eval suite. Extend it by adding more portal variants and cases in that domain — not by turning it into a generic web benchmark.

## Plug in an agent (30 seconds)

```python
from fixturebench import run, AgentRunResult, EvalTask

class MyAgent:
    @property
    def name(self) -> str:
        return "my-agent"

    def run(self, task: EvalTask) -> AgentRunResult:
        # task.url, task.goal, task.target_id (PO number), task.email, task.password
        return AgentRunResult(success=True, payload=extracted_po)

report = run(MyAgent(), tags=["smoke"])
```

Or CLI: `fixturebench run --agent my_agent:MyAgent --tag smoke`

## Adding a portal variant

1. **Portal** — copy an existing `portals/vN/` and change one primary challenge
2. **Golden fixture** — expected PO JSON under `tests/fixtures/` (reuse when data matches)
3. **Case** — entry in `eval/cases.json` with tags (`smoke` / `hard` / challenge name)
4. **Registry** — add the version to `PortalVersion` and `PORTAL_SPECS`
5. **Invariant test** — lock the challenge (e.g. decoys precede the real PO)

## Minimal case shape

```json
{
  "id": "v21_po_1042_example",
  "portal": "v21",
  "po_number": "PO-1042",
  "expected_fixture": "tests/fixtures/expected_po_1042.json",
  "tags": ["hard", "your-challenge"]
}
```

Adapter aliases (still procurement-shaped):

- `task.url` / `task.portal_url`
- `task.target_id` / `task.po_number`
- `AgentRunResult(payload=...)` / `po=...`

## Design rules for good portals

- **Deterministic** — no live third-party buyer sites
- **One primary failure mode per env**
- **Programmatic expected state** — fixtures (and later server-state asserts), not LLM judges
- **Realistic but small** — CI-friendly
- **Stay in domain** — POs, line items, acknowledgements, sessions, exports — not “book a flight”

## Good next challenges (same domain)

- More write-backs: quantity change / ASN submit → assert portal state (see `acknowledge_po`)
- Virtualized order grids (must scroll to mount rows)
- Stale cached detail until hard refresh
- Two Open POs with the same number under different buyers

### Write-back cases

Set `"outcome": "acknowledge_po"` plus:

- `expected_fixture` — PO JSON after lines unlock
- `expected_state` — portal server snapshot, e.g. `{"po_number":"PO-1042","acknowledged":true,"status":"Acknowledged"}`

Expose harness-only `GET /api/eval/orders/{po_number}` on the portal so scoring does not depend on the agent's cookies.

## Contributing

Open a PR with:

1. Self-hosted portal + catalog row
2. At least one golden fixture + one case
3. A regression test locking the challenge invariant
