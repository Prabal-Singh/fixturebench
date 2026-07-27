# Published scores

Baseline FixtureBench results. Re-run locally and update this table when scores change.

| Agent | Band | Score | Date | Where |
|-------|------|-------|------|-------|
| `playwright-smoke` | `smoke` | **4/4** | 2026-07-24 | FixtureBench CI / demo agent |
| `scruffy-deterministic` | `smoke` | **4/4** | 2026-07-24 | [Scruffy](https://github.com/Prabal-Singh/Scruffy) CI dogfood |
| `scruffy-agentic` (`qwen2.5:14b`) | `hard` | **4/10** | 2026-07-26 | local Ollama (`qwen2.5:14b`) |
| `playwright-agentic` (`llama-3.3-70b-versatile`) | `hard` | **7/9 attempted** | 2026-07-27 | Groq free tier (1 case, v21, never completed — daily token quota) |

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

## Hard-band breakdown (`playwright-agentic`, `llama-3.3-70b-versatile`, 2026-07-27)

| Case | Result | Failure mode |
|------|--------|--------------|
| `v14_po_1042_lazy_accordion` | **PASS** | |
| `v15_po_1042_unlabeled` | **PASS** | |
| `v16_po_1042_nested_menu` | FAIL | Extracted 0/3 lines (missed CSV export step) |
| `v17_po_1042_decoys` | **PASS** | |
| `v18_po_1042_interstitial` | **PASS** | |
| `v19_po_1042_acknowledge` | **PASS** | |
| `v20_po_1042_mfa` | **PASS** | |
| `v21_po_1042_virtualized` | not completed | Groq daily token quota exhausted mid-run. Notably, before hitting the quota wall it was stuck repeating `press` on the same virtualized-grid selector for 12+ steps — the same "stuck scrolling, can't tell when to stop" failure shape `qwen2.5:14b` hit on this exact case. Same failure, different model size — points at a sequencing/feedback gap, not a raw capability gap. |
| `v22_po_1042_multibuyer` | FAIL | Oscillated `po-link-PO-1042` ↔ `nav-orders` for 15 steps, stuck on the `ord-pacific-1042` decoy the whole time — the identical "opened Pacific decoy, then oscillated" failure `qwen2.5:14b` hit on this exact case |
| `v23_po_1042_stale_cache` | **PASS** | |

Two of the three hard cases either model got stuck on (`v21`, `v22`) produced the **same failure shape** in both the 14B local model and the 70B cloud model — a decoy-disambiguation loop and a can't-tell-when-to-stop-scrolling loop. Different model sizes, identical failure pattern. That's the actual finding: these aren't capability failures, they're missing feedback/sequencing signals that no amount of raw model strength fixes on its own.

## How to reproduce

### FixtureBench demo agent

```bash
pip install -e ".[envs,playwright]"
playwright install chromium
PYTHONPATH=. fixturebench run \
  --agent examples.playwright_smoke_agent:PlaywrightSmokeAgent \
  --tag smoke
```

### FixtureBench agentic example (any OpenAI-compatible model)

```bash
pip install -e ".[envs,playwright]"
playwright install chromium
export OPENAI_API_KEY=...
export OPENAI_BASE_URL=...   # e.g. https://api.groq.com/openai/v1
export OPENAI_MODEL=...      # e.g. llama-3.3-70b-versatile
PYTHONPATH=. fixturebench run \
  --agent examples.playwright_agentic_agent:PlaywrightAgenticAgent \
  --tag hard
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
- `examples/playwright_agentic_agent.py` retries on HTTP 429 with backoff and sends a real `User-Agent` (some providers, e.g. Groq, block the default urllib UA via Cloudflare). Free-tier daily/per-minute token quotas still apply and can block long-running hard-band cases — that's a provider limit, not an agent failure.
