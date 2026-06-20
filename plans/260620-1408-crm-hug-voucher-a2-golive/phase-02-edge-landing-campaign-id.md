---
title: "P2 — Edge landing: reveal offer_ref code + carry hug_campaign in opt-in POST"
status: pending
priority: P1
effort: 60m
---

## Context Links

- Plan overview: `plans/260620-1408-crm-hug-voucher-a2-golive/plan.md`
- Landing handler: `webhook_receiver/cloudflareD1/src/hug-handler.ts:532–699`
- Worker scan path (appends `?hug_campaign=` to redirect): `hug-handler.ts:254–257`
- `hug_campaign` D1 schema + `offer_ref` field: `webhook_receiver/cloudflareD1/schema_hug.sql` + `hug-handler.ts:67–68`
- Opt-in POST body (current): `hug-handler.ts:666–671` — sends `{token, phone, consent, ts}` — **no `campaign_id`**
- `src_hug_optin_event.sql:77–85` — current payload fields extracted (no `campaign_id`)
- `stg_hug_optin_event.sql` + `mart_hug_optin.sql` — downstream pipeline

## Overview

**Priority:** P1 (blocks P3 issuance writer, which needs `campaign_id` on the opt-in row)
**Status:** pending

Two gaps to close in the edge Worker landing page:

1. **Offer reveal**: landing currently shows generic "Nhận ưu đãi ngay" with no code. When the winning campaign has `offer_ref` set, the success state should display the code (e.g. "Mã của bạn: **HUG50**"). The code is already in D1 `hug_campaign.offer_ref`; the landing just needs to fetch and display it.

2. **campaign_id propagation**: the opt-in form POST (`/webhook/hug/optin/created`) sends `{token, phone, consent, ts}`. To write the issuance ledger locally (P3), the pipeline needs `campaign_id`. The simplest path: the landing reads `?hug_campaign=<id>` from its own URL (already appended by the scan redirect at `hug-handler.ts:256`) and includes it in the POST body.

Changes are **edge-only** (Worker TypeScript + downstream SQL extraction). No local Python changes needed until P3.

## Requirements

- Landing receives `?hug_campaign=<campaign_id>` in its URL (already true via scan redirect).
- Landing fetches `offer_ref` from D1 `hug_campaign` using the campaign_id param.
- After successful opt-in submit, success state shows the offer code prominently if `offer_ref` is non-null. If null, show generic "Chúng tôi sẽ liên hệ sớm" (no change from today).
- Opt-in POST body gains a `campaign_id` field (nullable — landing without `?hug_campaign` param sends `null`).
- Safety: missing/invalid campaign_id → proceed without offer reveal (no error to user). Empty string safety-placeholder → treat as null.
- No PII in the offer code reveal (code is shared, not per-customer). Safe to display.
- `src_hug_optin_event.sql` gains `campaign_id` extraction. `stg_hug_optin_event.sql` passes it through. `mart_hug_optin.sql` exposes it.

## Architecture

```
scan redirect → GET /optin/{token}?hug_campaign=<id>
  Worker:
    1. D1: SELECT offer_ref FROM hug_campaign WHERE campaign_id = ?hug_campaign
    2. Embed campaign_id + offer_ref into page HTML (baked, no client-side D1 call)
    3. Form submit includes campaign_id in POST body

POST /webhook/hug/optin/created  body: {token, phone, consent, ts, campaign_id?}
  → D1 queue → local poll → hug_raw/optin_event/ → src_hug_optin_event (extract campaign_id)
  → mart_hug_optin (expose campaign_id) → P3 issuance writer reads it
```

## Data Flow

| Stage | What changes |
|-------|-------------|
| `handleHugOptinLanding(token)` | Receives URL param `hug_campaign`; D1 lookup for `offer_ref`; embeds both into HTML |
| Client-side JS (`optin-form` submit) | Adds `campaign_id` to POST body |
| `src_hug_optin_event.sql` | `json_extract_string(payload, '$.campaign_id')` → new col |
| `stg_hug_optin_event.sql` | Pass-through new col |
| `mart_hug_optin.sql` | Expose `campaign_id` in SELECT |

## Related Code Files

**Modify:**
- `webhook_receiver/cloudflareD1/src/hug-handler.ts` — `handleHugOptinLanding` function (lines 532–699)
- `transformation/models/staging/src_hug_optin_event.sql` — add `campaign_id` extraction
- `transformation/models/staging/stg_hug_optin_event.sql` — add `campaign_id` pass-through col
- `transformation/models/marts/customer/mart_hug_optin.sql` — add `campaign_id` to SELECT

**No new files needed.**

## Implementation Steps

### Step 1 — Worker: `handleHugOptinLanding` signature + D1 lookup

`hug-handler.ts:532` currently:
```ts
export async function handleHugOptinLanding(
    _request: Request,
    env: Env,
    token: string
): Promise<Response>
```

Change to accept the full `Request` (already passed as `_request`) and read the `hug_campaign` query param from it:

```ts
export async function handleHugOptinLanding(
    request: Request,  // was _request
    env: Env,
    token: string
): Promise<Response> {
    // ... existing validation ...
    const url = new URL(request.url);
    const campaignId = url.searchParams.get('hug_campaign') ?? null;

    // Fetch offer_ref from D1 if campaign known
    let offerCode: string | null = null;
    if (campaignId) {
        const row = await env.DB.prepare(
            'SELECT offer_ref FROM hug_campaign WHERE campaign_id = ? AND status = \'active\' LIMIT 1'
        ).bind(campaignId).first<{ offer_ref: string | null }>();
        offerCode = row?.offer_ref ?? null;
    }
    // ... rest of function ...
```

### Step 2 — Bake campaignId + offerCode into HTML

In the HTML template (around line 629 where `TOKEN` is baked):
```ts
var TOKEN = ${JSON.stringify(safeToken)};
var CAMPAIGN_ID = ${JSON.stringify(campaignId ?? '')};
```

Success state: conditionally show offer code after submit:
```html
<div class="success" id="success-state">
  <h2>Đã nhận thông tin!</h2>
  ${offerCode
    ? `<p>Mã ưu đãi của bạn: <strong style="font-size:1.3rem;color:#e8231a">${offerCode}</strong></p>
       <p style="color:#555;font-size:.85rem">Nhập mã này khi đặt hàng để được giảm giá.</p>`
    : `<p>Cảm ơn bạn. Chúng tôi sẽ liên hệ sớm nhất có thể.</p>`}
  <!-- Zalo follow CTA stays regardless -->
```

Escape `offerCode` for HTML (it's a Sapo coupon code — alphanumeric, but be explicit):
```ts
const safeOffer = offerCode ? offerCode.replace(/[<>&"']/g, '') : null;
```

### Step 3 — Include campaign_id in POST body (client-side JS)

In the `fetch(SUBMIT_URL, ...)` body construction (around line 666):
```ts
var body = {
    token: TOKEN,
    phone: phone,
    consent: { phone: true, ts: ts },
    ts: ts
};
if (name) body.name = name;
if (CAMPAIGN_ID) body.campaign_id = CAMPAIGN_ID;  // ← add this
```

### Step 4 — `src_hug_optin_event.sql`: extract `campaign_id`

In the `extracted` CTE (after `opted_in_at_raw`):
```sql
json_extract_string(payload, '$.campaign_id')        AS campaign_id
```

Add to the UNION ALL fallback select list too (line ~97) and the QUALIFY select.

Note: `on_schema_change='append_new_columns'` is already set — new col auto-added on next incremental run without full-refresh. Existing rows get NULL campaign_id (correct — they pre-date this change).

### Step 5 — `stg_hug_optin_event.sql`: pass through

Add `campaign_id` to the SELECT after `opted_in_at_raw`:
```sql
campaign_id,
```

### Step 6 — `mart_hug_optin.sql`: expose column

Add `campaign_id` to the `latest_per_pair` CTE columns and to the final SELECT.

### Step 7 — Deploy Worker

```bash
cd webhook_receiver/cloudflareD1
npx wrangler deploy
```

Verify: open `https://hug.fjp.vn/optin/TEST_TOKEN?hug_campaign=default` → page loads; no JS errors; form submit includes campaign_id in network tab.

### Step 8 — dbt parse check

```bash
cd transformation
dbt parse
```

No errors expected (new column additions are backwards-compatible).

## Todo

- [ ] Worker: read `hug_campaign` URL param in `handleHugOptinLanding`
- [ ] Worker: D1 fetch `offer_ref` for campaign (nullable, safe failure)
- [ ] Worker: bake `CAMPAIGN_ID` + offer code into HTML template
- [ ] Worker: success state conditional offer-code display
- [ ] Worker: include `campaign_id` in form POST body
- [ ] `src_hug_optin_event.sql`: add `campaign_id` extraction + UNION ALL
- [ ] `stg_hug_optin_event.sql`: pass-through `campaign_id`
- [ ] `mart_hug_optin.sql`: add `campaign_id` to SELECT
- [ ] `npx wrangler deploy` + smoke test with `?hug_campaign=default`
- [ ] `dbt parse` clean

## Success Criteria

- Scanning a token whose winning campaign has `offer_ref='HUG50'` → landing success shows "Mã ưu đãi của bạn: HUG50".
- Scanning with no `?hug_campaign` or campaign with null `offer_ref` → landing shows generic success (no crash).
- POST body to `/webhook/hug/optin/created` includes `campaign_id` field when present.
- `mart_hug_optin` table has `campaign_id` column after next dbt run.
- `dbt parse` exits 0.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| D1 lookup adds latency to landing page load | Low | Low | One read on `hug_campaign` (small table, cached in Worker) — negligible |
| `offerCode` XSS via injected campaign data | Low | Medium | Escape `offerCode` before HTML embed (step 2) |
| `on_schema_change` does not add col in DuckDB incremental | Low | Low | dbt parse will catch; worst case force full-refresh of src model |
| Worker deploy breaks existing opt-in path | Low | High | Smoke-test immediately after deploy; rollback = `wrangler rollback` |

## Security Considerations

- `offer_ref` is a shared coupon code (not per-customer PII). Safe to display in HTML.
- `campaignId` from URL param: used only for a D1 lookup, not reflected into response unescaped. Validate max-length + alphanumeric before bind.
- `safeOffer` escaping prevents any injected HTML if D1 row is corrupted.

## Next Steps

- P3 (issuance writer) reads `campaign_id` from `mart_hug_optin` — depends on Step 6 being deployed + dbt run complete.
- No dependency on P1 (migration) — can develop in parallel.
