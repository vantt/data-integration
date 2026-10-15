#!/usr/bin/env python3
"""Export chosen tables of a DuckDB file to parquet for the local backup.

For tables that are derived but cannot be rebuilt from the raw lake (append-only history such
as ``main.monitor_taxonomy_parity_log``). The whole DuckDB file is not a restore source; dbt
rebuilds it. This opens the database ``read_only``, and inside one transaction counts the rows
of each table, ``COPY``s it to ``<out_dir>/<schema>.<table>.parquet``, and re-reads the parquet
to check the count. The manifest entry (``<backup_dir>/.components/<component>.json``) lists
rows, bytes and sha256 per table.

Run it while holding ``duckdb_lock`` (backup.sh runs inside the op that takes it), so dbt and
serving are not writing. A writer outside the lock (a script run by hand) holds an exclusive
file lock; opening is then retried with backoff (3 s doubling to 30 s) for at most
``--max-wait`` seconds.

Usage:
  duckdb_snapshot.py <db> <out_dir> --tables main.t1[,schema.t2] --backup-dir <dir> --component <name>
                     [--max-wait 180]

A table that does not exist (fresh database) is listed as skipped, not an error.
Exit 0: every existing table exported (or the database file is absent). Exit 1: lock wait
exceeded or export failed (component ``error``).
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backup_manifest import sha256_file, write_component  # noqa: E402

_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_tables(spec: str) -> list[tuple[str, str]]:
    tables = []
    for item in (t.strip() for t in spec.split(",") if t.strip()):
        schema, _, name = item.rpartition(".")
        schema = schema or "main"
        if not (_IDENT.match(schema) and _IDENT.match(name)):
            raise ValueError(f"invalid table name {item!r} (expected schema.table)")
        tables.append((schema, name))
    if not tables:
        raise ValueError("no table given")
    return tables


def _connect_read_only(db: Path, max_wait: float, sleep=time.sleep):
    import duckdb

    delay, waited = 3.0, 0.0
    while True:
        try:
            return duckdb.connect(str(db), read_only=True)
        except duckdb.IOException as exc:  # another process holds the write lock
            if waited + delay > max_wait:
                raise TimeoutError(f"{db} still locked after {waited:.0f}s: {exc}") from exc
            sleep(delay)
            waited += delay
            delay = min(delay * 2, 30.0)


def export(db: Path, out_dir: Path, tables: list[tuple[str, str]], backup_dir: Path, component: str,
           max_wait: float = 180, sleep=time.sleep) -> dict:
    entry: dict = {"component": component, "kind": "duckdb_export", "role": "source_of_truth",
                   "source": str(db), "files": [], "skipped_tables": []}
    if not db.is_file():
        entry.update(state="skipped", detail=f"{db} not found")
        return entry
    started = time.monotonic()
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        con = _connect_read_only(db, max_wait, sleep)
    except (TimeoutError, OSError) as exc:
        entry.update(state="error", detail=str(exc))
        return entry
    import duckdb

    try:
        con.execute("BEGIN TRANSACTION")
        for schema, name in tables:
            exists = con.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
                [schema, name]).fetchone()[0]
            if not exists:
                entry["skipped_tables"].append(f"{schema}.{name}")
                continue
            rows = con.execute(f'SELECT count(*) FROM "{schema}"."{name}"').fetchone()[0]
            dst = out_dir / f"{schema}.{name}.parquet"
            part = out_dir / f".{schema}.{name}.parquet.part"
            part.unlink(missing_ok=True)
            target = str(part).replace("'", "''")
            con.execute(f"COPY (SELECT * FROM \"{schema}\".\"{name}\") TO '{target}' (FORMAT parquet)")
            copied = con.execute("SELECT count(*) FROM read_parquet(?)", [str(part)]).fetchone()[0]
            if copied != rows:
                part.unlink(missing_ok=True)
                raise RuntimeError(f"{schema}.{name}: {rows} rows in the database, {copied} in the parquet")
            part.replace(dst)
            entry["files"].append({
                "table": f"{schema}.{name}",
                "path": str(dst.resolve().relative_to(backup_dir.resolve())),
                "rows": rows,
                "bytes": dst.stat().st_size,
                "sha256": sha256_file(dst),
            })
        con.execute("COMMIT")
    except (duckdb.Error, RuntimeError, OSError) as exc:
        entry.update(state="error", detail=f"{type(exc).__name__}: {exc}")
        return entry
    finally:
        con.close()
    entry.update(state="ok", duration_s=round(time.monotonic() - started, 1))
    return entry


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("db", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--tables", required=True)
    ap.add_argument("--backup-dir", type=Path, required=True)
    ap.add_argument("--component", required=True)
    ap.add_argument("--max-wait", type=float, default=180)
    args = ap.parse_args(argv)
    try:
        tables = parse_tables(args.tables)
    except ValueError as exc:
        ap.error(str(exc))

    entry = export(args.db, args.out_dir, tables, args.backup_dir, args.component, args.max_wait)
    write_component(args.backup_dir, entry)
    if entry["state"] == "error":
        print(f"{args.component}: error: {entry['detail']}", file=sys.stderr)
        return 1
    if entry["state"] == "skipped":
        print(f"{args.component}: skipped: {entry['detail']}")
        return 0
    done = ", ".join(f"{f['table']} {f['rows']} rows" for f in entry["files"]) or "no table present"
    skipped = f"; skipped (absent): {', '.join(entry['skipped_tables'])}" if entry["skipped_tables"] else ""
    print(f"{args.component}: ok {done}{skipped}, {entry['duration_s']}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
