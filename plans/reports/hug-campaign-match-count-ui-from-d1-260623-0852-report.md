# Hug Campaign Match Count: D1-Sourced Preview Design
**Report:** researcher-260623-0852 | **Advisory only — no code changes**

---

## 1. Current State

### What the preview does today

`_rerender_with_preview()` in `screen_hug_campaign.py:310–344` calls:
1. `preview_match_customers(targeting, _cache_db_path())` — `targeting_engine.py:113–180`
2. `find_overlapping_campaigns(conn, targeting, ...)` — `campaign_overlap.py:146–181`

Both feed `render_campaign_form(..., preview=preview_result, overlaps=overlaps)`, which delegates the result panel to `render_preview_panel()` in `screen_hug_campaign_html_preview.py:14–136`.

### Exact data source

`preview_match_customers` opens **cache.db** read-only (`sqlite3.connect("file:{path}?mode=ro")`), queries `wh_customer_tier` — `targeting_engine.py:130,137–147`. This is a **nightly** local snapshot, not the live D1 replica.

### What hug_customer in D1 actually holds

`schema_hug.sql:35–43` — only 5 columns: `customer_id TEXT PK`, `tier TEXT`, `recency_days INTEGER`, `value_group TEXT`, `is_contactable INTEGER 0|1`, `updated_at TEXT`. **No name, no phone, no email.** PII exposure risk = minimal; `customer_id` is Sapo's opaque integer ID.

### Current caveats (documented in code)

| Caveat | Source |
|---|---|
| Data source is nightly cache.db, not live D1 | `targeting_engine.py:1–34` (module docstring) |
| Touchpoint-level attrs (`op_type`, `channel`) marked `touchpoint_level=True` in catalog | `targeting_catalog.py:30–41` |
| Those attrs absent from customer rows → treated as "no constraint" → count is **upper bound** | `targeting_engine.py:28–33`, `screen_hug_campaign.py:292–307` |
| Upper-bound warning injected into preview dict before render | `screen_hug_campaign.py:325–327` |
| Sample capped at 5 rows | `targeting_engine.py:171` |

### CRM contactability overlay gap

`customer_push.py` merges CRM-captured phones (`crm_identity_link`) into `is_contactable` before pushing to D1 (`customer_push.py:127–149`). The local `wh_customer_tier` in cache.db does NOT include this overlay — so the preview's `is_contactable` counts may undercount contactable customers vs D1 truth.

---

## 2. Approach Evaluation

### (A) New Worker admin endpoint `POST /hug/campaign/preview`

Accepts targeting JSON, scans `hug_customer` rows in D1 using the existing `matchesTargeting` TS function, returns `{count, customers: [...], data_as_of}`.

**Pros:**
- Single source of matching truth — no Python/TS logic duplication or drift
- Existing `verifyAdminHmac` pattern (`hug-handler.ts:317–327`) applies directly; no new auth primitives
- CRM calls via `post_signed` (already imports `d1_transport.post_signed`) — zero new infrastructure
- D1 data reflects the CRM contactability overlay already applied at push time
- Can return a full list of matching `customer_id`s (paginated with `limit`/`offset`)

**Cons:**
- Requires one new Worker route + deploy (`wrangler deploy`)
- D1 full-scan of `hug_customer` (~7.5k rows, no index on tier/value_group) — acceptable; SQLite scan of 7.5k rows is <10ms at D1 latency
- Touchpoint-level attrs (`op_type`, `channel`) still uncountable — same caveat as today

### (B) CRM queries D1 directly via CF REST API

**Cons (decisive):**
- Must re-implement `matchesTargeting` in Python SQL — exact bug class to avoid (drift vs TS matcher)
- New credentials: CF account ID + database ID + API token (separate from HUG_ADMIN_SECRET)
- CF D1 HTTP REST API is in beta/GA but adds a new auth path with no existing precedent in this codebase
- Logic parity tests would be needed perpetually

**Verdict: reject.** Violates DRY; creates a second authoritative matcher.

### (C) Keep cache.db preview, add D1 reconciliation count (hybrid)

**Pros:** No Worker deploy needed now.

**Cons:**
- Two preview paths for one concept — confusing UX
- Does not fix the CRM contactability overlay gap
- Still no user list from D1
- Punts the problem; the user explicitly wants D1 accuracy

**Verdict: reject.** Temporary scaffold that would coexist with A eventually anyway.

### Recommendation: **Option A**

DRY (single matcher), existing auth pattern, no new credentials, solves the accuracy gap and unlocks user listing.

---

## 3. Concrete Design Sketch

### 3.1 New Worker endpoint

**Route:** `POST /hug/campaign/preview`
**Auth:** existing `verifyAdminHmac` (HUG_ADMIN_SECRET, X-Hug-Signature header)
**File to edit:** `webhook_receiver/cloudflareD1/src/hug-handler.ts` (add handler + export); `webhook_receiver/cloudflareD1/src/index.ts` (add route).

**Request body:**
```json
{
  "targeting": { "tier": ["VIP", "CORE"], "recency_days": {"gte": 30} },
  "limit": 50,
  "offset": 0
}
```
- `targeting`: object (same schema as `hug_campaign.targeting`)
- `limit`: int, default 50, max 200 (admin use only; D1 scan is synchronous)
- `offset`: int, default 0 (for pagination of the user list)

**Response body:**
```json
{
  "count": 312,
  "total_customers": 7543,
  "data_as_of": "2026-06-22T23:15:00Z",
  "customers": [
    {"customer_id": "1234567", "tier": "VIP", "recency_days": 45, "value_group": "HIGH", "is_contactable": 1},
    ...
  ]
}
```
- `count`: customers matching targeting (across all rows, not just this page)
- `total_customers`: total rows in hug_customer (for the "N / M" display)
- `data_as_of`: max(updated_at) from hug_customer (staleness indicator)
- `customers`: the page of matched rows (up to `limit`); customer_id only + tier attrs — no PII

**Matching logic in Worker:**
Reuse the existing `matchesTargeting(targetingJson, ctx)` function at `hug-handler.ts:148–189`. Scan all rows from `hug_customer`, build `ScanContext`-compatible objects (same fields as the scan path), apply `matchesTargeting`. Collect count and the requested page of IDs.

**D1 query pattern:**
```sql
SELECT customer_id, tier, recency_days, value_group, is_contactable,
       updated_at
FROM hug_customer
-- No WHERE filter; matchesTargeting applied in TS loop (targeting logic is too
-- complex for SQL alone — range + list + AND/OR in one expression)
ORDER BY customer_id
```
All filtering in TS, then slice `[offset..offset+limit]` from matched results. At 7.5k rows this is fine in a single D1 query (no pagination of the DB query itself needed).

**Worker file changes summary:**
- `hug-handler.ts`: add `handleHugCampaignPreview(request, env)` function; export it
- `index.ts`: add route `POST /hug/campaign/preview` → `handleHugCampaignPreview`
- `wrangler deploy` required

### 3.2 CRM Python side

**New function in `crm/src/hug/d1_transport.py` (or new `preview_transport.py`):**
```python
def post_signed_with_response(url, secret, payload) -> dict:
    # Like post_signed() but reads and parses the JSON response body.
    # Returns {"ok": True, "data": {...}} or {"ok": False, "error": str}
```
`post_signed` today discards the response body (`targeting_engine.py` returns only status). Need the body for the count + customer list.

**New function in `crm/src/hug/targeting_engine.py` or new `hug/d1_preview.py`:**
```python
def preview_match_customers_d1(targeting, limit=50, offset=0) -> dict:
    # Calls POST /hug/campaign/preview via post_signed_with_response.
    # Returns same shape as preview_match_customers() + "customers" list.
    # Falls back gracefully: if push_enabled() is False or call fails,
    # returns {"error": "D1 preview unavailable: ...", "matched": 0, ...}
```

### 3.3 Changes to `screen_hug_campaign.py`

`_rerender_with_preview()` at `screen_hug_campaign.py:310` currently calls `preview_match_customers(targeting, _cache_db_path())`. Replace with:

```python
if push_enabled():
    preview_result = preview_match_customers_d1(targeting)
else:
    preview_result = preview_match_customers(targeting, _cache_db_path())
    preview_result["source"] = "cache"  # for UI label
```

Fallback to cache.db when Worker URL not configured preserves dev-mode usability.

### 3.4 UI changes in `screen_hug_campaign_html_preview.py`

Extend `render_preview_panel()`:

1. **Count header:** already shows "Khớp ~N / M khách hàng". Change `~` to exact (no tilde) when source is D1. Add `data_as_of` timestamp as subscript.
2. **User list table:** currently shows up to 5 sample rows. With D1 response:
   - Show up to `limit` rows (50 by default) — same table columns as today
   - Add `Tải thêm` link/button: `action=preview_page&page=N` form param, re-POSTs to get next page
   - Keep 5-row sample when falling back to cache.db
3. **Source badge:** small pill "D1 (chính xác)" vs "cache.db (hôm qua)" to communicate data freshness
4. **Upper-bound warning:** retained — touchpoint-level caveat unchanged

### 3.5 Auth flow (unchanged)

`d1_transport.sign(secret, raw_body)` → `X-Hug-Signature: sha256=<hex>` + `User-Agent: FineJapan-Hug-Push/1.0`. Exactly the same as all other `/hug/*` admin routes. No new secrets.

---

## 4. Matching Accuracy Caveats That Remain

These persist **regardless of D1 as data source** because they are intrinsic to customer-level matching:

| Caveat | Detail |
|---|---|
| `op_type` (touchpoint_level) | Comes from `hug_token.op_type`, not `hug_customer`. A customer scanned via `package_insert` is a different context from `loyalty_card`. Preview counts them all (upper bound). No fix possible without joining tokens — but a customer can have tokens of multiple op_types; the count would then overcount. |
| `channel` (touchpoint_level) | Same issue: `hug_token.channel`. Per-scan attribute. |
| Snapshot staleness | D1 is updated nightly via `customer_push.run()`. Preview reflects the last push, not real-time. `data_as_of` from `max(updated_at)` surfaces this. |
| New customers between push cycles | Customers onboarded since the last nightly push are absent from D1 `hug_customer`. Same gap as cache.db today. |
| `is_contactable` overlay timing | CRM-captured phones pushed to D1 during nightly customer push. D1 preview is more accurate than cache.db (which lacks the overlay), but still not real-time. |

---

## 5. Effort & Risk

| Item | Estimate | Risk |
|---|---|---|
| Worker: add `handleHugCampaignPreview`, export, route | 1–2h TS | Low — follows existing handler pattern exactly |
| `wrangler deploy` | ~5 min | Low — additive route, no existing route touched |
| Python: `post_signed_with_response` | 30 min | Low — trivial extension of existing function |
| Python: `preview_match_customers_d1` + fallback | 1h | Low — wraps transport; graceful fallback already designed |
| `screen_hug_campaign.py`: swap call site | 30 min | Low — single call site at line 324 |
| `screen_hug_campaign_html_preview.py`: extend render | 1–2h | Low — additive HTML; existing panel structure reused |
| Pagination UX (optional) | +1h | Medium — adds a form re-POST path; can skip for v1, show 50 rows flat |

**Total: ~4–6h excluding pagination. No schema changes. No new secrets. Fully backwards-compatible (cache.db fallback when Worker URL unset).**

**Primary risk:** D1 Worker deploy. If `wrangler deploy` is blocked (e.g. Worker code has unrelated pending changes), the Python side must remain on cache.db until deploy is clear.

---

## Unresolved Questions

1. **Pagination UX:** Is a flat 50-row list sufficient for v1, or is paginated navigation required at launch? Affects the UI effort estimate.
2. **Worker deploy timing:** Are there any pending Worker changes that would complicate an additive deploy right now?
3. **`post_signed_with_response` placement:** Should it live in `d1_transport.py` (extending the transport module) or in a new `d1_preview.py`? The transport module currently has no response-body consumers — a new file keeps concerns separate; the transport module keeps it DRY.
4. **Preview latency expectation:** D1 cold-start + full-scan of 7.5k rows + TS loop may take 200–800ms on first request. Acceptable for an admin action? Worker in-memory campaign cache (`_campaignCache`) is irrelevant here — this is a new path. Should the CRM admin show a spinner?
5. **Customer list export:** Would the admin want to download (CSV) the matched customer list, or is the on-screen table enough?
