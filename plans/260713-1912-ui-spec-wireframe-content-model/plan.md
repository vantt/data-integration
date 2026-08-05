# ui-spec wireframe → real wireframe (content model)

**Status:** done (2026-07-13)
**Goal:** Layout tab renders a reviewable lo-fi wireframe (element types, repetition, vertical proportion, viewport frame) instead of an annotated region map.

## Phases

| # | Phase | File | Status |
|---|---|---|---|
| 0 | Single-writer schema module | phase-00-single-writer-schema.md | done |
| 1 | row_heights + viewport frame | phase-01-row-heights-viewport.md | done |
| 2 | `content:` model + renderer + S14 pilot | phase-02-content-model-s14-pilot.md | done |
| 3 | Visual QA + tests + docs | (inline in phase 2) | done |

## Decisions (from discussion 2026-07-13)

- Skip `kinds:` hint tier — go straight to structured `content:`; avoids two overlapping mechanisms.
- `content:` is optional per region; fallback = existing `samples` line. Migrate S14 first, other surfaces later.
- ASCII blueprint: regions with `content` get a deterministic 1-line flatten (`flattenContentLine`); no in-ASCII element drawing (too costly).
- Single-writer: `tools/wireframe/layout-schema.mjs` — dependency-free ESM; node imports it, `html-shell.mjs` inlines it export-stripped for the browser. All key sets, primitive registry, walkers, flatten live there.
- chip-audit for content surfaces: `btn` without `action:` = unmapped finding; badge/chips types are display-only by design.

## Acceptance

- validate + build green on crm/docs/ui-spec (54 surfaces), no regression on non-migrated surfaces.
- S14 screenshot passes Visual QA checklist §11 + new criteria: element differentiation, repetition, vertical proportion, viewport frame.
- `node --test` green in tools/.
- ui-layout-authoring.md documents row_heights + content schema; SKILL.md updated.
