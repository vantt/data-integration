# Phase 07 — End-to-end integration test + docs

**Priority:** P2 · **Status:** pending · **Effort:** 2h · **Blocked by:** Phase 05, Phase 06
**File ownership:** `crm/src/tests/test_suggestion_settings_end_to_end.py` (new),
`docs/project-changelog.md`, `crm/docs/ui-spec/00-overview.md` (index row only — Phase 06 owns the
P07 spec file itself; sequence them, do not edit in parallel).

## Context

- Test conventions: `crm/src/tests/conftest.py:30-74` — `tmp_data_dir`, `crm_db` (no migrations),
  `seeded_crm_db` (runs `db.apply_migrations()` at `:47`, seeds one `wh_party_seed` row).
- Cache-table fakes: `test_action_dismissal_ttl.py:39-98` — `_setup_cache_tables()`,
  `_insert_action()`, `_link_party()`; repo bundle builder `_make_repos()` at `:119-129`.
- Tests run locally against temp SQLite; no Docker.
- Existing suites that must stay green: `test_action_dismissal_ttl.py`,
  `test_worklist_suppression_do_not_contact.py`.

## Requirements

**Functional**
1. One end-to-end test that drives the **service** (not raw SQL) and asserts against
   `SQLiteCacheRepository.list_all_action_queue()` — proving the panel's toggle really changes the
   worklist, per mart.
2. Prove pre-emptive suppression: suppress before the action exists in `cache.wh_*`, then insert the
   action, then assert it never surfaces.
3. Prove `do_not_contact` is untouched.
4. Prove the quick-dismiss → panel handoff (locked decision #6).

**Non-functional**
5. `_setup_cache_tables()` must be extended to create `wh_action_scenario_registry` and seed the 13
   catalog rows, so the service's catalog validation works in tests. Extract the shared helpers into
   `crm/src/tests/helpers_action_queue_fixtures.py` if three files now copy them.

## Test matrix (end-to-end)

| # | Scenario | Assert |
|---|---|---|
| E1 | Party P has customer-level `REORDER_NUDGE` and SKU-level `REORDER_NUDGE`. `service.suppress(P,'REORDER_NUDGE','mart_customer_action_queue','2026-09-30')`. | `list_all_action_queue()` returns only the SKU row (`supply_stream` non-NULL) |
| E2 | Mirror: suppress the SKU mart. | only the customer row (`supply_stream` NULL) |
| E3 | Suppress both. | neither |
| E4 | `service.unsuppress(...)` after E1. | both rows back |
| E5 | Suppress `WIN_BACK` for P **before** any `WIN_BACK` action exists; then insert one. | never appears in the queue |
| E6 | Quick-dismiss a SKU action via `action_state.dismiss(action_id)`, then `service.get_settings(P)`. | that row shows suppressed, `source_mart='mart_customer_sku_action_queue'`, `+30d` |
| E7 | Then `service.suppress(...)` same key with a later date. | one row, date updated, `dismissed_by_user_id` updated |
| E8 | Suppression whose `dismissed_until` is in the past. | action back in the queue; `get_settings` reports `is_expired` |
| E9 | Log a `do_not_contact` activity for P, suppress nothing. | party gone from the queue entirely (mechanism #3 unchanged) |
| E10 | Legacy pre-0046 row expanded by the backfill. | both grains hidden |
| E11 | `service.get_settings` for a party with no dismissals. | 13 rows, all "bật", `GIFT_TO_PURCHASE` flagged globally-disabled |

## Related code files

**Create**
- `crm/src/tests/test_suggestion_settings_end_to_end.py`
- `crm/src/tests/helpers_action_queue_fixtures.py` (only if extraction is warranted)

**Modify**
- `crm/src/tests/test_action_dismissal_ttl.py` — import from the extracted helper if created.
- `docs/project-changelog.md` — feature entry.
- `crm/docs/ui-spec/00-overview.md` — P07 index row (if Phase 06 did not already add it).

## Implementation steps

1. Extend `_setup_cache_tables()` with the `wh_action_scenario_registry` DDL (mirror Phase 02's
   `cache_schema.sql` block) and insert the 13 rows.
2. Write E1-E11.
3. Run the full CRM suite: `pytest crm/src/tests -q`.
4. Changelog entry covering: the new panel, the schema change, and — prominently — the **D4 behaviour
   change** (quick-dismiss is now grain-specific).
5. Check whether `docs/codebase-summary.md` / `docs/system-architecture.md` describe the CRM
   suppression mechanisms; if yes, update them. If not, skip — do not create new top-level docs
   (YAGNI). `grep -rn "crm_action_dismissal" docs/` first.

## Todo list

- [x] Registry fixture in the cache-table helper (`helpers_action_queue_fixtures.py`, new — extracted since this was the 4th copy)
- [x] E1-E11 written and green (11/11)
- [x] `pytest crm/src/tests -q` fully green — 1196 passed, 1 skipped (pre-existing skip, unrelated)
- [x] Changelog entry incl. the behaviour-change note (`docs/project-changelog.md`)
- [x] `grep -rn "crm_action_dismissal" docs/` → no matches, nothing to update (top-level docs don't describe CRM suppression mechanisms)
- [x] P07 in the ui-spec index (00-overview.md table + directory tree + S03.hosts + 30-states-and-errors.md) — `ui-spec validate` 0 warnings/errors

## Success criteria

- E1 and E2 both pass — this is the single most important assertion in the whole plan.
- Full CRM suite green with zero skips added.
- No test asserts on hardcoded Vietnamese label text from the catalog (labels are seed data and will
  change) — assert on `action_type` + `source_mart` instead.

## Risk assessment

| Risk | L×I | Mitigation |
|---|---|---|
| E1/E2 pass for the wrong reason (both rows filtered by something else) | Med×High | Every case asserts the *complement* too: the row that must survive is asserted present, not just the suppressed one absent |
| Helper extraction breaks `test_action_dismissal_ttl.py` | Med×Low | Extract only if 3+ copies; run that suite immediately after |
| Fixture registry drifts from the real seed | Med×Med | Fixture asserts 13 rows and the 6/7 mart split, mirroring Phase 02's success criterion |
| Tests rely on wall-clock `now` near midnight ICT | Low×Med | Use dates ≥ 2 days out / ≥ 2 days past; never "today" |

## Rollback

Delete the test file. No production impact.

## Security considerations

Tests use synthetic parties only — no production data, no PII in fixtures.

## Next steps

- Release note to CS/Sales explaining the three distinct concepts: "Bỏ qua việc" (one card),
  "Cài đặt gợi ý" (this panel), "Đừng gọi nữa" (never contact).
- Deploy order: dbt (Phase 01) → reverse-ETL (Phase 02) → CRM app (03+04+05+06 in one deploy).
