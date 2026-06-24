# Plan: Marketing Spend Pipeline — MISA as Baseline, Sheet as Override

> Created: 2026-06-09
> Status: Backlog
> Origin: `docs/analytics-handbook/guides/analytics_improvement_opportunities.md` § Marketing Attribution
> (updated 2026-06-24: untouched by 260623 audit work; MISA account_ledger available but transformation layer not built)

---

## Objective

Build `fact_marketing_spend` from MISA account_ledger as the primary source (monthly totals, audited).
Google Sheet remains optional — when sheet data exists for a month/channel, it overrides MISA with campaign-level detail.

---

## Background

### What this unlocks

- Blended ROAS per channel per month (from day 1, no manual entry required)
- Monthly spend trend (Facebook, Shopee Ads)
- Spend % of revenue
- Campaign-level ROAS and CAC when Sheet data is provided
- Cohort retention by acquisition source (longer term)
- Budget reallocation recommendations

### Why MISA first

`fact_marketing_spend` currently has **8 rows of seed/test data** from a Google Sheet.
MISA `account_ledger` already contains real, audited monthly spend:

| MISA Account | Description | treatment |
|---|---|---|
| `642172` | Quảng cáo Facebook | `keep_marketing` → `media_facebook` |
| `642175` | Hỗ trợ QC + phí web EDI | `keep_selling` → `media_shopee_ads` |

MISA data already flows through `std_misa_account_ledger` (monthly rollup per account).
No new ingestion needed — only transformation layer additions.

---

## Architecture

```
std_misa_account_ledger          src_marketing_spend_raw (gsheet)
  642172 → media_facebook           campaign-level, daily, optional
  642175 → media_shopee_ads
         ↓                                   ↓
int_marketing_spend_misa         int_marketing_spend_sheet
  1 row / (spend_code, month)      N rows / (campaign, date)
  data_source = 'misa'             data_source = 'sheet'
                    ↓                    ↓
                  fact_marketing_spend

                  Priority rule:
                  Sheet covers (spend_code, month)?
                    YES → keep sheet rows, suppress MISA for that month
                    NO  → use MISA monthly total
```

### Merge rule

- MISA provides a monthly total for every month it has data
- Sheet overrides at month granularity: if sheet has ANY rows for `(spend_code, month)` → MISA row for that month is suppressed
- `data_source` column always shows which source is active

---

## Implementation Steps

### Phase 1 — MISA baseline (no Sheet dependency)

**1. Create `int_marketing_spend_misa.sql`**

```sql
{{ config(materialized='view', tags=['int', 'marketing']) }}

SELECT
    period_month,
    CASE account
        WHEN '642172' THEN 'media_facebook'
        WHEN '642175' THEN 'media_shopee_ads'
    END                 AS spend_code,
    net_cost            AS spend_amount,
    NULL::VARCHAR       AS campaign_id,
    NULL::INTEGER       AS clicks,
    NULL::INTEGER       AS impressions,
    'misa'              AS data_source
FROM {{ ref('std_misa_account_ledger') }}
WHERE account IN ('642172', '642175')
  AND net_cost > 0
```

**2. Update `fact_marketing_spend.sql`**

```sql
WITH misa AS (SELECT * FROM {{ ref('int_marketing_spend_misa') }}),

sheet AS (
    SELECT
        DATE_TRUNC('month', date::DATE) AS period_month,
        spend_code,
        spend_amount,
        campaign_id,
        clicks,
        impressions,
        'sheet' AS data_source
    FROM {{ ref('src_marketing_spend_raw') }}
),

sheet_covered AS (
    SELECT DISTINCT spend_code, period_month FROM sheet
),

combined AS (
    SELECT * FROM sheet

    UNION ALL

    SELECT * FROM misa
    WHERE NOT EXISTS (
        SELECT 1 FROM sheet_covered s
        WHERE s.spend_code = misa.spend_code
          AND s.period_month = misa.period_month
    )
)

SELECT
    {{ dbt_utils.generate_surrogate_key(['spend_code', 'period_month', 'campaign_id']) }} AS spend_key,
    period_month,
    spend_code,
    spend_amount,
    campaign_id,
    clicks,
    impressions,
    data_source
FROM combined
```

### Phase 2 — Channel join (ROAS calculation)

Add `dim_channels` join so `spend_code` maps to `channel_key`:

| spend_code | channel_key examples |
|---|---|
| `media_facebook` | Facebook channels |
| `media_shopee_ads` | Shopee channels |

Needed for: `ROAS = SUM(net_revenue WHERE channel_key IN (...)) / spend_amount`

### Phase 3 — Dashboard (Marketing ROI blueprint)

Wire into `marketing_roi.md` blueprint:
- Monthly spend trend card
- Blended ROAS card (revenue / spend, per channel)
- Spend % of revenue
- `data_source` indicator on cards (MISA vs Sheet)

---

## Caveats

**No double-counting risk:** `642172` is used in 2 places:
1. `int_overhead_pool_monthly` → cost allocation per order (fully-loaded margin)
2. `fact_marketing_spend` → ROAS calculation

Different purpose, same source. Not additive — document in dashboard text cards.

**`642175` is MIXED:** `keep_selling` in overhead pool, mapped to `media_shopee_ads` here.
If Shopee platform fees are separated from actual ad spend in the future, reclassify.

**Sheet completeness unknown:** When sheet exists, it may not sum to MISA total.
Consider adding a reconciliation metric: `sheet_total / misa_total` per month.

---

## Status

- [ ] Phase 1: create `int_marketing_spend_misa.sql` + update `fact_marketing_spend.sql`
- [ ] Phase 2: add channel_key join + ROAS formula
- [ ] Phase 3: wire into Marketing ROI blueprint/dashboard
- [ ] Future: Sheet data entry workflow for campaign-level detail
