# retailCRM — Developer Handoff

> **Internal Retail CRM** · ~10 users · Desktop-first · Vietnamese market  
> Backend target: **Go + templ/HTMX · SQLite WAL** (`crm.db` ↔ `cache.db` ATTACH read-only)

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Design Reference — Do Not Ship HTML](#2-design-reference--do-not-ship-html)
3. [Fidelity](#3-fidelity)
4. [How to Run the Prototype](#4-how-to-run-the-prototype)
5. [Harness vs. Product — KEEP / DELETE](#5-harness-vs-product--keep--delete)
6. [CSS Split: crm-extra.css](#6-css-split-crm-extracss)
7. [Surface Groups — 41 Surfaces](#7-surface-groups--41-surfaces)
8. [Interactions](#8-interactions)
9. [State Management](#9-state-management)
10. [Design Tokens](#10-design-tokens)
11. [Assets](#11-assets)
12. [File Inventory](#12-file-inventory)
13. [Domain Rules Quick Reference](#13-domain-rules-quick-reference)

---

## 1. Product Overview

An internal CRM for a Vietnamese beauty-retail business. ~10 concurrent users split across three
personas: **Sales Rep (NV)**, **CSKH (customer-care agent)**, and **Manager / Admin**.

The system surfaces warehouse-computed customer intelligence — RFM scores, affinity, action queues,
realized margin — from a read-only `cache.db` (Python reverse-ETL job) ATTACHed to the main
`crm.db`. The CRM itself owns parties, tasks, notes, activities, conversations, segments, campaigns,
and ad-attribution records.

**Persona summary:**

| Persona | Primary surfaces | Key jobs |
|---------|-----------------|----------|
| Sales Rep (NV) | S01 · S03 · S07 | Morning worklist → call → log |
| CSKH | S05 · S06 · S03 | Inbox triage → link PSID → close conversation |
| Manager | S08–S12 · S04 | Segments · campaigns · dedup · ads |
| Admin | S13 | Custom fields · tags · users |

**Stack context for porting:**
- Screens → Go `templ` components, server-rendered HTML
- Partials + live updates → `hx-get` / `hx-post` HTMX swaps
- Real-time badges → SSE (`GET /api/sse`)
- Data → SQLite queries replacing `window.DB.*`
- User preferences (theme/font) → server-side user-settings table + session cookie

---

## 2. Design Reference — Do Not Ship HTML

> **The files in `prototype/` are a design reference only.**  
> They run in-browser React (via CDN Babel transpilation) with mock data and no real backend.  
> **Do not ship this HTML to production.** Recreate every screen, panel, modal, and component
> in the target environment (Go + templ + HTMX, or an equivalent SPA if chosen).

The prototype's purpose is to demonstrate:

- Exact visual appearance (layout, colors, typography, spacing, motion)
- Interaction patterns (navigation flow, modal stacking, toast feedback, drag-and-drop)
- Business rule enforcement visible to the user (consent gating, margin display, R4 merge undo)
- Copy and microcopy (Vietnamese; see exact strings in each screen component)

Use the prototype as a **living spec** alongside `ui-spec/` (surface contracts, interaction IDs
`A-Sxx-###`, domain rules R1–R12, states/errors). When the prototype and `ui-spec/` conflict,
prefer the prototype for visual decisions and `ui-spec/` for behavioral rules.

---

## 3. Fidelity

**High-fidelity (hifi).** The prototype renders final colors, typography, spacing, interactions,
and copy. Recreate pixel-faithfully using the Precision design-system tokens. Do not re-derive or
eyeball values — all tokens are listed exactly in [§10 Design Tokens](#10-design-tokens) and in
`_ds/precision-design-system-c4fb20e2-a7c2-4891-8146-ada590b7c2c5/colors_and_type.css`
(canonical source; if any value in this README conflicts with the CSS file, the CSS file wins).

---

## 4. How to Run the Prototype

Open `prototype/retailCRM Prototype.html` **directly from inside this package** — the
`design_system/` folder is co-located so `../design_system/styles.css` resolves automatically.
Needs internet for Google Fonts + CDN React/Babel.

- **Left harness rail** — design-review navigator (not a product feature; see §5).
- **"Clean view"** button in header — hides the harness; `←` / `→` steps through all surfaces.
- **Palette icon** in header — theme / accent / font / density switcher (persists via
  `localStorage("crm_tweaks")`).
- **C01 Sidebar** (the product nav) — switches between everyday screens.
- **Click a customer name** in S01 or S07 → O02 quick preview popover.

---

## 5. Harness vs. Product — KEEP / DELETE

The prototype bundles two distinct layers in the same files. Identify and remove the harness
layer when porting.

### DELETE (harness — design-review tooling only)

| Artifact | File | What it is |
|----------|------|-----------|
| `HarnessRail` component | `app.jsx` | Left surface-list rail listing all 41 surfaces; jump-nav for reviewers |
| `RegRow` · `regActive` | `app.jsx` | Row renderer + active-state logic for harness rail |
| `CleanNav` component | `app.jsx` | Floating ← / → surface flipper; `Esc` exit; `h` hide |
| `SURFACE_ORDER` · `currentSurfaceIdx` · `loadClean` | `app.jsx` | Helpers driving CleanNav |
| "Clean view" button in header | `app.jsx` | Enters clean-view mode |
| `window.REG` object | `registry.js` | `{SURF, GROUPS, launch, count}` — surface metadata for harness |
| `ThemePanel` component + `theme-fab` | `app.jsx` | Design-time theme picker → port to user-prefs API |
| `harnessCollapsed` state + toggle | `app.jsx` | Harness collapsed state |
| `crm_harness` localStorage key | `app.jsx` | Harness collapse persistence |
| All `.harness-*` CSS | `crm-extra.css` | Harness chrome |
| All `.reg-*` CSS | `crm-extra.css` | Registry row chrome |
| All `.clean-*` CSS | `crm-extra.css` | Clean-view chrome |
| `.theme-panel` · `.tweaks-*` · `.theme-sw*` · `.theme-acc*` CSS | `crm-extra.css` | Theme panel chrome |
| `.shell` · `.shell--collapsed` | `app.jsx` + CSS | Outer wrapper that holds harness + app side-by-side |

### KEEP (product — recreate faithfully)

| Artifact | File | Notes |
|----------|------|-------|
| `App` shell (stripped) | `app.jsx` | Keep: header · `Sidebar` · `<main>` · modal stack · toast · `QuickPreview` |
| `Sidebar` **(C01)** | `app.jsx` | Product left nav — groups, badges, user footer |
| `GlobalSearch` **(C02)** | `app.jsx` | Header FTS search with dropdown results |
| `QuickPreview` **(O02)** | `app.jsx` | Customer popover from task/board card |
| `ToastStack` **(O01)** | `helpers.jsx` | Auto-dismiss toast stack |
| All screen components S01–S13 | `screens_*.jsx` | Recreate as templ components |
| All panel components P01–P06 | `screens_360.jsx` | Tab content inside S03 |
| All modal components M01–M14 | `modals.jsx` | Recreate as HTMX dialogs / templ fragments |
| `Icon` function (all 36 glyphs) | `helpers.jsx` | Redraw as inline SVG — same 16px / 1.3-stroke / round-caps spec |
| `Avatar` · `Bdg` · `Chip` · `GroupBadge` · `StatusBadge` | `helpers.jsx` | Badge/chip atoms |
| `Modal` shell · `Field` · `Inp` · `InpSel` · `RadioSet` · `ChkRow` | `helpers.jsx` | Form primitives |
| `AQCard` **(C03)** · `TagChips` **(C04)** · `FilterBar` **(C05)** · `FreshBadge` **(C06)** | `helpers.jsx` | Shared components |
| All formatters: `fmtVND` · `fmtDate` · `relTime` etc. | `helpers.jsx` | Port to Go template functions / JS |
| `THEMES` · `ACCENTS` · `FONTS` · `applyTheme` logic | `app.jsx` | Port as user-prefs API + CSS vars (see §10.12) |
| All **product CSS** in `crm-extra.css` | `crm-extra.css` | See §6 for exact class list |
| `window.DB` | `data.js` | Replace every `DB.*` call with real SQL / API |

---

## 6. CSS Split: crm-extra.css

`crm-extra.css` mixes harness chrome with shared product styles. **Split this file on port.**

### Harness-only CSS (delete)

```
.shell  .shell--collapsed
.harness-rail  .harness-rail--collapsed
.harness-head  .harness-head__id  .harness-head__title  .harness-head__sub
.harness-expand  .harness-expand__label  .harness-dot
.harness-foot  .harness-foot__tag
.reg-groups  .reg-group  .reg-row  .reg-sub  .reg-sub__label
.reg-id  .reg-tag  .reg-search  .reg-search__x
.reg-eyebrow  .reg-count  .reg-empty
.clean-nav  .clean-nav__btn  .clean-nav__label  .clean-nav__sid
.clean-nav__name  .clean-nav__count  .clean-exit-btn
.clean-toggle  .clean-toggle__dot
.theme-panel  .theme-panel__sub
.tweaks-panel__head  .tweaks-panel__title
.tweaks-sec  .tweaks-sec__label  .tweaks-sec--row
.tweaks-opts  .twk  .twk--on
.theme-swatches  .theme-sw  .theme-sw--on  .theme-sw__chip  .theme-sw__name
.theme-accents  .theme-acc  .theme-acc--on  .theme-acc__dot  .theme-acc__name  .theme-fab
```

### Product CSS (keep — port to your stylesheet)

Modal shell · Form primitives · Chip color overrides · Action queue card · Worklist rows ·
Customer 360 topbar/grid · Insight signal grid · Timeline · Notes · Dedup grid/compare ·
Inbox/conversation grid · Tasks board · Segment builder · Campaign/Ads layouts · Settings ·
Quick-preview popover · Toast stack · Avatar · Stat strips.

---

## 7. Surface Groups — 41 Surfaces

### 7.1 Screens (13)

**S01 — Worklist / Dashboard** `Sales Rep`  
Morning task queue from `crm_task` + `wh_action_queue`, sorted by due + priority. KPI strip
(open tasks / done / value-at-stake / P1 count) → task list → freshness footer. Task row: check
to complete, action-type chip (CALL NOW / WIN BACK / REORDER / UPSELL / CROSS-SELL / LOYALTY),
customer name (hover → O02), phone, group badge, rationale, value, due, priority, "Mở hồ sơ".
States: all-done, empty, loading, stale-cache. Rules: R2 · R6 · R8.

**S02 — Customer List & Search** `All`  
FTS5 search (name · phone · code · email); debounce 300ms, target <200ms. 5 value-group segment
cards (GOLD / VIP / SILVER / NEW / All) as quick filters. Table: name, code, phone, group badge,
status badge, owner, last-order → S03. Create new party → M02. Rule: R5 (E.164).

**S03 — Customer 360 Detail** `Sales Rep · CSKH` — hosts P01–P06  
2-column layout. **Left (70%+)**: tab bar (P01 Insight · P02 Đơn hàng · P03 Timeline · P04 Tasks
· P05 Ghi chú · P06 Chat) with count badges; active panel content. **Right sidebar (fixed,
~280px)**: Thông tin cơ bản (name · phone · email · Sapo ID · code · owner) + consent indicator +
Tags (C04, editable) + Custom fields. Topbar: ← back · name · group/status · Ghi log / Task /
Gán NV / Tag buttons. Merged-party warning banner when `is_merged=true`. States: loading,
no-profile, no-insight, merged. Rules: R2 · R3 · R6 · R7 (realized margin only).

**S04 — Dedup Review** `Manager`  
2-column: candidate list (left) / detail compare (right). Candidate row shows matched-names +
match rule (`exact_phone` / `fuzzy_name`). Detail: Party A (surviving, amber inset) vs Party B,
fact comparison rows, Merge A←B → M01 / Reject / Skip. States: no-pending, conflict. Rules:
R4 · R5 · R9.

**S05 — Inbox (Conversations)** `CSKH`  
Messenger inbound triage (read-only v1; R12). Status + assignee filter tabs. 2-column: conversation
list (unread dot + party name or PSID + amber "Chưa link" badge + preview + relative time +
unread count) / preview pane (thread preview + "Mở hội thoại" → S06 + "Gán NV" → M09). Rules:
R6 · R12.

**S06 — Conversation Detail** `CSKH`  
Full Messenger thread (customer-left / agent-right bubbles, ICT timestamps). Input bar **disabled**
(read-only v1). Right sidebar: linked customer mini-card → S03, or unlinked CTA → M11. Actions:
Đổi NV → M09, Ghi note → M08, Đóng → M10. Rules: R6 · R12.

**S07 — Tasks Board** `All`  
Kanban (4 columns: Open / Doing / Done / Cancelled) + list toggle. Drag card between columns →
updates `task.status`. Card: AUTO tag (if from action queue), priority pill, title → S03, customer
name (hover → O02), due, assignee avatar, ✓ Done quick action. Create → M05. Rules: R8 · R11.

**S08 — Segments List** `Manager`  
Table: name · conditions count · type (dynamic/static) · member count (−N consent excluded) ·
updated · status (ready / 0-members / materializing spinner). Create → S09 builder. Rules: R1 · R10.

**S09 — Segment Builder** `Manager`  
2-column. Left: rule editor — AND-joined condition rows [field select · operator · value · remove
×] + "Thêm điều kiện" + live JSON preview. Right (sticky): preview member count + "N bị loại do
consent" + 5-row party preview table. Actions: Hủy / Lưu & Materialize. States: preview-loading,
preview-zero (warn before save), consent-filtered. Rules: R1 · R10.

**S10 — Campaigns List** `Manager`  
Status-filter tabs (draft / active / done). Table: name · segment · objective · channel · targets ·
converted · rate · status → S11. Create → M07. Rules: R1 · R10.

**S11 — Campaign Detail / Targets** `Manager · Sales Rep`  
5-stat strip (Targets / Sent / Responded / Converted / Rate). Revenue attribution caveat. Status
filter → target table: customer → S03, status badge (queued / sent / responded / converted /
skipped), assignee, order code, revenue, "Ghi convert" → M12. Edit → M07, activate button.
States: no-targets, converting. Rules: R1 · R3 · R6 · R11.

**S12 — Ads Tracking** `Manager`  
2-column: left = ad-campaign cards (spend / leads / CPC / CPL) + platform/date filter; right
(sticky) = aggregated totals + expandable lead list (→ S03). Freshness badge (C06). States:
no-data, stale-cache. Rules: R2 · R6.

**S13 — Settings** `Admin · Manager`  
3-section nav: Custom Fields table (+ M13 / edit / delete → O01) · Tags table (+ M14) · Users
table (inline role select). Toast on save.

### 7.2 Panels (6 — tab content inside S03)

| Panel | Tab | Key content | Rules |
|-------|-----|-------------|-------|
| P01 Insight | Insight | Action queue cards (C03) · RFM trio · Signals grid (status / next-purchase / discount-sens / affinity / margin if `has_cogs`) · Freshness bar | R2 · R7 |
| P02 Order History | Đơn hàng | Last-10 orders table (code · ICT date · net revenue · status); total footer; Ghi log button | R2 · R3 · R6 |
| P03 Activity Timeline | Timeline | Type filter (call/note/visit/email/chat/other) + Ghi log; vertical timeline; chat items link → S06 | R6 |
| P04 Tasks | Tasks | Status filter + create; task rows: check-to-done, AUTO tag, edit → M05 | — |
| P05 Notes | Ghi chú | Add-note textarea + submit; note cards with hover reveal edit/delete → O01 | — |
| P06 Conversations | Chat | Status filter; conversation cards → S06; PSID badge for unlinked | R6 · R12 |

### 7.3 Modals (14)

All modals share a `Modal` shell: centered 480px card, scrim with `blur(3px)`, `Esc`/backdrop
close, header / body / actions layout. Primary actions guarded per spec. Success → toast.

| Modal | Trigger | Key behavior |
|-------|---------|--------------|
| M01 Merge Confirm | S04 "Merge" | Checkbox gate required before merge; shows what transfers; R4 snapshot |
| M02 Create Party | S02 "Tạo mới", M11 | Live E.164 preview on phone input; R5 |
| M03 Tag Management | S03 "Tag" | Add/remove tags; overflow "+N"; create new → M14 |
| M04 Assign Owner | S03 "Gán NV" | User radio list |
| M05 Create/Edit Task | S01 · S03 · S07 · P04 | Pre-fills from action queue; past-due warn (not block); P1–P4 |
| M06 Custom Fields Edit | S03 sidebar | Renders fields from `crm_custom_field_def` by type (bool/select/date/text) |
| M07 Create/Edit Campaign | S10 · S11 | Segment picker → shows consent-filtered count; R1 |
| M08 Log Activity | S03 · S06 · P02–P05 | Type radios (call/note/visit/email/chat); note-only mode; R6 |
| M09 Assign Conversation | S05 · S06 | User radio list |
| M10 Close Conversation | S06 | Optional activity log; R6 |
| M11 Link Party | S06 | FTS search for existing party; create new → M02; R5 |
| M12 Record Conversion | S11 | Order-code lookup or manual entry; R11 attribution window |
| M13 Custom Field Def | S13 | Type select → shows options editor for "select" type |
| M14 Create Tag | S13 · M03 | Name + category + tone |

### 7.4 Overlays (2)

**O01 — Confirm / Toast**  
Destructive confirm dialog (small centered card, `min-width: 360px`): used for delete-note,
delete-field, merge. Auto-dismiss toast stack anchored bottom-right: `3200ms`, kinds = success /
info / warn. Rise-in animation `--dur-open`.

**O02 — Quick Customer Preview**  
Popover anchored below the triggering customer-name element (position calculated from
`getBoundingClientRect`). Shows: name · phone · group/status · last purchase date · top affinity ·
queued actions. Primary CTA "Mở hồ sơ đầy đủ" → S03. Click-outside to close. Hosts: S01 · S07.

### 7.5 Components (6)

**C01 — Sidebar Nav** (all screens)  
Fixed-width left nav. Groups: Hằng ngày (S01/S02/S05/S07) · Tăng trưởng (S08/S10/S12) · Quản
trị (S04/S13). Inbox unread badge (sum of `conversation.unread`); Dedup pending badge. User
footer: avatar · name · role · "SERVING · SYNCED" status dot. Updates via SSE.

**C02 — Global Customer Search** (header)  
Input + magnifier. Filters `DB.parties` by name / phone / email / code; max 6 results dropdown.
Enter or first-result click → S03. Click-outside closes. Rule: R5.

**C03 — Action Queue Card** (P01 · S01)  
Card with 2px left accent border in `--accent`. Type chip (urgency: CALL NOW=coral / WIN BACK=amber
/ REORDER=moss / UPSELL=amber / CROSS-SELL=honey / LOYALTY=default), rationale text, value (mono),
"Tạo task" → M05. Compact variant for worklist.

**C04 — Tag Chips** (S02 · S03 · S04)  
Category-colored chips (moss/amber/coral or default). Edit mode: each chip has ✕ remove; "+" add
new. Overflow: "+N more" collapsed chip. Controlled by M03.

**C05 — Filter Bar** (S01 · S02 · S05 · S07 · S10 · S11)  
Faceted selects (dropdown or segmented pills). Shows active filter count. "Xóa" / clear-all
resets all selects. Renders from a prop array of `{key, label, options}`.

**C06 — Freshness Badge** (S01 · S03 · S12 · P01 · P02)  
Reads `refreshed_at` (UTC ISO). Displays ICT datetime + status dot: green = <24h, yellow = 24–48h,
red = >48h (ST-STALE-CACHE). Rule R2: never recompute; only show last-synced timestamp.

---

## 8. Interactions

### 8.1 Navigation / Routing

Prototype state: `{screen, party?, conversation?, campaign?, segment?, tab?}` held in React state +
`localStorage("crm_route")`. `nav(r)` replaces current route, resets modal stack and scroll.

**Port to:** Go router paths (`/customers/:id`, `/conversations/:id/detail`, etc.) +
`hx-push-url` on partial swaps. Panels (P01–P06) → query-param or hash tab on S03 URL.

Modal stack is independent of routing: `openModal(type, ctx)` pushes to an array; `closeModal`
pops. Supports nested modals (M03 → M14, M11 → M02). Port as HTMX `hx-target="#modal-slot"` or
dialog elements.

### 8.2 Drag-and-Drop (S07 Tasks Board)

HTML5 drag-and-drop between 4 kanban columns (Open / Doing / Done / Cancelled). Drop triggers
`task.status` mutation. In production: `hx-post /tasks/:id/status` PATCH + optimistic UI or
server-push.

### 8.3 Merge Confirm + R4 Reversibility

M01 has a **mandatory checkbox** ("Tôi hiểu rằng merge có thể hoàn tác qua log") that must be
checked before the primary "Merge" button enables. This enforces R4 in the UI.

**R4 server requirement:** before executing a merge, the backend **must** write a
`party_merge_log` row containing a full JSON snapshot of both parties (identities, activities,
tasks, conversations, notes, custom fields). The UI must expose an "Undo merge" path that reads
this snapshot. The prototype does not implement undo — it is the backend's responsibility to
support it and a future UI surface to expose it.

### 8.4 Toast System

`toast(msg, kind)` where kind ∈ `{success, info, warn}`. Auto-dismiss after **3200ms**.
Rise-in animation using `--dur-open` (260ms). Multiple toasts stack vertically, newest on top.
Position: fixed bottom-right, `z-index: 300`. Port as a shared event bus or Go SSE push.

### 8.5 CSS Transitions

All transitions use Precision motion tokens — never exceed 260ms:

| Event | Duration | Easing | Property |
|-------|----------|--------|----------|
| Hover on interactive rows | `--dur-fast` 120ms | `--ease-fast` | `background` |
| Button press | `--dur-fast` 120ms | `--ease-fast` | `background` |
| Modal scrim fade in | `--dur-fast` 120ms | `--ease-fast` | `opacity` |
| Modal card slide in | `--dur-open` 260ms | `--ease-open` | `transform + opacity` |
| Toast rise in | `--dur-open` 260ms | `--ease-open` | `transform + opacity` |
| Note-card actions reveal | `--dur-fast` 120ms | `--ease-fast` | `opacity` |
| Page enter | `--dur-open` 260ms | `--ease-open` | `transform + opacity` (class `page-enter`) |

Respect `prefers-reduced-motion`: gate entrance animations with `@media (prefers-reduced-motion: no-preference)`.

### 8.6 SSE Live Events

Connect to `GET /api/sse`. Events to wire:

| Event | Payload | Surfaces | Effect |
|-------|---------|----------|--------|
| `cache.refreshed` | `{table, refreshed_at}` | S01 · S03 · P01 | Refresh freshness badge; optionally reload data |
| `chat.message.received` | `{conversation_id, message_id}` | S05 · S06 | Append message; increment inbox badge |
| `dedup.candidate.created` | `{candidate_id, party_a_id, party_b_id}` | S04 | Increment dedup badge; refresh candidate list |
| `campaign.target.converted` | `{campaign_id, party_id, order_code, revenue_vnd}` | S11 | Refresh stats strip |
| `segment.materialized` | `{segment_id, member_count}` | S08 · S09 | Update member count; hide spinner |
| `party.merged` | `{surviving_party_id, merged_party_id}` | S03 · S04 | Remove resolved candidate; show merged banner |
| `conversation.assigned` | `{conversation_id, assignee_user_id}` | S05 · S06 | Update assignee display |
| `task.due.soon` | `{task_id, party_id, due_at}` | S01 | Highlight task row |

---

## 9. State Management

### Local state (per-screen, ephemeral)

Filters · pagination cursor · selected candidate/conversation/campaign · active tab · checked/done
sets · drag-in-progress · form field values · validation errors.

**Port:** server-rendered initial state + HTMX partial re-renders on user actions. For SPA: local
component state or Zustand slice per screen.

### App-level state

| Key | Prototype location | Production replacement |
|-----|-------------------|----------------------|
| Current route | React state + `localStorage("crm_route")` | Go router + `hx-push-url` |
| Modal stack | React array state | `<dialog>` element stack or HTMX `#modal-slot` |
| Toast queue | React array state | Shared event bus or SSE-delivered |
| Quick-preview anchor | React state (partyId + rect) | JS popover anchoring |
| Tweaks (theme/font/density) | `localStorage("crm_tweaks")` → CSS vars on `<html>` | User-preferences API + session cookie |
| Harness collapsed | `localStorage("crm_harness")` | **DELETE** |
| Clean mode | `localStorage("crm_clean")` | **DELETE** |

### Data layer

`window.DB.*` → replace with API calls:

| Prototype access | Production SQL / endpoint |
|-----------------|--------------------------|
| `DB.parties` | `SELECT … FROM crm_party JOIN crm_customer_profile` |
| `DB.partyById(id)` | `SELECT … FROM crm_party_360 WHERE customer_id=?` (view) |
| `DB.orders[partyId]` | `SELECT … FROM wh_order_hdr WHERE customer_id=?` (cache.db ATTACH) |
| `DB.tasks` | `SELECT … FROM crm_task WHERE assignee=?` |
| `DB.conversations` | `SELECT … FROM crm_conversation` |
| `DB.dedup` | `SELECT … FROM crm_dedup_candidate WHERE status='pending'` |
| `DB.segments` | `SELECT … FROM crm_segment JOIN crm_segment_rule` |
| Insight fields on party | `SELECT … FROM wh_customer_insight WHERE customer_id=?` (cache.db) |
| Action queue on party | `SELECT … FROM wh_action_queue WHERE customer_id=?` (cache.db) |

---

## 10. Design Tokens

**Source of truth:** `_ds/precision-design-system-c4fb20e2-a7c2-4891-8146-ada590b7c2c5/colors_and_type.css`
(linked via `styles.css`). If any value below conflicts with the CSS file, **the CSS file wins**.

### 10.1 Neutral Ink Ramp (warm-gray)

```css
--ink-000: #0a0a0c   /* absolute black                        */
--ink-050: #0e0e10   /* page background                       */
--ink-100: #15151a   /* card / panel surface                  */
--ink-150: #1c1c22   /* raised surface (modals, popovers)     */
--ink-200: #232329   /* hairline border                       */
--ink-300: #2f2f36   /* strong border                         */
--ink-400: #44413c   /* disabled foreground                   */
--ink-500: #6a655d   /* tertiary text                         */
--ink-600: #8a857a   /* secondary text / muted                */
--ink-700: #b4ad9f   /* fg-2                                  */
--ink-800: #d8d2c3   /* fg-1                                  */
--ink-900: #f0ece2   /* primary foreground (warm off-white)   */
```

### 10.2 Accent Colors

```css
/* Amber — primary action, the ONLY clickable accent */
--amber-500: #e8a341
--amber-hi:  #f5b35a   /* hover state  */
--amber-lo:  #b97d23   /* pressed state */
--amber-bg:  #3a2a14   /* chip surface tint */

/* Moss — success, ready, verified */
--moss-500:  #84b577
--moss-bg:   #1d2818

/* Coral — blocking errors */
--coral-500: #e0746c
--coral-bg:  #2b1815

/* Honey — soft warning, pepper hint */
--honey-500: #d4a548
```

### 10.3 Semantic Aliases

```css
--fg:            var(--ink-900)   /* primary text        */
--fg-1:          var(--ink-800)   /* secondary text      */
--fg-2:          var(--ink-700)
--fg-muted:      var(--ink-600)
--fg-tertiary:   var(--ink-500)
--fg-disabled:   var(--ink-400)

--bg-page:       var(--ink-050)
--bg-surface:    var(--ink-100)
--bg-raised:     var(--ink-150)

--border:        var(--ink-200)
--border-strong: var(--ink-300)

--accent:        var(--amber-500)
--accent-hover:  var(--amber-hi)
--accent-press:  var(--amber-lo)

--success:       var(--moss-500)
--warning:       var(--honey-500)
--danger:        var(--coral-500)

/* Finance gain/loss (number direction — never collapse with --accent) */
--gain:          var(--moss-500)
--gain-bg:       var(--moss-bg)
--loss:          var(--coral-500)
--loss-bg:       var(--coral-bg)

--on-amber:      #1a0f02   /* text on amber button background */
--on-accent:     var(--on-amber)
```

### 10.4 Account-Type (value_group) Colors

Drives `GroupBadge` and chip coloring — not global semantic accents:

| value_group | Chip class | Color |
|-------------|------------|-------|
| GOLD | `chip--amber` | `--amber-500` |
| VIP | `chip--amber` | `--amber-500` |
| SILVER | `chip` (default) | `--fg-muted` text |
| NEW | `chip--moss` | `--moss-500` |

Action-type urgency chip mapping (C03):

| Type | Chip class | Color |
|------|------------|-------|
| CALL_NOW | `chip--coral` | `--coral-500` |
| WIN_BACK | `chip--amber` | `--amber-500` |
| REORDER_NUDGE | `chip--moss` | `--moss-500` |
| UPSELL | `chip--amber` | `--amber-500` |
| CROSS_SELL | `chip--honey` (custom) | `--honey-500` |
| LOYALTY_REWARD | `chip` (default) | — |

### 10.5 Themes (surface palette)

Applied via `data-theme` attribute on `<html>`:

| Theme | `data-theme` | Page bg | Surface | Primary fg | Accent default |
|-------|-------------|---------|---------|-----------|----------------|
| Precision (dark) | *(absent)* | `#0e0e10` | `#15151a` | `#f0ece2` | amber |
| Than chì (slate) | `slate` | `#12161d` | `#181d26` | `#eaecf0` | amber |
| Sáng ấm (light) | `light` | `#faf7f0` | `#ffffff` | `#1a1610` | amber |
| Tài chính (finance) | `finance` | `#f5f6f7` | `#ffffff` | `#13161b` | **indigo** `#3a47d6` |

Finance theme re-maps `--gain` to green and `--loss` to red distinct from amber; indigo becomes
the default `--accent`. These are **display-time CSS overrides** — no rebuild needed.

### 10.6 Accent Overrides

Applied via `data-accent` attribute on `<html>` (combine with any theme):

| Accent | `data-accent` | `--accent` value |
|--------|--------------|-----------------|
| Hổ phách (amber) | *(absent)* | `#e8a341` |
| Rêu (moss) | `moss` | `#84b577` |
| Mật ong (honey) | `honey` | `#d4a548` |
| Chàm (indigo) | `indigo` | `#7c83f0` |
| Ngọc (teal) | `teal` | `#4bb3a7` |
| San hô (coral) | `coral` | `#e0746c` |

### 10.7 Typography

#### Font families

```css
--font-display: 'Fraunces', Georgia, 'Times New Roman', serif
--font-body:    'Geist', system-ui, -apple-system, 'Segoe UI', sans-serif
--font-mono:    'Geist Mono', ui-monospace, 'SF Mono', Menlo, monospace
```

The prototype also supports font-pairing tweaks via CSS var override at runtime (no rebuild):

| Pairing | `--font-display` | `--font-body` | `--font-mono` |
|---------|-----------------|--------------|--------------|
| Editorial (default) | Newsreader | Geist | Geist Mono |
| Precision | Fraunces | Geist | Geist Mono |
| Grotesk | Space Grotesk | Geist | Geist Mono |
| Plex | IBM Plex Serif | IBM Plex Sans | IBM Plex Mono |
| Source | Source Sans 3 | Source Sans 3 | JetBrains Mono |

In production implement as user-preference stored server-side; apply by writing the three
`--font-*` vars on `<html style="…">` from the session.

#### Size scale

```css
--fs-display: 64px   --fs-h1: 44px   --fs-h2: 28px   --fs-h3: 22px
--fs-name: 20px      --fs-body: 15px  --fs-body-sm: 13px
--fs-caption: 10.5px --fs-micro: 9.5px
--fs-mono-xl: 32px   /* password-slab / large KPI value */
```

#### Leading & tracking

```css
--lh-display: 1.02   --lh-tight: 1.15   --lh-snug: 1.3   --lh-body: 1.55

--tracking-display: -0.03em   --tracking-tight: -0.02em
--tracking-name: -0.015em     --tracking-body: -0.005em
--tracking-mono: 0.005em      --tracking-caps: 0.22em    --tracking-eyebrow: 0.18em
```

#### Weights

```css
--fw-light: 300   --fw-regular: 400   --fw-medium: 500
--fw-semi:  600   --fw-bold:    700
```

### 10.8 Spacing (4-base scale)

```
sp/0 = 0      sp/1 = 4px    sp/2 = 8px    sp/3 = 12px
sp/4 = 16px   sp/5 = 24px   sp/6 = 36px   sp/7 = 56px   sp/8 = 80px
```

CSS vars: `--sp-0` … `--sp-8`.  
Rule of thumb: sp/1–sp/3 hold a unit together; sp/4–sp/5 separate elements; sp/6–sp/7 separate sections.

### 10.9 Radii

```css
--radii-hairline: 2px    /* chips, tags                          */
--radii-control:  4px    /* buttons, inputs, cards (most common) */
--radii-soft:     8px    /* modals, raised surfaces              */
--radii-pill:     999px  /* status dots, avatars                 */
```

### 10.10 Shadows (two only)

```css
/* Status dot ambient glow — apply as: box-shadow: 0 0 8px <color>66 */
--shadow-status-glow: 0 0 8px;

/* Primary CTA hover — entire button, once per screen */
--shadow-cta-hover: 0 8px 24px rgba(232,163,65,0.20), 0 0 0 1px var(--amber-hi);
```

No card shadow. No modal shadow. Stacking elevation is conveyed through surface color steps
(`--bg-surface` → `--bg-raised`).

### 10.11 Motion

```css
--dur-instant: 0ms    --dur-fast: 120ms    --dur-settle: 200ms    --dur-open: 260ms

--ease-fast:   cubic-bezier(.2,0,.1,1)
--ease-settle: cubic-bezier(.2,.6,.1,1)
--ease-open:   cubic-bezier(.2,.8,.2,1)
```

Maximum transition duration: **260ms**. No bounces, no springs, no decorative loops.

### 10.12 Multi-Theme Mechanism — applyTheme + CSS Vars

```js
// Prototype's applyTweaks() — shows the full switching contract:
root.setAttribute("data-theme",   theme.attr || "");   // or removeAttribute
root.setAttribute("data-accent",  accent.attr || "");  // or removeAttribute
root.setAttribute("data-density", density === "compact" ? "compact" : "default");
root.setAttribute("data-numfont", numfont === "sans" ? "sans" : "mono");
root.style.setProperty("--font-display", font.display);
root.style.setProperty("--font-body",    font.body);
root.style.setProperty("--font-mono",    font.mono);
```

In production: emit these attributes from a Go templ layout template that reads
`user_preferences` from the session. No JS required on first load; JS can apply changes
optimistically on the preferences UI.

`data-density="compact"` tightens padding vars in `app.css`. `data-numfont="sans"` switches
`--num-font` from mono to body for financial figures — apply to `class="mono"` elements that
show numbers.

---

## 11. Assets

**No raster images or external icon library.**

### Icons

All icons are **inline SVG**, drawn in `crm/helpers.jsx` `Icon({ name, size })`. Spec:
- Viewport: 16×16
- Stroke: 1.3px, `round` linecap + linejoin
- Fill: none (outline-only)
- Color: `currentColor` (inherits from parent)

36 glyphs available: `worklist · customers · inbox · tasks · segments · campaigns · ads · dedup
· settings · search · plus · back · chevron · chevdown · close · check · phone · edit · trash ·
tag · filter · clock · money · user · merge · link · doc · warn · bolt · dots · logout ·
external · copy · refresh · palette · (+ more in source)`

When adding new glyphs: draw in the same 16px / 1.3-stroke / round-caps style. Do not import
Lucide, Heroicons, or any filled icon set — the stroke weight and optical style would conflict.

### Brand mark

The header wordmark is typography-only (no SVG file):
```html
<span class="brand__dot"></span>   <!-- small amber dot, CSS-rendered -->
<span class="brand__name">retail<b>CRM</b></span>
```
CSS: `brand__dot` = 6px solid circle, `var(--accent)` fill.

### Fonts (Google Fonts CDN)

| Family | Weights | Use |
|--------|---------|-----|
| Fraunces | 300–500 (+ italic 400–500) | Display / editorial — Precision pairing |
| Geist | 300–700 | Body (all pairings) |
| Geist Mono | 300–700 | Mono numbers, codes, labels |
| Newsreader | 400–500 (opsz 6–72) | Display — Editorial pairing (default) |
| Space Grotesk | 400–700 | Display — Grotesk pairing |
| IBM Plex Serif / Sans / Mono | 400–700 | Display / body / mono — Plex pairing |
| Source Sans 3 | 300–700 | Display + body — Source pairing |
| JetBrains Mono | 300–600 | Mono — Source pairing |

For production: serve Geist + Geist Mono as self-hosted WOFF2 (Vercel OFL). Fraunces and
Newsreader can be loaded from Google Fonts or self-hosted.

---

## 12. File Inventory

```
design_handoff_berich_ui_spec/
├── README.md                         ← this file (self-sufficient developer handoff)
├── FILEMAP.md                        ← surface ID → file → component / CSS class index
├── DESIGN_SYSTEM.md                  ← full Precision token reference (all palettes)
├── design_system/                    ← Precision DS — link styles.css in production
│   ├── styles.css                    entry (@imports the three below)
│   ├── colors_and_type.css           tokens · themes · type scale  ← canonical source
│   ├── PRECISION_GUIDE.md            system authoring guide
│   └── ui_kits/crm/styles/
│       ├── app.css                   shell · tables · tabs · KPIs · badges
│       └── crm.css                   nav · dashboard · toolbar · segment cards
└── prototype/
    ├── retailCRM Prototype.html      ← entry (open directly; DS path self-contained)
    └── crm/
        ├── data.js                   mock data (parties/orders/tasks/convos/dedup/segments/
        │                             campaigns/ads/fieldDefs/tags/users) on window.DB
        ├── registry.js               surface registry on window.REG (harness + useful SURF map)
        ├── helpers.jsx               formatters · Icon set · badge atoms · Modal/Field/Form
        │                             primitives · ToastStack · C03 AQCard · C04 TagChips
        │                             · C05 FilterBar · C06 FreshBadge
        ├── modals.jsx                M01–M14 + O01 confirm dialog
        ├── screens_lists.jsx         S01 Worklist · S02 CustomerList · S04 Dedup
        ├── screens_360.jsx           S03 Customer360 + P01–P06 panels
        ├── screens_inbox.jsx         S05 Inbox · S06 ConversationDetail · S07 Tasks
        ├── screens_growth.jsx        S08 Segments · S09 Builder · S10 Campaigns
        │                             · S11 CampaignDetail · S12 Ads · S13 Settings
        ├── app.jsx                   App shell · C01 Sidebar · C02 GlobalSearch · router
        │                             · O02 QuickPreview · ThemePanel (harness) · HarnessRail
        └── crm-extra.css             **mixed** — product styles + harness chrome
                                      (see §6 CSS Split for which classes to keep/delete)
```

In production: link `design_system/styles.css` from the Go templ layout template directly.

The `ui-spec/` folder (surface contracts, domain rules, states/errors, generated registry)
is the authoritative behavioral specification. Every surface has a Markdown contract with
interaction IDs (`A-Sxx-###`) and rule references (R1–R12).

---

## 13. Domain Rules Quick Reference

| ID | Name | Applies to | What the UI must do |
|----|------|-----------|---------------------|
| R1 | Consent Gating | S09 · S10 · S11 · M07 | Exclude `consent_contact=false` parties from segments/campaigns; show excluded count |
| R2 | No-Recompute Insight | S01 · S03 · P01 · P02 · S12 | Never recalculate RFM/affinity/margin; always show `refreshed_at` (C06) |
| R3 | Value-Link No-FK | S03 · P02 · S11 | Join `crm.db` ↔ `cache.db` by value (`customer_id` TEXT), not FK |
| R4 | Merge Reversibility | S04 · M01 | Write `party_merge_log` JSON snapshot before merge; expose undo path |
| R5 | Phone E.164 Normalization | S02 · S04 · M01 · M02 | Normalize `0xxx` → `+84xxx` on blur/save; show live preview in M02 |
| R6 | ICT Display Convention | S01 · S03 · S05 · S06 · S11 · S12 | Store UTC ISO-8601; display ICT (UTC+7) everywhere |
| R7 | realized_margin_pct Only | P01 · S03 | Never display `gross_margin_pct`; gate realized margin on `has_cogs=true` |
| R8 | Idempotent Task Generation | S01 · S07 | One task per `action_id`; re-running generator must not create duplicates |
| R9 | Dedup Fuzzy → Candidate Queue | S04 · M01 | Fuzzy match → candidate queue (manual review); exact phone → auto-link only |
| R10 | Segment Consent Re-eval | S09 · S10 | Re-evaluate consent on every materialization; update excluded count |
| R11 | Conversion Attribution Window | S11 · S07 | New order after `campaign.scheduled_at` + party match = conversion |
| R12 | Messenger Read-Only v1 | S05 · S06 | CRM ingests + displays only; no outbound send (Phase 2) |
