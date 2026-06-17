---
name: UI Surface Port
description: Port a UI surface (screen / panel / modal / component) from a high-fidelity design prototype into the project's server-side template + HTMX stack with pixel-faithful fidelity. Tech-agnostic and path-agnostic — the user supplies two roots (DESIGN_PATH + SPEC_PATH) at invocation; nothing is hardcoded. Works with any template engine (Go templ, Jinja2, ERB, Blade, …). Always read design files first; never guess or invent CSS classes.
---

# UI Surface Port Skill

> **Rule #1 — READ BEFORE CODE.** Every surface already exists as a high-fidelity prototype
> AND a structured spec. Read them both before writing a single line of template code. Implementing
> from memory or description is the root cause of most design mismatches.

> **Rule #2 — TECH- & PATH-AGNOSTIC.** This skill ports *design + behavior*, not a specific language
> or repo layout. The reading protocol, fidelity rules, and spec conventions are fixed. Paths and the
> output stack come from the inputs in §0 — never assume `crm/...` or any literal path.

---

## 0. Inputs (resolve before any work)

### Required — the user provides these two roots at invocation
| Input | What it points to |
|-------|-------------------|
| `DESIGN_PATH` | Root of the **design** material: the high-fidelity prototype (JSX/HTML) + design handoff docs + product CSS |
| `SPEC_PATH` | Root of the **ui-spec**: behavioral contracts (the writing convention below is fixed; only the path varies) |

If either is missing, **ask the user** for it before proceeding — do not guess a path.

### Derived from `DESIGN_PATH` (discover by role; folder layout may vary slightly)
| Handle | Role | How to find |
|--------|------|-------------|
| `PROTOTYPE_DIR` | Source-of-truth prototype components | dir under `DESIGN_PATH` holding `*.jsx`/`*.html` prototype files |
| `FILEMAP` | Surface ID → file → component map | a `FILEMAP*.md` under `DESIGN_PATH` (optional — if absent, grep prototype for the surface) |
| `DESIGN_README` | CSS split + handoff rules | `README*.md` / `DESIGN_SYSTEM*.md` under `DESIGN_PATH` |
| `PRODUCT_CSS` | Product-vs-harness CSS source | the `*-extra.css` (or equivalent) shipped beside the prototype |

### Derived from `SPEC_PATH` (convention is fixed — see §2)
| Handle | Role | Typical name |
|--------|------|--------------|
| `SPEC_INDEX` | Surface index / overview | `00-overview.md` |
| `DOMAIN_RULES` | Project business rules | `*-domain-rules.md` |
| `STATES_DOC` | Empty / loading / error copy | `*-states-and-errors.md` |
| `{SPEC_TYPE_DIRS}` | Per-type spec dirs | `screens/ panels/ modals/ overlays/ components/` |

### Target stack (discover in the current project, or ask if ambiguous)
| Handle | Role |
|--------|------|
| `TEMPLATE_ENGINE` | Output syntax — Go templ / Jinja2 / ERB / Blade / … |
| `TEMPLATE_DIR` | Where ported templates live |
| `FRAGMENT_DIR` | HTMX partials (often `TEMPLATE_DIR/fragments/`) |
| `STATIC_DIR` | Shipped design-system CSS (tokens, shell, components) |
| `PROJECT_CSS` | File where new product CSS classes are added |

> A project may ship **multiple** stacks behind one prototype/spec (e.g. a Go templ stack and a
> Jinja2 stack). Confirm which `TEMPLATE_ENGINE`/`TEMPLATE_DIR` to port into before coding.

Throughout this doc, `{HANDLE}` = the value resolved above. **No literal repo paths appear below.**

---

## 1. Source of Truth Hierarchy

| Priority | Source | Use for |
|----------|--------|---------|
| 1 (visual) | `{PROTOTYPE_DIR}/*` | Layout, CSS classes, copy, component structure, interaction micro-states |
| 2 (behavioral) | `{SPEC_PATH}/{type}/{ID}-*.md` | Business rules, interaction IDs, domain rules, states, error copy |
| 3 (conflict) | — | Prototype and spec conflict → **prototype wins for visual; spec wins for behavioral** |

---

## 2. Five-Step Reading Protocol

Execute **before writing any template code**. Identical for every target stack and every project.

### Step 1 — Locate the surface
Read `{FILEMAP}` → get prototype **file** + **component name** for your surface ID.
If `{FILEMAP}` doesn't exist, grep `{PROTOTYPE_DIR}` for the surface ID / component name.

### Step 2 — Read the ui-spec contract
File: `{SPEC_PATH}/{screens|panels|modals|overlays|components}/{ID}-*.md`. Extract:
- Regions / layout structure
- Interaction IDs (e.g. `A-Sxx-###`) and what they trigger
- Referenced domain rules → cross-check `{DOMAIN_RULES}`
- States (loading / empty / error) and their copy
- Data fields displayed

### Step 3 — Read the prototype component
Grep the component function in its prototype file, read start→end. Extract:
- **Exact CSS class names** — copy verbatim, never invent variants
- **Exact copy** (incl. localized text) — headings, labels, buttons, empty states, errors
- **DOM structure** — nesting, element types, layout patterns
- **Conditional rendering** (`{cond && …}`) → target-engine `if`
- **List rendering** (`.map()`) → target-engine `for`
- **Event handlers** (`onClick`/`onSubmit`) → HTMX attributes

### Step 4 — Read product CSS
For any class NOT in `{STATIC_DIR}`, look in `{PRODUCT_CSS}`. Read `{DESIGN_README}` (CSS-split
section) first to know which classes are **product** (keep) vs **harness** (delete).
Harness-only classes (prototype scaffolding) must **never** be ported — confirm the exact set in `{DESIGN_README}`.

### Step 5 — Check applicable domain rules
If the spec references domain rules, read them in `{DOMAIN_RULES}` and enforce each visually
(e.g. a rule "never expose metric X" → the template must omit X).

---

## 3. Translation: Prototype JSX → `{TEMPLATE_ENGINE}`

Map JSX **concepts** to your engine. Concepts are universal; only syntax differs. Translate by
concept — never blind find-replace.

### Concept map (universal)
| JSX | Template concept |
|-----|------------------|
| `{cond && <El/>}` | conditional block |
| `{cond ? <A/> : <B/>}` | if / else |
| `{items.map(i => …)}` | for-loop |
| `className="foo"` | `class="foo"` (verbatim) |
| `style={{color:'red'}}` | `style="color:red"` |
| `{variable}` | interpolation |
| `{fmtX(v)}` | format helper / filter / func |

### Syntax per engine (examples)
| Concept | Jinja2 | Go templ |
|---------|--------|----------|
| if | `{% if c %}…{% endif %}` | `if c { … }` |
| if/else | `{% if c %}…{% else %}…{% endif %}` | `if c { … } else { … }` |
| for | `{% for i in items %}…{% endfor %}` | `for _, i := range items { … }` |
| interpolate | `{{ variable }}` | `{ variable }` |
| format | `{{ v \| fmt_x }}` | `{ fmtX(v) }` |

> ERB (`<%= %>`), Blade (`@if/@foreach/{{ }}`), etc. follow the same concept map.

### Interaction (HTMX — engine-independent)
| React | HTMX |
|-------|------|
| `nav({screen, id})` | `<a href="/…/{id}">` |
| `openModal('Mxx', ctx)` | `hx-get="/modals/mxx?ctx=…" hx-target="#modal-slot"` |
| mutation | `hx-post="/…" hx-swap="outerHTML"` |
| inline search/filter | `hx-get="…" hx-trigger="input delay:300ms"` |
| tab switch | `hx-get="/…/tabs/{tab}" hx-target="#tab-panel"` |
| loading indicator | `class="htmx-indicator"` |

### Icons
Inline SVG only. Match the prototype's icon spec exactly (viewBox, stroke width, linecap/linejoin,
fill, color). Find paths in the prototype's `Icon()` helper. **Never** use an external icon library.

---

## 4. Design Fidelity Rules (tech-agnostic)

### 4.1 CSS — exactly what the prototype uses
- Copy class names **character-for-character**. Never rename (`cell-strong` ≠ `cell--strong`) or
  abbreviate (`scard` not `stat-card`). When unsure, grep the class in `{STATIC_DIR}` / `{PRODUCT_CSS}`.

### 4.2 Tokens — never hardcode values
```css
/* WRONG */ color:#e8a341; padding:16px; border-radius:4px;
/* RIGHT */ color:var(--accent); padding:var(--sp-4); border-radius:var(--radii-control);
```
(Use whatever token names the project's `{STATIC_DIR}` actually defines.)

### 4.3 Typography — use the project's token classes
e.g. eyebrow (`caption`), mono numbers (`mono`), muted secondary (`muted`), cell + sub-line — read
them from `{STATIC_DIR}`; do not invent.

### 4.4 Surface markers (mandatory)
1. A surface banner as **line 1**, in the engine's comment syntax:
   - Jinja2: `{# @surface ID · Name | @source {SPEC_PATH}/… | @kind TYPE #}`
   - Go templ: `// @surface ID · Name — @source {SPEC_PATH}/… — @kind TYPE`
2. `data-surface="ID"` on the **outermost element** of screen/panel roots.
3. HTMX partials: banner only, no `data-surface`.

### 4.5 Copy
Localized copy must match the prototype **exactly** — spelling, punctuation, diacritics. Microcopy
(empty states, errors, button text) is part of the design.

### 4.6 Motion
Use the project's duration/easing tokens. Modals animate in, toasts rise in, hovers transition fast.
Keep it subtle (≤ ~260ms), no bounces.

---

## 5. Surface Taxonomy (convention)

| Type | Prefix | Spec dir |
|------|--------|----------|
| Screen | `S` | `screens/` |
| Panel | `P` | `panels/` |
| Modal | `M` | `modals/` |
| Overlay | `O` | `overlays/` |
| Component | `C` | `components/` |

ID counts and the surface→prototype-file mapping are **per project** — read them from `{FILEMAP}`
(or discover in `{PROTOTYPE_DIR}`). Do not assume a fixed range.

---

## 6. Implementation Checklist

**Reading**
- [ ] `{FILEMAP}` (or discovered) for component name + prototype file
- [ ] ui-spec markdown for the surface
- [ ] Prototype component read in full
- [ ] `{PRODUCT_CSS}` for any component-specific product CSS

**Structure**
- [ ] Surface banner is line 1 (engine comment syntax)
- [ ] `data-surface="ID"` on root element (screens/panels only)
- [ ] DOM nesting matches prototype

**Fidelity**
- [ ] CSS class names copied verbatim
- [ ] No hardcoded color/size values — only token vars from `{STATIC_DIR}`
- [ ] Localized copy matches prototype exactly
- [ ] Icons inline SVG per prototype spec, not external lib
- [ ] Empty/loading/error states per `{STATES_DOC}`

**Behavior**
- [ ] Referenced domain rules from `{DOMAIN_RULES}` enforced visually
- [ ] HTMX interactions wired (navigation, modals, partials, forms)

**CSS**
- [ ] New product CSS classes added to `{PROJECT_CSS}`
- [ ] No harness-only classes used (per `{DESIGN_README}`)

---

## 7. Common Mistakes to Avoid

| Mistake | Correct approach |
|---------|-----------------|
| Assuming a path like `crm/docs/...` | Use `{DESIGN_PATH}`/`{SPEC_PATH}` from §0; ask if missing |
| Inventing CSS classes from description | Read prototype, copy exact class names |
| Find-replace JSX→template syntax | Translate by **concept** (§3) |
| Hardcoding `16px` / hex colors | Use the project's token vars |
| Building a modal from scratch | Reuse the prototype's Modal shell/pattern |
| Assuming a fixed surface ID range | Read `{FILEMAP}` / discover in `{PROTOTYPE_DIR}` |
| Porting harness scaffolding CSS | Keep only product classes per `{DESIGN_README}` |

---

## 8. Resolution Worksheet (fill at start of work)

```
# Required (from user)
DESIGN_PATH   = <user-provided>
SPEC_PATH     = <user-provided>

# Discovered under DESIGN_PATH
PROTOTYPE_DIR = …            (dir with *.jsx/*.html prototype)
FILEMAP       = …            (FILEMAP*.md, or "absent → grep prototype")
DESIGN_README = …            (README/DESIGN_SYSTEM — CSS split rules)
PRODUCT_CSS   = …            (*-extra.css)

# Discovered under SPEC_PATH (fixed convention)
SPEC_INDEX    = 00-overview.md
DOMAIN_RULES  = *-domain-rules.md
STATES_DOC    = *-states-and-errors.md
SPEC_TYPE_DIRS= screens/ panels/ modals/ overlays/ components/

# Target stack (current project — discover or ask)
TEMPLATE_ENGINE = …          (templ / Jinja2 / ERB / Blade / …)
TEMPLATE_DIR    = …
STATIC_DIR      = …          (tokens + design-system CSS)
PROJECT_CSS     = …          (project overrides)
```
