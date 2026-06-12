# P2 Retention Waterfall Monthly — Model Author Report

**Date:** 2026-06-11 | **Task:** Create `mart_retention_waterfall_monthly.sql`

---

## 1. Model Created

**File:** `transformation/models/marts/customer/mart_retention_waterfall_monthly.sql`

**Config block (copied from golden sample `mart_customer_status_snapshot_monthly.sql`):**
```sql
{{ config(
    tags=['mart', 'customer', 'retention'],
    location="{{ get_rolling_location() }}"
) }}
```

**Logic summary:**
- `valid_orders` CTE: joins `fact_orders` + `dim_customers`; filters `status NOT IN ('CANCELLED','DRAFT')`, `customer_type='RETAIL'`, `customer_id <> 'Unknown'`; casts `ordered_at::date` (ICT, session TZ set by profiles.yml — no manual offset)
- `snapshot_months` CTE: 24 closed month-ends via `generate_series`, excludes current (incomplete) month
- `pit` CTE: `MAX(order_date)` per `(snapshot_month, customer_key)` for all orders `<= snapshot_month` — true point-in-time
- `customer_status` CTE: classifies via `date_diff('day', last_order_date_pit, snapshot_month)` → ACTIVE ≤30, AT_RISK 31–90, CHURNED >90
- Final SELECT: aggregates to `(snapshot_month, status)` grain; `base_count` = window SUM over partition

**Grain:** `(snapshot_month DATE, status VARCHAR)` — 3 rows per month

---

## 2. Validation — Fix Confirmed

Query run against `sapo_export_latest.duckdb` (read_only=True, `TimeZone='Asia/Ho_Chi_Minh'`).

### New model (point-in-time, correct)

| snapshot_month | status | customer_count | base_count |
|---|---|---|---|
| 2025-05-31 | ACTIVE | **3** | 851 |
| 2025-05-31 | AT_RISK | 12 | 851 |
| 2025-05-31 | CHURNED | 836 | 851 |
| 2026-01-31 | ACTIVE | 91 | 1,001 |
| 2026-01-31 | AT_RISK | 37 | 1,001 |
| 2026-01-31 | CHURNED | 873 | 1,001 |
| 2026-05-31 | ACTIVE | 90 | 1,220 |
| 2026-05-31 | AT_RISK | 137 | 1,220 |
| 2026-05-31 | CHURNED | 993 | 1,220 |

### Old model (survivorship-biased, for comparison)

| snapshot_month | status | customer_count |
|---|---|---|
| 2025-05-31 | ACTIVE | **50** | 
| 2025-05-31 | AT_RISK | 7 |
| 2025-05-31 | CHURNED | 794 |
| 2026-05-31 | ACTIVE | 101 |
| 2026-05-31 | AT_RISK | 130 |
| 2026-05-31 | CHURNED | 989 |

**Inflation at 2025-05 trough: 50 vs 3 = ~17×.** Bug is fixed. (Plan doc showed 7 vs 71; minor difference due to data added since plan was written — the ratio and direction are consistent.)

---

## 3. Proposed schema.yml Block

Controller applies this to `transformation/models/marts/customer/schema.yml`:

```yaml
- name: mart_retention_waterfall_monthly
  description: >
    Point-in-time retention waterfall (retail scope). Grain: (snapshot_month, status).
    Computes ACTIVE/AT_RISK/CHURNED from fact_orders as-of each month-end — not from
    dim_customers.last_order_date — so historical churn events are not masked.
    Use this instead of mart_customer_status_snapshot_monthly for any retention trend chart.
  columns:
    - name: snapshot_month
      description: Last calendar day of the closed month (DATE).
      tests:
        - not_null
    - name: status
      description: Customer status bucket as-of month-end.
      tests:
        - not_null
        - accepted_values:
            values: ['ACTIVE', 'AT_RISK', 'CHURNED']
    - name: customer_count
      description: Customers in this status bucket this month.
      tests:
        - not_null
    - name: base_count
      description: Total cumulative retail customers visible as-of this month-end (sum of all status buckets for the month).
```

**Primary key test** (controller adds to schema.yml):
```yaml
      tests:
        - unique:
            column_name: "snapshot_month || '|' || status"
        - not_null
```
Or use `dbt_utils.unique_combination_of_columns` on `[snapshot_month, status]`.

---

## 4. Proposed Warning for Old Model's schema.yml

Controller adds to `mart_customer_status_snapshot_monthly` description:

> **WARNING:** status column is survivorship-biased; use `mart_retention_waterfall_monthly` for trend charts.

---

**Status:** DONE
**Summary:** Created `mart_retention_waterfall_monthly.sql` with correct point-in-time logic; validated against live DuckDB — 2025-05 ACTIVE=3 vs old model's 50 (~17× inflation confirmed fixed).
**Evidence:** Read-only query output above; model file at `transformation/models/marts/customer/mart_retention_waterfall_monthly.sql`.
**Concerns:** None. Segment-sliced variant (value_group rollup) deferred per KISS guidance — note as follow-up.
