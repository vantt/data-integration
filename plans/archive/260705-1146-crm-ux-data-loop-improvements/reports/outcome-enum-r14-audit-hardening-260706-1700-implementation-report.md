# Outcome-enum + R14 audit hardening — implementation report

Scope: AI-1, AI-3, AI-4, AI-7 from `phase-08-reassessment-fixes.md`.

## AI-1 — async-resolve writes `contact_outcome`, not free-text

File: `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:341-354` (`handle_resolve_async`).

- Replaced `"outcome": "async_sent"` with `"contact_outcome": "pending_reply"` in `act_data`.
- `channel_type` was already set to the raw `ch` value (`"zalo"`/`"email"`) a few lines above — this already maps to `CONTACT_OUTCOMES_BY_CHANNEL_TYPE["zalo"/"email"] = CONTACT_OUTCOMES_MESSAGING`, which contains `pending_reply` (`crm/src/domain/entities/activity.py:40-53`). Validation in `activity_service.log_activity` (`crm/src/application/activity_service.py:53-67`) passes without any further change.
- If `channel` is some other unexpected value, `CONTACT_OUTCOMES_BY_CHANNEL_TYPE.get(channel_type, VALID_CONTACT_OUTCOMES)` falls back to the merged enum, which also contains `pending_reply` — so validation can't fail either way.
- Legacy read path untouched: `task_detail.html:22` still maps `'async_sent': 'Đã gửi'` for old rows. No backfill performed (per instructions).
- Note (pre-existing, not introduced by this change): `task_detail.html:449` renders `entry.outcome`, not `entry.contact_outcome` — this display gap already existed for every `contact_outcome`-writing path since D2 Phase 03 (the main `handle_log_activity` route has written `contact_outcome` primarily since then), so async-resolve rows will show `—` in that specific timeline location, same as other contact_outcome-only rows. Out of scope for this task (file not in my edit list); flagging for a follow-up.

## AI-3 — r14-ack records `script_id`

Files:
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (banner, ~line 282-301)
- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py:370-401` (`handle_r14_ack`)

**Finding:** there is no distinct `script_id` field anywhere in the approach-script data model — the script file is keyed by `customer_id` (`{customer_id}.json`), the `ApproachScript` entity has no `script_id`, and the generator's `meta` block (`scripts/generate_approach_scripts.py:build_meta`) has no id, only `model`/`template_version`/`generated_at`. The template context (`script`, `meta`) also carries no `customer_id`.

Given the constraint to only touch `screen_customer_360_activity.py` + this template (not `screen_call_cockpit.py` / `screen_customer_360_panels.py`, which would be needed to thread a real customer_id through), the best available proxy for "which script version was overridden" is `refreshed_at` — already computed in the template as the script's freshness stamp (used in the trust footer) and functionally a de-facto version marker (file mtime). Documented this rationale inline in the template.

- Added hidden input `<input type="hidden" id="s14-r14-script-id-val" name="script_id" value="{{ refreshed_at or '' }}">` next to the existing `reason_shown` hidden input.
- Extended `hx-include` on `#s14-r14-ack-btn` to `"#s14-r14-reason-val, #s14-r14-script-id-val"`.
- Handler now reads `form.get("script_id", "")` and writes it into `custom_fields["script_id"]` (truncated to 200 chars, same pattern as `reason_shown`), alongside `r14_ack` and `reason_shown`, matching the D4 registry (`ux-action-queue-task-cockpit-data-loop-design.md` §6-D4).

**Unresolved question:** if a real per-generation script identifier is ever added to the JSON schema, `script_id` should be repointed from `refreshed_at` to that field — flagging for the controller/product owner since this is a known proxy, not the ideal value.

## AI-4 — R14 unlock only fires on successful audit POST

File: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`

- Changed `hx-on::after-request="s14UnlockR14()"` to `hx-on::after-request="if(event.detail.successful){s14UnlockR14();}else{s14R14AckError();}"` on `#s14-r14-ack-btn`.
- Added a hidden inline error span `#s14-r14-ack-err` next to the button (`display:none` by default).
- Added `window.s14R14AckError` next to `window.s14UnlockR14` (both defined inside the existing `{% if is_stop %}` script block) — shows the error span; banner stays locked (no changes to `s14UnlockR14` itself, so failure path never removes `s14-locked` / hides the banner).

## AI-7 — new tests for phase 04/05 behaviors

New file: `crm/src/tests/test_claim_context_snooze_r14.py` (self-contained, 15 tests, all read-only against the target production files):

- **(a)** `TestClaimCustomerActionsDenormalization` — exercises the real `TaskService.claim_customer_actions` (`crm/src/application/task_service.py:180-232`, untouched): sum of `value_at_stake_vnd` across actions, `top_affinity_product` sourced from the highest-value action, zero-sum → `None` (not `0`), and idempotent re-claim returns the existing task.
- **(b)** `TestSnoozeEndpoint` — drives `PATCH /tasks/{id}/snooze` (`crm/src/adapters/inbound/web/screen_worklist.py:370-398`, untouched) via a real `FastAPI`/`TestClient` app wired with `make_worklist_router` + mocked `tasks`/`task_writer`: clamp `days=999` and `days=0`/`-5` to the same `due_at` as `days=30`/`days=1` respectively, `doing`→`open` transition fires, `open` task doesn't transition.
- **(c)** `TestQueuePosAutoCorrection` — drives `GET /customers/{party_id}/call` (`crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py:140-145`, untouched) with a real Jinja render (same pattern as `test_task_detail_and_cockpit.py`): wrong caller-supplied `queue_pos` is corrected to the party's real index (`#2/3`, next-link `queue_pos=2`), position is left alone when party isn't in the queue list, and the queue counter is fully absent with no queue context.
- **(d)** `TestR14AckScriptId` + `TestR14UnlockGuardedOnSuccess` — exercises the new `handle_r14_ack` script_id write end-to-end (mocked `activity_log`, real form dict via `AsyncMock`), and asserts (string-contains) that the template source contains `event.detail.successful`, `s14R14AckError`, the `script_id` hidden input, and its `hx-include` wiring — JS execution itself isn't unit-testable in pytest, per the task's own caveat.

## Test results

```
docker compose exec -T crm sh -c "cd /app/crm && python -m pytest \
  src/tests/test_bulk_resolve_endpoint.py \
  src/tests/test_outcome_reason_enum.py \
  src/tests/test_task_detail_and_cockpit.py \
  src/tests/test_claim_context_snooze_r14.py -q"
```
→ **77 passed**, 0 failed (20 pre-existing `DeprecationWarning`s from Starlette's `TemplateResponse` positional-arg signature, unrelated to this change).

`docker compose restart crm` run successfully after changes.

## Files touched

- `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_activity.py`
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html`
- `crm/src/tests/test_claim_context_snooze_r14.py` (new)

## Unresolved questions

1. `script_id` currently = `refreshed_at` (script freshness stamp) because no true per-script id exists in the data model. If a real id is added later, repoint the hidden input's `value` and the handler stays unchanged (still just forwards whatever `script_id` form value it receives).
2. Pre-existing display gap: `task_detail.html:449` timeline renders `entry.outcome` only, not `entry.contact_outcome` — affects all `contact_outcome`-only rows (not just this task's async-resolve change). Not fixed here (file out of scope); worth a follow-up item.
