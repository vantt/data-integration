"""Helpers shared by kernel and connector job/schedule definitions.

Connector packages import from here instead of from definitions.py, which in turn
imports the connectors.
"""
from __future__ import annotations

from dagster import AssetKey, AssetSelection, DagsterRunStatus, RunsFilter

# All sync jobs share the 'dbt_rw' concurrency group (limit 1 in dagster.yaml) —
# this is the single-source-of-truth mutex for DuckDB writers. QueuedRunCoordinator
# enforces it at the instance level, replacing the old manual SkipReason logic.
SYNC_TAGS = {"concurrency_group": "dbt_rw"}

# fact_order_returns is not downstream of the shopee/misa file-drop sources, but
# fact_order_economics (which is) depends on it — without it, the first file-drop run
# on a fresh deploy fails because the parquet does not yet exist.
FACT_ORDER_RETURNS = AssetSelection.assets(AssetKey(["marts", "fact_order_returns"]))

# Active states: anything that hasn't terminated. NOT_STARTED is included
# to catch runs that were created but haven't been picked up yet.
ACTIVE_STATUSES = [
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.NOT_STARTED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
]

# Long-running dbt_rw jobs (60-90+ min). Submitting realtime/incremental while
# these are STARTED causes NOT_STARTED accumulation: the submitted run can't be
# dequeued (dbt_rw=1 occupied), blocks subsequent ticks via has_active_run,
# and eventually hits the 90-min QUEUE_STUCK_THRESHOLD and gets auto-canceled.
# Better to skip the tick and retry next tick (3-10 min later).
LONG_DBT_RW_JOBS = ["pipeline_batch_nightly_job", "pipeline_batch_fullrefresh_job"]

# Statuses that mean a job is ACTUALLY running (holds the dbt_rw slot).
# Exclude NOT_STARTED — a NOT_STARTED batch job hasn't acquired the slot yet
# and may fail to start; we shouldn't pre-emptively block on it.
RUNNING_STATUSES = [
    DagsterRunStatus.QUEUED,
    DagsterRunStatus.STARTING,
    DagsterRunStatus.STARTED,
]


def has_active_run(context, job_name: str) -> str | None:
    """Return run_id of an active run for this job, or None if none active."""
    runs = context.instance.get_runs(
        filters=RunsFilter(job_name=job_name, statuses=ACTIVE_STATUSES),
        limit=1,
    )
    return runs[0].run_id if runs else None


def long_dbt_rw_holder(context) -> str | None:
    """Return job_name if a long-running dbt_rw job is currently active (holds slot)."""
    for job_name in LONG_DBT_RW_JOBS:
        runs = context.instance.get_runs(
            filters=RunsFilter(job_name=job_name, statuses=RUNNING_STATUSES),
            limit=1,
        )
        if runs:
            return job_name
    return None
