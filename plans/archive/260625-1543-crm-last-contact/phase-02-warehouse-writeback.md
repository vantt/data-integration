# Phase 02 — Generic CRM-to-Warehouse Write-Back Pipeline

**Status:** ✅ DONE (shipped 2026-06-25, commits f597bd5 + d435f59)
**Depends on:** Phase 01 (crm_last_contact table in crm.db)

## Goal

Export CRM write-side data (from `crm.db`) back into the warehouse — generic,
config-driven, extensible. `crm_last_contact` is first; `crm_activity`,
`crm_hug_voucher`, `crm_task`, `crm_campaign_target` follow the same pattern.

---

## Table Registry — What to Ingest

| Table | Mode | Priority | Warehouse value |
|-------|------|----------|-----------------|
| `crm_last_contact`    | snapshot            | P0 | Action queue enrichment (last_contacted_at, is_recently_contacted) |
| `crm_activity`        | incremental_append  | P0 | Contact outcome funnel, conversion rate, channel effectiveness |
| `crm_hug_voucher`     | snapshot            | P0 | HUG campaign attribution: issued vs redeemed, ROI per campaign |
| `crm_campaign_target` | snapshot            | P0 | Campaign conversion rate, revenue attribution per campaign |

**Deferred (no immediate need):**
- `crm_task` — CS productivity dashboard not yet needed
- `crm_action_state` — dismiss/snooze feedback loop not yet needed

**Skipped:**
- `crm_segment_member` — segments are derived from warehouse data; circular
- `crm_customer_profile` — consent always null/unknown (policy=default-contactable); low value
- `crm_conversation`, `crm_message` — raw channel payloads, not analytical
- `crm_segment`, `crm_campaign` — metadata/definitions, not events

---

## Architecture

```
crm.db  (SQLite, /app/var/crm_data/crm.db — already RO-mounted in data_platform)
   │
   │  [Dagster: crm_writeback_assets.py]
   │  DuckDB ATTACH SQLite (native, zero pandas)
   │  Per-table export_query (party_id → customer_id resolved at export)
   │
   ▼  snapshot tables: full overwrite
   ▼  incremental_append: cursor by created_at → date-partitioned parquet
   │
/app/var/data_lake/crm_export/
   ├── crm_last_contact.parquet
   ├── crm_hug_voucher.parquet
   ├── crm_task.parquet
   ├── crm_campaign_target.parquet
   ├── crm_action_state.parquet
   └── crm_activity/                   ← incremental_append, date-partitioned
       ├── crm_activity_cursor.json    ← {"last_created_at": "2026-06-25T…"}
       └── date=20260625/batch_143000.parquet
   │
   │  [dbt: staging/crm/]
   │  one stg_crm__<table>.sql per exported table
   │  external source on crm_export/
   ▼
mart_customer_action_queue  (LEFT JOIN stg_crm__last_contact → +4 cols)
mart_crm_activity_log       (new mart — contact funnel analytics)
mart_hug_attribution        (joins crm_hug_voucher + fact_orders + mart_hug_optin)
```

---

## Key Design Decisions

### 1. DuckDB ATTACH SQLite — zero pandas
`ATTACH 'path.db' (TYPE sqlite, READ_ONLY)` native in DuckDB.
Direct parquet COPY in one session. No intermediate data structures.

### 2. party_id → customer_id resolved at export time
Tables with `party_id` JOIN `crm_party_identity WHERE identity_type = 'sapo_customer'`
to produce `customer_id` (INTEGER, warehouse key). dbt never sees CRM-internal party IDs.

Exception: `crm_hug_voucher.customer_id` is already the Sapo customer_id (TEXT).
No join needed; cast to INTEGER in staging.

### 3. Two export modes

**snapshot** — full parquet overwrite each run.
Suitable for: upsert/mutable tables small enough to reload (< ~200K rows).
All tables except `crm_activity` use this.

**incremental_append** — cursor-based; exports only rows newer than last run.
Writes date-partitioned parquets. Cursor stored in a JSON sidecar file.
`crm_activity` uses `created_at` (insert time, not `occurred_at`) to avoid
missing late-logged activities.

### 4. Config-driven table registry
```python
@dataclass
class CrmWritebackTable:
    name: str
    export_query: str      # SQL against ATTACHED crm.db
    mode: str              # "snapshot" | "incremental_append"
    watermark_column: str = "created_at"  # incremental_append only
```
Adding a table = one new `CrmWritebackTable(...)` entry.

### 5. mart_customer_action_queue enrichment is additive
New columns nullable via LEFT JOIN. Existing Metabase cards unaffected.

### 6. Dagster sequencing
`crm_last_contact_export` and `crm_activity_export` are upstream deps of dbt.
No separate schedule needed — fresh export on every pipeline run.

---

## Files to Create / Modify

```
orchestration/assets/crm_writeback_assets.py      NEW
transformation/models/staging/crm/                NEW directory
  _crm__sources.yml                               NEW
  stg_crm__last_contact.sql                       NEW
  stg_crm__activity.sql                           NEW
  stg_crm__hug_voucher.sql                        NEW
  stg_crm__task.sql                               NEW
  stg_crm__campaign_target.sql                    NEW
  stg_crm__action_state.sql                       NEW
transformation/models/marts/customer/
  mart_customer_action_queue.sql                  MODIFY (+4 cols, LEFT JOIN stg_crm__last_contact)
  mart_crm_activity_log.sql                       NEW (contact funnel analytics mart)
transformation/models/marts/core/
  mart_hug_attribution.sql                        NEW (HUG campaign ROI)
orchestration/definitions.py                      MODIFY (register assets + upstream deps)
.env.docker                                       MODIFY (add CRM_DB_PATH if not set)
```

---

## Dagster Asset: crm_writeback_assets.py

```python
import json, os
from dataclasses import dataclass, field
from typing import Optional
import duckdb
from dagster import asset, AssetExecutionContext, Output

CRM_DB_PATH = os.environ.get("CRM_DB_PATH", "/app/var/crm_data/crm.db")
DATA_LAKE   = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
CRM_EXPORT  = os.path.join(DATA_LAKE, "crm_export")

# ── Party ID resolver ──────────────────────────────────────────────────────────
# Reused in all queries where the table stores party_id (CRM-internal).
_PARTY_JOIN = """
    LEFT JOIN crm_party_identity pi
           ON pi.party_id      = {alias}.party_id
          AND pi.identity_type = 'sapo_customer'
"""

@dataclass
class CrmWritebackTable:
    name: str
    export_query: str
    mode: str = "snapshot"           # "snapshot" | "incremental_append"
    watermark_column: str = "created_at"


CRM_WRITEBACK_TABLES: list[CrmWritebackTable] = [

    CrmWritebackTable(
        name="crm_last_contact",
        mode="snapshot",
        export_query="""
            SELECT lc.party_id, pi.identity_value AS customer_id,
                   lc.last_contacted_at, lc.last_contact_result,
                   lc.channel AS last_contact_channel, lc.updated_at
            FROM crm_last_contact lc
            LEFT JOIN crm_party_identity pi
                   ON pi.party_id = lc.party_id AND pi.identity_type = 'sapo_customer'
        """,
    ),

    CrmWritebackTable(
        name="crm_activity",
        mode="incremental_append",
        watermark_column="created_at",  # insert time avoids missing late-logged activities
        export_query="""
            SELECT a.activity_id, a.party_id, pi.identity_value AS customer_id,
                   a.activity_type, a.direction, a.channel, a.channel_used,
                   a.outcome, a.contact_outcome, a.callback_at,
                   a.contact_duration_s, a.task_id, a.related_order_code,
                   a.staff_user_id, a.occurred_at, a.created_at
            FROM crm_activity a
            LEFT JOIN crm_party_identity pi
                   ON pi.party_id = a.party_id AND pi.identity_type = 'sapo_customer'
            WHERE a.created_at > '{cursor}'
        """,
    ),

    CrmWritebackTable(
        name="crm_hug_voucher",
        mode="snapshot",
        export_query="""
            SELECT code, customer_id, token, campaign_id, min_order,
                   issued_at, redeemed_at, order_code
            FROM crm_hug_voucher
        """,
        # customer_id is already Sapo integer (TEXT) — no party join needed
    ),

    CrmWritebackTable(
        name="crm_task",
        mode="snapshot",
        export_query="""
            SELECT t.task_id, t.party_id, pi.identity_value AS customer_id,
                   t.title, t.description, t.due_at, t.priority, t.status,
                   t.outcome, t.source, t.source_ref, t.assignee_user_id,
                   t.created_by, t.created_at, t.updated_at, t.completed_at
            FROM crm_task t
            LEFT JOIN crm_party_identity pi
                   ON pi.party_id = t.party_id AND pi.identity_type = 'sapo_customer'
        """,
    ),

    CrmWritebackTable(
        name="crm_campaign_target",
        mode="snapshot",
        export_query="""
            SELECT ct.campaign_id, ct.party_id, pi.identity_value AS customer_id,
                   ct.status, ct.assigned_user_id, ct.last_touch_at,
                   ct.converted_order_code, ct.converted_revenue_vnd, ct.converted_at
            FROM crm_campaign_target ct
            LEFT JOIN crm_party_identity pi
                   ON pi.party_id = ct.party_id AND pi.identity_type = 'sapo_customer'
        """,
    ),

    CrmWritebackTable(
        name="crm_action_state",
        mode="snapshot",
        export_query="""
            SELECT action_id, status, snoozed_until, updated_at, updated_by
            FROM crm_action_state
        """,
        # No party_id — keyed on action_id from warehouse
    ),
]


# ── Export helpers ─────────────────────────────────────────────────────────────

def _snapshot_export(crm_db: str, query: str, out_path: str) -> int:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with duckdb.connect() as con:
        con.execute(f"ATTACH '{crm_db}' AS crm_src (TYPE sqlite, READ_ONLY)")
        con.execute(f"""
            COPY (SELECT * FROM crm_src.({query}) q WHERE customer_id IS NOT NULL OR
                  -- tables without customer_id (crm_action_state): skip filter
                  NOT EXISTS (SELECT 1 FROM pragma_table_info('q') WHERE name='customer_id'))
            TO '{out_path}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE)
        """)
        return con.execute(f"SELECT COUNT(*) FROM read_parquet('{out_path}')").fetchone()[0]


def _incremental_export(crm_db: str, tbl: CrmWritebackTable,
                        export_dir: str, run_ts: str) -> int:
    os.makedirs(export_dir, exist_ok=True)
    cursor_path = os.path.join(export_dir, f"{tbl.name}_cursor.json")
    cursor = "1970-01-01T00:00:00.000Z"
    if os.path.exists(cursor_path):
        with open(cursor_path) as f:
            cursor = json.load(f).get("cursor", cursor)

    query = tbl.export_query.replace("{cursor}", cursor)
    date_part = run_ts[:10].replace("-", "")
    out_path = os.path.join(export_dir, f"date={date_part}", f"batch_{run_ts[11:19].replace(':', '')}.parquet")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with duckdb.connect() as con:
        con.execute(f"ATTACH '{crm_db}' AS crm_src (TYPE sqlite, READ_ONLY)")
        con.execute(f"COPY ({query.replace('crm_activity', 'crm_src.crm_activity').replace('crm_party_identity', 'crm_src.crm_party_identity')}) TO '{out_path}' (FORMAT PARQUET)")
        n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out_path}')").fetchone()[0]
        new_cursor = con.execute(f"SELECT MAX({tbl.watermark_column}) FROM read_parquet('{out_path}')").fetchone()[0]

    if new_cursor:
        with open(cursor_path, "w") as f:
            json.dump({"cursor": str(new_cursor)}, f)

    return n


# ── Dagster assets ─────────────────────────────────────────────────────────────

def _make_snapshot_asset(tbl: CrmWritebackTable):
    @asset(name=f"{tbl.name}_export", group_name="crm_writeback",
           description=f"Export {tbl.name} from crm.db → data lake (snapshot).")
    def _asset(context: AssetExecutionContext) -> Output:
        out = os.path.join(CRM_EXPORT, f"{tbl.name}.parquet")
        n = _snapshot_export(CRM_DB_PATH, tbl.export_query, out)
        context.log.info(f"{tbl.name}: {n} rows → {out}")
        return Output(n, metadata={"row_count": n, "path": out})
    return _asset


def _make_incremental_asset(tbl: CrmWritebackTable):
    @asset(name=f"{tbl.name}_export", group_name="crm_writeback",
           description=f"Export {tbl.name} from crm.db → data lake (incremental_append).")
    def _asset(context: AssetExecutionContext) -> Output:
        from datetime import datetime, timezone
        run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        export_dir = os.path.join(CRM_EXPORT, tbl.name)
        n = _incremental_export(CRM_DB_PATH, tbl, export_dir, run_ts)
        context.log.info(f"{tbl.name}: {n} new rows")
        return Output(n, metadata={"new_rows": n})
    return _asset


# Exported asset objects for definitions.py
crm_last_contact_export   = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_last_contact"))
crm_activity_export       = _make_incremental_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_activity"))
crm_hug_voucher_export    = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_hug_voucher"))
crm_task_export           = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_task"))
crm_campaign_target_export = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_campaign_target"))
crm_action_state_export   = _make_snapshot_asset(next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_action_state"))
```

---

## dbt: staging/crm/_crm__sources.yml

```yaml
version: 2
sources:
  - name: crm_export
    tables:
      - name: crm_last_contact
        external:
          location: "{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_last_contact.parquet"
          file_format: parquet
      - name: crm_activity
        external:
          location: "{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_activity/**/*.parquet"
          file_format: parquet
      - name: crm_hug_voucher
        external:
          location: "{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_hug_voucher.parquet"
          file_format: parquet
      - name: crm_task
        external:
          location: "{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_task.parquet"
          file_format: parquet
      - name: crm_campaign_target
        external:
          location: "{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_campaign_target.parquet"
          file_format: parquet
      - name: crm_action_state
        external:
          location: "{{ env_var('DBT_DATA_LAKE_PATH') }}/crm_export/crm_action_state.parquet"
          file_format: parquet
```

---

## mart_customer_action_queue Enrichment

```sql
-- Add CTE:
last_contact AS (SELECT * FROM {{ ref('stg_crm__last_contact') }}),

-- Add to SELECT (nullable — safe when lc row absent):
    lc.last_contacted_at,
    lc.last_contact_result,
    lc.last_contact_channel,
    CASE
        WHEN lc.last_contact_result IN ('answered', 'replied', 'met')
         AND lc.last_contacted_at::TIMESTAMPTZ >= (NOW() AT TIME ZONE 'UTC') - INTERVAL '24 hours'
        THEN TRUE ELSE FALSE
    END AS is_recently_contacted_positively,

-- Add to FROM:
LEFT JOIN last_contact lc ON classified.customer_id = lc.customer_id
```

---

## New mart: mart_crm_activity_log

```sql
-- marts/customer/mart_crm_activity_log.sql
-- Contact outcome funnel: who called, when, result, linked to customer
SELECT
    a.activity_id, a.customer_id::INTEGER AS customer_id,
    c.customer_key, c.full_name,
    a.activity_type, a.channel, a.channel_used,
    a.outcome, a.contact_outcome,
    a.occurred_at::TIMESTAMPTZ AS occurred_at,
    a.created_at::TIMESTAMPTZ  AS logged_at,
    a.staff_user_id, a.task_id, a.related_order_code,
    -- Derived
    a.contact_outcome IN ('answered', 'replied', 'met') AS is_reached,
    CASE a.contact_outcome
        WHEN 'answered' THEN 'Reached'
        WHEN 'no_answer' THEN 'No answer'
        WHEN 'callback' THEN 'Callback'
        WHEN 'refused'  THEN 'Refused'
        ELSE 'Unknown'
    END AS outcome_label
FROM {{ ref('stg_crm__activity') }} a
LEFT JOIN {{ ref('dim_customers') }} c ON c.customer_id = a.customer_id::INTEGER
```

---

## New mart: mart_hug_attribution

```sql
-- marts/core/mart_hug_attribution.sql
-- HUG campaign ROI: issued vs redeemed, link to orders
SELECT
    v.campaign_id,
    v.code,
    v.customer_id::INTEGER AS customer_id,
    c.full_name, c.value_group,
    v.issued_at::TIMESTAMPTZ  AS issued_at,
    v.redeemed_at::TIMESTAMPTZ AS redeemed_at,
    v.order_code,
    v.order_code IS NOT NULL  AS is_redeemed,
    o.total_price_vnd         AS redemption_revenue_vnd,
    o.contribution_margin_vnd AS redemption_margin_vnd
FROM {{ ref('stg_crm__hug_voucher') }} v
LEFT JOIN {{ ref('dim_customers') }} c ON c.customer_id = v.customer_id::INTEGER
LEFT JOIN {{ ref('fact_orders') }} o
       ON o.order_code = v.order_code AND o.source_system = 'sapo_v2'
```

---

## Dagster definitions.py changes

```python
from orchestration.assets.crm_writeback_assets import (
    crm_last_contact_export, crm_activity_export, crm_hug_voucher_export,
    crm_task_export, crm_campaign_target_export, crm_action_state_export,
)

# Add as upstream deps of dbt asset:
defs = Definitions(
    assets=[
        ...,
        crm_last_contact_export, crm_activity_export, crm_hug_voucher_export,
        crm_task_export, crm_campaign_target_export, crm_action_state_export,
        build_dbt_assets(..., deps=[
            crm_last_contact_export, crm_activity_export, crm_hug_voucher_export,
            crm_task_export, crm_campaign_target_export, crm_action_state_export,
        ]),
    ]
)
```

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| crm.db write lock during export | DuckDB ATTACH TYPE sqlite READ_ONLY never acquires write lock |
| `customer_id IS NULL` (party not linked) | WHERE filter at export; LEFT JOIN in mart (NULL cols, no row dropped) |
| crm_activity parquet accumulates indefinitely | Date-partitioned; GC job can prune partitions older than retention window |
| Incremental cursor lost / corrupted | Cursor JSON sidecar; if missing → cursor resets to epoch → full re-export (idempotent) |
| `crm_activity` late-logged activities | Watermark on `created_at` (insert time), not `occurred_at` (event time) |
| Missing parquet on first run | dbt source: clear failure at build time, not silent wrong data |

---

## Success Criteria

- [ ] All 6 Dagster export assets materialise without error
- [ ] Parquets present at expected paths in `/app/var/data_lake/crm_export/`
- [ ] `crm_activity` incremental: second run exports 0 rows when no new activities
- [ ] All `stg_crm__*` staging models compile and return rows
- [ ] `mart_customer_action_queue` builds with new contact columns
- [ ] `mart_crm_activity_log` returns rows with correct `is_reached` logic
- [ ] `mart_hug_attribution` shows redeemed vouchers linked to fact_orders
- [ ] No existing Metabase cards break (new cols are additive)
