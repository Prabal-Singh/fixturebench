# Fake buyer portals

Self-hosted Coupa-style supplier portals for procurement browser-agent eval.

See the full **[catalog](../docs/catalog.md)** and **[how to add a portal](../docs/extending.md)**.

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
| v14 | Lazy accordion (DOM-absent) | 8013 |
| v15 | Unlabeled fields | 8014 |
| v16 | Nested Actions → Export | 8015 |
| v17 | Decoy / near-duplicate rows | 8016 |
| v18 | Anti-bot interstitial | 8017 |
| v19 | Acknowledge to reveal | 8018 |
| v20 | MFA / OTP handoff | 8019 |
| v21 | Virtualized order grid | 8020 |
| v22 | Multi-buyer PO ambiguity | 8021 |
| v23 | Stale cached detail | 8022 |

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
