"""Tests for the parquet-based row-count fallback in dlt_metrics.

The current dlt + filesystem destination LoadInfo does not populate
items_count / row_count in jobs or job_metrics. extract_rows_written must
fall back to reading the actual parquet files produced by the load so
downstream health tracking stops recording false zeros.
"""
from __future__ import annotations

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from orchestration.ops.dlt_metrics import extract_rows_written


def _write_parquet(path, n_rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({"id": list(range(n_rows))})
    pq.write_table(table, path)


def _load_info_for(dataset: str, table: str, file_id: str) -> dict:
    """Minimal LoadInfo shape that matches what dlt emits for filesystem loads."""
    return {
        "dataset_name": dataset,
        "loads_ids": ["test-load"],
        "load_packages": [
            {
                "load_id": "test-load",
                "jobs": [
                    {
                        "state": "completed_jobs",
                        "table_name": table,
                        "file_id": file_id,
                        "file_format": "parquet",
                        "file_size": 1234,
                    },
                    # dlt always emits _dlt_pipeline_state as a control file.
                    # The fallback must skip internal tables.
                    {
                        "state": "completed_jobs",
                        "table_name": "_dlt_pipeline_state",
                        "file_id": "state_id",
                        "file_format": "jsonl",
                        "file_size": 500,
                    },
                ],
            }
        ],
    }


def test_fallback_counts_real_parquet_rows(tmp_path, monkeypatch):
    """With DBT_DATA_LAKE_PATH set, the fallback globs and COUNT(*)s parquets."""
    dataset, table, file_id = "sapo_raw", "order", "abc123"
    parquet = tmp_path / dataset / table / "ingest_method=batch_sync" / f"{file_id}.parquet"
    _write_parquet(parquet, n_rows=42)

    monkeypatch.setenv("DBT_DATA_LAKE_PATH", str(tmp_path))

    info = _load_info_for(dataset, table, file_id)
    assert extract_rows_written(info) == 42


def test_fallback_ignores_dlt_internal_tables(tmp_path, monkeypatch):
    """The _dlt_pipeline_state job in load_packages must never be counted."""
    dataset, table, file_id = "sapo_raw", "customer", "cust42"
    parquet = tmp_path / dataset / table / "y=2026" / f"{file_id}.parquet"
    _write_parquet(parquet, n_rows=7)
    # Intentionally do not write a parquet for _dlt_pipeline_state — it's jsonl
    # in practice and the fallback filters on file_format=parquet anyway.

    monkeypatch.setenv("DBT_DATA_LAKE_PATH", str(tmp_path))

    info = _load_info_for(dataset, table, file_id)
    assert extract_rows_written(info) == 7  # not 7 + anything


def test_fallback_returns_zero_when_env_unset(tmp_path, monkeypatch):
    """No DBT_DATA_LAKE_PATH → fallback can't resolve paths, returns 0 (packages exist)."""
    monkeypatch.delenv("DBT_DATA_LAKE_PATH", raising=False)
    info = _load_info_for("sapo_raw", "order", "x")
    # Packages exist but no metrics + no resolvable path → 0 is the best answer.
    assert extract_rows_written(info) == 0


def test_metrics_path_still_wins_over_fallback(tmp_path, monkeypatch):
    """When dlt DOES populate items_count, we must trust it and skip parquet I/O."""
    monkeypatch.setenv("DBT_DATA_LAKE_PATH", str(tmp_path))
    info = {
        "dataset_name": "sapo_raw",
        "loads_ids": ["x"],
        "load_packages": [
            {
                "load_id": "x",
                "jobs": [
                    {
                        "state": "completed_jobs",
                        "table_name": "order",
                        "file_id": "f1",
                        "file_format": "parquet",
                        "metrics": {"items_count": 99},
                    }
                ],
            }
        ],
    }
    # No parquet file exists, but metrics.items_count is trusted → 99.
    assert extract_rows_written(info) == 99


def test_empty_packages_returns_zero():
    info = {"dataset_name": "sapo_raw", "loads_ids": [], "load_packages": []}
    assert extract_rows_written(info) == 0


def test_none_info_returns_none():
    assert extract_rows_written({}) is None
    assert extract_rows_written(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Delta-Lake-style fallback: file_id does NOT match on-disk filename. Every
# row still carries _dlt_load_id, so scan + filter gives the right count.
# ---------------------------------------------------------------------------

def _write_parquet_with_load_id(path, load_id: str, n_rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table({
        "id": list(range(n_rows)),
        "_dlt_load_id": [load_id] * n_rows,
    })
    pq.write_table(table, path)


def test_load_id_fallback_counts_when_file_id_mismatch(tmp_path, monkeypatch):
    """Delta-style: on-disk file name ≠ {file_id}, but _dlt_load_id matches."""
    dataset, table = "sapo_raw", "order"
    load_id = "1776827427.1534114"

    # Delta-style part file — completely different name from dlt's file_id.
    part_dir = tmp_path / dataset / table / "ingest_method=history_log" / "year=2026" / "month=4"
    _write_parquet_with_load_id(
        part_dir / "part-00000-abc-c000.snappy.parquet", load_id, n_rows=5
    )
    # An unrelated older load's rows — must NOT be counted.
    _write_parquet_with_load_id(
        part_dir / "part-00000-def-c000.snappy.parquet", "OLD_LOAD", n_rows=11
    )

    monkeypatch.setenv("DBT_DATA_LAKE_PATH", str(tmp_path))

    info = {
        "dataset_name": dataset,
        "loads_ids": [load_id],
        "load_packages": [
            {
                "jobs": [
                    # dlt's file_id here does NOT match any on-disk file name.
                    {"table_name": table, "file_id": "c52eaece74",
                     "file_format": "parquet"},
                    {"table_name": "_dlt_pipeline_state", "file_id": "state",
                     "file_format": "jsonl"},
                ]
            }
        ],
    }
    assert extract_rows_written(info) == 5


def test_load_id_fallback_sums_across_multiple_tables(tmp_path, monkeypatch):
    dataset = "sapo_raw"
    load_id = "L1"
    _write_parquet_with_load_id(tmp_path / dataset / "order" / "a.parquet", load_id, 3)
    _write_parquet_with_load_id(tmp_path / dataset / "fulfillment" / "b.parquet", load_id, 4)

    monkeypatch.setenv("DBT_DATA_LAKE_PATH", str(tmp_path))
    info = {
        "dataset_name": dataset,
        "loads_ids": [load_id],
        "load_packages": [
            {"jobs": [
                {"table_name": "order", "file_id": "fake1", "file_format": "parquet"},
                {"table_name": "fulfillment", "file_id": "fake2", "file_format": "parquet"},
            ]}
        ],
    }
    assert extract_rows_written(info) == 7
