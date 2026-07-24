# Portal catalog — buyer / supplier workflows

**20 deterministic fake buyer portals** and **22 eval cases** covering failure modes procurement browser agents hit (login → find PO → extract / act).

This is a **procurement-portal stress suite**, not a general web-agent benchmark.

## Environment matrix

| Env | Port | Challenge | What breaks naive agents |
|-----|------|-----------|--------------------------|
| **v1** | 8000 | Baseline | Reference happy path |
| **v2** | 8001 | Messy headers | Semantic column mapping (`PO #`, `Unit` vs `UOM`) |
| **v3** | 8002 | Pagination | Target record on page 2 |
| **v4** | 8003 | CSV export | Lines only in downloadable CSV |
| **v5** | 8004 | Tab navigation | Target hidden under a secondary tab |
| **v6** | 8005 | Accordion | Lines collapsed in `<details>` (still in DOM) |
| **v7** | 8006 | Session expiry | Session dies before detail — must re-login |
| **v8** | 8007 | Modal detail | Detail opens in overlay, not new page |
| **v9** | 8008 | Messy DOM | No `data-testid`, div-grid layout |
| **v10** | 8009 | Search filter | 40+ decoys; search required |
| **v11** | 8010 | Iframe detail | Content inside embedded frame |
| **v12** | 8011 | Delayed load | Lines appear after JS fetch (~1.5s) |
| **v13** | 8012 | Empty state | No records — agent must finish gracefully |
| **v14** | 8013 | Lazy accordion | Lines **absent from DOM** until expand + fetch |
| **v15** | 8014 | Unlabeled fields | No labels / testids; ambiguous date vs due date |
| **v16** | 8015 | Nested export menu | Actions → More → Export CSV |
| **v17** | 8016 | Decoy rows | Near-duplicate PO numbers; must pick exact Open |
| **v18** | 8017 | Anti-bot interstitial | Human check gate after login |
| **v19** | 8018 | Acknowledge write-back | Must mutate portal state; harness asserts `/api/eval/...` |
| **v20** | 8019 | MFA handoff | OTP step after password (`424242`) |

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
| `v14_po_1042_lazy_accordion` | v14 | extract | **hard**, lazy-accordion |
| `v15_po_1042_unlabeled` | v15 | extract | **hard**, unlabeled-fields |
| `v16_po_1042_nested_menu` | v16 | extract | **hard**, nested-menu |
| `v17_po_1042_decoys` | v17 | extract | **hard**, decoy-rows |
| `v18_po_1042_interstitial` | v18 | extract | **hard**, antibot |
| `v19_po_1042_acknowledge` | v19 | **acknowledge_po** | **hard**, write-back |
| `v20_po_1042_mfa` | v20 | extract | **hard**, mfa |

## Credentials (this pack)

| Field | Value |
|-------|-------|
| Email | `vendor@fixturebench.test` |
| Password | `fixturebench123` |
| MFA OTP (v20 only) | `424242` |

## Difficulty bands

| Band | Cases | Intent |
|------|-------|--------|
| Smoke | `smoke` tag | Fast CI sanity |
| Core | v1–v13 | Common UI patterns |
| Hard | `hard` tag (v14–v20) | Realistic traps from agent failures |

Run hard cases only:

```bash
fixturebench run --agent examples.playwright_agentic_agent:PlaywrightAgenticAgent --tags hard
```

## Scoring outcomes

### `extract_po` (default)

Pass when the agent reports success **and** extracted fields match the golden fixture.

### `confirm_empty`

Pass when the agent reports success **and** returns no payload (`po is None`). Used for empty-state envs where the correct behavior is a graceful no-op.

### `acknowledge_po` (write-back)

Pass when **all** of the following hold:

1. Agent reports success
2. Extracted PO matches the golden fixture
3. Portal **server state** matches `expected_state` (harness reads `GET /api/eval/orders/{po}`)

Used by `v19_po_1042_acknowledge`. Extracting lines without clicking Acknowledge fails — the portal stays `Open` / `acknowledged: false`.

## Planned additions (same domain)

- More write-backs (quantity change, ASN submit) with server-state asserts
- Virtualized order grids; stale cache; multi-buyer PO ambiguity
- Captcha-style timing gate (wait N seconds)
