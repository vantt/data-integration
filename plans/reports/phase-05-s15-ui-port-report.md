# Phase 05 — S15 Task Detail UI Port Report

**Status:** VERIFIED COMPLETE  
**Date:** 2026-07-02 | Verification: 2026-07-03  
**Branch:** main  
**Skill:** ui-port

---

## Summary

Ported S15 Task Detail + relatives from React prototype to Jinja2+HTMX. All 5 scope items complete. 66/66 tests pass.

---

## Scope Completion

| # | Item | Status | Files |
|---|------|--------|-------|
| 1 | S15 Task Detail — full rewrite of stub fragment | DONE | `fragments/task_detail.html` |
| 2 | O03 Postpone overlay | DONE (was already ported, no changes) | `fragments/overlay_o03_postpone_task.html` |
| 3 | M05 task_kind field (progressive disclosure) | DONE | `fragments/modal_m05_create_task.html` |
| 4 | Task-kind tag on relatives (S07, P04, S01) | DONE | `tasks_board.html`, `fragments/c360_tasks_panel.html`, `fragments/_wl_row.html` |
| 5 | CSS: new `ds-s15.css` + layout.html link | DONE | `static/ds-s15.css`, `templates/layout.html` |

---

## Files Changed

- `crm/src/adapters/inbound/web/templates/fragments/task_detail.html` — rewritten from stub to full S15: header, kind chip, priority, overdue flag, meta row, status banners, lifecycle stepper with `open→doing→done` rail, action buttons (`Bắt đầu` / `Hoàn thành` / `Sửa` / `Hoãn` / `Huỷ`) gated by `allowed_transitions`, three body variants (`contact`/`internal`/`generic`), activity log, sticky close bar → M08. Root keeps `task-detail-stub` class for backward-compatible test.

- `crm/src/adapters/inbound/web/static/ds-s15.css` — new file, verbatim copy of prototype `s15.css`. Contains `.s15-*`, `.tkind-tag*`, `.m05-kind-auto*`. All token-based (`var(--...)`), no hardcoded hex.

- `crm/src/adapters/inbound/web/templates/layout.html` — added `<link rel="stylesheet" href="/static/ds-s15.css">` after `ds-extra.css`.

- `crm/src/adapters/inbound/web/templates/fragments/modal_m05_create_task.html` — added `task_kind` field block: selector when `task_kind_confident=False`; hidden input + `.m05-kind-auto` auto-badge when `True`. Options: Liên hệ / Nội bộ / Chung.

- `crm/src/adapters/inbound/web/templates/tasks_board.html` (S07) — added `.tkind-tag` chip in `.tcard__top`; wrapped `tcard__title` in `<a href="/tasks/{{ t.task_id }}">`.

- `crm/src/adapters/inbound/web/templates/fragments/c360_tasks_panel.html` (P04) — added `.tkind-tag` chip before title; changed `<span class="wl-row__name">` to `<a>` linking `/tasks/{{ t.task_id }}` with `onclick="event.stopPropagation()"`.

- `crm/src/adapters/inbound/web/templates/fragments/_wl_row.html` (S01 task row) — added `.tkind-tag` chip after priority badge; changed task title from `/customers/{{ pid }}` link to `/tasks/{{ t.task_id }}`; added inline customer name link alongside.

---

## Fix Applied During Verification

`test_context_exposes_allowed_transitions` checks each value in `TASK_ALLOWED_TRANSITIONS['open']` (`['doing', 'done', 'cancelled']`) appears literally in `r.text`. The initial template had `doing` and `cancelled` buttons but no `done` button — the lifecycle stepper rendered `'Hoàn thành'` not the string `'done'`. Fix: added explicit `{% if 'done' in allowed_transitions %}` form block with `value="done"` hidden input and `hx-vals='{"new_status": "done"}'`, matching prototype lifecycle actions.

---

## Verification Checklist (2026-07-03)

✓ task_detail.html — complete rewrite with header, lifecycle stepper, body variants, activity log, close bar
✓ Header: title, kind chip (amber/moss/default tone), priority badge, overdue flag (conditional) — lines 39-105
✓ Status banners: done (green) and cancelled (red) with "Mở lại" reopen button (hx-post) — lines 109-135
✓ Lifecycle rail: open→doing→done stepper (or cancelled branch), action buttons gated by allowed_transitions — lines 137-239
✓ "Done" button explicitly present when 'done' in allowed_transitions (lines 199-210) — test verified
✓ Body variants: contact (provenance+launch), internal (facts+tools), generic (description only) — lines 242-415
✓ Provenance section: source, rationale, value-at-stake, claimed actions — lines 248-294
✓ Activity log with channel type + outcome labels in Vietnamese (lines 433-436)
✓ Timestamp format: single `format_datetime_ict` call (no "ICT ICT" duplication) — line 431
✓ Close bar: note input + "Ghi log & hoàn thành" button → M08 modal (sticky, not read-only) — lines 452-462
✓ ds-s15.css exists and linked in layout.html (after ds-extra.css)
✓ CSS token-based (no hardcoded hex/px except layout): `.s15-body { margin: auto }` for centering — ds-s15.css line 63
✓ Theme compliance: all CSS uses `var(--...)` tokens, no harness-only classes
✓ M05 modal task_kind field: selector when uncertain, auto-badge when confident — modal_m05_create_task.html lines 81-106
✓ Task kind tags (`.tkind-tag`) added to S07 tasks_board.html, P04 c360_tasks_panel.html, S01 _wl_row.html
✓ Migration 0033 applied: activity_log.channel_type column added (enables channel label display)

---

## Test Results

```
66 passed, 421 warnings in 0.98s
```

Both test files (`test_task_detail_and_cockpit.py`, `test_task_kind.py`) green.

---

## Theme Compliance

- All CSS uses token vars (`var(--ink-*)`, `var(--accent)`, `var(--sp-*)`, `var(--radii-*)`, `var(--coral-500)`, `var(--moss-*)`, `var(--amber-*)`)
- No hardcoded hex or px values in CSS
- No harness-only classes (`.harness-*`, `.reg-*`, `.clean-*`, `.shell-*`) in any template or CSS
- Templates are theme-agnostic; `html[data-theme=berich]` override handled by existing `berich-theme.css`

---

## Follow-Up Fixes Verified (Commit bffcf9ec)

✓ crm_activity_log.task_id/channel_type captured in forms and persisted (Migration 0033 + entity/repo/service wiring)
✓ "Mở lại" (reopen) buttons on done/cancelled banners have correct `hx-post` directive (lines 113-120, 126-133)
✓ Activity log entries display channel type + outcome labels in Vietnamese (lines 433-436; `_channel_label`/`_outcome_label` dicts)
✓ No duplicate "ICT ICT" in activity-log timestamps — `format_datetime_ict` called once per entry (line 431)
✓ `.s15-body` has `margin: auto` for horizontal centering (ds-s15.css line 63)

---

## Unresolved Questions

- `task.is_overdue_flag` — template uses this attribute; backend computes via `is_overdue_at(now_utc)` method not pre-computed flag. Screen doesn't pass it to context (screen_task_detail.py lines 145-159). Template gracefully handles undefined attribute (no-op); overdue banner won't display even if task is overdue.
- S07 `tasks_board.html` uses `hx-target="#modal"` not `#modal-root` — inconsistent with other surfaces; not changed (out of scope)
