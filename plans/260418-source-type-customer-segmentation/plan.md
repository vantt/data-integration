# Plan: Source Type & Customer Segmentation Normalization

> **Created:** 2026-04-18
> **Status:** Planning
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

**Status:** Not Started
**Files:** `transformation/seeds/sapo/ref_order_sources.csv`

### Tasks

- [ ] Add `source_type` column with values: `channel`, `customer_type`, `team`, `purpose`, `arrangement`
- [ ] Remove deprecated `customer_segment` column
- [ ] Classify all existing sources

### source_type Values

| source_type | Description | Example Sources |
|-------------|-------------|-----------------|
| `channel` | Actual sales channel | Shopee, Zalo, POS, Web |
| `customer_type` | Customer relationship type | Đại Lý, Chợ sỉ |
| `team` | Team/function handling | CS, Telesale |
| `purpose` | Special order purpose | Test SP, Quà Tặng, Ưu đãi NV |
| `arrangement` | Business arrangement | US (CrossBorder) |

---

## Phase 2: dbt Model Updates

**Status:** Not Started
**Files:** `transformation/models/staging/sapo/`

### Tasks

- [ ] Update `stg_ref_order_sources.sql` to include `source_type`
- [ ] Remove `customer_segment` from staging models
- [ ] Update `dim_channels` to include `source_type`
- [ ] Verify downstream models don't break

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

---

## Phase 3: Customer Segmentation Alignment

**Status:** Documentation Complete
**Files:** `docs/context/customer-segmentation.md`

### Completed

- [x] Rename PRICING dimension → `customer_type`
- [x] Update values: RETAIL, WHOLESALE, PARTNER, STAFF, KOL
- [x] Clarify VALUE_VIP is `value_group`, not `customer_type`
- [x] Update all 8 dimension field names
- [x] Add FAQ for customer_type vs value_group distinction

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

## Phase 4: Sapo Customer Group Setup

**Status:** Not Started
**Owner:** Sales + Data

### Tasks

- [ ] Chuẩn hóa RETAIL, WHOLESALE groups trong Sapo
- [ ] Tạo PARTNER, STAFF, KOL groups
- [ ] Cập nhật 12 khách sỉ ẩn → WHOLESALE
- [ ] Document policy: ai được approve chuyển customer_type?

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking downstream queries | High | Run full dbt test suite before deploy |
| Sapo customer data loss | Medium | Backup before changes |
| Confusion between dimensions | Low | Clear documentation + FAQ |

---

## Success Criteria

1. `source_type` column exists in seed and dim_channels
2. `customer_segment` removed from Channel entity
3. Customer segmentation docs use consistent `customer_type` naming
4. No breaking changes in existing dashboards/reports
5. dbt tests pass

---

## Changelog

| Date | Change |
|------|--------|
| 2026-04-18 | Initial plan created from discussion |
