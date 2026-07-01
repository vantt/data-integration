"""Backfill claim tasks for parties contacted recently without prior claiming.

Run once to fix Band-4 items that were contacted via C360/M08 before the
auto-claim feature existed. Idempotent — INSERT OR IGNORE skips duplicates.

Usage (inside container):
    python /app/crm/ops/backfill_claim_tasks.py [--hours N] [--dry-run]

Defaults: --hours 24 (match Band-4 window), --dry-run False.
"""
from __future__ import annotations

import argparse
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone

_CRM_DB = "/data/crm.db"
_CACHE_DB = "/data/cache.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_CRM_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"ATTACH DATABASE '{_CACHE_DB}' AS cache")
    return conn


def _candidates(conn: sqlite3.Connection, cutoff: str) -> list[sqlite3.Row]:
    """Return parties: recently contacted + no active claim task."""
    return conn.execute("""
        SELECT
            lc.party_id,
            lc.last_contacted_at,
            lc.last_contact_result,
            lc.last_activity_id,
            act.staff_user_id,
            au.user_id    AS assignee_user_id,
            au.full_name  AS assignee_name,
            COALESCE(pi.identity_value, lc.party_id) AS customer_name
        FROM crm_last_contact lc
        LEFT JOIN crm_activity_log act ON act.activity_id = lc.last_activity_id
        LEFT JOIN crm_app_user     au  ON au.user_id      = act.staff_user_id
        -- primary name identity (type='name'), one row per party
        LEFT JOIN crm_party_identity pi
               ON pi.party_id = lc.party_id
              AND pi.identity_type = 'name'
              AND pi.is_primary = 1
        WHERE lc.last_contacted_at >= ?
          AND NOT EXISTS (
              SELECT 1 FROM crm_task t
              WHERE  t.source     = 'action_queue_claim'
                AND  t.source_ref = lc.party_id
                -- Skip if active task exists OR if a task was already created
                -- for this contact cycle (created_at >= last_contacted_at means
                -- this contact was already claimed, even if now done/cancelled).
                AND (t.status NOT IN ('cancelled', 'done') OR t.created_at >= lc.last_contacted_at)
          )
        GROUP BY lc.party_id
    """, (cutoff,)).fetchall()


def _backfill(dry_run: bool, hours: int) -> None:
    conn = _connect()
    now = datetime.now(timezone.utc)
    cutoff = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    rows = _candidates(conn, cutoff)
    print(f"Candidates (contacted in last {hours}h, no claim task): {len(rows)}")

    created = skipped = 0
    for row in rows:
        party_id       = row["party_id"]
        customer_name  = row["customer_name"] or party_id
        assignee_id    = row["assignee_user_id"]
        assignee_name  = row["assignee_name"] or "?"
        contacted_at   = row["last_contacted_at"]
        result         = row["last_contact_result"] or "?"

        if not assignee_id:
            print(f"  SKIP {party_id}: staff_user_id={row['staff_user_id']!r} → no crm_app_user match")
            skipped += 1
            continue

        print(
            f"  {'DRY ' if dry_run else ''}CREATE  {party_id}  '{customer_name}'"
            f"  → assignee={assignee_name}  last={contacted_at[:16]}  outcome={result}"
        )
        if not dry_run:
            task_id  = str(uuid.uuid4())
            now_str  = now.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            conn.execute("""
                INSERT OR IGNORE INTO crm_task (
                    task_id, party_id, title, description,
                    priority, status, source, source_ref,
                    assignee_user_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, 'open', 'action_queue_claim', ?, ?, ?, ?)
            """, (
                task_id, party_id,
                f"Liên hệ {customer_name}",
                f"Backfill: liên hệ {contacted_at[:16]} · {result}",
                party_id, assignee_id, now_str, now_str,
            ))
            created += 1

    if not dry_run:
        conn.commit()

    conn.close()
    print(f"\nDone — created: {created}, skipped (no assignee): {skipped}")
    if dry_run:
        print("(dry-run, nothing written)")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--hours",   type=int,  default=24,    help="lookback window in hours (default 24)")
    ap.add_argument("--dry-run", action="store_true",      help="print what would be created, don't write")
    args = ap.parse_args()
    _backfill(dry_run=args.dry_run, hours=args.hours)


if __name__ == "__main__":
    main()
