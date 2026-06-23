# Hug Campaign Targeting — Criteria Expansion Advisory

**Date:** 2026-06-23  
**Scope:** Advisory only. No code changes. Covers what data exists, what the matcher supports, and what additions are worth doing.

---

## 1. Baseline: What Is Actually In Place

### 1a. D1 Data Available at Match Time

`handleHugScan` joins two tables at scan time (`hug-handler.ts:226-230`):

| Column | Table | Notes |
|--------|-------|-------|
| `op_type` | `hug_token` | touchpoint_level |
| `channel` | `hug_token` | touchpoint_level |
| `ship_date` | `hug_token` | touchpoint_level; ISO date string |
| `sku` | `hug_token` | touchpoint_level; primary SKU only |
| `order_code` | `hug_token` | touchpoint_level |
| `batch_id` | `hug_token` | touchpoint_level |
| `campaign_hint` | `hug_token` | NOT in ScanContext (dropped at build) |
| `tier` | `hug_customer` | customer_level |
| `recency_days` | `hug_customer` | customer_level |
| `value_group` | `hug_customer` | customer_level |
| `is_contactable` | `hug_customer` | customer_level |

`ScanContext` interface (`hug-handler.ts:79-90`) includes: `op_type, tier, channel, value_group, recency_days, is_contactable, customer_id, order_code, ship_date, sku`. All are in-scope for `matchesTargeting`.

**Notably absent from ScanContext:** `batch_id`, `campaign_hint`, any scan history (no scan count). These columns exist in `hug_token` D1 but are NOT forwarded into the context object used for matching.

### 1b. Implemented Targeting Attributes (v1)

Six in `TARGETING_CATALOG` (`targeting_catalog.py:27-68`):
- `op_type` — list, touchpoint_level
- `channel` — list, touchpoint_level
- `tier` — list, customer_level
- `value_group` — list, customer_level  
- `is_contactable` — list [0,1], customer_level
- `recency_days` — range (gte/gt/lte/lt), customer_level

Deferred: `order_value`, `scan_index`, `geo` — explicitly noted in `targeting_catalog.py:16-17`.

### 1c. Matcher Shape Support

`matchesTargeting` (`hug-handler.ts:148-189`) supports:
- **Array rule** → OR membership, string-coerced (`hug-handler.ts:165-172`)
- **Object rule** → numeric range with gte/gt/lte/lt (`hug-handler.ts:173-180`)
- **Scalar rule** → string equality (`hug-handler.ts:182-186`)
- **Empty object** → always-match DEFAULT

**Not supported:** negation (`not_in`), regex, set-intersection beyond membership, OR across keys (by design — separate campaigns used instead per `discussion-hug.md §7`).

### 1d. Mart Data Available for Push

`mart_customer_tier.sql` selects from `dim_customers` — **NOT currently pushed** to `hug_customer` but available at nightly build time:
- `customer_type` (WHOLESALE/CROSSBORDER/PARTNER/STAFF/KOL/RETAIL) — `dim_customers.sql:119-126`
- `lifetime_value` (monetary_value) — `dim_customers.sql:200`
- `order_count` — `dim_customers.sql:201`
- `acquisition_source` (first-order channel_name) — `dim_customers.sql:191`
- `geo_region` (GEO_HCMC/GEO_HANOI/GEO_MEKONG/GEO_CENTRAL/GEO_OTHER) — `dim_customers.sql:180-187`
- `channel_preference` — `dim_customers.sql:143`

`customer_push.py:127-149` (`_build_edge_rows`) only pushes: `customer_id, tier, recency_days, value_group, is_contactable`. All other mart columns are silently dropped.

---

## 2. Evaluation of Deferred Attributes

### 2a. `order_value` (last-order or avg spend)

- **Data source:** `dim_customers.avg_order_spend` (available in mart) — customer_level
- **In D1 today?** No — not in `hug_customer` schema (`schema_hug.sql:35-45`) and not pushed by `customer_push.py`
- **Worker change needed?** New column in `hug_customer` + add to `ScanContext` + `matchesTargeting` already handles numeric range objects — **no matcher change needed**
- **Business value:** High. Enables "only offer 100K voucher to HIGH-spend segment." Already partially covered by `value_group` (HIGH/MID/LOW), but `value_group` is lifetime-based. Avg order spend allows targeting the "small-basket-but-frequent" vs "high-basket-rare" split.
- **Concern:** `value_group` already proxy-covers this. Marginal gain over combining `tier + value_group`. The real gap is **"did this specific order justify a premium offer?"** which is per-shipment context — but that's `order_code` + local lookup, not feasible at edge.
- **Complexity:** Low — add 1 column to `hug_customer`, push from mart. 3 touch points: schema migration, customer_push, targeting_catalog.
- **Verdict:** DEFER. `value_group` already covers the main use case. Add when a real campaign requires finer spend targeting that `value_group` cannot express.

### 2b. `scan_index` (Nth scan of same token)

- **Data source:** Would require counting rows in `hug_voucher` or a separate scan-count table in D1 per token. Currently **no scan history stored in D1** — scan events go to the `webhooks` transient queue (`hug-handler.ts:302-308`) which is drained/deleted locally. D1 has no persistent scan log.
- **In D1 today?** No. Would require a new D1 persistent table `hug_scan_count(token TEXT PK, count INTEGER)` and an atomic increment on every scan (D1 has no `RETURNING` + update-and-read in one statement easily — needs a second SELECT or Durable Object for strict ordering).
- **Worker change needed?** Yes — substantial. New D1 table, atomic counter write on hot path, add to ScanContext, add to matcher. Counter write on hot path is latency concern (D1 write + read before redirect vs current single read).
- **Business value:** Genuine use case: "first scan = opt-in campaign; subsequent scans = reorder/loyalty." Trulyl differentiating lifecycle-aware routing (noted as a core capability in `phase-hug-dynamic-touchpoint-platform.md:48`). But the `op_type=loyalty_card` already separates lifecycle channels somewhat.
- **Complexity:** High. D1 atomic increment is tricky (SQLite WAL, not Durable Object). Adds D1 write to hot path. Soft-count (eventual) over-counts for parallel scans.
- **Verdict:** KEEP for v2. Highest business value of the three deferred attrs but highest implementation risk. The hot-path latency impact (extra D1 write) must be measured. The scan-count preview work (sibling investigation) must solve the same counting problem — coordinate there first.

### 2c. `geo`

- **Data source:** `dim_customers.geo_region` (GEO_HCMC/GEO_HANOI/GEO_MEKONG/etc) computed from `province` — customer_level, available in mart.
- **In D1 today?** No — not in `hug_customer` schema or push.
- **Worker change needed?** No — existing list-type matcher handles it.
- **Business value:** Moderate. FineJapan distributes nationally; geo campaigns (HCM pickup event, Hanoi distributor promo) are plausible. But at 7.5k customer scale, geographic segmentation likely doesn't produce cohorts large enough to justify separate campaigns vs just running "LIVE_CORE + tier" targeting.
- **Data quality concern:** `province` from Sapo is user-entered (varies in naming). `dim_customers.sql:179-187` normalizes ~40 provinces to 5 regions — good enough.
- **Complexity:** Low. Add `geo_region TEXT` to `hug_customer`, push from mart, add to catalog.
- **Verdict:** DEFER. Genuinely low marginal value at current scale. Revisit when physical event campaigns require geographic filtering.

---

## 3. New Candidate Criteria

### 3a. `sku` / Product Category Targeting — ALREADY IN SCANCONTEXT

- **Data source:** `hug_token.sku` (primary SKU on the order at pack time) — touchpoint_level. **Already in `ScanContext`** (`hug-handler.ts:89`) and already in D1 (`schema_hug.sql:22`).
- **Worker change needed?** No — matcher supports list equality. Only change: add `sku` to `TARGETING_CATALOG` with `touchpoint_level=True`.
- **Business value:** High. Enables "if they bought Product X (low-margin SKU), route to 'no voucher' campaign; if Product Y (high-margin), offer 50K." Exactly the voucher guard economics described in `discussion-hug.md §9`. Also enables product-specific landing pages (review request for specific SKU).
- **Complexity:** Low — zero schema/Worker changes. Only add to catalog + validator + preview note.
- **Preview impact:** touchpoint_level, so preview count is upper bound (same as op_type/channel).
- **Verdict:** KEEP. Highest ROI addition — zero infrastructure cost, direct business use case.

### 3b. `customer_type` (B2B vs retail)

- **Data source:** `mart_customer_tier.sql:65` selects `customer_type` from `dim_customers`. Values: WHOLESALE/CROSSBORDER/PARTNER/STAFF/KOL/RETAIL. In mart but **not pushed** to `hug_customer`.
- **In D1 today?** No — `hug_customer` schema has 4 columns, `customer_type` not among them (`schema_hug.sql:36-44`).
- **Worker change needed?** No — list matcher handles it.
- **Business value:** Genuine. WHOLESALE/B2B customers should NOT receive retail opt-in campaigns or discount vouchers (different pricing structure). CROSSBORDER customers (VN recipients of US-shipped gifts) have different campaign context. Without this, a VIP wholesale buyer gets the same insert campaign as retail.
- **Complexity:** Low. Add `customer_type TEXT` column to `hug_customer` D1 schema, add to `customer_push._build_edge_rows`, add to catalog. `_content_str` in `customer_push.py:183-189` must include new field.
- **Verdict:** KEEP. Prevents campaign mis-targeting of B2B accounts. Already partially expressible via tier (WHOLESALE accounts may not appear in strategic tiers), but not reliably — `customer_type` is explicit.

### 3c. `batch_id` Campaign Cohort Targeting

- **Data source:** `hug_token.batch_id` — touchpoint_level. **Already in D1** (`schema_hug.sql:23`) and already in the `HugToken` interface (`hug-handler.ts:49`) but **NOT forwarded to `ScanContext`** (`hug-handler.ts:232-243` — batch_id omitted).
- **Worker change needed?** Minor — add `batch_id: string | null` to `ScanContext`, populate it in `handleHugScan`. Matcher already handles list equality.
- **Business value:** Moderate-high. Enables "run a specific campaign only for tokens from batch BATCH_202606 (Tết packaging run) vs BATCH_202603 (regular)." Useful for cohort-level A/B experiments across packaging runs without op_type differentiation.
- **Complexity:** Very low — one line change to ScanContext build in `handleHugScan`. Add to catalog with `touchpoint_level=True`.
- **Verdict:** KEEP. Already in D1, near-zero cost to expose.

### 3d. `ship_date` Recency (Days Since Ship)

- **Data source:** `hug_token.ship_date` (ISO date string) — touchpoint_level. **Already in D1 and ScanContext** (`hug-handler.ts:88`). But `matchesTargeting` receives it as a **string**, and the range matcher requires a **number**. No date arithmetic at match time.
- **Worker change needed?** Yes — compute `days_since_ship = (now - ship_date) / 86400000` at ScanContext build time, add as `ship_days_ago: number | null` to ScanContext. One addition to `handleHugScan`.
- **Business value:** High. "Show reorder campaign only if scanned within 30 days of shipment (still fresh)." "Show win-back campaign if scanned >90 days after ship (dormant re-engagement, unusual)." This distinguishes an engaged customer scanning right away vs someone who found an old insert. 
- **Complexity:** Low. Compute a derived numeric at context build time. No D1 schema change.
- **Verdict:** KEEP. Unique insight unavailable from customer-level attrs. Pairs naturally with `op_type` for lifecycle logic.

### 3e. `order_count` (Lifetime Purchase Count)

- **Data source:** `mart_customer_tier.sql:68` selects `order_count` from `dim_customers`. In mart, **not pushed**.
- **In D1 today?** No.
- **Worker change needed?** No — range matcher handles integers.
- **Business value:** Low-moderate. Mostly redundant with `tier`: LIVE_CORE requires order_count > 1, MASKED_REPEAT requires order_count > 1, SECOND_ORDER is exactly order_count = 1. The strategic tier already encodes order_count thresholds. A direct `order_count` attr would only matter for finer-grained targeting (e.g., "3+ orders" vs "2 orders") not expressible via tier.
- **Complexity:** Low but adds a number to push payload and content hash.
- **Verdict:** DEFER. `tier` covers the material splits. Add only if a campaign explicitly needs exact order-count thresholds that `tier` cannot express.

### 3f. Day-of-Week / Time-of-Scan

- **Data source:** Runtime — `new Date()` in the Worker. No D1 lookup needed.
- **Worker change needed?** Add `day_of_week: number` (0-6) and/or `hour_of_day: number` (0-23 in ICT) to ScanContext at call time. Matcher already handles numeric range and list.
- **Business value:** Low at current scale. Could enable "weekend-only flash sale" or "evening campaign." But FineJapan campaigns are not yet time-sensitive enough to justify this complexity. Also conflicts with the 60s campaign cache (`CAMPAIGN_CACHE_TTL_MS`) — a campaign that starts at 18:00 might not activate until 18:01 due to cache staleness. Acceptable but surprising.
- **Complexity:** Low (pure runtime computation) but the catalog addition + campaign cache interaction needs documentation.
- **Verdict:** DEFER (YAGNI). No active campaign need identified.

### 3g. `acquisition_source` (First-Order Channel)

- **Data source:** `dim_customers.acquisition_source` (first-order channel_name). In mart, not pushed.
- **Business value:** Low for campaign routing. Mostly subsumed by `channel` (current order channel) and `tier`. "First bought on Shopee" doesn't dictate what campaign to show on the 5th shipment.
- **Verdict:** SKIP.

### 3h. Per-Customer Scan Caps / One-Redemption Guards

- **Nature:** These are NOT targeting criteria — they're **quota enforcement**. The distinction matters architecturally.
- **Current state:** `hug_campaign.quota_total` / `quota_used` (`schema_hug.sql:62-63`) is a campaign-level cap, not per-customer. `hug_voucher` PK `(code, customer_id)` (`schema_hug.sql:84`) prevents duplicate voucher issuance per customer per code — one-redemption guard already exists at voucher level.
- **Missing:** Per-customer scan frequency cap (e.g., "don't show this campaign to the same customer more than once"). Implementing this requires a per-customer × per-campaign counter in D1 (persistent), checked on every scan. Similar latency concern as scan_index.
- **Verdict:** Separate concern from targeting. Track in `hug_voucher` table improvements, not targeting_catalog. DEFER.

---

## 4. Rule-Shape Gaps in the Matcher

### 4a. Negation (`not_in`)

**Current:** list rule = OR membership. No way to say "tier NOT IN ['WHOLESALE', 'STAFF']."  
**Workaround:** Create a new campaign with explicit positive list of all non-excluded tiers. With ~10 tier values, this is verbose but workable.  
**Cost of adding `not_in`:** The `matchesTargeting` function in both `hug-handler.ts` and `targeting_engine.py` (Python mirror) must distinguish `{"tier": [...]}` (include) from `{"tier": {"not_in": [...]}}` (exclude). This breaks the current clean `Array → OR` pattern.  
**Verdict:** ADD `not_in` operator. It unlocks "all tiers except WHOLESALE/STAFF/KOL" in one clean rule without enumerating 7+ values. Customer-type exclusion (`customer_type not_in ['WHOLESALE']`) is the primary use case. Implementation: treat `{"not_in": [...]}` as the object-rule branch, check array membership and negate. 3 touch-points: `matchesTargeting` (TS), `matches_targeting` (Python), `validate_targeting`. Low complexity.

### 4b. Multiple Ranges on Same Attribute

**Current:** `recency_days` can express one contiguous range `{gte: 30, lte: 90}`. Cannot express "30-60 OR 120-180 days."  
**Workaround:** Two campaigns with same destination, different priority.  
**Verdict:** SKIP. The workaround is clean and the AND/OR model (`discussion-hug.md §7`) was intentionally kept simple. Adding disjunctive range arrays would complicate the catalog significantly.

### 4c. Date Comparison for `ship_date`

**Current:** `ship_date` is a string in ScanContext, unusable by the range matcher. The `ship_days_ago` computed field (rec 3d above) solves this at context build time.  
**Verdict:** Covered by `ship_days_ago` proposal — no matcher shape change needed.

---

## 5. Prioritized Candidate Table

| Criterion | Source | In D1? | Worker change? | Shape supported? | Value | Complexity | Verdict |
|-----------|--------|--------|---------------|-----------------|-------|------------|---------|
| **`sku`** | hug_token (touchpoint) | YES | No (catalog only) | Yes (list) | High | Very Low | **KEEP — P0** |
| **`not_in` operator** | matcher shape | N/A | Yes (TS+Python+validator) | No | High | Low | **KEEP — P0** |
| **`customer_type`** | mart_customer_tier (customer) | No | No (schema+push) | Yes (list) | High | Low | **KEEP — P1** |
| **`batch_id`** | hug_token (touchpoint) | YES | Minor (ScanContext only) | Yes (list) | Med-High | Very Low | **KEEP — P1** |
| **`ship_days_ago`** | hug_token derived (touchpoint) | YES (ship_date) | Yes (compute at context) | Yes (range) | High | Low | **KEEP — P1** |
| `scan_index` | New D1 table needed | No | Yes (major) | Yes (range) | High | High | KEEP — v2 |
| `geo` | mart_customer_tier (customer) | No | No | Yes (list) | Mod | Low | DEFER |
| `order_value` | mart (customer) | No | No | Yes (range) | Low-Mod | Low | DEFER |
| `order_count` | mart (customer) | No | No | Yes (range) | Low | Low | DEFER |
| `day_of_week` | Runtime (touchpoint) | N/A | Yes (runtime) | Yes (list/range) | Low | Low | DEFER |
| `acquisition_source` | mart (customer) | No | No | Yes (list) | Low | Low | SKIP |
| Scan frequency cap | New D1 counter | No | Yes (major) | N/A (not targeting) | Med | High | SKIP (separate concern) |

---

## 6. Top Recommendations

### Priority 1: `sku` Targeting (catalog-only, zero infra cost)

`sku` is already in `hug_token` D1 (`schema_hug.sql:22`), already in `ScanContext` (`hug-handler.ts:89`), and the list matcher handles it. The only change is adding it to `TARGETING_CATALOG` with `touchpoint_level=True` and updating `validate_targeting`. This unlocks product-based routing (premium SKU → premium offer; low-margin SKU → no voucher) which directly serves the voucher guard economics (`discussion-hug.md §9`). Zero Worker deployment needed, zero D1 migration. Implement in an afternoon.

### Priority 2: `not_in` Negation Operator

Without negation, excluding B2B accounts (WHOLESALE/STAFF/KOL) from retail campaigns requires enumerating all valid retail tiers in a positive list — fragile as new tiers are added. Adding `{"not_in": [...]}` as an object-rule branch in `matchesTargeting` (and its Python mirror) is ~10 lines of code across 2 files + catalog validator. This pairs directly with `customer_type` (P1) — the canonical use case is `{"customer_type": {"not_in": ["WHOLESALE", "STAFF", "KOL"]}}`. Both must land together.

### Priority 3: `customer_type` + `batch_id` (low-cost schema additions)

`customer_type` needs: 1 new column in `hug_customer` D1, add to `customer_push._build_edge_rows` and `_content_str`, add to catalog. `batch_id` needs: 1 line in `ScanContext` build (`handleHugScan`), add to catalog with `touchpoint_level=True`. Both are under-an-hour changes each. Together they unlock B2B exclusion and cohort-level routing — both real operational needs.

### Explicitly NOT recommended now

- **`scan_index`**: Real value but wrong time. The hot-path D1 write is a latency risk, and the sibling match-count-preview investigation must first establish whether per-token event counting is feasible in D1 without Durable Objects. Block this on that outcome.
- **`order_value`**: Redundant with `value_group`. Add only when a campaign specifically fails because `value_group` buckets are too coarse.
- **Disjunctive range / multiple range operators**: YAGNI. Workaround (multiple campaigns same destination) is clean.
- **`geo`**: Not worth the push complexity until a geo-specific physical event campaign is planned.

---

## 7. Architectural Notes

1. **Nightly push content-diff** (`customer_push.py:183-189`, `_content_str`) must include any new customer-level field added to `hug_customer` — otherwise the push diff will miss changes to the new field even when tier/recency are unchanged.

2. **Preview limitation unchanged**: all new touchpoint_level attrs (`sku`, `batch_id`, `ship_days_ago`) remain upper-bound-only in `preview_match_customers` (`targeting_engine.py:31-33`). The preview docstring already documents this; no change needed, but the sibling investigation on match-count-preview should flag that `ship_days_ago` is particularly hard to preview meaningfully (depends on token distribution, not customer segments).

3. **`not_in` in Python mirror**: `targeting_engine.py` is the authoritative Python port. Any new operator shape added to `matchesTargeting` in TS MUST be replicated there (`targeting_engine.py:3-9` states this explicitly). The module docstring maps each TS line to its Python equivalent — maintain that mapping for `not_in`.

4. **`campaign_hint` suppression**: `hug_token.campaign_hint` (`schema_hug.sql:21`) exists but is NOT in ScanContext (`hug-handler.ts:232-243`). This is intentional — the hint field was meant for pack-time operator suggestion, not runtime routing. The campaign selection algorithm uses priority + targeting, not hints. Leave this out of targeting.

---

## Unresolved Questions

1. **scan_index feasibility**: Does the sibling match-count-preview investigation conclude that D1 can sustain atomic per-token scan counters without Durable Objects? This blocks the highest-value deferred attr.

2. **`not_in` in admin UI**: The CRM rule-builder uses dropdowns (discussion-hug.md §7). How does the admin UI expose `not_in` vs the existing list (OR) rule? Is this a tag-list with an "include/exclude" toggle, or a separate field type? UI design must happen before implementation.

3. **`customer_type` data quality**: Memory ref notes ~92 RETAIL-labeled Đại-Lý dealers leak into RETAIL. For B2B exclusion via `customer_type`, this leakage means a small number of dealer accounts would still receive retail campaigns. Acceptable for v1, but worth monitoring.

4. **Campaign cache TTL vs schedule constraints**: Adding time-sensitive criteria (`day_of_week`, or strict schedule windows) conflicts with the 60s campaign cache (`CAMPAIGN_CACHE_TTL_MS = 60_000`, `hug-handler.ts:98`). A campaign scheduled to start at 18:00:00 may not activate until 18:01:00. Is this acceptable? Documented but not resolved.

5. **`sku` domain values**: `TARGETING_CATALOG` requires a fixed `values` domain for list attrs (used by the validator). `sku` values are not a closed set — new SKUs are added continuously. Should the validator skip domain-checking for `sku` (i.e., `values: None`), or maintain a pushed SKU list? The catalog spec (`targeting_catalog.py:9`) allows open lists (domain check only if `values` is defined).
