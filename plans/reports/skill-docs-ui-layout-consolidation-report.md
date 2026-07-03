# Skill Docs — UI Layout Authoring Consolidation

Date: 2026-07-03

## Deliverables

### 1. NEW `.agents/skills/ui-spec/references/ui-layout-authoring.md` (~270 lines)

Covers:
- **Philosophy** — why model-first: LLMs generate 1D, 2D ASCII is unreliable; YAML fence is source of truth, both grid and ASCII are deterministic renders; VR-ASCII-DRIFT enforces this.
- **Full schema** with inline commentary: `columns`, `areas` (rectangle constraint), `floating` (overlay banners), `variants` (prepend/append rows), `children` (1-level sub-layout, skip-in-grid-if-also-floating rule), `samples` ([brackets] → chips), `elements` (chip→action mapping, unambiguous-only rule, VR-ELEMENT-REF).
- **S14 worked example** showing `reason_to_call` and `collect` spanning 2 rows, `stop_banner` in floating, `topbar` in variant prepend_rows, and 4 verified `elements` mappings.
- **Coverage rule** — regions[] ↔ layout must agree exactly; VR-LAYOUT-ORPHAN + VR-LAYOUT-UNKNOWN guard both directions.
- **Validation rules catalog** — 7 rules (VR-LAYOUT-PARSE/UNKNOWN/RECT/ORPHAN, VR-ELEMENT-REF, VR-ASCII-DRIFT, VR-WIREFRAME-STALE): trigger + severity + fix, one row each.
- **Workflow** — edit fence → validate → build; build pipeline order; ASCII injection is part of build (idempotent); combined one-liner.
- **Wireframe UX contract** — Layout tab behavior (chips, Contract Inspector hover/pin, floating toggle, variant switch), Interactions tab, Blueprint tab (generated ASCII = first block found), Storyboard/Graph disabled.
- **Migration recipe** — LLM reads hand ASCII → drafts YAML (never draws) → validate geometry → build generates ASCII → human diffs. Batch by directory; no parallel build workers (ASCII writes .md files).
- **Common mistakes** — non-rectangular regions (diagonal boundary trap), orphan regions, floating+children double-render pattern (intentional skip), guessing element mappings, editing generated ASCII, YAML quoting traps, unregistered region in samples, wide glyph substitution behavior.
- **Quick-reference table** — all 7 schema keys.

### 2. SKILL.md surgical updates

- `### validate` — added layout-specific rules to the checks list: VR-LAYOUT-UNKNOWN/RECT/ORPHAN, VR-ELEMENT-REF, VR-ASCII-DRIFT, VR-WIREFRAME-STALE.
- `### ui-layout fence` section — added `elements:` key to schema example; added philosophy sentence (LLMs/1D/model-first); updated rectangle constraint comment with VR-LAYOUT-RECT; expanded rule block to name all 7 VR codes; added pointer to `references/ui-layout-authoring.md`. `interpret:wf` and `build` sections already complete (Contract Inspector, ASCII injection, preferred workflow pointer) — no change needed.

### 3. METHODOLOGY.md surgical update

Added one paragraph under "For design generation" that points authors to the model-first flow (`yaml ui-layout` fence → `build.mjs`, not hand ASCII) and links to `references/ui-layout-authoring.md`.

## Verification

```
node .agents/skills/ui-spec/tools/validate.mjs --root crm/docs/ui-spec
Scanned 54 spec files, 311 actions, 52 surfaces.
⚠ (4 pre-existing warnings: 3× VR-ASCII-DRIFT, 1× VR-WIREFRAME-STALE — from in-flight spec edits, not this change)
✓ validation passed (4 warning(s)).
```

No errors. All pre-existing warnings are from the spec corpus (other agents editing spec files); zero introduced by the doc changes.

## Files changed

| File | Change |
|---|---|
| `.agents/skills/ui-spec/references/ui-layout-authoring.md` | New — ~270 lines |
| `.agents/skills/ui-spec/SKILL.md` | Surgical — `validate` section + `ui-layout` fence section |
| `.agents/skills/ui-spec/references/METHODOLOGY.md` | Surgical — one paragraph added |

---

Status: DONE
Summary: Created `references/ui-layout-authoring.md` consolidating the full layout authoring know-how (schema, S14 example, VR rules, workflow, migration recipe, common mistakes); updated SKILL.md to name VR-LAYOUT-* rules, add `elements:` to schema overview, and point to the reference; added a model-first flow note to METHODOLOGY.md. Validate passes 0 errors.
