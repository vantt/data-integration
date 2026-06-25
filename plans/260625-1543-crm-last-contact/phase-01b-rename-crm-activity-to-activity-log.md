# Phase 01b — Rename crm_activity → crm_activity_log

**Status:** 🔲 TODO
**Must complete before:** Phase 2 implementation (export query references table name)

## Scope

SQLite `ALTER TABLE crm_activity RENAME TO crm_activity_log`. SQLite 3.26+
auto-updates FK references and view/trigger bodies that mention the old name.

## Blast Radius

| File | Change |
|------|--------|
| `crm/migrations/0028_rename_activity_to_activity_log.up.sql` | NEW — `ALTER TABLE crm_activity RENAME TO crm_activity_log` |
| `crm/src/adapters/outbound/sqlite/activity_repository.py` | SQL strings: `crm_activity` → `crm_activity_log` (2 queries) |
| `crm/src/adapters/inbound/web/templates/fragments/c360_timeline_panel.html` | Display text only (cosmetic) |
| `crm/src/domain/entities/last_contact.py` | Comment: `FK → crm_activity` → `FK → crm_activity_log` |
| `crm/src/domain/entities/profile.py` | Comment only |
| `plans/260625-1543-crm-last-contact/phase-02-warehouse-writeback.md` | Update export_query strings |

## Migration

```sql
-- crm/migrations/0028_rename_activity_to_activity_log.up.sql
-- SQLite 3.26+ automatically rewrites FK references and trigger bodies
-- that mention the old table name when using RENAME TO.
ALTER TABLE crm_activity RENAME TO crm_activity_log;
```

## Notes

- Prior migrations (0004, 0012, 0013, 0019, 0027) still say `crm_activity` in
  their DDL text — that's fine, they are already applied and won't re-run.
- The `crm_last_contact.last_activity_id REFERENCES crm_activity(activity_id)`
  FK is auto-updated by SQLite RENAME TO. No manual DDL needed.
- No data loss; pure rename.
