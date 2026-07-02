# FILEMAP — surface → file → component

All paths relative to `design_handoff/`. Surface ids mirror `prototype/crm/registry.js`
(`window.REG.SURF`) — **44 surfaces**: 15 screens · 6 panels · 14 modals · 3 overlays ·
6 components. Harness/Clean-view/Theme rows are **review-only — do not port** (see README §2).

## Screens

| ID | Name (vi) | File | Component | Notes |
|---|---|---|---|---|
| S01 | Worklist | `prototype/crm/screens_lists.jsx` | `S01_Worklist` | KPI tiles · **WLFilterBar** (`wl_filter.jsx`) · task list · O02 on hover |
| S02 | Khách hàng | `prototype/crm/screens_lists.jsx` | `S02_CustomerList` | Segment cards · FTS toolbar · table · pager → S03 |
| S03 | Hồ sơ 360 | `prototype/crm/screens_360.jsx` | `S03_Customer360` | Hosts P01–P06 (tabs) + right info panel |
| S04 | Dedup | `prototype/crm/screens_lists.jsx` | `S04_Dedup` | A↔B compare · Merge → M01 (R4) |
| S05 | Inbox | `prototype/crm/screens_inbox.jsx` | `S05_Inbox` | List + preview → S06 · Gán NV → M09 |
| S06 | Hội thoại | `prototype/crm/screens_inbox.jsx` | `S06_Conversation` | Read-only thread · → M10/M11 |
| S07 | Tasks | `prototype/crm/screens_inbox.jsx` | `S07_Tasks` | **Kanban HTML5 drag-and-drop** (List/Board) · title click → S15 |
| S08 | Segments | `prototype/crm/screens_growth.jsx` | `S08_Segments` | → S09 |
| S09 | Segment Builder | `prototype/crm/screens_growth.jsx` | `S09_Builder` | AND-rule editor + live JSON + match count |
| S10 | Chiến dịch | `prototype/crm/screens_growth.jsx` | `S10_Campaigns` | → S11 · create → M07 |
| S11 | Chi tiết chiến dịch | `prototype/crm/screens_growth.jsx` | `S11_Campaign` | Target table · Ghi convert → M12 |
| S12 | Ads | `prototype/crm/screens_growth.jsx` | `S12_Ads` | Ad cards + sticky stats panel |
| S13 | Cài đặt | `prototype/crm/screens_growth.jsx` | `S13_Settings` | Custom Fields → M13 · Tags → M14 · Users |
| S14 | Chế độ gọi | `prototype/crm/screens_call.jsx` | `S14_CallMode` | Full-bleed cockpit; **no C01 sidebar on this screen** |
| S15 | Chi tiết task | `prototype/crm/screens_task.jsx` | `S15_TaskDetail` | Task lifecycle owner: `open→doing→done/cancelled`. Body varies by `task_kind` (`contact`/`internal`/`generic`); contact tasks launch the shared S14 call session. Sticky close-bar → M08 log |

## Panels — hosted inside S03 (`prototype/crm/screens_360.jsx`)

| ID | Name (vi) | Host tab | Behavior |
|---|---|---|---|
| P01 | Insight | Insight | Action queue (C03) · RFM · signals · freshness (R2, R7) |
| P02 | Đơn hàng | Đơn hàng | Last-10 orders, net revenue, no margin% (R2, R3, R6) |
| P03 | Timeline | Timeline | Activity timeline; chat items → S06 (R6) |
| P04 | Tasks | Tasks | Check-to-done · edit → M05 · hoãn → O03 |
| P05 | Ghi chú | Ghi chú | Add → M08 (note-only) · delete → O01 |
| P06 | Chat | Chat | Conversation cards → S06 (R6, R12) |

## Modals & overlays (`prototype/crm/modals.jsx`, except M08 / O03)

| ID | Name | Component / File | Host(s) | Notes |
|---|---|---|---|---|
| M01 | Merge Confirm | `M01` · modals.jsx | S04 | Checkbox-gated; lists transfers; R4 reversible |
| M02 | Create Party | `M02` · modals.jsx | S02 | E.164 live preview |
| M03 | Tag Management | `M03` · modals.jsx | S03 | → M14 |
| M04 | Assign Owner | `M04` · modals.jsx | S03 | Needs selection |
| M05 | Create/Edit Task | `M05` · modals.jsx | S01·S03·S07·P04·**S15** | Needs title + due |
| M06 | Custom Fields Edit | `M06` · modals.jsx | S03 | Renders by field type |
| M07 | Create/Edit Campaign | `M07` · modals.jsx | S10·S11 | Segment → consent-filtered count |
| M08 | Log Activity | `M08` · **`modal_m08.jsx`** | S03·S06·P02·P03·P05·S15 (via close-bar) | Redesign; **overrides** `MODALS.M08` |
| M09 | Assign Conversation | `M09` · modals.jsx | S05·S06 | |
| M10 | Close Conversation | `M10` · modals.jsx | S06 | + optional activity |
| M11 | Link Party | `M11` · modals.jsx | S06 | FTS + create → M02 |
| M12 | Record Conversion | `M12` · modals.jsx | S11 | Order lookup / manual; R11 attribution |
| M13 | Custom Field Definition | `M13` · modals.jsx | S13 | Type → options |
| M14 | Create Tag | `M14` · modals.jsx | S13·M03 | |
| O01 | Confirm / Toast | `O01` + `ToastStack` · modals.jsx | S03·S05·S13·P05 | Destructive confirm + 3.2 s toast stack |
| O02 | Quick Preview | `QuickPreview` · app.jsx | S01·S07 | Popover → S03 |
| O03 | Postpone Task | `O03_Postpone` · **`screens_task.jsx`** (registers into `MODALS.O03`) | P04·S07·S15 | `modal--sm`; sets new due date/time; resets `doing`→`open`; logs a "hoãn" entry (does not open M08) |

## Components

| ID | Name | Component / File | Notes |
|---|---|---|---|
| C01 | Sidebar Nav | `Sidebar` · app.jsx | **KEEP** — product nav (Hằng ngày/Tăng trưởng/Quản trị) |
| C02 | Global Search | `GlobalSearch` · app.jsx | **KEEP** — header FTS dropdown → S03 |
| C03 | Action Queue Card | `ActionQueueCard` · helpers.jsx | Type chip + rationale + value → M05 |
| C04 | Tag Chips | `TagChips` · helpers.jsx | Category-colored, editable, +N overflow |
| C05 | Filter Bar | `FilterBar` / `FilterSelect` · helpers.jsx | Faceted selects + clear-all (S02/S05/S07/S10/S11). **S01 uses the redesigned `WLFilterBar` (`wl_filter.jsx`) instead** — sticky two-row: search + mode toggles, collapsible advanced row, active-filter count pill |
| C06 | Freshness Badge | `FreshnessBadge` · helpers.jsx | <24h green / 24–48h amber / >48h red |

## Shell / infrastructure (`prototype/crm/app.jsx`)

| Piece | Component | Port? |
|---|---|---|
| Root + router + modal stack + toasts | `App` | KEEP (strip harness/clean/theme wiring) |
| App header (brand · C02 · context crumb) | `App` header | KEEP |
| C01 product sidebar | `Sidebar` | KEEP |
| **Surface harness rail** | `HarnessRail` · `RegRow` | **DELETE** (review chrome) |
| **Clean view + mini-nav** | `CleanNav` · `loadClean` | **DELETE** |
| **Theme panel + applyTweaks** | `ThemePanel` · `applyTweaks` · `THEMES/ACCENTS/FONTS` | OPTIONAL (keep CSS-var mechanism, drop picker) |

## Non-surface files

| File | Role |
|---|---|
| `prototype/crm/data.js` | Mock data (`window.DB`) — **REPLACE** with real queries/API |
| `prototype/crm/registry.js` | `window.REG` surface registry (44 ids) — drives the harness (review-only) |
| `prototype/crm/helpers.jsx` | Formatters (VND/ICT), `Icon` set, badges, C03–C06, `Modal`/`Field`, `ToastStack` exports |
| `prototype/crm/wl_filter.jsx` | S01 worklist filter redesign — exports `WLFilterBar`, `WLF_DEFAULTS`, `wlfChips`, `wlfCount`. Loads **before** `screens_lists.jsx` |
| `prototype/crm/screens_task.jsx` | **S15 Task Detail** (`S15_TaskDetail`) + **O03 Postpone Task** overlay. Owns task lifecycle rendering; body variants `BodyContact`/`BodyInternal`/`BodyGeneric` keyed on `task_kind`. Registers `window.MODALS.O03` itself (loads after `modals.jsx`) |
| `prototype/crm/crm-extra.css` | ⚠ Harness + product styles **mixed** — split on port (README §8). Includes `.wlf-*` (S01 filter) and `.tkind-tag`/`.m05-kind-auto` (task_kind mini-tags, shared with S15) |
| `prototype/crm/s15.css` | **S15-only** styles (`.s15-*`) — header, lifecycle rail, body sections, activity timeline, sticky close-bar. Clean product CSS, nothing to split |
| `prototype/crm/berich-theme.css` | **beRich** theme — a second, alternate visual skin ported in as a selectable theme (`data-theme="berich"` / `"berich-dark"` + 6 gemstone accents). Clean, self-contained token remap — nothing to split. **This is the prototype's current default theme** (see README §6.4) |
| `design_system/styles.css` | DS entry (@imports the three token/util files) — **link directly** |
| `design_system/colors_and_type.css` | **Token source of truth** (colors, type, spacing, radii, motion, themes) |
| `design_system/ui_kits/crm/styles/app.css` | Shell, tables, tabs, KPIs, light theme, accent hooks |
| `design_system/ui_kits/crm/styles/crm.css` | Nav, dashboard, toolbar, segment cards, filters |
| `design_system/PRECISION_GUIDE.md` | Design system's own authoring guide (Precision — the base theme; beRich is a CRM-local addition, see README §6.4) |
