# Plan: Card & Pill Macro Consolidation (CRM templates)

## Status
Phase 1 + Phase 2 done (2026-07-09). Phase 1: `card()`/`facts()` macros built, piloted on
`dedup_review.html`. Phase 2: all 7 remaining card-family templates migrated across 3
batches (see phase-02 for commit hashes) — `tasks_board.html`, note cards, `customer_360`,
`order_detail`, `conversation_detail`, `c360_insight_panel` (`aq-card`/`aq-session-card`,
including a deliberate visual fix removing a design-system-contradicting box-shadow).
New macro: `card_header()`. Card family count went from 6 drifted + 1 canonical down to 1
canonical (`scard`) + documented variants (`--survive`, `--lead`) + additive layout
modifier classes. Phase 3 (pill/badge) and Phase 4 (docs) not started.

## Context
Survey (2026-07-09) found the Precision design system already has a full token layer
(`ds-precision.css`, 150+ vars) and a documented canonical class list
(`crm/docs/design/DESIGN_SYSTEM.md` §10 — `scard`, `bdg`, `chip`, `btn`...). `btn` usage
stayed disciplined; `card` and `badge/pill` usage drifted into parallel one-off families
across templates despite the doc's guidance. Goal is NOT a new design system — it's
converging drifted markup back onto the canonical classes, wrapped in Jinja macros so
future changes happen in one file instead of N templates.

Existing macro convention to follow (see `templates/fragments/_wl_row.html:1-8`):
docstring header `{# @surface <id> · <name> | @kind MACRO ... Usage: {% from "..." import x %} #}`.

## Phases
1. [phase-01-card-macro-design-and-pilot.md](phase-01-card-macro-design-and-pilot.md) — design `card()` macro API from the 6 drifted families, pilot on 1 template
2. [phase-02-card-migration-rollout.md](phase-02-card-migration-rollout.md) — migrate remaining templates to the `card()` macro
3. [phase-03-pill-badge-convergence.md](phase-03-pill-badge-convergence.md) — converge `radio-pill`/`freshness-badge`/`aq-session-card__pill`/`dedup-card__tag` onto `bdg`
4. [phase-04-docs-and-conventions.md](phase-04-docs-and-conventions.md) — update DESIGN_SYSTEM.md §10 + add macro usage note

## Dependencies
- Phase 2 depends on Phase 1 (macro API must be validated before mass migration).
- Phase 3 is independent of Phase 1/2 (different CSS classes), can run in parallel.
- Phase 4 depends on Phase 2 + Phase 3 being done (docs describe final state).

## Acceptance Criteria
- One `templates/macros/card.html` macro (thin shell + `{% call %}` body slot) covers all
  current `scard`/`tcard`/`note-card`/`dedup-card`/`aq-card`/`aq-session-card`/
  `conv-cust-card` use cases — or each documented exception has a stated reason it can't
  converge.
- `DESIGN_SYSTEM.md` gains a new §11 "Macros" section naming `templates/macros/` as the
  canonical location for cross-template macros, with the `card()` signature documented.
- No visual regression across all 3 themes (dark default, `data-theme="light"`,
  `data-theme="finance"`) on every migrated screen — verified by manual click-through
  (`docker compose restart crm`, no rebuild needed — templates are bind-mounted).
- Badge/pill count of parallel families drops from 4+ to 1 canonical (`bdg`) + macro.
- `crm/docs/design/DESIGN_SYSTEM.md` §10 reflects the macro as the lifting mechanism.

## Risks
- Some drifted card variants may carry real layout differences (not just cosmetic),
  e.g. `dedup-card--survive` likely needs a distinct visual state for merge decisions —
  macro must support this via a variant param, not force one shape onto all.
- CSS is hand-authored across 7 stacked files with 3 themes; a change to `.scard` base
  ripples everywhere `scard` appears — pilot on 1 template first (phase 1) before rollout.

## Decisions
- Macro location: `templates/macros/` (new dir) — confirmed. This becomes the canonical
  home for cross-template shared macros (as opposed to macros owned by one fragment,
  e.g. `wl_row` staying in `fragments/_wl_row.html`). `DESIGN_SYSTEM.md` must document
  this directory as the convention (see Phase 4) so future macros land here too.
- Macro shape: thin wrapper (`{% call card(...) %}...{% endcall %}`) around the outer
  `scard` div only — standardizes the shell (class composition, variant modifier,
  optional eyebrow/tag), leaves all inner content to the caller. Rationale: the actual
  drift was in the OUTER div/class (6 different wrapper classes across 6 CSS files) —
  inner content (facts grid, meta rows, checklist forms, button rows) is legitimately
  different data per card type and forcing it into macro params would bloat the
  signature for no CSS-dedup benefit. See phase-01 for full per-family mapping.

## Unresolved Questions
None currently — see phase-01 for the one open item on whether inner BEM class names
(`tcard__top`, `note-card__head`, etc.) get renamed to a shared `scard__*` vocabulary
during migration or stay as-is (secondary decision, not blocking Phase 1 start).
