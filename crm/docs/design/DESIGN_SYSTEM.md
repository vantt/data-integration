# Precision Design System — Token Reference

This document is the **complete, exact token reference** for the retailCRM design.
Every value below is what the prototype actually renders. The canonical source is
`design_system/colors_and_type.css` (+ `ui_kits/crm/styles/app.css`, `crm.css`),
re-exported here for convenience.

Everything is driven by CSS custom properties on `:root`, with **theme** and **accent**
swapped by `data-*` attributes on `<html>`:

| Attribute | Values | Effect |
|---|---|---|
| `data-theme` | _(unset = dark)_ · `light` · `finance` | Swaps the whole surface ramp + value colors |
| `data-accent` | _(unset = amber)_ · `moss` · `honey` | Re-points the single action accent |
| `data-density` | _(unset = default)_ · `compact` | Tightens row padding |
| `data-numfont` | _(unset = mono)_ · `sans` | Number/figure font |

> **Accent rule (Precision):** the accent is the **only thing the user clicks**. Semantic
> colors (moss/coral/honey) appear *only* when something is true, wrong, or actionable.
> Never use blue/purple/gradient backgrounds in the dark theme.

---

## 1 · Color — DARK theme (default, `data-theme` unset)

### Ink ramp (warm-gray surfaces, ink-000 → ink-900)
| Token | Hex | Use |
|---|---|---|
| `--ink-000` | `#0a0a0c` | deepest / code bg |
| `--ink-050` | `#0e0e10` | **page base** (`--bg-page`) |
| `--ink-100` | `#15151a` | **card surface** (`--bg-surface`) |
| `--ink-150` | `#1c1c22` | **raised surface** (`--bg-raised`) |
| `--ink-200` | `#232329` | **hairline** (`--border`) |
| `--ink-300` | `#2f2f36` | **strong border** (`--border-strong`) |
| `--ink-400` | `#44413c` | disabled fg (`--fg-disabled`) |
| `--ink-500` | `#6a655d` | tertiary text (`--fg-tertiary`) |
| `--ink-600` | `#8a857a` | secondary text (`--fg-muted`) |
| `--ink-700` | `#b4ad9f` | (`--fg-2`) |
| `--ink-800` | `#d8d2c3` | (`--fg-1`) |
| `--ink-900` | `#f0ece2` | **display fg** warm off-white (`--fg`) |

### Semantic accents
| Token | Hex | Use |
|---|---|---|
| `--amber-500` | `#e8a341` | **primary action / accent** (default) |
| `--amber-hi` | `#f5b35a` | accent hover |
| `--amber-lo` | `#b97d23` | accent pressed |
| `--amber-bg` | `#3a2a14` | amber chip surface tint |
| `--moss-500` | `#84b577` | success · ready · verified · gain |
| `--moss-bg` | `#1d2818` | moss tint |
| `--coral-500` | `#e0746c` | blocking error · loss |
| `--coral-bg` | `#2b1815` | coral tint |
| `--honey-500` | `#d4a548` | warning · pepper hint |
| `--on-amber` | `#1a0f02` | fg on the accent button |

---

## 2 · Color — WARM LIGHT theme (`data-theme="light"`)
Warm paper. Flips the ink ramp meaning; accent stays amber (deepened for paper).

| Token | Hex |
|---|---|
| `--ink-050` (page) | `#f3efe6` |
| `--ink-100` (card) | `#faf7f0` |
| `--ink-150` (raised) | `#ffffff` |
| `--ink-200` (hairline) | `#e5ded0` |
| `--ink-300` (strong) | `#d6cdba` |
| `--ink-400` (disabled) | `#b3a994` |
| `--ink-500` (tertiary) | `#8a8472` |
| `--ink-600` (secondary) | `#6a655a` |
| `--ink-700` | `#4a463d` |
| `--ink-800` | `#2a2823` |
| `--ink-900` (fg) | `#16150f` |
| `--amber-bg` | `#f6e4c4` |
| `--moss-bg` | `#dde9d6` |
| `--coral-bg` | `#f6dcd6` |
| `--gain` / `--gain-bg` | `#3f8557` / `#dde9d6` |
| `--loss` / `--loss-bg` | `#c0453a` / `#f6dcd6` |
| `--on-amber` | `#1a0f02` |

---

## 3 · Color — FINANCE LIGHT theme (`data-theme="finance"`)
Neutral, faintly-cool paper. **Indigo** action accent. Value direction (gain/loss) carries
money in/out so it never collides with the accent.

| Token | Hex |
|---|---|
| `--ink-000` | `#ffffff` |
| `--ink-050` (page) | `#f5f6f7` |
| `--ink-100` (card) | `#ffffff` |
| `--ink-150` (raised) | `#ffffff` |
| `--ink-200` (hairline) | `#e9ebed` |
| `--ink-300` (strong) | `#d7dade` |
| `--ink-400` (disabled) | `#abafb5` |
| `--ink-500` (tertiary) | `#7f848c` |
| `--ink-600` (secondary) | `#565b63` |
| `--ink-700` | `#3a3f46` |
| `--ink-800` | `#23272d` |
| `--ink-900` (fg) | `#13161b` |
| `--indigo-500` (**accent**) | `#3a47d6` |
| `--indigo-hi` (hover) | `#4f5cf0` |
| `--indigo-lo` (press) | `#2c37ad` |
| `--indigo-bg` | `#e9ebfb` |
| `--gain` / `--gain-bg` | `#0f9564` / `#e2f1ea` |
| `--loss` / `--loss-bg` | `#d63b48` / `#fbe1e3` |
| `--warning` | `#c0871f` |
| `--on-accent` | `#ffffff` |

---

## 4 · Accent overrides (combine with any theme)

`data-accent="moss"`
```
--accent:#84b577;  --accent-hover:#9bc78f;  --accent-press:#5f8f54;  --on-amber:#0e1609;
```
`data-accent="honey"`
```
--accent:#d4a548;  --accent-hover:#e2bd6a;  --accent-press:#a98430;  --on-amber:#1a1302;
```
`data-accent` unset → amber (dark/light) or indigo (finance).

### Semantic aliases (theme-independent names used in components)
```
--fg / --fg-1 / --fg-2 / --fg-muted / --fg-tertiary / --fg-disabled
--bg-page / --bg-surface / --bg-raised
--border / --border-strong / --border-amber
--accent / --accent-hover / --accent-press / --on-accent
--success(moss) / --warning(honey) / --danger(coral)
--gain / --gain-bg / --loss / --loss-bg   (value direction — money in/out)
```

---

## 5 · Typography

**Default families** (Precision): display `Fraunces`, body `Geist`, mono `Geist Mono`.

> ⚠ **Vietnamese:** `Fraunces` (variable) mis-positions stacked Vietnamese diacritics
> (e.g. `ầ`, `ế`). The prototype ships **Editorial = `Newsreader`** as the default display
> face for that reason. Use a Vietnamese-clean serif/sans for VN headings.

**Font pairings exposed in the Tweaks panel** (override `--font-display/--font-body/--font-mono`):
| Id | Display | Body | Mono |
|---|---|---|---|
| `editorial` _(default)_ | Newsreader | Geist | Geist Mono |
| `precision` | Fraunces | Geist | Geist Mono |
| `grotesk` | Space Grotesk | Geist | Geist Mono |
| `plex` | IBM Plex Serif | IBM Plex Sans | IBM Plex Mono |

### Size scale
| Token | px | Use |
|---|---|---|
| `--fs-display` | 64 | doc hero |
| `--fs-h1` | 44 | |
| `--fs-h2` | 28 | page titles |
| `--fs-h3` | 22 | card / panel titles |
| `--fs-name` | 20 | profile name |
| `--fs-mono-xl` | 32 | big mono figure |
| `--fs-body` | 15 | body |
| `--fs-body-sm` | 13 | dense / table body |
| `--fs-caption` | 10.5 | eyebrows / labels |
| `--fs-micro` | 9.5 | micro caption |

### Weights · line-height · tracking
```
weights:  300 / 400 / 500 / 600 / 700
line-h:   display 1.02 · tight 1.15 · snug 1.3 · body 1.55
tracking: display -0.03em · tight -0.02em · name -0.015em · body -0.005em
          mono 0.005em · caps 0.22em · eyebrow 0.18em
```
**Eyebrows / captions / table headers:** Geist Mono, UPPERCASE, `letter-spacing` caps/eyebrow.

---

## 6 · Spacing — 4-base scale
```
--sp-0 0 · --sp-1 4 · --sp-2 8 · --sp-3 12 · --sp-4 16
--sp-5 24 · --sp-6 36 · --sp-7 56 · --sp-8 80   (px)
```
sp/1–3 hold a unit together; sp/5–7 separate ideas.
Density compact: `--row-pad-y` 11→6px, `--card-pad` 24→16px.

## 7 · Radii
```
--radii-hairline 2px (chips/tags) · --radii-control 4px (buttons/inputs/cards)
--radii-soft 8px (modals/raised) · --radii-pill 999px (status dots)
```
Most surfaces use **4px**. Precision is sharp on purpose.

## 8 · Shadow — almost shadowless
Only two sanctioned uses:
- **Status dot glow:** `0 0 8px <color>66` (the 7px status pill dot only).
- **Primary CTA hover:** `--shadow-cta-hover` = `0 8px 24px rgba(232,163,65,0.20), 0 0 0 1px <amber-hi>`.

Cards/modals/popovers cast **no** shadow — they sit on a raised ink surface instead.

## 9 · Motion
| Token | Duration | Easing |
|---|---|---|
| `--dur-fast` | 120ms | `cubic-bezier(.2,0,.1,1)` |
| `--dur-settle` | 200ms | `cubic-bezier(.2,.6,.1,1)` |
| `--dur-open` | 260ms | `cubic-bezier(.2,.8,.2,1)` |

No bounces, no springs, nothing over 260ms. `prefers-reduced-motion` is honored.

## 10 · Reusable component classes (from the DS ui-kit)
Lift these rather than re-styling raw HTML:
`app-header` · `brand` · `search` / `search__input` / `search__results` · `crm-nav` /
`crm-nav__item` / `crm-nav__badge` · `crm-page` / `crm-pagehead` · `kpi` / `kpi-grid` ·
`dash-card` · `tbl` (+ `th-sort`, `td-go`, `is-clickable`) · `tabbar` / `tab` · `scard` /
`facts` / `fact` · `timeline` / `tl-item` · `bdg` (`--good/--warn/--bad/--accent`) ·
`chip` (`--moss/--amber/--coral`) · `status` (`--ready/--warn/--blocked`) · `btn`
(`--primary/--secondary/--ghost`) · `caveat` (`--info/--warn/--rule`) · `strip-stats` ·
`segcard` · `pager` · `toolbar` / `fsel` · `skeleton` / `state`.

Prototype-only additions live in `prototype/crm/crm-extra.css` (modal, form fields, kanban,
chat thread, rule builder, tweaks panel) — all built strictly on the tokens above.
