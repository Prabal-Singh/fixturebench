# Environment pack catalog — structured extraction

First FixtureBench pack: **13 deterministic fake sites** and **15 eval cases** covering failure modes browser agents hit on enterprise UIs (login → navigate → extract structured records).

This pack happens to use buyer-portal / PO-shaped data. Treat it as a structured-extraction stress suite, not a procurement-only product.

## Environment matrix

| Env | Port | Challenge | What breaks naive agents |
|-----|------|-----------|--------------------------|
| **v1** | 8000 | Baseline | Reference happy path |
| **v2** | 8001 | Messy headers | Semantic column mapping (`PO #`, `Unit` vs `UOM`) |
| **v3** | 8002 | Pagination | Target record on page 2 |
| **v4** | 8003 | CSV export | Lines only in downloadable CSV |
| **v5** | 8004 | Tab navigation | Target hidden under a secondary tab |
| **v6** | 8005 | Accordion | Lines collapsed in `<details>` |
| **v7** | 8006 | Session expiry | Session dies before detail — must re-login |
| **v8** | 8007 | Modal detail | Detail opens in overlay, not new page |
| **v9** | 8008 | Messy DOM | No `data-testid`, div-grid layout |
| **v10** | 8009 | Search filter | 40+ decoys; search required |
| **v11** | 8010 | Iframe detail | Content inside embedded frame |
| **v12** | 8011 | Delayed load | Lines appear after JS fetch (~1.5s) |
| **v13** | 8012 | Empty state | No records — agent must finish gracefully |

## Case registry

| Case ID | Env | Outcome | Tags |
|---------|-----|---------|------|
| `v1_po_1042` | v1 | extract | smoke, baseline |
| `v1_po_1041` | v1 | extract | single-line |
| `v2_po_1042` | v2 | extract | messy-headers |
| `v3_po_1042` | v3 | extract | pagination (page 2) |
| `v3_po_1039` | v3 | extract | pagination (page 3) |
| `v4_po_1042_csv` | v4 | extract | csv-export |
| `v5_po_1042_tabs` | v5 | extract | tab-navigation |
| `v6_po_1042_accordion` | v6 | extract | accordion |
| `v7_po_1042_session` | v7 | extract | session-expiry |
| `v8_po_1042_modal` | v8 | extract | modal |
| `v9_po_1042_messy_dom` | v9 | extract | messy-dom |
| `v10_po_1042_search` | v10 | extract | search |
| `v11_po_1042_iframe` | v11 | extract | iframe |
| `v12_po_1042_delayed` | v12 | extract | delayed-load |
| `v13_empty_orders` | v13 | **confirm_empty** | empty-state |

## Credentials (this pack)

| Field | Value |
|-------|-------|
| Email | `vendor@fixturebench.test` |
| Password | `fixturebench123` |

## Scoring outcomes

### `extract_po` (default)

Pass when the agent reports success **and** extracted fields match the golden fixture.

### `confirm_empty`

Pass when the agent reports success **and** returns no payload (`po is None`). Used for empty-state envs where the correct behavior is a graceful no-op.

## Planned pack additions

- Write-back / acknowledge cases (state mutation scoring)
- MFA handoff screen (human-in-the-loop stub)
- Nested **Actions → Export** menu
- Duplicate/decoy rows in tables
- Anti-bot interstitial page
- Second pack outside structured-extraction (see [extending.md](extending.md))
