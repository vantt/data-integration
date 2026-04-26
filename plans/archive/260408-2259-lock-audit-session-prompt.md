# Session Prompt — Lock & Concurrency Audit

> **How to use:** Paste the entire "PROMPT" section below into a fresh Claude
> Code session. It is fully self-contained — no prior conversation needed.

---

## PROMPT

You are starting a fresh session to audit **all locking and concurrency
mechanisms** in this `data-integration` repository. Your job is to scan the
codebase, evaluate what's in place, and write a comprehensive technical
document describing the current state, what works, what's broken or risky,
and what is fundamentally inherent to the technology and must be accepted.

### Mission

1. **Discover** every lock / mutex / concurrency primitive in the codebase
2. **Classify** each by layer (DB, process, OS file, app-level)
3. **Evaluate** what's done well, what's broken, what's risky, what's accepted
4. **Document** findings as `docs/architecture/locking-and-concurrency.md`
5. **Recommend** specific improvements (with priority + effort estimate)

### Critical Background — Read FIRST

A long debugging session on **2026-04-08** uncovered several misconceptions and
real bugs around locking. **Do not repeat these mistakes.** Read these insights
before scanning:

#### Insight 1 — The 16h hang was subprocess pipe deadlock, NOT a lock issue
Earlier analysis blamed "Metabase JDBC exclusive lock on `olap.duckdb`" for
a 16-hour hung serving asset. This was **wrong**. The actual root cause:
`subprocess.run(cmd, capture_output=True, check=True)` without `timeout=`,
where the child process printed enough log to fill the OS pipe buffer
(~64KB), causing classic pipe deadlock. See `orchestration/assets/serving.py`
post-fix and `.skills/data-pipeline/lessons-learned.md` L17.

**Lesson:** Hypotheses about locking must be verified empirically (with a
real test) before building plans on top of them. "Catch + warning" defensive
code does NOT prove the catch ever fires in production.

#### Insight 2 — DuckDB `read_only=true` does NOT acquire file locks
Verified empirically on 2026-04-08:
```python
# While Metabase is connected (read_only=true) to olap.duckdb:
duckdb.connect("/app/data_lake/serving/olap.duckdb")  # default RW
# → SUCCESS in 15ms. No lock contention. No exception.
```
DuckDB `read_only` mode does **not** take any file lock — it just mmaps the
file. This is **different from SQLite**, which uses shared locks for readers.
Metabase MotherDuck driver v1.4.4 with `read_only=true` exhibits the same
behavior. Multiple readers + 1 writer can coexist on the same DuckDB file.

**Implication:** The "best-effort lock handling" in old serving scripts was
defensive code that probably never fired. The Metabase + pipeline coexistence
was never actually broken by lock contention. See `lessons-learned.md` L18.

#### Insight 3 — Two distinct DuckDB files exist; they have very different roles
| File | Used by | Concurrency concern |
|---|---|---|
| `sapo.duckdb` (or similar — dbt internal warehouse) | dbt during compute | **Real concern**: 2 dbt runs in parallel deadlock. Hence `op_tags={"dagster/concurrency_key": "duckdb_lock"}` on `sapo_dbt_assets` |
| `olap.duckdb` (serving layer) | Metabase reader + bootstrap script writer | **Not a real concern**: read_only doesn't lock. Pattern C (split bootstrap from runtime refresh) keeps it simple. |

The `duckdb_lock` op concurrency key is for **the dbt internal DB**, not the
serving DB. Don't conflate them.

#### Insight 4 — `QueuedRunCoordinator` does NOT prevent queue buildup
`tag_concurrency_limits` in `dagster.yaml` enforces concurrency at **dequeue
time** only — i.e., it limits how many runs with the same tag can be LAUNCHED
simultaneously. It does **not** limit queue size. If a schedule keeps ticking
while a run is pending, the queue grows unbounded.

Earlier today, after removing manual mutex from schedules with the (wrong)
assumption that "the coordinator handles everything", we observed 28+ runs
piled up in the queue over 1h20m. The fix: schedules still need a self-overlap
skip check in their body. See `lessons-learned.md` L19.

**Pattern:** Cross-job mutex = coordinator tag. Self-overlap = schedule body.
Both are needed. Neither replaces the other.

#### Insight 5 — Asset-level concurrency pool slots LEAK on cancel
When a Dagster run is cancelled (manually or by container restart), Dagster's
`report_run_canceled()` releases run-level coordinator tag concurrency BUT
does **not** release **asset-level** op concurrency pool slots (the kind set
via `op_tags={"dagster/concurrency_key": "..."}`). The slot stays held by
the ghost run forever, blocking all subsequent runs that need the same key.

Verified today: after cancelling 40 sapo_* runs, `duckdb_lock` pool showed
`slot_count=1, active=1, pending=2`. The active slot was held by a cancelled
ghost run. Manually calling `event_log_storage.free_concurrency_slots_for_run()`
drained it.

**Cleanup tool:** `scripts/maintenance/unstick_concurrency_pools.py` (already
in repo). Run it after any cancel batch or container restart. See
`lessons-learned.md` L20.

#### Insight 6 — `define_asset_job(tags=...)` only applies to runs LAUNCHED after deploy
Pre-deploy ghost runs (started before tags were added to job definition)
don't have the concurrency tag and bypass the coordinator's limit
entirely. They appear as "started" in the instance state, can't be
controlled by the new tag rule, and must be explicitly cancelled +
unstuck.

### Files to Scan (start here)

#### Dagster orchestration
- `orchestration/definitions.py` — schedules, jobs, sensors, run coordinator config
- `orchestration/assets/dbt.py` — `op_tags` (concurrency key), `SapoDbtTranslator`
- `orchestration/assets/serving.py` — subprocess pattern (post-fix)
- `orchestration/assets/sapo_assets.py` — webhook consumer, batch assets
- `orchestration/sensors/stuck_run_alerter.py` — stuck detection
- `orchestration/sensors/failure_alerting.py` — failure alerts
- `app_data/dagster_home/dagster.yaml` — `QueuedRunCoordinator` + `tag_concurrency_limits`

#### Provisioning
- `scripts/provisioning/bootstrap_serving_views.py` — opens `olap.duckdb` RW
- `scripts/provisioning/refresh_rolling.py` — file ops only, no DB connect
- `scripts/maintenance/unstick_concurrency_pools.py` — slot release helper

#### dlt ingestion
- `ingestion/src/utils/shared_cookie_manager.py` — cross-process file lock for cookie sharing
- `ingestion/run_*.py` — dlt pipeline launchers (look for state lock semantics)
- `ingestion/.dlt/` — pipeline state directory (any locks?)

#### dbt
- `transformation/profiles.yml` — DuckDB threads, memory_limit
- `transformation/macros/get_rolling_location.sql` — parquet rolling pattern
- `transformation/dbt_project.yml` — model configs

#### Skill docs (read for prior analysis, don't blindly trust)
- `.skills/data-pipeline/serving-layer.md` — serving layer mechanism + post-mortem note
- `.skills/data-pipeline/dagster-patterns.md` — Lessons 1-6 (Lessons 5,6 are recent)
- `.skills/data-pipeline/lessons-learned.md` — L11 (DuckDB), L12 (cookie lock), L17-L20 (recent)
- `.skills/data-pipeline/troubleshooting.md` — symptom-based table

### Analysis Framework

For each lock / concurrency primitive you find, answer:

1. **Layer** — DB / OS file / Process / Dagster run / Dagster op / Application
2. **Mechanism** — what specifically (e.g., file lock, semaphore, advisory tag, regex check)
3. **Scope** — what it protects (cross-process? cross-thread? cross-run?)
4. **Implementation quality** — correct? buggy? defensive without need?
5. **Failure mode** — what happens if it fails (deadlock? leak? lost work?)
6. **Verification** — has it been tested empirically? Or assumed?
7. **Classification:**
   - ✅ **Working well** — correct implementation, justified design
   - ⚠️ **Risky / fragile** — works now but has known failure modes
   - 🚨 **Broken / leaky** — actively causing problems
   - 📌 **Inherent — must accept** — fundamental to the technology, not fixable
   - ❌ **Defensive but probably dead code** — exists but rarely/never fires

### Specific Questions to Answer

1. **Where exactly is `sapo.duckdb` (the dbt internal DB) and how is it
   protected?** — find the file path, the writers, and verify the
   `op_tags={"dagster/concurrency_key": "duckdb_lock"}` is actually applied
   to `sapo_dbt_assets`.
2. **What's the slot count for `duckdb_lock` pool?** Is it set explicitly
   somewhere or relying on default? What happens at default?
3. **SharedCookieManager** — is the cross-platform lock implementation
   correct? Are there any places that bypass it?
4. **dlt pipeline state** — does dlt acquire any lock when writing state
   files? What happens if 2 dlt processes share the same `.dlt/pipelines/`
   directory?
5. **Schedule self-overlap** — verify each schedule has the
   `_has_active_run` check after the recent fix.
6. **Coordinator tag application** — verify `concurrency_group=dbt_rw` is
   applied to all 4 sync jobs (`realtime`, `incremental`, `nightly`, `sheets`).
7. **Subprocess patterns elsewhere** — search for ANY other
   `subprocess.run(... capture_output=True ...)` without `timeout=` (the
   2026-04-08 bug pattern). Even one is dangerous.
8. **Metabase + serving DB coexistence** — confirm read_only is set in
   Metabase Admin and that the bootstrap script doesn't actually need
   Metabase to be stopped (per Insight 2).
9. **Inherent limits** — what concurrency limitations are baked into
   DuckDB/dbt/dlt that we cannot work around and must accept?

### Deliverable

Write the audit as `docs/architecture/locking-and-concurrency.md` with this
structure:

```markdown
# Locking & Concurrency Architecture

## Executive Summary
- Bullet list of overall posture (good / risky / known issues)

## Layer Map
- Table of every concurrency primitive, classified by layer

## Detailed Inventory
### DB-level
### OS file-level
### Process-level
### Dagster run-level
### Dagster op-level
### Application-level

## What's Working Well
- Specific items + why

## What's Risky or Fragile
- Specific items + failure mode + recommended fix

## What's Broken / Leaky
- Specific items + reproduction steps + fix priority

## Inherent Limits (Must Accept)
- Things that cannot be changed without swapping the underlying tech
- Each with a brief explanation of why

## Defensive Dead Code (Candidates for Removal)
- Code that exists "just in case" but probably never fires in production
- Each with verification approach (how to confirm it's dead)

## Recommended Improvements
- Prioritized list: P0 (must-fix), P1 (should-fix), P2 (nice-to-have)
- Each with effort estimate (hours/days) and concrete next step

## Verification History
- List of empirical tests run during this audit and their results
- (Don't trust documentation alone — test behaviors)

## Unresolved Questions
- Things you couldn't figure out from code alone
- Each with what info would resolve it
```

### Anti-Patterns to Avoid (from 2026-04-08 lessons)

- ❌ Don't trust "catch + warning" code as evidence of a real bug — verify empirically
- ❌ Don't conflate `sapo.duckdb` (dbt internal) with `olap.duckdb` (serving)
- ❌ Don't assume DuckDB locks like SQLite — they don't
- ❌ Don't assume `QueuedRunCoordinator` solves all concurrency — it only handles dequeue
- ❌ Don't assume `report_run_canceled()` releases asset-level pool slots — it doesn't
- ❌ Don't write large plans on unverified hypotheses — test first

### How to Verify Lock Behavior Empirically

Use this pattern from 2026-04-08:
```python
# Inside the running dagster container:
docker compose exec data_platform python -c "
import duckdb, time
t0 = time.time()
con = duckdb.connect('/app/data_lake/serving/olap.duckdb')  # try RW
print(f'connected in {(time.time()-t0)*1000:.1f}ms')
con.close()
"
```

For pool state inspection:
```python
from dagster import DagsterInstance
inst = DagsterInstance.get()
els = inst.event_log_storage
for key in els.get_concurrency_keys():
    info = els.get_concurrency_info(key)
    print(f"{key}: slot={info.slot_count} active={info.active_slot_count} "
          f"pending={info.pending_step_count} active_runs={info.active_run_ids}")
```

### Constraints

- Be **brutally honest** — if something is broken, say so. Don't soften.
- Be **specific** — file paths, line numbers, function names. Not "around there".
- Be **empirical** — when in doubt, run a test. Don't speculate.
- Be **concise** — sacrifice grammar for concision (project rule)
- Don't make this task into a multi-day epic — produce a usable doc in one
  focused pass. Iterate later if needed.
- Output markdown only into `docs/` (per project rule on doc location).

### Working Directory & Environment

- Project root: `D:\Vantt\app\data-integration` (Windows host)
- Container: `data_platform` (running, use `docker compose exec`)
- Metabase container: `metabase` (running, do not stop unless required)
- Branch: `main` (you can commit findings; ask before pushing)

### Start

Begin by:
1. Reading the 6 insights above carefully
2. Reading `.skills/data-pipeline/lessons-learned.md` L17-L20 for full context
3. Listing all the files in the "Files to Scan" section to understand the surface area
4. Asking the user any clarifying questions BEFORE starting the deep scan
5. Then proceed methodically through the analysis framework

End the session by writing the deliverable doc and producing a 1-paragraph
summary for the user with the headline findings.

---

## Notes for the prompt author (not part of the prompt)

This prompt was generated at the end of the 2026-04-08 debugging session. The
session uncovered that the original "Metabase lock" hypothesis was wrong, and
many existing locking-related code paths and docs reflect that wrong mental
model. A clean-slate audit will produce:

1. Trustworthy reference doc for future debugging
2. List of dead defensive code that can be removed
3. Clear separation of "real concurrency concerns" vs "imagined ones"
4. Prioritized improvement list

Reference for next session:
- Plan: `plans/260408-1611-fix-serving-db-hang-metabase-lock/plan.md`
- Commits today: `c6dcefa..ca67709` (11 commits, all on main)
