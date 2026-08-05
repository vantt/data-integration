# ui-spec content migration — wave 1 (S01, S02, S03)

**Status:** done (2026-07-14)
**Goal:** Migrate 3 most-reviewed screens from `samples:`/`elements:` to `content:` + `row_heights`, proving table skeleton (S01), list/search (S02), and children sub-layout content (S03).

## Scope

| Surface | Key proof point |
|---|---|
| S01 Worklist/Dashboard | `table:` skeleton for worklist rows — density review |
| S02 Customer List & Search | filter bar + `list:`/`table:` |
| S03 Customer 360 Detail | `content:` inside `children` sub-regions (sidebar.*) + `tabs:` + `slot:` for main_col |

Code-path note: `gridCellHtml` already routes child regions through the content path (verified 260714) — no renderer change expected; S03 is the proving migration.

## Rules (from ui-layout-authoring.md §2b)

- Per migrated region: author `content:`, DELETE its `samples:` line + covered `elements:` entries in the same edit.
- Actionable elements (`btn`/`tabs`) carry `action:`; audit must come out clean or legitimately display-only.
- Add `row_heights` where a region dominates (worklist table, S03 main_col).
- After each file: validate → build → screenshot → vision QA (checklist §11).

## Acceptance

- validate 0 errors / 0 warnings (post-build); verify-runtime PASS.
- chip-audit: no actionable-unmapped on S01/S02/S03.
- Vision QA: table/list skeletons visible, tabs render as tabs, main_col slot hatched, proportions honest.
