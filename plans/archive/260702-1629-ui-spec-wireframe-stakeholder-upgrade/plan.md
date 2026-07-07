# UI-Spec Wireframe — Stakeholder Upgrade

**Status:** DONE — tất cả 8 phases committed. Follow-ups 2026-07-03/05: chip audit (155→163 mappings), visual QA tool, VR-ASCII-DRIFT rule, elements: map all 39 surfaces, hand-drawn ASCII removed từ 40 surfaces + rebuild (2026-07-05), S11 activate-confirm, chip-overflow fix. Còn: scope tiếp "wireframe render đẹp hơn" — chờ user cho pain point cụ thể.
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
- RESOLVED 2026-07-03: all 7 spec gaps closed (8 interactions added, A-P02-003/S07-008..010/S11-008/S15-011/M15-008/M13-005; actions 311→319, mapped chips 155→163). Detection now mechanical: `chip-audit.mjs` (build phase 7.5) writes `generated/chip-audit.md` listing unmapped sample chips per surface.
- RESOLVED 2026-07-05: S11 `Kích hoạt` needs confirm — added `hx-confirm` (native browser confirm, same pattern as A-M15-006 deactivate-channel) to `campaigns.html` activate button; not routed through O01 (O01 has no wired backend route beyond delete_note — extending it was out of scope). S11 spec doc updated with a one-line interaction note.
- RESOLVED 2026-07-05: chip overflow fixed — `.gc-inline-chip` in `styles-phase6.mjs` changed from `white-space: nowrap` to `white-space: normal` + `max-width: 100%` + `overflow-wrap: break-word` so long chips (e.g. S03 tab_bar) wrap inside the cell instead of overflowing.
- OPEN 2026-07-05: user wants further wireframe render polish beyond the above ("đẹp hơn nữa") — scope not yet specified; next step is to get concrete pain points from user (spacing, density, color, typography, or something else) before starting.

- Phase 6b (2026-07-02, post-user-feedback): grid cells redesigned for stakeholders (gridCellHtml: label + dominant sample + name-only pills; listeners/counts/guards hidden, tooltip keeps contract); fixed grid-template-areas quoting bug that collapsed the grid to a stack; children sub-layouts render as stacked mini-sections inside parent cell (floating children excluded). Screenshot-verified S14/S03/M01.

- RESOLVED 2026-07-05: hand-drawn ASCII removed from all 40 migrated surfaces (35 single-block files scripted; 6 multi-block files — M08/M15/M16/S13/S14/S15 — edited per-heading, headings kept since each carries explanatory prose beyond just introducing the block). Verified zero stray box-drawing chars remain outside the generated `ui-layout:ascii:start/end` markers. Rebuilt (`build.mjs`): 54 surfaces/320 actions, ascii regenerated 40/40, wireframe-v2.html regenerated. `validate.mjs`: 1 pre-existing unrelated warning (S14 `ST-CALL-R14-WARN` state typo), otherwise clean.
- DECIDED 2026-07-05: S11 `conversion_stats` stays as its own declared region (display-only, SSE-updated) — not merged into `summary_bar` (user: không cần).
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
