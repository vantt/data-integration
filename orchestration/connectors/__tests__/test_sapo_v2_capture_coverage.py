"""sapo_v2 capture_coverage check: reads the latest successful capture from ingestion_health."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from dagster import AssetCheckSeverity, build_asset_context

from orchestration.connectors.sapo_v2.checks import SNAPSHOT_ASSET_KEY, product_daily_snapshot_coverage

_DDL = """
CREATE TABLE ingestion_runs (
    asset_key TEXT NOT NULL, run_id TEXT NOT NULL, run_started_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL, rows_written INTEGER, metadata_json TEXT,
    PRIMARY KEY (asset_key, run_id)
);
"""


@pytest.fixture
def health_db(tmp_path):
    path = str(tmp_path / "ingestion_health.db")
    conn = sqlite3.connect(path)
    conn.execute(_DDL)
    conn.commit()
    conn.close()

    def add(run_id, hours_ago, status, meta):
        c = sqlite3.connect(path)
        c.execute(
            "INSERT INTO ingestion_runs VALUES (?, ?, ?, ?, ?, ?)",
            [SNAPSHOT_ASSET_KEY, run_id,
             (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat(),
             status, meta.get("products"), json.dumps(meta)],
        )
        c.commit()
        c.close()

    with patch("orchestration.asset_checks.health_db.get_db_path", return_value=path):
        yield add


def _run():
    return product_daily_snapshot_coverage(build_asset_context())


def test_no_capture_yet_is_suppressed(health_db):
    result = _run()
    assert result.passed is True


def test_full_capture_passes(health_db):
    health_db("r1", 2, "success", {"products": 560, "sapo_total": 560, "coverage_ratio": 1.0})
    result = _run()
    assert result.passed is True
    assert result.metadata["coverage_ratio"].value == 1.0


def test_short_latest_capture_warns_even_after_a_full_one(health_db):
    health_db("r1", 26, "success", {"products": 560, "sapo_total": 560, "coverage_ratio": 1.0})
    health_db("r2", 2, "success", {"products": 540, "sapo_total": 560, "coverage_ratio": 540 / 560})
    health_db("r3", 1, "failed", {})  # failed runs are not captures
    result = _run()
    assert result.passed is False
    assert result.severity == AssetCheckSeverity.WARN
    assert "540 of 560" in result.description


def test_unknown_total_warns(health_db):
    health_db("r1", 2, "success", {"products": 560, "sapo_total": None, "coverage_ratio": None})
    result = _run()
    assert result.passed is False
    assert result.severity == AssetCheckSeverity.WARN
