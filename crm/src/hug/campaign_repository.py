"""crm_hug_campaign CRUD + history snapshots.

Pure data-access over crm.db. No HTTP, no push — that lives in campaign_push.py.
Every create/update writes a full JSON snapshot to crm_hug_campaign_history so any
prior state can be restored without a separate diff table.

All functions accept an open sqlite3.Connection (single-writer discipline: caller
controls the connection lifecycle; functions commit their own writes).
"""
from __future__ import annotations

import json
import re
import sqlite3
from shared.timestamps import utc_now

# campaign_id must be safe to use as a URL segment and as a D1 key.
# Accept alphanumeric, hyphen, and underscore only.
_CAMPAIGN_ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')

_REQUIRED_FIELDS = ("campaign_id", "name", "destination_type", "destination_url")
_VALID_DEST_TYPES = {"zalo_oa", "cf_pages", "url"}
_VALID_STATUSES   = {"active", "paused", "archived"}


def _validate(row: dict) -> None:
    """Raise ValueError for obviously malformed campaign rows at the boundary."""
    for field in _REQUIRED_FIELDS:
        if not row.get(field):
            raise ValueError(f"campaign row missing required field: {field!r}")

    campaign_id = row["campaign_id"]
    if not _CAMPAIGN_ID_RE.match(campaign_id):
        raise ValueError(
            f"campaign_id must be alphanumeric/hyphen/underscore, max 128 chars: {campaign_id!r}"
        )

    if row["destination_type"] not in _VALID_DEST_TYPES:
        raise ValueError(
            f"destination_type must be one of {_VALID_DEST_TYPES}, got: {row['destination_type']!r}"
        )

    status = row.get("status", "active")
    if status not in _VALID_STATUSES:
        raise ValueError(f"status must be one of {_VALID_STATUSES}, got: {status!r}")


def _row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sqlite3.Row to a plain dict (needed to produce JSON snapshot)."""
    return dict(row)


def _write_history_snapshot(conn: sqlite3.Connection, row: sqlite3.Row) -> None:
    """Append a full JSON snapshot of the given campaign row to history."""
    snapshot = json.dumps(_row_to_dict(row), ensure_ascii=False)
    conn.execute(
        "INSERT INTO crm_hug_campaign_history (campaign_id, snapshot, saved_at)"
        " VALUES (?, ?, ?)",
        (row["campaign_id"], snapshot, utc_now()),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_campaigns(
    conn: sqlite3.Connection,
    status: str | None = None,
) -> list[sqlite3.Row]:
    """Return campaigns ordered by priority ASC.

    Args:
        status: If provided, filter to rows with that status value.
    """
    conn.row_factory = sqlite3.Row
    if status is not None:
        cur = conn.execute(
            "SELECT * FROM crm_hug_campaign WHERE status = ? ORDER BY priority ASC",
            (status,),
        )
    else:
        cur = conn.execute(
            "SELECT * FROM crm_hug_campaign ORDER BY priority ASC"
        )
    return cur.fetchall()


def get_campaign(conn: sqlite3.Connection, campaign_id: str) -> sqlite3.Row | None:
    """Return the campaign row for campaign_id, or None if not found."""
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM crm_hug_campaign WHERE campaign_id = ?",
        (campaign_id,),
    )
    return cur.fetchone()


def upsert_campaign(conn: sqlite3.Connection, row: dict) -> sqlite3.Row:
    """Insert or replace a campaign row and write a history snapshot.

    Required keys: campaign_id, name, destination_type, destination_url.
    Optional keys default to column defaults when absent.
    Returns the saved row.
    """
    _validate(row)

    now = utc_now()
    conn.row_factory = sqlite3.Row

    conn.execute(
        """
        INSERT INTO crm_hug_campaign
            (campaign_id, name, targeting, destination_type, destination_url,
             offer_ref, priority, schedule_start, schedule_end, quota_total,
             status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
            (SELECT created_at FROM crm_hug_campaign WHERE campaign_id = ?), ?
        ), ?)
        ON CONFLICT(campaign_id) DO UPDATE SET
            name             = excluded.name,
            targeting        = excluded.targeting,
            destination_type = excluded.destination_type,
            destination_url  = excluded.destination_url,
            offer_ref        = excluded.offer_ref,
            priority         = excluded.priority,
            schedule_start   = excluded.schedule_start,
            schedule_end     = excluded.schedule_end,
            quota_total      = excluded.quota_total,
            status           = excluded.status,
            updated_at       = excluded.updated_at
        """,
        (
            row["campaign_id"],
            row["name"],
            row.get("targeting", "{}"),
            row["destination_type"],
            row["destination_url"],
            row.get("offer_ref"),
            row.get("priority", 100),
            row.get("schedule_start"),
            row.get("schedule_end"),
            row.get("quota_total"),
            row.get("status", "active"),
            row["campaign_id"],  # for COALESCE sub-select
            now,                 # created_at fallback on INSERT
            now,                 # updated_at
        ),
    )

    saved = get_campaign(conn, row["campaign_id"])
    assert saved is not None  # just inserted/updated — must exist
    _write_history_snapshot(conn, saved)
    conn.commit()
    return saved


def archive_campaign(conn: sqlite3.Connection, campaign_id: str) -> None:
    """Soft-delete a campaign by setting status='archived' and writing a snapshot."""
    conn.row_factory = sqlite3.Row
    now = utc_now()
    conn.execute(
        "UPDATE crm_hug_campaign SET status = 'archived', updated_at = ? WHERE campaign_id = ?",
        (now, campaign_id),
    )
    saved = get_campaign(conn, campaign_id)
    if saved is not None:
        _write_history_snapshot(conn, saved)
    conn.commit()


def list_history(
    conn: sqlite3.Connection,
    campaign_id: str,
    limit: int = 20,
) -> list[sqlite3.Row]:
    """Return the most recent history snapshots for a campaign, newest first."""
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM crm_hug_campaign_history"
        " WHERE campaign_id = ? ORDER BY saved_at DESC LIMIT ?",
        (campaign_id, limit),
    )
    return cur.fetchall()


def restore_snapshot(
    conn: sqlite3.Connection,
    campaign_id: str,
    snapshot_id: int,
) -> sqlite3.Row:
    """Restore a campaign to a prior state captured in history.

    Reads the JSON snapshot from crm_hug_campaign_history row `snapshot_id`,
    writes it back as the current campaign row, and appends a new history entry
    so the restore itself is auditable.
    Raises KeyError if snapshot_id does not exist for campaign_id.
    """
    conn.row_factory = sqlite3.Row
    hist_row = conn.execute(
        "SELECT * FROM crm_hug_campaign_history WHERE id = ? AND campaign_id = ?",
        (snapshot_id, campaign_id),
    ).fetchone()
    if hist_row is None:
        raise KeyError(f"snapshot id={snapshot_id} not found for campaign {campaign_id!r}")

    prior: dict = json.loads(hist_row["snapshot"])
    # Drop fields managed by upsert_campaign (created_at preserved via COALESCE above)
    prior.pop("created_at", None)
    prior.pop("updated_at", None)
    return upsert_campaign(conn, prior)


def suggest_next_priority(conn: sqlite3.Connection) -> int:
    """Return MAX(priority)+10 across active campaigns, or 10 if none exist.

    Provides a soft-unique hint for the UI; does not enforce uniqueness.
    """
    row = conn.execute(
        "SELECT MAX(priority) FROM crm_hug_campaign WHERE status != 'archived'"
    ).fetchone()
    current_max = row[0] if row and row[0] is not None else 0
    return current_max + 10
