# Impact Analysis: source_type & customer_segment Changes

> **Date:** 2026-04-18
> **Status:** Analysis Complete
> **Risk Level:** MEDIUM

## Executive Summary

Implementing the source_type normalization plan affects **2 layers** of the pipeline. Most importantly, there's a **naming collision** between two different `customer_segment` fields that must be addressed.

---

## 1. Naming Collision Discovery

**Critical finding:** Two different fields named `customer_segment` exist with different meanings:

| Entity | Field | Values | Purpose |
|--------|-------|--------|---------|
| `dim_channels` | customer_segment | B2C, B2B | Channel's target market |
| `dim_customers` | customer_segment | VIP, Loyal, Regular | Customer value tier |

**Problem:** This creates confusion and makes schema changes risky.

**Recommendation:** 
- dim_channels.customer_segment → rename to `market_segment` or deprecate entirely
- dim_customers.customer_segment → rename to `value_group` (aligns with customer-segmentation.md)

---

## 2. Pipeline Impact Chain

### Adding source_type (SAFE)

```
ref_order_sources.csv  →  dim_channels.sql  →  (downstream marts)
        ↓                       ↓
    ADD COLUMN              ADD COLUMN
    source_type             source_type
        ↓                       ↓
      NO BREAKING CHANGES - ADDITIVE ONLY
```

**Affected files:**
- `transformation/seeds/ref_order_sources.csv` — add column
- `transformation/models/marts/core/dim_channels.sql` — add to SELECT
- `transformation/models/marts/schema.yml` — document new column

**Impact:** NONE — purely additive change.

---

### Removing dim_channels.customer_segment (BREAKING)

```
ref_order_sources.csv  →  dim_channels.sql  →  rill/orders_enriched.sql  →  METABASE
        ↓                       ↓                        ↓
  REMOVE COLUMN            REMOVE COLUMN          ❌ COLUMN NOT FOUND
                                                       ↓
                                             marketing_monthly_analysis
                                             "Revenue by Customer Segment"
                                             (B2C/B2B pie chart)
```

**Pipeline stops at:** `rill/models/orders_enriched.sql` (line 17)

**Directly affected:**

| File | Line | Usage | Action Required |
|------|------|-------|-----------------|
| `rill/models/orders_enriched.sql` | 17 | `c.customer_segment` | Remove or replace |
| `docs/analytics-handbook/blueprints/marketing_monthly_analysis.md` | 717-727 | B2C/B2B revenue split | Remove or use alternative |
| `transformation/models/marts/schema.yml` | 75-77 | Documentation | Remove |

**Indirectly affected (blueprints - docs only):**
- `channel_classification_implementation_prompt.md` — update instructions
- `marketing_monthly_analysis playbook` — update data source note

---

### Renaming dim_customers.customer_segment (OPTIONAL BUT RECOMMENDED)

If renamed to `value_group`:

```
dim_customers.sql  →  Multiple Blueprints
       ↓                     ↓
  RENAME COLUMN        ❌ COLUMN NOT FOUND
  customer_segment           ↓
  → value_group      customer_operational_dashboard
                     customer_intelligence_monthly
                     customer_retention_dashboard
                     ceo_monthly_scorecard
                     sales_daily_operation
                     sales_yesterday_operation
```

**Affected blueprints (all use VIP/Loyal/Regular):**
- `customer_operational_dashboard.md` — 6 queries
- `customer_intelligence_monthly.md` — 12 queries
- `customer_retention_dashboard.md` — 6 queries
- `ceo_monthly_scorecard.md` — 2 queries
- `sales_daily_operation.md` — 1 query
- `sales_yesterday_operation.md` — 1 query
- `marketing_monthly_analysis.md` — 1 query (line 1124)

**Total: ~29 SQL queries in blueprints**

---

## 3. Recommended Phased Approach

### Phase 1: Add source_type (SAFE)
- Add column to seed
- Update dim_channels.sql
- Update schema.yml
- **No breaking changes**

### Phase 2: Deprecate dim_channels.customer_segment (MEDIUM RISK)
1. Check if B2C/B2B split is actually needed in any dashboard
2. If needed: derive from `source_type` or `channel_format` instead
   - `channel_format = 'B2B'` → B2B
   - Everything else → B2C
3. Update rill/orders_enriched.sql:
   - Option A: Remove `customer_segment` column
   - Option B: Derive: `CASE WHEN c.channel_format = 'B2B' THEN 'B2B' ELSE 'B2C' END`
4. Update marketing_monthly_analysis blueprint

### Phase 3: Rename dim_customers.customer_segment → value_group (DEFER)
- **Recommendation:** DEFER this change
- Current naming works, just documented differently
- If changed: requires updating 29+ SQL queries in blueprints
- Can be done later as part of broader customer segmentation implementation

---

## 4. Summary Matrix

| Change | Risk | Pipeline Impact | Files Changed | Dashboards Affected |
|--------|------|-----------------|---------------|---------------------|
| Add source_type | LOW | None | 3 | 0 |
| Remove dim_channels.customer_segment | MEDIUM | Stops at Rill | 4 | 1 (B2C/B2B chart) |
| Rename dim_customers.customer_segment | HIGH | Stops at Metabase | 7+ | 6 dashboards, ~29 queries |

---

## 5. Decision Points

1. **Is B2C/B2B revenue split analysis still needed?**
   - If YES: Derive from `channel_format` instead
   - If NO: Simply remove

2. **Should we rename dim_customers.customer_segment → value_group now?**
   - If YES: Budget time to update ~29 queries
   - If NO: Document the naming discrepancy, fix later

3. **Is rill/orders_enriched.sql actively used?**
   - If YES: Must update before removing column
   - If NO: Safe to break temporarily

---

## 6. Unresolved Questions

1. Is the "Revenue by Customer Segment (B2C/B2B)" chart in marketing_monthly_analysis actually deployed to Metabase?
2. Are there any ad-hoc queries in Metabase using dim_channels.customer_segment?
3. Should we keep backward compatibility with an alias/view?
