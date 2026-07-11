---
phase: 2
title: "Resolve-Outcome Gating"
status: superseded
priority: P0
dependencies: []
---

# Phase 2: Resolve-Outcome Gating

> **SUPERSEDED (2026-07-11)** — a parallel plan, `plans/260711-0933-fix-p0-outreach-flow-gaps/phase-02-outcome-aware-resolve.md`, covers this exact finding with a functionally identical design (same `_NO_CONTACT_OUTCOMES`/snooze approach). Treat that file as canonical/executable for this fix — it also carries a red-team amendment (the `/reason/resolve-async` + "+Nhắn Zalo" bypass, Critical) ported over from this plan's review. This file is kept for its research/evidence trail only; do not implement from here.

## Overview

Finding #2 (report §II.2). `execute_side_effects` step 7 (bulk-resolve) dismisses actions / marks tasks done whenever `resolve_action_ids`/`resolve_task_ids` are non-empty — regardless of `contact_outcome`. A failed call (`no_answer`/`busy`) currently burns the signal: the action vanishes from the queue for 30 days (`crm_action_dismissal` TTL) and the pinned task is marked done, with no retry mechanism.

**Policy decision (locked with user, report §"User decisions" #1)**: for `contact_outcome in ("no_answer", "busy")`, do NOT dismiss/complete — auto-snooze instead (1-3 days). All other outcomes (`answered`, `purchased`, `refused`, `wrong_number`, etc.) keep today's resolve/dismiss behavior unchanged.

This is a single-point fix: `execute_side_effects()` already receives the full `activity` object (which carries `contact_outcome`) and is the sole executor for both the legacy M08 POST and the new finalize API (its own docstring calls this the "một đường ghi duy nhất" invariant) — so the gate goes in exactly one place, not duplicated per caller.

Reuses existing snooze primitives instead of inventing new write paths:
- `action_state.snooze(action_id, until_date, user_id)` (`action_state_repository.py:158-169`) — already used by the manual ⏰ snooze button (`screen_worklist.py:542-551`, `handle_snooze_action`). Sets `crm_action_state.status='snoozed'` + `snoozed_until`; critically does **not** touch `crm_action_dismissal` (that table is only written by `dismiss()`), so the 30-day cross-episode TTL is never triggered.
- Task due-date push mirrors `handle_snooze_task` (`screen_worklist.py:408-434`) — `task_svc.update_task(task_id, {"due_at": ...})`, ICT-anchored, and resets `status` back to `open` if it was `doing` (do NOT call `transition_status(tid, "done")` for these ids).

## Requirements

- `contact_outcome in {"no_answer", "busy"}` at finalize time → resolve_action_ids get `action_state.snooze(...)` instead of `action_state.dismiss(...)`; remaining_task_ids get a due-date push + stay `open` instead of `transition_status(tid, "done")`.
- Snooze window: 1-3 days (report's suggested range) — pick a single fixed value (e.g. 2 days) for v1; do not add a user-facing day picker (out of scope, no UI hook requested).
- All other `contact_outcome` values (including empty/None — e.g. save-as-note-only submissions with no outcome) → unchanged existing dismiss/done behavior.
- `complete_task_ids` (step 6, explicit task completion via checkbox) is untouched — this gating applies ONLY to step 7's bulk-resolve (`resolve_action_ids`/`resolve_task_ids`), which is the implicit "outcome bar resolved this too" path the report is about.

## Related Code Files

- Modify: `crm/src/application/activity_side_effects.py` (step 7, lines 164-183; add `timedelta` to the existing `from datetime import datetime, timezone` import)
- Reference only (no change): `crm/src/adapters/outbound/sqlite/action_state_repository.py:158-169` (`snooze()`), `crm/src/adapters/inbound/web/screen_worklist.py:408-434` (`handle_snooze_task`, ICT due-date math to mirror), `crm/src/domain/entities/activity.py:37-39` (`CONTACT_OUTCOMES_CALL` — confirms `"no_answer"`/`"busy"` are the exact string constants)
- Check at implementation time: does `task_svc` (as passed into `execute_side_effects`) expose `update_task(task_id, data)` — confirmed yes, it's part of the `TaskWriter`-shaped interface already used elsewhere in this same file (step 6 uses `task_svc.transition_status`; `update_task` is the sibling method per `task_service.py:144`).

## Implementation Steps

1. Add `timedelta` to `activity_side_effects.py`'s datetime import.
2. In step 7 (lines 164-183), read `outcome = getattr(activity, "contact_outcome", None)` and define a module-level constant `_NO_CONTACT_OUTCOMES = {"no_answer", "busy"}` and `_AUTO_SNOOZE_DAYS = 2` near the top of the file (alongside existing module-level helpers).
3. Branch inside the `if resolve_action_ids or remaining_task_ids:` block:
   - If `outcome in _NO_CONTACT_OUTCOMES`: compute `until_date` the same way `handle_snooze_action` does (`(datetime.now(timezone.utc) + timedelta(days=_AUTO_SNOOZE_DAYS)).strftime("%Y-%m-%d")`), call `action_state.snooze(aid, until_date, user_id=uid)` for each `resolve_action_ids`, and for each `remaining_task_ids` call `task_svc.update_task(tid, {"due_at": <ICT-anchored UTC ISO string for until_date>})` — mirror `handle_snooze_task`'s ICT math (`screen_worklist.py:416-424`) rather than reusing the action's plain `YYYY-MM-DD` format, since tasks store a full timestamp. Do not call `transition_status`.
   - Else: existing `dismiss`/`transition_status(tid, "done")` logic, unchanged.
4. Keep the existing per-item try/except-log isolation (never let one bad id abort the loop) — same shape for both branches.
5. Do not touch step 6 (`complete_task_ids` → `transition_status(tid, "done")`), and do not touch `_dismiss_by_party_and_type`/`crm_action_dismissal` at all — the fix is entirely about which of `snooze`/`dismiss` gets called, no schema change.

## Success Criteria

- [ ] Finalize a call with outcome `no_answer` and a pinned resolve action → action status becomes `snoozed` (not `dismissed`), `crm_action_dismissal` gets no new/updated row for that (party_id, action_type), action reappears in the queue after `snoozed_until` passes.
- [ ] Finalize with outcome `busy` + a resolve task → task stays `status=open` with `due_at` pushed ~2 days out, not `done`.
- [ ] Finalize with outcome `answered`/`purchased`/`refused`/`wrong_number` + resolve ids → unchanged: dismiss + done, exactly as before (regression-covered by existing tests).
- [ ] Finalize with no outcome at all (empty string / None) + resolve ids → unchanged existing behavior (falls to the `else` branch, matches pre-fix behavior for that case).
- [ ] New tests: `no_answer`/`busy` → snooze path (action_state.snooze called, not dismiss; task_svc.update_task called, not transition_status); existing bulk-resolve tests (`test_bulk_resolve_endpoint.py`) still green.

## Risk Assessment

- **Risk**: task due-date ICT math duplicated between `screen_worklist.py` and `activity_side_effects.py` (application layer can't import the web-adapter helper — clean-arch boundary). Acceptable duplication (same pattern already accepted elsewhere per `task_service.py`'s own comment about not importing from `adapters/inbound/web`); keep both in sync manually if the ICT offset ever changes.
- **Risk**: fixed 2-day snooze may feel wrong for some flows (e.g. VIP escalation wanting 1 day). No UI to adjust it in v1 — acceptable per user's locked decision (range given as "1-3 ngày", a single value is in-range; revisit only if user asks for a picker later).
- **Rollback**: single-file, single-function change; revert step 7 to the pre-fix unconditional dismiss/done block.
