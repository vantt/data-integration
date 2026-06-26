"""CRM-to-warehouse write-back: export CRM SQLite tables to parquet for dbt consumption."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass

import duckdb
from dagster import AssetExecutionContext, Output, asset

CRM_DB_PATH = os.environ.get("CRM_DB_PATH", "/app/var/crm_data/crm.db")
DATA_LAKE = os.environ.get("DBT_DATA_LAKE_PATH", "/app/var/data_lake")
CRM_EXPORT = os.path.join(DATA_LAKE, "crm_export")

_DEFAULT_CURSOR = "1970-01-01T00:00:00.000Z"

# All bare CRM table names that may appear in export queries (needs crm_src. prefix after ATTACH).
_CRM_TABLE_NAMES = [
    "crm_last_contact", "crm_party_identity", "crm_hug_voucher",
    "crm_campaign_target", "crm_task", "crm_action_state", "crm_activity_log",
]


def _qualify_for_attach(query: str) -> str:
    """Prefix bare crm_* table names with crm_src. schema after ATTACH."""
    qualified = query
    for t in _CRM_TABLE_NAMES:
        qualified = qualified.replace(t, f"crm_src.{t}")
    return qualified


@dataclass
class CrmWritebackTable:
    name: str
    export_query: str
    mode: str = "snapshot"  # "snapshot" | "incremental_append"
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
        name="crm_activity_log",
        mode="incremental_append",
        watermark_column="created_at",
        # created_at = DB insert time; avoids missing late-logged activities vs occurred_at
        export_query="""
            SELECT a.activity_id, a.party_id, pi.identity_value AS customer_id,
                   a.activity_type, a.direction, a.channel, a.outcome,
                   a.contact_outcome, a.callback_at, a.contact_duration_s,
                   a.task_id, a.related_order_code, a.staff_user_id,
                   a.occurred_at, a.created_at
            FROM crm_activity_log a
            LEFT JOIN crm_party_identity pi
                   ON pi.party_id = a.party_id AND pi.identity_type = 'sapo_customer'
            WHERE a.created_at > '{cursor}'
        """,
    ),
    CrmWritebackTable(
        name="crm_hug_voucher",
        mode="snapshot",
        # customer_id is already Sapo integer stored as TEXT — no party join needed
        export_query="""
            SELECT code, customer_id, token, campaign_id, min_order,
                   issued_at, redeemed_at, order_code
            FROM crm_hug_voucher
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
]


def _snapshot_export(crm_db: str, query: str, out_path: str) -> int:
    """Export full table as single parquet (overwrite)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    qualified = _qualify_for_attach(query)
    with duckdb.connect() as con:
        con.execute(f"ATTACH '{crm_db}' AS crm_src (TYPE sqlite, READ_ONLY)")
        con.execute(
            f"COPY ({qualified}) "
            f"TO '{out_path}' (FORMAT PARQUET, OVERWRITE_OR_IGNORE TRUE)"
        )
        return con.execute(f"SELECT COUNT(*) FROM read_parquet('{out_path}')").fetchone()[0]


def _incremental_export(
    crm_db: str, tbl: CrmWritebackTable, export_dir: str, run_ts: str
) -> int:
    """Export rows newer than cursor; write date-partitioned parquet; advance cursor."""
    os.makedirs(export_dir, exist_ok=True)
    cursor_path = os.path.join(export_dir, f"{tbl.name}_cursor.json")
    cursor = _DEFAULT_CURSOR
    if os.path.exists(cursor_path):
        with open(cursor_path) as f:
            cursor = json.load(f).get("cursor", cursor)

    query = tbl.export_query.replace("{cursor}", cursor)
    date_part = run_ts[:10].replace("-", "")
    batch_ts = run_ts[11:19].replace(":", "")
    out_path = os.path.join(export_dir, f"date={date_part}", f"batch_{batch_ts}.parquet")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with duckdb.connect() as con:
        con.execute(f"ATTACH '{crm_db}' AS crm_src (TYPE sqlite, READ_ONLY)")
        qualified = _qualify_for_attach(query)
        con.execute(f"COPY ({qualified}) TO '{out_path}' (FORMAT PARQUET)")
        n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{out_path}')").fetchone()[0]
        if n == 0:
            os.remove(out_path)
            return 0
        new_cursor = con.execute(
            f"SELECT MAX({tbl.watermark_column}) FROM read_parquet('{out_path}')"
        ).fetchone()[0]

    if new_cursor:
        with open(cursor_path, "w") as f:
            json.dump({"cursor": str(new_cursor)}, f)

    return n


def _make_snapshot_asset(tbl: CrmWritebackTable):
    @asset(
        name=f"{tbl.name}_export",
        group_name="crm_writeback",
        description=f"Export {tbl.name} from crm.db to data lake (snapshot).",
    )
    def _asset(context) -> Output:
        out = os.path.join(CRM_EXPORT, f"{tbl.name}.parquet")
        n = _snapshot_export(CRM_DB_PATH, tbl.export_query, out)
        context.log.info(f"{tbl.name}: {n} rows → {out}")
        return Output(n, metadata={"row_count": n, "path": out})

    return _asset


def _make_incremental_asset(tbl: CrmWritebackTable):
    @asset(
        name=f"{tbl.name}_export",
        group_name="crm_writeback",
        description=f"Export {tbl.name} from crm.db to data lake (incremental_append).",
    )
    def _asset(context) -> Output:
        from datetime import datetime, timezone

        run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        export_dir = os.path.join(CRM_EXPORT, tbl.name)
        n = _incremental_export(CRM_DB_PATH, tbl, export_dir, run_ts)
        context.log.info(f"{tbl.name}: {n} new rows")
        return Output(n, metadata={"new_rows": n})

    return _asset


# Module-level asset objects — imported by definitions.py via load_assets_from_modules
crm_last_contact_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_last_contact")
)
crm_activity_log_export = _make_incremental_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_activity_log")
)
crm_hug_voucher_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_hug_voucher")
)
crm_campaign_target_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_campaign_target")
)
