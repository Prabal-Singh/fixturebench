# Published scores

Baseline FixtureBench results. Re-run locally and update this table when scores change.

| Agent | Band | Score | Date | Where |
|-------|------|-------|------|-------|
| `playwright-smoke` | `smoke` | **4/4** | 2026-07-24 | FixtureBench CI / demo agent |
| `scruffy-deterministic` | `smoke` | **4/4** | 2026-07-24 | [Scruffy](https://github.com/Prabal-Singh/Scruffy) CI dogfood |
| `scruffy-agentic` (`qwen2.5:14b`) | `hard` | **4/10** | 2026-07-26 | local Ollama (`qwen2.5:14b`) |

## Hard-band breakdown (`scruffy-agentic`, 2026-07-26)

Run id: `20260726T170057Z` · avg ~7 steps · ~7.2s LLM / case

| Case | Result | Failure mode |
|------|--------|--------------|
| `v14_po_1042_lazy_accordion` | FAIL | Oscillating orders ↔ detail |
| `v15_po_1042_unlabeled` | FAIL | `extract_table` before lines ready |
| `v16_po_1042_nested_menu` | FAIL | `extract_table` before CSV export |
| `v17_po_1042_decoys` | **PASS** | |
| `v18_po_1042_interstitial` | **PASS** | |
| `v19_po_1042_acknowledge` | **PASS** | |
| `v20_po_1042_mfa` | FAIL | Repeated identical `type` |
| `v21_po_1042_virtualized` | FAIL | Repeated identical `click` |
| `v22_po_1042_multibuyer` | FAIL | Opened Pacific decoy, then oscillated |
| `v23_po_1042_stale_cache` | **PASS** | |

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
pip install -e ".[portal,dev]"
pip install "fixturebench[envs,playwright] @ git+https://github.com/Prabal-Singh/fixturebench.git"
playwright install chromium
PYTHONPATH=src:. fixturebench run \
  --agent scruffy.fixturebench_agent:ScruffyDeterministicAgent \
  --tag smoke
```

Agentic hard band (needs a reachable Ollama host):

```bash
export SCRUFFY_OLLAMA_URL=http://127.0.0.1:11434   # or your Ollama host
export SCRUFFY_OLLAMA_MODEL=qwen2.5:14b
PYTHONPATH=src:. fixturebench run \
  --agent scruffy.fixturebench_agent:ScruffyAgenticAdapter \
  --tag hard
```

## Notes

- Smoke band: `v1_po_1042`, `v2_po_1042`, `v3_po_1042`, `v13_empty_orders`
- Hard band: `v14`–`v23` (10 cases)
- Agentic hard scores are **not** CI-gated (need a reachable Ollama host)
- FixtureBench discovers its own data root even when run from Scruffy (`FIXTUREBENCH_ROOT` override if needed)
