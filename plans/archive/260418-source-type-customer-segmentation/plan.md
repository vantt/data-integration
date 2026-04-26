# Plan: Source Type & Customer Segmentation Normalization

> **Created:** 2026-04-18
> **Status:** Complete
> **Owner:** Data Team

## Overview

Normalize Sapo's overloaded `source` field by adding `source_type` classification and clarify customer segmentation across the data model.

## Context

**Problem:** Sapo `source` field mixes 5 concepts:
- Channel (Shopee, Zalo, POS)
- Customer Type (Đại Lý, Chợ sỉ)
- Team (CS, Telesale)
- Order Purpose (Test SP, Quà Tặng)
- Business Arrangement (US CrossBorder)

**Solution:** Add `source_type` field to explicitly classify each source.

## Related Documents

- [data-model-overview.md](../../docs/context/data-model-overview.md) — Master overview
- [channel-classification.md](../../docs/context/channel-classification.md) — Section 7 updated
- [customer-segmentation.md](../../docs/context/customer-segmentation.md) — 8 dimensions clarified
- [team-management.md](../../docs/context/team-management.md) — Team attribution reference

---

## Phase 1: Seed Data Updates

**Status:** DONE
**Files:** `transformation/seeds/ref_order_sources.csv`

### Tasks

- [x] Add `source_type` column with values: `channel`, `customer_type`, `team`, `purpose`, `arrangement`
- [x] Remove deprecated `customer_segment` column
- [x] Classify all existing sources

### source_type Values

| source_type | Description | Example Sources |
|-------------|-------------|-----------------|
| `channel` | Actual sales channel | Shopee, Zalo, POS, Web, CS, Telesale |
| `customer_type` | Customer relationship type | Đại Lý, Chợ sỉ |
| `purpose` | Special order purpose | Test SP, Quà Tặng, Ưu đãi NV |
| `arrangement` | Business arrangement | US (CrossBorder) |

> **Note:** CS and Telesale classified as `channel` — they represent order acquisition paths, not internal team attribution.

---

## Phase 2: dbt Model Updates

**Status:** DONE
**Files:** `transformation/models/marts/core/`

### Tasks

- [x] Update `dim_channels.sql` to use `source_type` instead of `customer_segment`
- [x] Update `dim_customers.sql` to use `value_group` instead of `customer_segment`
- [x] Update `rill/models/orders_enriched.sql`
- [x] Update `transformation/models/marts/schema.yml`
- [x] Update `transformation/seeds/properties.yml`
- [x] Update `transformation/dbt_project.yml`

### dim_channels Schema Change

```diff
  dim_channels:
    channel_key
    channel_category      -- tier 1
    channel_format        -- tier 2
    platform              -- tier 3
    channel_name          -- tier 4
+   source_type           -- NEW: channel, customer_type, team, purpose, arrangement
-   customer_segment      -- REMOVED: wrong entity placement
```

### dim_customers Schema Change

```diff
  dim_customers:
-   customer_segment      -- REMOVED: VIP/Loyal/Regular
+   value_group           -- NEW: VALUE_VIP/VALUE_GOLD/VALUE_SILVER/VALUE_BRONZE
    customer_status       -- unchanged: Active/At Risk/Churned
```

---

## Phase 3: Documentation & Blueprints

**Status:** DONE
**Files:** Multiple docs and blueprints

### Completed

- [x] `docs/context/customer-segmentation.md` — Renamed PRICING → customer_type, updated 8 dimensions
- [x] `docs/context/data-model-overview.md` — Created master overview
- [x] `docs/context/channel-classification.md` — Updated source_type documentation
- [x] `docs/analytics-handbook/domains/customer.md` — Updated thresholds
- [x] `docs/analytics-handbook/guides/channel_classification_implementation_prompt.md` — Updated schema

### Blueprint Updates (8 files)

- [x] `customer_operational_dashboard.md`
- [x] `customer_intelligence_monthly.md`
- [x] `customer_retention_dashboard.md`
- [x] `ceo_monthly_scorecard.md`
- [x] `sales_daily_operation.md`
- [x] `sales_yesterday_operation.md`
- [x] `sales_monthly_review.md`
- [x] `marketing_monthly_analysis.md`

### 8 Dimensions Summary

| Dimension | Field | Type | Values |
|-----------|-------|------|--------|
| Customer Type | `customer_type` | Manual | RETAIL, WHOLESALE, PARTNER, STAFF, KOL |
| Value | `value_group` | Auto | VALUE_VIP, VALUE_GOLD, VALUE_SILVER, VALUE_BRONZE |
| Lifecycle | `lifecycle_stage` | Auto | NEW, ACTIVE, AT_RISK, CHURNED |
| Channel | `channel_preference` | Auto | SOCIAL, MARKETPLACE, DIRECT, OFFLINE |
| Product | `product_affinity` | Auto | FINE_JAPAN, FG_CARE, FINE_CARE, MULTI |
| Payment | `payment_behavior` | Auto | PREPAID, COD, CREDIT, DELINQUENT |
| Geo | `geo_region` | Auto | HCMC, HANOI, MEKONG, CENTRAL, OTHER |
| Source | `acquisition_source` | Manual | ORGANIC, ADS, REFERRAL, KOL, EVENT |

---

## Phase 4: Sapo Customer Group Setup (FUTURE)

**Status:** Not Started — Requires Sapo Admin Access
**Owner:** Sales + Data

### Tasks

- [ ] Chuẩn hóa RETAIL, WHOLESALE groups trong Sapo
- [ ] Tạo PARTNER, STAFF, KOL groups
- [ ] Cập nhật 12 khách sỉ ẩn → WHOLESALE
- [ ] Document policy: ai được approve chuyển customer_type?

> **Note:** This phase requires manual Sapo configuration, not code changes.

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking downstream queries | High | Run full dbt test suite before deploy |
| Sapo customer data loss | Medium | Backup before changes |
| Confusion between dimensions | Low | Clear documentation + FAQ |

---

## Success Criteria

1. [x] `source_type` column exists in seed and dim_channels
2. [x] `customer_segment` removed from dim_channels
3. [x] `customer_segment` renamed to `value_group` in dim_customers
4. [x] Customer segmentation docs use consistent `customer_type` naming
5. [x] All blueprints updated to use `value_group`
6. [x] dbt build passes — verified 2026-04-18 (14/14 tests pass)
7. [x] Metabase dashboards re-deployed — 8 dashboards updated

---

## Breaking Changes Summary

| Entity | Old Field | New Field | Old Values | New Values |
|--------|-----------|-----------|------------|------------|
| dim_channels | customer_segment | source_type | B2C, B2B | channel, customer_type, team, purpose, arrangement |
| dim_customers | customer_segment | value_group | VIP, Loyal, Regular | VALUE_VIP, VALUE_GOLD, VALUE_SILVER, VALUE_BRONZE |

**Threshold changes for value_group:**
- VALUE_VIP: >=50M OR >=20 orders (was VIP: >10M)
- VALUE_GOLD: >=20M (was Loyal: 5-10M)
- VALUE_SILVER: >=5M (new tier)
- VALUE_BRONZE: <5M (was Regular: <5M)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-18 | Initial plan created from discussion |
| 2026-04-18 | Implementation complete — all code & docs updated |
| 2026-04-18 | Verification complete — dbt build pass, 8 dashboards redeployed |
| 2026-04-18 | Playbooks updated — 7 files migrated from VIP/Loyal/Regular to value_group |
| 2026-04-18 | Note: CS/Telesale kept as source_type=channel (intentional — they are order acquisition channels) |
| 2026-04-18 | Rill updated — added source_type, channel_brand, market to all 3 models + 3 metrics views |
| 2026-04-18 | Design specs finalized — 5 files updated with VALUE_VIP/GOLD/SILVER/BRONZE terminology |
| 2026-04-18 | Blueprint series labels fixed — pie.colors and series_settings now match actual data values |
