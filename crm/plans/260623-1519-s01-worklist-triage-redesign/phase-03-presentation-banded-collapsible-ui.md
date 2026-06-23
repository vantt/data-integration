# Phase 03 — Presentation: Banded Collapsible UI

**Context:** `plan.md` · proposal §5 (wireframe). **Priority:** P1. **Status:** pending. **Depends:** Phase 01.

## Overview
Rework `worklist_fragment.html` to render the banded structure from Phase 01: collapsible band sections with counts, per-band cap + "Xem thêm", visual hierarchy by band, completion progress, and split dismiss-vs-done controls. Fix KPI inconsistency.

## Key insights
- Phase 01 returns `bands: [{id,label,rows,count,total_value}]` → template iterates bands, not two flat loops.
- Current ✓ overload: action ✓ = dismiss (`:89`), task ✓ = done (`:191`) → split into distinct controls.
- KPI bug: `value_total` sums actions only; `p1_count` counts tasks only → recompute consistently over banded rows (Phase 01 supplies totals).
- Verify `bdg_cls`/`bdg_tip` cover mart action_types (REORDER_PREEMPT/SECOND_ORDER/HIGH_CANCEL_RISK) — add styles if missing.

## Requirements
**Functional**
- Render 4 bands in order; Band 0/1/2 expanded, Band 3 collapsed (HTML `<details>`).
- Band header: icon + label + count (+ total value for value-bearing bands).
- Per-band cap (default 10; Band 3 = 5) with "Xem thêm (N)" → expands remaining (HTMX fragment param `?expand=<band>` or client `<details>`/JS toggle — prefer no-JS `<details>` or HTMX).
- Visual hierarchy: left-border color per band (coral B0/B1, neutral B2, muted B3); B3 rows compact.
- Progress: "Đã xong X/Y" + bar (Y = total open rows; X from done state this session or task done count).
- Controls split:
  - action row: "✕ Bỏ qua" (dismiss) + quick-contact + snooze + Xem 360.
  - task row: checkbox done + quick-contact + Mở hồ sơ; Band 0 adds "Dời hạn" (→ M05 edit) + "Dọn" (cancel).
- Neglect badge "đã chờ N ngày" (Band 2, from Phase 01).
- Empty/all-done states preserved (ST-WORKLIST-EMPTY / ALL-DONE).
- Freshness footer + `is_stale` unchanged.

**Non-functional:** keep server-rendered + HTMX; minimal/no new JS; reuse existing `wl-*` classes; new CSS additive.

## Architecture
- Template loops `for band in bands` → `for row in band.rows[:cap]`. Row macro switches on `row.kind` to render action vs task variant (DRY: Jinja macro `wl_row(row)`).
- Cap/expand: simplest = render all but hide overflow via `<details>` per band; or pass `expand` query to re-render uncapped. Choose `<details>`-based to avoid extra round-trips.

## Related code files
- **Modify:** `src/adapters/inbound/web/templates/fragments/worklist_fragment.html` (major rework → consider extracting `fragments/_wl_row.html` macro if > ~200 lines)
- **Read/Modify CSS:** locate `wl-row`/`prio`/`kpi` styles (grep `wl-row` in `static/app.css`, `static/ds-extra.css`); add band + progress + compact styles.
- **Read:** `templates/worklist.html`, `fragments/task_done_row.html`, badge filters (`templating.py`).

## Implementation steps
1. Grep + read current `wl-*`/`kpi`/`prio` CSS; identify file to extend.
2. Build Jinja `wl_row` macro (action + task variants) in `fragments/_wl_row.html`.
3. Rewrite `worklist_fragment.html`: KPI strip (from Phase 01 totals + progress bar) → filter bar (Phase 02) → band loop with `<details>` cap → footer.
4. Split dismiss/done controls; add Band 0 "Dời hạn"/"Dọn".
5. Add CSS: band sections, left-border tones, compact B3, progress bar, neglect badge.
6. Verify badge styles for all mart action_types; add missing.
7. Manual smoke: empty, all-done, mixed bands, collapsed B3, "Xem thêm".

## Todo
- [ ] locate wl-* CSS source
- [ ] `_wl_row.html` macro (DRY)
- [ ] band loop + collapse + cap/"Xem thêm"
- [ ] dismiss/done split + Band 0 reschedule/clear
- [ ] progress bar + KPI fix
- [ ] band visual hierarchy CSS
- [ ] action_type badge coverage
- [ ] states preserved

## Success criteria
- 4 bands render with counts; B3 collapsed; long band caps at 10 with working "Xem thêm".
- Dismiss (action) and Done (task) are visually distinct controls.
- KPIs consistent (value across all value-bearing rows; urgent count via urgency).
- No regression: row click → S03, quick-contact → M08, snooze/dismiss HTMX still work.
- No raw/unstyled action_type badges.

## Risks
- `worklist_fragment.html` already non-trivial; macro extraction needed to stay < 200 LoC (modularization rule).
- `<details>` cap vs HTMX expand — pick one; document. Keyboard/a11y: ensure `<details>` accessible.
