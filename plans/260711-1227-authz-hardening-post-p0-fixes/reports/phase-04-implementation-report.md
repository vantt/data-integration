# Phase 4 Implementation Report — No-Party Task Creation Fix

## Executed Phase
- Phase: phase-04-no-party-task-creation-fix
- Plan: D:\Vantt\app\data-integration\plans\260711-1227-authz-hardening-post-p0-fixes
- Status: completed

## Files Modified
- `crm/src/adapters/inbound/web/screen_tasks_board.py` (+21/-6 net; `handle_create_task` now ~132-176)
  - added import `from adapters.inbound.web.screens.modals.screen_modal_shared import parse_priority`
  - `handle_create_task`: added Form params `priority` (default `"P3"`), `task_kind` (default `""`), `source` (default `"manual"`), `source_ref` (default `""`), `return_to` (default `"redirect"`)
  - `task_data` dict now forwards `source` (was hardcoded `"manual"`), `priority` via `parse_priority()` (was hardcoded `0`; `parse_priority("P3")==0` so default behavior for existing callers is unchanged), plus new `task_kind`/`source_ref` keys
  - response: `return_to=="stay"` → `HTMLResponse("", 200, headers={"HX-Trigger": '{"worklistRefresh": true, "closeModal": true}'})`; else unchanged hardcoded `HX-Trigger: closeModal` + `HX-Redirect: /tasks`
- `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html` (1 line, ~43)
  - create-mode form `hx-post` now `{% if party_id %}/customers/{{ party_id }}/tasks{% else %}/tasks{% endif %}`
- `crm/src/tests/test_tasks_board_no_party_create.py` (new, 209 lines) — 7 tests, mock-closure pattern mirroring `test_modal_task_return_to.py` (patches `APIRouter` in `screen_tasks_board` module to capture the mock router and recover `handle_create_task` from `router.post.return_value.call_args_list[0]`)

## Tasks Completed
- [x] Step 1: added optional Form params, forwarded into `task_data`
- [x] Step 2: `return_to`-aware response mirroring `screen_modal_task.py:190-192`, combined `worklistRefresh`+`closeModal` per spec
- [x] Step 3: template conditional `hx-post` target
- [x] Step 4: grep confirmed zero pre-existing `hx-post="/tasks"` callers; 2 `hx-get="/tasks/modal/create"` callers found (tasks_board.html:28,86) — expected, unrelated to this fix
- [x] Step 5: flagged pre-existing bug below (not fixed, out of scope)
- [x] Step 6: manual-verify step covered by automated test `test_create_task_no_party_id_succeeds_no_404` (asserts 200, not 404) since this environment has no interactive browser session available to this agent

## Pre-existing bug flagged (not fixed — separate scope)
`GET /tasks/modal/create` (`screen_tasks_board.py:124-129`, `handle_modal_create_task`) renders `fragments/modal_create_task.html`, which does not exist on disk (confirmed via Glob — only `modal_m05_create_task.html` exists in `templates/fragments/`). S07 Tasks Board's own two "+ Tạo task" buttons (`tasks_board.html:28,86`) `hx-get` this route, so clicking them would 500/error on template lookup today. This is unrelated to the worklist-header fix (which targets `/modals/m05` + `/tasks`, not `/tasks/modal/create`) and was out of this phase's scope per the plan. Flagging per step 5 for user decision.

## Tests Status
- Type check: N/A (no typecheck script wired for this Python codebase beyond pytest)
- Unit tests: pass — new file 7/7, full crm suite 1119 passed + 1 skipped (pre-existing skip, unrelated), 0 failed
  - `docker compose exec -T crm pytest crm/src/tests/test_tasks_board_no_party_create.py -v` → 7 passed
  - `docker compose exec -T crm pytest crm/src/tests -q` → 1119 passed, 1 skipped, 55 warnings (pre-existing `TemplateResponse` deprecation warnings, unrelated)
- Integration tests: N/A (no browser/e2e suite touches this route)

## Acceptance Criteria Verification
- [x] Worklist header "+ Tạo task" (no customer) → no 404 — `test_create_task_no_party_id_succeeds_no_404` asserts `status_code in (200, 204)` and `party_id is None` forwarded to `task_creator.create_task`
- [x] `return_to=stay` → no `HX-Redirect`, `HX-Trigger` = `{"worklistRefresh": true, "closeModal": true}` — `test_create_task_return_to_stay_no_redirect`
- [x] `return_to` omitted/default → unchanged `HX-Redirect: /tasks` + `HX-Trigger: {"closeModal":true}` — `test_create_task_return_to_omitted_defaults_to_redirect`
- [x] Party-attached M05 create unaffected — template change is a conditional that resolves to the prior unconditional target when `party_id` truthy; `POST /customers/{party_id}/tasks` handler (`screen_modal_task.py`) untouched
- [x] `priority`/`task_kind`/`source`/`source_ref` forwarded — `test_create_task_forwards_priority_task_kind_source_source_ref` asserts `priority==2` (P1), `task_kind=="internal"`, `source=="action_queue"`, `source_ref=="aq-123"` land in the dict passed to `task_creator.create_task`

## Notes on task_kind resolution (Risk Assessment item)
Per spec, no service-layer change — `TaskService.create_task()` (`task_service.py:96-138`) already derives `task_kind` via `derive_task_kind()` when the caller doesn't supply an explicit non-empty value (line 107-116). The route handler forwards `task_kind` as `None` when blank, so `task_data.get("task_kind") or ""` in the service correctly falls through to derivation. For the worklist-header case (`party_id=None`), `derive_task_kind`'s Rule 1 (`task_kind.py:49-51`) yields `generic, confident=True` — confirmed this is the intended semantic (party-less task = generic), not a regression from M05-with-party's usual `contact` kind.

## Issues Encountered
- Transient false alarm during investigation: an initial `Read` of `crm/src/tests/test_modal_task_return_to.py` returned content inconsistent with a second read of the same file moments later (different test name/assertions on the no-party-id case: `/customers/` vs `/tasks`). Re-read + running the file in the container confirmed the second read (mock-closure with `patch('...APIRouter', side_effect=...)`) is the actual ground truth; adjusted my new test's helper to follow that exact pattern instead of my first (slightly different, functionally equivalent) `mod.APIRouter = MagicMock(...)` approach. No file ownership violation — `screen_modal_task.py` and its test file were read-only references, never edited.
- No live caller of `hx-post="/tasks"` existed before this phase (confirmed via grep), so there was no regression surface to protect beyond the additive Form-param contract itself — matches the red-team correction already noted in the phase file's Overview.

## Next Steps
- User decision needed on the flagged `fragments/modal_create_task.html` missing-template bug (S07 Tasks Board's own "+ Tạo task" buttons) — separate phase/ticket, not blocking this phase.
- No other phases were unblocked by this one (dependencies: none listed in phase frontmatter).

## Unresolved Questions
- None blocking. The missing-template bug (see above) is flagged, not resolved, per explicit phase-file instruction to leave it out of scope.
