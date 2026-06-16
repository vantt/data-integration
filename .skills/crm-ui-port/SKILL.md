---
name: CRM UI Port
description: Port a retailCRM surface (screen / panel / modal / component) from the React prototype into the Python Jinja2 + HTMX stack with pixel-faithful fidelity. Always read design files first — never guess or invent CSS classes.
---

# CRM UI Port Skill

> **Rule #1 — READ BEFORE CODE.** Every surface already exists as a high-fidelity React prototype
> AND a structured spec. Read them both before writing a single line of Jinja2. Implementing from
> memory or description is the root cause of most design mismatches.

---

## 1. Source of Truth Hierarchy

| Priority | Source | Use for |
|----------|--------|---------|
| 1 (visual) | `crm/docs/design/prototype/crm/*.jsx` | Layout, CSS classes, copy, component structure, interaction micro-states |
| 2 (behavioral) | `crm/docs/ui-spec/{type}/{ID}-*.md` | Business rules, interaction IDs, domain rules (R1–R12), states, error copy |
| 3 (conflict rule) | — | When prototype and spec conflict: **prototype wins for visual; spec wins for behavioral** |

---

## 2. Five-Step Reading Protocol

Execute these steps **before writing any template code**:

### Step 1 — Look up surface in FILEMAP
Read `crm/docs/design/FILEMAP.md`.
Find the row for your surface ID → get: prototype **file** and **component name**.

### Step 2 — Read the ui-spec contract
File: `crm/docs/ui-spec/{screens|panels|modals|overlays|components}/{ID}-*.md`

Extract:
- Regions / layout structure
- Interaction IDs (`A-Sxx-###`) and what they trigger
- Referenced domain rules (R1–R12) → cross-check `20-domain-rules.md`
- States (loading / empty / error) and their copy
- Data fields displayed

### Step 3 — Read the prototype component
Grep the exact component function in the prototype JSX file.
```
grep -n "function S01_\|function P01_\|function M05_" crm/docs/design/prototype/crm/screens_lists.jsx
```
Read from function start to end.

Extract:
- **Exact CSS class names** — copy them verbatim, never invent variants
- **Exact Vietnamese copy** — headings, labels, button text, empty states, error messages
- **DOM structure** — nesting, element types, layout patterns
- **Conditional rendering** — `{condition && ...}` → translate to `{% if %}`
- **List rendering** — `.map()` → translate to `{% for %}`
- **Event handlers** — `onClick` / `onSubmit` → translate to HTMX attributes

### Step 4 — Read product CSS from crm-extra.css
For any CSS class that does NOT exist in `ds-precision.css / ds-app.css / ds-crm.css / ds-extra.css`, it lives in `crm/docs/design/prototype/crm/crm-extra.css`.

Read `crm/docs/design/README.md §6 CSS Split` first to know which classes are product (keep) vs harness (delete).

Classes to **delete** (harness-only — never port these):
```
.shell  .harness-*  .reg-*  .clean-*
.theme-panel  .tweaks-*  .theme-sw*  .theme-acc*  .theme-fab
```

Classes to **keep** (port into your app.css or inline if component-scoped):
- Modal shell, form primitives, chip color overrides, AQCard, worklist rows,
  customer 360 topbar/grid, insight signal grid, timeline, notes, dedup grid,
  inbox/conv grid, tasks board, segment builder, campaign/ads layouts, settings,
  quick-preview popover, toast stack, avatar, stat strips.

### Step 5 — Check the domain rules that apply
If the spec references R1–R12, read the relevant rule in `crm/docs/ui-spec/20-domain-rules.md`
and ensure the template enforces it visually (e.g., R7 = never show `gross_margin_pct`).

---

## 3. Translation Rules: React JSX → Jinja2 + HTMX

### Rendering
| JSX | Jinja2 |
|-----|--------|
| `{condition && <El />}` | `{% if condition %}<El>{% endif %}` |
| `{condition ? <A /> : <B />}` | `{% if condition %}<A>{% else %}<B>{% endif %}` |
| `{items.map(item => ...)}` | `{% for item in items %}...{% endfor %}` |
| `className="foo"` | `class="foo"` |
| `style={{ color: 'red' }}` | `style="color:red"` |
| `{variable}` | `{{ variable }}` |
| `{fmtVND(value)}` | `{{ value \| fmt_vnd }}` |
| `{fmtDate(ts)}` | `{{ ts \| fmt_date }}` |
| `{relTime(ts)}` | `{{ ts \| rel_time }}` |

### Interaction
| React | HTMX |
|-------|------|
| `nav({screen: 'S03', party: id})` | `<a href="/customers/{{ id }}">` |
| `openModal('M05', ctx)` | `hx-get="/modals/m05?ctx=..." hx-target="#modal-slot"` |
| `hx-post` mutation | `hx-post="/..." hx-swap="outerHTML"` |
| Inline search / filter | `hx-get="..." hx-trigger="input delay:300ms"` |
| Tab switch | `hx-get="/customers/{{ id }}/tabs/{{ tab }}" hx-target="#tab-panel"` |
| HTMX loading indicator | `class="htmx-indicator"` (hide by default, show during request) |

### Icons
All icons are inline SVG. Spec: `16×16 viewBox, stroke 1.3, round linecap+linejoin, fill none, color currentColor`.
Find exact paths in `crm/docs/design/prototype/crm/helpers.jsx` `Icon({ name })` function.
**Never use external icon libraries.**

---

## 4. Design Fidelity Rules

### 4.1 CSS — use exactly what the prototype uses
- Copy class names **character-for-character** from the JSX
- Never rename: `kpi-grid` ≠ `kpi_grid`, `cell-strong` ≠ `cell--strong`
- Never invent shorthand: `scard` not `stat-card`
- When in doubt, grep the class in the design system CSS files to confirm it exists

### 4.2 Design tokens — never hardcode values
```css
/* WRONG */
color: #e8a341;
padding: 16px;
border-radius: 4px;

/* RIGHT */
color: var(--accent);
padding: var(--sp-4);
border-radius: var(--radii-control);
```

### 4.3 Typography — use token classes
```html
<!-- eyebrow label -->
<div class="caption">LABEL</div>

<!-- mono number -->
<span class="mono">42,000</span>

<!-- muted secondary text -->
<span class="muted">secondary</span>

<!-- cell with sub-line -->
<td class="cell-strong">Primary<span class="cell-sub">secondary</span></td>
```

### 4.4 Surface markers (mandatory)
Every template file **must** have:
1. `{# @surface  ID · Name\n   @source   path/to/spec\n   @kind     TYPE #}` as **line 1**
2. `data-surface="ID"` on the **outermost element** of screen/panel roots
3. Partials (HTMX fragments): banner only, no `data-surface`

### 4.5 Copy
- Vietnamese copy must match the prototype **exactly** — spelling, punctuation, diacritics
- Microcopy (empty states, error messages, button text) is part of the design

### 4.6 Motion
- Modals: `animation: modalIn var(--dur-open) var(--ease-open)`
- Toasts: rise-in `--dur-open`
- Hovers: `transition: all var(--dur-fast) var(--ease-fast)`
- Never exceed 260ms. No bounces.

---

## 5. Surface Lookup Reference

| ID range | Type | ui-spec dir | Prototype file |
|----------|------|-------------|----------------|
| S01–S13 | Screen | `screens/` | See FILEMAP.md |
| P01–P06 | Panel | `panels/` | `screens_360.jsx` |
| M01–M14 | Modal | `modals/` | `modals.jsx` |
| O01–O02 | Overlay | `overlays/` | `modals.jsx` / `app.jsx` |
| C01–C06 | Component | `components/` | `app.jsx` / `helpers.jsx` |

Screen → prototype file mapping (from FILEMAP.md):
```
S01, S02, S04  → screens_lists.jsx
S03, P01–P06   → screens_360.jsx
S05, S06, S07  → screens_inbox.jsx
S08–S13        → screens_growth.jsx
M01–M14, O01   → modals.jsx
C01, C02, O02  → app.jsx
C03–C06        → helpers.jsx
```

---

## 6. Python Implementation Checklist

Before marking work as done, verify all items:

**Reading**
- [ ] Read FILEMAP.md for component name + prototype file
- [ ] Read ui-spec markdown for the surface
- [ ] Read prototype JSX component in full
- [ ] Read crm-extra.css for any component-specific product CSS classes

**Structure**
- [ ] `{# @surface ... #}` banner is line 1 of the file
- [ ] `data-surface="ID"` on root element (screens/panels only)
- [ ] DOM nesting matches prototype structure

**Fidelity**
- [ ] All CSS class names copied verbatim from prototype
- [ ] No hardcoded color/size values — only `var(--*)` tokens
- [ ] Vietnamese copy matches prototype exactly
- [ ] Icons are inline SVG (16px / 1.3 stroke / round), not external lib
- [ ] Empty/loading/error states implemented per spec §30-states-and-errors.md

**Behavior**
- [ ] Domain rules enforced (R1–R12 as referenced in spec)
- [ ] HTMX interactions wired (navigation, modals, partials, forms)
- [ ] R6: all timestamps displayed in ICT (UTC+7)
- [ ] R7: realized_margin_pct only, gated on has_cogs
- [ ] R5: phone numbers formatted E.164 on display

**CSS**
- [ ] Any new product CSS classes added to `crm/app/internal/adapters/inbound/web/static/app.css`
- [ ] No harness-only CSS classes used (.theme-panel, .harness-*, .reg-*, .clean-*)

---

## 7. Common Mistakes to Avoid

| Mistake | Correct approach |
|---------|-----------------|
| Inventing CSS classes from description | Read prototype JSX, copy exact class names |
| Using only 3 themes when there are 4 | Read THEMES array in app.jsx |
| Using `#3a47d6` for indigo accent | Accent override = `#7c83f0`; finance theme default = `#3a47d6` |
| `data-density="normal"` | Design uses `"comfortable"` as default label; CSS responds to `"compact"` only |
| Setting font via `data-font` attribute | Correct: `root.style.setProperty("--font-display", ...)` inline CSS vars |
| Hardcoding spacing as `16px` | Use `var(--sp-4)` |
| Building modal from scratch | Read `Modal` shell in helpers.jsx + Modal pattern in modals.jsx |
| Forgetting consent exclusion copy | R1: always show "N bị loại do consent" in segments/campaigns |
| Showing gross_margin_pct | R7: show only realized_margin_pct, gated on has_cogs |
| Using `normal` density in JS | Default density key = `comfortable`; apply `data-density="compact"` only when compact |

---

## 8. Project File Paths

```
Design reference:
  crm/docs/design/README.md               — developer handoff, all rules
  crm/docs/design/FILEMAP.md              — surface ID → file → component
  crm/docs/design/prototype/crm/          — JSX prototype (source of truth for visual)
  crm/docs/design/prototype/crm/crm-extra.css   — product + harness CSS (split before use)

UI spec:
  crm/docs/ui-spec/00-overview.md         — surface index
  crm/docs/ui-spec/20-domain-rules.md     — R1–R12
  crm/docs/ui-spec/30-states-and-errors.md
  crm/docs/ui-spec/{screens,panels,modals,overlays,components}/

Python templates:
  crm/python/adapters/inbound/web/templates/          — full page templates
  crm/python/adapters/inbound/web/templates/fragments/ — HTMX partials

Static assets:
  crm/app/internal/adapters/inbound/web/static/ds-precision.css  — tokens
  crm/app/internal/adapters/inbound/web/static/ds-app.css        — shell, tables, tabs
  crm/app/internal/adapters/inbound/web/static/ds-crm.css        — nav, dashboard
  crm/app/internal/adapters/inbound/web/static/ds-extra.css      — modals, fields, kanban
  crm/app/internal/adapters/inbound/web/static/app.css           — project overrides
```
