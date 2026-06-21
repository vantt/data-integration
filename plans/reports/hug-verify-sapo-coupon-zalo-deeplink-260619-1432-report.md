# Verification Report: Sapo Coupon API + Zalo OA Deep Link
_Date: 2026-06-19 | Read-only. No codebase changes._

---

## V1a — Sapo API Client (codebase)

**Verdict: Outbound Sapo API client EXISTS — cookie/session auth only, read-centric.**

- `ingestion/src/sapo/client.py` — `SapoClient` wraps a `SharedCookieManager` (Playwright-driven browser login, 7-day cookie TTL). Auth: **username + password → session cookie**. No OAuth token, no API key.
- Env var names (credentials only): `SOURCES__SAPO__DOMAIN`, `SOURCES__SAPO__USERNAME`, `SOURCES__SAPO__PASSWORD`.
- Existing endpoints used via this client (all GET/read):
  - `GET /admin/orders.json`
  - `GET /admin/customers/doSearch.json`
  - `GET /admin/products.json`
  - `GET /admin/accounts.json`
  - `GET /admin/reports/inventories/transaction.json`
  - `GET /admin/settings/get_logs` (history log)
  - `GET /admin/orders.json` (api_count reconciliation)
- **No write/POST endpoints are called anywhere in the codebase.** No coupon, price_rule, promotion, or discount-create calls exist.
- The client can in principle POST to any admin endpoint (it returns a `requests.Session`), but no such code exists today.

---

## V1b — Order Coupon-Code Field (warehouse — CRITICAL)

**Verdict: `order_coupon_code` EXISTS in raw Sapo payload but is NOT surfaced in `fact_orders` mart. `discount_codes` on orders is a separate field (Sapo PriceRule-based codes) and is also NULL in the mart for all 15,507 current rows.**

### Raw payload fields found (in `sapo_v2_raw/order` parquets, 72,615 total rows):

| Field | Location | Notes |
|---|---|---|
| `order_coupon_code` | `$.order_coupon_code` in raw JSON payload | JSON object when present: `{"id":…,"coupon_code":"OFF100","coupon_promotion_id":7077,"order_total_required":500000.0,"discount_amount":100000.0,"discount_percent":null,"status":"active","maximum_amount":null,"order_discount_value":100000.0}` |
| `discount_codes` | `$.discount_codes` in raw JSON payload | NULL in all sampled rows with `order_coupon_code` present |
| `discount_items` | `$.discount_items` JSON array | Contains `source`, `rate`, `value`, `amount`, `reason`, `promotion_redemption_id`; reason field contains informal text like `"voucher seller: [FINE0426]"` |
| `promotion_redemptions` | `$.promotion_redemptions` JSON array | Present but empty `[]` in all sampled rows |

### Sample `order_coupon_code` values from raw data:
- `OFF100` (min order: ₫500,000, discount: ₫100,000) — `coupon_promotion_id: 7077`
- `OFF500` (min order: ₫2,000,000, discount: ₫500,000) — `coupon_promotion_id: 7079`
- `OFF1M` (min order: ₫4,000,000, discount: ₫1,000,000) — `coupon_promotion_id: 7080`

### mart gap:
- `fact_orders.discount_codes` → all NULL (15,507 rows). The staging SQL extracts `$.discount_codes` from raw payload, but this field is NULL whenever `order_coupon_code` is used. Sapo uses **two separate discount mechanisms**: (a) `order_coupon_code` (Sapo's coupon system) and (b) `discount_codes` (price_rule-based codes). Only (b) reaches the mart.
- `order_coupon_code` is NOT extracted in `transformation/models/staging/src_sapo_v2_orders.sql` — it is noted in internal reports but never mapped to a staging column.
- `dim_promotions` mart contains only 1 row (`Unknown`) — confirming no PriceRule discount codes have been ingested via `discount_codes`.

### Conclusion for redeem-matching:
- `order_coupon_code` IS in raw parquets and contains the human-readable code string + min-order constraints.
- It is **not in `fact_orders`** today. Matching redeemed codes to issued codes would require either (a) adding `order_coupon_code` extraction to the staging pipeline, or (b) querying `sapo_v2_raw/order` parquets directly.
- The raw data is sufficient to implement matching — the field exists and is populated when a coupon is applied.

---

## V1c — Sapo Coupon API (web, official docs)

**Verdict: Sapo has a documented REST API for creating discount codes. Full constraint control requires a two-step: create PriceRule → create DiscountCode.**

Source: `https://support.sapo.vn/discountcode` + `https://support.sapo.vn/price-rule`

### Step 1 — Create PriceRule: `POST /admin/price_rules.json`

Supported constraints:

| Constraint | Field | Notes |
|---|---|---|
| Min order value | `prerequisite_subtotal_range.greater_than_or_equal_to` | e.g. `"500000.0"` |
| Product scope | `entitled_product_ids` / `entitled_variant_ids` / `entitled_collection_ids` | Mutually exclusive |
| Single-use per customer | `once_per_customer` | Boolean |
| Total usage cap | `usage_limit` | Integer |
| Expiry | `ends_on` | ISO 8601 timestamp |
| Discount type | `value_type` | `fixed_amount` / `percentage` / `fixed_price` |
| Discount value | `value` | Negative number |
| Applies to | `target_type` | `line_item` / `shipping_line` |
| Customer scope | `customer_selection` | `all` / `prerequisite` |

### Step 2 — Create DiscountCode: `POST /admin/price_rules/#{price_rule_id}/discount_codes.json`

Request body: `{ "discount_code": { "code": "YOUR_CODE" } }` — code up to 255 chars.

### Auth concern:
The official docs reference OAuth (`/oauth`) but our client uses session cookies (browser login). Whether the admin API accepts cookie auth for write operations (POST) needs to be verified — it likely works since our read GETs use the same session, but this is unverified for writes.

---

## V2a — Zalo Integration in Codebase

**Verdict: Zalo is present as a CHANNEL identity and conversation concept in CRM entities. ZNS sending capability is ABSENT.**

Files with Zalo references:
- `crm/src/domain/entities/party.py` — defines `IDENTITY_TYPE_ZALO_UID = "zalo_uid"`, `IDENTITY_TYPE_ZALO = "zalo"` as valid identity types on customer party.
- `crm/src/domain/entities/conversation.py` — defines `CHANNEL_ZALO = "zalo"` and includes it in `VALID_CHANNELS = [messenger, shopee, zalo]`.
- `crm/src/adapters/inbound/web/screen_customer_360.py` — maps `"zalo"` activity type to `"chat"` in UI.
- `crm/sync/search_index.py` — `"zalo_uid"` in verbatim token types (FTS index).
- `scripts/maintenance/sync_seeds.py` — classifies "zalo" channel name as `'Zalo'` channel.
- `transformation/exposures.yml` — Zalo appears as a sales channel source.
- **No ZNS API client, no ZNS sending code, no Zalo OA access token, no Zalo-related env vars** found anywhere in the codebase.

---

## V2b — Zalo OA Deep Link / Ref Parameter (web)

**Verdict: No native ref/payload parameter on the OA follow link is confirmed from official docs (docs are JavaScript-gated and not fetchable). Community evidence suggests no follow-link ref exists; the reliable path for token-tying is a web landing page.**

### What is documented:
- Zalo does fire a `follow` webhook event when a user follows an OA (confirmed via search + `developers.zalo.me/docs/official-account/webhook/quan-ly/su-kien-nguoi-dung-quan-tam-hay-bo-quan-tam-oa`). Payload fields known from community examples: `event_name`, `app_id`, `oa_id`, `timestamp`, `follower.id`, `follower.display_name`.
- **No `source`, `follow_link`, `ref`, or `location` field** is documented in the follow webhook payload. Community searches returned no evidence of such a parameter.
- Zalo Mini App deep links DO support parameters (`sh_type`, `sh_data` in base64) — but this is Mini App only, not OA follow links.
- Standard Zalo OA follow URLs: `https://zalo.me/<oa_id>` or QR code — no query parameter support documented.

### Practical conclusion:
A follow via `zalo.me/<oa_id>` cannot carry a per-customer token to the OA follow webhook. The reliable token-tie pattern is a **web landing page**:
1. Send customer a unique URL: `https://your-site.com/claim?token=<unique_token>`
2. Page validates token, captures Zalo uid via Zalo Social Login / OAuth (or phone form), marks token redeemed.
3. This is independent of the OA follow action — customer can follow OA from the same page via the Follow Widget (`developers.zalo.me/docs/social/widget-follow`).

---

## Verdicts

### V1 — Coupon feasibility

| Flavor | Description | Feasible? |
|---|---|---|
| A — Sapo system coupon | Create via PriceRule + DiscountCode API; Sapo enforces constraints (once_per_customer, min_order, expiry) natively | YES — API supports all needed constraints. Auth method (cookie POST) unverified for writes but likely works. Code string up to 255 chars → can encode customer token. |
| B — Manual/offline code | Pre-generate list, distribute via Zalo; Sapo enforces at checkout | YES — simpler, no API needed to create. Less real-time. |
| C — discount_items reason text | Informal voucher notation in discount_items.reason (e.g. `"voucher seller: [FINE0426]"`) | PARTIAL — present in raw data, not a structured code field, not in mart. |

**Can we match redeemed codes from ingested order data?**
- YES, but requires pipeline work. `order_coupon_code.coupon_code` (e.g. `"OFF100"`) is in raw parquets, linked to `coupon_promotion_id`. It is not in `fact_orders` today.
- If we issue per-customer unique codes (Flavor A), matching is: issued_code = redeemed code in `order_coupon_code.coupon_code`.
- Adding this column to staging (`src_sapo_v2_orders`) is straightforward — extract `json_extract_string(payload, '$.order_coupon_code')` → parse the code field.

### V2 — Zalo token-tie

| Approach | Feasible? |
|---|---|
| Deep-link ref on OA follow URL | NOT CONFIRMED. No `ref` parameter on `zalo.me/<oa_id>` documented. Follow webhook carries no source field. |
| Web landing page captures token + phone/Zalo uid | YES — reliable. Send unique URL, customer enters phone or Zalo Login, server ties token to Zalo uid before or alongside OA follow. |

**Recommendation for V2:** Web-form / web landing page approach is the only reliably documented path. ZNS-based confirmation is separately possible once a `zalo_uid` is captured (requires ZNS setup — currently absent).

---

## Unresolved Questions

1. **Sapo POST auth**: Does cookie-session auth support write (POST) to `/admin/price_rules.json`? Needs a live test call. OAuth may be required for programmatic writes.
2. **order_coupon_code → mart**: Is `coupon_promotion_id` enough to uniquely identify a per-customer issued code, or do we need to mint unique code strings (e.g. `CUST12345-OFF100`) to enable 1:1 matching?
3. **Zalo follow webhook source field**: Zalo docs are JavaScript-gated (WebFetch returned only page title). A Vietnamese dev who has implemented Zalo OA follow tracking should confirm whether any `source` or `app_id` variant can distinguish QR scans from link shares.
4. **ZNS setup effort**: ZNS requires Zalo OA verified account + ZNS template approval. Timeline unknown; if ZNS is part of the funnel flow, this is a dependency to size.
5. **dim_promotions / fact_orders gap**: `discount_codes` (PriceRule path) is all NULL in the mart — were PriceRule-style discounts ever used, or is Sapo coupon system (`order_coupon_code`) the only active mechanism? Clarify which coupon flavor will be used in the re-sell funnel.
