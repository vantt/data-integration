---
title: "P5 — A2 go-live: runbook + seed campaign + attribution readout"
status: pending
priority: P1
effort: 45m
---

## Context Links

- Plan overview: `plans/260620-1408-crm-hug-voucher-a2-golive/plan.md`
- A2 target: `mart_customer_tier.sql:44` tier=MASKED_REPEAT (~364 customers, 683M VND CM)
- Campaign UI (C2, live): `crm/src/adapters/inbound/web/screen_hug_campaign.py`
- campaign_push.py: `crm/src/hug/campaign_push.py`
- Attribution view: `v_hug_voucher_attribution` (P1 migration, `crm/migrations/0025_hug_voucher_ledger.up.sql`)
- Customer 360 screen: `crm/src/adapters/inbound/web/templates/customer_360.html`
- Sapo coupon verify: `plans/reports/hug-verify-sapo-coupon-zalo-deeplink-260619-1432-report.md`
- HUG_ZALO_OA_URL env var: `webhook_receiver/cloudflareD1/src/hug-handler.ts` (`getZaloOaUrl(env)`)
- build-order.md M5 row: targeting `{"op_type":["package_insert"],"tier":["MASKED_REPEAT"]}`, destination `zalo_oa`, offer_ref = `HUG50`

## Overview

**Priority:** P1 (prize — this is M5 go-live)**
**Status:** pending
**Depends on:** P3 (issuance writer live), P4 (redeem matcher live)

Operational phase: no new backend modules. Three deliverables:

1. **Manual Sapo step** (B0): create coupon "HUG50" in Sapo admin (once_per_customer + min-order 300,000 VND).
2. **A2 campaign seed** (config row via live C2 UI → campaign_push to edge D1).
3. **Attribution readout** (a minimal screen/query showing issued vs redeemed per campaign — reuses `v_hug_voucher_attribution`).

## Requirements

### B0 — Sapo coupon (manual, one-time)

Sapo admin → Price Rules → New:
- Code: `HUG50`
- Type: Fixed amount, 50,000 VND
- Min order: 300,000 VND
- Usage limit per customer: 1 (`once_per_customer = true`)
- Validity: set end date ~3 months out (align with campaign schedule_end)
- Applicable to: all products (or exclude margin-negative SKUs per economics guard §6 probe: `is_margin_negative`)
- Status: active

Verify by placing a test order with HUG50 in Sapo sandbox (if available) or confirm via API read:
`GET /admin/price_rules.json?discount_type=fixed_amount` (read-auth available per verify report).

### A2 campaign seed (C2 UI → campaign_push)

Navigate to `/hug/campaigns` → New Campaign:

| Field | Value |
|-------|-------|
| campaign_id | `a2-masked-repeat-optin` |
| name | `A2 — Masked Repeat Opt-in (HUG50)` |
| targeting | `{"op_type": ["package_insert"], "tier": ["MASKED_REPEAT"]}` |
| destination_type | `zalo_oa` |
| destination_url | `{HUG_ZALO_OA_URL}` (from env — confirm value) |
| offer_ref | `HUG50` |
| priority | `10` (below DEFAULT at 100 — wins when targeting matches) |
| schedule_start | today UTC |
| schedule_end | 90 days out |
| quota_total | NULL (Sapo once_per_customer enforces per-customer cap; shared code needs no local quota) |
| status | `active` |

Save → C2 UI calls `campaign_push.py` → `POST /hug/campaign/upsert` (HMAC) → D1 `hug_campaign` row live.

Verify: `wrangler d1 execute fgcare-webhook-db --remote --command "SELECT * FROM hug_campaign WHERE campaign_id='a2-masked-repeat-optin'"` → row present.

Scan a `package_insert` token belonging to a MASKED_REPEAT customer → landing shows "Mã ưu đãi của bạn: HUG50".

### Attribution readout (minimal screen)

Add a simple admin screen at `/hug/vouchers` (or surface as a tab on `/hug/campaigns`) showing:

- Source: `v_hug_voucher_attribution` (read from `crm.db`)
- Columns: Campaign ID | Code | Issued | Redeemed | Redeem Rate %
- No pagination needed for v1 (at most a handful of campaign rows)
- Reuse existing HTML template pattern (Jinja2 + htmx, same as `/hug/review`)

**Files to create/modify for readout:**
- `crm/src/adapters/inbound/web/screen_hug_voucher_attribution.py` — route + data fetch
- `crm/src/adapters/inbound/web/templates/screen_hug_voucher_attribution.html` — Jinja2 table

OR defer screen entirely: the attribution is also readable via:
```bash
sqlite3 /path/to/crm.db "SELECT * FROM v_hug_voucher_attribution"
```
This is acceptable for v1 if screen build would delay go-live. **Flag for user: screen vs CLI.**

## Architecture

```
Go-live sequence:
  B0: Sapo admin → create HUG50 coupon (manual, one-time)
  ↓
  A2 seed: C2 UI (/hug/campaigns) → save → campaign_push → D1 hug_campaign live
  ↓
  M3 packing begins: tokens bound to MASKED_REPEAT orders → push D1 hug_token
  ↓
  Customer scans QR → Worker resolves tier=MASKED_REPEAT + op_type=package_insert
                    → campaign a2-masked-repeat-optin wins
                    → redirect to {HUG_ZALO_OA_URL}?hug_token=...&hug_campaign=...
                    → landing: "Follow Zalo + để SĐT → nhận HUG50"
  ↓
  /admin/refresh cycle:
    hug_resolve      → crm_identity_link (customer contactable)
    hug_voucher_issue → crm_hug_voucher {HUG50, customer_id, issued_at}
    hug_voucher_redeem → (watches fact_orders for HUG50 usage)
  ↓
  Customer reorders with HUG50 (Sapo discounts B3)
  ↓
  Order ingest (webhook → parquet → dbt) → fact_orders.order_coupon_code = 'HUG50'
  ↓
  Next /admin/refresh → hug_voucher_redeem matches → redeemed_at set
  ↓
  v_hug_voucher_attribution: issued=N, redeemed=M, redeem_rate_pct=M/N*100
```

## Related Code Files

**Create (attribution screen — optional for v1):**
- `crm/src/adapters/inbound/web/screen_hug_voucher_attribution.py`
- `crm/src/adapters/inbound/web/templates/screen_hug_voucher_attribution.html`

**No backend code changes required** for B0 or A2 campaign seed (C2 UI already live).

**Verify existing env vars are set (`.env` at repo root):**
- `HUG_ZALO_OA_URL` — Zalo OA follow URL (required for landing page CTA + A2 destination)
- `HUG_WORKER_URL` — already set per build-order.md M3 notes
- `HUG_ADMIN_SECRET` — already set per build-order.md M2 notes

## Implementation Steps

1. **Confirm `HUG_ZALO_OA_URL`** is set in `.env`. The Worker uses `getZaloOaUrl(env)` in the landing page. If unset, landing Zalo CTA breaks silently.

2. **B0 — Create HUG50 in Sapo admin** (manual). Document the Sapo price_rule ID in a comment or in the campaign's `sku_guard` field for traceability.

3. **Seed A2 campaign via C2 UI** (`/hug/campaigns` → New). Use values from the table above. After save, verify D1 row via wrangler CLI.

4. **Smoke test full loop** (pre-scale):
   a. Bind a test token to a MASKED_REPEAT order (claim station or direct SQL insert into `hug_token` + push D1).
   b. Scan `hug.fjp.vn/h/{token}` → should redirect to Zalo OA URL with `?hug_campaign=a2-masked-repeat-optin`.
   c. Open opt-in landing for that token → submit test phone → success state shows "HUG50".
   d. Trigger `/admin/refresh` → check `crm_identity_link` row + `crm_hug_voucher` row.
   e. Insert a synthetic `fact_orders` row with `order_coupon_code='HUG50'` + matching `customer_id` → trigger refresh → `redeemed_at` set.
   f. Query `v_hug_voucher_attribution` → `issued=1, redeemed=1, redeem_rate_pct=100.0`.
   g. Clean up test data.

5. **Attribution screen** (optional — build or defer based on user preference):
   - If building: `screen_hug_voucher_attribution.py` reads `crm.db` directly (same pattern as `screen_hug_review_data.py`). Register route in main app router. Add nav link under Hug section.
   - If deferring: document the SQL query in a `# HOW TO CHECK` comment in `voucher_issuer.py`.

6. **Packing team briefing**: confirm claim station is operational (`/hug/claim`) and MASKED_REPEAT orders are being bound.

## Todo

- [x] Confirm `HUG_ZALO_OA_URL` — ✅ chốt + deploy 2026-07-10: `https://zalo.me/4578048148495215534`, set trong `webhook_receiver/cloudflareD1/wrangler.toml` `[vars]`, live trên `hug.fjp.vn` (Version ID `5225dc64-c763-47bf-839a-a9d045192e05`).
- [ ] B0: create HUG50 coupon in Sapo admin (manual step, document price_rule ID)
- [ ] Seed A2 campaign via C2 UI + verify D1 row via wrangler
- [ ] Smoke test full loop (steps 4a–4g above)
- [ ] Attribution readout — decide: screen vs CLI (user preference)
- [ ] (If screen) create `screen_hug_voucher_attribution.py` + template
- [ ] Packing team briefing on claim station

## Success Criteria

- `hug_campaign` D1 row `a2-masked-repeat-optin` is active with `offer_ref='HUG50'`.
- Scanning a MASKED_REPEAT token → redirect hits Zalo OA URL (not DEFAULT).
- Landing success state shows "HUG50" code.
- After opt-in + refresh: `crm_identity_link` row present, `crm_hug_voucher` row present with non-null `issued_at`.
- After order with HUG50 + refresh: `crm_hug_voucher.redeemed_at` set.
- `v_hug_voucher_attribution` queryable and returns correct counts.
- No DEFAULT fallback for MASKED_REPEAT + package_insert scans (campaign wins before DEFAULT).

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `HUG_ZALO_OA_URL` not set → landing Zalo CTA broken | Medium | High | Confirm env var before go-live (step 1) |
| A2 campaign priority conflicts with existing campaigns | Low | Medium | C2 UI overlap detector flags collisions; check before saving |
| MASKED_REPEAT tier definition drift (mart_customer_tier.sql update) | Low | Low | hug_customer nightly push keeps edge replica fresh; tier re-evaluates automatically |
| Sapo HUG50 coupon expired or misconfigured | Low | High | Verify coupon config in Sapo admin after B0; note expiry date in campaign schedule_end |
| Test data pollution (synthetic fact_orders row) | Low | Low | Delete test rows immediately after smoke test; use a clearly fake order_code |

## Security Considerations

- HUG50 is a shared code — Sapo `once_per_customer` is the only per-customer cap. Confirm this setting is active before go-live.
- Attribution screen is admin-only (behind CRM auth). No public exposure of issuance counts.
- `HUG_ZALO_OA_URL` is the Zalo OA follow link — public (users click it). No secrets embedded.

## Next Steps (M6 / deferred)

- **P6 (optional):** push `crm_hug_voucher` rows to edge D1 `hug_voucher` (voucher_push module + Worker `/hug/voucher/upsert` route) for edge-visible issuance/quota state.
- **A/B experimentation**: split MASKED_REPEAT traffic between HUG50 and control (no offer) to measure offer lift on opt-in rate.
- **ZNS follow-up (A4)**: once ZNS client/token available, send HUG50 reminder to opted-in-but-not-redeemed customers after N days.
- **Per-customer codes (flavor B)**: spike Sapo write-API auth; migrate to unique codes for stronger attribution.
