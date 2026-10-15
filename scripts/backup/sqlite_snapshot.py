#!/usr/bin/env python3
"""Consistent copy of a live SQLite database (WAL or rollback journal) for the local backup.

``cp`` of a SQLite file that another process is writing can produce a torn copy. This uses the
SQLite online backup API (``sqlite3.Connection.backup``), which copies one consistent snapshot
while writers keep working, then:

- switches the copy to ``journal_mode=DELETE`` so it is one self-contained file,
- runs ``PRAGMA integrity_check`` on the copy,
- records sha256 and the row count of every table in a manifest entry
  (``<backup_dir>/.components/<component>.json``, merged by ``backup_manifest.py assemble``).

Usage:
  sqlite_snapshot.py <src.db> <dst.db> --backup-dir <dir> --component <name> [--role source_of_truth]

``dst`` must lie inside ``--backup-dir`` (the manifest stores paths relative to it).
Exit 0: copy ok, or source absent (component ``skipped``). Exit 1: copy failed or the copy fails
its integrity check (component ``error``, the bad copy is removed).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup_manifest import ROLES, sha256_file, write_component  # noqa: E402

BUSY_TIMEOUT_S = 60


def _table_counts(con: sqlite3.Connection) -> dict[str, int]:
    names = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    return {n: con.execute(f'SELECT count(*) FROM "{n}"').fetchone()[0] for n in names}


def snapshot(src: Path, dst: Path, backup_dir: Path, component: str, role: str = "source_of_truth") -> dict:
    entry: dict = {"component": component, "kind": "sqlite", "role": role, "source": str(src), "files": []}
    if not src.is_file():
        entry.update(state="skipped", detail=f"{src} not found")
        return entry
    rel = dst.resolve().relative_to(backup_dir.resolve())
    dst.parent.mkdir(parents=True, exist_ok=True)
    part = dst.with_name(dst.name + ".part")
    part.unlink(missing_ok=True)
    started = time.monotonic()
    try:
        # A normal (read-write) connection: a read-only one cannot open a WAL database whose
        # -shm file does not exist yet. No statement here writes to the source.
        source = sqlite3.connect(str(src), timeout=BUSY_TIMEOUT_S)
        target = sqlite3.connect(str(part))
        try:
            source.backup(target)  # pages=-1: the whole database under one read transaction
        finally:
            source.close()
        target.execute("PRAGMA journal_mode=DELETE")
        integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        counts = _table_counts(target)
        target.close()
    except sqlite3.Error as exc:
        part.unlink(missing_ok=True)
        entry.update(state="error", detail=f"{type(exc).__name__}: {exc}")
        return entry
    if integrity != "ok":
        part.unlink(missing_ok=True)
        entry.update(state="error", detail=f"integrity_check on the copy: {integrity}")
        return entry
    part.replace(dst)
    entry["files"].append({
        "path": str(rel),
        "bytes": dst.stat().st_size,
        "sha256": sha256_file(dst),
        "integrity_check": integrity,
        "tables": counts,
    })
    entry.update(state="ok", duration_s=round(time.monotonic() - started, 1))
    return entry


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--backup-dir", type=Path, required=True)
    ap.add_argument("--component", required=True)
    ap.add_argument("--role", default="source_of_truth", choices=ROLES)
    args = ap.parse_args(argv)

    entry = snapshot(args.src, args.dst, args.backup_dir, args.component, args.role)
    write_component(args.backup_dir, entry)
    if entry["state"] == "ok":
        f = entry["files"][0]
        rows = sum(f["tables"].values())
        print(f"{args.component}: ok {f['bytes']} bytes, {len(f['tables'])} tables, {rows} rows, "
              f"integrity ok, {entry['duration_s']}s")
        return 0
    print(f"{args.component}: {entry['state']}: {entry['detail']}", file=sys.stderr)
    return 0 if entry["state"] == "skipped" else 1


if __name__ == "__main__":
    sys.exit(main())
