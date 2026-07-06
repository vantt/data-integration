# Phase 02 — task_kind derivation + M05 backend

## Context
Tasks created via `application/task_service.py` (`create_task`, `claim_customer_actions`) and M05 modal `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py`. `task_kind` must be set at creation (not derived at render).

## Files
- `crm/src/application/task_service.py` — set task_kind on create/claim.
- NEW helper `crm/src/application/task_kind.py` — `derive_task_kind(source, source_ref, party_id, action_type=None) -> str`.
- `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py` — accept `task_kind` form field; derive when absent; pass reveal flag to template.

## Steps
1. `derive_task_kind`:
   - `party_id is None` → `generic`.
   - `source == 'verify_account'` (or other known internal sources) → `internal`.
   - `source in (action_queue, action_queue_claim)` → map `action_type` → outreach types → `contact`; COLLECT_FEEDBACK/review → `internal`; default `contact`.
   - `source == 'manual'` with party → `contact` (best guess; editable).
   - Return + a `confident: bool` (True except ambiguous manual) so M05 can hide/show.
2. `task_service`: on `create_task`/`claim_customer_actions`, compute task_kind (claim = `contact`) and persist. Keep idempotency (source+source_ref) intact.
3. M05 backend: accept optional `task_kind` Form; if empty → `derive_task_kind`; store. Provide `task_kind`, `task_kind_confident` to the modal template context (template hides the selector when confident — Phase 5/ui-port renders it).

## Tests
- Unit `derive_task_kind` truth table (all branches).
- `create_task` from action_queue outreach → contact; from null-party → generic; verify_account → internal.
- M05 POST without task_kind → derived; with explicit → honored.

## Rollback
- Helper is additive; default `'contact'` column default means missing logic degrades safely.
