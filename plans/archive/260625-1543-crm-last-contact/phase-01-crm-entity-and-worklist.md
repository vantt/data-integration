# Phase 01 — CRM Last Contact Entity + Worklist Integration

**Status:** ✅ DONE (shipped 2026-06-24)
**Commits:** `8e539d7`, `7bda654`, `7214ab8`

## What was built

### Migration
`crm/migrations/0027_last_contact.up.sql`
- `crm_last_contact` table: `party_id PK`, `last_activity_id FK→crm_activity`,
  `last_contacted_at`, `last_contact_result`, `channel`, `updated_at`
- Index on `last_contacted_at DESC`

### Domain entity
`crm/src/domain/entities/last_contact.py`
- `LastContact` dataclass
- `POSITIVE_OUTCOMES = {"answered", "replied", "met"}` — drives hide_contacted
- `PENDING_OUTCOMES = {"callback"}`, `REJECTED_OUTCOMES = {"refused"}`

### Repository
`crm/src/adapters/outbound/sqlite/last_contact_repository.py`
- `upsert()` — UPSERT with `WHERE excluded.last_contacted_at >= crm_last_contact.last_contacted_at`
  (newer always wins; older activity never overwrites)
- `get_map_for_parties(party_ids)` — single bulk IN query → `dict[party_id, LastContact]`

### Activity service hook
`crm/src/application/activity_service.py`
- After every `insert(activity)` where `activity.outcome` is set → `last_contact_repo.upsert()`
- Silent warn on failure (non-blocking)

### Worklist screen
`crm/src/adapters/inbound/web/screen_worklist.py`
- `LastContactReader` Protocol wired via `composition.py`
- `lc_map` bulk-fetched for all party_ids on every worklist load
- Merged into `party_extras[pid]["last_contact"]`
- `hide_contacted` second-pass filter: suppresses actions contacted positively in last 24h

### UI
`_wl_row.html` — `wl-lc-strip` badge on action + task rows (pos/neg/neu color)
`_wl_filter_bar.html` — "✅ Ẩn đã liên hệ" checkbox
`app.css` — `.wl-lc-strip`, `.wl-lc-badge--pos/neg/neu`, `.wl-lc-link`

### Filter logic
`crm/src/application/worklist_filters.py`
- `parse_filters` → `hide_contacted: bool`
- `active_filter_count` counts it
- `apply_filters` does NOT apply hide_contacted (needs party_extras, done in screen layer)

## Known gaps / Phase 2 prerequisites

- `crm_last_contact` lives only in `crm.db` (SQLite); warehouse knows nothing about it
- `mart_customer_action_queue` cannot join contact history → no warehouse-level suppression
- No analytics on contact frequency, conversion rate, outcome distribution
