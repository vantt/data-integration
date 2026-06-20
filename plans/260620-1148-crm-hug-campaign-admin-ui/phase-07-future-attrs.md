# Phase 7 (Deferred) — Extend Targeting Attributes: order_value / scan_index / geo

## Context Links
- Attribute catalog v1: `crm/src/hug/targeting_catalog.py` (Phase 3)
- Edge matching: `webhook_receiver/cloudflareD1/src/hug-handler.ts` — `matchesTargeting`, `ScanContext`
- Design intent: `discussion-hug.md §7` — full catalog lists `order_value, scan_index, geo` as named but NOT implemented in v1

## Overview
- **Priority:** deferred (do not implement until after A2 go-live)
- **Status:** deferred
- **Goal:** Record what changes are needed across which layers so a future implementer can execute cleanly. This is a scope-fence, not an implementation plan.

## Why Deferred
These three attributes require changes at the Worker/edge layer (TypeScript + D1 schema), which are outside the scope of local CRM work and require a coordinated deploy. v1 ships only the 6 implemented attrs. No code should reference these attrs in v1 paths.

## What Each Attribute Requires

### `order_value` — order total in VND at scan time
| Layer | Change needed |
|-------|--------------|
| D1 `hug_token` | Add `order_value INTEGER` column |
| Worker `schema_hug.sql` | ALTER TABLE or recreate |
| `crm/src/hug/d1_push.py:_row_to_payload` | Include `order_value` from hug.db `hug_token` |
| `hug.db` schema (`hug/db.py`) | Add `order_value INTEGER` to `hug_token` |
| Claim station (`screen_hug_claim.py`) | Capture `order_value` from Sapo order at bind time |
| Worker `ScanContext` | Add `order_value: number \| null` |
| Worker `matchesTargeting` | Already handles range objects — no logic change, just key recognised |
| `targeting_catalog.py` | Add `order_value: {type: "range", description: "Giá trị đơn hàng (VND)"}` |

### `scan_index` — which scan number this is for the token (1st, 2nd, ...)
| Layer | Change needed |
|-------|--------------|
| D1 `hug_token` or scan log | Track `scan_count` per token; Worker reads it at scan time |
| Worker hot path `handleHugScan` | Query `SELECT COUNT(*) FROM webhooks WHERE ...` or maintain counter in `hug_token.scan_count` |
| Worker `ScanContext` | Add `scan_index: number` |
| `targeting_catalog.py` | Add `scan_index: {type: "range"}` |
| Notes | Most complex: requires atomic increment at scan time (race condition risk on concurrent scans of the same token — edge case but possible for shared QR). Durable Objects or atomic D1 transaction needed for strict accuracy. v1 approximation acceptable. |

### `geo` — geographic region at scan time
| Layer | Change needed |
|-------|--------------|
| Worker `handleHugScan` | Read `request.cf.region` or `request.cf.city` (Cloudflare provides this free) |
| Worker `ScanContext` | Add `geo: string \| null` (e.g. "Ho Chi Minh City") |
| `targeting_catalog.py` | Add `geo: {type: "list", description: "Khu vực địa lý", values: [...]}` |
| Notes | Easiest of the three — no D1 schema change needed (geo is derived at request time from CF headers, not stored). Values must be calibrated to Cloudflare's city/region naming for VN. |

## Implementation Order (when prioritised)

Recommended sequence if this phase is activated:
1. `geo` — simplest, Worker-only change, no D1 schema migration.
2. `order_value` — requires D1 schema change + claim station capture + push update.
3. `scan_index` — most complex; design atomic counter approach first.

Each sub-attribute should be a separate PR to contain blast radius.

## Scope Fence for v1

The following MUST NOT appear in v1 implementations (Phases 1–6):
- `order_value`, `scan_index`, or `geo` as keys in `TARGETING_CATALOG`.
- Any UI dropdown option for these attrs.
- Any `_to_edge_row` field mapping for these attrs.
- Any preview or overlap logic referencing these attrs.

If a user enters one of these keys in a targeting JSON directly (e.g. via a future raw-JSON escape hatch), `validate_targeting` must reject it with: "Thuộc tính '{key}' chưa được hỗ trợ trong v1."

## Todo (activate when scheduled)

- [ ] Spike: verify `request.cf.region` accuracy for VN cities in Cloudflare free tier
- [ ] D1 schema migration for `order_value` on `hug_token`
- [ ] Claim station UI change to capture order_value from Sapo order at bind
- [ ] Worker ScanContext + matchesTargeting update (additive — existing campaigns unaffected)
- [ ] Catalog + engine update in Python (additive)
- [ ] Overlap check update (range intersection for order_value, set for geo)
- [ ] Coordinated deploy: Worker → then CRM (Worker change is backwards-compatible with old push payloads that lack the new fields)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| scan_index race condition on concurrent scans | Medium | Low | v1 approximation (best-effort counter); strict accuracy deferred to Durable Objects |
| geo values from CF don't match expected Vietnamese city names | Medium | Medium | Spike first; build value list from actual CF headers before exposing in UI |
| order_value not available at claim time (async resolve) | Low | Low | Claim station reads Sapo order directly at bind (it already has order_code); order total is available from Sapo API or from DOM if using the userscript |

## Next Steps
- This file is a scope record, not an action item. Re-evaluate after A2 go-live and M6 campaign data accumulates.
- Link from `TARGETING_CATALOG` docstring in Phase 3: "# Deferred attrs: order_value, scan_index, geo — see phase-07-future-attrs.md"
