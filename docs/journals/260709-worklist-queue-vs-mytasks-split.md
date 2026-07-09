# Worklist Split: UUID Leak + Design Contradiction

**Date**: 2026-07-09 14:45
**Severity**: High
**Component**: CRM Worklist (S01), `worklist_ranking.py`, `_wl_row.html`
**Status**: Resolved

## What Happened

User flagged a row in the worklist that literally read "Gọi Khách lẻ · 12 hành động · bf9904af-c395-47c9-a932-fd8f9c053fb1" — a raw customer party_id UUID bleeding through instead of the customer name. At the same time, deeper confusion: were these rows "tasks" that needed execution, or "action-queue opportunities" that needed a decision to claim first? Both types lived in the same urgency bands (Khẩn, Trong hạn), and the UI didn't distinguish them.

## The Brutal Truth

The UUID leak is infuriating because it's a repeat. I dug back and found that exact category of bug (raw party_id leaking into UI text) had already been fixed 7 times across other surfaces in the codebase (commit 35072659 is one example). This one got missed because it's *hidden in a template field-name typo* — `_wl_row.html` was reading `customer_name` on a Task object that only has `party_name`. Jinja just silently renders Undefined as empty, then falls back to the raw party_id in the row data. No error, no warning, no way to catch it without reading the template carefully.

The deeper frustration: the codebase *already had the right pattern* in place, half-applied. Unassigned manual tasks got their own "Hàng Đợi Chung" queue section outside the urgency bands — exactly what action-queue items needed. But action-queue items were just thrown into bands 0-4 alongside claimed tasks, creating the exact confusion the user complained about. This wasn't a design gap; it was an inconsistency that got missed during the original architecture decision.

## Technical Details

**Hash leak root cause:**
- Template line: `{{ a.customer_name }}` on a Task entity
- Task only has: `party_name` (correctly joined, never a data issue)
- Jinja 2 renders undefined attribute as blank, template falls back to rendering `a` directly (the full row dict), which Python-stringifies to the party_id
- Fix: 1 character change in the template

**Design contradiction root cause:**
- `rank_worklist()` outputs 5 bands (0-4 urgency, band 4 = "recently contacted")
- Both unclaimed action-queue items AND claimed task rows fed into bands 0-4
- Existing code already had "Hàng Đợi Chung" (unassigned manual tasks) as a separate queue section pre-band rendering
- Action-queue items weren't getting the same treatment — they landed in the band loop indiscriminately
- This wasn't two separate features; it was one pattern applied half-way

## What We Tried

**First pass (phase 02 implementation):**
- Added `split_worklist_view()` pure function to regroup `rank_worklist()` output by kind (`kind == 'action'` vs `kind == 'task'`)
- Wired it into the screen adapter and template
- Both queue sections reused the existing `_wl_bands.html` partial to render their sub-sections with the same urgency-band metadata

**Code review gate (mandatory, before commit):**
- Caught a real bug the phase-02 file had *explicitly flagged as a required check* but the implementation still missed anyway
- The `/worklist/band/{id}/more` overflow route always re-ranks actions-only input (correct for the action queue)
- But band IDs 1 and 2 now exist in BOTH `queue_action_bands` AND `my_task_bands`
- Result: lazy "Xem thêm" from a task band would have fetched action rows, undoing the split entirely
- **Fix**: Changed `my_task_bands` to render eager/uncapped (`show_overflow=false` flag added to `_wl_bands.html`) instead of sharing the lazy-load route. Action queue keeps the lazy behavior since its route was already correct.

## Root Cause Analysis

**UUID leak:** Template variable typo, same category as 7 prior bugs. Pattern: no automated check catches Jinja undefined-attribute fallback (falls through to object repr). No type checking on template context at runtime.

**Design contradiction:** The architecture *had the answer already* in the codebase (queue section pattern), but it was only applied to one kind of queue item (manual unassigned tasks), not generalized to all unclaimed work. The original implementation of the band system mixed everything together, then one surface (unassigned tasks) got the exception treatment, and no one updated action-queue to match. It took user feedback to surface the inconsistency.

**Process lesson from phase 02:** Code review found a bug the plan file **explicitly warned about** ("check `handle_worklist_band_more`"). The first implementation pass didn't actively verify that check — it got skipped in the press of implementation. The mandatory code review forced the verification. This is a reminder: explicit pre-implementation checklists don't auto-verify themselves; they need an explicit checkpoint (code review, test annotation, or a pre-commit hook) or they get treated as optional context.

## Lessons Learned

1. **Jinja template bugs are invisible without runtime inspection.** Template typos (wrong attribute name) don't fail; they degrade gracefully into wrong output. Consider: (a) type-hint the template context in a Python annotation that a linter could check, or (b) add a rule to tests/lint that flags any `{{ x.undefined_attr }}` patterns post-render by scanning for UUID patterns in UI text.

2. **Half-applied patterns are harder to spot than missing patterns.** If action-queue items had never gotten any queue section, the gap would be obvious. But they lived in the band system (which was working fine for claimed tasks), so the fact that unclaimed items landed there too read as "normal, just how the system works." The pattern existed, just incomplete. Review checklist: scan for "is this feature handled consistently across all similar cases?"

3. **Explicit phase-file instructions need an explicit verification hook.** The phase 02 file said "check `handle_worklist_band_more`" — good call by the plan author. But the implementation phase didn't include a "verify this check" step. Added 2 regression tests to lock it in (`test_my_task_bands_never_show_xem_them_even_when_over_cap`, `test_queue_and_my_tasks_overflow_do_not_collide_on_shared_band_id`). Next time, make the check a test requirement in the phase file itself, not just a comment.

4. **Concurrent work + git staging discipline.** A separate session landed unrelated work (card-badge-macro) in the same tree mid-session. Split the commits by staging only the files/hunks relevant to this task (hash fix in 1c90e448, redesign in c4e5fdff). This took manual discipline with `git apply` / interactive staging since both commits touched `_wl_row.html` and `screen_worklist.py`. Learned: git workflows under concurrent sessions need tighter scoping than interactive rebase (which isn't available here).

## Next Steps

- Commits ready (hash-fix + redesign, split as above), awaiting user decision on merge/deploy
- 928 tests passing; live smoke test via curl confirmed 3-section layout, correct row counts, no action rows in task bands
- Deferred: `my_tasks` due_date scoping (mentioned in plan as future work, not in scope here)
- Future audit: scan for other instances of Jinja undefined-attr fallback in template suite (likely to find more UUID leaks in edge cases)

