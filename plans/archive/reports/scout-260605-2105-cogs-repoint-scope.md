# Scout Report: Phase-05 COGS Repoint Scope
**Date:** 2026-06-05 | **Author:** scout (read-only)

---

## Summary

- Order-P&L pipeline live. Current `fact_order_economics.cogs_amount` sources from MISA-632 interim filter (`int_misa_sales_lines WHERE cogs_account LIKE '632%'`), covering only **28% of FOE orders** (945/3,397 in latest snapshot). `int_order_cogs_reconciled` exists with `cogs_goods_primary` (var-driven, default `sapo_mac`) + `cogs_source` ('both'|'sapo_mac'|'misa'|'none'), coverage **79-89%**.
- Phase-05 = repoint `cogs_amount` from MISA-632 → `int_order_cogs_reconciled.cogs_goods_primary`; surface `cogs_source` string column.
- **Headline KPI delta (2026 orders):** COGS total increases **+1.16B VND (+185%)** (625M → 1.78B). Gross profit drops **~1.16B VND (−56%)** (2.05B → 895M). Channel net profit drops **~1.16B VND (−58%)**. This is a MATERIAL shift. **Business sign-off required before production deploy.**
- `fact_order_economics` does NOT yet ref `int_order_cogs_reconciled` → new DAG edge, restart required.

---

## A. Current COGS Wiring

### `fact_order_economics.sql` — COGS CTE (lines 29–40)

```sql
-- Aggregate MISA invoice lines to order level
misa_order AS (
    SELECT
        voucher_no AS order_code,
        SUM(cogs_amount)              AS cogs_amount,
        SUM(revenue_net_of_discount)  AS misa_revenue,
        SUM(gross_profit)             AS misa_gross_profit,
        COUNT(*)                      AS misa_line_count
    FROM {{ ref('int_misa_sales_lines') }}
    -- BUG-1: only TK632 = true COGS; exclude TK642 promo-goods
    WHERE cogs_account LIKE '632%'
    GROUP BY voucher_no
),
```

**SELECT (lines 104–108, 113, 139–145, 163–172):**
- `m.cogs_amount` → `cogs_amount`
- `m.cogs_amount IS NOT NULL AS has_cogs`
- `gross_profit` = `net_revenue - COALESCE(m.cogs_amount, 0)`
- `channel_net_profit` = `net_revenue - COALESCE(m.cogs_amount, 0) + shopee fees`
- `fully_loaded_net_profit` = `channel_net_profit - allocated_overhead`
- JOIN: `LEFT JOIN misa_order m ON o.order_code = m.order_code` (line 197)

**No reference to `int_order_cogs_reconciled` anywhere in marts/sales/.**

### `fact_order_costs.sql` — COGS CTE (lines 21–38)

```sql
cogs AS (
    SELECT
        om.order_id,
        m.voucher_no                        AS order_code,
        'cogs'                              AS cost_type,
        'COGS'                              AS cost_category,
        ABS(SUM(m.cogs_amount))             AS amount,
        'misa'                              AS source_system,
        ...
    FROM {{ ref('int_misa_sales_lines') }} m
    JOIN order_meta om ON m.voucher_no = om.order_code
    -- BUG-1: TK632 = true COGS only (exclude TK642 promo-goods)
    WHERE m.cogs_amount IS NOT NULL AND m.cogs_account LIKE '632%'
    GROUP BY om.order_id, m.voucher_no
),
```

`source_system` hardcoded `'misa'`.

---

## B. `int_order_cogs_reconciled` Contract

**Grain:** `(order_code, sku)` — one row per order × SKU combination (FULL OUTER JOIN Sapo ↔ MISA)

**Key columns (SELECT list, lines 76–115):**

| Column | Description |
|---|---|
| `order_code` | COALESCE(sapo, misa) |
| `sku` | COALESCE(sapo, misa) |
| `variant_id` | Sapo-side only |
| `qty_sapo` | SUM(quantity_delta) from std_inventory_movements |
| `qty_misa` | SUM(quantity) from std_misa_sales_lines |
| `cogs_goods_sapo` | SUM(cogs_amount) for OUT-301 legs |
| `cogs_goods_misa` | SUM(cogs_amount) from std_misa_sales_lines WHERE cost_account_group='632' |
| `cogs_variance` | sapo − misa (NULL when either absent) |
| `has_sapo_cogs` | BOOLEAN |
| `has_misa_cogs` | BOOLEAN |
| `cogs_source` | 'both' \| 'sapo_mac' \| 'misa' \| 'none' |
| `cogs_goods_primary` | var-driven: default `cogs_goods_sapo`, override `--vars cogs_primary_source=misa` |

**`cogs_source` logic (lines 101–106):**
```sql
CASE
    WHEN sapo IS NOT NULL AND misa IS NOT NULL THEN 'both'
    WHEN sapo IS NOT NULL AND misa IS NULL     THEN 'sapo_mac'
    WHEN sapo IS NULL     AND misa IS NOT NULL THEN 'misa'
    ELSE 'none'
END
```

**CRITICAL:** With default var `sapo_mac`, `cogs_goods_primary` = NULL for `cogs_source='misa'` rows. Downstream aggregation `SUM(cogs_goods_primary)` silently returns 0 for misa-only orders unless we explicitly fall back to `cogs_goods_misa`.

---

## C. Quantified KPI Impact

### Data Snapshot
- Latest rolling parquet: `*_20260605142236.parquet`
- FOE: **3,397 orders**, date range 20210526–20260605 (rolling window = full history)
- int_order_cogs_reconciled: **16,974 distinct orders** (covers all history, not just rolling FOE)

### Full FOE (all 3,397 orders)

| Metric | Current (MISA-632) | Proposed (Sapo-MAC) |
|---|---|---|
| Orders with COGS | 945 (27.8%) | 3,044 (89.6%) |
| Total COGS | 1,906,752,406 VND | 17,016,291,686 VND |
| Total gross_profit | 8,445,421,355 VND | est. −6,664,117,925 VND |
| Total channel_net_profit | 8,385,856,090 VND | est. −6,723,683,190 VND |
| COGS delta | — | +15.1B VND (+792%) |

**⚠ WARNING:** FOE rolling parquet includes 2,413 "SON00xxx" legacy orders (pre-2022 internal orders). These have minimal net_revenue but carry high Sapo-MAC COGS (Sapo inventory movements tracked from day 1). They heavily distort the aggregate. See 2026-only analysis below for business-relevant delta.

### 2026 Orders Only (850 orders — most business-relevant)

| Metric | Current (MISA-632) | Proposed (Sapo-MAC+misa fallback) | Delta |
|---|---|---|---|
| Orders with COGS | 379 (44.6%) | 668 (78.6%) | +289 orders |
| Total COGS | 624,668,776 VND | 1,782,819,523 VND | **+1,158,150,747 VND (+185%)** |
| Total gross_profit | 2,053,373,979 VND | 895,223,232 VND | **−1,158,150,747 VND (−56%)** |
| Total channel_net_profit | 1,993,808,714 VND | 835,657,967 VND | **−1,158,150,747 VND (−58%)** |
| Orders GAIN COGS | — | 275 gained | COGS was NULL, now has Sapo-MAC |
| Orders LOSE COGS | — | 1 lost | — |
| Not in recon | — | 182 orders (21.4%) | No COGS in either system |

### `cogs_source` Distribution (2026 FOE orders, order-level)

| cogs_source | Orders | % | Notes |
|---|---|---|---|
| `both` | 379 | 44.6% | Sapo-MAC + MISA available → **recon panel WILL render** |
| `sapo_mac` | 289 | 34.0% | Sapo-MAC only (no MISA match) |
| `not_in_recon` | 182 | 21.4% | Order not in recon at all (recent orders not yet in inventory) |
| `misa` | 0 (2026) | 0% | No 2026 orders are misa-only at order level |

**For overlapping 'both' orders at SKU level:** Sapo-MAC is **94.1% of MISA** (close, not exact — expected variance from return netting, timing, catalog SKUs).

**Recon panel:** YES — 379 orders (44.6% of 2026) have `cogs_source='both'` → panel will render for real traffic.

---

## D. Implementation Plan (Precise Edits)

### 1. `fact_order_economics.sql`

**Replace `misa_order` CTE with `cogs_recon` CTE. Keep ALL profit formula structure unchanged — only swap the input variable.**

```sql
-- Replace misa_order CTE (lines 29-40) with:
cogs_recon AS (
    SELECT
        order_code,
        SUM(COALESCE(cogs_goods_primary, cogs_goods_misa, 0)) AS cogs_amount,
        -- Order-level cogs_source: 'both' if any SKU has both; 'sapo_mac' if sapo-only; etc.
        CASE
            WHEN BOOL_OR(cogs_goods_sapo IS NOT NULL) AND BOOL_OR(cogs_goods_misa IS NOT NULL) THEN 'both'
            WHEN BOOL_OR(cogs_goods_sapo IS NOT NULL)                                          THEN 'sapo_mac'
            WHEN BOOL_OR(cogs_goods_misa IS NOT NULL)                                          THEN 'misa'
            ELSE 'none'
        END AS cogs_source,
        COUNT(*) AS misa_line_count  -- rename or drop: becomes cogs_line_count
    FROM {{ ref('int_order_cogs_reconciled') }}
    GROUP BY order_code
),
```

**Notes on `cogs_goods_primary` fallback:**
- With default var `sapo_mac`, `cogs_goods_primary` is NULL for misa-only rows.
- The CTE should aggregate using: `SUM(COALESCE(cogs_goods_sapo, cogs_goods_misa, 0))` — this gives Sapo-MAC primary, misa as fallback, preserving coverage for misa-only orders.
- **Business decision required**: Should misa-only orders (no Sapo-MAC) keep their MISA COGS? Recommendation: YES (use fallback), otherwise 3,584 orders lose COGS entirely. But 2026 data shows 0 misa-only orders so impact is historical.

**Replace JOIN** (line 197): `LEFT JOIN cogs_recon m ON o.order_code = m.order_code`

**Replace SELECT** (lines 104-108):
```sql
m.cogs_amount,
m.misa_line_count,    -- can stay as cogs_line_count or drop
m.cogs_amount IS NOT NULL AS has_cogs,
m.cogs_source,        -- NEW column
```

All profit formulas (`gross_profit`, `channel_net_profit`, `fully_loaded_net_profit`, all `_pct` variants) reference `COALESCE(m.cogs_amount, 0)` — **no formula changes needed**, only the CTE alias changes from `misa_order` to `cogs_recon` (already aliased as `m`).

**File:** `transformation/models/marts/sales/fact_order_economics.sql`

---

### 2. `fact_order_costs.sql`

**Replace `cogs` CTE (lines 21-38):**

```sql
cogs AS (
    SELECT
        om.order_id,
        r.order_code,
        'cogs'                              AS cost_type,
        'COGS'                              AS cost_category,
        ABS(SUM(COALESCE(r.cogs_goods_sapo, r.cogs_goods_misa, 0)))  AS amount,
        -- source_system reflects actual data origin
        CASE
            WHEN BOOL_OR(r.cogs_goods_sapo IS NOT NULL) AND BOOL_OR(r.cogs_goods_misa IS NOT NULL) THEN 'sapo_mac+misa'
            WHEN BOOL_OR(r.cogs_goods_sapo IS NOT NULL) THEN 'sapo_mac'
            WHEN BOOL_OR(r.cogs_goods_misa IS NOT NULL) THEN 'misa'
            ELSE 'none'
        END                                 AS source_system,
        r.order_code                        AS source_record,
        'actual'                            AS fee_source,
        MIN(om.date_key)                    AS date_key,
        MIN(om.channel_key)                 AS channel_key
    FROM {{ ref('int_order_cogs_reconciled') }} r
    JOIN order_meta om ON r.order_code = om.order_code
    WHERE COALESCE(r.cogs_goods_sapo, r.cogs_goods_misa, 0) > 0
    GROUP BY om.order_id, r.order_code
),
```

**File:** `transformation/models/marts/sales/fact_order_costs.sql`

---

### 3. `transformation/models/marts/schema.yml`

Under `fact_order_economics` columns section, **add** after `has_cogs`:

```yaml
      - name: cogs_source
        description: "COGS data source: 'sapo_mac' (Sapo-MAC only) | 'misa' (MISA-632 only) | 'both' (both systems) | 'none' (no COGS). Drives recon panel in detailView."
        tests:
          - accepted_values:
              arguments:
                values: ['sapo_mac', 'misa', 'both', 'none']
              config:
                where: "cogs_source IS NOT NULL"
```

**Update** `cogs_amount` description:
```yaml
      - name: cogs_amount
        description: "Giá vốn hàng bán (primary: Sapo-MAC moving-avg cost; fallback: MISA TK632). NULL nếu không có dữ liệu COGS."
```

**Update** `has_cogs` description:
```yaml
      - name: has_cogs
        description: "true nếu đơn có dữ liệu COGS (sapo_mac, misa, or both). Alias: cogs_source IS NOT NULL AND cogs_source != 'none'."
```

Under `fact_order_costs` columns, **update** `source_system`:
```yaml
      - name: source_system
        description: "Origin: sapo_mac | misa | sapo_mac+misa | shopee | sapo | derived | estimated"
```

---

### 4. `detailView/app/adapters/outbound/duckdb/queries/order_header.sql`

**Replace TODO block (lines 48–52):**

```sql
-- Phase-05: real cogs_source from mart
foe.cogs_source,
```

Remove the `CASE WHEN foe.has_cogs THEN 'misa' ELSE 'none' END AS cogs_source` workaround.

**File:** `detailView/app/adapters/outbound/duckdb/queries/order_header.sql`

---

### 5. `detailView/tests/seed_schema.py`

Add `cogs_source VARCHAR` to `fact_order_economics` DDL (line 29):
```python
order_id VARCHAR, order_code VARCHAR, cogs_amount DOUBLE, has_cogs BOOLEAN,
cogs_source VARCHAR,   # ADD THIS
```

---

### 6. New DAG Edge → Restart Required

`fact_order_economics` currently refs: `fact_orders`, `int_misa_sales_lines`, `int_shopee_order_fees`, `std_fulfillments`, `fact_order_returns`, `int_order_promo_goods_cost`, `int_order_overhead_allocation`.

**`int_order_cogs_reconciled` is a NEW dependency edge** for `fact_order_economics` and `fact_order_costs`.

**Action required:**
```bash
docker compose restart data_platform
```
Required before `dbt run` to force manifest reload (dbt pre-parses the DAG at startup; new ref edges must be picked up).

---

### 7. Bootstrap Serving Views Required

Adding `cogs_source` column to `fact_order_economics` (a rolling parquet fact):
- DuckDB views are built from parquet schema at bootstrap time
- Adding a column requires `bootstrap_serving_views.py`
- **Must stop Metabase + detailView first** (DuckDB single-writer)

```bash
docker compose stop metabase detail_view
python ingestion/bootstrap_serving_views.py  # or equivalent
docker compose start metabase detail_view
```

---

## E. Verify Protocol

1. `docker compose restart data_platform` (new DAG edge)
2. `dbt run --select int_order_cogs_reconciled fact_order_economics fact_order_costs` inside container
3. `dbt test --select fact_order_economics fact_order_costs` — verify `accepted_values` on `cogs_source`
4. **BUG-1/Delta check**: confirm `fact_order_costs` has no `cogs_type='cogs' WHERE source_system LIKE '%642%'` rows (promo-goods still excluded)
5. **Baseline compare**: `SUM(cogs_amount)` before vs after (expect +185% on 2026 orders per section C)
6. **Coverage check**: `COUNT(*) FILTER (WHERE cogs_source IS NOT NULL AND cogs_source != 'none') / COUNT(*)` — expect ~79% for 2026
7. Bootstrap serving views (stop metabase/detail_view, run bootstrap, restart)
8. Dagster nightly run: verify zero errors on `fact_order_economics` and `fact_order_costs` assets
9. detailView: spot-check an order with `cogs_source='both'` — confirm recon panel renders

---

## F. Risks / Unresolved Questions

**🔴 Business Decision Required (BLOCKING):**

1. **The +185% COGS increase (2026)** — Sapo-MAC reports ~2.85M VND avg COGS vs MISA 2.02M avg for overlapping orders. Gross profit drops from ~2.05B → ~895M VND on 2026 cohort. This is not a bug — it reflects MISA-632 having been an UNDERCOUNT (not all COGS lines captured, and only 28% order coverage). But management must accept this new, lower reported margin before deploy.

2. **Fallback for misa-only orders** — `cogs_goods_primary` = NULL when `cogs_source='misa'` (sapo var default). Decision: should those orders keep MISA COGS in `cogs_amount`? Recommendation: YES (use `COALESCE(cogs_goods_sapo, cogs_goods_misa)`). Impact: 2026 data shows 0 misa-only orders, so low near-term impact; historical orders affected.

3. **`not_in_recon` orders (182 of 850 2026 orders = 21.4%)** — These FOE orders have no matching entry in `int_order_cogs_reconciled` (likely: very new orders where Sapo inventory movement hasn't been ingested yet, or fulfillment hasn't happened). They will have `cogs_source='none'` and `cogs_amount=NULL` after repoint. Currently they ALSO have no COGS (same result). Monitor post-deploy.

4. **SON00xxx legacy orders** — 2,413 of 3,397 FOE orders are pre-2022 internal orders with high Sapo-MAC COGS but minimal revenue (COGS >> revenue). They will show negative gross_profit after repoint. Confirm these are expected to appear in FOE rolling window (or if rolling window should exclude status=internal).

**🟡 Implementation Clarifications:**

5. `misa_line_count` column in FOE: after repoint, this no longer reflects MISA line count. Rename to `cogs_sku_count` or drop — check if detailView uses it (search shows it is NOT queried in `order_header.sql`).

6. `source_system` in `fact_order_costs` cogs row: changing `'misa'` → `'sapo_mac'/'sapo_mac+misa'/etc.` may break Metabase filters/dashboards that currently filter `source_system = 'misa'`. Audit Metabase COGS cards before deploy.

7. `detailView/tests/seed_rows.py` — seed data for `fact_order_economics` likely lacks `cogs_source` column. After schema change, tests will fail until `seed_schema.py` + `seed_rows.py` updated. The `detailView/tests/test_order_repository.py` line 28 asserts `fin.has_cogs is True` — this should still pass, but verify `cogs_source` assertion added.

---

**Status:** DONE
**Summary:** Phase-05 COGS repoint fully scoped. New DAG edge (int_order_cogs_reconciled) requires container restart + bootstrap. KPI delta is material (+185% COGS, −56% gross profit on 2026 orders) — business sign-off required before production deploy.
**Concerns/Blockers:** Business decision #1 (KPI shift acceptance) is blocking production deploy. Technical implementation is straightforward once approved.
