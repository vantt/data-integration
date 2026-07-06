# Phase 01 — Data: `task_kind` column + backfill + entity/repo wiring

## Context
Migrations: `crm/migrations/*.up.sql` (numbered, idempotent; runner `crm/src/adapters/outbound/sqlite/migrations.py` silently skips duplicate-column ADD). Verify highest number (party.py references 0016 → next likely **0017**).

## Files
- CREATE `crm/migrations/00NN_task_kind.up.sql` (+ `.down.sql` if repo keeps down files — 0004 has one).
- `crm/src/domain/entities/task.py` — add field + constants.
- `crm/src/adapters/outbound/sqlite/task_repository.py` — INSERT + all SELECT column lists + `_row_to_task` + `_UPDATE`.
- VERIFY `transformation/models/staging/stg_crm__task.sql` (add `task_kind` only if warehouse needs it).

## COMPATIBILITY GUARANTEE (non-negotiable)
Old rows must be fully compatible **from the migration alone — NO runtime code bridging**. After the migration, EVERY existing `crm_task` row has a definitive, correct `task_kind` (0 NULLs). The Python entity default (`'contact'`) is only for NEW in-memory objects; reads of old rows rely solely on the DB column.

**Why SQL-only is sufficient (not a shortcut):** `task_kind` is COARSER than `action_type`. Every warehouse action_type (CALL_NOW/REORDER_*/WIN_BACK/UPSELL/CROSS_SELL/SECOND_ORDER/HIGH_CANCEL_RISK/COLLECT_FEEDBACK) is outreach → `contact`. The only `internal` signal (verify_account) lives in `crm.db` itself (`source` + `title`). So NO join to `cache.wh_action_queue` (ephemeral, maybe unattached at migrate time, old action_ids may be gone). 100% classifiable within crm.db.

## Steps
1. Migration up.sql — **complete, deterministic, idempotent**:
   - `ALTER TABLE crm_task ADD COLUMN task_kind TEXT NOT NULL DEFAULT 'contact';`  ← SQLite fills ALL existing rows with `'contact'` immediately (no NULL window).
   - `ALTER TABLE crm_task ADD COLUMN channel TEXT;`  (nullable, reserved)
   - Backfill (ordered; covers 100% of rows — `contact` is the catch-all default already set):
     - `UPDATE crm_task SET task_kind='generic' WHERE party_id IS NULL;`
     - `UPDATE crm_task SET task_kind='internal' WHERE source='verify_account' OR source_ref LIKE 'verify_account%' OR lower(title) LIKE '%xác minh tài khoản%';`
   - Statement-per-line (runner splits on `;`; duplicate-column ADD is skipped on re-run).
   - Add a CHECK-style guard in the app layer (entity `VALID_TASK_KINDS`), not a DB CHECK (keep migration simple/idempotent).
2. Entity `task.py`: constants `TASK_KIND_CONTACT/_INTERNAL/_GENERIC`, `VALID_TASK_KINDS`; add `task_kind: str = "contact"`, `channel: Optional[str] = None`.
3. Repo `task_repository.py`: add `task_kind` (+`channel`) to `_INSERT` columns+`?`+param tuple; to **every** SELECT column list (`_GET_BY_ID`, `_GET_BY_SOURCE_REF`, all list queries); map in `_row_to_task`; add to `_UPDATE` (M05 edit may change kind).
4. NO Python enrichment pass. If a rare misclassified manual task is found later, fix via M05 edit (user-editable) — not code that patches reads.

## Tests / validation
- **Run against a COPY of the real `crm.db`** (not just an empty scratch DB) — this is the compatibility gate:
  - `SELECT COUNT(*) FROM crm_task WHERE task_kind IS NULL` → **must be 0**.
  - `SELECT task_kind, COUNT(*) FROM crm_task GROUP BY task_kind` → distribution sane (generic only where party_id NULL; internal only for verify rows; rest contact).
  - Spot-check: every row with `party_id IS NULL` = generic; every `source='verify_account'` = internal.
- Re-run migration on the same DB → **no error, no change** (idempotent; duplicate-column skipped, UPDATEs converge).
- `crm/src/tests/test_migrations_split.py` passes; add a case asserting `task_kind` column + NOT NULL + 0-null invariant on a seeded fixture.
- Repo round-trip: insert task with task_kind → `get_by_id` returns it; all existing task tests green (no read path assumes task_kind default).

## Rollback
- `.down.sql`: SQLite can't drop column pre-3.35 easily → down = no-op or table-rebuild; prefer forward-fix. Keep column nullable-safe so partial apply is harmless.
