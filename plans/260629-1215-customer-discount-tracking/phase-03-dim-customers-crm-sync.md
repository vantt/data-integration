---
phase: 3
title: "dim_customers + CRM Sync"
status: pending
priority: P2
dependencies: [1, 2]
---

# Phase 3: dim_customers + CRM Sync

## Overview

Thêm 6 discount fields vào `dim_customers` (join `int_customer_discount_metrics`), đồng bộ sang CRM cache qua path: `duckdb_reader.py` → `sqlite_upsert.py` → `wh_customer_insight` → `cache_insight.py` → `c360_insight_panel.html`.

## CRM Sync Path

```
dim_customers (DuckDB/parquet)
    │  fetch_customer_insight()
    ▼
duckdb_reader.py  _DIM_CUSTOMERS_INSIGHT_COLS  (pinned column contract)
    │  upsert_customer_insight()
    ▼
sqlite_upsert.py  wh_customer_insight table schema
    │
    ▼
cache.db  wh_customer_insight  (SQLite, cache_repository.py reads from here)
    │  CacheInsight entity
    ▼
cache_insight.py  (domain entity)
    │
    ▼
c360_insight_panel.html  (Jinja2 template)
```

## Related Code Files

- Modify: `transformation/models/marts/core/dim_customers.sql`
- Modify: `crm/sync/duckdb_reader.py` (`_DIM_CUSTOMERS_INSIGHT_COLS` list)
- Modify: `crm/sync/sqlite_upsert.py` (`apply_schema` + `upsert_customer_insight`)
- Modify: `crm/src/domain/entities/cache_insight.py`
- Modify: `crm/src/adapters/outbound/sqlite/cache_repository.py`
- Modify: `crm/src/adapters/inbound/web/templates/fragments/c360_insight_panel.html`

## Implementation Steps

### 1. `dim_customers.sql` — join intermediate + add 8 columns

Add to `WITH` block:

```sql
discount_metrics AS (
    SELECT * FROM {{ ref('int_customer_discount_metrics') }}
),
```

Add to `joined_data` SELECT:

```sql
-- Discount metrics from int_customer_discount_metrics (4 buckets × 2 metrics)
dm.last_line_discount_rate,
dm.max_line_discount_rate,
dm.last_voucher_discount_rate,
dm.max_voucher_discount_rate,
dm.last_campaign_discount_rate,
dm.max_campaign_discount_rate,
dm.last_negotiated_discount_rate,
dm.max_negotiated_discount_rate,
```

Add LEFT JOIN:

```sql
LEFT JOIN discount_metrics dm ON c.customer_key = dm.customer_key
```

Add to final SELECT (after `discount_order_rate`):

```sql
-- Discount tracking: last + max rate per bucket (NULL = customer never had this type)
-- Rates are 0.0–1.0 (not percentages). 4 buckets: line_discount / voucher / campaign / negotiated.
-- See plans/260629-1215-customer-discount-tracking/ for taxonomy.
last_line_discount_rate,
max_line_discount_rate,
last_voucher_discount_rate,
max_voucher_discount_rate,
last_campaign_discount_rate,
max_campaign_discount_rate,
last_negotiated_discount_rate,
max_negotiated_discount_rate,
```

**Deploy sequence** (incremental → new columns require full-refresh):

```bash
# 1. Stop Metabase to release DuckDB read lock
# 2. Run dbt full-refresh for dim_customers only
docker exec -it data_platform bash -c "
  cd /app/transformation &&
  dbt run --select dim_customers --full-refresh --target prod
"
# 3. Rebuild serving views
docker exec -it data_platform python bootstrap_serving_views.py
# 4. Restart Metabase
docker compose restart metabase
```

### 2. `duckdb_reader.py` — add to column contract

In `_DIM_CUSTOMERS_INSIGHT_COLS` list:

```python
_DIM_CUSTOMERS_INSIGHT_COLS = [
    "customer_key",
    "customer_id",
    # ... existing cols ...
    "discount_sensitivity",
    "cancel_rate",
    # ── NEW: discount bucket metrics (4 buckets × 2 metrics) ─────────────
    "last_line_discount_rate",
    "max_line_discount_rate",
    "last_voucher_discount_rate",
    "max_voucher_discount_rate",
    "last_campaign_discount_rate",
    "max_campaign_discount_rate",
    "last_negotiated_discount_rate",
    "max_negotiated_discount_rate",
    # ─────────────────────────────────────────────────────────────────────
    "last_purchased_sku",
    # ... remaining cols ...
]
```

> Column order in this list must match the SELECT order in `fetch_customer_insight()`.
> `_check_columns()` will raise `MissingColumnError` immediately if any col is absent from DuckDB — fast-fail guard.

### 3. `sqlite_upsert.py` — schema + upsert

In `apply_schema()`, add to `wh_customer_insight` CREATE TABLE:

```sql
last_line_discount_rate       REAL,
max_line_discount_rate        REAL,
last_voucher_discount_rate    REAL,
max_voucher_discount_rate     REAL,
last_campaign_discount_rate   REAL,
max_campaign_discount_rate    REAL,
last_negotiated_discount_rate REAL,
max_negotiated_discount_rate  REAL,
```

In `upsert_customer_insight()` INSERT statement, add 8 columns to column list and `ON CONFLICT DO UPDATE SET`:

```sql
-- in column list:
last_line_discount_rate, max_line_discount_rate,
last_voucher_discount_rate, max_voucher_discount_rate,
last_campaign_discount_rate, max_campaign_discount_rate,
last_negotiated_discount_rate, max_negotiated_discount_rate,

-- in VALUES (:...):
:last_line_discount_rate, :max_line_discount_rate,
:last_voucher_discount_rate, :max_voucher_discount_rate,
:last_campaign_discount_rate, :max_campaign_discount_rate,
:last_negotiated_discount_rate, :max_negotiated_discount_rate,

-- in ON CONFLICT DO UPDATE SET:
last_line_discount_rate       = excluded.last_line_discount_rate,
max_line_discount_rate        = excluded.max_line_discount_rate,
last_voucher_discount_rate    = excluded.last_voucher_discount_rate,
max_voucher_discount_rate     = excluded.max_voucher_discount_rate,
last_campaign_discount_rate   = excluded.last_campaign_discount_rate,
max_campaign_discount_rate    = excluded.max_campaign_discount_rate,
last_negotiated_discount_rate = excluded.last_negotiated_discount_rate,
max_negotiated_discount_rate  = excluded.max_negotiated_discount_rate,
```

> `wh_customer_insight` uses `customer_key` as PRIMARY KEY with `ON CONFLICT` upsert — existing pattern, no schema change needed beyond adding columns.

### 4. `cache_insight.py` — domain entity

In `CacheInsight` dataclass, add 8 fields:

```python
# Discount tracking: 4 buckets × 2 metrics (0.0–1.0; NULL = no order of that type ever)
last_line_discount_rate:       float | None = None
max_line_discount_rate:        float | None = None
last_voucher_discount_rate:    float | None = None
max_voucher_discount_rate:     float | None = None
last_campaign_discount_rate:   float | None = None
max_campaign_discount_rate:    float | None = None
last_negotiated_discount_rate: float | None = None
max_negotiated_discount_rate:  float | None = None
```

### 5. `cache_repository.py` — SELECT projection

Add 8 fields to entity mapping:

```python
last_line_discount_rate       = row["last_line_discount_rate"],
max_line_discount_rate        = row["max_line_discount_rate"],
last_voucher_discount_rate    = row["last_voucher_discount_rate"],
max_voucher_discount_rate     = row["max_voucher_discount_rate"],
last_campaign_discount_rate   = row["last_campaign_discount_rate"],
max_campaign_discount_rate    = row["max_campaign_discount_rate"],
last_negotiated_discount_rate = row["last_negotiated_discount_rate"],
max_negotiated_discount_rate  = row["max_negotiated_discount_rate"],
```

### 6. `c360_insight_panel.html` — surface in UI

Add to the discount section (near `discount_sensitivity`):

```html
{% set has_discount = ins.last_line_discount_rate or ins.last_voucher_discount_rate
                      or ins.last_campaign_discount_rate or ins.last_negotiated_discount_rate %}
{% if has_discount %}
<div class="signal-row">
  <span class="signal-label">Giảm giá gần nhất</span>
  <div class="signal-values">
    {% if ins.last_line_discount_rate %}
    <span class="signal-tag">SP {{ "%.0f"|format(ins.last_line_discount_rate * 100) }}%
      {% if ins.max_line_discount_rate != ins.last_line_discount_rate %}(max {{ "%.0f"|format(ins.max_line_discount_rate * 100) }}%){% endif %}
    </span>
    {% endif %}
    {% if ins.last_voucher_discount_rate %}
    <span class="signal-tag">Voucher {{ "%.0f"|format(ins.last_voucher_discount_rate * 100) }}%
      {% if ins.max_voucher_discount_rate != ins.last_voucher_discount_rate %}(max {{ "%.0f"|format(ins.max_voucher_discount_rate * 100) }}%){% endif %}
    </span>
    {% endif %}
    {% if ins.last_campaign_discount_rate %}
    <span class="signal-tag">KM {{ "%.0f"|format(ins.last_campaign_discount_rate * 100) }}%
      {% if ins.max_campaign_discount_rate != ins.last_campaign_discount_rate %}(max {{ "%.0f"|format(ins.max_campaign_discount_rate * 100) }}%){% endif %}
    </span>
    {% endif %}
    {% if ins.last_negotiated_discount_rate %}
    <span class="signal-tag">Thỏa thuận {{ "%.0f"|format(ins.last_negotiated_discount_rate * 100) }}%
      {% if ins.max_negotiated_discount_rate != ins.last_negotiated_discount_rate %}(max {{ "%.0f"|format(ins.max_negotiated_discount_rate * 100) }}%){% endif %}
    </span>
    {% endif %}
  </div>
</div>
{% endif %}
```

### 7. CRM container rebuild

Per `feedback_new_mart_crm_serving_integration.md` — sync code is baked into the image:

```bash
docker compose up -d --build crm
```

## Success Criteria

- [ ] `dim_customers` SELECT includes 8 new columns, non-null for customers with discount history
- [ ] `dbt run --select dim_customers --full-refresh` completes without error
- [ ] `bootstrap_serving_views.py` runs after full-refresh
- [ ] `python -m crm.sync.reverse_etl_warehouse_to_crm` runs without `MissingColumnError`
- [ ] `SELECT last_price_reduction_rate FROM wh_customer_insight WHERE last_price_reduction_rate IS NOT NULL LIMIT 5` in cache.db returns data
- [ ] Customer 360 view for a known discounted customer shows "Giảm giá gần nhất" section
- [ ] CRM container rebuilt and serving without error

## Risk Assessment

- **SQLite schema migration**: `wh_customer_insight` is recreated by `apply_schema()` (`CREATE TABLE IF NOT EXISTS`) — new columns are NOT added to existing table. If cache.db already has the old schema, need to either:
  - Drop and recreate: `DROP TABLE wh_customer_insight; python -m crm.sync.reverse_etl_warehouse_to_crm`
  - Or add `ALTER TABLE wh_customer_insight ADD COLUMN ...` statements to `apply_schema()`
  - **Recommended**: add `ALTER TABLE IF column not exists` guards in `apply_schema()` — safer, preserves existing rows
- **CRM container**: templates/static NOT volume-mounted → rebuild required (per `feedback_detailview_code_baked_in_image.md` — same pattern)
- **Rollback**: revert 6 columns from `_DIM_CUSTOMERS_INSIGHT_COLS`, re-run sync → cache cols become NULL; CRM template guards with `{% if ins.last_price_reduction_rate %}` prevent display errors
