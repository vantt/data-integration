"""test_golden_snapshot.py — the refactor safety net must catch what it claims to catch.

Covers the two blind spots of a per-column checksum: values swapped between rows (same
multiset per column), and stale parquet inherited from the source lake (a model that was
never rebuilt looks identical).

Run:
  python -m pytest scripts/tests/test_golden_snapshot.py -q
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import duckdb
import yaml

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from checks import golden_snapshot as gs  # noqa: E402


def _write_parquet(path: Path, rows: list[tuple[str, str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE t (k VARCHAR, team VARCHAR, revenue DOUBLE)")
    con.executemany("INSERT INTO t VALUES (?, ?, ?)", rows)
    con.execute(f"COPY t TO '{path}' (FORMAT parquet)")


def _fp(path: Path) -> dict:
    return gs.fingerprint(duckdb.connect(), f"read_parquet('{path}')", [])


def test_swapped_values_between_rows_change_row_fingerprint_only(tmp_path):
    a = tmp_path / "a.parquet"
    b = tmp_path / "b.parquet"
    _write_parquet(a, [("s1", "team_x", 100.0), ("s2", "team_y", 200.0)])
    _write_parquet(b, [("s1", "team_y", 100.0), ("s2", "team_x", 200.0)])
    fa, fb = _fp(a), _fp(b)
    assert fa["percol"] == fb["percol"]  # every column holds the same multiset
    assert fa["row"] != fb["row"]        # but the row tuples differ


def test_identical_data_in_different_row_order_is_equal(tmp_path):
    a = tmp_path / "a.parquet"
    b = tmp_path / "b.parquet"
    _write_parquet(a, [("s1", "x", 1.0), ("s2", "y", 2.0)])
    _write_parquet(b, [("s2", "y", 2.0), ("s1", "x", 1.0)])
    assert _fp(a) == _fp(b)


def _make_lake(tmp_path: Path, build_start: str, status: str) -> tuple[Path, Path]:
    lake = tmp_path / "lake"
    meta = lake / "_shadow_meta"
    meta.mkdir(parents=True)
    duckdb.connect(str(lake / gs.WAREHOUSE)).close()
    (meta / "build_start").write_text(build_start)
    (meta / "run_results.json").write_text(json.dumps(
        {"results": [{"unique_id": "model.p.fact_x", "status": status}]}))
    _write_parquet(lake / gs.ROLLING_REL / "fact_x" / "fact_x_20260101000000.parquet", [("k", "t", 1.0)])
    models = tmp_path / "models.yaml"
    models.write_text(yaml.safe_dump({"tables": {"fact_x": {"kind": "rolling", "unique_id": "model.p.fact_x"}}}))
    return lake, models


def _capture(lake: Path, models: Path, out: Path) -> int:
    return gs.cmd_capture(argparse.Namespace(lake=str(lake), models=str(models), out=str(out)))


def test_capture_rejects_parquet_older_than_build_start(tmp_path):
    future = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() + 3600))
    lake, models = _make_lake(tmp_path, future, "success")
    out = tmp_path / "out.json"
    assert _capture(lake, models, out) == 1
    assert "predates build start" in " ".join(json.loads(out.read_text())["errors"])


def test_capture_rejects_model_not_rebuilt(tmp_path):
    past = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))
    lake, models = _make_lake(tmp_path, past, "skipped")
    out = tmp_path / "out.json"
    assert _capture(lake, models, out) == 1
    assert "not rebuilt" in " ".join(json.loads(out.read_text())["errors"])


def test_capture_accepts_fresh_successful_build(tmp_path):
    past = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))
    lake, models = _make_lake(tmp_path, past, "success")
    assert _capture(lake, models, tmp_path / "out.json") == 0
