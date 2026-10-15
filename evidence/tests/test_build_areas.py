"""evidence/scripts/build-areas.sh with a stub `evidence` command: atomic switch, retention, status,
failure keeps the previous build, restart does not rebuild."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build-areas.sh"

STUB = """#!/bin/sh
# stub of `npx evidence`: `sources` does nothing, `build` writes ./build/index.html
case "$1" in
  sources) exit 0 ;;
  build)
    if [ -f pages/FAIL ]; then echo "boom" >&2; exit 3; fi
    mkdir -p build && echo "<html>theme ?? 'system'</html>" > build/index.html ;;
esac
"""


@pytest.fixture()
def env(tmp_path: Path) -> dict:
    for area in ("dieu-hanh",):
        d = tmp_path / "areas" / area
        (d / "pages").mkdir(parents=True)
        (d / "sources" / "datalake").mkdir(parents=True)
        (d / "evidence.config.yaml").write_text("deployment:\n  basePath: /dieu-hanh\n")
    legacy = tmp_path / "legacy"
    (legacy / "pages").mkdir(parents=True)
    (legacy / "sources" / "datalake").mkdir(parents=True)
    (legacy / "evidence.config.yaml").write_text("plugins: {}\n")
    (tmp_path / "olap.duckdb").write_text("catalog")
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "node_modules").mkdir()
    stub = tmp_path / "evidence-stub"
    stub.write_text(STUB)
    stub.chmod(0o755)
    return {
        **os.environ,
        "AREAS_DIR": str(tmp_path / "areas"), "LEGACY_DIR": str(legacy), "SITE_DIR": str(tmp_path / "site"),
        "REQUEST_DIR": str(tmp_path / "req"), "OLAP_DB": str(tmp_path / "olap.duckdb"),
        "NODE_MODULES": str(tmp_path / "node_modules"), "PACKAGE_JSON": str(tmp_path / "package.json"),
        "WORK_DIR": str(tmp_path / "work"), "EVIDENCE_CMD": str(stub), "KEEP_BUILDS": "2",
        "AREA_TIMEOUT": "30", "POLL_SECONDS": "1",
    }


def _run(env, *args, timeout=60):
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, timeout=timeout)


def test_once_builds_every_area_and_writes_status(env):
    res = _run(env, "--once")
    assert res.returncode == 0, res.stdout + res.stderr
    site = Path(env["SITE_DIR"])
    for area in ("dieu-hanh", "legacy"):
        current = site / area / "current"
        assert current.is_symlink() and os.readlink(current).startswith("builds/")
        html = (current / "index.html").read_text()
        assert "?? 'dark'" in html  # theme patch applied
    status = json.loads((Path(env["REQUEST_DIR"]) / "status.json").read_text())
    assert status["ok"] is True and set(status["areas"]) == {"dieu-hanh", "legacy"}
    assert status["request_id"].startswith("manual-")


def test_failed_area_keeps_previous_build(env, tmp_path):
    assert _run(env, "--once").returncode == 0
    site = Path(env["SITE_DIR"])
    before = os.readlink(site / "dieu-hanh" / "current")
    (Path(env["AREAS_DIR"]) / "dieu-hanh" / "pages" / "FAIL").write_text("")
    import time
    time.sleep(1.1)  # build ids have one-second resolution
    res = _run(env, "--once")
    assert res.returncode != 0
    assert os.readlink(site / "dieu-hanh" / "current") == before
    status = json.loads((Path(env["REQUEST_DIR"]) / "status.json").read_text())
    assert status["ok"] is False
    assert status["areas"]["dieu-hanh"]["ok"] is False and "failed" in status["areas"]["dieu-hanh"]["error"]
    assert status["areas"]["legacy"]["ok"] is True


def test_retention_keeps_newest_builds(env):
    import time
    for _ in range(3):
        assert _run(env, "--once").returncode == 0
        time.sleep(1.1)
    builds = sorted(os.listdir(Path(env["SITE_DIR"]) / "legacy" / "builds"))
    assert len(builds) == 2
    assert os.readlink(Path(env["SITE_DIR"]) / "legacy" / "current") == f"builds/{builds[-1]}"


def test_loop_does_not_rebuild_on_restart_and_builds_new_requests(env):
    assert _run(env, "--once").returncode == 0
    site = Path(env["SITE_DIR"])
    before = os.readlink(site / "legacy" / "current")
    # restart: current exists, no request -> waits without building
    proc = subprocess.Popen(["bash", str(SCRIPT)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        import time
        time.sleep(2.5)
        assert os.readlink(site / "legacy" / "current") == before
        req = Path(env["REQUEST_DIR"])
        req.mkdir(exist_ok=True)
        (req / "request.json").write_text(json.dumps({"request_id": "nightly-1", "requested_at": "x"}))
        deadline = time.time() + 20
        while time.time() < deadline:
            status = req / "status.json"
            if status.exists() and json.loads(status.read_text())["request_id"] == "nightly-1":
                break
            time.sleep(0.5)
        assert json.loads((req / "status.json").read_text())["request_id"] == "nightly-1"
        assert (site / ".last_request_id").read_text().strip() == "nightly-1"
    finally:
        proc.terminate()
        out, _ = proc.communicate(timeout=10)
    assert "current exists for every area" in out


def test_second_builder_refuses_to_run(env):
    site = Path(env["SITE_DIR"])
    site.mkdir()
    holder = subprocess.Popen(["bash", "-c", f"exec 9>{site}/.build.lock; flock 9; sleep 5"])
    try:
        import time
        time.sleep(0.5)
        res = _run(env, "--once")
        assert res.returncode == 1 and "another build is running" in res.stdout
    finally:
        holder.kill()
