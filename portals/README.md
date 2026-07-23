# Fake Buyer Portals

Deterministic Coupa-style supplier portals for browser agent evaluation.

These environments are self-hosted, reproducible, and designed to stress common failure modes without hitting live websites.

## Credentials

| Field | Value |
|-------|-------|
| Email | `vendor@fixturebench.test` |
| Password | `fixturebench123` |

## v1 — Midwest Foods Vendor Portal

Clean Coupa-style layout. Baseline extraction case.

```bash
pip install -e ".[portal]"
python portals/v1/server.py
# → http://127.0.0.1:8000
```

## v2 — Pacific Retail Supplier Portal

Same layout and `data-testid`s as v1, but **messy column headers** and **inconsistent UOM labels** (`CASE`, `each`, `EA`).

```bash
python portals/v2/server.py
# → http://127.0.0.1:8001
```

## v3 — National Grocers Alliance (NGA)

Clean headers like v1, but the **orders list is paginated** (2 POs per page). PO-1042 is on page 2.

```bash
python portals/v3/server.py
# → http://127.0.0.1:8002
```

Pagination controls use `data-testid="orders-next"`, `orders-prev`, and `orders-page-info`.

## Test data

| Buyer description | Buyer code | Supplier SKU (not shown on portal) |
|-------------------|------------|-------------------------------------|
| Sweet-Disk | SWT-DSK | Choc-1 |
| Crunch-Bar | CRN-BAR | SNK-42 |
| Fizz-Pop | FIZ-POP | BEV-7 |

See [docs/design-rationale.md](docs/design-rationale.md) for why these variants exist.
