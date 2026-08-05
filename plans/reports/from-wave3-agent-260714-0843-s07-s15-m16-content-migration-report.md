# S07 / S15 / M16 — samples/elements → content migration report

Recipe followed: `.skills/ui-spec/references/ui-layout-authoring.md` §8b, primitives §2b.
Canonical examples imitated: S14 (row/kpi/badge/tabs), S02 (slot for C01 sidebar, select/input filters,
table+pagination), S03 (per-tab `actions:`), M08 (form row/select/chips/input), P01 (kpi rows, list).

## S07 — Tasks Board (`crm/docs/ui-spec/screens/S07-tasks-board.md`)

Regions migrated: `sidebar`, `topbar`, `board` (all 3; frontmatter `regions[]` unchanged).
Added `row_heights: [auto, "minmax(280px,auto)"]` — board is the dominant region vs. the thin topbar row.

- `sidebar` → `slot: "C01 Sidebar Nav (global)"` (same idiom as S02/S04/S05/S08/S10/S12/S13).
- `topbar` → `h` "Tasks" + `btn "+ Tạo task"` (A-S07-001, primary) in one row; second row: 4× `select`
  (Assignee/Priority/Campaign/Status, no `action:` — matches S02's filter convention, select/input
  are non-actionable types) + `input "🔍 Party"` + `tabs: ["List","Board"]` with a single
  `action: A-S07-007` (whole-bar toggle, matches btn_toggle_view semantics).
- `board` → header row of 3 `h` (OPEN/DOING/DONE) + row of 3 `list:` blocks (one skeleton lane per
  status), sample text carried verbatim from the old `[AUTO] CALL_NOW…` / `Follow-up A…` / `Gọi T. B…`
  lines.

Actions mapped: A-S07-001 (btn), A-S07-007 (tabs). Filters A-S07-005/006/008/009/010 are `select`/`input`
— per §2b these types are never checked for `action:` (only `btn`/`tabs` are actionable), so no mapping
needed/possible on them; this matches S02's identical filter-select pattern.

Contract gap noted (not fixed, no action invented): A-S07-002 (task_card click→S15), A-S07-003
(task_checkbox→set_done), A-S07-004 (task_card_drag) have real contract entries but no primitive in
the `list`/`table` schema carries a per-item `action:` — this is a schema limitation (list/table are
non-actionable types), not a missing mapping I could fix. The "AI-11 dismissed actions manager view"
link mentioned in Implementation Notes is explicitly documented as "not part of the formal interaction
contract — plain navigational link" and isn't a declared region, so nothing to migrate there.

## S15 — Task Detail (`crm/docs/ui-spec/screens/S15-task-detail.md`)

Regions migrated: all 7 (`header`, `lifecycle`, `body_contact`, `body_internal`, `body_generic`,
`activity_log`, `close_bar`). `body_internal`/`body_generic` stay in `floating` (unchanged geometry),
now with their own `content:` entries (same pattern as S14's `stop_banner`).
Added `row_heights: [auto, auto, "minmax(200px,auto)", "minmax(120px,auto)", auto]` (5 base areas rows;
`body_contact` dominates, `activity_log` secondary).

- `header`: row of `btn "← Quay lại"` (A-S15-011), `h` title, 3× `badge` (P1 / "Quá hạn 2 ngày" /
  "status chip" — kept literal, see ambiguity below), 2× `text` (due date, assignee), `btn "Nguyễn Văn A
  ↗ 360"` (A-S15-007).
- `lifecycle`: `text` state-chain + row of 4 `btn` (A-S15-001..004).
- `body_contact`: provenance `text` + row (`h` name, `badge GOLD`, `text` phone, `btn "▶ Vào phiên
  gọi"` A-S15-006 primary).
- `body_internal`: row (`h` name, `badge GOLD`, `text` LTV, `btn "Xem 360 >"` A-S15-007) + `checklist`
  + a new row of 2 `btn` for the "tool CTAs" the Purpose section calls out (`✎ Sửa liên hệ` →
  A-S15-009, `＋ Thêm tag` → A-S15-010). **Note**: these two buttons were NOT visible as bracketed
  chips in the old `samples:` line (only checkbox glyphs, no `[…]` tokens) even though the contract
  already defines `btn_tool_edit_contact`/`btn_tool_add_tag` scoped to `region: body_internal` and the
  Purpose/task_kind table explicitly says body_internal = "Checklist/bước + facts khách tối thiểu +
  tool CTAs". Per step 1 of the recipe ("the contract's element names + region fields tell you which
  actions belong in which region") I surfaced them as buttons rather than omitting real, region-scoped
  interactions. Flagging this interpretation call rather than silently doing it.
- `body_generic`: `text` description + `checklist` + `text` link (no `link` primitive exists; kept as
  plain `text`).
- `activity_log`: `list: { item: "12/06 10:30 Cuộc gọi — Không bắt", rows: 2 }` — the old sample had two
  *distinct* real log lines; `list` only supports one real item + ghost repeats, so the second entry
  ("13/06 14:00 Zalo — Chưa phản hồi") is now a repeated skeleton row, not literal text. This is the
  primitive's designed behavior (matches S02/P01 usage), not a bug, but is a genuine content loss vs.
  the old two-line sample — noting it as a recipe-inherent tradeoff rather than a mapping error.
- `close_bar`: row of `input "ghi chú nhanh…"` + `btn "✓ Ghi log & hoàn thành"` (A-S15-005, primary).

Actions mapped: A-S15-001..007, A-S15-009, A-S15-010, A-S15-011 (all `btn` types carry `action:`).

Ambiguity/gap flagged (pre-existing, not introduced by this migration):
1. `badge: "status chip"` — the original samples line literally used the bracket placeholder text
   `[status chip]` rather than a real status value (e.g. `doing`/`open`). Recipe says "do not invent
   new business facts," so I kept the placeholder text verbatim rather than guessing a real state.
2. A-S15-007 (`btn_view_360`) is declared in the contract with `region: header` only, but both the
   original `elements:` map AND my `content:` use it in two places — `header` ("Nguyễn Văn A ↗ 360")
   and `body_internal` ("Xem 360 >"). This region/action mismatch predates this migration (same dual
   mapping existed in the old `elements:` block); carried forward unchanged, not introduced or fixed
   by me since I cannot edit the contract block.

## M16 — Promote / Create Insight Modal (`crm/docs/ui-spec/modals/M16-promote-insight-modal.md`)

Regions migrated: all 3 (`header`, `body`, `actions`). No `row_heights` added (3-row form modal,
matches M08 canonical example which also omits it).

- `header`: row of `h "Insight: Nguyễn Văn A"` + `btn "✕"` (A-M16-001).
- `body`: row (`text "Loại insight *"` + `select "Persona"`) + `text "Nội dung *"` + `input` (prefill
  text carried verbatim) + row (`text "Độ tin cậy"` + `chips` for the 3 confidence levels — kept as
  display-only `chips` since the contract has no separate interaction/action id for confidence
  selection; it's only captured via the Save guard `form.insight_type != null && form.body != ''`) +
  `text` source-note line.
- `actions`: row of `btn "Hủy"` (A-M16-002) + `btn "Lưu insight"` (A-M16-003, primary).

Actions mapped: A-M16-001, A-M16-002, A-M16-003 — full coverage, no gaps.

## Recipe ambiguity encountered

- §2b doesn't have a primitive for a Kanban-style multi-lane board (S07's OPEN/DOING/DONE columns).
  Used a `row:` of 3 `h` headers + a `row:` of 3 `list:` blocks as the closest fit ("collection → list,
  repetition is the point"), but the recipe doesn't explicitly cover multi-column collections — this
  was a judgment call, not a documented pattern.
- No primitive exists for a hyperlink (S15 `body_generic`'s Google Drive URL) — used plain `text`, same
  as would be done for any other prose-with-no-matching-type case; recipe doesn't call this out
  explicitly.
- `list`/`table` have no `action:` opt in the schema (confirmed in `layout-schema.mjs` CONTENT_TYPES),
  so per-item contract interactions on collection rows (S07's task_card click/checkbox/drag) can't be
  represented at all in `content:` — worth a docs note for future skill maintainers, but not something
  I could resolve within the current primitive set.

## Verify outputs (summarized)

```
validate.mjs (pre-build):  0 errors, 4 warnings (all VR-ASCII-DRIFT, expected — fence edited, ASCII not yet regenerated)
build.mjs:                 3/40 surfaces' ASCII regenerated (S07, S15, M16); chip-audit: 242 tokens, 195 mapped, 47 unmapped (all in OTHER, still-samples-path surfaces — S07/S15/M16 have zero entries)
validate.mjs (post-build): 0 errors, 0 warnings
verify-runtime.mjs:        RESULT: PASS — 54 surfaces exercised, 6 flows, 0 errors
screenshot.mjs:             3/3 written:
  crm/docs/ui-spec/generated/screenshots/S07.png
  crm/docs/ui-spec/generated/screenshots/S15.png
  crm/docs/ui-spec/generated/screenshots/M16.png
```

Visual QA (vision pass on all 3 PNGs): proportions match declared `columns`/`row_heights`; sample
content dominant, region labels small/muted; airy layout, no overflow/overlap; primary CTAs visually
distinct (dark fill); Vietnamese diacritics render cleanly, no mojibake/tofu; S07's List/Board tabs and
S15's floating body_internal/body_generic toggle banners render correctly at the bottom of the grid.

## Files modified

- `D:\Vantt\app\data-integration\crm\docs\ui-spec\screens\S07-tasks-board.md`
- `D:\Vantt\app\data-integration\crm\docs\ui-spec\screens\S15-task-detail.md`
- `D:\Vantt\app\data-integration\crm\docs\ui-spec\modals\M16-promote-insight-modal.md`

No files under `.skills/`, no other spec surfaces, and no `crm-contract` yaml blocks were touched.

## Unresolved questions

1. Should the skill's §2b primitive table gain a multi-lane/kanban-column primitive, or is `row` of
   `list` blocks the intended/accepted idiom for boards like S07? (Currently a judgment call.)
2. Should `list`/`table` gain an `action:` opt for per-item interactions (task_card click/checkbox/
   drag on S07's board), or is that intentionally out of scope for the wireframe model (display-only,
   full contract lives in the Interactions tab)?
3. S15's A-S15-007 region mismatch (declared `region: header`, used in both `header` and
   `body_internal`) — worth fixing in the contract block at some point, but out of scope for this
   migration (contract edits were explicitly disallowed).

Status: DONE
Summary: Migrated S07/S15/M16 samples+elements to typed content per §8b recipe; 0 validate errors/warnings, verify-runtime PASS, 3/3 screenshots written, chip-audit shows zero unmapped actionable entries for all three surfaces.
Concerns/Blockers: Three recipe ambiguities noted above (no kanban/board primitive, no link primitive, list/table lack per-item action) — none blocking, all resolved via documented judgment calls in the report.
