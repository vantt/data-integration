"""Consistent local backup: SQLite and DuckDB snapshots, manifest, backup.sh, unit templates.

Run:
  python -m pytest scripts/tests/test_backup_snapshots.py -q
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import duckdb
import pytest

REPO = Path(__file__).resolve().parents[2]
BACKUP_SCRIPTS = REPO / "scripts" / "backup"
if str(BACKUP_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(BACKUP_SCRIPTS))

import backup_manifest  # noqa: E402
import duckdb_snapshot  # noqa: E402
import sqlite_snapshot  # noqa: E402

PARITY = "main.monitor_taxonomy_parity_log"


def _make_wal_db(path: Path, rows: int) -> None:
    con = sqlite3.connect(path)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("CREATE TABLE ingestion_runs (id INTEGER PRIMARY KEY, asset_key TEXT)")
    con.executemany("INSERT INTO ingestion_runs (asset_key) VALUES (?)", [(f"a{i}",) for i in range(rows)])
    con.commit()
    con.close()


def _hold(script: str, ready: Path) -> subprocess.Popen:
    """Run a helper process that signals readiness by creating ``ready``."""
    proc = subprocess.Popen([sys.executable, "-c", script])
    deadline = time.monotonic() + 30
    while not ready.exists():
        if proc.poll() is not None or time.monotonic() > deadline:
            proc.kill()
            raise RuntimeError("helper process did not start")
        time.sleep(0.05)
    return proc


def _make_warehouse(path: Path, rows: int) -> None:
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE monitor_taxonomy_parity_log (run_at TIMESTAMP, domain VARCHAR, n_label_diff INTEGER)")
    con.execute(f"INSERT INTO monitor_taxonomy_parity_log SELECT now(), 'customer_type', i FROM range({rows}) t(i)")
    con.close()


# --- sqlite_snapshot ---------------------------------------------------------------------

def test_sqlite_snapshot_of_wal_db_with_open_writer(tmp_path):
    src = tmp_path / "ingestion_health.db"
    _make_wal_db(src, 50)
    ready = tmp_path / "ready"
    # Another process inserts 10 rows inside a write transaction it keeps open.
    writer = _hold(textwrap.dedent(f"""
        import sqlite3, time, pathlib
        con = sqlite3.connect({str(src)!r}, isolation_level=None)
        con.execute("BEGIN IMMEDIATE")
        con.executemany("INSERT INTO ingestion_runs (asset_key) VALUES (?)", [("open",)] * 10)
        pathlib.Path({str(ready)!r}).touch()
        time.sleep(30)
    """), ready)
    try:
        backup_dir = tmp_path / "bk"
        dst = backup_dir / "app_data" / "monitoring" / "ingestion_health.db"
        entry = sqlite_snapshot.snapshot(src, dst, backup_dir, "monitoring")
    finally:
        writer.kill()
        writer.wait()
    assert entry["state"] == "ok", entry
    f = entry["files"][0]
    assert f["path"] == "app_data/monitoring/ingestion_health.db"
    assert f["integrity_check"] == "ok"
    assert f["tables"] == {"ingestion_runs": 50}  # uncommitted rows are not in the snapshot
    con = sqlite3.connect(dst)
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "delete"  # self-contained file
    con.close()
    assert not dst.with_name(dst.name + ".part").exists()


def test_sqlite_snapshot_skips_missing_source(tmp_path):
    entry = sqlite_snapshot.snapshot(tmp_path / "nope.db", tmp_path / "bk" / "x.db", tmp_path / "bk", "dagster_home")
    assert entry["state"] == "skipped"


def test_sqlite_snapshot_rejects_corrupt_source(tmp_path):
    src = tmp_path / "bad.db"
    src.write_bytes(b"not a database" * 100)
    backup_dir = tmp_path / "bk"
    dst = backup_dir / "bad.db"
    entry = sqlite_snapshot.snapshot(src, dst, backup_dir, "bad")
    assert entry["state"] == "error"
    assert not dst.exists()


# --- duckdb_snapshot ---------------------------------------------------------------------

def test_duckdb_export_one_table_and_skip_missing(tmp_path):
    db = tmp_path / "sapo_warehouse.duckdb"
    _make_warehouse(db, 82)
    backup_dir = tmp_path / "bk"
    out = backup_dir / "exports" / "warehouse"
    entry = duckdb_snapshot.export(db, out, duckdb_snapshot.parse_tables(f"{PARITY},main.no_such_table"),
                                   backup_dir, "exports_warehouse")
    assert entry["state"] == "ok", entry
    assert entry["skipped_tables"] == ["main.no_such_table"]
    [f] = entry["files"]
    assert f["table"] == PARITY and f["rows"] == 82
    assert f["path"] == "exports/warehouse/main.monitor_taxonomy_parity_log.parquet"
    rows = duckdb.connect().execute("SELECT count(*) FROM read_parquet(?)", [str(backup_dir / f["path"])]).fetchone()[0]
    assert rows == 82


def test_duckdb_export_skips_missing_database(tmp_path):
    entry = duckdb_snapshot.export(tmp_path / "none.duckdb", tmp_path / "out", [("main", "t")], tmp_path, "x")
    assert entry["state"] == "skipped"


def test_parse_tables_rejects_injection():
    with pytest.raises(ValueError):
        duckdb_snapshot.parse_tables("main.t; DROP TABLE x")
    assert duckdb_snapshot.parse_tables("t") == [("main", "t")]


def _lock_holder(db: Path, ready: Path, seconds: float) -> subprocess.Popen:
    return _hold(textwrap.dedent(f"""
        import duckdb, time, pathlib
        con = duckdb.connect({str(db)!r})
        pathlib.Path({str(ready)!r}).touch()
        time.sleep({seconds})
        con.close()
    """), ready)


def test_duckdb_export_retries_until_writer_closes(tmp_path):
    db = tmp_path / "w.duckdb"
    _make_warehouse(db, 5)
    holder = _lock_holder(db, tmp_path / "ready", 2)
    try:
        entry = duckdb_snapshot.export(db, tmp_path / "bk" / "out", [("main", "monitor_taxonomy_parity_log")],
                                       tmp_path / "bk", "exports_warehouse", max_wait=60)
    finally:
        holder.wait(timeout=30)
    assert entry["state"] == "ok", entry
    assert entry["files"][0]["rows"] == 5


def test_duckdb_export_gives_up_after_max_wait(tmp_path):
    db = tmp_path / "w.duckdb"
    _make_warehouse(db, 5)
    holder = _lock_holder(db, tmp_path / "ready", 60)
    waits: list[float] = []
    try:
        entry = duckdb_snapshot.export(db, tmp_path / "bk" / "out", [("main", "monitor_taxonomy_parity_log")],
                                       tmp_path / "bk", "exports_warehouse", max_wait=180, sleep=waits.append)
    finally:
        holder.kill()
        holder.wait()
    assert entry["state"] == "error"
    assert "still locked" in entry["detail"]
    assert waits[:4] == [3.0, 6.0, 12.0, 24.0] and max(waits) == 30.0 and sum(waits) <= 180


# --- manifest ----------------------------------------------------------------------------

def _backup_with_components(tmp_path) -> Path:
    backup_dir = tmp_path / "20261015-010441"
    src = tmp_path / "src.db"
    _make_wal_db(src, 20)
    backup_manifest.write_component(backup_dir, sqlite_snapshot.snapshot(
        src, backup_dir / "app_data" / "monitoring" / "ingestion_health.db", backup_dir, "monitoring"))
    db = tmp_path / "wh.duckdb"
    _make_warehouse(db, 7)
    backup_manifest.write_component(backup_dir, duckdb_snapshot.export(
        db, backup_dir / "exports" / "warehouse", [("main", "monitor_taxonomy_parity_log")], backup_dir,
        "exports_warehouse"))
    (backup_dir / "app_data" / "input_source").mkdir(parents=True)
    (backup_dir / "app_data" / "input_source" / "a.csv").write_text("x\n")
    backup_manifest.write_component(backup_dir, backup_manifest.dir_entry(
        backup_dir, "input_source", "app_data/input_source", "source_of_truth"))
    backup_manifest.assemble(backup_dir)
    return backup_dir


def test_manifest_assemble_and_verify(tmp_path, monkeypatch):
    monkeypatch.setenv("BACKUP_GIT_SHA", "abc123")
    backup_dir = _backup_with_components(tmp_path)
    manifest = json.loads((backup_dir / "manifest.json").read_text())
    assert manifest["git_sha"] == "abc123"
    assert {c["component"] for c in manifest["components"]} == {"monitoring", "exports_warehouse", "input_source"}
    assert {c["component"]: c["role"] for c in manifest["components"]}["input_source"] == "source_of_truth"
    assert not (backup_dir / ".components").exists()
    assert backup_manifest.verify(backup_dir) == []


def test_verify_catches_a_deleted_row(tmp_path):
    backup_dir = _backup_with_components(tmp_path)
    con = sqlite3.connect(backup_dir / "app_data" / "monitoring" / "ingestion_health.db")
    con.execute("DELETE FROM ingestion_runs WHERE id = 1")
    con.commit()
    con.close()
    problems = backup_manifest.verify(backup_dir)
    assert any("monitoring" in p and "sha256" in p for p in problems)
    assert any("monitoring" in p and "row counts" in p for p in problems)


def test_verify_catches_a_shortened_parquet(tmp_path):
    backup_dir = _backup_with_components(tmp_path)
    pq = backup_dir / "exports" / "warehouse" / "main.monitor_taxonomy_parity_log.parquet"
    con = duckdb.connect()
    con.execute(f"COPY (SELECT * FROM read_parquet('{pq}') LIMIT 3) TO '{pq}.new' (FORMAT parquet)")
    os.replace(f"{pq}.new", pq)
    problems = backup_manifest.verify(backup_dir)
    assert any("exports_warehouse" in p and "row count" in p for p in problems)


def test_status_file_lists_component_states(tmp_path):
    backup_dir = _backup_with_components(tmp_path)
    status = backup_manifest.write_status(tmp_path / "status" / "local.json", "partial", 12, backup_dir,
                                          ["monitoring snapshot failed"])
    on_disk = json.loads((tmp_path / "status" / "local.json").read_text())
    assert on_disk == status
    assert on_disk["ok"] is False and on_disk["state"] == "partial"
    assert on_disk["components"]["exports_warehouse"] == "ok"


# --- backup.sh end to end (Docker layout) -------------------------------------------------

def _data_root(tmp_path: Path) -> Path:
    root = tmp_path / "var"
    lake = root / "data_lake"
    (lake / "sapo_v2_raw" / "order").mkdir(parents=True)
    (lake / "sapo_v2_raw" / "order" / "part-0.parquet").write_bytes(b"PAR1")
    (lake / "monitoring").mkdir()
    _make_wal_db(lake / "monitoring" / "ingestion_health.db", 30)
    (lake / "monitoring" / "desktop.ini").write_text("x")
    _make_warehouse(lake / "sapo_warehouse.duckdb", 4)
    dh = root / "dagster_home"
    (dh / "schedules").mkdir(parents=True)
    _make_wal_db(dh / "schedules" / "schedules.db", 12)
    (dh / "dagster.yaml").write_text("telemetry:\n  enabled: false\n")
    (dh / "history" / "runs").mkdir(parents=True)
    (dh / "history" / "runs" / "index.db").write_bytes(b"x" * 1000)
    (dh / "storage" / "run-1").mkdir(parents=True)
    (root / "input_source" / "misa").mkdir(parents=True)
    (root / "input_source" / "misa" / "a.xlsx").write_bytes(b"xlsx")
    return root


def _run_backup(tmp_path: Path, data_root: Path) -> subprocess.CompletedProcess:
    project = tmp_path / "project"  # no app_data/ inside: the Docker branch runs
    project.mkdir(exist_ok=True)
    (project / "docker-compose.yml").write_text("services: {}\n")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("METABASE_", "BACKUP_"))}
    env.update(BACKUP_ROOT=str(tmp_path / "backups"), BACKUP_PROJECT_ROOT=str(project), DATA_ROOT=str(data_root))
    return subprocess.run(["bash", str(BACKUP_SCRIPTS / "backup.sh")], env=env, capture_output=True, text=True,
                          timeout=300)


def test_backup_sh_docker_layout(tmp_path):
    data_root = _data_root(tmp_path)
    res = _run_backup(tmp_path, data_root)
    assert res.returncode == 0, res.stdout + res.stderr
    [bk] = [p for p in (tmp_path / "backups").iterdir() if p.is_dir() and p.name[0].isdigit()]
    app = bk / "app_data"
    assert (app / "data_lake" / "sapo_v2_raw" / "order" / "part-0.parquet").is_file()
    assert not (app / "data_lake" / "monitoring").exists()  # live SQLite volume is not file-copied
    assert (app / "monitoring" / "ingestion_health.db").is_file()
    assert not (app / "monitoring" / "desktop.ini").exists()
    assert (app / "dagster_home" / "schedules" / "schedules.db").is_file()
    assert (app / "dagster_home" / "dagster.yaml").is_file()
    assert not (app / "dagster_home" / "history").exists()
    assert not (app / "dagster_home" / "storage").exists()
    assert (app / "input_source" / "misa" / "a.xlsx").is_file()
    assert (bk / "exports" / "warehouse" / "main.monitor_taxonomy_parity_log.parquet").is_file()
    manifest = json.loads((bk / "manifest.json").read_text())
    roles = {c["component"]: c["role"] for c in manifest["components"]}
    assert roles["data_lake/sapo_warehouse.duckdb"] == "accelerator"
    assert roles["data_lake/sapo_v2_raw"] == "source_of_truth"
    states = {c["component"]: c["state"] for c in manifest["components"]}
    assert states["monitoring"] == states["dagster_home"] == states["exports_warehouse"] == "ok"
    assert backup_manifest.verify(bk) == []
    status = json.loads((tmp_path / "backups" / "status" / "local.json").read_text())
    assert status["state"] == "ok" and status["ok"] is True and status["backup_dir"] == bk.name


def test_backup_sh_removes_secret_files_and_reports_partial(tmp_path):
    data_root = _data_root(tmp_path)
    (data_root / "data_lake" / "sapo_v2_raw" / ".env.docker").write_text("SECRET=1\n")
    res = _run_backup(tmp_path, data_root)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "SECRET=1" not in res.stdout + res.stderr
    [bk] = [p for p in (tmp_path / "backups").iterdir() if p.is_dir() and p.name[0].isdigit()]
    assert not list(bk.rglob(".env*"))
    status = json.loads((tmp_path / "backups" / "status" / "local.json").read_text())
    assert status["state"] == "partial"
    assert any("secret" in e for e in status["errors"])


def test_backup_sh_failed_run_writes_failed_status(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    res = _run_backup(tmp_path, empty)
    assert res.returncode != 0
    status = json.loads((tmp_path / "backups" / "status" / "local.json").read_text())
    assert status["state"] == "failed" and status["backup_dir"] is None
    assert not [p for p in (tmp_path / "backups").iterdir() if p.is_dir() and p.name[0].isdigit()]


# --- systemd unit templates ---------------------------------------------------------------

def test_install_units_renders_without_hardcoded_home(tmp_path):
    unit_dir = tmp_path / "units"
    res = subprocess.run(["bash", str(BACKUP_SCRIPTS / "install-units.sh"), "--project-root", str(REPO),
                          "--unit-dir", str(unit_dir)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stdout + res.stderr
    service = (unit_dir / "metabase-cold-backup.service").read_text()
    timer = (unit_dir / "metabase-cold-backup.timer").read_text()
    assert f"ExecStart={REPO}/scripts/backup/metabase_cold_backup.sh nightly" in service
    assert "OnCalendar=*-*-* 00:30:00 Asia/Ho_Chi_Minh" in timer
    for text in (service, timer):
        assert "@FG_PROJECT_ROOT@" not in text
        if not str(REPO).startswith("/home/vantt"):
            assert "/home/vantt" not in text


def test_install_units_refuses_a_non_checkout(tmp_path):
    res = subprocess.run(["bash", str(BACKUP_SCRIPTS / "install-units.sh"), "--project-root", str(tmp_path),
                          "--unit-dir", str(tmp_path / "u")], capture_output=True, text=True, timeout=60)
    assert res.returncode == 2
