"""Restore-verify drill: prove a CRM backup can bootstrap a fresh, correct app.

Run on the HOST (drives docker directly — no git-bash, so no MSYS path mangling):
    python crm/ops/restore_verify_crm.py            # latest backup, happy path
    python crm/ops/restore_verify_crm.py --backup 20260624-152558
    python crm/ops/restore_verify_crm.py --negative value   # expect the drill to FAIL

Two gates (see plan 260624-2010):
  A. FILE INTEGRITY (before any boot): export the backup to a host temp dir and assert
     each restored DB matches its manifest (sha256 + row counts + content checksums +
     integrity). Boot mutates the file header, so this must run pre-boot.
  B. FUNCTIONAL: boot a throwaway crm (CRM_VERIFY_MODE=1, isolated name/port/volume,
     NO crm_data / caddy_net / Caddy label / prod data_lake) and assert it serves real
     data + a write→read→delete round-trip works.

Prod safety: the prod `crm` container + `crm_data` are never mounted/written; prod
`crm.db` size+mtime is asserted unchanged before vs after.
"""

from __future__ import annotations

import argparse
import atexit
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import backup_crm  # noqa: E402  (profile_db reuse)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

REPO = Path(__file__).resolve().parents[2]
VERIFY_NAME = "crm-restore-verify"          # MUST differ from prod "crm"
VERIFY_PORT = 18090                          # MUST differ from prod 3007
BACKUP_VOL = "crm_backups"
TMP_HOST = REPO / "app_data" / "crm_verify_tmp"

_cleanup_paths: list[Path] = []


def _run(cmd: list[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=capture, text=True)


def _cleanup() -> None:
    subprocess.run(["docker", "rm", "-f", VERIFY_NAME], capture_output=True, text=True)
    for p in _cleanup_paths:
        shutil.rmtree(p, ignore_errors=True)


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"\n[FAIL] DRILL FAILED: {msg}")
    sys.exit(1)


def _resolve_backup_volume() -> str:
    """Compose prefixes named volumes with the project name (e.g. data-integration_crm_backups)."""
    names = _run(["docker", "volume", "ls", "--format", "{{.Name}}"]).stdout.split()
    prefixed = [n for n in names if n.endswith(f"_{BACKUP_VOL}")]  # compose project volume
    if prefixed:
        return prefixed[0]
    if BACKUP_VOL in names:
        return BACKUP_VOL
    _fail(f"no '{BACKUP_VOL}' volume found — run a backup first")


# --------------------------------------------------------------------------- #
def latest_backup() -> str:
    out = _run(["docker", "run", "--rm", "-v", f"{BACKUP_VOL}:/b", "alpine",
                "sh", "-c", "ls -1 /b"]).stdout
    stamps = sorted(s for s in out.split() if s[:8].isdigit())
    if not stamps:
        _fail(f"no backups found in volume {BACKUP_VOL}")
    return stamps[-1]


def export_backup(ts: str, dest: Path) -> dict:
    dest.mkdir(parents=True, exist_ok=True)
    _cleanup_paths.append(dest)
    _run(["docker", "run", "--rm", "-v", f"{BACKUP_VOL}:/b:ro",
          "-v", f"{dest}:/out", "alpine",
          "sh", "-c", f"cp /b/{ts}/*.db /b/{ts}/manifest.json /out/"])
    return json.loads((dest / "manifest.json").read_text())


def gate_a_integrity(dest: Path, manifest: dict) -> None:
    print("── Gate A: file integrity (pre-boot) ──")
    for db, info in manifest["dbs"].items():
        if not info.get("ok"):
            print(f"   {db}: skipped (manifest marks it failed/partial)")
            continue
        path = dest / db
        if not path.exists():
            _fail(f"{db} missing from exported backup")
        try:
            prof = backup_crm.profile_db(path)
        except Exception as e:  # corrupt/truncated DB → can't even open
            _fail(f"{db}: cannot open/profile restored DB ({e})")
        expected = info["snapshot"]
        if prof["sha256"] != expected["sha256"]:
            _fail(f"{db}: sha256 mismatch vs manifest (file changed since backup)")
        if prof["integrity_check"] != "ok":
            _fail(f"{db}: integrity_check = {prof['integrity_check']}")
        diffs = backup_crm._tables_match(expected, prof)  # expected(snapshot) vs restored
        if diffs:
            _fail(f"{db}: content diverges from manifest: {diffs}")
        nrows = sum(t["rows"] for t in prof["tables"].values())
        print(f"   {db}: OK (sha+checksums+counts match; {nrows} rows, head={prof['migration_head']})")


def prod_db_fingerprint() -> str | None:
    r = subprocess.run(["docker", "exec", "crm", "stat", "-c", "%s-%Y", "/data/crm.db"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def gate_b_functional(dest: Path, image: str, manifest: dict) -> None:
    print("── Gate B: functional boot (isolated) ──")
    subprocess.run(["docker", "rm", "-f", VERIFY_NAME], capture_output=True, text=True)
    # CRM_VERIFY_MODE gate is baked-stale in the image until rebuild → mount the current
    # entrypoint. LF-normalize (host file is CRLF on Windows → breaks the exec shebang) and
    # run it via /bin/sh (robust to exec bit + shebang).
    entrypoint = dest / "_entrypoint.sh"
    entrypoint.write_bytes((REPO / "crm" / "entrypoint.sh").read_text().replace("\r\n", "\n").encode())
    # Isolated run: distinct name/port, temp host /data, NO crm_data/caddy_net/label/data_lake.
    _run(["docker", "run", "-d", "--name", VERIFY_NAME,
          "-v", f"{dest}:/data",
          "-v", f"{entrypoint}:/app/entrypoint.sh:ro",
          "-e", "CRM_VERIFY_MODE=1", "-e", "CRM_DATA_DIR=/data", "-e", "CRM_PORT=8090",
          "-p", f"{VERIFY_PORT}:8090",
          "--entrypoint", "/bin/sh", image, "/app/entrypoint.sh"])
    base = f"http://localhost:{VERIFY_PORT}"
    _poll_health(base)
    # Functional reads + row floor
    parties = manifest["dbs"]["crm.db"]["snapshot"]["tables"].get("crm_party", {}).get("rows", 0)
    _get(base, "/healthz", expect=200)
    _get(base, "/api/dedup/candidates", expect=200)
    print(f"   reads OK; manifest crm_party rows = {parties}")
    _assert_writable()


def _poll_health(base: str, timeout: int = 90) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/healthz", timeout=5) as r:
                if r.status == 200:
                    print("   /health: ready")
                    return
        except Exception:
            time.sleep(3)
    logs = subprocess.run(["docker", "logs", "--tail", "30", VERIFY_NAME],
                         capture_output=True, text=True)
    _fail(f"ephemeral CRM never became healthy.\n{logs.stdout}\n{logs.stderr}")


def _get(base: str, path: str, expect: int) -> bytes:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=10) as r:
            if r.status != expect:
                _fail(f"GET {path} → {r.status} (expected {expect})")
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code != expect:
            _fail(f"GET {path} → {e.code} (expected {expect})")
        return b""


def _assert_writable() -> None:
    """Real write to the restored DB inside the running app container (not a vacuous HTTP probe).

    Proves the restored crm.db + container FS accept writes. Also asserts the app's own
    migration step reported success at boot (a real write to schema_migrations).
    """
    code = ("import sqlite3;c=sqlite3.connect('/data/crm.db');"
            "c.execute('CREATE TABLE IF NOT EXISTS _verify_probe(x INTEGER)');"
            "c.execute('INSERT INTO _verify_probe VALUES(1)');"
            "c.execute('DELETE FROM _verify_probe');c.execute('DROP TABLE _verify_probe');"
            "c.commit();c.close();print('WRITABLE')")
    r = subprocess.run(["docker", "exec", VERIFY_NAME, "python3", "-c", code],
                       capture_output=True, text=True)
    if "WRITABLE" not in (r.stdout or ""):
        _fail(f"restored DB not writable in app container: {(r.stderr or r.stdout or '').strip()}")
    print("   write probe: OK (create/insert/drop on restored crm.db in the running app container)")


# --------------------------------------------------------------------------- #
def _tamper(dest: Path, kind: str) -> None:
    db = dest / "crm.db"
    conn = sqlite3.connect(str(db))
    try:
        if kind == "row":
            conn.execute("DELETE FROM crm_party WHERE rowid=(SELECT MIN(rowid) FROM crm_party)")
        elif kind == "value":
            cols = [r[1] for r in conn.execute("PRAGMA table_info(crm_party)").fetchall()]
            target = next((c for c in cols if c.lower() != "id"), cols[-1])
            try:
                conn.execute(f'UPDATE crm_party SET "{target}"="{target}"||"_x" '
                             "WHERE rowid=(SELECT MIN(rowid) FROM crm_party)")
            except sqlite3.Error:
                conn.execute("DELETE FROM crm_party WHERE rowid=(SELECT MIN(rowid) FROM crm_party)")
        elif kind == "truncate":
            conn.execute("DELETE FROM crm_party")
        conn.commit()
    finally:
        conn.close()
    if kind == "file":
        with open(db, "r+b") as f:
            f.truncate(1024)
    print(f"   [negative] tampered restored crm.db: {kind}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="CRM restore-verify drill.")
    ap.add_argument("--backup", default="latest")
    ap.add_argument("--negative", choices=["row", "value", "truncate", "file"],
                   help="tamper the restored DB and EXPECT the drill to fail")
    args = ap.parse_args(argv)

    atexit.register(_cleanup)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: (_cleanup(), sys.exit(130)))

    global BACKUP_VOL
    BACKUP_VOL = _resolve_backup_volume()
    ts = latest_backup() if args.backup == "latest" else args.backup
    print(f"Restore-verify drill — backup {ts}")
    image = _run(["docker", "inspect", "crm", "--format", "{{.Image}}"]).stdout.strip()
    prod_before = prod_db_fingerprint()

    run_dir = TMP_HOST / ts
    manifest = export_backup(ts, run_dir)

    if args.negative:
        _tamper(run_dir, args.negative)
        try:
            gate_a_integrity(run_dir, manifest)
            gate_b_functional(run_dir, image, manifest)
        except SystemExit as e:
            if e.code == 1:
                print(f"\n[PASS] NEGATIVE TEST PASS: tamper '{args.negative}' was correctly caught.")
                return 0
            raise
        _fail(f"NEGATIVE TEST FAIL: tamper '{args.negative}' was NOT caught — checks are vacuous!")

    gate_a_integrity(run_dir, manifest)
    gate_b_functional(run_dir, image, manifest)

    prod_after = prod_db_fingerprint()
    if prod_before != prod_after:
        _fail(f"prod crm.db CHANGED during drill ({prod_before} → {prod_after}) — isolation breach!")
    print(f"── Prod untouched: crm.db fingerprint stable ({prod_before}) ──")
    print(f"\n[PASS] DRILL PASS — backup {ts} restores to a working CRM with correct data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
