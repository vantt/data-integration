"""Consistent, *verified* backup of the CRM SQLite databases.

Backs up `crm.db` (source of truth) + `cache.db` (regenerable warehouse snapshot)
from a live volume, with no app downtime.

Design — a backup is a GATE, not a blind dump (see plan 260624-2010):
  1. `wal_checkpoint(TRUNCATE)` + `integrity_check` on the LIVE source.
  2. Profile the LIVE source (per-table row counts + content checksums).
  3. Snapshot via the SQLite online-backup API (`Connection.backup()`) — page-
     consistent even under concurrent writes; never a raw file copy of a WAL DB.
  4. Profile the SNAPSHOT and assert it equals the source (delta == 0) — else FAIL.
  5. Write `manifest.json` (the "expected truth" the restore drill verifies against).

Callable: `backup_crm(data_dir, dest_root, keep)`.
CLI:      `python -m crm.ops.backup_crm --data-dir /data --dest /backups --keep 7`

NOTE: row counts + a file sha alone cannot detect value mutation, so the manifest
also stores a per-table content checksum (order-independent hash of all rows).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# crm.db + hug.db = irreplaceable sources of truth (hug.db is the single registry
# for the physical Hug token lifecycle — printed/bound tokens are not derivable
# from anything else). cache.db = regenerable warehouse cache, included so a
# restore is self-contained / needs no warehouse.
SOURCE_OF_TRUTH = "crm.db"
CRITICAL_DBS = ("crm.db", "hug.db")  # present-but-failed ⇒ hard fail (not "partial")
SNAPSHOT_DBS = ("crm.db", "hug.db", "cache.db")


# --------------------------------------------------------------------------- #
# DB profiling (the "expected truth")
# --------------------------------------------------------------------------- #
def _user_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _table_checksum(conn: sqlite3.Connection, table: str) -> str:
    """Order-independent content hash of every row in a table.

    Order-independent (sort rows in Python) so it does not depend on rowid and
    survives VACUUM/rebuild; catches value mutation that row counts miss.
    crm.db/cache.db are small enough to read fully.
    """
    rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
    encoded = sorted(repr(tuple(r)).encode("utf-8") for r in rows)
    h = hashlib.sha256()
    for e in encoded:
        h.update(e)
        h.update(b"\x00")
    return h.hexdigest()


def _migration_head(conn: sqlite3.Connection) -> str | None:
    """Max applied migration version (crm.db only); None if no tracking table."""
    try:
        row = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else None
    except sqlite3.Error:
        return None


def profile_db(path: Path) -> dict:
    """Read-only structural + content profile of a SQLite DB file."""
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        tables = {}
        for t in _user_tables(conn):
            count = conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            tables[t] = {"rows": count, "checksum": _table_checksum(conn, t)}
        return {
            "file_size": path.stat().st_size,
            "sha256": _file_sha256(path),
            "integrity_check": integrity,
            "migration_head": _migration_head(conn),
            "tables": tables,
        }
    finally:
        conn.close()


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Snapshot + gate
# --------------------------------------------------------------------------- #
def _checkpoint(src_path: Path) -> None:
    """Best-effort WAL checkpoint so the snapshot can't miss un-checkpointed commits.

    PASSIVE (not TRUNCATE) so it never blocks the live writer; safe to fail.
    """
    conn = sqlite3.connect(str(src_path), timeout=10)
    try:
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
    except sqlite3.Error:
        pass  # checkpoint is an optimization; the backup API is still consistent
    finally:
        conn.close()


def _snapshot(src_path: Path, dst_path: Path) -> None:
    """Consistent online-backup copy (handles WAL; never a torn file copy)."""
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    dst = sqlite3.connect(str(dst_path))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _tables_match(source: dict, snapshot: dict) -> list[str]:
    """Return a list of human-readable diffs between two profiles (empty == match)."""
    diffs: list[str] = []
    s_tabs, b_tabs = source["tables"], snapshot["tables"]
    if set(s_tabs) != set(b_tabs):
        diffs.append(f"table set differs: source={sorted(s_tabs)} snapshot={sorted(b_tabs)}")
    for t in set(s_tabs) & set(b_tabs):
        if s_tabs[t]["rows"] != b_tabs[t]["rows"]:
            diffs.append(f"{t}: row count {s_tabs[t]['rows']} -> {b_tabs[t]['rows']}")
        elif s_tabs[t]["checksum"] != b_tabs[t]["checksum"]:
            diffs.append(f"{t}: content checksum mismatch")
    return diffs


# --------------------------------------------------------------------------- #
# Rotation + disk pre-flight
# --------------------------------------------------------------------------- #
def _preflight_disk(dest_root: Path, needed_bytes: int) -> None:
    free = shutil.disk_usage(dest_root).free
    if free < needed_bytes * 2:  # 2x headroom
        raise RuntimeError(
            f"insufficient disk: need ~{needed_bytes * 2} free at {dest_root}, have {free}"
        )


def _rotate(dest_root: Path, keep: int) -> None:
    dirs = sorted(
        [d for d in dest_root.iterdir() if d.is_dir() and d.name[:8].isdigit()],
        reverse=True,
    )
    for old in dirs[keep:]:
        shutil.rmtree(old, ignore_errors=True)


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def backup_crm(data_dir: str, dest_root: str, keep: int = 7) -> dict:
    """Take a verified backup of the CRM DBs. Returns the manifest dict.

    Raises RuntimeError if the source-of-truth (`crm.db`) fails its verification
    gate. `cache.db` is best-effort: if it fails, the backup is kept but flagged
    `partial=true` (crm.db is what matters).
    """
    data = Path(data_dir)
    dest = Path(dest_root)
    dest.mkdir(parents=True, exist_ok=True)

    present = [db for db in SNAPSHOT_DBS if (data / db).exists()]
    if SOURCE_OF_TRUTH not in present:
        raise RuntimeError(f"{SOURCE_OF_TRUTH} not found in {data} — nothing to back up")

    _preflight_disk(dest, sum((data / db).stat().st_size for db in present))
    _rotate(dest, keep - 1)  # make room before writing the new one

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out_dir = dest / ts
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sqlite_version": sqlite3.sqlite_version,
        "image_digest": os.environ.get("CRM_IMAGE_DIGEST"),  # pinned by the drill
        "partial": False,
        "dbs": {},
    }

    for db in present:
        src_path = data / db
        dst_path = out_dir / db
        try:
            _checkpoint(src_path)
            source_profile = profile_db(src_path)          # 1. live source truth
            if source_profile["integrity_check"] != "ok":
                raise RuntimeError(f"source {db} integrity_check = {source_profile['integrity_check']}")
            _snapshot(src_path, dst_path)                  # 2. consistent snapshot
            snap_profile = profile_db(dst_path)            # 3. snapshot profile
            diffs = _tables_match(source_profile, snap_profile)  # 4. GATE
            if diffs or snap_profile["integrity_check"] != "ok":
                raise RuntimeError(f"snapshot != source for {db}: {diffs or snap_profile['integrity_check']}")
            manifest["dbs"][db] = {
                "ok": True,
                "source": source_profile,
                "snapshot": snap_profile,
            }
        except Exception as exc:  # noqa: BLE001 — record + decide by DB criticality
            manifest["dbs"][db] = {"ok": False, "error": str(exc)}
            if db in CRITICAL_DBS:
                # irreplaceable source failed → the whole backup is worthless
                (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
                raise RuntimeError(f"backup FAILED on critical db {db}: {exc}") from exc
            manifest["partial"] = True  # cache.db failed — keep crm.db/hug.db, flag partial

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Verified backup of CRM SQLite DBs.")
    ap.add_argument("--data-dir", default=os.environ.get("CRM_DATA_DIR", "/data"))
    ap.add_argument("--dest", default="/backups")
    ap.add_argument("--keep", type=int, default=int(os.environ.get("CRM_BACKUP_KEEP", "7")))
    args = ap.parse_args(argv)
    try:
        m = backup_crm(args.data_dir, args.dest, args.keep)
    except Exception as exc:  # noqa: BLE001
        print(f"[backup_crm] FAILED: {exc}", file=sys.stderr)
        # Best-effort failure alert (silent backup stoppage is the zombie-run lesson).
        _alert(f"CRM backup FAILED: {exc}")
        return 1
    flag = " (PARTIAL — cache.db failed)" if m.get("partial") else ""
    print(f"[backup_crm] OK{flag} — {list(m['dbs'])}")
    return 0


def _alert(message: str) -> None:
    """Best-effort Lark alert; never raises (alerting must not break backup exit)."""
    try:
        from orchestration.notifications.lark_client import send_lark_alert  # type: ignore

        send_lark_alert(message)
    except Exception:  # noqa: BLE001
        pass  # alerting is best-effort


if __name__ == "__main__":
    raise SystemExit(main())
