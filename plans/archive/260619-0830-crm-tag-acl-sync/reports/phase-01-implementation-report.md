# Phase 01 Implementation Report — Schema ACL for Tags

**Plan:** `plans/260619-0830-crm-tag-acl-sync/` · **Phase:** 01 — Schema ACL tables + source column
**Date:** 2026-07-07

## Migration number used

Confirmed next-free number by listing `crm/migrations/*.up.sql` (latest was `0038_action_dismissal_ttl`). Used **0039** — matches plan's re-check note, no drift.

## Files created

- `crm/migrations/0039_tag_acl_ext_mapping.up.sql`
- `crm/migrations/0039_tag_acl_ext_mapping.down.sql`

## DDL decisions vs phase doc

- Followed repo convention (0009/0003): `TEXT PRIMARY KEY` app-generated id style for `ext_tag_id`/`map_id`, not surrogate INTEGER.
- Added `created_at TEXT NOT NULL DEFAULT (strftime(...))` to both new tables — every other registry/mapping table in the schema (0009, 0003, 0038) has it; omitting would be an inconsistency, not a scope reduction (YAGNI doesn't apply to matching existing conventions).
- `direction` defaults `'inbound'`, `priority` defaults `0`, `is_active` defaults `1` (INTEGER bool, matching `crm_customer_profile.consent_contact` convention).
- Down migration uses real `ALTER TABLE ... DROP COLUMN` (not the older no-op-with-comment pattern from 0006/0016/0032/0036) — verified SQLite 3.46.1 in the `crm` container supports it, and migration 0035 (`crm_activity_log.outcome_reason`, most recent DROP-COLUMN precedent) already uses this same real-drop style. Followed the newer precedent since the version constraint no longer applies.
- Drop order in down.sql: index → `crm_party_tag` columns → `crm_ext_tag_map` (child) → `crm_ext_tag` (parent) — respects FK dependency now that `PRAGMA foreign_keys=ON` is set by the app connection.

## Apply + verify

`docker compose restart crm` → entrypoint log: `[entrypoint] running migrations …` → `[entrypoint] migrations OK` (no errors), followed by normal reverse-ETL/sync steps. Container healthy (`/healthz` 200 before restart, normal startup sequence after).

### PRAGMA table_info verification (live crm.db)

```
crm_ext_tag:
(0, 'ext_tag_id', 'TEXT', 0, None, 1)
(1, 'source_system', 'TEXT', 1, None, 0)
(2, 'ext_key', 'TEXT', 1, None, 0)
(3, 'ext_label', 'TEXT', 0, None, 0)
(4, 'created_at', 'TEXT', 1, "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')", 0)

crm_ext_tag_map:
(0, 'map_id', 'TEXT', 0, None, 1)
(1, 'ext_tag_id', 'TEXT', 1, None, 0)
(2, 'crm_tag_id', 'TEXT', 1, None, 0)
(3, 'direction', 'TEXT', 1, "'inbound'", 0)
(4, 'priority', 'INTEGER', 1, '0', 0)
(5, 'is_active', 'INTEGER', 1, '1', 0)
(6, 'created_at', 'TEXT', 1, "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')", 0)

crm_party_tag (extended):
(0, 'party_id', 'TEXT', 1, None, 1)
(1, 'tag_id', 'TEXT', 1, None, 2)
(2, 'tagged_by', 'TEXT', 0, None, 0)
(3, 'tagged_at', 'TEXT', 1, "strftime('%Y-%m-%dT%H:%M:%fZ', 'now')", 0)
(4, 'source', 'TEXT', 1, "'crm_user'", 0)
(5, 'ext_ref', 'TEXT', 0, None, 0)
```

Indexes confirmed present: `idx_ext_tag_map_active` on `(ext_tag_id, is_active)`, `idx_party_tag_source_party` on `(source, party_id)`, plus autoindexes for the two UNIQUE constraints (`crm_ext_tag(source_system, ext_key)`, `crm_ext_tag_map(ext_tag_id, crm_tag_id)`).

`schema_migrations` tail confirms `0039_tag_acl_ext_mapping.up.sql` applied, after `0038`.

### Backfill check

`SELECT source, COUNT(*) FROM crm_party_tag GROUP BY source` → `[('crm_user', 13)]` — all 13 pre-existing rows backfilled to `source='crm_user'` via the column DEFAULT, as required.

## Tests

Ran `docker exec crm python3 -m pytest crm/src/tests -q`.

- Before/baseline (per prior project memory, `project_approach_script_codex_pipeline.md`): 2 CRM tests fail pre-existing.
- After this change: same 2 failures, both unrelated to tag schema:
  1. `test_approach_script_handler.py` — collection `ImportError` (`wire_approach_script_router` missing from `approach_script_handler.py`) — pre-existing, unrelated module.
  2. `test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit` — file-cache staleness assertion, pre-existing, unrelated module.
- Full run (excluding the collection-error module to get a count): **796 passed, 1 failed** (the pre-existing file-repo test) — no new failures introduced by this migration.

## Acceptance criteria

- [x] `crm_ext_tag` + `crm_ext_tag_map` exist in crm.db
- [x] `crm_party_tag` has `source` (default `crm_user`) + `ext_ref`
- [x] Existing tags/rows unaffected — 13 rows backfilled, 0 lost, no new test failures

## Scope respected

No data seeded (Phase 02 scope). No changes to `tag_note_repository.py` or any sync consumer (Phase 03 scope). No commit made — changes left uncommitted for review.

Status: DONE
Summary: Migration 0039 adds `crm_ext_tag`/`crm_ext_tag_map` ACL tables + `source`/`ext_ref` on `crm_party_tag`, applied cleanly via container restart, schema verified via PRAGMA, existing 13 tag rows backfilled to `crm_user`, no new test failures (796 passed, 2 pre-existing unrelated failures unchanged).
Concerns/Blockers: None.
