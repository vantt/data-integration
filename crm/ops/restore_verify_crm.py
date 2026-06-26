"""Restore-verify drill: prove a CRM backup can bootstrap a fresh, correct app.

Two run modes (auto-detected from env):

* **Sidecar mode** (production, via `crm_drill_runner`): set when
  `CRM_VERIFY_DATA_DIR` + `CRM_VERIFY_DATA_VOLUME` + `CRM_BACKUPS_DIR` are present.
  The runner has the `crm_backups` + `crm_verify_data` volumes mounted locally and
  the Docker socket, so it reads/writes those volumes directly and spins the
  ephemeral CRM as a sibling container (mounting the named volume by name).
* **Host mode** (dev/manual): `python crm/ops/restore_verify_crm.py` — uses a host
  temp dir + an `alpine` helper to export the backup out of the `crm_backups` volume.

Gates (both modes):
  A. FILE INTEGRITY (pre-boot): restored DBs match the backup manifest
     (sha256 + content checksums + row counts + integrity).
  B. FUNCTIONAL: boot a throwaway CRM (`CRM_VERIFY_MODE=1`, isolated name/port,
     NO prod crm_data/caddy_net/Caddy-label/data_lake) → serves reads + a real write.

Requires the crm image to have the `CRM_VERIFY_MODE` gate baked into its entrypoint
(Phase 6 rebuild) — the drill no longer mounts entrypoint.sh.

Prod safety: prod `crm` / `crm_data` are never mounted/written; prod `crm.db`
size+mtime is asserted unchanged before vs after.
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
VERIFY_PORT = int(os.environ.get("CRM_VERIFY_PORT", "18090"))  # MUST differ from prod 3007
BACKUP_VOL = "crm_backups"

# Sidecar mode: the runner has crm_backups + crm_verify_data mounted locally AND the
# Docker socket. It reads/writes those volumes directly and boots the ephemeral CRM by
# mounting the named volume (resolved on the host daemon — a host-bind path from a
# socket-mounted container would NOT translate). Set by the compose env.
VERIFY_DATA_DIR = os.environ.get("CRM_VERIFY_DATA_DIR")        # local mount of crm_verify_data
BACKUPS_DIR = os.environ.get("CRM_BACKUPS_DIR")               # local mount of crm_backups
VERIFY_DATA_VOLUME = os.environ.get("CRM_VERIFY_DATA_VOLUME")  # optional override of -v boot volume
VERIFY_VOL = "crm_verify_data"
SIDECAR = bool(VERIFY_DATA_DIR and BACKUPS_DIR)

_cleanup_paths: list[Path] = []


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, capture_output=True, text=True)


def _cleanup() -> None:
    subprocess.run(["docker", "rm", "-f", VERIFY_NAME], capture_output=True, text=True)
    if SIDECAR and VERIFY_DATA_DIR:
        for f in Path(VERIFY_DATA_DIR).glob("*"):
            try:
                f.unlink()
            except OSError:
                pass
    for p in _cleanup_paths:
        shutil.rmtree(p, ignore_errors=True)


def _fail(msg: str) -> "NoReturn":  # type: ignore[name-defined]
    print(f"\n[FAIL] DRILL FAILED: {msg}")
    sys.exit(1)


def _resolve_named_volume(suffix: str) -> str:
    """Find the compose-prefixed volume (`<project>_<suffix>`), else the bare name."""
    names = _run(["docker", "volume", "ls", "--format", "{{.Name}}"]).stdout.split()
    prefixed = [n for n in names if n.endswith(f"_{suffix}")]
    if prefixed:
        return prefixed[0]
    if suffix in names:
        return suffix
    _fail(f"no '{suffix}' volume found")


def _resolve_backup_volume() -> str:
    return _resolve_named_volume(BACKUP_VOL)


# --------------------------------------------------------------------------- #
def latest_backup() -> str:
    if SIDECAR:
        stamps = sorted(p.name for p in Path(BACKUPS_DIR).iterdir() if p.is_dir() and p.name[:8].isdigit())
    else:
        out = _run(["docker", "run", "--rm", "-v", f"{_resolve_backup_volume()}:/b", "alpine",
                    "sh", "-c", "ls -1 /b"]).stdout
        stamps = sorted(s for s in out.split() if s[:8].isdigit())
    if not stamps:
        _fail("no backups found")
    return stamps[-1]


def export_backup(ts: str) -> tuple[Path, str, dict]:
    """Returns (gate_a_dir, boot_mount, manifest). boot_mount = volume name (sidecar)
    or host dir (host mode) for `docker run -v <boot_mount>:/data`."""
    if SIDECAR:
        src = Path(BACKUPS_DIR) / ts
        dst = Path(VERIFY_DATA_DIR)
        for f in dst.glob("*"):
            f.unlink()
        for db in ("crm.db", "cache.db"):
            if (src / db).exists():
                shutil.copy2(src / db, dst / db)
        manifest = json.loads((src / "manifest.json").read_text())
        boot_vol = VERIFY_DATA_VOLUME or _resolve_named_volume(VERIFY_VOL)
        return dst, boot_vol, manifest
    # host mode: export via alpine helper to a host temp dir
    dest = REPO / "app_data" / "crm_verify_tmp" / ts
    dest.mkdir(parents=True, exist_ok=True)
    _cleanup_paths.append(dest)
    _run(["docker", "run", "--rm", "-v", f"{_resolve_backup_volume()}:/b:ro",
          "-v", f"{dest}:/out", "alpine",
          "sh", "-c", f"cp /b/{ts}/*.db /b/{ts}/manifest.json /out/"])
    return dest, str(dest), json.loads((dest / "manifest.json").read_text())


def gate_a_integrity(data_dir: Path, manifest: dict) -> None:
    print("-- Gate A: file integrity (pre-boot) --")
    for db, info in manifest["dbs"].items():
        if not info.get("ok"):
            print(f"   {db}: skipped (manifest marks it failed/partial)")
            continue
        path = data_dir / db
        if not path.exists():
            _fail(f"{db} missing from exported backup")
        try:
            prof = backup_crm.profile_db(path)
        except Exception as e:
            _fail(f"{db}: cannot open/profile restored DB ({e})")
        expected = info["snapshot"]
        if prof["sha256"] != expected["sha256"]:
            _fail(f"{db}: sha256 mismatch vs manifest (file changed since backup)")
        if prof["integrity_check"] != "ok":
            _fail(f"{db}: integrity_check = {prof['integrity_check']}")
        diffs = backup_crm._tables_match(expected, prof)
        if diffs:
            _fail(f"{db}: content diverges from manifest: {diffs}")
        nrows = sum(t["rows"] for t in prof["tables"].values())
        print(f"   {db}: OK (sha+checksums+counts match; {nrows} rows, head={prof['migration_head']})")


def prod_db_fingerprint() -> str | None:
    r = subprocess.run(["docker", "exec", "crm", "stat", "-c", "%s-%Y", "/data/crm.db"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def gate_b_functional(boot_mount: str, image: str, manifest: dict) -> None:
    print("-- Gate B: functional boot (isolated) --")
    subprocess.run(["docker", "rm", "-f", VERIFY_NAME], capture_output=True, text=True)
    # Isolated: distinct name; CRM_VERIFY_MODE gate is BAKED into the image (no entrypoint
    # mount); NO crm_data mount, NO Caddy label, NO prod data_lake → prod untouched.
    run_cmd = ["docker", "run", "-d", "--name", VERIFY_NAME,
               "-v", f"{boot_mount}:/data",
               "-e", "CRM_VERIFY_MODE=1", "-e", "CRM_DATA_DIR=/data", "-e", "CRM_PORT=8090"]
    if SIDECAR:
        # The drill runs INSIDE the sidecar, so a host-published port is NOT reachable as
        # localhost here. Join caddy_net (shared with the sidecar) and reach the ephemeral
        # by name. No Caddy label → Caddy never routes to it, so isolation still holds.
        run_cmd += ["--network", "caddy_net"]
        base = f"http://{VERIFY_NAME}:8090"
    else:
        # Host mode (dev): publish to a distinct host port and reach via localhost.
        run_cmd += ["-p", f"{VERIFY_PORT}:8090"]
        base = f"http://localhost:{VERIFY_PORT}"
    _run(run_cmd + [image])
    _poll_health(base)
    parties = manifest["dbs"]["crm.db"]["snapshot"]["tables"].get("crm_party", {}).get("rows", 0)
    _get(base, "/healthz", 200)
    _get(base, "/api/dedup/candidates", 200)
    print(f"   reads OK; manifest crm_party rows = {parties}")
    _assert_writable()


def _poll_health(base: str, timeout: int = 120) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base}/healthz", timeout=5) as r:
                if r.status == 200:
                    print("   /healthz: ready")
                    return
        except Exception:
            time.sleep(3)
    logs = subprocess.run(["docker", "logs", "--tail", "30", VERIFY_NAME], capture_output=True, text=True)
    _fail(f"ephemeral CRM never became healthy.\n{logs.stdout}\n{logs.stderr}")


def _get(base: str, path: str, expect: int) -> None:
    try:
        with urllib.request.urlopen(f"{base}{path}", timeout=10) as r:
            if r.status != expect:
                _fail(f"GET {path} -> {r.status} (expected {expect})")
    except urllib.error.HTTPError as e:
        if e.code != expect:
            _fail(f"GET {path} -> {e.code} (expected {expect})")


def _assert_writable() -> None:
    """Real write to the restored DB inside the running app container (non-vacuous)."""
    code = ("import sqlite3;c=sqlite3.connect('/data/crm.db');"
            "c.execute('CREATE TABLE IF NOT EXISTS _verify_probe(x INTEGER)');"
            "c.execute('INSERT INTO _verify_probe VALUES(1)');"
            "c.execute('DELETE FROM _verify_probe');c.execute('DROP TABLE _verify_probe');"
            "c.commit();c.close();print('WRITABLE')")
    r = subprocess.run(["docker", "exec", VERIFY_NAME, "python3", "-c", code], capture_output=True, text=True)
    if "WRITABLE" not in (r.stdout or ""):
        _fail(f"restored DB not writable in app container: {(r.stderr or r.stdout or '').strip()}")
    print("   write probe: OK (create/insert/delete/drop on restored crm.db in the running app container)")


# --------------------------------------------------------------------------- #
def _tamper(data_dir: Path, kind: str) -> None:
    db = data_dir / "crm.db"
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
    ap.add_argument("--negative", choices=["row", "value", "truncate", "file"])
    args = ap.parse_args(argv)

    atexit.register(_cleanup)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: (_cleanup(), sys.exit(130)))

    print(f"Restore-verify drill ({'sidecar' if SIDECAR else 'host'} mode)")
    ts = latest_backup() if args.backup == "latest" else args.backup
    print(f"  backup {ts}")
    image = _run(["docker", "inspect", "crm", "--format", "{{.Image}}"]).stdout.strip()
    prod_before = prod_db_fingerprint()

    gate_a_dir, boot_mount, manifest = export_backup(ts)

    if args.negative:
        _tamper(gate_a_dir, args.negative)
        try:
            gate_a_integrity(gate_a_dir, manifest)
            gate_b_functional(boot_mount, image, manifest)
        except SystemExit as e:
            if e.code == 1:
                print(f"\n[PASS] NEGATIVE TEST PASS: tamper '{args.negative}' correctly caught.")
                return 0
            raise
        _fail(f"NEGATIVE TEST FAIL: tamper '{args.negative}' NOT caught — checks are vacuous!")

    gate_a_integrity(gate_a_dir, manifest)
    gate_b_functional(boot_mount, image, manifest)

    prod_after = prod_db_fingerprint()
    if prod_before != prod_after:
        _fail(f"prod crm.db CHANGED during drill ({prod_before} -> {prod_after}) — isolation breach!")
    print(f"-- Prod untouched: crm.db fingerprint stable ({prod_before}) --")
    print(f"\n[PASS] DRILL PASS - backup {ts} restores to a working CRM with correct data.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
