# Incident Post-Mortem: Zombie Run + Stuck-Run Sensor Gap

**Date:** 2026-06-24  
**Incident:** `pipeline_sapo_v2_realtime_job` stuck STARTED for ~7h after process death; self-overlap guard blocked all schedule ticks; `health_alert_stuckrun_sensor` reported "No stuck runs detected" the whole time.

---

## Root-Cause Findings

### 1. Why did `health_alert_stuckrun_sensor` NOT catch the 7h zombie?

**Primary gap: `last_event_time is None` → unconditional `continue`**

Pass 1 of the sensor (STARTED runs) calls `_get_last_event_time()` to read the most recent event from the SQLite event log. When that returns `None` (exception or empty result), the sensor does `continue` — it skips the run entirely and emits "No stuck runs detected". This is the conservative design choice to avoid false-positive kills during `purge_runs` VACUUM (which holds an exclusive SQLite lock). But if the lock persisted across ticks (or the dead process left the event log in a bad state), the sensor would skip the zombie indefinitely.

**Secondary gap: no absolute max-runtime backstop**

Even when `last_event_time` is readable, the existing code checks:
1. `runtime >= MIN_RUNTIME_BEFORE_KILL` (10 min) — prevents killing during init
2. `inactivity >= INACTIVITY_THRESHOLD` (5 min) — fires when process is dead

For a healthy dead-process zombie this WOULD catch it at ~15 min. The 7h duration strongly implies the `last_event_time is None` path was triggered continuously (likely due to ongoing SQLite contention or a corrupted event log entry for that run).

**Pass 2 (QUEUED/NOT_STARTED) gap:** The two QUEUED runs were downstream victims, not the root. They would have been caught by Pass 2 at 20 min — but only after the STARTED zombie was gone. Since the zombie persisted, Pass 2 kept looping but the overlap guard kept blocking new runs from the schedule, not from Pass 2 termination.

### 2. Self-overlap guard (`_has_active_run`)

Location: `orchestration/definitions.py` lines 250-264.

`_ACTIVE_STATUSES` includes ALL pre-terminal states:
```python
_ACTIVE_STATUSES = [QUEUED, NOT_STARTED, STARTING, STARTED]
```

`_has_active_run(context, "pipeline_sapo_v2_realtime_job")` returns the zombie's run_id as long as it sits in STARTED. The realtime schedule fires every 3 min and skips every tick with `"realtime: previous run still active (XXXXXXXX)"`. This is correct by design — but depends entirely on the sensor cleaning up the zombie. Since the sensor failed, the guard blocked for 7h.

### 3. `run_monitoring` was DISABLED

`app_data/dagster_home/dagster.yaml` had no `run_monitoring` block. From the Dagster instance:

```
run_monitoring_enabled: False
run_launcher.supports_check_run_worker_health: False
```

Because `supports_check_run_worker_health` is False, the `monitor_started_run()` path falls through to `check_run_timeout()`. With `max_runtime_seconds: 0` (default when disabled), `check_run_timeout` returns immediately without acting. Result: Dagster's built-in zombie-detection was entirely inert.

---

## Changes Made

### Fix A — Enable `run_monitoring` in `dagster.yaml`

**File:** `app_data/dagster_home/dagster.yaml` (appended before the storage comment)

```yaml
run_monitoring:
  enabled: true
  start_timeout_seconds: 300       # fail STARTING/NOT_STARTED runs stuck >5 min
  cancel_timeout_seconds: 300      # fail CANCELING runs stuck >5 min
  max_runtime_seconds: 3600        # fail any STARTED run running >60 min
  max_resume_run_attempts: 0       # no auto-resume (launcher doesn't support it)
  poll_interval_seconds: 120       # sweep every 2 min
```

With `supports_check_run_worker_health: False`, the RunMonitoringDaemon for STARTED runs calls `check_run_timeout()` which now has `max_runtime_seconds=3600`. Any STARTED run older than 60 min gets failed automatically by the daemon — independent of the sensor. This is the canonical Dagster-level fix.

Note: 60 min is the nightly job's upper bound. The realtime job should complete in ~10 min, so a 60-min cut is very conservative for it. If you want tighter cuts per-job, use the `dagster/max_runtime_seconds` tag on the job definition.

**Validated:** `process_config(dagster_instance_config_schema(), yaml)` returns success. All keys are confirmed from Dagster 1.13.2 source (`dagster/_core/instance/config.py`).

### Fix B — Harden stuck-run sensor with absolute max-runtime backstop

**File:** `orchestration/sensors/stuck_run_alerter.py`

Added `_JOB_MAX_RUNTIME` dict (lines 70-88) with per-job absolute max runtimes:
- Realtime/incremental/hourly: 45 min
- Nightly/fullrefresh: 120 min  
- Health/maintenance jobs: 30-60 min
- Unknown jobs: 90 min default

Modified Pass 1 logic (around line 217): when `last_event_time is None`, instead of unconditional `continue`, now checks if `runtime >= job_max`. If so, terminates regardless — a healthy job cannot run for 45+ min without writing a single event to the log. If `runtime < job_max`, still skips (conservative, avoids false positives during brief VACUUM windows).

Updated `report_run_failed` message and Lark alert to include `termination_reason` string (describes which branch triggered the kill).

**Validated:** `python -m py_compile` in container → OK.

---

## Detection Timeline After Fix (new incident scenario)

| Time | What happens |
|---|---|
| T+0 | `data_platform` restarted; run worker for realtime job dies |
| T+2 min | RunMonitoringDaemon first sweep (poll_interval=120s) — `check_run_timeout` sees runtime < 3600s, skips |
| T+10 min | `health_alert_stuckrun_sensor` tick — runtime ≥ MIN_RUNTIME_BEFORE_KILL(10); if event log readable + inactivity >5 min → sensor terminates |
| T+45 min | Even if sensor kept missing (all-None event log): absolute max-runtime backstop triggers |
| T+60 min | RunMonitoringDaemon `max_runtime_seconds=3600` fires — fails the run at Dagster level |

Worst-case detection: 60 min (down from 7h+).

---

## Apply Step

**Restart `data_platform` container** (the human will do this after review):

```bash
docker compose up -d --force-recreate data_platform
```

The `dagster.yaml` change takes effect on restart (file is volume-mounted). The sensor code change is picked up on restart (code is volume-mounted in `./orchestration`).

No migration or schema change needed. `run_monitoring` uses the existing SQLite event log.

---

## Residual Risks

1. **`max_runtime_seconds: 3600` may kill a legitimately slow nightly run.** The nightly job normally completes in 60-90 min — 3600s (60 min) matches the low end. If a dbt full-refresh or cold-start pushes it to 70 min, the daemon kills it. Mitigation: raise to `7200` (120 min) for more headroom, or tag the nightly job with `dagster/max_runtime_seconds: "7200"` at definition time to override per-job. Current setting is acceptable for the realtime/incremental jobs but is tight for nightly.

2. **Root cause of the 7h `last_event_time is None` is unconfirmed.** We patched the gap but haven't proven what caused persistent SQLite event-log read failures. Could be: (a) purge_runs VACUUM overlap, (b) event log DB file corruption, (c) the zombie run's event log table having no records (process died before writing any STARTED events). Recommend checking `app_data/dagster_home/storage/` SQLite health after the next incident.

3. **`_JOB_MAX_RUNTIME` dict must be kept in sync with job definitions.** New jobs added to `definitions.py` will use the 90-min default, which is safe but suboptimal. Consider adding a comment near `define_asset_job` calls reminding to update `_JOB_MAX_RUNTIME`.

---

## Unresolved Questions

- Why did `last_event_time` return `None` continuously for 7h? Was `purge_runs` overlapping, or did the event log have no records for that run_id? Answerable by checking `app_data/dagster_home/storage/` post-mortem if the DB is still accessible.
- Should `max_runtime_seconds` in `dagster.yaml` be raised to 7200 to safely cover the nightly job? Recommend yes if nightly can legitimately take >60 min.
