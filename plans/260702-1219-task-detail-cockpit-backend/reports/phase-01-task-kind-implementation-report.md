# Phase 01 Implementation Report — `task_kind` column

**Date:** 2026-07-02
**Branch:** feature/task-detail-cockpit-backend

## Migration

- **File:** `crm/migrations/0032_task_kind.up.sql`
- **Down:** `crm/migrations/0032_task_kind.down.sql` (no-op — SQLite pre-3.35 can't DROP COLUMN; forward-fix preferred)
- **Statements:**
  1. `ALTER TABLE crm_task ADD COLUMN task_kind TEXT NOT NULL DEFAULT 'contact'` — fills ALL rows immediately, 0-NULL window
  2. `ALTER TABLE crm_task ADD COLUMN channel TEXT` — nullable, reserved
  3. `UPDATE … SET task_kind='generic' WHERE party_id IS NULL`
  4. `UPDATE … SET task_kind='internal' WHERE source='verify_account' OR source_ref LIKE 'verify_account%' OR lower(title) LIKE '%xác minh tài khoản%'`
- Idempotent: duplicate-column ADD silently skipped by runner; UPDATEs converge on re-run.

## Entity changes — `crm/src/domain/entities/task.py`

- Added constants: `TASK_KIND_CONTACT='contact'`, `TASK_KIND_INTERNAL='internal'`, `TASK_KIND_GENERIC='generic'`, `VALID_TASK_KINDS`
- Added fields to `Task` dataclass: `task_kind: str = "contact"`, `channel: Optional[str] = None`

## Repository changes — `crm/src/adapters/outbound/sqlite/task_repository.py`

All 10 sites updated:

| Site | Change |
|---|---|
| `_INSERT` | Added `task_kind, channel` to column list + `?` placeholders |
| `_UPDATE` | Added `task_kind = ?, channel = ?` before `WHERE task_id = ?` |
| `_GET_BY_ID` | Added `t.task_kind, t.channel` |
| `_GET_BY_SOURCE_REF` | Added `t.task_kind, t.channel` |
| `_GET_CUSTOMER_CLAIM` | Added `t.task_kind, t.channel` |
| `_LIST_BY_ASSIGNEE_AND_STATUS` | Added `t.task_kind, t.channel` |
| `_LIST_BY_ASSIGNEE` | Added `t.task_kind, t.channel` |
| `_LIST_BY_STATUS` | Added `t.task_kind, t.channel` |
| `_LIST_ALL` | Added `t.task_kind, t.channel` |
| `_LIST_UNASSIGNED_BY_STATUS` | Added `t.task_kind, t.channel` |
| `_LIST_UNASSIGNED` | Added `t.task_kind, t.channel` |
| `_LIST_BY_PARTY` | Added `t.task_kind, t.channel` |
| `_task_from_row` | Maps `row["task_kind"]`, `row["channel"]` (with defensive key-check fallback) |
| `insert()` param tuple | `task.task_kind, task.channel` appended |
| `update()` param tuple | `task.task_kind, task.channel` before `task.task_id` |

Note: `_GET_CLAIMED_BY_ACTION_IDS` intentionally NOT changed — it selects only `task_id, party_id, source_ref, assignee_user_id, assignee_name` and returns a `dict`, not a `Task`. No `_task_from_row` call.

## Test file

`crm/src/tests/test_task_kind_migration.py` — 15 tests across 3 classes:

- `TestMigration0032Compatibility` (8 tests): seeds rows before migration 0032, applies it, asserts 0-null + correct distribution + idempotency
- `TestTaskKindConstants` (3 tests): constant values, `VALID_TASK_KINDS` completeness, entity default
- `TestTaskKindRepoRoundTrip` (4 tests): insert/get_by_id round-trip, contact kind, update kind, existing optional-field defaults

## Test output

```
15 passed in 11.02s

PASSED test_0_nulls_after_migration
PASSED test_contact_classification
PASSED test_generic_classification
PASSED test_internal_classification_source
PASSED test_internal_classification_source_ref
PASSED test_internal_classification_title
PASSED test_distribution_sanity            ← 2 contact, 2 generic, 3 internal
PASSED test_idempotency                    ← re-run → no error, 0 NULLs
PASSED test_constants_values
PASSED test_valid_kinds_complete
PASSED test_task_default_kind
PASSED test_insert_and_get_by_id_preserves_task_kind
PASSED test_insert_contact_kind
PASSED test_update_task_kind
PASSED test_existing_task_entity_fields_still_work
```

Broader suite (excl. pre-existing fastapi import errors): **534 passed, 42 skipped, 4 pre-existing failures** — none in files touched by this phase. The 4 pre-existing failures (`test_approach_script_file_repository`, `test_cache_repository_customer_id` ×2, `test_worklist_filters`) touch no task/migration code.

## Files changed

- `crm/migrations/0032_task_kind.up.sql` (new)
- `crm/migrations/0032_task_kind.down.sql` (new)
- `crm/src/domain/entities/task.py`
- `crm/src/adapters/outbound/sqlite/task_repository.py`
- `crm/src/tests/test_task_kind_migration.py` (new)
