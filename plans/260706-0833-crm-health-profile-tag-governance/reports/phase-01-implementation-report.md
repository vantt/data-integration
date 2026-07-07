# Phase 01 Implementation Report — Schema: is_provisional + is_archived + Health Tag Seed

## Executed Phase
- Phase: phase-01-schema
- Plan: `plans/260706-0833-crm-health-profile-tag-governance/`
- Status: completed

## Migration number used
`0041` — no collision. Checked `crm/migrations/` before and after: highest existing was `0039_tag_acl_ext_mapping`; neither `0040` nor `0041` existed at time of check or after restart. Used `0041` exactly as instructed.

## Files Modified
- `crm/migrations/0041_tag_provisional_archived.up.sql` (new, 21 lines)
- `crm/migrations/0041_tag_provisional_archived.down.sql` (new, 10 lines)

No app code changes — searched `crm/src` for a hardcoded `TagCategory` class/enum (`class.*Category`, `'segment'|'profile'|'action'`). Only hit was a false positive (`class="fact__k"` HTML attribute in `order_context_tab.html`). No Python category enum exists → skipped step 4 per YAGNI (phase doc's own "if hardcoded" condition not met).

## Live DB verification (trust-DB-over-doc, as instructed)
`PRAGMA table_info(crm_tag)` before writing migration showed 5 cols: `tag_id, name, category, color, display_label` (display_label from migration 0017, nullable — not in phase doc's original column list but included in my INSERT for UX consistency with 0017's "falls back to name in UI" convention; harmless since nullable).

Actual live distinct categories: `behavioral, preference, risk, vip_tier` (post-migration-0014 values) — differs from phase doc's claim of `segment/profile/action` (that text was stale/wrong; doc itself flags DB as source of truth). Irrelevant to this migration since `category` has no CHECK constraint (free TEXT) and my seed uses a brand-new `health_domain` category value.

## Tasks Completed
- [x] `ALTER TABLE crm_tag ADD COLUMN is_provisional INTEGER NOT NULL DEFAULT 0`
- [x] `ALTER TABLE crm_tag ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0`
- [x] Seed 8 canonical `health_domain` tags (`tag-health-0001`..`0008`), `is_provisional=0, is_archived=0`, plus Vietnamese `display_label` values
- [x] `.down.sql`: DELETE 8 seed rows by tag_id, then `DROP COLUMN is_archived` / `is_provisional` (SQLite 3.46 real DROP COLUMN, same pattern as 0035/0039)
- [x] `crm_customer_profile.custom` JSON keys (`health_context_raw`, `health_context_raw_reviewed`) — documentation-only per phase doc, no code touched
- [x] Applied via `docker compose restart crm` — logs show `[entrypoint] migrations OK`
- [x] Verified `PRAGMA table_info(crm_tag)` — 7 columns total, `is_provisional`/`is_archived` both `INTEGER NOT NULL DEFAULT 0`
- [x] Verified 8 health_domain rows present with correct values
- [x] Verified L2 provisional case (`category IS NULL, is_provisional=1`) not rejected — scratch insert/select/delete, no residue left
- [x] Ran full CRM test suite

## PRAGMA output (post-migration)
```
(0, 'tag_id', 'TEXT', 0, None, 1)
(1, 'name', 'TEXT', 1, None, 0)
(2, 'category', 'TEXT', 0, None, 0)
(3, 'color', 'TEXT', 0, None, 0)
(4, 'display_label', 'TEXT', 0, None, 0)
(5, 'is_provisional', 'INTEGER', 1, '0', 0)
(6, 'is_archived', 'INTEGER', 1, '0', 0)
```

## Seed verification
```
('tag-health-0001', 'tim-mach', 'health_domain', '#E53E3E', 'Tim mạch', 0, 0)
('tag-health-0002', 'ho-hap', 'health_domain', '#3182CE', 'Hô hấp', 0, 0)
('tag-health-0003', 'mien-dich', 'health_domain', '#38A169', 'Miễn dịch', 0, 0)
('tag-health-0004', 'xuong-khop', 'health_domain', '#DD6B20', 'Xương khớp', 0, 0)
('tag-health-0005', 'tieu-hoa', 'health_domain', '#D69E2E', 'Tiêu hóa', 0, 0)
('tag-health-0006', 'than-kinh-ngu', 'health_domain', '#805AD5', 'Thần kinh & giấc ngủ', 0, 0)
('tag-health-0007', 'nang-luong', 'health_domain', '#319795', 'Năng lượng', 0, 0)
('tag-health-0008', 'da', 'health_domain', '#D53F8C', 'Da', 0, 0)
```

L2 provisional scratch test: inserted `('tag-test-l2-scratch', 'test-l2-scratch', NULL, NULL, 1, 0)` → succeeded, no constraint rejection. Deleted immediately after; post-cleanup count = 0.

## Tests Status
- Type check: N/A (Python, no mypy configured for this module per existing repo pattern)
- Unit tests: `docker compose exec crm python3 -m pytest crm/src/tests -q --continue-on-collection-errors` → **1 failed, 796 passed, 1 collection error** (both pre-existing, unrelated to `crm_tag`/this migration — `test_approach_script_handler.py` ImportError for `wire_approach_script_router`, and `test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit` — both in the `approach_script` module, matches known pre-existing failures per prior session memory). No new failures introduced.

## Issues Encountered
None. No file-ownership conflicts; migration number 0041 confirmed free both before writing and after restart (other agent's 0040 did not collide).

## Next Steps
Phase 02 (S14 collect — health chips + free text + inline provisional POST) and Phase 03 (Tag Governance Admin) are now unblocked. Both should read `crm_tag.is_provisional`/`is_archived` and the 8 seeded `health_domain` tags. Note for Phase 02/03 implementer: `domain/entities/profile.py::Tag` dataclass does NOT yet have `is_provisional`/`is_archived` fields — intentionally left out of Phase 01 (schema-only scope); add them when building the app logic that reads/writes those flags.

## Unresolved Questions
None.

Status: DONE
Summary: Migration 0041 (up/down) adds crm_tag.is_provisional/is_archived + seeds 8 canonical health_domain tags; applied via docker compose restart crm (migrations OK), verified PRAGMA/seed/L2-provisional-insert live, no hardcoded TagCategory found so step 4 skipped, full test suite shows only 2 known pre-existing approach_script failures (unrelated).
Concerns/Blockers: None.
