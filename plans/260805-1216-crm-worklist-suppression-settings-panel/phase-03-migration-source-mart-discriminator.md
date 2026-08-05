# Phase 03 — Migration 0046: add `source_mart` to `crm_action_dismissal`

**Priority:** P2 · **Status:** pending · **Effort:** 1.5h · **Blocked by:** —
**File ownership:** `crm/migrations/0046_action_dismissal_source_mart.{up,down}.sql` + one new test file.

## Context

Current DDL — `crm/migrations/0038_action_dismissal_ttl.up.sql:12-23`:
```sql
CREATE TABLE IF NOT EXISTS crm_action_dismissal (
  party_id             TEXT    NOT NULL REFERENCES crm_party(party_id),
  action_type          TEXT    NOT NULL,
  dismissed_by_user_id TEXT    REFERENCES crm_app_user(user_id),
  dismissed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  dismissed_until      TEXT    NOT NULL,
  PRIMARY KEY (party_id, action_type)
);
CREATE INDEX IF NOT EXISTS idx_action_dismissal_until
  ON crm_action_dismissal (dismissed_until);
```
Current max migration: `0045_activity_draft_lifecycle` → this is **0046**.

## Key insights (verified)

1. **Runner:** `crm/src/adapters/outbound/sqlite/migrations.py:90-158`. Applies `*.up.sql` only, in
   glob-sorted order, tracked in `schema_migrations` (`:22-27`). Called on every app start via
   `connection.py:112-115`.
2. **`.down.sql` is NEVER executed** by the runner (`:32` globs `*.up.sql`). It is documentation +
   manual-rollback material. There is **no existing up/down migration test** in the repo.
3. **Each file runs inside a SAVEPOINT** (`:125`), each statement inside an inner SAVEPOINT (`:134`).
   → A multi-statement table rebuild is atomic. Good.
4. **`PRAGMA foreign_keys` cannot be toggled inside a transaction** — SQLite silently ignores it.
   The migration runs inside a savepoint with `foreign_keys=ON` (`connection.py:53`), so
   **do not write `PRAGMA foreign_keys=OFF` into the migration**; it would be a no-op that lulls the
   reader into a false sense of safety.
5. **Safe anyway:** `crm_action_dismissal` has only *outgoing* FKs (→ `crm_party`, → `crm_app_user`).
   Grep confirms no other table or view references it, so DROP + RENAME rewrites nothing.
6. **Statement splitter** (`:45-87`) splits on `;` at depth 0 and treats a line that is exactly
   `BEGIN` as a trigger-body opener. A plain DDL rebuild is fine — but **do not** put a bare `BEGIN`
   on its own line, and keep `--` comments out of the middle of a statement's code portion.
7. The runner swallows only `duplicate column name` errors (`:141`). Everything else rolls the file back.

## Locked decision — backfill by row expansion (D2)

Existing rows mean "suppress this action_type for this party, everywhere" (the read path was
mart-agnostic: `cache_repository.py:179-181, 227-229`). Two candidate backfills:

| Option | Read predicate | Panel semantics | Verdict |
|---|---|---|---|
| `'ANY'` sentinel | `ad.source_mart IN (:mart, 'ANY')` — an OR in a hot query | ambiguous: un-toggling mart A must delete the shared `'ANY'` row, which silently un-toggles mart B | rejected |
| **Expand into 2 rows** | `ad.source_mart = :mart` — plain equality | 1 row = 1 toggle, always | **chosen** |

Expansion preserves legacy semantics exactly. Volume is trivial (30-day TTL, ~10 users). A row for an
`(action_type, mart)` combination that does not exist in the registry simply never matches anything.

> Deviation note: the feature request offered `'ANY'`/NULL as an *example* default and explicitly
> delegated the choice ("decide a sensible default"). Flagged for confirmation in the plan summary.

## Requirements

**Functional**
1. New column `source_mart TEXT NOT NULL` with `CHECK (source_mart IN ('mart_customer_action_queue','mart_customer_sku_action_queue'))`.
2. PK becomes `(party_id, action_type, source_mart)`.
3. Every pre-existing row is duplicated into both mart values, preserving `dismissed_by_user_id`,
   `dismissed_at`, `dismissed_until`.
4. `idx_action_dismissal_until` preserved.
5. `.down.sql` restores the 0038 shape, collapsing duplicates back to one row per
   `(party_id, action_type)` — keeping the row with the LATEST `dismissed_until` (least surprising:
   never shortens an active suppression on rollback).

**Non-functional**
6. Migration is idempotent-safe to re-run in the sense the runner requires (it only runs once per
   version row, but must not corrupt if applied to an already-migrated DB — guard with a rebuild that
   starts from `CREATE TABLE ... _new`).
7. No `PRAGMA` statements in the file.

## Related code files

**Create**
- `crm/migrations/0046_action_dismissal_source_mart.up.sql`
- `crm/migrations/0046_action_dismissal_source_mart.down.sql`
- `crm/src/tests/test_migration_action_dismissal_source_mart.py`

**Modify** — none in this phase. **Delete** — none.

## Implementation steps

1. Write `0046_...up.sql`. Statement order (each terminated by `;` on its own logical statement):
   ```sql
   -- Suppression is now tracked per originating mart so a customer-level REORDER_NUDGE can be
   -- turned off while the per-SKU REORDER_NUDGE for the same customer keeps firing. SQLite cannot
   -- alter a primary key in place, so the table is rebuilt. Pre-existing rows were mart-agnostic
   -- ("suppress everywhere") and are expanded into one row per mart to preserve that meaning.
   CREATE TABLE IF NOT EXISTS crm_action_dismissal_new (
     party_id             TEXT    NOT NULL REFERENCES crm_party(party_id),
     action_type          TEXT    NOT NULL,
     source_mart          TEXT    NOT NULL
       CHECK (source_mart IN ('mart_customer_action_queue','mart_customer_sku_action_queue')),
     dismissed_by_user_id TEXT    REFERENCES crm_app_user(user_id),
     dismissed_at         TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
     dismissed_until      TEXT    NOT NULL,
     PRIMARY KEY (party_id, action_type, source_mart)
   );

   INSERT OR IGNORE INTO crm_action_dismissal_new
     (party_id, action_type, source_mart, dismissed_by_user_id, dismissed_at, dismissed_until)
   SELECT d.party_id, d.action_type, m.mart_name,
          d.dismissed_by_user_id, d.dismissed_at, d.dismissed_until
   FROM crm_action_dismissal d
   CROSS JOIN (
     SELECT 'mart_customer_action_queue' AS mart_name
     UNION ALL
     SELECT 'mart_customer_sku_action_queue'
   ) m;

   DROP TABLE crm_action_dismissal;

   ALTER TABLE crm_action_dismissal_new RENAME TO crm_action_dismissal;

   CREATE INDEX IF NOT EXISTS idx_action_dismissal_until
     ON crm_action_dismissal (dismissed_until);

   CREATE INDEX IF NOT EXISTS idx_action_dismissal_party
     ON crm_action_dismissal (party_id, source_mart);
   ```
   The second index serves the new per-party panel read (Phase 04).
2. Write `0046_...down.sql` as the mirror rebuild: create the 0038-shaped table, insert
   `SELECT party_id, action_type, dismissed_by_user_id, dismissed_at, MAX(dismissed_until)
   ... GROUP BY party_id, action_type`, drop, rename, recreate `idx_action_dismissal_until`.
3. Write `test_migration_action_dismissal_source_mart.py` (first migration test in the repo — keep it
   small, it sets the pattern):
   - Build a temp DB, run migrations up to 0045 only is NOT supported by the runner → instead:
     run all migrations, then manually re-create the 0038 shape, insert 2 legacy rows, then execute
     the `0046 .up.sql` file text directly against the connection and assert 4 rows with the right
     mart split. This tests the SQL, not the runner.
   - Then execute the `.down.sql` text and assert 2 rows with the later `dismissed_until` retained.
   - Assert the `CHECK` rejects `source_mart = 'nonsense'`.
4. Run the full CRM test suite — `test_action_dismissal_ttl.py` **will fail** at this point because
   `_dismiss_by_party_and_type()` still writes 5 columns with `ON CONFLICT(party_id, action_type)`.
   That is expected; Phase 04 fixes it. Land 03 + 04 together in one PR, or keep 03 on a branch until
   04 is ready — do not merge 03 alone.

## Todo list

- [x] `0046_action_dismissal_source_mart.up.sql`
- [x] `0046_action_dismissal_source_mart.down.sql`
- [x] `test_migration_action_dismissal_source_mart.py` (up, down, CHECK) — 3/3 pass
- [x] Verify no `PRAGMA` in the migration files
- [x] Full suite run: 11 failures, all in `test_action_dismissal_ttl.py` (`ON CONFLICT(party_id, action_type)` mismatch — expected, Phase 04 fixes), 1144 passed otherwise, zero unrelated regressions

## Success criteria

- On a DB with N pre-existing dismissals, post-migration count is exactly 2N and every legacy
  `(party_id, action_type)` appears once per mart with unchanged `dismissed_until`.
- `PRAGMA integrity_check` and `PRAGMA foreign_key_check` return clean after the migration.
- Inserting `source_mart='foo'` raises `CHECK constraint failed`.
- `.down.sql` returns the table to the exact 0038 column list and PK.

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| Statement splitter mangles the multi-statement file | Low×High | No bare `BEGIN` lines; no `;` inside trailing comments; test executes the real file text (step 3) |
| Someone adds `PRAGMA foreign_keys=OFF` "for safety" | Med×Med | Insight #4 documented in the migration header comment itself |
| A legacy row's `party_id` no longer exists in `crm_party` → FK failure on INSERT | Low×High | FK was already enforced on write, so data is valid; `PRAGMA foreign_key_check` in step 5 confirms |
| Phase 03 merged without Phase 04 → prod write path broken (`ON CONFLICT(party_id, action_type)` no longer matches the PK) | Med×High | Step 4: never merge 03 alone. Make it explicit in the PR description |
| Rollback collapses two different end-dates into one | Low×Low | `.down.sql` keeps `MAX(dismissed_until)` — documented, never shortens |

## Rollback

Run `0046_...down.sql` manually, then `DELETE FROM schema_migrations WHERE version = '0046_action_dismissal_source_mart.up.sql'`.
Requires Phase 04/05 code to be reverted first, otherwise the app writes a column that no longer exists.

## Security considerations

No new PII. FK to `crm_app_user` preserved so "bởi ai" stays attributable.

## Next steps

Unblocks Phase 04 (writes) and Phase 05 (reads), which are parallel and touch disjoint files.
