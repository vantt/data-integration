---
name: ui-spec
description: "Generate, validate, and interpret UI specifications from PRD. Creates machine-readable interaction contracts embedded in human-readable Markdown. Use when building UI spec for any app with ≥20 surfaces or complex domain rules."
license: MIT
argument-hint: "[command] [args] — commands: generate, validate, build, check, interpret, init, add-surface, context"
metadata:
  author: claudekit
  version: "1.0.0"
---

# ui-spec skill

> Core insight: **Prose for humans, structured YAML contract for machines, compiler as trust gate.**
> Each surface file = free-form Markdown + one fenced `yaml {project}-contract` block. Compiler ignores prose; only parses frontmatter + contract block. Drift is impossible by construction.

---

## Commands

### `generate <prd-path> [--output docs/ui-spec]`
Read a PRD and produce a complete UI spec from scratch.

**Pipeline (2-pass):**
1. Read PRD (accepts Markdown, plain text, or structured doc)
2. **Completeness analysis** — warn if missing: screen list, user flows, domain entities, business rules, platforms. User can supplement missing info or skip.
3. **Pass 1 — Skeleton:** generate `spec.config.yaml`, `00-overview.md`, `20-domain-rules.md`, `30-states-and-errors.md`, `15-system-events.md`; create all surface files with frontmatter + prose only (no contract blocks yet)
4. **Pass 2 — Contracts:** read generated surface list → fill `{project}-contract` blocks in each surface file → generate flow files
5. Run `validate` → fix errors → report
6. Run `build` → generate artifacts (`surface-registry.yaml`, `navigation-graph.yaml`, `action-registry.csv`, `coverage-report.md`)

### `init <project-name> [--output docs/ui-spec]`
Scaffold empty spec structure with config, schema, templates, and tools directory.

Creates:
```
docs/ui-spec/
├── spec.config.yaml          # project name, contract tag, surface ID prefixes
├── schema/surface-contract.schema.json
├── tools/                    # extract.mjs, validate.mjs, build.mjs (Node ≥18)
├── templates/                # surface type templates
└── generated/                # build output (gitignore-able)
```

### `check [surface-id]`
Run `validate` + `build`. If `surface-id` provided, validate that single surface in context.

### `validate`
Structural validation only — does not generate artifacts.
Checks: unique action IDs, target resolution, modal exit rules, rule drift, required frontmatter.
Exit non-zero on any error → CI gate.

### `build`
Generate artifacts from validated source files:
- `generated/surface-registry.yaml` — all surfaces with metadata
- `generated/navigation-graph.yaml` — navigate edges between surfaces
- `generated/action-registry.csv` — all action IDs, elements, triggers, targets
- `generated/coverage-report.md` — surface coverage, flow coverage, rule coverage

### `add-surface <type> <id> <name>`
Add a new surface file from the appropriate template.
Types: `screen | panel | modal | overlay | component | flow`
Example: `/ui-spec add-surface modal M05 "Edit Account"`

### `interpret`
Launch runtime wireframe renderer — opens a single HTML file in browser.
- Resolves entry surface from `spec.config.yaml`
- Renders surface as interactive wireframe (parses ASCII layout from prose)
- User clicks elements → resolves interaction → renders target surface
- No server needed; pure HTML + vanilla JS
- Command: `node interpret.mjs --root <spec-root>` or `npm run interpret -- --root <spec-root>`

### `interpret:wf` (wireframe v2 — region-box layout)
Launch wireframe v2 renderer — interactions laid out inside their region boxes.
- **Layout tab (default):** region boxes with action buttons (colored) + reaction chips (dashed ⚡)
- **Blueprint tab:** original hand-authored ASCII layout for 2D reference
- Declared regions with no interactions show "(display only)" dashed box
- Sidebar groups all surfaces by type; click to navigate; overlay surfaces open in a card
- Storyboard + Graph tabs present but disabled (Phase 2/3)
- Output: `generated/wireframe-v2.html` (does not overwrite v1's `wireframe.html`)
- Command: `node interpret-wireframe.mjs --root <spec-root>` or `npm run interpret:wf -- --root <spec-root>`

### `context <surface-or-flow-id>`
Output LLM-ready context block for codegen — surface contract + relevant domain rules + connected surfaces. Use before implementing a specific screen/component.

---

## Methodology (brief)

### Surface file anatomy

```markdown
---
id: S05
type: screen
name: Product List
platforms: [desktop, mobile]
hosts: []
status: active
design_ref: "designs/s05.png"
rules: [R2, R4]
---

# S05 — Product List

## Purpose
(free prose — why this screen exists, user journey context)

## Layout
(ASCII layout, descriptions — compiler ignores all of this)

## Interactions

```yaml crm-contract
interactions:
  - id: A-S05-001
    element: product_row
    trigger: click
    action: navigate
    target: S06
    payload: { product_id: "$product.id" }
  - id: A-S05-002
    element: add_button
    trigger: click
    action: open_overlay
    target: M03
```

## States
(prose or ST-* links)
```

### Surface types
| Type | ID prefix | Key rule |
|---|---|---|
| screen | Sxx | May host panels |
| panel | Pxx | Hosted by screen |
| modal | Mxx | Must have ≥1 close_overlay + ≥1 return_to_invoker |
| overlay | Oxx | Lightweight, no navigation |
| component | Cxx | Emits events only; no navigate/open_overlay |
| flow | Fxx | References existing action IDs only |

### Action IDs
Auto-generated as sequence `A-{SURFACE}-{001,002,...}`. Manual override allowed. IDs are unique across the entire repo. Canvas surfaces use `A-CV-*`. System events use `A-SYS-*`.

### Domain rules
Declared in `20-domain-rules.md` with bidirectional surface mapping. Validator checks that every surface listed under a rule has that rule ID in its frontmatter `rules:` array.

### Component event model
Components only `emit_event`. Host surfaces (screens/panels) listen via `listens_to` in their own contract block. This prevents tight coupling between component and host.

### `region` field (optional)
Interactions may include `region: <region-id>` as a layout hint. If present, the region must appear in the surface frontmatter `regions[]` array. Compiler validates consistency.

---

## Compiler pipeline

```
*.md  --extract.mjs-->  contracts (in-mem)
                          │
                          ├── validate.mjs   (schema + rules)  → exit≠0 on error
                          └── build.mjs      → generated/*
```

Source of truth = `.md` files. `generated/` is output — do not edit by hand, safe to gitignore.

---

## Reader guide

| Role | Read |
|---|---|
| PM | `00-overview.md`, `flows/`, `generated/coverage-report.md` |
| Designer | `screens/`, `panels/`, `modals/`, `components/` |
| Dev / LLM codegen | target surface + `20-domain-rules.md` + `30-states-and-errors.md` |
| QA | `flows/`, `generated/navigation-graph.yaml` |
| Tooling | `generated/*` + contract blocks |

---

## Multi-agent orchestration

When spec size > 40 surfaces, `generate` can be parallelized across agents.

**Split by domain — NOT by surface type.**

```
✅ Agent A: S01 + components hosted on S01 (C02, C04) + modals opened from S01 (M01)
✅ Agent B: S02 + components on S02 (C06, C07) + modals on S02 (M06)
✅ Agent C: S04 + components on S04 (C08) + flows through S04 (F01, F03)

❌ Agent A: screens/ + panels/          ← breaks component→host wiring
❌ Agent B: modals/ + components/ + flows/
```

**Why:** Component `emits:` and host surface `listens_to` must be co-authored in the same context.
Splitting by surface type breaks this dependency; splitting by domain preserves it.

**Rule:** Each agent owns one screen + everything it hosts or opens.

After parallel pass, run `validate` to catch any remaining cross-agent wiring gaps.

---

## When to use

- App ≥ 20 surfaces with domain rules crossing multiple surfaces
- LLM as primary author, human as reviewer
- Need validated, machine-readable UI spec for codegen or design generation
- CI enforcement against spec drift required

## When NOT to use

- Simple app < 15 screens, basic CRUD — PRD + Figma is enough
- Prototype/MVP iterating daily — code IS the spec
- State machine is the core complexity — use XState instead

---

---

## Authoring & propagation workflows

Three modes an LLM agent will encounter. Run `npm run check` (= validate + build) as the final step of every mode.

---

### Mode 1 — Generate spec from a PRD

Ordered steps — do NOT skip step order; cross-file consistency depends on it.

1. **Inventory surfaces** from the PRD: list every screen (S), panel (P), modal (M), overlay (OV), component (C), flow (F) + assign IDs using `spec.config.yaml` prefixes.
2. **Draft cross-cutting files first** (before any surface file):
   - `15-system-events.md` — all backend/SSE events surfaces will listen to (dotted names, e.g. `upload.done`)
   - `20-domain-rules.md` — all business rules + `surfaces[]` lists (populate after surfaces are named)
   - `30-states-and-errors.md` — state + error catalogue (prose; no contract block needed)
   - `00-overview.md` — surface index table (fill as you go; keep current)
3. **Pass 1 — Skeleton**: author each surface file (frontmatter + prose sections). No contract blocks yet. Use the matching template from `templates/surfaces/`:
   - screen → `screen.md`, panel → `panel.md`, modal → `modal.md`, overlay → `overlay.md`, component → `component.md`, flow → `flow.md`
4. **Pass 2 — Contracts**: read the full surface list (`generated/surface-registry.yaml` if already built, otherwise your inventory), then fill the `{project}-contract` block in each surface:
   - Set `navigate`/`open_overlay` `target:` to real surface IDs
   - Set component `emits[].event` names; set host screen `listens_to:` to match
   - Set `rules:` frontmatter to match `20-domain-rules.md` `surfaces[]` entries (bidirectional)
   - Set `hosts:` frontmatter on components pointing to their host screen IDs
5. **Wire flows**: author `flows/Fxx-*.md` referencing real action IDs from Pass 2.
6. **Run `npm run check`** (= validate + build) from `docs/ui-spec/tools/`. Fix every error:
   - Dangling targets → VR-TARGET
   - Bad hosts → VR-HOSTS
   - Listen-orphans → VR-LISTEN-ORPHAN
   - Rule drift → VR-RULE-DRIFT
   - Modal missing exit → VR-MODAL-EXIT-001
7. **Eyeball**: `npm run interpret` (v1 wireframe) or `npm run interpret:wf` (v2, region-box layout) to confirm navigation graph makes sense.

> **Multi-agent note:** for > 40 surfaces split by *domain* (one screen + its hosted components + its modals per agent). Never split by surface type. After parallel pass, run validate to catch cross-agent wiring gaps. See "Multi-agent orchestration" section.

---

### Mode 2 — Update an existing surface

**a. Find dependents FIRST (before touching anything)**

| What to grep/check | Where | Finds |
|---|---|---|
| `target: <SurfaceId>` | `generated/navigation-graph.yaml` | surfaces that navigate/open_overlay TO this one |
| `<SurfaceId>` (surface ID literal) | whole spec tree (`screens/`, `panels/`, `modals/`, `flows/`) | all files referencing this surface |
| action IDs of this surface (e.g. `A-S05-*`) | `generated/action-registry.csv` or grep spec tree | flow `steps`/`branches` using those action IDs |
| emitted event names (from this surface's `emits` block) | grep spec tree for `listens_to:` | host screens that will break if event renamed |
| `hosts: [<SurfaceId>]` | `generated/surface-registry.yaml` | components listing this screen as host |

**b. Apply the change** to the target surface file.

**c. Propagate** — work through the dependent list from (a):

| Change type | What to propagate |
|---|---|
| Rename surface ID | Find+replace the old ID across ALL spec files + `00-overview.md` index |
| Rename action ID | Update every flow `steps[]`/`branches[]` that referenced the old ID |
| Rename/remove emitted event | Update `listens_to:` in every host screen that consumed it; update `15-system-events.md` if it was declared there |
| Add/remove `rules:` frontmatter entry | Sync `20-domain-rules.md` `surfaces[]` for that rule (bidirectional) |
| Add/remove `regions:` | Fix any interaction `region:` fields on this surface that now mismatch |
| Rename/remove surface from `hosts:` | Update dependent components' `hosts:` frontmatter |
| Split surface into two new IDs | Old ID must be replaced everywhere; update `00-overview.md`; re-wire flows |

> **Rename tool:** for a pure rename (surface ID, action ID, or event name) run `npm run rename <old> <new>` (dry-run; add `--apply` to write) — it word-boundary-replaces every reference across the spec (including `A-<id>-*` action prefixes) and renames the file. Then `npm run check`.

**d. `npm run check`** — the validator now catches: VR-TARGET (dangling navigate), VR-HOSTS (bad host ref), VR-LISTEN-ORPHAN (listen to non-existent event), VR-RULE-DRIFT (rules mismatch). Fix every **error** before done; warns are advisory.

> **State refs:** `ST-*` references in prose are now checked by **VR-STATE** (warn) against the `### ST-*` headings in `30-states-and-errors.md` — a typo'd / missing state shows as a warning in `check`. It's a prose scan at warn level, so still eyeball semantic correctness; `ERR-*` ids are not yet cataloged.

---

### Mode 3 — Add a surface or element

1. Run `/ui-spec add-surface <type> <id> <name>` (creates file from template) — or copy the correct template from `templates/surfaces/` manually. **Replace the template's placeholder `regions:` with regions meaningful to THIS surface** — region names are free-form snake_case strings; every `region:` you put on an interaction MUST appear in `regions[]` (VR-REGION).
2. Fill frontmatter + prose + contract block, following CONVENTION §1–3. **Read `20-domain-rules.md` and set `rules:` to the existing rule IDs that apply** — VR-RULE-DRIFT errors if a rule lists this surface but the surface omits it (or vice-versa).
3. **Propagation checklist** — touch every side-file that needs updating:

   - ☐ `00-overview.md` — add a row to the surface index table **AND a path to the directory tree** (both live in this file)
   - ☐ `15-system-events.md` — if the new surface needs a new backend/SSE event, declare it here (dotted name convention)
   - ☐ `20-domain-rules.md` — if a NEW domain rule is needed: add rule + add surface ID to `surfaces[]`; also add the rule ID to the surface's `rules:` frontmatter (bidirectional)
   - ☐ **Does this new screen RENDER an existing component?** (sidebar, filter bar, …) → add THIS surface's ID to that component's `hosts:` frontmatter, and add the component's emitted-event `listens_to:` interactions here if it should react (else VR-HOSTS / VR-LISTEN-ORPHAN)
   - ☐ Host screens' `listens_to` — if this NEW surface IS a component that emits an event: add `listens_to: <event>` to every host screen that should react
   - ☐ Flow files — if an existing flow now passes through this surface: add a step referencing the new action ID
   - ☐ Make it reachable — add a `navigate`/`open_overlay` (`target: <newId>`) from a real source surface. NOTE: components can't `navigate` (CONVENTION §2) — for sidebar/menu links wire it as component `emit_event` → a host screen `listens_to` that navigates, or put a direct navigate on a screen.
   - ☐ If this new surface is a panel/component: set its own `hosts: [<HostScreenId>]` frontmatter pointing at the screen(s) that render it
   - ☐ Verify every `target:` you declared IN this surface points at an existing surface

4. **`npm run check`** — fix every error before done (VR-TARGET / VR-HOSTS / VR-LISTEN-ORPHAN / VR-RULE-DRIFT).

---

### Propagation model reference

Which link each validate rule guards. `npm run check` catches everything in this table except the prose-only rows.

| Link | How expressed in spec | Validator rule | Severity |
|---|---|---|---|
| surface → surface (navigate) | interaction `action: navigate`, `target: <SurfaceId>` | VR-TARGET | **error** |
| surface → surface (overlay) | interaction `action: open_overlay`, `target: <SurfaceId>` | VR-TARGET | **error** |
| component → host screen | component frontmatter `hosts: [Sxx]` | VR-HOSTS | **error** |
| component emits → screen listens | component `emits[].event` ↔ screen `listens_to:` | VR-LISTEN-ORPHAN | **error** |
| external/system signal | `listens_to:` a dotted name (e.g. `upload.done`) — declared in `15-system-events.md` | exempt from VR-LISTEN-ORPHAN (dotted = backend SSE) | — |
| emitted event with no listener | `emits[].event` or `emit_event` with no `listens_to` anywhere | VR-EMIT-LISTEN | warn |
| rule ↔ surface (bidirectional) | surface `rules: [Rn]` ↔ `20-domain-rules.md` `surfaces: [Sxx]` | VR-RULE-DRIFT | **error** |
| action ID uniqueness | `id: A-S05-001` unique across all files | VR-ID-UNIQUE | **error** |
| action ID prefix matches surface | `A-S05-*` must live in S05 | VR-ID-PREFIX | warn |
| interaction region ∈ frontmatter | `region: <r>` must be in `regions[]` frontmatter | VR-REGION | warn |
| modal must have exit | modal has ≥1 `close_overlay` action | VR-MODAL-EXIT-001 | **error** |
| modal must return to invoker | modal has ≥1 `return_to_invoker` target | VR-MODAL-EXIT-002 | warn |
| flow steps resolve | flow `steps[]` + `branches[].action` must be real action IDs | VR-FLOW | **error** |
| state IDs (`ST-*`) | referenced in prose; registry = `### ST-*` headings in `30-states-and-errors.md` | VR-STATE | warn |
| `00-overview.md` index | id + name rows must match frontmatter | VR-OVERVIEW | warn |

---

## References

- `references/CONVENTION.md` — detailed writing rules, hard constraints, block variants
- `references/METHODOLOGY.md` — rationale, alternatives comparison, 3-layer model, LLM consumption protocol
