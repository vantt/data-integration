# CONVENTION — Surface writing rules (contract between author and compiler)

> Compiler **does not parse free Markdown**. It reads exactly 2 structured things per surface file: **frontmatter** and **one fenced block tagged `yaml {project}-contract`**. All other prose is invisible to the compiler — write freely.
> The `{project}-contract` tag is configured in `spec.config.yaml` → `contract_tag`. Example: `crm-contract`, `shop-contract`.
> Any file violating this convention → `validate` fails → build fails. Trust comes from **this gate**, not a smart parser.

---

## 1. Surface file structure

```markdown
---
# (1) FRONTMATTER — surface meta, machine-readable
id: S05
type: screen            # screen | panel | modal | overlay | component | flow
name: Product List
platforms: [desktop, mobile]   # desktop | mobile | all
hosts: []               # screens only — surfaces THIS screen embeds (panels, components)
hosted_by: []           # non-screens — surfaces that embed THIS surface
regions: [header, list, sidebar]  # named layout regions (optional; enables region validation)
status: active          # active | future
design_ref: "designs/s05.png"
rules: [R2, R4]         # domain rule IDs this surface must comply with (for cross-validation)
---

# S05 — Product List          ← (2) NARRATIVE: for humans, compiler ignores

## Purpose
Why this screen exists, user journey context, edge cases... (free prose)

## Layout
(ASCII art or descriptions — write anything)

## Interactions               ← (3) human-readable heading; contract block follows immediately

```yaml crm-contract
interactions:
  - id: A-S05-001
    element: product_row
    trigger: click             # click|tap|drag|drag_drop|submit|change|keydown|system_event|event
    guard: product.status == "active"   # optional condition
    action: navigate           # navigate|open_overlay|close_overlay|mutate|emit_event|external|system_event
    target: S06                # Sxx|Pxx|Mxx|Oxx|self|return_to_invoker|external:<url>|<event-name>
    payload: { product_id: "$product.id" }   # optional
    effects: []                # optional side effects list
    region: list               # optional — must match frontmatter regions[] if present
  - id: A-S05-002
    element: add_button
    trigger: click
    action: open_overlay
    target: M03
```

## States
(prose or links to 30-states-and-errors.md)
```

---

## 2. Hard rules (validator enforces)

1. **Exactly 1** fenced block with info-string `yaml {project}-contract` per surface. Pure display components with no interactions still need the block: `interactions: []`.
2. Required frontmatter: `id`, `type`, `name`. `id` must match filename (`S05-*.md` → `id: S05`).
3. Every interaction requires: `id`, `trigger`, `action`. If `action ∈ {navigate, open_overlay}` → `target` is required.
4. Action `id` must be unique across the entire repo. Prefix must match the surface (`A-S05-*` in S05; canvas uses `A-CV-*`; system events use `A-SYS-*`).
5. `target` must exist in the surface registry or be a reserved keyword: `self`, `return_to_invoker`, `external:<url>`, or a named event string.
6. **Do NOT** duplicate interaction content in prose tables. Any human-readable table is **generated output**, not hand-authored.
7. Components only `emit_event` (hosts map via `listens_to`). Components must not `navigate` or `open_overlay` unless genuinely self-contained controls.
8. Modals must have ≥1 `close_overlay`/submit exit and ≥1 cancel/close → `return_to_invoker`.
9. Flow files: **no new interactions**. Use `yaml {project}-contract` with `flow:` key only (see §3).
10. **`region` field** (optional): if present on an interaction, must match a value in the surface frontmatter `regions[]` array. If `regions` is not declared in frontmatter, `region` field is ignored by validator.
11. **`hosts:` is valid only on screens** and lists the panels permanently embedded in this screen. All other surface types use `hosted_by:` to list their container screens (one-way for components). Bidirectional consistency is validated by VR-HOSTS-BIDIR (warn, panel type only).

---

## 3. Block variants by surface type

**Screen / Panel (interactions):**
```yaml crm-contract
interactions:
  - id: A-S05-001
    element: save_button
    trigger: click
    action: mutate
    effects: [form.submit, ui.toast.show]
```

**Component (emit-only):**
```yaml crm-contract
emits:
  - id: A-C01-001
    trigger: click
    event: contact_row.selected
    payload: { contact_id: "$contact.id" }
```

**Host listening to component event:**
```yaml crm-contract
interactions:
  - id: A-S05-LSN-01
    listens_to: contact_row.selected
    action: mutate
    effects: [ui.selectedContactId.set, P02.mode.show_contact_details]
```

**Modal:**
```yaml crm-contract
interactions:
  - id: A-M03-001
    element: confirm_button
    trigger: click
    action: mutate
    effects: [product.archive]
  - id: A-M03-002
    element: cancel_button
    trigger: click
    action: close_overlay
    target: return_to_invoker
```

**Flow (references existing action IDs only):**
```yaml crm-contract
flow:
  goal: "User creates a new contact and assigns to a deal"
  steps: [A-S01-002, A-S05-001, A-M03-001, A-SYS-001]
  branches:
    - { when: "validation fails", action: A-M03-003 }
```

**Tab switching (show_panel):**
```yaml crm-contract
interactions:
  - id: A-S03-004
    element: tab_insight
    region: tab_bar
    trigger: click
    action: show_panel
    target: P01          # must be type=panel; validated by VR-SHOW-PANEL
```
`show_panel` makes a panel visible within the current screen's layout. It is captured as a *display edge* in `navigation-graph.yaml` (not a navigation edge). Target must be a registered panel (`type: panel`). Effects array is dropped when migrating from `mutate + effects: [main_col.show_panel_Pxx]`.

---

## 3.5 Promotion rules — when a layout block becomes a surface type

| Pattern | Promote to | Why |
|---|---|---|
| Pure layout block, appears on exactly 1 surface, no own state, no events | dotted region (e.g. `sidebar.core_info`) | No reuse; region string is sufficient identity |
| Reused on ≥2 surfaces **OR** emits events **OR** carries own local state | component (`Cxx`) | Coupling via event model; hosts need `listens_to` |
| Navigation target **OR** independently shown/hidden lazy content (e.g. tab panel) | panel (`Pxx`) | Distinct lifecycle; shown via `show_panel` action |
| Standalone route with own URL / deep-link | screen (`Sxx`) | Navigated via `action: navigate` |

**Dotted region convention:** hierarchical regions expressed as `parent.child` snake_case paths. The parent segment must also appear in `regions[]` as a layout anchor. Example:
- `regions: [topbar, sidebar, sidebar.warning, sidebar.core_info, sidebar.contact, sidebar.dates, sidebar.tags, main_col, tab_bar]`
- Interaction: `region: sidebar.core_info`
- VR-REGION-PARENT warns if `sidebar.core_info` is in `regions[]` but `sidebar` is not.

---

## 4. Domain rules cross-cutting

`20-domain-rules.md` carries one `yaml {project}-contract` block declaring rules → surfaces. Validator checks that every surface listed under a rule has that rule ID in frontmatter `rules:`.

```yaml crm-contract
rules:
  - id: R4
    name: Deal Stage Gating
    description: "A deal cannot advance to Closed Won without a linked contact"
    surfaces: [S08, S09, M05]
```

---

## 5. Action ID conventions

| Context | Pattern | Example |
|---|---|---|
| Regular surface | `A-{SURFACE}-{001,002,...}` | `A-S05-001` |
| Canvas / drawing surface | `A-CV-{001,...}` | `A-CV-003` |
| System / async events | `A-SYS-{001,...}` | `A-SYS-001` |
| Listener (listen action) | `A-{SURFACE}-LSN{01,...}` | `A-S05-LSN01` |

IDs are auto-generated sequentially by convention. Manual assignment is allowed. **IDs once assigned are never reused** — gaps are permitted.

> Both `A-S03-LSN-01` and `A-S03-LSN01` are accepted by the schema regex. Prefer no-hyphen form (`LSN01`) for new authors — it matches existing crm spec usage.

---

## 6. Compiler pipeline

```
*.md  --extract.mjs-->  contracts (in-mem)
                          │
                          ├── validate.mjs   (schema + §2 rules)  → exit≠0 on any error
                          └── build.mjs      → generated/
                                                  surface-registry.yaml
                                                  navigation-graph.yaml
                                                  action-registry.csv
                                                  coverage-report.md
```

Source of truth = `.md` files. `generated/` is derived output — run `build`, do not edit by hand, safe to gitignore.

```bash
# From repo root (canonical — no vendor copy needed):
npm install --prefix .skills/ui-spec/tools   # one-time
node .skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec
node .skills/ui-spec/tools/build.mjs   --root crm/docs/ui-spec
# combined:
node .skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

`init` scaffolds the spec directory without copying tools. Pass `--vendor` only when the spec is exported to a repo with no access to `.skills/ui-spec/`.

---

## 7. PRD completeness warnings (for `generate` command)

When generating a spec from a PRD, the skill warns if the PRD is missing:

| Missing | Warning |
|---|---|
| Explicit screen list | `WARN: no screen inventory found — inferring from flows` |
| User flows / task flows | `WARN: no user flows — generated flows will be skeletal` |
| Domain entities | `WARN: no data model — domain rules will be generic` |
| Business rules | `WARN: no business rules — 20-domain-rules.md will be empty` |
| Platform targets | `WARN: platform not specified — assuming desktop` |

User can provide supplements before Pass 2, or proceed and fill gaps manually afterward.

---

## 8. `spec.config.yaml` reference

```yaml
project: crm              # used as ID prefix in surface files
contract_tag: crm-contract  # info-string of the fenced contract block
surface_id_prefixes:
  screen: S
  panel: P
  modal: M
  overlay: O
  component: C
  flow: F
entry_surface: S01
platforms: [desktop, mobile]
```

---

## 9. Payload variable grammar

| Context | Pattern | Example |
|---|---|---|
| Data entity field | `$<entity>.<field>` | `$party.id`, `$task.due_at` |
| Listener event field | `$event.<field>` (inside `listens_to` interactions only) | `$event.party_id` |
| Component prop (bare) | `$<prop_name>` (single word, no dot, in component `emits` blocks only) | `$current_filter_values` in C05 emits |

Validator rule VR-PAYLOAD-GRAMMAR warns on bare `$<word>` tokens found in payload objects, **except inside component `emits`** — there the data context is the component's own props, so bare prop tokens are the documented pattern and are not flagged. If a bare token actually mirrors an entity field (e.g. `$party_id` for `$party.id`), prefer the entity form. Declare every bare prop in the component's Props/API section.

> **VR-HOSTS-BIDIR note:** `hosts:` on screens lists only permanently-embedded **panels**. Component placement is tracked one-way via the component's own `hosted_by:` — screens do not mirror it. VR-HOSTS-BIDIR therefore warns for `panel` type only; components, modals, and overlays are exempt (modals/overlays are opened via `open_overlay`, not embedded).
