# Prompt: Redesign WorkList Filter Bar

> **Target file:** `crm/src/adapters/inbound/web/templates/fragments/_wl_filter_bar.html`
> **Surface:** S01 — Worklist / Việc cần làm hôm nay
> **Stack:** Python/FastAPI + HTMX + Jinja2 + Precision Design System (custom CSS, no Tailwind)

---

## 1. Current Filter Bar — Full Technical Description

### Layout skeleton

```html
<div class="toolbar" id="wl-filter-bar"
     style="flex-wrap:wrap;gap:var(--sp-3);margin-bottom:var(--sp-3);align-items:center;">

  <form id="wl-filter-form" style="display:contents">
    <!-- all controls here -->
  </form>
</div>
```

`.toolbar` is defined in `ds-crm.css`:
```css
.toolbar {
  display: flex; align-items: center; gap: var(--sp-3);
  flex-wrap: wrap; justify-content: space-between;
}
```

The `<form>` uses `display:contents` so its children become direct flex items in the toolbar. This is the key structural trick — **the form is invisible in the layout** and all inputs participate directly in the flex row. `hx-include="#wl-filter-form"` on every control serialises all inputs together on any change.

### 7 current filter controls

| # | Name | HTML | Query param | Default |
|---|------|------|-------------|---------|
| 1 | Ưu tiên (Priority) | `<select>` — Tất cả / Cao / Khẩn | `priority` | `all` |
| 2 | Loại (Action type) | `<select>` — Tất cả + dynamic values; **hidden if `avail` list is empty** | `type` | `""` |
| 3 | Sản phẩm (Product) | `<select>` — Tất cả + 8 core SKUs; **hidden if `prods` empty** | `product` | `""` |
| 4 | Tìm (Search) | `<input type="search">` — debounce 400 ms, min-width 160px | `q` | `""` |
| 5 | 💰 Giá trị cao | `<input type="checkbox" value="1000000">` | `min_value` | `0` (absent) |
| 6 | ✅ Ẩn đã liên hệ | `<input type="checkbox" value="1">` | `hide_contacted` | absent/false |
| 7 | 📋 Có kịch bản | `<input type="checkbox" value="1">` | `has_script` | absent/false |

After a `<span style="flex:1">` spacer:
- **Badge + clear:** `<span class="badge badge--primary">N</span>` + `<a class="btn btn--ghost btn--sm">Xóa filter</a>` — only rendered when `badge_count > 0`.
- Clear fires `hx-get="/worklist/fragment"` with **no params** (resets everything).

### HTMX pattern (same for every control)

```html
hx-get="/worklist/fragment"
hx-target="#worklist-container"
hx-swap="outerHTML"
hx-trigger="change"          <!-- "keyup changed delay:400ms, search" for the text input -->
hx-include="#wl-filter-form"
```

The fragment endpoint returns the full `#worklist-container` replacement, including a fresh filter bar with correct `selected`/`checked` state re-rendered server-side from query params.

### Active filter count

`active_filter_count` is passed in context by the router. It counts filter dimensions that are non-default. The clear button does **not** submit the form — it does a bare `hx-get="/worklist/fragment"` with no params, which the server reads as "all defaults."

### CSS classes actually defined in the design system

The filter bar template references `.input`, `.input--sm`, `.badge`, `.badge--primary`, `.btn--sm` — **none of these are defined in the CSS files**. They are placeholders that currently fall through to browser defaults. This means any redesign can freely define or reuse them without breaking other pages. The classes that **are** defined and relevant:

- **`.toolbar`** — parent flex container (`ds-crm.css`)
- **`.caption`** — Geist Mono, 10.5px, uppercase, tracked (`ds-precision.css`)
- **`.btn`** — inline-flex, body font 14px, rounded 4px (`ds-precision.css`)
- **`.btn--ghost`** — transparent bg, fg-muted color, hover → accent (`ds-precision.css`)
- **`.chip`** — Geist Mono, 10px, uppercase, border (`ds-precision.css`)
- **`.fchip`** — filter chip, dashed border, hover + `.fchip--on` (amber fill) (`ds-crm.css`)
- **`.chips`** — flex row of fchips (`ds-crm.css`)
- **`.fsel`** / **`.fsel__label`** / **`.fsel__field`** — faceted-label + select (`ds-crm.css`)
- **`.bdg`** / **`.bdg--accent`** — badge primitives (`ds-app.css`)

### Design system tokens in use

```
Spacing:  --sp-1=4px  --sp-2=8px  --sp-3=12px  --sp-4=16px  --sp-5=24px  --sp-6=36px
Colors:   --fg-tertiary (muted label)  --fg-muted  --fg-1  --fg
          --bg-surface  --bg-raised  --bg-page
          --border  --border-strong
          --accent (amber #e8a341 default)  --accent-hover
Radii:    --radii-control=4px  --radii-pill=999px  --radii-hairline=2px
Motion:   --dur-fast=120ms  --dur-settle=200ms  --ease-fast
Fonts:    --font-body (Geist)  --font-mono (Geist Mono)  --font-display (Newsreader, VN-safe)
```

---

## 2. Redesign Goals

### Core problems to solve

1. **Visual clutter at rest.** Seven controls in a flat `flex-wrap` row collapse into two or three lines on anything below 1280px. At rest (no filters active) all seven look equally important.

2. **Invisible active state.** The only feedback for "filters are on" is a tiny badge count integer. A user who set a filter three minutes ago has no visual reminder which filters are active without scanning all controls.

3. **Hierarchy mismatch.** A `<select>` (Ưu tiên) and a `<checkbox>` (💰 Giá trị cao) sit at identical visual weight. Neither communicates its role as a filter.

4. **Incoming density crisis.** Two new filters are being added:
   - `strategic_tier` (Phân khúc): 7-value select — customer strategic segment
   - `value_group` (Hạng KH): 4-value select (VIP / GOLD / SILVER / BRONZE)
   
   With these, the bar grows to **9 filter dimensions** (priority, type, strategic_tier, value_group, product, q, min_value, hide_contacted, has_script). A flat row is untenable.

5. **No mobile story.** The current bar wraps ungracefully at small widths.

### Vision statement

> "Compact when clean, expressive when filtered."
>
> At rest the bar should be one slim line. When filters are active the active selections should be legible at a glance without opening anything.

---

## 3. Proposed Design Options

### Option A — Collapsible Drawer (recommended for density)

A single pill button `Bộ lọc (N)` replaces the entire filter bar at rest. Clicking it expands a popover/drawer panel with all filters grouped by category. Active filters are shown as small chips beneath the trigger even when closed.

**Trade-offs:**

| Pro | Con |
|-----|-----|
| Maximum space saving — one line at rest | Two clicks to change a filter (open drawer + interact) |
| Logical grouping teaches the filter taxonomy | Drawer must close on outside-click (small JS) |
| Active state can be expressive (chips under trigger) | First-time discoverability lower |
| Scales to any number of future filters without redesign | |

**Groups inside the drawer:**

- **Ưu tiên & Loại** → Ưu tiên (priority), Loại (type)
- **Phân khúc & Hạng** → Phân khúc (strategic_tier), Hạng KH (value_group)
- **Sản phẩm** → Sản phẩm (product)
- **Tìm kiếm** → Tìm (q)
- **Chế độ** → 💰 Giá trị cao, ✅ Ẩn đã liên hệ, 📋 Có kịch bản (three toggles)

**ASCII wireframe — collapsed (clean state):**

```
┌──────────────────────────────────────────────────────────────┐
│  [☰ Bộ lọc]   [🔍 Tìm kiếm...]                      [Làm mới]│
└──────────────────────────────────────────────────────────────┘
```

**ASCII wireframe — collapsed (3 filters active):**

```
┌──────────────────────────────────────────────────────────────┐
│  [☰ Bộ lọc  3]  [Khẩn ×]  [VIP ×]  [💰 ×]   [Xóa filter]   │
└──────────────────────────────────────────────────────────────┘
```

**ASCII wireframe — drawer expanded:**

```
┌──────────────────────────────────────────────────────────────┐
│  [☰ Bộ lọc  3]  [Khẩn ×]  [VIP ×]  [💰 ×]   [Xóa filter]   │
│  ┌────────────────────────────────────────────┐              │
│  │  ŨU TIÊN & LOẠI                            │              │
│  │  [Tất cả] [Cao] [Khẩn●]   Loại [chọn ▾]  │              │
│  │──────────────────────────────────────────  │              │
│  │  PHÂN KHÚC & HẠNG KH                       │              │
│  │  Phân khúc [chọn ▾]   Hạng KH [VIP● ▾]   │              │
│  │──────────────────────────────────────────  │              │
│  │  SẢN PHẨM                                  │              │
│  │  [Tất cả ▾]                                │              │
│  │──────────────────────────────────────────  │              │
│  │  CHẾ ĐỘ                                    │              │
│  │  [💰 Giá trị cao ●]  [✅ Ẩn đã LH]  [📋] │              │
│  └────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────┘
```

**Implementation hint for the drawer:**  
Use a `<details>` element for zero-JS disclosure. The Worklist bands already use this pattern (`.wl-band`). The active-filter chips beneath the trigger are a separate `<div>` rendered server-side (from the same `filters` context) outside the `<details>`. Inputs inside the drawer still carry the full HTMX attributes — every change fires the fragment reload AND closes the drawer via a small `<script>` or CSS `:has([open])` rule.

---

### Option B — Tag-based Filter Row

Always show active filter values as dismissible pill chips. An `＋ Thêm bộ lọc` button opens a dropdown menu of available filter dimensions. The search box is always visible.

**Trade-offs:**

| Pro | Con |
|-----|-----|
| Active filters are maximally visible at all times | Requires managing a chip-list data model (which dims are active vs. available) |
| Familiar pattern (Gmail, Jira, Linear) | Dropdown menu needs vanilla JS or `<details>` |
| `[+] Thêm bộ lọc` is a clear CTA | Adding a filter is two clicks (open menu → pick dim → set value in a second step) |
| Bar is empty/clean when no filters active | A second-level value picker per dimension adds complexity |

**ASCII wireframe — no active filters:**

```
┌──────────────────────────────────────────────────────────────┐
│  [🔍 Tìm kiếm...]   [＋ Thêm bộ lọc ▾]                      │
└──────────────────────────────────────────────────────────────┘
```

**ASCII wireframe — 3 active filters:**

```
┌──────────────────────────────────────────────────────────────┐
│  [🔍 Tìm kiếm...]  [Khẩn ×]  [VIP ×]  [💰 Giá trị cao ×]   │
│  [＋ Thêm bộ lọc ▾]   ·   Xóa filter                        │
└──────────────────────────────────────────────────────────────┘
```

**`＋ Thêm bộ lọc` dropdown (available dimensions):**

```
┌─────────────────────┐
│  Ưu tiên       ▸   │
│  Loại          ▸   │
│  Phân khúc     ▸   │
│  Hạng KH       ▸   │
│  Sản phẩm      ▸   │
│  ─────────────────  │
│  ☐ Giá trị cao     │
│  ☐ Ẩn đã liên hệ  │
│  ☐ Có kịch bản    │
└─────────────────────┘
```

**Implementation hint:**  
The DS already defines `.fchip` and `.fchip--on` in `ds-crm.css` — these are the exact pill-chip primitives for this pattern. The clear (`×`) on each chip can be a bare `<a>` that fires `hx-get="/worklist/fragment"` with the current params minus that dimension. This requires the server to handle individual-dimension removal URLs (e.g., `?priority=all&product=...` without the cleared param), or the chips can be hidden `<input>` resets (set value to default and trigger form submit).

---

### Option C — Sticky Two-Row Bar

Row 1 is always visible: search + most-used filters (Ưu tiên, three checkboxes). Row 2 starts collapsed and expands to show secondary filters (Loại, Phân khúc, Hạng KH, Sản phẩm). A `+ Lọc nâng cao (N)` toggle button in row 1 opens row 2.

**Trade-offs:**

| Pro | Con |
|-----|-----|
| Primary filters always accessible — zero clicks | Two-row layout takes more vertical space than Option A |
| No overlay/popover to manage | "Primary vs secondary" distinction is subjective and may confuse |
| Simplest HTMX implementation (all inputs always in DOM) | Row 2 CSS animation (slide-down) needs a small JS helper |
| No chip-list to manage (Option B complexity avoided) | Still dense when row 2 is open |

**ASCII wireframe — row 2 collapsed:**

```
┌──────────────────────────────────────────────────────────────┐
│ ROW 1 │ [🔍 Tìm...]  [Ưu tiên ▾]  [💰][✅][📋]  [+ Lọc(0)] │
└──────────────────────────────────────────────────────────────┘
```

**ASCII wireframe — row 2 expanded (2 secondary filters active):**

```
┌──────────────────────────────────────────────────────────────┐
│ ROW 1 │ [🔍 Tìm...]  [Ưu tiên ▾]  [💰][✅][📋]  [▲ Lọc(2)] │
├───────────────────────────────────────────────────────────────┤
│ ROW 2 │ Loại [▾]  Phân khúc [VIP●▾]  Hạng KH [▾]  SP [▾]   │
│       │                                             [Xóa all] │
└──────────────────────────────────────────────────────────────┘
```

**Implementation hint:**  
Row 2 can be a `<details>` or a `<div hidden>` toggled by vanilla JS. All inputs in both rows must remain inside `#wl-filter-form` regardless of row-2 visibility — hidden inputs in a collapsed row still get serialised by HTMX. The `display:contents` form trick is harder here; the form should instead become a flex column wrapper or the two rows should each be separate `<div>`s inside the form (and the form itself should not use `display:contents`).

---

## 4. Technical Constraints for the Implementer

### Non-negotiable HTMX requirements

- All filter inputs **must remain inside** `<form id="wl-filter-form">`.
- Every filter input must carry: `hx-get="/worklist/fragment" hx-target="#worklist-container" hx-swap="outerHTML" hx-include="#wl-filter-form"`.
- The search input trigger must be: `hx-trigger="keyup changed delay:400ms, search"`.
- "Xóa filter" must do: `hx-get="/worklist/fragment"` with **no** `hx-include` (bare GET = all defaults).
- `hx-target="#worklist-container"` and `hx-swap="outerHTML"` — the fragment replaces the entire container div, including a fresh filter bar. Preserved state comes from the server re-rendering `selected`/`checked` from query params.

### No JavaScript frameworks

- Use `<details>` for disclosure (drawer open/close) wherever possible. The `.wl-band` pattern in `ds-extra.css` proves this works in this codebase.
- CSS `:has()` is available in all modern browsers and can drive show/hide: e.g., `details[open] > .drawer-body { display: block }`.
- Vanilla JS is acceptable only for: (a) closing a `<details>` after an HTMX response, (b) active-chip removal URL construction (Option B).
- No Alpine.js, Vue, React, or HTMX extensions beyond the already-loaded `htmx.min.js`.

### Form structure — display:contents trade-off

The current form uses `style="display:contents"` so its children participate directly in the toolbar flex row. This is elegant for the flat single-row layout but breaks for Options A and C where the form needs internal structure.

**If you change the form structure** (remove `display:contents`):
- The form must become a `width:100%` block that acts as the flex container itself, OR
- The `.toolbar` parent must change from `display:flex` to `display:block`, and the form becomes the flex row.
- Either approach is fine — just explain the change in a comment.

### CSS design system rules

- **Only use design tokens** (`var(--*)`) — never hard-code colors, sizes, or shadows.
- Available components you should **reuse** (do not recreate from scratch):
  - `.fchip` + `.fchip--on` — filter chip with active state (ds-crm.css)
  - `.chips` — chip row wrapper (ds-crm.css)
  - `.fsel` + `.fsel__label` + `.fsel__field` — labelled select (ds-crm.css)
  - `.btn`, `.btn--ghost` — buttons (ds-precision.css)
  - `.caption` — Geist Mono 10.5px uppercase tracked (ds-precision.css)
  - `.bdg` + `.bdg--accent` — count badge (ds-app.css)
- The undefined classes `.input`, `.input--sm`, `.badge`, `.badge--primary`, `.btn--sm` can be **replaced** with the above DS primitives — they have no existing definitions to preserve.
- New utility CSS (e.g., drawer positioning, chip-row layout) belongs in `ds-extra.css` under a `/* ── Worklist filter bar ──` section header, following the existing file convention.

### Server-side context (read-only — do not change)

The Jinja2 context passed to the partial:

```
filters             dict  — {priority, types:list, q, min_value, product, hide_contacted, has_script}
available_types     list  — distinct action_type values from UNFILTERED data
core_products       list  — [(key, label), …] for 8 core SKUs
active_filter_count int   — non-default filter count (badge value)
```

**New context variables being added** (not yet in context, will be added when the new filters are wired):
```
strategic_tiers     list  — [(key, label), …] — 7 Phân khúc values
value_groups        list  — [(key, label), …] — [VIP, GOLD, SILVER, BRONZE]
filters.strategic_tier  str — current value (default "")
filters.value_group     str — current value (default "")
```

**When implementing the new filters**, wire them with:
- `name="strategic_tier"` and `name="value_group"`
- Same HTMX attributes as the other selects
- Both are `<select>` controls; do NOT use checkboxes or radio buttons

### Query param contract summary

```
priority         str   — "all" | "high" | "urgent"         default: "all"
type             str   — action_type value or ""            default: ""
strategic_tier   str   — strategic segment key or ""        default: ""
value_group      str   — "VIP" | "GOLD" | "SILVER" | "BRONZE" | ""   default: ""
product          str   — core SKU key or ""                 default: ""
q                str   — free text                          default: ""
min_value        int   — 1000000 when checked; absent = 0   default: 0
hide_contacted   str   — "1" when checked; absent = false   default: absent
has_script       str   — "1" when checked; absent = false   default: absent
```

---

## 5. Acceptance Criteria

Before marking the redesign done, verify all of the following:

**Filter functionality:**
- [ ] All 9 filter dimensions work: priority, type, strategic_tier, value_group, product, q, min_value, hide_contacted, has_script
- [ ] Each control fires an HTMX request on change; the worklist rows update without full page reload
- [ ] Search input debounces 400ms; clears on `type="search"` clear button
- [ ] "Xóa filter" resets all 9 filters to defaults in one click
- [ ] `active_filter_count` badge shows the correct count after any filter change

**HTMX integrity:**
- [ ] All inputs serialised correctly via `hx-include="#wl-filter-form"`
- [ ] Filter state preserved across fragment reloads (query params reflected in `selected`/`checked`)
- [ ] No JS errors in console on filter change or clear

**Visual:**
- [ ] Bar is visually compact when no filters are active
- [ ] Active filters are clearly distinguishable from inactive ones
- [ ] "Xóa filter" / clear button only appears when `active_filter_count > 0`
- [ ] Works in dark theme (default), light theme, and finance theme
- [ ] Works at 1280px and 900px viewport widths without horizontal scroll

**Code quality:**
- [ ] No hard-coded colors or sizes (only `var(--*)` tokens)
- [ ] No new JavaScript frameworks introduced
- [ ] New CSS added to `ds-extra.css` under a clearly labelled section
- [ ] HTML template stays under 200 lines (modularise if needed)
- [ ] Comments retained or updated: context vars, query-param contract, HTMX pattern note

---

## 6. Files to Read and Modify

**Read before writing:**
- `crm/src/adapters/inbound/web/templates/fragments/_wl_filter_bar.html` — current implementation
- `crm/src/adapters/inbound/web/static/ds-crm.css` lines 182–210 (`.toolbar`, `.fsel`) and 327–336 (`.fchip`, `.chips`)
- `crm/src/adapters/inbound/web/static/ds-precision.css` lines 388–450 (`.chip`, `.btn`, `.btn--ghost`)
- `crm/src/adapters/inbound/web/static/ds-extra.css` lines 345–450 (`.wl-band` pattern for `<details>` reuse)

**Modify:**
- `crm/src/adapters/inbound/web/templates/fragments/_wl_filter_bar.html` — primary implementation
- `crm/src/adapters/inbound/web/static/ds-extra.css` — add new CSS under `/* ── Worklist filter bar (S01) ──` heading

**Do NOT modify:**
- Any router or Python file (the redesign is HTML+CSS only)
- `ds-precision.css`, `ds-app.css`, `ds-crm.css`, `app.css` — extend via `ds-extra.css` instead
- `worklist.html` or `worklist_fragment.html` — the container IDs and HTMX targets must stay as-is

---

## 7. Recommendation

**Choose Option A (Collapsible Drawer)** for the initial redesign.

Rationale:
- 9 filters in a flat row is unsustainable. The drawer pattern scales to any future filter additions without structural change.
- The `<details>` element already used in this codebase (`.wl-band` pattern) gives zero-JS disclosure.
- Active-filter chips shown beneath the trigger provide the "expressive when filtered" quality.
- The DS already has `.fchip` / `.fchip--on` — the chips need no new CSS.
- Staff on mobile (900px) get a single-line header and a full-panel filter drawer, which is more usable than a three-row wrapping bar.

If Option A feels too hidden for the team's workflow, Option C (two-row bar) is the easiest incremental improvement with the least structural change.

---

*Written 2026-06-30 · CRM S01 WorkList filter bar redesign planning doc*
