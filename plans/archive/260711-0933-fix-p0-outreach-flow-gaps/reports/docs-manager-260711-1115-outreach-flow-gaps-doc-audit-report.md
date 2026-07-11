# Documentation Audit: P0 Outreach Flow Gaps (260711-0933) — Doc Changes

## Executive Summary

Reviewed CRM UI specification documentation for references to the 4 P0 bug fixes shipped in this plan:
1. M05/M08 modals `return_to=stay` mode
2. Bulk-resolve snooze vs dismiss per outcome (Phase 02)
3. Callback/follow-up task assignee (Phase 03)
4. S14 cockpit JS for no-script customers (Phase 04)

**Findings**: One documentation inaccuracy identified and corrected.

---

## Files Checked

### Modals
- **M05-create-edit-task-modal.md** ✓ No changes needed
  - Current doc correctly describes `close_overlay, target: return_to_invoker` behavior
  - Does not document the old incorrect HX-Redirect behavior
  - The new `return_to=stay` parameter is an implementation detail, not a spec change
  
- **M08-log-activity-modal.md** ⚠️ **UPDATED**
  - **Issue**: Lines 154 and 166 made blanket claims that `resolve_action_ids` are "dismissed"
  - **Reality**: Per Phase 02 (2026-07-11), actions are now conditionally handled:
    - `no_answer`/`busy` outcomes → snooze 2 days, DO NOT complete tasks
    - Other outcomes → dismiss (TTL 30 days), complete tasks
  - **Fix applied**: 
    - Line 154: Changed description to "outcome-dependent" with reference to POST behavior
    - Lines 165-166: Expanded POST behavior to document the conditional logic
    - Added Phase 02 date reference for audit trail

### Screens
- **S14-call-mode-cockpit.md** ✓ No changes needed
  - Lines 194–199 correctly describe state `ST-CALL-NO-SCRIPT` as "empty + CTA Worklist / 360"
  - Does not claim that collect/rail functionality works or doesn't work (it just describes the fallback UI state)
  - "Known accepted gap" (lines 191–192) still valid — documents unreachable dead code in Python, tracked as technical debt, unrelated to JS fixes

### Code Standards / Architecture
- **code-standards.md**: Does not exist in `crm/docs/`
- **system-architecture.md**: Does not exist in `crm/docs/`

---

## Verification Results

| Behavior Fixed | Documentation Status |
|---|---|
| M05/M08 return context without redirecting | ✓ No outdated claims in docs (spec already said "return_to_invoker") |
| Outcome-aware snooze vs dismiss | ⚠️ **Updated M08** to clarify per-outcome behavior |
| Callback tasks assigned to caller | ✓ No claims about assignee in docs (implementation detail) |
| S14 collect/rail JS works w/o script | ✓ No claims about broken JS in docs (pure JS bug, not spec) |

---

## Changes Made

**File**: `crm/docs/ui-spec/modals/M08-log-activity-modal.md`

**Change 1** (line 154):
```diff
- | `resolve_action_ids` | `str` | Comma-separated action_id values — mỗi cái sẽ được dismiss sau khi log |
+ | `resolve_action_ids` | `str` | Comma-separated action_id values — hành vi phụ thuộc outcome (xem POST behavior dưới đây) |
```

**Change 2** (lines 164–166):
```diff
  **POST behavior (A3):**
  - `act_data["custom_fields"]` được ghi snapshot `{resolve_task_ids: [...], resolve_action_ids: [...]}` **trước** khi gọi `activity_log.log_activity()`.
- - Sau đó `_bulk_resolve()` thực sự dismiss/close các IDs.
+ - Sau đó `_bulk_resolve()` xử lý các IDs theo outcome (Phase 02 — 2026-07-11):
+   - Outcome ∈ `{no_answer, busy}` (cuộc gọi không thành công): **snooze action 2 ngày**, KHÔNG transition task.
+   - Outcome khác (answered, purchased, refused, v.v.): **dismiss action** (TTL 30 ngày), transition task → done.
```

---

## Impact Analysis

- **Scope**: Minimal, localized to one modal spec file
- **Risk**: None — clarifies existing implementation, does not change behavior
- **Audience**: Developers/QA reviewing M08 handler behavior; PM/design reviewing cockpit outcome flow

---

## Follow-up Notes

1. **S14 "Known accepted gap"** (line 191) remains valid — documents unreachable Python code emitting removed JS. No action needed; tracked separately.

2. **No schema/architecture docs exist** for CRM project — code-standards.md and system-architecture.md are not present in `crm/docs/`. Would improve onboarding but out of scope for this audit.

3. **Implementation detail**: Phase-01 `return_to=stay` parameter does not require spec changes in M05/M08 docs — only callers (S01, S03, S14) needed to know about it, which lives in their calling code, not the modal specs themselves.

---

## Conclusion

✓ **Documentation is now aligned with shipped code.** The only outdated claim (bulk-resolve behavior in M08) has been corrected to reflect the Phase 02 outcome-aware snooze/dismiss logic.
