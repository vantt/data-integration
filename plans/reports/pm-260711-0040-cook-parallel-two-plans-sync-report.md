# PM sync — /ck:cook --auto --parallel, 2 plans

2026-07-11. Cooked remaining phases of 2 plans in parallel (file-disjoint, verified safe). Full sync-back done across ALL phase files in both dirs, not just touched ones.

## `plans/260710-1338-activity-log-disposition-api/`

| Phase | Status |
|---|---|
| 1 (M08 lightening) | ✅ DONE 2026-07-10, pre-existing |
| 2 (draft/PATCH/finalize API) | ✅ DONE 2026-07-10, pre-existing |
| 3 (Disposition Strip v2) | ✅ DONE 2026-07-11 — cooked this session |

Phase 3 cooked → code review found 2 blocking bugs (refused-outcome PATCH always 422/409; silent PATCH error swallowing) → fixed → re-review found the fix itself dropped server-side validation for M08-edit-on-final-row → fixed → re-verified. 3 review rounds total. Full suite 1052 passed/1 skipped/0 failed.

All acceptance criteria `[x]`. No open items left in this plan beyond its one pre-existing open question (save-as-note/insight usage — data-driven decision in 2 weeks, not blocking).

## `plans/260709-1638-crm-outreach-effort-report/`

| Phase | Status |
|---|---|
| 0 (mart extend, Track A) | ✅ DONE 2026-07-10, pre-existing |
| 1 (schema fix, Track B) | ✅ DONE 2026-07-10, pre-existing |
| 2 (intermediate model) | ✅ DONE 2026-07-11 — cooked this session |
| 3 (weekly mart) | ✅ DONE 2026-07-11 — cooked this session |
| 4 Track A (dashboard) | ✅ DONE 2026-07-10, pre-existing (id 147, live) |
| 4 Track B (dashboard card) | pending — needs weeks of post-cutover data first |

Phase 2 cooked → code review clean (SQL logic sound) but found `staff_user_id` bug (sourced from wrong table) not caught by the implementing agent → fixed at the root (intermediate model), simplified Phase 3's redundant workaround join (DRY) → re-verified, both models + 6 dbt tests green.

**2 gaps found during sync-back that no phase in this plan owns** (flagged, not fixed — out of session scope):
1. `zalo_connected_count` — UI + export ready, never landed as a mart column. Blocks the Sprint's "Zalo connect ≥50%" KPI from showing on the dashboard.
2. `crm_party_tag.source_activity_id` — write-path ready since Phase 1, but no CRM form actually sends it. Column stays NULL forever until wired.

Both added to plan.md's open-questions list (#7, #8) with the "why" and a pointer to the phase-01 report section that already scoped the 2 candidate approaches for #2.

## Files touched this session (beyond plan/report docs)

- `transformation/models/marts/core/intermediate/int_crm_outreach_effort_events.sql` + `.yml` (new + 1 root-cause fix)
- `transformation/models/marts/crm/mart_crm_outreach_effort_by_action_weekly.sql` + `schema.yml` entry (new + doc-drift fix)
- `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (new disposition strip + bugfix)
- `crm/src/adapters/inbound/web/static/ds-extra.css`, `layout.html` (cache-bust bump)
- `crm/src/application/activity_service.py` (new disposition strip API wiring + 2-round validation bugfix)
- `crm/src/adapters/inbound/web/screens/customer360/screen_call_cockpit.py`, `screen_customer_360_panels.py`, `screen_customer_360.py`
- `crm/docs/ui-spec/screens/S14-call-mode-cockpit.md` + generated ui-spec artifacts
- `crm/src/tests/test_disposition_strip_v2.py` (new), `test_activity_draft_lifecycle.py` (+6 tests total across 2 fix rounds)

## Docs (`./docs`)

No `./docs/*.md` update triggered — both plans extend already-documented systems (CRM activity-log API pattern from a prior phase; new dbt mart follows the existing mart-authoring convention) with no new architecture, setup, or public-contract change. `crm/docs/ui-spec/` was auto-updated by the ui-spec skill as part of Phase 3 (in-scope, not a separate ./docs trigger).

## Unresolved questions
1. Who owns adding `zalo_connected_count` to `mart_staff_performance_weekly` — Track A extension (retroactive Phase 0 scope) or a new mini-phase?
2. Who owns wiring `source_activity_id` into the CRM tag-attach UI — this plan (data/mart side already built for it) or the CRM UI plan?
