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
    "crm_app_user",
    "crm_note", "crm_tag", "crm_party_tag", "crm_party_insight", "crm_customer_profile",
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


def _dedup_identity_join(fk_alias: str) -> str:
    """LEFT JOIN clause against a de-duplicated crm_party_identity.

    Defensive against fan-out: a dedup-merge bug elsewhere could leave more
    than one crm_party_identity row per party_id with identity_type =
    'sapo_customer'. A plain LEFT JOIN on party_id would then duplicate
    every row of the exporting table. Collapse to exactly one row per
    party via ROW_NUMBER() before joining.

    NOTE: the literal "crm_party_identity" must appear unqualified here so
    _qualify_for_attach() can prefix it with crm_src. after ATTACH.
    """
    return f"""LEFT JOIN (
                SELECT party_id, identity_value,
                       ROW_NUMBER() OVER (PARTITION BY party_id ORDER BY identity_value) AS rn
                FROM crm_party_identity
                WHERE identity_type = 'sapo_customer'
            ) pi ON pi.party_id = {fk_alias}.party_id AND pi.rn = 1"""


CRM_WRITEBACK_TABLES: list[CrmWritebackTable] = [
    CrmWritebackTable(
        name="crm_last_contact",
        mode="snapshot",
        export_query="""
            SELECT lc.party_id, pi.identity_value AS customer_id,
                   lc.last_contacted_at, lc.last_contact_result,
                   lc.channel AS last_contact_channel, lc.updated_at
            FROM crm_last_contact lc
            """ + _dedup_identity_join("lc"),
    ),
    CrmWritebackTable(
        name="crm_activity_log",
        mode="incremental_append",
        watermark_column="created_at",
        # created_at = DB insert time; avoids missing late-logged activities vs occurred_at
        export_query="""
            SELECT a.activity_id, a.party_id, pi.identity_value AS customer_id,
                   a.activity_type, a.direction, a.channel, a.channel_type, a.outcome,
                   a.contact_outcome, a.outcome_reason, a.callback_at, a.contact_duration_s,
                   a.task_id, a.related_order_code, a.staff_user_id,
                   a.occurred_at, a.created_at, a.custom_fields
            FROM crm_activity_log a
            """ + _dedup_identity_join("a") + """
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
            """ + _dedup_identity_join("ct"),
    ),
    CrmWritebackTable(
        name="crm_app_user",
        mode="snapshot",
        export_query="""
            SELECT user_id, staff_id, email, full_name, role,
                   is_active, lark_user_id, created_at, updated_at
            FROM crm_app_user
        """,
    ),
    CrmWritebackTable(
        name="crm_task",
        mode="incremental_append",
        watermark_column="updated_at",
        export_query="""
            SELECT t.task_id, t.party_id, pi.identity_value AS customer_id,
                   t.title, t.status, t.priority,
                   t.source, t.source_ref,
                   t.assignee_user_id, t.created_by,
                   t.due_at, t.completed_at,
                   t.created_at, t.updated_at,
                   t.outcome, t.task_kind, t.channel,
                   t.value_at_stake_vnd, t.top_affinity_product,
                   t.claimed_action_types
            FROM crm_task t
            """ + _dedup_identity_join("t") + """
            WHERE t.updated_at > '{cursor}'
        """,
    ),
    CrmWritebackTable(
        name="crm_note", mode="incremental_append", watermark_column="created_at",
        export_query="""
            SELECT n.note_id, n.party_id, pi.identity_value AS customer_id,
                   n.note_type, n.body, n.author_user_id,
                   n.pinned, n.pinned_until, n.visibility, n.task_id, n.campaign_id,
                   n.source_activity_id, n.updated_at, n.updated_by_user_id, n.deleted_at, n.created_at
            FROM crm_note n
            """ + _dedup_identity_join("n") + """
            WHERE n.created_at > '{cursor}' AND n.visibility != 'private'
        """),
    CrmWritebackTable(
        name="crm_tag", mode="snapshot",
        export_query="SELECT tag_id, name, category, color, display_label, is_archived FROM crm_tag"),
    CrmWritebackTable(
        name="crm_party_tag", mode="snapshot",
        export_query="""
            SELECT pt.party_id, pi.identity_value AS customer_id, pt.tag_id, pt.tagged_by, pt.tagged_at,
                   pt.source AS source, pt.source_activity_id
            FROM crm_party_tag pt
            """ + _dedup_identity_join("pt")),
    CrmWritebackTable(
        name="crm_party_insight", mode="incremental_append", watermark_column="created_at",
        export_query="""
            SELECT i.insight_id, i.party_id, pi.identity_value AS customer_id,
                   i.insight_type, i.body, i.confidence,
                   i.source_note_id, i.created_by, i.updated_at, i.deleted_at, i.created_at
            FROM crm_party_insight i
            """ + _dedup_identity_join("i") + """
            WHERE i.created_at > '{cursor}' AND i.deleted_at IS NULL
        """),
    CrmWritebackTable(
        name="crm_customer_profile_custom", mode="snapshot",
        export_query="""
            SELECT cp.party_id, pi.identity_value AS customer_id, cp.custom, cp.updated_at
            FROM crm_customer_profile cp
            """ + _dedup_identity_join("cp")),
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
crm_app_user_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_app_user")
)
crm_task_export = _make_incremental_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_task")
)
crm_note_export = _make_incremental_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_note")
)
crm_tag_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_tag")
)
crm_party_tag_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_party_tag")
)
crm_party_insight_export = _make_incremental_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_party_insight")
)
crm_customer_profile_custom_export = _make_snapshot_asset(
    next(t for t in CRM_WRITEBACK_TABLES if t.name == "crm_customer_profile_custom")
)
