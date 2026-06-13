# Engagement Domain Schema Scan — Chat, Ads, Channel, Staff
**Scan date:** 2026-06-13 | **Repo:** data-integration | **Branch:** main

---

## 1. Chat / Conversation (Facebook Messenger)

All 4 models are `enabled=false` — scaffolded but never materialized. No live data.

### dim_fb_conversations
| Field | Type | Note |
|---|---|---|
| thread_id | VARCHAR | PK — raw FB conversation `id` |
| updated_time | TIMESTAMP | Last activity |
| message_count | INTEGER | |
| snippet | VARCHAR | Last message preview |
| participants | JSON | NOT flattened; page_id + PSID buried here |

### fact_fb_messages
| Field | Type | Note |
|---|---|---|
| message_id | VARCHAR | PK — raw FB message `id` |
| thread_id | VARCHAR | FK → dim_fb_conversations |
| created_time | TIMESTAMP | |
| content_length_chars | INTEGER | Original content stripped from mart |
| sender_info | JSON/VARCHAR | Raw `from` field (id + name) |

**Grain:** dim_fb_conversations = 1 row/thread; fact_fb_messages = 1 row/message.

**Customer linkage:** ABSENT. No `customer_id`, `phone`, or `sapo_customer_id` in any FB Messenger model. The `participants` column is unexploded JSON. To link a Messenger thread to a Sapo customer the CRM must implement its own PSID→phone→customer_id resolution; no bridge exists in this warehouse.

---

## 2. Facebook Ads

All 5 models are `enabled=false` — scaffolded but never materialized. No live data.

### dim_fb_ads (joined dim: ad + ad_set + campaign)
| Field | Type | Note |
|---|---|---|
| ad_id | VARCHAR | PK — native FB ad id |
| ad_name | VARCHAR | |
| ad_status | VARCHAR | |
| campaign_id | VARCHAR | FK to campaign |
| campaign_name | VARCHAR | |
| campaign_objective | VARCHAR | |
| adset_id | VARCHAR | FK to ad set |
| adset_name | VARCHAR | |

### fact_fb_ads_insights_daily
| Field | Type | Note |
|---|---|---|
| date | DATE | |
| ad_id | VARCHAR | FK → dim_fb_ads |
| adset_id | VARCHAR | |
| campaign_id | VARCHAR | |
| account_id | VARCHAR | |
| spend | DECIMAL | |
| impressions | INTEGER | |
| clicks | INTEGER | |
| reach | INTEGER | |
| frequency | FLOAT | |

**Grain:** 1 row per (date, ad_id).

**Order/customer linkage:** ABSENT. No conversion events, order_id, customer_id, or click-through attribution. Ads data stops at impressions/clicks/spend — no downstream order or customer join path in this warehouse.

**No staging schema.yml files** exist for either facebook_messenger or facebook_ads. The source tables (`facebook_messenger.conversations`, `facebook_messenger.messages`, `facebook_ads.ads`, `facebook_ads.ad_sets`, `facebook_ads.campaigns`, `facebook_ads.insights`) are declared as dbt sources but no source YAML was found — these may rely on a missing `sources.yml` under those sub-directories.

---

## 3. Marketing Spend (fact_marketing_spend)

**Status:** LIVE (enabled, materialized as parquet).

| Field | Type | Note |
|---|---|---|
| spend_key | VARCHAR | PK — surrogate from (date, spend_code, campaign_id) |
| date_key | INTEGER | YYYYMMDD |
| channel_key | VARCHAR | FK → dim_channels (via source_id + location_id) |
| spend_code | VARCHAR | FK → ref_spend_category |
| campaign_id | VARCHAR | Free-text optional field; NOT linked to dim_fb_ads |
| spend_amount | DECIMAL | VND |
| clicks | INTEGER | Optional |
| impressions | INTEGER | Optional |

**Spend categories (ref_spend_category.csv):** 29 codes across cost_groups: Media (Facebook, Google, TikTok, Shopee, Lazada, others), KOLs (booking/production), PR, Seeding, Production (video/image/content/model), POSM, Software (CRM/design/marketing/data), Affiliate (network/partner), Opex (bonus/training/event/travel).

**Source:** Google Sheet → parquet ingestion via `gsheet_marketing_spend.py`. Dropdown-constrained input (spend_category_name → code; channel_name → source_id + location_id).

**Attribution depth:** spend → channel only. The `campaign_id` is a free-text string — not a FK to any FB Ads dimension. No order-level ROI attribution exists.

---

## 4. Channel Dimension (dim_channels)

**Status:** LIVE.

| Field | Type | Note |
|---|---|---|
| channel_key | VARCHAR | PK — surrogate(source_id, location_id) |
| channel_name | VARCHAR | Display name |
| channel_code | VARCHAR | Short code |
| channel_category | VARCHAR | Online-Ecommerce / Offline / Internal |
| channel_format | VARCHAR | Marketplace / Social / Web / Retail / B2B / Direct / System / CrossBorder Fulfillment / Other |
| platform | VARCHAR | Facebook / Shopee / TikTok / POS / etc. |
| channel_brand | VARCHAR | Brand that owns the channel |
| market | VARCHAR | Domestic / Export |
| source_type | VARCHAR | channel / customer_type / purpose / arrangement |
| is_sales_channel | BOOLEAN | Excludes System/Internal |
| is_marketplace | BOOLEAN | Third-party marketplace flag |
| source_id | VARCHAR | Sapo order_source id (FK to ref_order_sources) |
| location_id | VARCHAR | Sapo branch_location id (for POS channels) |
| is_active | BOOLEAN | |

**ref_order_sources.csv channels:** 47 rows. Notable social: Facebook (id 3988153), Zalo (3988154), Instagram (4461848), FaceBookJPC (8075218), FaceBookFJPTViet (8075219). Facebook channels use format=Social, platform=Facebook.

**MISA channel codes (ref_misa_channel_codes.csv):** 5 codes only (DAILY, ECOM, CS, KHAC, UNKNOWN) — minimal mapping, not used for customer attribution.

**Linkage to orders:** `fact_orders.channel_key` → `dim_channels.channel_key` (solid, tested).

---

## 5. Staff Dimension (dim_staff)

**Status:** LIVE.

| Field | Type | Note |
|---|---|---|
| staff_key | VARCHAR | PK — surrogate(account_id) |
| staff_id | VARCHAR | Native Sapo account_id |
| full_name | VARCHAR | |
| email | VARCHAR | Business key — used for team lookup |
| phone_number | VARCHAR | |

**Source:** `std_accounts` ← `stg_sapo_v2_accounts` ← Sapo Accounts API.

**Linkage to orders:** `fact_orders.seller_staff_key` / `creator_staff_key` → `dim_staff.staff_key`. Primary attribution = seller (assignee); creator = operational fallback. Tested in schema.yml.

---

## 6. Teams Dimension (dim_teams)

**Status:** LIVE.

| Field | Type | Note |
|---|---|---|
| team_key | VARCHAR | PK — surrogate(team_code) |
| team_code | VARCHAR | BK from Google Sheet |
| team_name | VARCHAR | |
| revenue_type | VARCHAR | member / platform / channel_name (drives revenue aggregation logic) |
| revenue_filter | VARCHAR | Comma-separated values for platform/channel_name types |
| leader_email | VARCHAR | |
| active_member_count | INTEGER | Derived from stg_team_members |

**Team membership (stg_team_members):** SCD2 table keyed by (staff_email, team_code, effective_from). Join: `fact_orders.seller_staff_key` → `dim_staff.email` → `stg_team_members.staff_email` → `dim_teams.team_code`. This SCD2 path is what populates `fact_orders.team_key`.

---

## 7. Targets (fact_targets + dim_channel_targets)

### fact_targets
**Grain:** 1 row per (staff/branch/channel/product × cycle × metric). Keys: target_key, target_code, date_key, branch_key, staff_key, channel_key, product_key, team_code (raw, not FK yet).

### dim_channel_targets
**Grain:** 1 row per (channel_key, period_month, metric_type, target_source). metric_type: NET_REVENUE / NET_MARGIN_PCT / ORDER_COUNT. target_source: BUDGET / STRETCH / MIN_VIABLE.

---

## 8. Linkage Map

### Conversation → Customer
```
FB thread (thread_id)
  → participants JSON (PSID + page_id)    ← UNEXPLODED, no bridge
  → ??? phone number
  → dim_customers.phone
  → dim_customers.customer_key
```
**Status: BROKEN / GAP.** No PSID→customer resolution exists anywhere in the warehouse. All Messenger models are disabled stubs.

### Ad → Order
```
fact_fb_ads_insights_daily.ad_id / campaign_id
  → (no FK to orders)
  → fact_marketing_spend.campaign_id     ← free-text only, not a real FK
  → fact_orders                          ← NO join path
```
**Status: BROKEN / GAP.** FB Ads are disabled stubs. Even if enabled, there is no click-through or conversion attribution linking ad spend to order_id or customer_key.

### Staff → Order
```
fact_orders.seller_staff_key
  → dim_staff.staff_key                  ← solid, tested
fact_orders.team_key
  → dim_teams.team_key                   ← solid, via SCD2 team_members
```
**Status: SOLID.** Both individual and team attribution are operational.

### Channel → Order
```
fact_orders.channel_key
  → dim_channels.channel_key             ← solid, tested
fact_marketing_spend.channel_key
  → dim_channels.channel_key             ← solid
```
**Status: SOLID.**

### Marketing Spend → Order (ROI)
```
fact_marketing_spend (channel_key, date_key, campaign_id)
  → dim_channels (channel_key)
  → fact_orders (channel_key + date_key)
```
**Status: WEAK.** Can correlate spend vs revenue at channel+date grain only. No true attribution (impression→click→order). `campaign_id` is a free-text label, not a structural FK.

---

## 9. CRM Design Gaps & Observations

| Gap | Severity | Detail |
|---|---|---|
| No PSID→customer bridge | Critical | CRM must build its own FB PSID → phone → sapo_customer_id resolution table |
| FB Messenger models all disabled | Critical | The `enabled=false` stubs have schema errors: `participants` unexploded, `content` stripped in mart, `conversation_id` commented as "assuming dlt links this" — source schema not confirmed |
| FB Ads all disabled | High | Scaffold only; no source YAML, no ingestion pipeline confirmed |
| Ad→Order attribution absent | High | No click/conversion tracking; spend analytics limited to channel+date grain |
| `campaign_id` on marketing_spend is free-text | Medium | Cannot FK join to FB Ads dimension even if both are enabled |
| Staff has no role/permission field | Low | dim_staff has name/email/phone only; no role, department, or access level for CRM RBAC |
| Teams: `team_code` not FK in fact_targets | Low | `fact_targets.team_code` is raw VARCHAR, not resolved to team_key |
| No staff→conversation link | Critical | For CRM inbox assignment, the CRM needs a `assigned_staff_id` on conversations — absent in current schema |

---

## Open Questions

1. Is there an existing PSID→phone mapping in any ingestion pipeline (dlt, Python scripts) outside the dbt layer? Check `ingestion/` directory.
2. Has the FB Messenger API ingestion (dlt pipeline) ever run? The source tables in dbt sources may point to non-existent raw tables.
3. Does `fact_marketing_spend.campaign_id` currently carry FB Ads `campaign_id` values, or is it always NULL/custom labels? If FB Ads is enabled, this field is the only possible join bridge.
4. What is the intended FB Ads ingestion method? The staging models reference `source('facebook_ads', 'ads')` etc. — is this via dlt, Airbyte, or manual CSV?
5. For CRM staff assignment, will the CRM create its own staff table (synced from Sapo accounts) or reference `dim_staff` directly?
6. `dim_channels` has `platform=Facebook` channels (id 3988153, 8075218, 8075219). Are these for order source tracking only, or intended to link to Messenger conversations? Currently no structural bridge.
