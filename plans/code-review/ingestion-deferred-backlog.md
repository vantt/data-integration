# Ingestion Deferred Backlog

**Source:** `code-reviewer-260227-1721-ingestion-edge-cases-plan.md` (archived 2026-04-03)
**Status:** Backlog — low priority / not urgent

---

## Deferred Items

### 1. Cookie Lock — Orphaned `.tmp` File
**File:** `ingestion/src/shared_cookie_manager.py`
**Risk:** Low-frequency; on hard crash, leaves stale `.tmp` lock file, forcing re-login (~30s delay on next run). Self-heals on restart.
**Fix when ready:** Use per-process temp file name (PID-stamped) so orphaned files don't block other processes.

---

### 2. Pipeline State — Partial Load Recovery
**File:** `ingestion/src/pipeline_runner.py`
**Risk:** dlt append disposition means a mid-run crash creates duplicate envelopes (not data loss). Downstream `stg_` dbt models deduplicate by `entity_id + payload_hash`. Manual recovery: `--full-refresh` flag.
**Fix when ready:** Implement atomic state checkpoint or explicit rollback before appending.

---

### 3. `--limit` Flag No-op
**File:** `ingestion/src/pipeline_runner.py`
**Risk:** None (data integrity). CLI convenience only — `--limit` argument is accepted but ignored.
**Fix when ready:** Wire `--limit` to `max_pages` or a row cap in the dlt source.

---

### 4. GSheet Targets — Schema Contract Validation
**File:** `ingestion/src/gsheet_targets.py`
**Risk:** Low. `_validate_rows()` already validates `cycle_start_date`, `metric_code`, `target_value`, `cycle_type`, `repeat_until`, `staff_email`. Remaining gap: no check against downstream dbt column expectations.
**Fix when ready:** Add dbt schema tests (`accepted_values`, `not_null`) rather than ingestion-side validation.
