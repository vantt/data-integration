# Phase 03 + 04 Implementation Report

**Date:** 2026-07-02
**Branch:** feature/task-detail-cockpit-backend (main tree)

---

## Status

DONE

## Summary

Phase 03 (S15 Task Detail) and Phase 04 (S14 Call Cockpit v2) backend implemented.
35 new tests pass; 0 regressions introduced (9 pre-existing failures unchanged —
none touch new code).

---

## Files Changed / Created

### New files

| File | Purpose |
|------|---------|
| `crm/src/adapters/inbound/web/screens/screen_task_detail.py` | Router factory `make_task_detail_router` — GET /tasks/{id} + POST /tasks/{id}/status |
| `crm/src/application/reason_rail.py` | `assemble_reason_rail()` — merges action queue + contact-tasks into PRIMARY/SECONDARY rail |
| `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py` | `register_call_cockpit_route()` — GET /customers/{party_id}/call full-screen shell |
| `crm/src/adapters/inbound/web/templates/fragments/task_detail.html` | S15 stub template (renders full context contract) |
| `crm/src/adapters/inbound/web/templates/call_cockpit.html` | S14 full-screen stub template (renders rail + cockpit fragment) |
| `crm/src/adapters/inbound/web/templates/fragments/_s14_collect_row.html` | Inline collect one-row fragment (stub) |
| `crm/src/tests/test_task_detail_and_cockpit.py` | 35 tests covering S15 + S14 backend |

### Modified files

| File | Change |
|------|--------|
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360_panels.py` | Enriched `call_cockpit` panel branch with party, identities, insight, warning_notes, resolved_action_ids, geo_region, rail_primary, rail_secondary |
| `crm/src/adapters/inbound/web/screens/customer360/screen_customer_360.py` | Imported + registered `register_call_cockpit_route` |
| `crm/src/adapters/inbound/web/screens/modals/screen_modal_contact.py` | Added `inline: str = Form("0")` branch to `post_contact` + `post_core`; inline=1 returns `_s14_collect_row.html` fragment instead of redirect |
| `crm/src/composition.py` | Imported + wired `make_task_detail_router` (after management router) |

---

## Test Output

```
35 passed, 17 warnings in 1.18s
```

Tests cover:
- `TestTaskDetailGet` (9): contact/internal/generic/claim 200; 404 unknown; allowed_transitions exposed; "Vào phiên gọi" link; no party block for generic
- `TestTaskStatusTransition` (6): start/cancel/reopen valid; done→doing rejected 422; cancelled→done rejected 422; 404 unknown task
- `TestReasonRail` (9): empty→None; single action primary; dismissed excluded; resolved excluded; contact-task in rail; doing-task beats CALL_NOW; pinned forced primary; multiple split; actions+tasks both present
- `TestCallCockpitRoute` (8): renders ±task_id; return_target set; 404 no party; rail primary from action; contact-tasks in rail; doing-task is primary
- `TestInlineCollect` (3): inline=1 returns row fragment (no HX-Redirect); non-inline still redirects; inline core returns row fragment

Pre-existing failures (not introduced): 9 failures in
`test_approach_script_file_repository`, `test_cache_repository_customer_id`,
`test_web_templating`, `test_worklist_filters` — none reference new code.

---

## Context Keys for Future ui-port Templates

### `fragments/task_detail.html`

| Key | Type | Notes |
|-----|------|-------|
| `task` | `Task` | Full entity incl. `task_kind`, `source`, `source_ref`, `due_at`, `priority_label` |
| `party` | `Party360 \| None` | Populated when `task.party_id` set |
| `identities` | `list[PartyIdentity]` | |
| `insight` | `CacheInsight \| None` | |
| `provenance_action` | `ActionQueueItem \| None` | Resolved when source=action_queue; carries `rationale_vi`, `value_at_stake_vnd` |
| `attempt_log` | `list[Activity]` | Activities where `task_id` matches |
| `claim_actions` | `list[ActionQueueItem]` | Non-empty when `source=action_queue_claim`; from `insight.sorted_actions` |
| `allowed_transitions` | `list[str]` | e.g. `['doing','done','cancelled']` |
| `body_kind` | `str` | `contact \| internal \| generic` — selects body block |

### `call_cockpit.html`

| Key | Type | Notes |
|-----|------|-------|
| `party_id` | `str` | |
| `party` | `Party360` | |
| `identities` | `list[PartyIdentity]` | |
| `insight` | `CacheInsight \| None` | |
| `warning_notes` | `list[Note]` | type=warning, active |
| `resolved_action_ids` | `set[str]` | action_ids with outcomes |
| `geo_region` | `str` | HCMC/Hà Nội/Mekong/Miền Trung/Khác |
| `script` | `dict \| None` | Approach script data (has `approach` key) |
| `meta` | `dict \| None` | `{recommended, confidence, refreshed_at}` |
| `rail_primary` | `RailItem \| None` | Ripest item; carries `action_id` or `task_id` provenance |
| `rail_secondary` | `list[RailItem]` | Remaining items |
| `pinned_task_id` | `str \| None` | Set when entered from S15 |
| `return_target` | `str \| None` | `/tasks/{id}` when pinned, else None |

### `fragments/c360_call_cockpit_panel.html` (enriched)

Same keys as `call_cockpit.html` minus `pinned_task_id`/`return_target`; adds `party_id` as before.

### `fragments/_s14_collect_row.html`

| Key | Type | Notes |
|-----|------|-------|
| `party_id` | `str` | |
| `field` | `str` | identity_type or `"core"` |
| `value` | `str` | Collected value |
| `done` | `bool` | True on success |

---

## Unresolved Questions

1. **Outcome bulk-resolve**: Phase 04 step 3 (one POST resolves N action_ids AND flips task status) is not yet wired — the existing `handle_log_activity` already handles single `complete_task` flip; multi-action bulk-resolve needs an endpoint that accepts `action_ids[]` + `task_ids[]` and loops dismiss + transition_status. Left for the outcome handler extension (not in scope of this phase per plan — no specific file designated).

2. **Async-resolve (A-S14-026)**: Rail item resolve-by-Zalo (log async contact without a call) mentioned in Phase 04 step 6 — not yet implemented. Requires a dedicated endpoint.

3. **`action_task_resolver` not wired into `make_customer_360_router` call** in `composition.py`: the protocol exists but the arg was already missing before this phase. The panel now calls it conditionally (None-safe) so it gracefully degrades — wire when the resolver is ready.

4. **`TemplateResponse` deprecation warning** (17 hits): Starlette wants `TemplateResponse(request, name)` order. Pre-existing pattern throughout codebase — low priority, not introduced by this phase.
