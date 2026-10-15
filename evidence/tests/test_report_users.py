"""evidence/site/report-users.sh: per-area, per-person accounts; the password never lands in a file."""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "site" / "report-users.sh"
FAKE_HASH = "$2a$14$" + "A" * 53
PASSWORD = "correct horse battery"


@pytest.fixture()
def env(tmp_path: Path) -> dict:
    caddyfile = tmp_path / "Caddyfile"
    caddyfile.write_text("import /etc/caddy/users/dieu-hanh.caddy\nimport /etc/caddy/users/legacy.caddy\n")
    stub = tmp_path / "hash-stub"
    # reads the password on stdin (like `caddy hash-password`) and records it to prove it arrived there
    stub.write_text(f"#!/bin/sh\nread -r p\nprintf '%s' \"$p\" > {tmp_path}/seen\necho '{FAKE_HASH}'\n")
    stub.chmod(0o755)
    return {**os.environ, "REPORT_SITE_USERS_DIR": str(tmp_path / "users"), "REPORT_SITE_CADDYFILE": str(caddyfile),
            "REPORT_SITE_HASH_CMD": str(stub), "REPORT_SITE_RELOAD_CMD": "true"}


def _run(env, *args, stdin=""):
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, input=stdin, capture_output=True, text=True, timeout=30)


def test_add_stores_only_the_hash(env, tmp_path):
    res = _run(env, "add", "dieu-hanh", "an.nguyen", stdin=PASSWORD + "\n")
    assert res.returncode == 0, res.stderr
    file = tmp_path / "users" / "dieu-hanh.caddy"
    assert file.read_text() == f"an.nguyen {FAKE_HASH}\n"
    assert PASSWORD not in res.stdout + res.stderr
    assert (tmp_path / "seen").read_text() == PASSWORD  # passed on stdin, not as an argument
    assert stat.S_IMODE(file.stat().st_mode) == 0o600
    assert stat.S_IMODE((tmp_path / "users").stat().st_mode) == 0o700


def test_add_replaces_the_same_user_and_keeps_others(env, tmp_path):
    for user in ("an.nguyen", "binh", "an.nguyen"):
        assert _run(env, "add", "dieu-hanh", user, stdin=PASSWORD + "\n").returncode == 0
    lines = (tmp_path / "users" / "dieu-hanh.caddy").read_text().splitlines()
    assert sorted(line.split()[0] for line in lines) == ["an.nguyen", "binh"]


def test_remove_and_list(env, tmp_path):
    _run(env, "add", "dieu-hanh", "an.nguyen", stdin=PASSWORD + "\n")
    _run(env, "add", "legacy", "an.nguyen", stdin=PASSWORD + "\n")
    res = _run(env, "list")
    assert "dieu-hanh: an.nguyen" in res.stdout and "legacy: an.nguyen" in res.stdout
    assert FAKE_HASH not in res.stdout
    assert _run(env, "remove", "dieu-hanh", "an.nguyen").returncode == 0
    assert (tmp_path / "users" / "dieu-hanh.caddy").read_text() == ""
    assert _run(env, "remove", "dieu-hanh", "an.nguyen").returncode == 1
    assert "legacy: an.nguyen" in _run(env, "list").stdout


@pytest.mark.parametrize("args,stdin,msg", [
    (("add", "ban-hang", "an"), PASSWORD, "not in"),           # unknown area
    (("add", "dieu-hanh", "An Nguyen"), PASSWORD, "user name"),  # invalid user name
    (("add", "dieu-hanh", "an.nguyen"), "short", "shorter"),     # weak password
])
def test_rejects(env, args, stdin, msg):
    res = _run(env, *args, stdin=stdin + "\n")
    assert res.returncode == 1 and msg in res.stderr


def test_hash_failure_writes_nothing(env, tmp_path):
    env = {**env, "REPORT_SITE_HASH_CMD": "false"}
    res = _run(env, "add", "dieu-hanh", "an.nguyen", stdin=PASSWORD + "\n")
    assert res.returncode == 1 and "hashing failed" in res.stderr
    assert not (tmp_path / "users" / "dieu-hanh.caddy").exists()
