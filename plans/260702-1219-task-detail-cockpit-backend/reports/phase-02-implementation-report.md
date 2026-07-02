# Phase 02 — task_kind derivation + M05 backend — Implementation Report

## Status: DONE

## Summary

Pure-function `derive_task_kind` created; wired into all task-creation paths in
`TaskService`; M05 POST accepts optional `task_kind` form field (derives when
absent/invalid); M05 GET passes `task_kind` + `task_kind_confident` to template context.
46 new tests pass; 4 known pre-existing failures unchanged; 0 regressions.

---

## Files Changed

| File | Change |
|---|---|
| `crm/src/application/task_kind.py` | NEW — `derive_task_kind(source, source_ref, party_id, action_type) → (str, bool)` |
| `crm/src/application/task_service.py` | Import `derive_task_kind`; derive in `create_task`, `claim_action_item`, `_process_action`; hardcode `'contact'` in `claim_customer_actions` + `auto_claim_from_contact` |
| `crm/src/adapters/inbound/web/screens/modals/screen_modal_task.py` | Import `derive_task_kind`, `VALID_TASK_KINDS`; GET adds `task_kind`/`task_kind_confident` to context; POST accepts `task_kind: str = Form("")`, resolves and passes to `create_task` |
| `crm/src/tests/test_task_kind.py` | NEW — 31 tests across 4 classes (truth table, service, claim, M05 logic) |

---

## derive_task_kind Rule Table

| Condition | kind | confident |
|---|---|---|
| `party_id` is None/empty | `generic` | True |
| `source == 'verify_account'` | `internal` | True |
| `source_ref` starts with `'verify_account'` | `internal` | True |
| `source in (action_queue, action_queue_claim)` + `action_type == COLLECT_FEEDBACK` | `internal` | True |
| `source in (action_queue, action_queue_claim)` + any outreach action type (or none) | `contact` | True |
| `source == 'manual'` + party present | `contact` | False |
| fallback (unknown source + party present) | `contact` | False |

`confident=False` is the signal for M05 to show the kind selector (template wired in Phase 5/ui-port).

---

## Test Output

```
46 passed in 4.21s   (test_task_kind.py + test_task_kind_migration.py)

Full suite (580 passed, 42 skipped, 4 KNOWN pre-existing failures):
  FAILED test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit
  FAILED test_cache_repository_customer_id.py::test_list_all_action_queue_customer_id_present
  FAILED test_cache_repository_customer_id.py::test_list_all_action_queue_customer_id_none_when_no_base_row
  FAILED test_worklist_filters.py::test_parse_filters_defaults
```

All 4 failures pre-date this work. 0 new failures.

Note: `test_approach_script_handler.py` and `test_web_templating.py` have collection-time
`ModuleNotFoundError: No module named 'fastapi'` — also pre-existing in the system Python
environment (no virtualenv active during pytest run).

---

## Concerns

None.
