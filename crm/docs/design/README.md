# Handoff: retailCRM — Internal Retail CRM

## Overview
A desktop-first internal CRM for a Vietnamese retail business (~10 users: Sales Rep, CSKH/care,
Manager, Admin). It surfaces warehouse-computed customer insight (RFM, action queue, affinity,
margin) on top of CRM-owned data (parties, tasks, notes, activities, conversations, segments,
campaigns, ad attribution). Backend context: **Go + templ/HTMX, SQLite WAL**, a read-only
`cache.db` warehouse ATTACH-ed to `crm.db`.

This package implements the full UI spec (`ui-spec/`): **13 screens, 6 panels, 14 modals,
2 overlays, 6 reusable components** — all of it interactive.

## About the design files
The files in `prototype/` are a **design reference built in HTML/React (via in-browser Babel)** —
a clickable prototype that shows the intended look and behavior. They are **not** production code
to ship as-is (no real backend, mock data only, Babel-in-the-browser).

**The task:** recreate these designs in the target codebase's environment. The real stack is
**Go + templ + HTMX** — so each screen/panel/modal should become templ components rendered
server-side, with HTMX for the partial reloads, SSE for live events, and the **Precision design
system CSS** (`design_system/`) linked directly. If you implement a SPA instead, the React in
`prototype/crm/*.jsx` is a faithful component map you can port 1:1.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, component styling, copy, and
interactions. Recreate pixel-faithfully using the bundled `design_system/` tokens and classes —
don't re-derive styling. All visual values are documented exactly in **`DESIGN_SYSTEM.md`**.

## How to run the prototype
Open `prototype/retailCRM Prototype.html` in a browser (it links `../design_system/styles.css`
and CDN React/Babel + Google Fonts; needs network for those). Bottom-right gear = **Tweaks**
(theme / accent / font / density). Left nav switches sections; click a customer to open the 360.

---

## Design system & palettes (the user's explicit requirement)
The **complete Precision design system** ships in `design_system/`:
`styles.css` (entry) → `colors_and_type.css` + `ui_kits/crm/styles/app.css` + `crm.css`, plus
`PRECISION_GUIDE.md` (the system's own authoring guide).

**All color palettes are included and documented** in `DESIGN_SYSTEM.md`:
- **Dark** (default) — full warm-gray ink ramp + amber/moss/coral/honey accents.
- **Warm Light** (`data-theme="light"`) — paper ramp + deepened gain/loss.
- **Finance Light** (`data-theme="finance"`) — cool neutral ramp + **indigo** accent + finance gain/loss.
- **Accent overrides** (`data-accent="moss" | "honey"`) combine with any theme.
- **Font pairings**: Editorial (default), Precision, Grotesk, Plex.

Themes/accents/fonts are swapped purely via `data-*` attributes on `<html>` + three font CSS vars —
no rebuild needed. See `DESIGN_SYSTEM.md` §1–§5 for every hex value.

---

## Screens / Views

> Region names and interaction IDs below map to `ui-spec/` (`A-Sxx-###`). Layout: a sticky
> **header** (brand · global customer search · context) + a fixed **left nav** (`crm-nav`) +
> a scrolling content column (`crm-page`, max-width 1320px).

### S01 · Worklist / Dashboard  `M4 · Sales Rep`
- **Purpose:** the rep's morning queue — today's tasks (from `crm_task` + `wh_action_queue`),
  sorted by due + priority.
- **Layout:** page head (+ "Tạo task") → 4 KPI tiles (task mở / đã xong / value-at-stake / P1) →
  filter bar (assignee Của tôi·Tất cả, priority) → task list → freshness footer.
- **Task row:** check-to-complete · action-type **chip** (CALL NOW/WIN BACK/REORDER…) or `AUTO`
  tag · customer name (hover = O02 quick preview) · phone · group badge · rationale · value
  (`đ`) · due · priority pill · quick-call · "Mở hồ sơ".
- **States:** all-done (celebratory), empty, loading skeleton, stale-cache (yellow freshness).
- **Rules:** R2 no-recompute · R8 idempotent tasks · R6 ICT display.

### S02 · Customer List & Search  `M1 · All`
- **Purpose:** browse/search parties (FTS5 + exact phone, target <200ms, 300ms debounce).
- **Layout:** page head (+ "Tạo mới") → 5 segment cards (GOLD/VIP/SILVER/NEW/All, click to filter)
  → toolbar (search input + Value group / Status / Owner selects) → results table → pager.
- **Row:** name + code · phone (mono) · group badge · status badge · owner · last-order · go-arrow → S03.
- **States:** search-empty (→ create), loading. **Rule:** R5 phone E.164.

### S03 · Customer 360 Detail  `M2,M3 · Rep, CSKH`  (hosts P01–P06)
- **Purpose:** full 360° profile; point-lookup ≤200ms (`crm_party_360`).
- **Layout (2-col):** topbar (← back · name · group/status · Ghi log / Task / Gán NV / Tag) →
  **LEFT = primary**: tab bar (Insight·Đơn hàng·Timeline·Tasks·Ghi chú·Chat) + active panel;
  **RIGHT = info panel** (`detail-sidebar`, sticky): Thông tin cơ bản + Consent · Tags (editable)
  · Thông tin bổ sung (custom fields). _(Info panel intentionally placed on the right, matching
  Inbox/Conversation/Builder/Ads.)_
- **States:** loading, no-profile (→ create), no-insight (placeholder), merged (warning banner).
- **Rules:** R2, R3 value-link, R6, R7 realized_margin only.

### S04 · Dedup Review  `M1 · Manager`
- **Purpose:** review `crm_dedup_candidate` (pending) pairs; merge or reject.
- **Layout:** page head (pending count + match-rule filter) → 2-col: candidate list (left) ·
  detail compare (right) showing **Party A = surviving** (amber inset) vs Party B, fact lists,
  match-rule caveat, actions: **Merge A←B** (→ M01) / Reject / Bỏ qua.
- **States:** no-pending, conflict (ERR-MERGE-CONSTRAINT). **Rules:** R4 reversible, R5, R9.

### S05 · Inbox (Conversations)  `M5 · CSKH`
- **Purpose:** Messenger inbound triage (read-only v1).
- **Layout:** page head (Gán cho tôi) → status/assignee filters → 2-col: conversation list (left,
  unread dot + linked/Chưa-link badge + preview + relative time + unread count) · preview pane
  (right: thread preview + "Mở hội thoại" → S06 + "Gán NV" → M09).
- **States:** empty, unresolved-PSID (amber "Chưa link khách"). **Rules:** R6, R12 read-only.

### S06 · Conversation Detail  `M5 · CSKH`
- **Purpose:** read full Messenger thread; link party, log note, close.
- **Layout:** topbar (← Inbox · psid/name · status · Đổi NV / Ghi note / Đóng hội thoại) →
  2-col: message thread (customer left / agent right bubbles, ICT times) + **disabled** input bar
  (read-only v1) · right sidebar = linked customer mini-card (→ S03) **or** "Chưa link khách"
  CTA (→ M11).
- **States:** no-party, closed (input disabled, re-open), loading. **Rules:** R6, R12.

### S07 · Tasks Board  `M4 · All`
- **Purpose:** company-wide tasks, kanban or list.
- **Layout:** page head (List/Board segmented + "Tạo task") → assignee filter → **Board**: 4
  columns Open/Doing/Done/Cancelled, **drag-and-drop** cards between columns; card = AUTO tag +
  priority pill + title (→ S03) + customer (hover O02) + due + assignee + quick "✓ Done".
  **List** view = same data as rows.
- **States:** empty. **Rules:** R8, R11 conversion attribution (done triggers conversion check).

### S08 · Segments List  `M6 · Manager`
- **Layout:** page head (+ "Tạo segment") → name search → table: name + #conditions · type
  (dynamic/static) · member count (−N consent) · updated · status (ready / 0-members /
  materializing spinner) · → S09.
- **States:** materializing, empty-members. **Rules:** R1 consent, R10 re-eval.

### S09 · Segment Builder  `M6 · Manager`
- **Purpose:** visual rule builder (no raw JSON).
- **Layout:** topbar (← · name input · Dynamic/Static) → 2-col: rule editor (left) = AND-joined
  condition rows [field select · operator · value · remove] + "Thêm điều kiện" + live JSON
  preview; **preview panel (right, sticky)** = big match count + "N bị loại do consent" +
  member preview + Hủy / **Lưu & Materialize**.
- **States:** preview-loading, preview-zero (warn), consent-filtered. **Rules:** R1, R10.

### S10 · Campaigns List  `M6 · Manager`
- **Layout:** page head (+ "Tạo chiến dịch" → M07) → status filter → table: name + segment ·
  objective · channel · targets · converted · rate · status → S11.
- **States:** empty (CTA). **Rules:** R1, R10.

### S11 · Campaign Detail / Targets  `M6 · Manager, Rep`
- **Layout:** topbar (← · name · status · Sửa → M07 · Kích hoạt) → 5-stat strip
  (Targets/Sent/Responded/Converted/Rate) → attributed-revenue caveat → status filter →
  target table: customer (→ S03) · status badge (queued/sent/responded/converted/skipped) ·
  assignee · order code · revenue · "Ghi convert" → M12.
- **States:** no-targets, converting. **Rules:** R1, R3, R6, R11.

### S12 · Ads Tracking  `M6 · Manager`
- **Layout:** page head (date range / platform) → 2-col: ad-campaign cards (left: spend/leads/
  CPC/CPL) + freshness · **stats panel (right, sticky)**: total spend / leads / conversion /
  revenue attributed + expandable lead list (→ S03).
- **States:** no-data (Python ingest hint), stale-cache, loading. **Rules:** R2, R6.

### S13 · Settings  `Admin, Manager`
- **Layout:** 2-col: settings nav (Custom Fields / Tags / Người dùng) + content:
  Custom Fields table (+ add → M13, edit, delete → O01) · Tags table (+ create → M14) ·
  Users table with inline role select. **State:** saved toast (O01).

---

## Panels (rendered inside S03 right-of-tab area)
- **P01 Insight** — Action queue cards (C03) · RFM trio (R/F/M) · Signals grid (status,
  next-purchase, discount sensitivity, top affinity, realized margin if `has_cogs`) · freshness
  bar. _R2, R7._
- **P02 Order History** — toolbar (freshness + Ghi log) + last-10 orders table (code · ICT date ·
  net revenue · status); footer total. No `gross_margin_pct`. _R2, R3, R6._
- **P03 Activity Timeline** — type filter + Ghi log; vertical timeline (call/note/visit/email/
  chat/other), chat items link → S06. _R6._
- **P04 Tasks** — status filter + create; task rows with check-to-done, AUTO tag, edit → M05.
- **P05 Notes** — add note (→ M08 note_only); note cards with edit/delete (→ O01).
- **P06 Conversations** — status filter; conversation cards → S06. _R6, R12 read-only._

## Modals (`prototype/crm/modals.jsx`)
M01 Merge Confirm (checkbox-gated, shows what transfers) · M02 Create Party (E.164 live preview) ·
M03 Tag Management (add/remove + create→M14) · M04 Assign Owner · M05 Create/Edit Task
(prefill from action queue) · M06 Custom Fields Edit (renders from registry by type) ·
M07 Create/Edit Campaign (segment → consent-filtered count) · M08 Log Activity (type radios /
note-only mode) · M09 Assign Conversation · M10 Close Conversation (+ optional activity) ·
M11 Link Party (FTS search + create→M02) · M12 Record Conversion (order lookup / manual) ·
M13 Custom Field Definition (type → options) · M14 Create Tag.
All share a `Modal` shell: scrim + Esc/backdrop close + header/body/actions; primary actions
guarded per the spec, success → toast.

## Overlays & Components
- **O01 Confirm/Toast** — small destructive-confirm dialog + auto-dismiss toast stack (3s).
- **O02 Quick Customer Preview** — popover from a customer name in S01/S07 (name · phone · group ·
  last order · affinity · action queue) + "Mở hồ sơ đầy đủ" → S03.
- **C01 Sidebar Nav** — grouped (Hằng ngày / Tăng trưởng / Quản trị), active highlight, **inbox
  unread + dedup pending badges**, user footer, sync status.
- **C02 Global Search** — header FTS dropdown (name · code/group · phone) → S03.
- **C03 Action Queue Card** — type chip (urgency color) + rationale + value + "Tạo task" → M05.
- **C04 Tag Chips** — category-colored chips, editable (+ add / ✕ remove), `+N` overflow.
- **C05 Filter Bar** — faceted selects + active-count + clear-all.
- **C06 Freshness Badge** — green <24h / yellow 24–48h / red >48h, ICT tooltip. _R2._

---

## Interactions & behavior
- **Navigation:** internal route state `{screen, party?, conversation?, campaign?, segment?, tab?}`.
  In the Go/HTMX target these become real routes / `hx-get` partials.
- **Live (SSE) events** to wire server-side: `cache.refreshed` (S01/S03/P01 freshness + reload),
  `chat.message.received` (S05/S06 + inbox badge), `dedup.candidate.created` (S04 badge),
  `campaign.target.converted` (S11 stats), `segment.materialized` (S08/S09 counts),
  `party.merged` (S03/S04), `conversation.assigned` (S05/S06).
- **Transitions:** page-enter translateY(8px) over `--dur-open`; modal/scrim fade+rise; toast
  rise. Honor `prefers-reduced-motion`. No element animates longer than 260ms.
- **Kanban (S07):** native HTML5 drag-and-drop; drop sets `task.status` from column.
- **Forms:** guards per spec (e.g. M02 needs name + valid phone; M05 needs title + due;
  M09/M04 need a selection). Phone normalizes to `+84…` on blur. Past due = warn, not block.

## State management
Per-screen UI state (filters, pagination, selected row, tab, checked/done sets, drag state) is
local. App-level: current route, modal stack (supports M03→M14, M11→M02), toast queue, quick-
preview anchor, and the Tweaks object `{theme, accent, font, density, numfont}` persisted to
`localStorage("crm_tweaks")`; route persisted to `localStorage("crm_route")`. In production these
map to server state + HTMX swaps; Tweaks would be a user preference.

## Design tokens
**See `DESIGN_SYSTEM.md`** — complete color palettes (3 themes + 2 accent overrides + value
colors), full type scale + 4 font pairings, 4-base spacing, radii, the two sanctioned shadows,
and motion tokens. Canonical CSS in `design_system/`.

## Assets
No raster assets. All icons are **inline SVG, 16px box, 1.3 stroke, round caps, `currentColor`**
(`Icon` in `prototype/crm/helpers.jsx`) — redraw in the same style for any new glyph; do not pull
in a rounded/filled icon library. Fonts load from Google Fonts (Fraunces, Geist, Geist Mono,
Newsreader, Space Grotesk, IBM Plex Serif/Sans/Mono). Mock data is fictional (`crm/data.js`).

## Files
```
design_handoff_retail_crm/
├── README.md                         ← this file
├── DESIGN_SYSTEM.md                  ← exact tokens + ALL color palettes
├── design_system/                    ← the full Precision DS (link styles.css)
│   ├── styles.css                    (entry — @imports the three below)
│   ├── colors_and_type.css           (tokens + themes + base type)
│   ├── ui_kits/crm/styles/app.css    (shell, tables, tabs, KPIs, badges…)
│   ├── ui_kits/crm/styles/crm.css    (nav, dashboard, toolbar, segment cards…)
│   └── PRECISION_GUIDE.md            (the system's own guide)
└── prototype/
    ├── retailCRM Prototype.html      ← entry (open this)
    └── crm/
        ├── data.js                   mock data (parties, orders, tasks, convos, …)
        ├── helpers.jsx               fmt/ICT, Icon set, badges, C03–C06, Modal/Field, Toast
        ├── modals.jsx                M01–M14 + O01
        ├── screens_lists.jsx         S01 · S02 · S04
        ├── screens_360.jsx           S03 + panels P01–P06
        ├── screens_inbox.jsx         S05 · S06 · S07
        ├── screens_growth.jsx        S08 · S09 · S10 · S11 · S12 · S13
        ├── app.jsx                   shell + C01 nav + C02 search + router + O02 + Tweaks
        └── crm-extra.css             prototype-only styling (all on DS tokens)
```
Original UI spec lives in the attached `ui-spec/` (surface contracts, domain rules R1–R12,
states/errors, system events) — the authoritative source for behavior.
