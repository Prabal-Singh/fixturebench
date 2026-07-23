# Fake Buyer Portals

Deterministic Coupa-style supplier portals for browser agent evaluation.

See the full **[portal catalog](../docs/catalog.md)** for the challenge matrix and case registry.

## Quick reference

| Portal | Challenge | Default port |
|--------|-----------|--------------|
| v1 | Baseline | 8000 |
| v2 | Messy headers | 8001 |
| v3 | Pagination | 8002 |
| v4 | CSV export | 8003 |
| v5 | Tab navigation | 8004 |
| v6 | Accordion lines | 8005 |
| v7 | Session expiry | 8006 |
| v8 | Modal detail | 8007 |
| v9 | Messy DOM | 8008 |
| v10 | Search filter | 8009 |
| v11 | Iframe detail | 8010 |
| v12 | Delayed JS load | 8011 |
| v13 | Empty orders | 8012 |

## Credentials (all portals)

| Field | Value |
|-------|-------|
| Email | `vendor@fixturebench.test` |
| Password | `fixturebench123` |

## Start a portal

```bash
pip install -e ".[portal]"
python portals/v4/server.py
# → http://127.0.0.1:8003
```

Each server accepts `--port` for eval harness managed runs.

## Test data (buyer terminology ≠ supplier SKU)

| Buyer description | Buyer code | Supplier SKU (not shown on portal) |
|-------------------|------------|-------------------------------------|
| Sweet-Disk | SWT-DSK | Choc-1 |
| Crunch-Bar | CRN-BAR | SNK-42 |
| Fizz-Pop | FIZ-POP | BEV-7 |
