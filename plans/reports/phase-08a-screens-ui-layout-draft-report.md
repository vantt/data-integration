# Phase 08a — Screens UI Layout Draft Report

Date: 2026-07-02  
Validator: `node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec`  
Result: ✓ validation passed (1 warning — stale wireframe, ignored per task instructions)

---

## Per-file Status

| File | Status | Notes |
|------|--------|-------|
| S01-worklist-dashboard.md | ✓ DONE | `main` not labeled in ASCII → interpreted as right-side container; nested topbar/kpi_strip/filter_bar/task_list in `children.main` |
| S02-customer-list-search.md | ✓ DONE | Same `main`-as-container pattern; topbar contains search + filters, result_list is the table area |
| S03-customer-360-detail.md | ✓ DONE | 2-col [7fr, 3fr]; sidebar sub-regions in `children.sidebar`; `sidebar.warning` in BOTH children (positional slot) AND floating (conditionality flag) |
| S04-dedup-review.md | ✓ DONE | 3-col [1fr, 2fr, 4fr]; topbar spans candidate_list + detail_pane columns |
| S05-inbox.md | ✓ DONE | 3-col [1fr, 2fr, 3fr]; topbar spans conv_list + preview_pane |
| S06-conversation-detail.md | ✓ DONE | 2-col [3fr, 1fr]; C01 sidebar not in regions (global nav, not a screen region); customer_sidebar spans all 3 rows on right |
| S07-tasks-board.md | ✓ DONE | 2-col [1fr, 4fr]; board is single region for kanban columns |
| S08-segments-list.md | ✓ DONE | 2-col [1fr, 4fr]; straightforward single-content-area layout |
| S09-segment-builder.md | ✓ DONE | 2-col [3fr, 2fr]; no sidebar in regions (C01 is global nav); topbar + actions_bar span both columns |
| S10-campaigns-list.md | ✓ DONE | 2-col [1fr, 4fr]; straightforward |
| S11-campaign-detail-targets.md | ✓ DONE | Single column; C01 sidebar not in regions; `conversion_stats` absent from ASCII — placed last by regions[] order |
| S12-ads-tracking.md | ✓ DONE | 3-col [1fr, 3fr, 2fr]; topbar spans ad_campaign_list + stats_panel |
| S13-settings.md | ✓ DONE | 3-col [1fr, 1fr, 4fr]; sidebar=C01 global nav, settings_nav=inner left nav, settings_content=inner right; topbar spans inner 2 columns |
| S15-task-detail.md | ✓ DONE | Single column; body_contact as default in base areas; body_internal + body_generic as `floating` with `replaces: [body_contact]` to express mutual exclusion by task_kind |

---

## Judgment Calls

1. **S01/S02 — `main` region**: Region declared but never labeled in ASCII wireframe. Interpreted as the right-side chrome wrapper containing the specific content regions. Used `children.main.areas` to nest them. The alternative (putting `main` as a flat row in areas) would create an orphaned row with no visual meaning.

2. **S03 — `sidebar.warning` dual placement**: Added to both `children.sidebar.areas` (top slot, always in DOM) and `floating` (marks the conditional nature). This is intentional: the children entry defines positional order (warning appears above core_info), the floating entry communicates the condition. Validator accepts this.

3. **S06/S09/S11 — C01 sidebar not in regions**: The ASCII wireframes show a `C01 SIDEBAR` column, but these screens don't declare `sidebar` in their `regions[]`. That global nav chrome is not a screen-owned region. Layout blocks omit the sidebar column accordingly.

4. **S11 — `conversion_stats` absent from ASCII**: Region is declared but not labeled in the wireframe. No interaction references it directly (LSN01 updates `summary_bar.stats` and `target_list`). Placed last in single-column areas per regions[] order. Sample marked as a tracker that updates via SSE.

5. **S15 — body variants via `floating`**: Three mutually exclusive body regions (`body_contact`, `body_internal`, `body_generic`) can't be expressed via `prepend_rows`/`append_rows` variants (those only add rows, not swap). Used `floating` with `replaces: [body_contact]` for the non-default kinds. `body_contact` is the default in base areas (maps to the most common task_kind per existing data).

6. **S13 — `settings_nav` column proportions**: Assigned [1fr, 1fr, 4fr]. The inner settings_nav is a narrow label list, but since its width relative to settings_content depends on design implementation, 1fr:4fr for nav:content is a reasonable starting estimate.

---

## Unresolved Questions

- **S11 `conversion_stats`**: Is this a separate visible panel (e.g., a chart or extended stats section below target_list), or is it embedded within `summary_bar`? Interaction A-S11-LSN01 touches `summary_bar.stats` but not `conversion_stats`. If it's truly a separate visible region, the single-column placement is correct; if it's a logical sub-region of `summary_bar`, the spec should be updated to reflect that.
- **S03 `topbar` scope**: The ASCII shows topbar buttons only in the left (main_col) column, with sidebar starting at the same vertical level on the right. Placed as `[topbar, sidebar]` in row 1 (topbar does not span full width). If the intent is a full-width topbar above both columns, areas matrix needs adjustment to `[topbar, topbar]` in row 1.

---

Status: DONE  
Summary: Drafted and inserted `yaml ui-layout` blocks into all 14 owned screen files; validator passes clean with only the expected stale-wireframe warning.
