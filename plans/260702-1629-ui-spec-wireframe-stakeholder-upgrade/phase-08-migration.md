# Phase 08 — Migration: All 54 Surfaces

## Context links
- `tools/validate.mjs` — VR-LAYOUT-* rules added in phase 05; must pass for all surfaces after migration
- `tools/wireframe/generate-ascii.mjs` — ASCII generator from phase 07; `--surface` flag for per-surface runs
- `tools/wireframe/extract-layout.mjs` — `extractLayout`, `layoutAreaNames`, `nonRectRegions`
- `tools/build.mjs` — final integration: validate → registries → wireframe → ascii injection
- `tools/wireframe/verify-runtime.mjs` — full Playwright green required at end
- `crm/docs/ui-spec/` — spec root; 54 surfaces across `surfaces/`, `modals/`, `panels/`, `flows/`
- `templates/surfaces/*.md` — surface templates that need `ui-layout` placeholder added
- `.agents/skills/ui-spec/SKILL.md` — workflow docs that need build step update

## Scope

54 surfaces total. Rough breakdown by complexity:
- Simple modals / panels (M-*, P-* series): single-column or 2-region; ~30 surfaces
- Complex screens (S-* series): multi-column, spanning regions; ~14 surfaces
- Flows (FL-*): no spatial layout needed — skip ui-layout; mark as exempt
- Components (C-*): may have layout or may be exempt (author's discretion)

Flows and components without layout fence are valid — VR-LAYOUT-ORPHAN only warns, does not error.

## Steps

### Step 1 — Pilot: S14 + one simple modal

**Goal:** validate schema, generator, and reviewer workflow before bulk.

1. **S14** (already partially done in phase 05 pilot):
   - Finalize `yaml ui-layout` fence (2-column, `reason_to_call` spanning, all 14 regions placed).
   - Run `node tools/validate.mjs` → VR-LAYOUT-* clean.
   - Run `node tools/wireframe/generate-ascii.mjs --surface S14` → diff vs hand ASCII.
   - Human diff review: adjust schema if proportions or spanning are wrong.
   - Run `node tools/build.mjs` → markers injected; wireframe renders grid correctly.

2. **One simple modal** (e.g. M01 or first modal in modals/ dir):
   - Author `yaml ui-layout` fence: `columns: ["1fr"]`, `areas` with 2-3 regions.
   - Same validate → generate → review cycle.
   - Confirm single-column grid renders in wireframe.

3. **Schema adjustments:** if pilot reveals schema gaps (e.g. need `min_height`, or `children` sub-layout for dotted regions), update schema definition in `extract-layout.mjs` and phase 05 docs before bulk.

### Step 2 — Bulk: remaining ~52 surfaces

**Agent workflow** (LLM-assisted, human-reviewed):

For each surface batch (suggest 10 surfaces per agent run):

```
Agent prompt template:
  Read {surface file}.
  The existing hand-drawn ## Layout ASCII block describes the 2D arrangement.
  Author a yaml ui-layout fence that captures the same layout.
  Rules:
    - columns: fr strings matching visual proportions
    - areas: matrix matching ASCII regions (use frontmatter regions[] names exactly)
    - floating: any region shown as overlay/STOP variant
    - samples: one realistic Vietnamese data line per region
    - do NOT invent region names; use frontmatter regions[] only
  Output: the yaml ui-layout fence content only (no surrounding markdown).
```

After agent drafts:
1. Paste fence into surface .md under `## Layout`.
2. Run `node tools/validate.mjs --root crm/docs/ui-spec` → fix any VR-LAYOUT-* errors.
3. Run `node tools/wireframe/generate-ascii.mjs --surface {ID}` → eyeball diff.
4. Run `node tools/build.mjs` to regenerate wireframe and confirm grid renders.

**Surfaces to skip (no ui-layout needed):**
- Flow surfaces (FL-*): narrative only, no spatial layout.
- Surfaces where ASCII block is absent and regions[] is empty: leave as-is, stacked fallback renders correctly.

### Step 3 — Template + SKILL.md updates

**`templates/surfaces/*.md`** — add placeholder after `## Layout` heading:
```markdown
## Layout

<!-- Author the hand-drawn ASCII layout here, then add the ui-layout fence below. -->

```yaml ui-layout
columns: ["1fr"]
areas:
  - [main]
samples:
  main: ""
```

<!-- ui-layout:ascii:start -->
<!-- ui-layout:ascii:end -->
```

**`.agents/skills/ui-spec/SKILL.md`** — update build workflow section:
- Add: `node tools/build.mjs` now runs: validate → surface-registry → navigation-graph → action-registry → coverage-report → wireframe-v2.html → ascii injection.
- Add: ASCII in `## Layout` between markers is **generated** — edit the `yaml ui-layout` fence, not the ASCII.
- Add: `--no-open` flag for CI runs.
- Remove or update any reference to running `interpret-wireframe.mjs` separately.

### Step 4 — Final build + full validation

```bash
node tools/validate.mjs --root crm/docs/ui-spec
node tools/build.mjs --root crm/docs/ui-spec
node tools/wireframe/verify-runtime.mjs
```

Expected:
- `validate.mjs`: 0 errors; VR-LAYOUT-ORPHAN warnings only for flows/components (acceptable).
- `build.mjs`: all 54 surfaces processed; ascii markers injected in surfaces with layout fence.
- `verify-runtime.mjs`: all existing assertions green + phase 01/02 new assertions green.

## Wide-char normalization in samples

All sample text authored in Vietnamese contains wide or special chars. Apply normalization before writing into ASCII cells:
- `▶ → >`
- `⚠ → !`
- `→ → ->`
- Em dash `— → -`
- Ellipsis `… → ...`

This is already handled by `ascii-normalize.mjs`; `generate-ascii.mjs` must run samples through the same table.

## Rectangularity conflicts in complex screens

Some screens (e.g. S03 with sidebar sub-regions) may produce VR-LAYOUT-RECT errors if the author tries to place dotted child regions in the top-level areas matrix.

**Resolution:** dotted regions (`sidebar.core_info`) belong in the `children.sidebar` sub-layout, not the top-level `areas`. Top-level areas only contain parent tokens (`sidebar`). Documented in schema (phase 05). If a surface cannot be expressed rectangularly, allow a layout redesign with a note in the surface file — the goal is spatial fidelity, not mechanical mapping of every historical ASCII variant.

## Acceptance criteria

1. `validate.mjs` exits 0 (no errors) across all 54 surfaces.
2. VR-LAYOUT-* rules: no UNKNOWN or RECT errors. ORPHAN warns acceptable for flows/components.
3. Every screen + modal + panel surface has either a `yaml ui-layout` fence OR a note `<!-- no-ui-layout: {reason} -->` explaining the exemption.
4. All ASCII between markers is machine-generated (no hand edits after marker insertion).
5. `build.mjs` runs end-to-end without error; wireframe opens with generation stamp.
6. `verify-runtime.mjs` green.
7. SKILL.md reflects new build workflow accurately.

## Risks & rollback

- **Risk: ASCII richness loss** — hand ASCII may have arrows, call-outs, or annotations not expressible in the generator. Mitigate: preserve original hand ASCII above the START marker as a comment block; generated ASCII replaces only the marked section.
- **Risk: rectangularity conflicts on complex screens** — do not force-fit; allow `<!-- no-ui-layout: L-shaped region, deferred -->` exemption and stacked fallback. Track exemptions in a `plans/260702-1629-ui-spec-wireframe-stakeholder-upgrade/migration-status.md` scratch file (delete after all resolved).
- **Risk: agent draft quality** — LLM may invent region names or miss spanning. Mitigation: VR-LAYOUT-UNKNOWN catches invented names immediately; human diff review catches missed spanning.
- **Risk: wide-char alignment in generated ASCII** — Vietnamese text is double-width in some terminals. Normalize all sample text to ASCII-safe substitutions; do not attempt to account for terminal double-width rendering in column budget.
- **Rollback:** stacked region-box view (`renderLayout`) is always the fallback for surfaces without `ui-layout` fence. Removing a fence from any surface restores prior rendering with zero side effects. Templates + SKILL.md changes are documentation-only and fully reversible.
