# UI-Spec Wireframe — Stakeholder Upgrade

**Status:** ALL 8 PHASES DONE (2026-07-02). Uncommitted. Pending: user review of generated ASCII → then remove hand-drawn ASCII (decision: generated-only after review).
**Branch:** feature/task-detail-cockpit-backend (tooling changes only, no CRM runtime code)
**Skill root:** `.agents/skills/ui-spec/` (source of truth — NOT `.claude/skills`)
**Spec root:** `crm/docs/ui-spec/` (54 surfaces, 311 interactions)
**Output:** `crm/docs/ui-spec/generated/wireframe-v2.html`

## Context / Decisions (user-confirmed 2026-07-02)

- Primary reviewer = **stakeholder** (not dev) → spatial fidelity > contract detail.
- Regeneration must be **automatic** as part of build (was manual-only).
- Phase 2/3 legacy features (storyboard/graph, currently disabled tabs) — keep, do not strip.
- Layout source of truth = new machine-readable `yaml ui-layout` fence (grid-template-areas semantics). Hand-drawn ASCII becomes **generated-only** after migration. Sample content (`samples:`) included — stakeholders need realistic data.
- Rationale: LLMs cannot reliably author aligned 2D ASCII; they author 1D structured YAML reliably. Tool renders 2D (CSS grid + generated ASCII) deterministically.

## Phases

| # | Phase | File | Status |
|---|-------|------|--------|
| 1 | Build pipeline + freshness stamp + staleness warning | phase-01-build-pipeline-freshness.md | done |
| 2 | Search + hash routing (#S14, #A-S14-009) | phase-02-search-hash-routing.md | done |
| 3 | Blueprint ↔ region-box 2-way linking (minimal — partially superseded by ph.6) | phase-03-blueprint-regionbox-linking.md | done |
| 4 | States/Errors subtab (stakeholder-friendly) | phase-04-states-errors-subtab.md | done |
| 5 | ui-layout schema + parser + VR-LAYOUT-* validation | phase-05-layout-schema-validation.md | done |
| 6 | CSS grid renderer (samples, floating, variants toggle) | phase-06-grid-renderer.md | done |
| 7 | ASCII generator from layout model (idempotent) | phase-07-ascii-generator.md | done |
| 8 | Migration: pilot S14 + 1 modal, then bulk 54 surfaces | phase-08-migration.md | done |

## Follow-ups

- Phase 6c (2026-07-02): pills removed from grid cells; `[...]` tokens in samples render as inline hoverable chips; fixed 300px Contract Inspector panel (hover region/chip → contract; click pins; mapped navigate chips still navigate). New optional `elements:` map in ui-layout (chip text → action id, VR-ELEMENT-REF warn rule); S14 piloted with 4 verified mappings. Screenshot-verified S14/S03.
- DONE 2026-07-03: `elements:` maps migrated to all 39 remaining surfaces — 149 chip→action mappings total; VR-ELEMENT-REF clean. Skill know-how consolidated into `references/ui-layout-authoring.md` + SKILL.md/METHODOLOGY.md pointers. VR-ASCII-DRIFT rule + build-order fix (ascii before wireframe) landed.
- DONE 2026-07-03: Visual QA loop encoded into skill — `tools/wireframe/screenshot.mjs` (headless capture, browser discovery, 20KB blank-guard) + §11 in ui-layout-authoring.md (mandatory triggers, 7-item checklist, representative-surface criteria) + SKILL.md command entry. End-to-end proven: agent captured S14/S03/M01 and self-judged against checklist.
- SPEC GAPS found during elements mapping (sample draws a control, contract lacks the interaction): P02 `Xem thêm →`; S07 `Priority ▼`/`Party 🔍`/`Status ▼` filters; S11 `Kích hoạt`; S15 `← Quay lại` (btn_back); M15 `Hủy` (no btn_cancel); M13 `+ Thêm tùy chọn`. Decide per item: add interaction or drop from sample.
- Minor polish: long chip (S03 tab_bar) overflows cell edge slightly — wrap/max-width tweak.

- Phase 6b (2026-07-02, post-user-feedback): grid cells redesigned for stakeholders (gridCellHtml: label + dominant sample + name-only pills; listeners/counts/guards hidden, tooltip keeps contract); fixed grid-template-areas quoting bug that collapsed the grid to a stack; children sub-layouts render as stacked mini-sections inside parent cell (floating children excluded). Screenshot-verified S14/S03/M01.

- Hand-drawn ASCII still present below generated blocks in all 40 migrated surfaces — remove after user reviews (prioritized diff review: S03, S14, S06, S09, S11).
- S11 `conversion_stats`: kept as separate declared region (display-only, SSE-updated); revisit if domain says it belongs inside summary_bar.
- Judgment calls resolved 2026-07-02: S03 topbar = left-column-only (matches hand ASCII); M08 `when:` rewritten to canonical `crm_note(note_type='contact_pref', pinned=true)`.

- Phase 4: modal error entries in `- error: ERR-*` form (no ST- prefix) skipped by states extractor — normalize spec format or extend regex during phase 8 migration.
- Phase 3: hand ASCII names few regions (S14: 3/14 spans) — density improves automatically once phase 7 generates ASCII from layout model.

## Dependencies

- 1, 2, 3, 4 independent of each other (can run in any order).
- 5 → 6 → 8; 5 → 7 → 8. Phase 8 last.
- Phase 3 kept minimal: grid renderer (6) supersedes most of its value.

## Acceptance criteria (plan level)

1. One build command regenerates registries + wireframe together; opening wireframe shows generation timestamp + surface count.
2. `validate.mjs` warns when wireframe older than any surface .md.
3. Reviewer can deep-link `#S14` / `#A-S14-009` and search surfaces/actions.
4. Surfaces with `ui-layout` render as spatial CSS grid with sample content; STOP/variant toggles work.
5. ASCII in markdown Layout sections is generated from layout model, regeneration idempotent.
6. All 54 surfaces migrated; `validate.mjs` passes with VR-LAYOUT-* rules; verify-runtime.mjs green.

## Key existing files

- `tools/interpret-wireframe.mjs` (87), `tools/extract.mjs` (120), `tools/build.mjs`, `tools/validate.mjs`
- `tools/wireframe/`: html-shell.mjs (183), extract-prose.mjs (57), ascii-normalize.mjs (143), styles*.mjs, verify-runtime.mjs (200)
- `tools/wireframe/client/`: app.js (192), app-chrome.js (113), region-model.js (149), render-regionbox.js (123), flow-play.js, render-storyboard.js, render-graph.js, graph-controls.js
- Templates: `templates/surfaces/*.md`
