# Phase 05 — UI integration via skill `ui-port` (after Claude Design delivers)

## Context
Claude Design returns HTML/CSS for **S14 v2**, **S15**, **M05 task_kind**. Use skill **`ui-port`** ("Port CRM Surface") to extract each into CRM Jinja templates and bind to the Phase 3/4 backend context. ui-spec remains the contract to verify against.

## Preconditions
- Phases 1–4 merged: migration applied, `/tasks/{id}` + `/customers/{id}/call` handlers return full context, inline/lifecycle endpoints live.
- Design artifacts received (per surface).

## Steps (per surface)
1. Place design HTML in the ui-port input location; run `/ui-port` for the surface.
2. Map design regions → context vars (S14: identity/alert/talk_track/reason_to_call primary+secondary/snapshot/collect/outcome; S15: header/lifecycle/body_{contact,internal,generic}/activity_log/close_bar; M05: task_kind selector w/ hide-when-confident).
3. Preserve reuse: `.s14-*`, `.aq-card`, filters, existing inline JS. Enforce INVARIANT (sub-region HTMX only).
4. Wire routing links: S07 card / P04 row / S01 row → `/tasks/{id}`; cockpit entries → `/customers/{id}/call`.
5. Verify against ui-spec (regions/interactions) + `30-states` states render.

## Tests / validation
- Visual check each surface (desktop) + state matrix (contact/internal/generic; STOP; no-actions; collect-done).
- HTMX flows: inline collect swaps row only; outcome resolves multi + task.status; lifecycle transitions; launch cockpit from task returns to S15.
- Narrow template/render tests; then broaden to touched routes.

## Rollback
- Templates are the last layer; revert to stubs to disable UI while keeping backend.
