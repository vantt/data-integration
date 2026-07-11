# Phase 4: Docs + Conventions Update

## Context
Once Phase 2 (card) and Phase 3 (pill/badge) land, `DESIGN_SYSTEM.md` needs two things it
doesn't have today: (1) a pointer from each converged class name to the macro/filter that
now generates it, and (2) a standing convention section for `templates/macros/` itself —
so the NEXT drifted pattern someone notices has an obvious place to land instead of
spawning a 7th one-off family. This is the step the user specifically asked not to skip.

## Requirements
- Only document what actually shipped in Phase 2/3 — no aspirational claims.
- Add a new `## 11 · Macros` section to `DESIGN_SYSTEM.md` (after existing §10) — don't
  restructure the existing 10 sections, just append.
- The new section must state, concretely:
  - `templates/macros/` is the canonical location for any macro shared across more than
    one template (macros owned by a single fragment, e.g. `wl_row` in
    `fragments/_wl_row.html`, stay where they are — only cross-cutting ones move here).
  - The docstring convention every macro file must follow (the `@surface`/`@kind MACRO`/
    `Usage:` header, per `fragments/_wl_row.html:1-8`).
  - The current macro inventory as of this phase: `macros/card.html` → `card()` with its
    full signature (`eyebrow`, `tag`, `tag_variant`, `variant`, `extra_class`) and one
    example call, plus whatever Phase 3 produced (`bdg_cls`/`bdg_tip` filter usage note,
    or a new macro if Phase 3 needed one for a non-badge-catalog case).
- Update §10's existing `scard` bullet to add: "→ build via `{% from "macros/card.html"
  import card %}`, don't hand-roll the div structure" (same pattern for any pill/badge
  class Phase 3 converged).

## Files
- Modify: `crm/docs/design/DESIGN_SYSTEM.md` (append new §11, edit §10's `scard` bullet)
- Modify (if it exists and covers UI components): check
  `crm/docs/ui-spec/components/*.md` for any card/badge component doc that also needs
  the pointer — only touch if it currently describes markup structure directly.

## Implementation Steps
1. Read final state of `macros/card.html` and the badge_catalog.py changes from Phase 3.
2. Write §11 "Macros" per the Requirements above.
3. Edit §10's `scard` (and converged pill/badge) bullets to point at §11.
4. Grep `crm/docs/ui-spec/` for references to the old drifted class names to see if
   anything else needs updating.

## Tests
N/A — docs-only phase.

## Risks / Rollback
None — additive doc change, trivially revertible.
