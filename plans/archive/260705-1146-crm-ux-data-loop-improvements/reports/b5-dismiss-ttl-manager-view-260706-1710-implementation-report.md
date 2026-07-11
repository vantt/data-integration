# B5 Dismiss TTL by (party_id, action_type) + Manager View — Implementation Report

**Date:** 2026-07-06 · **Scope:** AI-10, AI-11 (phase-08-reassessment-fixes.md)

## Summary

Dismiss memory now keyed on `(party_id, action_type)` with a 30-day TTL (new
`crm_action_dismissal` table, migration 0038), fixing the bug where warehouse
weekly `action_id` regeneration made dismissed items reappear. A read-only
manager view at `GET /tasks/dismissed` (linked from Tasks Board S07) lists
active dismissals. 13 new tests pass; full suite 785 passed / 0 failed
(baseline pre-existing exclusions unchanged).

## AI-10 — migration/table design

**New table over overloading `crm_action_state`** (as instructed) — grain differs:
`crm_action_state` is per-`action_id` (episode-scoped, no expiry, used for both
dismiss AND snooze); `crm_action_dismissal` is per-`(party_id, action_type)`
with an explicit `dismissed_until` TTL. Migration `0038_action_dismissal_ttl.{up,down}.sql`:

```sql
CREATE TABLE crm_action_dismissal (
  party_id TEXT NOT NULL REFERENCES crm_party(party_id),
  action_type TEXT NOT NULL,
  dismissed_by_user_id TEXT REFERENCES crm_app_user(user_id),
  dismissed_at TEXT NOT NULL DEFAULT (strftime(...)),
  dismissed_until TEXT NOT NULL,
  PRIMARY KEY (party_id, action_type)
);
```

**Endpoint unchanged, resolution moved inside the repository** — `PATCH
/worklist/actions/{action_id}/dismiss` still takes only `action_id`. Rather than
threading `party_id`/`action_type` through all 3 call sites of
`ActionStatePort.dismiss()` (worklist dismiss, C360 `dismiss-session` bulk
endpoint, M08 `outcome_resolve_helpers.bulk_resolve`), the resolution lives once
in `SQLiteActionStateRepository.dismiss()` (`crm/src/adapters/outbound/sqlite/action_state_repository.py`):
it queries `cache.wh_action_queue`/`wh_sku_action_queue` joined through
`crm_party_identity` (same join pattern as `list_all_action_queue()`) to get
`(party_id, action_type)`, then upserts the dismissal row. All 3 callers benefit
automatically with zero call-site changes — **flagged design judgment call**:
this is a bigger blast-radius change than editing one handler, but avoids
inconsistent logic duplicated 3 ways with different available context (only the
worklist and C360 handlers have `party_id` in scope at all; the M08 bulk-resolve
path only has raw `action_id` strings).

**Dual write, not migration-away:** `dismiss()` still writes the legacy
`crm_action_state.status='dismissed'` for the given `action_id` (unchanged),
*and* the new dismissal row. The legacy write remains the source of truth for
`SQLiteCacheRepository._fetch_actions()` (C360 reason rail, per-episode display) —
untouched, out of AI-10's explicit scope. The new table is the sole basis for
the worklist's cross-episode memory.

**Query filter** (`cache_repository.py::list_all_action_queue`, both the
customer-level and SKU-level branches): added `LEFT JOIN crm_action_dismissal ad
ON ad.party_id = pi.party_id AND ad.action_type = a.action_type` +
`AND (ad.party_id IS NULL OR ad.dismissed_until <= now)`. Runs alongside the
pre-existing `crm_action_state.status != 'dismissed'` filter — either hides the row.

**Backfill:** none attempted (per phase-08's own suggested fallback: "nếu không
tra được thì bỏ qua"). Existing dismissed action_ids simply age out naturally as
the warehouse regenerates them; no historical action_id → party+type mapping is
retroactively created.

## AI-11 — manager view

**Location:** `GET /tasks/dismissed`, new template `dismissed_actions.html`,
route added to `screen_tasks_board.py` (S07), wired via a new optional
`dismissal_reader` param on `make_tasks_board_router()` → `sqlite_repos["action_state"]`
in `composition.py`. Chosen over S01 per the brief (avoids touching worklist
rendering files); linked via a plain "Đã bỏ qua" button in the Tasks Board
pagehead — not added to the global sidebar nav (kept surgical, no new `ui-spec`
screen ID needed).

**Read query:** `SQLiteActionStateRepository.list_active_dismissals()` — joins
`crm_action_dismissal` with `crm_party` (name → phone → placeholder fallback,
matching `TaskService._customer_fallback_label`'s existing pattern) and
`crm_app_user` (dismissed-by name). Returns `ActionDismissal` dataclass
(`crm/src/domain/entities/action_dismissal.py`). Filters `dismissed_until > now`
(active only).

**ui-spec:** Added `R15 — Dismiss TTL by (party_id, action_type)` to
`crm/docs/ui-spec/20-domain-rules.md` (prose + yaml contract), matching the
R14 style; added `R15` to `S01`/`S07` frontmatter `rules:` lists (validator
requires bidirectional declaration — confirmed via `node
.skills/ui-spec/tools/validate.mjs`, 0 new errors, only pre-existing
`VR-ASCII-DRIFT` warnings). Added a short line to S07's "Implementation Notes"
documenting the new route is a plain link, not part of the formal interaction
contract.

## Tests

New file `crm/src/tests/test_action_dismissal_ttl.py`, 13 tests, all passing:
- dismiss writes `crm_action_dismissal` keyed by resolved party/type + correct TTL
- dismiss still writes legacy `crm_action_state` (unaffected)
- unresolvable action_id skips the new table without raising
- **the actual B5 bug**: dismissal survives `action_id` regeneration for the same
  (party, action_type); a different `action_type` for the same party is NOT hidden
- TTL expiry lets the item reappear (see note below); re-dismiss after expiry
  sets a fresh TTL
- legacy snooze path untouched (writes only `crm_action_state`, zero
  `crm_action_dismissal` rows); dismiss + snooze on different actions don't interfere
- `list_active_dismissals()` enrichment (name, phone-fallback, dismissed-by name)
  and expiry exclusion

**Test-design note (flagged):** the "expiry → reappears" tests regenerate the
`action_id` before checking reappearance (deleting the old `wh_action_queue` row,
inserting a new one for the same party+type) rather than expiring the dismissal
against the *same, unchanged* `action_id`. Reason: the legacy
`crm_action_state.status='dismissed'` write has no expiry of its own (unchanged
pre-B5 behavior) and would keep the *exact same* `action_id` hidden forever
regardless of the new table's TTL. The 30-day "reappears normally" guarantee is
about the semantic action surviving warehouse `action_id` churn, which per the
design doc happens on a weekly cadence — so in production this is not an
observable gap. A dismiss on an `action_id` that somehow survives >30 days
unregenerated would remain hidden via the pre-existing per-episode mechanism,
which is no worse than before this change.

Test run: `test_action_dismissal_ttl.py` 13 passed. Broader suite:
`pytest src/tests -q --ignore=test_approach_script_handler.py
--ignore=test_approach_script_file_repository.py` → **785 passed, 0 failed**
(no new failures; the pre-existing approach-script exclusions are untouched).

## Deploy

`docker compose restart crm` — migration 0038 applied cleanly against the live
`crm.db` (verified `schema_migrations` + `sqlite_master` post-restart). Smoke-tested
`/worklist`, `/tasks`, `/tasks/dismissed` all return 200; dismissed view renders.

## Files touched

- `crm/migrations/0038_action_dismissal_ttl.{up,down}.sql` (new)
- `crm/src/domain/entities/action_dismissal.py` (new)
- `crm/src/adapters/outbound/sqlite/action_state_repository.py` (dismiss() dual-write, list_active_dismissals())
- `crm/src/adapters/outbound/sqlite/cache_repository.py` (list_all_action_queue filter, both branches)
- `crm/src/adapters/inbound/web/screen_tasks_board.py` (new `/tasks/dismissed` route + `DismissalReader` protocol)
- `crm/src/adapters/inbound/web/templates/dismissed_actions.html` (new)
- `crm/src/adapters/inbound/web/templates/tasks_board.html` (link to dismissed view)
- `crm/src/composition.py` (wire `dismissal_reader`)
- `crm/docs/ui-spec/20-domain-rules.md` (R15)
- `crm/docs/ui-spec/screens/S01-worklist-dashboard.md`, `S07-tasks-board.md` (frontmatter `rules:` + S07 implementation note)
- `crm/src/tests/test_action_dismissal_ttl.py` (new, 13 tests)

## Unresolved questions

- None blocking. Open item carried from phase-08 doc (§8, Q1): `crm_note`
  `visibility='private'` export treatment — unrelated to this workstream (D1),
  not touched here.
