# Orchestration + Ingestion Fixes — 260624-1826

## Task 1 — HIGH: system_backup.py pipe-buffer deadlock fix

**File:** `orchestration/ops/system_backup.py:26-53`

**Change:** Replaced `subprocess.run(capture_output=True)` with `Popen + stdout-stream + stderr=STDOUT + wait(timeout)` pattern, mirroring `serving.py:_run_provisioning_script()`.

Key points:
- `capture_output=True` buffers all output in OS pipe (~64 KB). Large rsync/file-listing output fills it → subprocess blocks on write → parent waits forever → only exits at 600s timeout.
- New pattern: streams each line to `context.log.info()` as it arrives; OS pipe never fills.
- Timeout preserved (`_BACKUP_TIMEOUT_SEC = 600`). On expiry: `proc.kill()` + `proc.wait()` + `Failure` raised.
- stderr merged into stdout via `stderr=STDOUT` (matches serving.py).
- `output_lines[-20:]` in the failure message gives last 20 lines for triage (matches serving.py style).

**Validation:** `py_compile` PASS

---

## Task 2 — MED: gsheet naive datetime.now() → UTC-aware

**Files changed:**
- `ingestion/src/gsheet_team_config.py` — 3 partition-key sites
- `ingestion/src/gsheet_targets.py` — 1 fillna fallback site
- `ingestion/src/gsheet_marketing_spend.py` — 1 year-heuristic in `clean_date()`

**Change:** Added `timezone` to `from datetime import datetime, timezone` in all 3 files. Replaced `datetime.now()` with `datetime.now(timezone.utc)` at all partition-key / year-guess call sites. Non-partition usages (date formatting, pd.to_datetime, etc.) left untouched.

Details per file:
- `gsheet_team_config.py`: computed `_now_utc = datetime.now(timezone.utc)` once per run call; used for `valid_teams["year/month"]` and `valid_members["year/month"]` (4 assignment sites).
- `gsheet_targets.py`: `fillna(datetime.now().year/month)` — the fallback fires only when `cycle_start_date` is NaT, which is the partition guess site. Fixed to `datetime.now(timezone.utc).year/month`.
- `gsheet_marketing_spend.py`: `clean_date()` appends current year to short date strings like "12/25". This year feeds `df['year']` partition. Fixed by hoisting `_current_year = datetime.now(timezone.utc).year` before the function.

**Validation:** `py_compile` PASS ×3

---

## Task 3 — LOW: _INGESTION_JOBS dynamic build from SYNC_TAGS

**File:** `orchestration/definitions.py:301-315`

**Change:** Replaced the manual `_INGESTION_JOBS` string list with a dynamic build:
1. Defined `_ALL_SYNC_JOBS` — an explicit list of the 10 job objects defined above it in the same module.
2. `_INGESTION_JOBS = [j.name for j in _ALL_SYNC_JOBS if j.tags.get("concurrency_group") == "dbt_rw"]`

When a new job is added with `tags=SYNC_TAGS` (or any tags dict containing `concurrency_group=dbt_rw`), the developer only needs to add it to `_ALL_SYNC_JOBS` — it auto-appears in `_INGESTION_JOBS` and therefore in the backup sensor's ingestion-idle check.

**Validation:** Logic verified in isolation — filter produces identical 10-name list as the original hardcoded list. `py_compile` PASS.

**Note:** `_ALL_SYNC_JOBS` is still an explicit list (not a reflection scan) because Dagster job objects are local module-level variables, not enumerable from a registry at import time. The anti-drift protection is: a developer adding a job without adding it to `_ALL_SYNC_JOBS` gets no protection, but at least the filter logic is self-documenting and the pattern is clear.

---

## Task 4a — LOW: morning_digest.py sapo_inventory asset_type fix

**File:** `orchestration/ops/morning_digest.py:65`

**Change:** `"sapo_inventory"` entry in `ASSET_DISPLAY`:
- `asset_type`: `"batch"` → `"cursor"` 
- label: `"Sapo tồn kho (batch)"` → `"Sapo tồn kho (hourly)"`

**Reason:** The `_format_row_vi()` docstring documents `batch` = "runs once a day". `sapo_inventory` runs hourly via `pipeline_sapo_v2_hourly_job` (schedule `25 0-2,4-23 * * *`) — so the "Batch hôm qua: 0 giao dịch mới" message was misleading on days with no new transactions. `cursor` format shows run frequency, which is accurate for an hourly job.

**Validation:** `py_compile` PASS

---

## Task 4b — LOW: reconciliation_checks.py thresholds → ingestion_sla.yaml

**Files changed:**
- `orchestration/config/ingestion_sla.yaml` — added 2 keys to `defaults:` block
- `orchestration/asset_checks/reconciliation_checks.py` — read thresholds via `get_defaults()`

**Changes:**

`ingestion_sla.yaml` `defaults:` block — added:
```yaml
recon_drift_warn_pct: 0.01   # |drift_pct| > 1%  → WARN
recon_drift_error_pct: 0.05  # |drift_pct| > 5%  → ERROR
```

`reconciliation_checks.py`:
- Added `from orchestration.asset_checks.sla_loader import get_defaults`
- Replaced `_WARN_THRESHOLD = 0.01` / `_ERROR_THRESHOLD = 0.05` with reads from `get_defaults()` with hardcoded fallbacks for safe startup.
- Removed stale TODO comment.

**Behavior identical**: defaults in YAML match previous hardcoded values exactly. Changing thresholds now only requires editing `ingestion_sla.yaml` + Dagster webserver restart (same as all other SLA config).

**Validation:** `get_defaults()` returns correct values (`recon_drift_warn_pct=0.01`, `recon_drift_error_pct=0.05`). `py_compile` PASS.

---

## definitions import

The `python -c "import orchestration.definitions"` command fails on host Python with `ModuleNotFoundError: No module named 'dagster_dbt'`. This is **pre-existing**: `dagster_dbt` is not installed in the host Python environment (only in the Docker container). The failure occurs at line 30 (`from dagster_dbt import DbtCliResource`), which is untouched by any of these edits. All changed code is in lines 301-315 and the `_INGESTION_JOBS` filter, both well past the import block.

Verified:
- All 6 changed files pass `py_compile`
- `_INGESTION_JOBS` dynamic filter produces identical 10-name list to the original hardcoded list (validated with mock job objects)
- `sla_loader.get_defaults()` correctly returns new YAML keys

---

**Status:** DONE_WITH_CONCERNS

**Per-task:**
1. system_backup.py — Popen streaming pattern applied; deadlock eliminated; timeout preserved. DONE
2. gsheet_*.py — `datetime.now(timezone.utc)` applied to all 3 files at all partition-key sites. DONE
3. definitions.py — `_INGESTION_JOBS` built dynamically from `_ALL_SYNC_JOBS` filter; behavior identical. DONE
4a. morning_digest.py — `sapo_inventory` asset_type changed `batch` → `cursor`. DONE
4b. reconciliation_checks.py — thresholds moved to `ingestion_sla.yaml` defaults; get_defaults() wired in. DONE

**definitions import:** FAIL on host Python — pre-existing `dagster_dbt` not installed; unrelated to these edits. Docker container will succeed.

**Concern:** Task 3 `_ALL_SYNC_JOBS` is still a manual list of job objects — it just auto-derives the names. A new SYNC_TAGS job added without updating `_ALL_SYNC_JOBS` would still be missed. True auto-discovery would require a Dagster Definitions registry scan post-construction, which is not feasible at import time. This is the minimal viable improvement.
