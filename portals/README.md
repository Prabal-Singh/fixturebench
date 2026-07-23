# First environment pack — structured extraction

Self-hosted fake sites for browser-agent eval. Lives under `portals/` for historical reasons; conceptually this is FixtureBench's first **environment pack**.

See the full **[pack catalog](../docs/catalog.md)** and **[how to add packs](../docs/extending.md)**.

## Quick reference

| Env | Challenge | Default port |
|-----|-----------|--------------|
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
| v13 | Empty state | 8012 |

## Credentials (all envs in this pack)

| Field | Value |
|-------|-------|
| Email | `vendor@fixturebench.test` |
| Password | `fixturebench123` |

## Start an environment

```bash
pip install -e ".[portal]"
python portals/v4/server.py
# → http://127.0.0.1:8003
```

Each server accepts `--port` for harness-managed runs.

## Sample records (buyer jargon ≠ supplier SKU)

| Description on site | Site code | Canonical SKU (not shown) |
|---------------------|-----------|---------------------------|
| Sweet-Disk | SWT-DSK | Choc-1 |
| Crunch-Bar | CRN-BAR | SNK-42 |
| Fizz-Pop | FIZ-POP | BEV-7 |
