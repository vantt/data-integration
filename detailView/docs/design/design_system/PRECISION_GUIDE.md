# Precision Design System

The visual language of **PassMan** — a Chrome extension that generates and unlocks passwords directly inside Google Sheets. Editorial in tone, sparse in chrome, deliberate in motion. The user is here for one thing: a credential. Everything else stands back.

> **Version:** v0.1 · for PassMan v2.2
> **Wordmark name in product:** *mindVault*
> **Codename of system:** *Precision*

---

## Index

| File / folder | Purpose |
| --- | --- |
| `README.md` | This file. Overview, content fundamentals, visual foundations, iconography. |
| `SKILL.md` | Agent Skill manifest — usable as a Claude Code skill. |
| `colors_and_type.css` | CSS custom properties for the full token system (color, type, spacing, radii, motion). |
| `preview/` | One HTML card per design-system concept — surfaces in the Design System tab. |
| `assets/` | Logos, glyphs, sample binding QR, illustration placeholders. |
| `fonts/` | (empty — using Google Fonts CDN; see *Substitution note* below.) |
| `ui_kits/passman/` | Pixel-faithful recreation of the PassMan Chrome popup with click-through interactivity. |
| `ref/` | Original source files imported from the Claude Design exploration project. |

## Source

Imported from a Claude Design exploration project:
**https://claude.ai/design/p/d952a3e5-ee4e-45dc-b26b-0f7728998fb7**
Originals preserved in `ref/`:

- `ref/precision-refined.jsx` — the canonical component source (tokens, primitives, all 8 popup states, home screen).
- `ref/design-system-doc.jsx` — the long-form visual-doc page.
- `ref/Precision.html`, `ref/DesignSystem.html` — page shells.

No Figma file or production codebase was attached. Everything below was derived from the JSX source. **If a real PassMan production codebase exists, please share it** so the UI kit can match icons, copy, and detail exactly.

---

## Product context

**PassMan** is a Chrome browser extension. The popup attaches to a Google Sheets tab; the user puts a password "recipe" in a cell, clicks the cell, opens the popup, and PassMan deterministically rebuilds the password from the recipe + their session secrets. Three audiences:

1. **Solo users** with a private vault.
2. **Team members** who receive shared profiles bound to a specific sheet (the v2.2 cryptographic anchor is in the recipe itself).
3. **Sysadmins / sharers** who hand a profile + sheet pair to a teammate.

The product feels closer to *editorial design software* than to a password manager — there is no list of "saved sites", no autofill. It's a tool you reach for, use for under three seconds, and put down.

---

## Content fundamentals

### Voice
Quiet, technically literate, lightly anachronistic. The product addresses the user as if they already know what a recipe is — it doesn't onboard, it doesn't sell. When the system *does* speak in a human tone (the pepper hint, error headlines), it sets that line in **Fraunces italic** so the shift is unmistakable.

### Casing
- Sentence case in product copy: *"Open a sheet, then click any cell containing a recipe."*
- **ALL CAPS WITH 0.18–0.22em TRACKING** for captions, labels, and section eyebrows — set in Geist Mono. Never use small caps. Never combine caps with bold.
- Section markers in the doc use a `§ 01` form, not "Section 1".

### Pronouns & address
*You* (the reader / user). The system never refers to itself as "I" or "we". It does refer to itself as *the extension* or *PassMan* when it has to name itself.

### Specific examples (from the source)

| Surface | Sample copy |
| --- | --- |
| Hero | *A design system for a careful tool.* |
| Primary CTA | **Build recipe** &nbsp; *compose with secrets* → |
| Empty state | *Open a sheet, then click any cell containing a recipe.* |
| Pepper hint | *Don't forget your pepper.* |
| Error headline (hard) | *Select a cell with a recipe.* |
| Error headline (soft) | *This recipe is bound to another sheet.* |
| Caption | `GENERATED · 16 CHARS · ~96 BITS · VERIFIED` |
| Footer | *Lock session ⌘L* |

### Microcopy rules
- **No exclamation marks.** Even errors are stated, not shouted.
- **No emoji.** Status uses colored dots; binding uses a sheet ID; verification uses a 1.6-stroke check glyph.
- **No "Oops!" or "Whoops".** Errors begin with the action the user should take, not an apology.
- **No marketing puffery** ("blazing fast", "AI-powered"). The product *is* fast; the copy doesn't say so.
- Numbers are typeset in **Geist Mono** with a thin middle-dot separator: `16 chars · ~96 bits · verified`.
- The first letter of the wordmark *mindVault* is lowercase — always.

### Vibe
Letterpress in spirit. Think *Monocle* magazine column furniture meets a Unix man page. The product feels like a piece of equipment that has been used by a craftsperson, not a piece of "software you signed up for".

---

## Visual foundations

### Color
- **Surfaces:** a 12-step *warm-gray ink* ramp running from `#0a0a0c` (ink/000) to `#f0ece2` (ink/900 — warm off-white). Page base is **ink/050 `#0e0e10`**, raised surface is **ink/100 `#15151a`**.
- **Accents (semantic only):**
  - **Amber `#e8a341`** — primary action, the pepper dot, the v2.2 verification glyph. **Only thing the user clicks.**
  - **Amber Hi `#f5b35a`** — hover.
  - **Amber Lo `#b97d23`** — pressed / muted.
  - **Moss `#84b577`** — success, *Ready* status, *verified* chip.
  - **Coral `#e0746c`** — blocking errors, *Cannot generate* status.
  - **Honey `#d4a548`** — pepper hint dot, soft warning.
- **No blue, no purple, no gradient backgrounds.** Saturation only enters the frame when something is true, wrong, or actionable.

### Type
- **Display:** *Fraunces* — variable opsz, 9..144. 400 regular; italic reserved for human voice.
- **Body:** *Geist* — 300–700.
- **Mono:** *Geist Mono* — 300–700.
- All three are loaded from Google Fonts. See *Substitution note* below.
- The **Italic Fraunces** rule is sacred: italic = the system is speaking like a person. Never italicize body, never use Fraunces below 15 px.

### Spacing — 4-base scale
`0, 4, 8, 12, 16, 24, 36, 56, 80` px → tokens `sp/0`–`sp/8`.

- `sp/1–sp/3` hold a unit together (icon ↔ label, caption ↔ value).
- `sp/5–sp/7` separate ideas (field gap, section break, major rule).

### Backgrounds
- Solid **ink/050** at the page level. No noise, no texture.
- A single **atmospheric vignette** is permitted: a soft radial of `rgba(232,163,65,0.04)` from the upper-right of the popup. It is barely perceptible — it warms the dark without becoming a "gradient".
- No full-bleed photography. No hand-drawn illustration. No repeating pattern.

### Borders & dividers
- **1 px hairlines** at `ink/200` (`#232329`) for ordinary dividers.
- **1 px strong** at `ink/300` (`#2f2f36`) for the password slab and field separators.
- Dashed borders only appear on *capsule rules* inside docs (never in product) — `1px dashed ink/300`.

### Shadow system
Precision is *almost* shadowless. Two permitted uses only:

| When | Spec |
| --- | --- |
| Status dot glow | `0 0 8px <color>66` — only on the 7 px status pill dot. |
| Primary CTA on hover | `0 8px 24px amber33, 0 0 0 1px amberHi` — once per screen at most. |

Card stacking, modals, popovers do **not** cast shadow. They sit on a slightly raised ink surface (ink/100 → ink/150) instead.

### Corner radii
| Token | Value | Use |
| --- | --- | --- |
| `radii/hairline` | 2 px | Chips, tags |
| `radii/control` | 4 px | Buttons, inputs, cards |
| `radii/soft` | 8 px | Raised surfaces, modals |
| `radii/pill` | 999 px | Status indicator dots only |

Most surfaces use **4 px**. Larger radii feel friendly; Precision is sharp on purpose.

### Cards
- Surface: `ink/100` against page `ink/050`.
- Border: `1px solid ink/200`.
- Radius: 4 px (`radii/control`).
- No shadow. No glow.
- Padding: `sp/4`–`sp/5`.
- A "rule strip" variant: same card, but a **2 px left border in amber** introduces an editorial pull-quote / system rule. (This is the *only* sanctioned left-border accent.)

### Hover state
- Buttons: background steps to **amber/Hi**. The shadow turns on. Color is the only signal.
- Ghost links: text color shifts to **amber**. No underline change.
- Cards: do not change on hover.
- Icons: opacity 0.6 → 1.0, with `motion/fast`.

### Press state
- Buttons: background steps to **amber/Lo**. No shrink, no scale transform.
- Ghost links: opacity drop to 0.7.

### Focus state
- A 1 px outline in `amber` at `outline-offset: 2px`. **No focus ring shadow.** Visible only on keyboard navigation.

### Motion
| Token | Duration | Easing |
| --- | --- | --- |
| `motion/instant` | 0 ms | linear |
| `motion/fast` | 120 ms | `cubic-bezier(.2,0,.1,1)` |
| `motion/settle` | 200 ms | `cubic-bezier(.2,.6,.1,1)` |
| `motion/open` | 260 ms | `cubic-bezier(.2,.8,.2,1)` |

**No bounces. No springs. No long fades.** If a transition would last longer than 260 ms, the user is waiting on the system instead of using it. Copy-confirmation flashes a soft amber wash across the password slab for 1.5 s and then resets — that is the most "showy" the system gets.

### Transparency & blur
- The sticky doc header uses `backdrop-filter: blur(12px)` over an 0xF0-alpha ink surface. That's the only blur in the product.
- Chip backgrounds use 50 %-alpha versions of `amberBg` / `mossBg` / `coralBg` over the ink surface, so the badge tone bleeds slightly into the page without becoming a solid plate.

### Imagery & illustration
- The product has *no photography* and *no illustration* by design. Identity lives in type and in three small accent colors. If imagery is ever needed (marketing site, app store hero), it must be **monochrome editorial photography with warm grain** — never stock saturation, never bluish UI screenshots floating in a gradient.

### Layout rules
- Fixed popup width **600 px**, height ~520 px. Designed for the Chrome popup; never stretches.
- A single hairline rule below the header is the only structural element that crosses the popup edge to edge.
- Everything else lives in a single 24 px-padded column.
- The **password slab** is always the visual anchor — Geist Mono 32 px, full-bleed left, copy control flush right, top + bottom hairline.

### Iconography motifs (visual)
- **1.3–1.6 px stroke**, never filled glyphs.
- **No corner caps that aren't `round`.**
- Status pills: a 7 px solid dot with a soft glow — never a checkmark, never a shield.
- The verification glyph is a tiny check at 1.6 stroke (see `assets/glyph-check.svg`).

---

## Iconography

PassMan ships almost no iconography. The few glyphs that exist are **inline SVG drawn from scratch** in the source (`PCopyIcon`, `PCheckTiny`, the settings cog in the header). They are committed in this design system as standalone SVGs in `assets/icons/` and documented in `preview/Iconography.html`.

### Catalogue (everything PassMan currently uses)

| Glyph | Where | Spec |
| --- | --- | --- |
| `copy.svg` | Password-slab copy button | 13 px box, stroke 1.3, round caps. Two-rect "duplicate" shape. |
| `check-tiny.svg` | "verified" chip, "Copied" flash | 11 px box, stroke 1.6, round caps. |
| `cog.svg` | Header settings button | 16 px box, stroke 1.3, two concentric circles + 4-axis ticks. |
| `arrow-right.svg` | Primary CTA | Set in body text as the character `→`, not an icon. *Do not replace.* |
| `dot-status.svg` | Header status pill | A 7 px solid circle with `0 0 8px color66` glow. Drawn in CSS, not SVG. |

### Rules
- **No emoji.** Anywhere. Including in documentation copy. The wordmark uses a tiny solid amber dot in lieu of any decorative mark.
- **No Unicode icon glyphs** as decoration (no ⚙, no 🔒, no ✔). The arrow `→` is the *one* exception because it is set as type in a sentence: `Build recipe →`.
- **No icon library** is used. Lucide / Heroicons / Phosphor would all be too rounded and too fill-heavy for this system. **If new glyphs are needed**, draw them in the same 16 px box, 1.3 stroke, round caps style.
- All icons inherit `currentColor` from their parent. They never carry their own color.

### Iconography substitution
There is no third-party icon set linked from CDN. Drawing new icons by hand is the deliberate default. If a designer absolutely needs a stand-in placeholder, **Lucide** is the nearest stroke-weight match (1.5 px round) — flag the substitution in the file and replace with a hand-drawn glyph before ship.

---

## Substitution note — fonts

The Precision source loads **Fraunces, Geist, and Geist Mono** from `fonts.googleapis.com`. All three are open-source and available there:

- *Fraunces* (Undercase Type, OFL) — https://fonts.google.com/specimen/Fraunces
- *Geist* (Vercel, OFL) — https://fonts.google.com/specimen/Geist
- *Geist Mono* (Vercel, OFL) — https://fonts.google.com/specimen/Geist+Mono

No woff/ttf files have been committed to `fonts/` — the design system loads them from Google Fonts at the CSS level. **If you want the design system to work offline or in a stricter network**, download the static `.ttf`/`.woff2` files from Google Fonts and drop them in `fonts/`, then update the `@font-face` block at the top of `colors_and_type.css`.

---

## How to use this system

1. **Start a new design:** copy `colors_and_type.css` into the page `<head>` and link `<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;1,9..144,400&family=Geist:wght@300..700&family=Geist+Mono:wght@300..700&display=swap" rel="stylesheet">`.
2. **Reach for an existing component:** look in `ui_kits/passman/` first — every popup state is already factored.
3. **Need a new component?** Check it passes the three Precision tests: (a) does it use only ink + amber + one semantic accent? (b) does its motion fit inside 260 ms? (c) can the user understand it without an icon?
4. **Need new copy?** Read it aloud. If it sounds like marketing, rewrite it.
