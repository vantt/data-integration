# Phase 03 — Convention + SKILL.md docs

**Effort:** 1h  
**Blocker:** Phase 02 (validator must be final before docs describe its rules)  
**File ownership:** `.agents/skills/ui-spec/references/CONVENTION.md` (full); `.agents/skills/ui-spec/SKILL.md` (propagation table + Mode sections); `.agents/skills/ui-spec/templates/surfaces/{panel,component,modal,overlay,flow}.md`

No crm spec files touched here. No schema or tool files touched here.

---

## Context

CONVENTION.md and SKILL.md still describe:
- vendored-tools invocation (`cd docs/ui-spec/tools && npm run check`) — stale after Phase 01
- no promotion rules table (D3-1)
- no `show_panel` action (D3-2)
- ambiguous `hosts:` direction (D3-3)
- no payload grammar definition (D3-4)
- inconsistent listener ID convention (D3-5-e)

Templates for panel/component/modal/overlay use `hosts: []` with wrong-direction semantics.

---

## A. CONVENTION.md additions

### §1 — Frontmatter: split `hosts` + add `hosted_by`

In the existing frontmatter sample block (§1), update the panel/component examples to show `hosted_by:` instead of `hosts:`. Add a note after the `hosts:` line:

```
hosts: []        # screens only — surfaces THIS screen embeds (panels, components)
hosted_by: []    # non-screens — surfaces that embed THIS surface
```

Add a rule in §2 (Hard rules), numbered 11:

> **11.** `hosts:` is valid only on **screens** and lists child surfaces (panels/components) rendered by this screen. All other surface types use `hosted_by:` to list their container screens. Bidirectional consistency is validated by VR-HOSTS-BIDIR (warn).

---

### §2 — New section: Block identity / promotion rules (D3-1)

Insert a new §3.5 "Promotion rules" after current §3 (Block variants):

```markdown
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
```

---

### §3 — Document `show_panel` action (D3-2)

In §3 (Block variants), add a new example block under "Screen / Panel (interactions)":

```markdown
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
```

Update the §6 propagation model table (propagation reference section in SKILL.md — see below) to add:

| panel show/hide (tab switch) | `action: show_panel`, `target: Pxx` | VR-SHOW-PANEL | **error** |

---

### §4 — Payload variable grammar (D3-4)

Add new §9 "Payload variable grammar":

```markdown
## 9. Payload variable grammar

| Context | Pattern | Example |
|---|---|---|
| Data entity field | `$<entity>.<field>` | `$party.id`, `$task.due_at` |
| Listener event field | `$event.<field>` (inside `listens_to` interactions only) | `$event.party_id` |
| Component prop (bare) | `$<prop_name>` (single word, no dot, in `emits` blocks only) | `$party_id` in C04 emits |

Validator rule VR-PAYLOAD-GRAMMAR warns on bare `$<word>` tokens found outside component `emits` contexts (see validate.mjs). Bare props in `emits` are documented explicitly in the component's Props/API section.

> **Normalization note:** C04 emits use `$party_id` (bare prop). This is a component-level prop variable, distinct from `$party.id` (entity field). Both are valid in their context. See Phase 06 for spec normalization status.
```

---

### §5 — Listener ID convention clarification (D3-5-e)

In §5 (Action ID conventions), update the table row for listeners:

| Listener (listen action) | `A-{SURFACE}-LSN{01,...}` | `A-S03-LSN01` |

Remove the hyphen before the number to match the pattern actually used throughout the crm spec. Add note:
> Both `A-S03-LSN-01` and `A-S03-LSN01` are accepted by the schema regex. Prefer no-hyphen form (`LSN01`) for new authors — it matches existing crm spec usage.

---

### §6 — Update §6 tool invocation (already partially done in Phase 01)

Replace the `cd docs/ui-spec/tools && npm install && npm run check` block (updated in Phase 01) with the full centralized form plus the `--vendor` init note:

```markdown
## 6. Compiler pipeline

...

```bash
# From repo root (canonical — no vendor copy needed):
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec
node .agents/skills/ui-spec/tools/build.mjs   --root crm/docs/ui-spec

# One-time install (if node_modules absent):
npm install --prefix .agents/skills/ui-spec/tools
```

`init` scaffolds the spec directory without copying tools. Pass `--vendor` only when the spec is exported to a repo with no access to `.agents/skills/ui-spec/`.
```

---

## B. SKILL.md propagation model table update

In `.agents/skills/ui-spec/SKILL.md`, the propagation model reference table (last section before References, ~line 318) currently has no `show_panel` row. Add:

```markdown
| panel show/hide (tab switch) | `action: show_panel`, `target: Pxx` | VR-SHOW-PANEL | **error** |
```

Also update `hosts:` / `hosted_by:` row:

Current:
```markdown
| component → host screen | component frontmatter `hosts: [Sxx]` | VR-HOSTS | **error** |
```

Replace with two rows:
```markdown
| screen → hosted panels/components | screen frontmatter `hosts: [Pxx, Cxx]` | VR-HOSTS | **error** |
| panel/component → host screen | surface frontmatter `hosted_by: [Sxx]` | VR-HOSTED-BY | **error** |
| bidirectional hosting consistency | X.hosted_by lists Y ↔ Y.hosts lists X | VR-HOSTS-BIDIR | warn |
```

---

## C. Template updates

### `templates/surfaces/panel.md`
Line 6: `hosts: []  # screens that embed this panel`  
→ `hosted_by: []  # screens that embed this panel`

### `templates/surfaces/component.md`
Line 6: `hosts: []  # surfaces that use this component`  
→ `hosted_by: []  # surfaces that use this component`

### `templates/surfaces/modal.md`
Read the file first to confirm `hosts:` appears; apply same rename.

### `templates/surfaces/overlay.md`
Same.

### `templates/surfaces/flow.md`
Read the file first; if `hosts: []` present, either remove the key entirely (flows have no hosting relationship) or change to `hosted_by: []`.

### `templates/surfaces/screen.md`
No change — screen correctly uses `hosts: []`.

---

## Implementation steps

1. Edit `CONVENTION.md`: add §3.5 promotion rules table, `show_panel` block, §9 payload grammar, listener ID note, §6 command update, `hosts:`/`hosted_by:` frontmatter note.
2. Edit `.agents/skills/ui-spec/SKILL.md`: update propagation table, ensure all `npm run check` / `cd tools` references removed.
3. Edit templates: panel.md, component.md, modal.md, overlay.md, flow.md — rename `hosts:` to `hosted_by:`.

---

## Validation command

```bash
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec && \
  node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
```

**Expected outcome:** identical to end of Phase 02 — no new errors or warns from doc/template changes (templates are not parsed by the compiler).

---

## Risk / Rollback

**Risk (Low×Low):** Editing CONVENTION.md breaks a validator reference to the doc (validator doesn't read CONVENTION.md — no coupling).  
**Rollback:** `git checkout HEAD -- .agents/skills/ui-spec/references/CONVENTION.md .agents/skills/ui-spec/SKILL.md .agents/skills/ui-spec/templates/`
