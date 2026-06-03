# Column & Model Naming Conventions

Canonical naming rules for the `transformation/` (dbt) layer. The `std_*` (standard/conformed) models are the **contract**: any new source version (e.g. Sapo v3) must produce these names. Locking the vocabulary here keeps dashboards, the serving layer, and `detailView` stable across source migrations.

Standards followed: Kimball dimensional modeling + dbt-labs style guide + e-commerce/finance domain terms.

## 1. Casing & general
- `snake_case` for all columns and model names. No camelCase, no spaces.
- No abbreviations: `birth_date` not `dob`, `gender` not `sex`, `quantity` not `qty` (in column names; `_qty` suffix allowed where it reads naturally).
- One concept per column; embed the unit when there is one: `weight_grams`, `time_to_complete_hours`, `recency_days`.

## 2. Identifiers (the key rule)
| Suffix | Meaning | Examples |
|---|---|---|
| `_key` | **surrogate key** (hashed/generated, joins facts↔dims) | `customer_key`, `channel_key`, `date_key`, `time_key` |
| `_id` | **system natural id** from the source (usually numeric/opaque) | `order_id`, `customer_id`, `product_id`, `variant_id` |
| `_code` | **human/business identifier that is ALPHANUMERIC** | `order_code` (`260316A6VJXGMT`), `sku`, `customer_code`, `brand_code` |
| `_number` | only when it is a strictly numeric sequence | (avoid for alphanumerics) |

> **`order_code` stays `order_code`** — it is an alphanumeric string (`260316A6VJXGMT`), not a number, so `order_number` would mislead. Same logic keeps `customer_code`, `brand_code`, `category_code`.
> Date dimension keys are "smart" integers `YYYYMMDD` (`date_key`), Kimball-style.
> Line-item degenerate key is `order_line_id` (not the ambiguous `item_id`).

## 3. Timestamps, dates, durations
- Event timestamps (TIMESTAMPTZ, UTC-native — see [[project_timezone_architecture]]): suffix **`_at`** → `created_at`, `ordered_at`, `shipped_at`, `paid_at`, `returned_at`, `cancelled_at`, `last_modified_at`, `extracted_at`.
- Calendar dates (DATE): suffix **`_date`** → `first_order_date`, `return_date`.
- Durations: suffix the unit → `_days`, `_hours` (`recency_days`, `time_to_complete_hours`).
- Do NOT use `_timestamp` (use `_at`) and do not leave a bare `last_modified`.

## 4. Money
- **Revenue / profit concepts → domain noun, no suffix:** `gross_revenue`, `net_revenue`, `total_collected`, `gross_profit`, `channel_net_profit`.
- **Line / cost / tax / refund amounts → `_amount`:** `discount_amount`, `cogs_amount`, `refund_amount`, `vat_amount`, `cod_amount`.
- **VAT specifically → `vat_amount`** (the domain is Vietnamese 8/10% VAT; see [[project_sapo_vat_inclusive_pricing]]). Reserve `tax_` only for genuine non-VAT taxes (e.g. US sales tax, Shopee `personal_income_tax`).
- Spend by a customer is `total_spend` (NOT `total_expense` — expense = a cost to the business).
- Currency is VND unless a `currency_code` column says otherwise.

## 5. Ratios, rates, counts, booleans
- **Margins / percentages → `_pct`** (stored as a 0..1 fraction): `gross_margin_pct`, `channel_net_margin_pct`.
- **Behavioral rates → `_rate`** (also 0..1): `cancel_rate`, `discount_rate`, `discount_order_rate`.
- **Counts → `_count`:** `order_count` (not `total_orders_count`), `return_count`, `misa_line_count`.
- **Booleans → `is_` / `has_`:** `is_active` (not `is_active_status`), `is_taxable`, `has_cogs`, `has_returns`.

## 6. Types & lineage
- Categorical "kind of X" columns → `_type` (NOT `_nature`): `discount_type`, `payment_method_type`, `return_status`.
- Lineage/metadata columns: `source_system` ('sapo', 'misa', 'shopee'), `source_version` ('v2' / 'v3'), `source_record`, `extracted_at`.
- Source-specific columns keep a system prefix: `misa_join_key`, `shopee_net_settlement`.

## 7. Models
- `src_<source>_<entity>` (raw extract, incremental) · `stg_<source>_<entity>` (enrich, view) · `std_<entity>` (conformed contract, source-agnostic) · `int_<desc>` (business logic) · `dim_<entity>` / `fact_<process>` (marts).
- **Source version = a `_v<N>` SUFFIX** on the src/stg model files: `src_sapo_orders_v2`, `stg_sapo_orders_v2` (and later `src_sapo_orders_v3`, `stg_sapo_orders_v3`). Suffix (not infix) keeps all variants of one entity adjacent.
- `std_<entity>` is the conformance contract: it UNIONs the versions and **never carries a version suffix** — it is the stable, source-agnostic interface every downstream model reads.

## 8. Canonical glossary (order/revenue domain — v3 must conform)
| Term | Definition |
|---|---|
| `gross_revenue` | giá bán × qty before discount, VAT-inclusive |
| `discount_amount` | total discount |
| `total_collected` | cash the customer pays = VAT-inclusive amount after discount (Sapo `$.total`) |
| `vat_amount` | embedded VAT (Sapo `$.total_tax`; 8/108 or 10/110) |
| `net_revenue` | revenue after discount, **VAT-excluded** = `total_collected − vat_amount` (P&L line) |
| `cogs_amount` | cost of goods sold (MISA), VAT-exclusive |
| `gross_profit` | `net_revenue − cogs_amount` |
| `channel_net_profit` | `gross_profit − platform_fees` |

See [[project_sapo_vat_inclusive_pricing]] and `docs/analytics-handbook/guides/revenue_terminology.md`.
