# Phase 08c — Panels / Overlays / Components ui-layout Draft Report

Date: 2026-07-02

## Per-File Status

### Panels (P01–P06) — quality notes only, blocks already exist

| File | Status | Quality note |
|------|--------|--------------|
| P01 — Value & Behavior | pre-existing ✓ | Single-column, all 6 regions covered; samples are Vietnamese-rich with tier badges (GOLD, active), monetary amounts (18.4tr), and both action-queue modes — sensible and complete. |
| P02 — Order History | pre-existing ✓ | Single-column, 2 regions; toolbar sample includes freshness timestamp (ICT), order_list sample has order_code + VND + status — minimal but accurate. |
| P03 — Activity Timeline | pre-existing ✓ | Single-column, 2 regions; timeline sample captures activity type badge, ICT timestamp, and Vietnamese free-text note — representative of the richest content. |
| P04 — Tasks | pre-existing ✓ | Single-column, 2 regions; task_list sample shows status indicator (●), AUTO badge, priority, overdue label, and action buttons — covers all visible sub-elements. |
| P05 — Notes | pre-existing ✓ | Single-column, 3 regions; pinned_section sample shows starred warning with author+date, notes_list shows type badge with Vietnamese content — distinct samples per region. |
| P06 — Conversations | pre-existing ✓ | Single-column, 2 regions; conv_list sample includes channel, ICT timestamp, agent name, closed status, and action button [Xem →] — region coverage complete. |

### Overlays (O01–O03) — drafted this session

| File | Status | Notes |
|------|--------|-------|
| O01 — Confirm/Toast | DONE ✓ | Single-column [content → actions]; `content` covers message text + backdrop (per A-O01-001 region mapping); toast auto-dismiss is a runtime state, no layout variant needed (no ASCII variant shown). |
| O02 — Quick Customer Preview | DONE ✓ | Single-column [content → actions]; close button [✕] placed in `content` (per A-O02-002); `actions` = single CTA "Mở hồ sơ đầy đủ →"; loading/no-insight states are runtime, not variants. |
| O03 — Postpone Task | DONE ✓ | Single-column [body → actions]; `body` = form with date+time inputs (scrim also in body per A-O03-002); error state (empty date) is runtime guard, not layout variant. |

### Components (C01–C06) — skipped

All 6 component files declare `regions: []` in frontmatter. Per spec rule ("component with NO regions at all → skip file, note in report"), no `yaml ui-layout` block was added to any component file.

| File | Status |
|------|--------|
| C01 — Sidebar Nav | SKIPPED — regions: [] |
| C02 — Global Customer Search | SKIPPED — regions: [] |
| C03 — Action Queue Card | SKIPPED — regions: [] |
| C04 — Tag Chips | SKIPPED — regions: [] |
| C05 — Filter Bar | SKIPPED — regions: [] |
| C06 — Freshness Badge | SKIPPED — regions: [] |

## Validator Result

```
Scanned 54 spec files, 311 actions, 52 surfaces.
⚠ [wireframe] wireframe-v2.html is older than 14 spec file(s) — run build to regenerate
✓ validation passed (1 warning(s)).
```

Stale-wireframe warning pre-authorized to ignore. No VR-LAYOUT-* errors.

## Judgment Calls

- O01 `content` region encompasses both the dialog text and the overlay backdrop element (A-O01-001 maps `overlay_backdrop` to `content`) — consistent with treating the whole overlay body as content.
- O02 [✕] close button lives in `content` not `actions` — confirmed by A-O02-002 (`btn_close, region: content`); CTA "Mở hồ sơ đầy đủ →" is the only true action.
- O03 scrim falls in `body` (per A-O03-002 `scrim, region: body`) even though scrim is technically a backdrop — consistent with the only two declared regions.
- No `floating:` or `variants:` added to any overlay since no ASCII variant diagrams exist and states described are runtime only.

## Unresolved Questions

None.

---

Status: DONE
Summary: Drafted `yaml ui-layout` blocks for O01, O02, O03 (single-column overlays, all declared regions covered); skipped C01–C06 (no regions declared); noted P01–P06 panel block quality (all sensible, region coverage complete). Validator clean.
