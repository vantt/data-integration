# Handoff — retailCRM (Internal Retail CRM)

> **Design reference for engineering. Do not ship this HTML.** The files in `prototype/`
> are a clickable HTML/React prototype (in-browser Babel, mock data, no backend). They exist
> to show the intended **look, copy, and behavior** at high fidelity. The deliverable for
> engineering is to **rebuild these surfaces in the target codebase/environment** using the
> bundled Precision design-system CSS as the visual contract — not to embed or serve these
> `.html`/`.jsx` files.

---

## 1 · Overview

A desktop-first internal CRM for a Vietnamese retail business (~10 seats: Sales Rep, CSKH/care,
Manager, Admin). It surfaces **warehouse-computed customer insight** (RFM, action queue, affinity,
realized margin) on top of **CRM-owned data** (parties, tasks, notes, activities, conversations,
segments, campaigns, ad attribution).

- **Intended stack:** Go + templ + HTMX, SQLite (WAL), with a read-only `cache.db` warehouse
  `ATTACH`-ed to `crm.db`. SSE for live events.
- **Two ways to consume this package:**
  1. **templ + HTMX (primary):** each screen/panel/modal becomes a templ component rendered
     server-side; HTMX drives partial reloads; SSE pushes live events; link the Precision CSS
     directly.
  2. **SPA (alternative):** the React in `prototype/crm/*.jsx` is a faithful component map you can
     port 1:1 (it's plain React, no framework lock-in).

**Fidelity: high-fi (hifi).** Final colors, type, spacing, component styling, copy, and
interactions. Recreate pixel-faithfully from the bundled `design_system/` tokens and classes —
do **not** re-derive styling values. Where this README and the source disagree, **the source code
is authoritative** (tokens come verbatim from `design_system/colors_and_type.css`; behavior comes
verbatim from the `.jsx`).

### Run the prototype
Open `prototype/retailCRM Prototype.html` in a browser (needs network for CDN React/Babel +
Google Fonts). Left **Surface harness** rail jumps to any surface. Header **palette** icon = Theme
panel (color + font + density). Header **Clean view** hides the harness for screenshots
(`?clean=1`, then `←/→` to step surfaces, `Esc` to exit).

---

## 2 · Harness vs Product — what to KEEP / DELETE

The prototype deliberately runs in **two separated layers**. Only the product layer ships.

| Layer | Lives in | Port? | Notes |
|---|---|---|---|
| **Surface harness** rail (left, `position:fixed`) — registry-driven access list of every surface | `app.jsx` `HarnessRail`/`RegRow`, `registry.js`, `.harness-*`/`.reg-*` CSS in `crm-extra.css` | **DELETE** | Review chrome only. Generated from `window.REG` so a reviewer can reach any surface. Not a user feature. |
| **Clean view** + floating mini-nav (`←/→`, `Esc`, `h`) | `app.jsx` `CleanNav`, `loadClean`, `.clean-*` CSS | **DELETE** | Screenshot/review tool. There is no infinite canvas here — see §4. |
| **Theme panel** (palette icon → theme/accent/font/density) | `app.jsx` `ThemePanel`, `applyTweaks`, `THEMES/ACCENTS/FONTS` | **OPTIONAL** | Demo of the multi-theme mechanism (6 base themes × 12 accents × 6 font pairings — see §6.4). Keep the *mechanism* (CSS-var theming); drop the in-app picker unless you want a user preference. |
| **C01 Sidebar Nav** (left in-app nav: Hằng ngày · Tăng trưởng · Quản trị) | `app.jsx` `Sidebar`, `.crm-nav` CSS | **KEEP** | Real product nav. Curated daily destinations only — never modals/panels/components. |
| **C02 Global Search** (header) | `app.jsx` `GlobalSearch` | **KEEP** | Product. |
| **App header / brand / context crumb** | `app.jsx` `App` header | **KEEP** | Drop the harness toggle + Clean-view + palette buttons; keep brand, search, screen title, account. |
| **All S/P/M/O/C surfaces** | `screens_*.jsx`, `modals.jsx`, `modal_m08.jsx`, `helpers.jsx` | **KEEP** | The actual product. |
| **Mock data** | `data.js` | **REPLACE** | Swap for real queries/API. |

> **Rule of thumb:** if it exists to *navigate the prototype* (harness rail, clean view, surface
> registry, theme picker), it does not ship. If it's a surface a real user touches, it does.

---

## 3 · Surfaces

The registry (`crm/registry.js`) is the single source of truth for navigation. It currently
declares **44 surfaces**: **15 screens · 6 panels · 14 modals · 3 overlays · 6 components.**
(An earlier snapshot of this package said "37" / "42" — those are stale; trust the live
registry count.) Each surface carries `type`, a Vietnamese label, host(s), and the business-rule
tags it must honor (`R1`–`R14`, catalogued in §4).

### Screens (S01–S15)
- **S01 Worklist / Dashboard** — rep's morning queue: KPI tiles → **WLFilterBar** (redesigned
  two-row sticky filter: search + mode toggles on row 1, collapsible advanced selects on row 2,
  active-filter count pill — in `wl_filter.jsx`, replaces the generic C05 here) → task list (check-to-
  complete · action-type chip or `AUTO` · task_kind tag · customer (hover → O02) · value `đ` · due ·
  priority; row title click → S15). States: all-done, empty, loading, stale-cache. _R2, R6, R8._
- **S02 Customer List & Search** — segment cards (GOLD/VIP/SILVER/NEW/All) → toolbar (FTS + facets)
  → results table → pager → row arrow to S03. _R5 (phone E.164)._
- **S03 Customer 360** — 2-col: LEFT tab bar (Insight·Đơn·Timeline·Tasks·Ghi chú·Chat) hosting
  P01–P06; RIGHT sticky info panel (basics + consent · tags · custom fields). Topbar actions →
  M03/M04/M05/M08. _R2, R3, R6, R7._
- **S04 Dedup Review** — candidate list + A↔B compare; **Merge A←B → M01** / Reject / Skip.
  _R4 (merge reversible), R5, R9._
- **S05 Inbox** — Messenger triage (read-only v1): list + preview pane → S06, Gán NV → M09.
  _R6, R12._
- **S06 Conversation Detail** — thread (customer/agent bubbles, ICT times), disabled input
  (read-only v1), linked-customer card or "Chưa link" → M11; Đóng → M10. _R6, R12._
- **S07 Tasks Board** — List/Board toggle; **Board = 4 columns with HTML5 drag-and-drop** between
  Open/Doing/Done/Cancelled; task title click → S15. _R8, R11._
- **S08 Segments List** → **S09 Segment Builder** (visual AND-rule editor + live JSON preview +
  match count − consent-filtered). _R1, R10._
- **S10 Campaigns List** → **S11 Campaign Detail / Targets** (stat strip + target table, Ghi convert
  → M12). _R1, R3, R6, R11._
- **S12 Ads Tracking** — ad cards + sticky stats panel; attributed revenue caveat. _R2, R6._
- **S13 Settings** — Custom Fields (→ M13) · Tags (→ M14) · Users (inline role). _O01 saved toast._
- **S14 Call Mode / Strategy Cockpit** — full-bleed calling cockpit (no C01 sidebar on this screen).
  Session is **customer-grained, not task-grained** — S15 "Vào phiên gọi" launches this same
  screen rather than a per-task cockpit. _R1, R2, R6, R14._
- **S15 Task Detail** *(new)* — the **task lifecycle owner** (`open → doing → done` /
  `cancelled`), reached from S07, P04, O02, worklist rows, or a direct link. Header (title · kind
  tag · priority · overdue flag) → status banner (done/cancelled) → lifecycle rail with actions
  (Bắt đầu / Sửa / Hoãn → O03 / Huỷ) → **body that switches on `task_kind`**, read directly off
  the task record (never re-derived at render time):
  - `contact` → provenance/rationale block, customer summary, **"Vào phiên gọi" → launches S14**
    (the customer's shared call session, not an embedded per-task cockpit), contact-attempt
    history.
  - `internal` → minimal customer facts + tool shortcuts (360 / sửa thông tin / thêm tag) +
    checklist + internal note.
  - `generic` → description + checklist + links + note (no customer block).

  Below the body, a shared **activity log** merges `task.log` with contact attempts. A sticky
  close-bar ("Ghi log & hoàn thành") opens M08 to log the closing activity and marks the task
  done. _R6._

### Panels — hosted inside S03 (P01–P06)
P01 Insight (action queue C03 + RFM + signals + freshness) · P02 Order History (last-10, net
revenue, no margin%) · P03 Activity Timeline (chat items → S06) · P04 Tasks (check-to-done, edit →
M05, postpone → O03) · P05 Notes (→ M08 note-only, delete → O01) · P06 Conversations (→ S06).

### Modals (M01–M14) — open on their host screen
M01 Merge Confirm (checkbox-gated) · M02 Create Party (E.164 live preview) · M03 Tag Mgmt
(→ M14) · M04 Assign Owner · M05 Create/Edit Task (now also opened from S15) · M06 Custom Fields
Edit · M07 Create/Edit Campaign · **M08 Log Activity (redesigned, `modal_m08.jsx` — overrides
`MODALS.M08`)** · M09 Assign Conversation · M10 Close Conversation · M11 Link Party (FTS +
create → M02) · M12 Record Conversion · M13 Custom Field Definition · M14 Create Tag. All share the
`Modal` shell (scrim · Esc/backdrop close · header/body/actions; primary action guarded per spec;
success → toast).

### Overlays & Components
- **O01** Confirm / Toast — destructive-confirm dialog + auto-dismiss toast stack.
- **O02** Quick Customer Preview — popover from a name in S01/S07 → "Mở hồ sơ" → S03.
- **O03** Postpone Task *(new)* — small modal (`modal--sm`) off P04/S07/S15: pick a new due
  date/time; if the task was `doing` it resets to `open`; logs a "hoãn" entry directly (does
  **not** open M08).
- **C01** Sidebar Nav · **C02** Global Search · **C03** Action Queue Card · **C04** Tag Chips ·
  **C05** Filter Bar (faceted selects + clear-all; **S01 uses the dedicated `WLFilterBar` redesign
  in `wl_filter.jsx` instead**) · **C06** Freshness Badge (green <24h / amber 24–48h / red >48h).

---

## 4 · Interactions & behavior

- **Navigation (product):** internal route object `{screen, party?, conversation?, campaign?,
  segment?, tab?, task?}` in `app.jsx`. `nav()` sets route + clears modals/preview. In the target,
  these become real routes / `hx-get` partials. `SCREEN_OF_TAB` maps detail routes (incl. S15→S07)
  back to their C01 parent for active-state.
- **Harness / Clean-view navigation (review-only, do not port):** the harness `go(id)` reads
  `REG.launch[id]` and either routes to a screen/panel, opens a modal on its host
  (`navOpen`), fires a component toast, or opens O02. Clean view steps a flat surface list with
  `←/→`. **There is no infinite-canvas pan/zoom anywhere in this product** — navigation is
  route-based; the only "pan" is keyboard stepping through the surface list in clean view (review
  chrome, not shipped).
- **Drag:** the one real drag interaction is the **S07 Tasks Board** kanban (native HTML5
  drag-and-drop; dropping a card sets `task.status` from the destination column).
- **Confirm / transaction flows:**
  - **M01 Merge Confirm** is **checkbox-gated** and lists exactly what transfers; merge is
    **reversible per R4** (surviving party = A, amber inset; see the exact rule text below —
    R4 is about merge undo, *not* a numeric variance/tolerance check).
  - **M12 Record Conversion** confirms an attributed-revenue transaction (order lookup or manual
    entry) feeding R11 conversion attribution; respect the attributed-revenue caveat (R3).
  - **O01** guards destructive actions (delete note/field — "không thể hoàn tác").
  - **O03** guards a schedule change (postpone), not a destructive one — no checkbox gate, just a
    date/time picker and a status side-effect (`doing`→`open`).
  - Form guards per spec: M02 needs name + valid phone (normalizes to `+84…` on blur); M05 needs
    title + due; M04/M09 need a selection. Past-due = warn, not block.
- **Toasts:** `toast(msg, kind)` pushes onto a queue and auto-dismisses after **3.2 s**
  (`ToastStack`). Kinds: success / info.
- **Transitions:** page-enter `translateY(8px)`; modal/scrim fade+rise; toast rise. **Nothing
  animates longer than 260 ms** (`--dur-open`). Honor `prefers-reduced-motion`.
- **Live (SSE) events to wire server-side:** `cache.refreshed` (S01/S03/P01 freshness + reload),
  `chat.message.received` (S05/S06 + inbox badge), `dedup.candidate.created` (S04 badge),
  `campaign.target.converted` (S11 stats), `segment.materialized` (S08/S09 counts),
  `party.merged` (S03/S04), `conversation.assigned` (S05/S06), `task.status.changed` (S07/P04/S15).

### R1–R14 business rules referenced above

| ID | Name | Applies to | What the UI must do |
|----|------|-----------|---------------------|
| R1 | Consent Gating | S09 · S10 · S11 · M07 | Exclude `consent_contact=false` parties from segments/campaigns; show excluded count |
| R2 | No-Recompute Insight | S01 · S03 · P01 · P02 · S12 | Never recalculate RFM/affinity/margin; always show `refreshed_at` (C06) |
| R3 | Value-Link No-FK | S03 · P02 · S11 | Join `crm.db` ↔ `cache.db` by value (`customer_id` TEXT), not FK |
| R4 | **Merge Reversibility** | S04 · M01 | Write `party_merge_log` JSON snapshot before merge; expose undo path. (Not a numeric-variance rule — no such rule exists in this product; the checkbox gate + snapshot *is* the full requirement.) |
| R5 | Phone E.164 Normalization | S02 · S04 · M01 · M02 | Normalize `0xxx` → `+84xxx` on blur/save; show live preview in M02 |
| R6 | ICT Display Convention | S01 · S03 · S05 · S06 · S11 · S12 · S15 | Store UTC ISO-8601; display ICT (UTC+7) everywhere |
| R7 | realized_margin_pct Only | P01 · S03 | Never display `gross_margin_pct`; gate realized margin on `has_cogs=true` |
| R8 | Idempotent Task Generation | S01 · S07 | One task per `action_id`; re-running generator must not create duplicates |
| R9 | Dedup Fuzzy → Candidate Queue | S04 · M01 | Fuzzy match → candidate queue (manual review); exact phone → auto-link only |
| R10 | Segment Consent Re-eval | S09 · S10 | Re-evaluate consent on every materialization; update excluded count |
| R11 | Conversion Attribution Window | S11 · S07 | New order after `campaign.scheduled_at` + party match = conversion |
| R12 | Messenger Read-Only v1 | S05 · S06 | CRM ingests + displays only; no outbound send (Phase 2) |
| R14 | AI Script No-Recommend → STOP | S14 (via S15 launch) | `recommended=false` on the approach script drives the S14 STOP state; CRM only reads + shows `refreshed_at`, never recomputes (same no-recompute contract as R2) |

> R13 is not currently referenced by any surface in the registry — omitted rather than guessed at.

---

## 5 · State management

- **Local (per-screen):** filters, pagination, selected row, active tab, checked/done sets, kanban
  drag state, search query, task checklist/close-note (S15) — all `useState` inside each screen
  component. → In the target these become component-local UI state or URL/query params; server
  state arrives via HTMX swaps / API.
- **App-level (`App` in `app.jsx`):** current `route`, modal **stack** (supports M03→M14,
  M11→M02), toast queue, O02 preview anchor, and the Tweaks object
  `{theme, accent, font, density, numfont}`. → Map route to a router, modal stack to a modal
  service/route, toasts to a notification store.
- **Persistence (localStorage — all prototype conveniences):** `crm_tweaks`, `crm_route`,
  `crm_harness`, `crm_clean`. → In production, only a user *theme preference* would persist
  (server-side or cookie); the rest is review scaffolding.

---

## 6 · Design tokens (source of truth: `design_system/colors_and_type.css`)

> All values below are verbatim from the CSS. If anything here drifts, the CSS file wins.

### 6.1 Neutrals — warm-gray **ink ramp** (dark / default "Precision" theme)
`--ink-000 #0a0a0c` · `--ink-050 #0e0e10` (page) · `--ink-100 #15151a` (card) ·
`--ink-150 #1c1c22` (raised) · `--ink-200 #232329` (hairline) · `--ink-300 #2f2f36` (strong
border) · `--ink-400 #44413c` (disabled) · `--ink-500 #6a655d` (tertiary) · `--ink-600 #8a857a`
(secondary) · `--ink-700 #b4ad9f` · `--ink-800 #d8d2c3` · `--ink-900 #f0ece2` (display fg).

### 6.2 Brand / semantic accents (use only when something is true, wrong, or actionable)
- **Amber (Precision's primary action):** `--amber-500 #e8a341` · hi `#f5b35a` · lo `#b97d23` ·
  bg `#3a2a14`; `--on-amber #1a0f02` (fg on amber).
- **Moss (success/ready):** `--moss-500 #84b577` · bg `#1d2818`.
- **Coral (blocking error):** `--coral-500 #e0746c` · bg `#2b1815`.
- **Honey (warning/hint):** `--honey-500 #d4a548`.
- **Semantic aliases:** `--success`=moss · `--warning`=honey · `--danger`=coral.
- **Finance/value direction (numbers, NOT actions):** `--gain`=moss / `--loss`=coral (dark);
  re-pointed per theme. Never collapse gain/loss into the action accent.

### 6.3 Account-type / status tones (data-driven, reuse the accents above)
These are **tones**, not new hexes (see `helpers.jsx`):
- **Customer value group** (`GROUP_TONE`): `GOLD`/`VIP` → amber (accent badge) · `SILVER` →
  neutral · `NEW` → moss.
- **Action-queue type** (`ACTION_META`): `CALL_NOW` → coral · `WIN_BACK` → amber · `REORDER` /
  `UPSELL` / `LOYALTY_REWARD` → neutral.
- **Status** (`STATUS_META`): active → good(moss) · at_risk → warn(amber) · churned → bad(coral).
- **Task kind** (`KIND_META`, S15/S07): `contact` → amber · `internal` → moss · `generic` → neutral.

### 6.4 Multi-theme + accent palettes (CSS-variable theming)
Themes flip the ink ramp + value colors; accents repoint `--accent`. Applied by **`applyTweaks(tw)`
in `app.jsx`** (NB: the function is named `applyTweaks`, not `applyTheme`): it toggles
`data-theme` / `data-accent` / `data-density` / `data-numfont` on `<html>` and sets
`--font-display/-body/-mono` inline, then persists to `localStorage`.

- **Base themes (6):** `dark` "Precision" (default DS theme, ink ramp above) · `slate` (`crm-extra.css`,
  cool graphite ramp) · `light` (`app.css`, warm paper: page `#f3efe6`, card `#faf7f0`, gain
  `#3f8557` / loss `#c0453a`) · `finance` (`colors_and_type.css`, neutral-cool ramp + **indigo**
  accent `#3a47d6`, gain `#0f9564` / loss `#d63b48`) · **`berich`** and **`berich-dark`**
  (`berich-theme.css` — see below).
- **⚠ The prototype's actual default is `berich` / jade / Be Vietnam Pro+Spectral**, not the
  Precision dark theme — see `DEFAULT_TWEAKS` in `app.jsx`. If the target product should default
  to plain Precision, change that default explicitly; don't assume dark/amber is "the" theme.
- **Accents (12):** `amber` (Precision default) · `moss #84b577` · `honey #d4a548` (in `app.css`) ·
  `indigo #7c83f0` · `teal #4bb3a7` · `coral #e0746c` (in `crm-extra.css`) · plus 6 **beRich
  gemstone accents**: `jade #13A06E` (beRich's own default) · `gold #C8A04D` · `sapphire #2563C9` ·
  `topaz #D97A34` · `amethyst #7C5CD6` · `garnet #C23B4B`. Each sets `--accent` / `--accent-hover` /
  `--accent-press` / `--on-amber`.

#### The **beRich** theme — a second ported design system, not a Precision variant
`berich-theme.css` is a full foundation remap ("prosperity in jewel tones": ivory paper /
warm-obsidian dark, jade + antique-gold, 5 gemstone accents), targeted at the **same CSS variable
names** the CRM already consumes (`--ink-*`, `--accent`, `--font-*`, `--radii-*`, `--shadow-cta-hover`,
`--bg-vignette`) — the same re-pointing trick the `light`/`finance` themes use, just with a bigger
swing on radii (8/12px vs Precision's 4/8) and an entirely different type family (Spectral +
Be Vietnam Pro + IBM Plex Mono, not Fraunces + Geist). Treat it as **a second visual identity
living alongside Precision**, selectable the same way. It does not appear in the bundled Precision
`colors_and_type.css` — it is CRM-local, defined only in `crm/berich-theme.css`.

### 6.5 Typography
- **Precision roles:** `--font-display` Fraunces (variable opsz; italic = human voice only) ·
  `--font-body` Geist · `--font-mono` Geist Mono (numbers, labels, captions).
- **beRich roles:** display Spectral (serif) · body Be Vietnam Pro · mono IBM Plex Mono.
- **Size scale:** display 64 · h1 44 · h2 28 · h3 22 · name 20 · mono-xl 32 · body 15 · body-sm 13 ·
  caption 10.5 · micro 9.5 px. Reading layer adds title 40 / lede 20 / prose 17. S15 adds title
  27px (Fraunces/display, between h1 and h2).
- **Tracking:** caps/eyebrows ALL-CAPS in mono at `--tracking-caps 0.22em` /
  `--tracking-eyebrow 0.18em`; body `-0.005em`; display `-0.03em`.
- **Tweaks font pairings** (HTML `<link>` + `FONTS` in `app.jsx`): Editorial (Newsreader display) ·
  Precision (Fraunces) · Grotesk (Space Grotesk) · Plex (IBM Plex Serif/Sans/Mono) · Source
  (Source Sans 3 + JetBrains Mono) · **beRich** (Spectral + Be Vietnam Pro + IBM Plex Mono). Each
  pairing = display + body + mono. **No Manrope anywhere in this build.**

### 6.6 Spacing · radii · shadow · motion
- **Spacing (4-base, sp/0–sp/8):** 0 · 4 · 8 · 12 · 16 · 24 · 36 · 56 · 80 px.
- **Radii — Precision:** hairline 2 · control 4 (most surfaces) · soft 8 · pill 999 px.
  **Radii — beRich (overridden per-theme):** hairline 4 · control 8 · soft 12 px.
- **Shadow (only two sanctioned in Precision):** status-dot glow `0 0 8px <color>66`; CTA-hover
  `0 8px 24px amber33, 0 0 0 1px amber-hi`. Cards/modals cast **no** shadow. beRich keeps the same
  two-shadow discipline but re-tints the CTA-hover glow to its own accent.
- **Motion:** instant 0 · fast 120 · settle 200 · open 260 ms; easings `--ease-fast/settle/open`.
  No bounces, no springs, nothing > 260 ms. Applies under both themes.

---

## 7 · Assets

- **Icons:** hand-drawn **inline SVG** only — `Icon` in `crm/helpers.jsx`, 16px box, **1.3 stroke,
  round caps, `currentColor`**. Names in use: worklist, customers, inbox, tasks, segments,
  campaigns, ads, dedup, settings, search, plus, back, chevron, chevdown, close, check, phone,
  edit, trash, tag, filter, clock, money, user, merge, link, doc, warn, bolt, dots, logout,
  external, copy, refresh, palette. **No icon library, no Material Symbols, no emoji.** Redraw new
  glyphs in the same 16px/1.3/round style.
- **Logo / wordmark:** there is **no logo SVG file** — the brand mark is a CSS dot (`.brand__dot`,
  `background: var(--accent)` + glow) next to the text wordmark `retail<b>CRM</b>`
  (`.brand__name`). Recreate in markup, not as an image.
- **Fonts:** all from Google Fonts CDN — Fraunces, Geist, Geist Mono (via the DS `@import`);
  Newsreader, Space Grotesk, Source Sans 3, IBM Plex Serif/Sans/Mono, JetBrains Mono, Be Vietnam
  Pro, Spectral (via the HTML `<link>` tags, for the Tweaks pairings + beRich theme). For
  offline/strict networks, self-host these.
- **Imagery:** none by design (no photography, no illustration). Mock data is fictional
  (`crm/data.js`).

> The task brief mentioned Material Symbols, Manrope, and a logo SVG — **none are present in this
> build.** Per the "source wins" rule, treat the inline-SVG / CSS-dot / Fraunces-Geist(+Spectral/
> Be Vietnam Pro for beRich) reality above as canonical.

---

## 8 · Port note — `crm-extra.css` mixes harness + product

There is **no `shell.css`** in this build; the file that plays that role is
**`prototype/crm/crm-extra.css`**, and it **mixes review-harness chrome with shared product
styling**. Split it when porting:

- **DELETE (harness/review only):** `.harness-rail`, `.harness-*`, `.reg-*`, `.clean-*`,
  `.shell`/`.shell--collapsed` layout that exists to host the harness, and the collapsed-rail
  responsive rules.
- **KEEP (product / shared):** the **theme + accent palettes** (`html[data-theme="slate"]`,
  `html[data-accent="indigo|teal|coral"]`), density rules, `.wlf-*` (S01 filter), `.tkind-tag` /
  `.m05-kind-auto` (task_kind mini-tags — shared between S07 list and S15), and any other
  product-surface styling that isn't harness-specific.

Two newer CSS files are **already clean** and need no splitting:
- **`s15.css`** — S15-only (`.s15-*`), pure product styling.
- **`berich-theme.css`** — the beRich theme remap, pure token definitions, no harness coupling.

The canonical design tokens already live in `design_system/` (`styles.css` → `colors_and_type.css`
+ `ui_kits/crm/styles/app.css` + `crm.css`) — link those directly and lift only the genuinely
product-shared rules out of `crm-extra.css`. Don't carry the harness CSS into production.

---

## 9 · Files

See **`FILEMAP.md`** for the full surface → file → component index. Folder layout:

```
design_handoff/
├── README.md                 ← this file
├── FILEMAP.md                ← surface → file → component index
├── prototype/                ← design reference (DO NOT SHIP — rebuild in target)
│   ├── retailCRM Prototype.html   (entry; links ../design_system/styles.css)
│   └── crm/
│       ├── data.js                mock data (parties, orders, tasks, convos, campaigns…)
│       ├── registry.js            surface registry → harness nav (review-only, 44 surfaces)
│       ├── helpers.jsx            formatters · Icon set · badges · C03–C06 · Modal/Field · Toast
│       ├── modals.jsx             M01–M14 + O01
│       ├── modal_m08.jsx          M08 Log Activity (redesign; overrides MODALS.M08)
│       ├── wl_filter.jsx          S01 WLFilterBar redesign (C05 for Worklist) — load before screens_lists
│       ├── screens_lists.jsx      S01 · S02 · S04
│       ├── screens_360.jsx        S03 + panels P01–P06
│       ├── screens_inbox.jsx      S05 · S06 · S07
│       ├── screens_growth.jsx     S08 · S09 · S10 · S11 · S12 · S13
│       ├── screens_call.jsx       S14 Call Mode
│       ├── screens_task.jsx       S15 Task Detail + O03 Postpone Task
│       ├── app.jsx                shell · C01 nav · C02 search · router · harness · Theme · O02
│       ├── crm-extra.css          ⚠ harness + product styles mixed — split on port (§8); incl. `.wlf-*`, `.tkind-tag`
│       ├── s15.css                S15-only styles — clean, no split needed
│       └── berich-theme.css       beRich theme token remap — clean, no split needed
├── design_system/            ← Precision DS (the visual contract — link directly)
│   ├── styles.css                 entry — @imports the three below
│   ├── colors_and_type.css        tokens + themes + base/reading type  (TOKEN SOURCE OF TRUTH)
│   ├── ui_kits/crm/styles/app.css shell · tables · tabs · KPIs · light theme · accent hooks
│   ├── ui_kits/crm/styles/crm.css nav · dashboard · toolbar · segment cards · filters
│   └── PRECISION_GUIDE.md         the design system's own authoring guide (Precision base theme only — beRich is CRM-local, §6.4)
└── screenshots/              ← reference captures (per-surface in surfaces/, plus M08/S14 studies)
```
