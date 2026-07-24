# Published scores

Baseline FixtureBench results. Re-run locally and update this table when scores change.

| Agent | Band | Score | Date | Where |
|-------|------|-------|------|-------|
| `playwright-smoke` | `smoke` | **4/4** | 2026-07-24 | FixtureBench CI / demo agent |
| `scruffy-deterministic` | `smoke` | **4/4** | 2026-07-24 | [Scruffy](https://github.com/Prabal-Singh/Scruffy) CI dogfood |
| `scruffy-agentic` (Ollama) | `hard` | *not published* | — | Requires local Ollama; not run in GitHub Actions |

## How to reproduce

### FixtureBench demo agent

```bash
pip install -e ".[envs,playwright]"
playwright install chromium
PYTHONPATH=. fixturebench run \
  --agent examples.playwright_smoke_agent:PlaywrightSmokeAgent \
  --tag smoke
```

### Scruffy dogfood

From the Scruffy repo:

```bash
pip install -e ".[portal,dev,fixturebench]"
playwright install chromium
PYTHONPATH=src:. fixturebench run \
  --agent scruffy.fixturebench_agent:ScruffyDeterministicAgent \
  --tag smoke
```

Agentic (needs Ollama):

```bash
PYTHONPATH=src:. fixturebench run \
  --agent scruffy.fixturebench_agent:ScruffyAgenticAdapter \
  --tag hard
```

## Notes

- Smoke band today: `v1_po_1042`, `v2_po_1042`, `v3_po_1042`, `v13_empty_orders`
- Hard band (`v14`–`v23`) is intentionally tougher; publish agentic hard scores once a stable Ollama/CI path exists
- FixtureBench discovers its own data root even when run from Scruffy (see `FIXTUREBENCH_ROOT` override if needed)
