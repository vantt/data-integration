# Worklist label clarity (phase-09) + 8 pre-existing test fixes — implementation report

Date: 2026-07-06

## Part A — 8 pre-existing failing tests: root cause + fix

All 8 were **stale tests/fixtures**, not code regressions — verified via `git log -p` on each
production file to confirm the behavior change was deliberate (a prior commit), then the test
was checked to see if it had been updated alongside. In every case it hadn't.

1. **`test_worklist_filters.py::test_parse_filters_defaults`**
   Root cause: commit `68a6a028` (two-row collapsible filter bar) added 3 new keys
   (`strategic_tier`, `value_group`, `adv`) to `parse_filters()`'s return dict but the test's
   exact-equality assertion was never updated.
   Fix: updated the expected dict to include the 3 new keys (all default `""`).

2. **`test_cache_repository_customer_id.py::test_list_all_action_queue_customer_id_present`**
   **`::test_list_all_action_queue_customer_id_none_when_no_base_row`**
   Root cause: same commit `68a6a028` added a `LEFT JOIN cache.wh_customer_tier` to
   `list_all_action_queue()`'s SQL (for the new strategic_tier/value_group filters). The test's
   `_setup_cache_tables()` fixture never created that table, so the query hit `sqlite3.OperationalError:
   no such table`, the code's safety-net fallback caught it and returned `[]` (by design — degrades
   gracefully when a table is absent), and the test's `len(items) == 1` assertion failed.
   Fix: added `CREATE TABLE IF NOT EXISTS wh_customer_tier (...)` to the fixture.

3. **`test_web_templating.py::TestWorlistFilterBar::test_action_type_chips_rendered_for_available_types`**
   **`::test_all_new_action_types_have_chips`**
   Root cause: same commit `68a6a028` moved the action-type `<select>` into filter-bar "row 2",
   which only renders when `filters.adv` is truthy. Tests built a context without `adv` set, so the
   `<select>`/`<option>` markup was never rendered.
   Fix: set `filters={"adv": "1", ...}` in these two tests to open row 2.

4. **`::test_active_filter_badge_and_clear_all_shown_when_filters_active`**
   Root cause: same commit removed the old `<span class="badge badge--primary">` counter (verified
   via `git show 68a6a028 -- _wl_filter_bar.html`, which shows its removal) in favor of the "Xóa filter"
   button as the sole active-filter signal. Test still asserted the removed CSS class.
   Fix: dropped the `"badge--primary" in html` assertion; kept the "Xóa filter" check (the actual
   current signal).

5. **`TestBandCollapseAndOverflow::test_xem_them_shown_when_band_exceeds_cap`**
   **`::test_xem_them_shown_when_band3_exceeds_cap_5`**
   Root cause: commit `0164c3ab` (paginated overflow) added `request.url.query` to the "Xem thêm"
   overflow link in `_wl_bands.html`. In production `request` is always in context (FastAPI's
   `Jinja2Templates.TemplateResponse` injects it), but the test's `_render_fragment()` uses a bare
   `jinja2.Environment` with no `request` stub, so rendering raised `jinja2.exceptions.UndefinedError`.
   Fix: added a `SimpleNamespace(url=SimpleNamespace(query=""))` stub as `request` in `_base_ctx()`
   (used by every test in the file — harmless for tests that don't hit that code path).

Cascading fix required by R3 (see Part B): `TestActionTypeBadges::test_badge_class_is_styled_not_neutral`
started failing once the badge started showing the short VN label instead of the raw
`action_type` code — updated its assertion to check for `bdg_label("action_type", action_type)`
instead of the raw code (this is a Part B side-effect, not one of the original 8, but reported
here for completeness since the suite must be 0-red at the end).

## Part B — phase-09 R1-R9

Implemented exactly per the phase file's decided requirements — see the updated table in
`plans/260705-1146-crm-ux-data-loop-improvements/phase-09-worklist-label-clarity.md` for
file:line references per requirement. Summary:

- **R1/R2**: `badge_catalog.py` gained `_ACTION_TYPE_SHORT_LABEL` (parallel dict, not a 3rd
  `BadgeDef` field — avoids forcing every other domain to carry an unused label) + `bdg_label()`.
  `fmt_badge.py` exposes `bdg_label_filter`, wired as Jinja filter `bdg_label` in `composition.py`
  (production) and in `test_web_templating.py`'s `_make_env()` (mirrors production wiring).
- **R3**: action-row badge text now `a.action_type | bdg_label('action_type')`; tooltip (`bdg_tip`)
  untouched, still shows the full hint.
- **R4**: action row no longer renders `a.customer_key` at all. When `customer_name` is empty, falls
  back to the preferred identity's phone (`identity_type == 'phone'` only, per the phase's risk
  note — zalo/facebook prefs do NOT leak as a substitute) or `"(chưa xác định)"`.
- **R5**: `task_service.py` — title fallback (used when `rationale_vi` is empty) no longer uses
  `action.customer_key`. Added `_customer_fallback_label()` (name → phone via `party_repo.get_by_id()`
  → placeholder) and a **local duplicate** of the short-label dict (not imported from
  `badge_catalog.py` — `task_service.py` is application layer and must not import the web adapter,
  per the project's existing clean-arch rule from commit `9906994f`). Both `claim_action_item` and
  `_process_action` now use `[{_action_type_short_label(...)}] {label}`.
- **R6**: task-row band-0 cancel button text "Dọn" → "Hủy" (endpoint unchanged: `PATCH /tasks/{id}/cancel`).
- **R7**: task-row band-0 reschedule button icon changed to "📅 Dời hạn" (was plain text) to visually
  distinguish it from the "⏰" snooze dropdown when both appear on the same row (endpoint unchanged:
  `GET /modals/m05`).
- **R8**: task-row "Mở hồ sơ" → "Xem 360" (now matches the action row's existing label for the
  identical `/customers/{pid}` destination).
- **R9**: action-row "📞 Gọi chế độ" → "📞 Gọi" (tooltip "Vào chế độ gọi với hàng đợi" unchanged). Verified
  no collision with the task row's `contact_btn` macro (also labeled "📞 Gọi") — they never render on
  the same row (`contact_btn` is task-row-only).
- **ui-spec**: `crm/docs/ui-spec/screens/S01-worklist-dashboard.md` documented these exact labels —
  updated the layout sample, `elements` map, row-detail bullets, and the A2 call-mode note.

### Tests added

- `crm/src/tests/test_task_service_title_fallback.py` (new file): 7 tests covering
  `claim_action_item` and `generate_tasks_from_action_queue`/`_process_action` — customer_key never
  leaks, name/phone/placeholder fallback chain, short-label in the `[...]` prefix.
- `crm/src/tests/test_web_templating.py`: new `TestActionRowLabelClarity` class (4 tests) — short
  label for `call_now`/`reorder_nudge`, no-hash-on-empty-name, phone fallback via `party_extras`,
  name takes priority over phone/placeholder.
- Updated `TestActionTypeBadges::test_badge_class_is_styled_not_neutral` (5 parametrized cases) to
  assert on the short label instead of the raw code.

### Live verification

Restarted the `crm` container (`docker compose restart crm`) and fetched `/worklist/fragment`
directly: confirmed "Gọi ngay" (20×) / "Nhắc tái đặt" (2×) short labels render, "Xem 360" (25×)
replaces all "Mở hồ sơ", zero occurrences of "Dọn" / "Gọi chế độ" remain. No band-0 task rows exist
in the current seed data, so "📅 Dời hạn"/"Hủy" weren't exercised live — covered by the unit/template
tests instead.

## Final test count

`python -m pytest src/tests -q --ignore=src/tests/test_approach_script_handler.py
--ignore=src/tests/test_approach_script_file_repository.py` → **772 passed, 0 failed**
(baseline was 749 passed / 9 failed; +8 from the fixed pre-existing failures, +11 new tests
added for phase-09 R1-R9, net +23 → 772).

## Files touched

- `crm/src/tests/test_worklist_filters.py`
- `crm/src/tests/test_cache_repository_customer_id.py`
- `crm/src/tests/test_web_templating.py`
- `crm/src/tests/test_task_service_title_fallback.py` (new)
- `crm/src/adapters/inbound/web/badge_catalog.py`
- `crm/src/adapters/inbound/web/fmt_badge.py`
- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html`
- `crm/src/application/task_service.py`
- `crm/src/composition.py` (filter registration only — required to wire R2's new `bdg_label` filter
  into production; not in the original ownership list but necessary or R1-R3 would be dead code in prod)
- `crm/docs/ui-spec/screens/S01-worklist-dashboard.md`
- `plans/260705-1146-crm-ux-data-loop-improvements/phase-09-worklist-label-clarity.md` (status +
  per-requirement annotations)

## Unresolved questions

- None. `composition.py` was touched despite not being in the explicit Part B ownership list — flagging
  this since it's the one exception: without it, `bdg_label` filter would never be registered in the
  real app (only in the test's mirrored `_make_env()`), silently breaking R1-R3 in production while
  tests stayed green. Judged necessary; happy to revert if the controller wants that wiring done
  separately.
