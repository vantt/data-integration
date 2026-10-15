#!/usr/bin/env python3
"""Manifest and status files of a local backup.

A backup directory (``<BACKUP_ROOT>/<YYYYmmdd-HHMMSS>/``) gets a ``manifest.json`` listing every
component with its role, size, sha256 and row counts, so a later step (off-site copy, restore
drill) can prove the copy is the one that was taken. The snapshot scripts
(``sqlite_snapshot.py``, ``duckdb_snapshot.py``) each drop one entry file into
``<backup_dir>/.components/``; ``assemble`` merges them with directory summaries into the
manifest.

Usage:
  backup_manifest.py dir-entry <backup_dir> <component> <rel_path> <role>   # summary of a copied tree or file
  backup_manifest.py assemble <backup_dir>                                  # write manifest.json
  backup_manifest.py verify <backup_dir>                                    # recheck sha256 and row counts
  backup_manifest.py status <status_file> <state> <duration_s> [<backup_dir>] [--error MSG ...]

Roles: ``source_of_truth`` (needed to restore), ``accelerator`` (hot copy of a derived DuckDB
file, used only if it opens), ``copy`` (plain file copy kept for reference).
Component states: ``ok``, ``skipped`` (source absent, e.g. a fresh instance), ``error``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

COMPONENTS_DIR = ".components"
MANIFEST = "manifest.json"
ROLES = ("source_of_truth", "accelerator", "copy")
_ICT = timezone(timedelta(hours=7))


def now_iso() -> str:
    return datetime.now(_ICT).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path: Path, data: dict) -> None:
    """Write JSON through a temp file in the same directory, then rename (never half-written)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.write("\n")
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def write_component(backup_dir: Path, entry: dict) -> None:
    """Store one component entry for ``assemble``; ``entry['component']`` names the file."""
    name = entry["component"].replace("/", "_")
    write_json_atomic(backup_dir / COMPONENTS_DIR / f"{name}.json", entry)


def dir_entry(backup_dir: Path, component: str, rel_path: str, role: str) -> dict:
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    target = backup_dir / rel_path
    entry = {"component": component, "kind": "tree", "role": role, "path": rel_path}
    if not target.exists():
        entry.update(state="skipped", detail="not present in the backup")
        return entry
    files, size = 0, 0
    if target.is_file():
        files, size = 1, target.stat().st_size
    else:
        for root, _dirs, names in os.walk(target):
            for n in names:
                p = Path(root) / n
                if not p.is_symlink():
                    files += 1
                    size += p.stat().st_size
    entry.update(state="ok", files=files, bytes=size)
    return entry


def assemble(backup_dir: Path) -> dict:
    comp_dir = backup_dir / COMPONENTS_DIR
    components = []
    if comp_dir.is_dir():
        for p in sorted(comp_dir.glob("*.json")):
            components.append(json.loads(p.read_text()))
    manifest = {
        "format": 1,
        "created_at": now_iso(),
        "backup_dir": backup_dir.name,
        "git_sha": os.environ.get("BACKUP_GIT_SHA") or None,
        "components": components,
    }
    write_json_atomic(backup_dir / MANIFEST, manifest)
    if comp_dir.is_dir():
        for p in comp_dir.glob("*.json"):
            p.unlink()
        comp_dir.rmdir()
    return manifest


def _sqlite_counts(path: Path) -> dict[str, int]:
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        names = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        return {n: con.execute(f'SELECT count(*) FROM "{n}"').fetchone()[0] for n in names}
    finally:
        con.close()


def _parquet_rows(path: Path) -> int:
    import duckdb  # only needed for DuckDB exports; present in the data_platform image

    con = duckdb.connect()
    try:
        return con.execute("SELECT count(*) FROM read_parquet(?)", [str(path)]).fetchone()[0]
    finally:
        con.close()


def verify(backup_dir: Path) -> list[str]:
    """Return a list of problems (empty = the backup matches its manifest)."""
    manifest_path = backup_dir / MANIFEST
    if not manifest_path.is_file():
        return [f"{MANIFEST} missing"]
    manifest = json.loads(manifest_path.read_text())
    problems: list[str] = []
    for c in manifest.get("components", []):
        name = c.get("component", "?")
        if c.get("state") != "ok":
            continue
        for f in c.get("files", []) if c.get("kind") in ("sqlite", "duckdb_export") else []:
            path = backup_dir / f["path"]
            if not path.is_file():
                problems.append(f"{name}: {f['path']} missing")
                continue
            if sha256_file(path) != f["sha256"]:
                problems.append(f"{name}: {f['path']} sha256 differs from manifest")
            if c["kind"] == "sqlite":
                counts = _sqlite_counts(path)
                if counts != f["tables"]:
                    problems.append(f"{name}: row counts differ from manifest")
            elif _parquet_rows(path) != f["rows"]:
                problems.append(f"{name}: {f['path']} row count differs from manifest")
    return problems


def write_status(status_file: Path, state: str, duration_s: int, backup_dir: Path | None,
                 errors: list[str]) -> dict:
    status = {
        "ok": state == "ok",
        "state": state,
        "ts": now_iso(),
        "duration_s": duration_s,
        "backup_dir": backup_dir.name if backup_dir else None,
        "components": {},
        "errors": errors,
    }
    manifest_path = backup_dir / MANIFEST if backup_dir else None
    if manifest_path and manifest_path.is_file():
        for c in json.loads(manifest_path.read_text()).get("components", []):
            status["components"][c["component"]] = c.get("state", "?")
    write_json_atomic(status_file, status)
    return status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dir-entry")
    d.add_argument("backup_dir", type=Path)
    d.add_argument("component")
    d.add_argument("rel_path")
    d.add_argument("role", choices=ROLES)
    a = sub.add_parser("assemble")
    a.add_argument("backup_dir", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("backup_dir", type=Path)
    s = sub.add_parser("status")
    s.add_argument("status_file", type=Path)
    s.add_argument("state", choices=("ok", "partial", "failed"))
    s.add_argument("duration_s", type=int)
    s.add_argument("backup_dir", type=Path, nargs="?")
    s.add_argument("--error", action="append", default=[])
    args = ap.parse_args(argv)

    if args.cmd == "dir-entry":
        entry = dir_entry(args.backup_dir, args.component, args.rel_path, args.role)
        write_component(args.backup_dir, entry)
        print(f"{args.component}: {entry['state']} {entry.get('files', 0)} files, {entry.get('bytes', 0)} bytes")
        return 0
    if args.cmd == "assemble":
        m = assemble(args.backup_dir)
        bad = [c["component"] for c in m["components"] if c.get("state") == "error"]
        print(f"manifest: {len(m['components'])} components" + (f", errors: {', '.join(bad)}" if bad else ""))
        return 0
    if args.cmd == "verify":
        problems = verify(args.backup_dir)
        for p in problems:
            print(f"verify: {p}")
        print("verify: OK" if not problems else f"verify: FAILED ({len(problems)} problem(s))")
        return 0 if not problems else 1
    backup_dir = args.backup_dir if args.backup_dir and args.backup_dir.is_dir() else None
    write_status(args.status_file, args.state, args.duration_s, backup_dir, args.error)
    return 0


if __name__ == "__main__":
    sys.exit(main())
