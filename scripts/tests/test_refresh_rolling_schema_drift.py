"""test_refresh_rolling_schema_drift.py — column-level schema drift check.

Covers plans/260709-1638-crm-outreach-effort-report plan.md open Q#9: a
follow-up to closing Q#7 (zalo_connected_count), which surfaced that
bootstrap_serving_views.py's union_by_name=true silently coerces/widens an
existing column's TYPE across rolling parquet versions instead of erroring.
This adds a loud [!] SCHEMA_DRIFT alert for that specific case, independent
of the pre-existing new-table-folder drift check.

Run:
  python -m pytest scripts/tests/test_refresh_rolling_schema_drift.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pytest

_SCRIPTS_DIR = str(Path(__file__).resolve().parents[1])
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from provisioning import refresh_rolling  # noqa: E402


def _sql_literal(value) -> str:
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def _write_parquet(path: Path, rows: list[dict]) -> None:
    """Write a single-row parquet file with the given column values. Test-only
    helper (fixed, non-adversarial literals) — not a general SQL builder."""
    path.parent.mkdir(parents=True, exist_ok=True)
    row = rows[0]
    select_list = ", ".join(f"{_sql_literal(v)} AS {k}" for k, v in row.items())
    con = duckdb.connect()
    con.execute(f"COPY (SELECT {select_list}) TO '{path.as_posix()}' (FORMAT PARQUET)")


class TestGetLatestSchema:
    def test_reads_column_types_from_parquet(self, tmp_path):
        f = tmp_path / "t_20260101000000.parquet"
        _write_parquet(f, [{"a": 1, "b": "x"}])
        schema = refresh_rolling.get_latest_schema(str(tmp_path), f.name)
        assert schema == {"a": "INTEGER", "b": "VARCHAR"}

    def test_returns_none_on_missing_file(self, tmp_path):
        schema = refresh_rolling.get_latest_schema(str(tmp_path), "does_not_exist.parquet")
        assert schema is None


class TestKnownTablesMarkerRoundtrip:
    def test_save_then_load_roundtrips_tables_and_schemas(self, tmp_path, monkeypatch):
        marker = tmp_path / ".known_tables.json"
        monkeypatch.setattr(refresh_rolling, "KNOWN_TABLES_MARKER", str(marker))
        monkeypatch.setattr(refresh_rolling, "SERVING_DIR", str(tmp_path))

        refresh_rolling.save_known_tables(
            {"mart_a", "mart_b"}, {"mart_a": {"col1": "BIGINT"}}
        )
        tables, schemas = refresh_rolling.load_known_tables()
        assert tables == {"mart_a", "mart_b"}
        assert schemas == {"mart_a": {"col1": "BIGINT"}}

    def test_pre_upgrade_marker_without_schemas_key_loads_empty_schemas(self, tmp_path, monkeypatch):
        """Backward compat: a marker written before this feature existed has no
        "schemas" key — must load as {}, not crash, so the first run after
        upgrading just establishes a baseline (no false-positive drift)."""
        marker = tmp_path / ".known_tables.json"
        marker.write_text(json.dumps({"tables": ["mart_a"]}), encoding="utf-8")
        monkeypatch.setattr(refresh_rolling, "KNOWN_TABLES_MARKER", str(marker))

        tables, schemas = refresh_rolling.load_known_tables()
        assert tables == {"mart_a"}
        assert schemas == {}

    def test_missing_marker_file_loads_empty(self, tmp_path, monkeypatch):
        monkeypatch.setattr(refresh_rolling, "KNOWN_TABLES_MARKER", str(tmp_path / "nope.json"))
        tables, schemas = refresh_rolling.load_known_tables()
        assert tables == set()
        assert schemas == {}


class TestRefreshRollingColumnDriftDetection:
    """End-to-end through refresh_rolling() itself, capturing stdout."""

    def _setup_rolling_dir(self, tmp_path, monkeypatch):
        rolling_dir = tmp_path / "rolling"
        serving_dir = tmp_path / "serving"
        monkeypatch.setattr(refresh_rolling, "ROLLING_DIR", str(rolling_dir))
        monkeypatch.setattr(refresh_rolling, "SERVING_DIR", str(serving_dir))
        monkeypatch.setattr(
            refresh_rolling, "KNOWN_TABLES_MARKER", str(serving_dir / ".known_tables.json")
        )
        return rolling_dir

    def test_type_change_on_existing_column_raises_schema_drift(self, tmp_path, monkeypatch, capsys):
        rolling_dir = self._setup_rolling_dir(tmp_path, monkeypatch)
        table_dir = rolling_dir / "mart_x"
        _write_parquet(table_dir / "mart_x_20260101000000.parquet", [{"amount": 100}])

        # First run: establishes baseline (amount=BIGINT), no drift possible yet.
        refresh_rolling.refresh_rolling()
        capsys.readouterr()

        # Second run: same column now VARCHAR — a real incompatible type change.
        _write_parquet(table_dir / "mart_x_20260102000000.parquet", [{"amount": "100"}])
        refresh_rolling.refresh_rolling()
        out = capsys.readouterr().out
        assert "[!] SCHEMA_DRIFT: mart_x column 'amount' type changed INTEGER -> VARCHAR" in out

    def test_added_column_does_not_raise_schema_drift(self, tmp_path, monkeypatch, capsys):
        """A plain added column (the common, already-fixed case via
        union_by_name) must NOT trigger this alert — only a type change on a
        pre-existing column should."""
        rolling_dir = self._setup_rolling_dir(tmp_path, monkeypatch)
        table_dir = rolling_dir / "mart_y"
        _write_parquet(table_dir / "mart_y_20260101000000.parquet", [{"a": 1}])
        refresh_rolling.refresh_rolling()
        capsys.readouterr()

        _write_parquet(table_dir / "mart_y_20260102000000.parquet", [{"a": 1, "b": "new"}])
        refresh_rolling.refresh_rolling()
        out = capsys.readouterr().out
        assert "SCHEMA_DRIFT" not in out

    def test_unchanged_schema_across_runs_stays_silent(self, tmp_path, monkeypatch, capsys):
        rolling_dir = self._setup_rolling_dir(tmp_path, monkeypatch)
        table_dir = rolling_dir / "mart_z"
        _write_parquet(table_dir / "mart_z_20260101000000.parquet", [{"a": 1}])
        refresh_rolling.refresh_rolling()
        capsys.readouterr()

        _write_parquet(table_dir / "mart_z_20260102000000.parquet", [{"a": 2}])
        refresh_rolling.refresh_rolling()
        out = capsys.readouterr().out
        assert "SCHEMA_DRIFT" not in out
