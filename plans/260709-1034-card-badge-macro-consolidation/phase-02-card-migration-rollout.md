# Phase 2: Card Migration Rollout

## Status
In progress (2026-07-09). Batch 1 done: `tasks_board.html` (`68857088`) + `note_card.html`/
`note_card_typed.html` (`a59a9d31`). Both verified live against the running server with real
data (not just synthetic render tests). Extended `card()` with an `attrs` param (raw
attribute pass-through — needed for `tcard`'s `id`/`draggable`) and discovered a real class
of regression this migration style risks: the OLD family classes sometimes carried layout/
interaction behavior beyond visual styling (`tcard`'s flex/gap/cursor/hover,
`note-card`'s hover-reveal + inter-sibling spacing) that bare `.scard` doesn't provide —
fixed via additive modifier classes (`.task-card`, `.note-item`) applied through the macro's
`extra_class` param, NOT by expanding `.scard` itself (which is shared by unrelated call
sites). Apply the same "check for base-class side rules, not just visual ones" scrutiny to
the remaining batch below.

Remaining (batch 2, not started): `customer_360.html`, `order_detail.html`,
`conversation_detail.html`, `fragments/c360_insight_panel.html` — meaningfully harder:
`customer_360`/`order_detail` already use canonical `.scard` (no class rename needed) but
carry heavy `facts()`/`card_header()` extraction opportunity (78 `.facts` usages across 6
files per Phase 1 survey); `c360_insight_panel.html` has the `aq-session-card` checklist
form which needs the same base-class-side-rule check as this batch.


## Context
Phase 1 produced a validated `card()` macro (`macros/card.html`) and proved it on
`dedup_review.html`. This phase migrates the remaining 5 template families to it:
`customer_360.html`/`order_detail.html`/`conversation_detail.html` (`scard`),
`tasks_board.html` (`tcard`), `fragments/note_card.html` + `note_card_typed.html`
(`note-card`), `fragments/c360_insight_panel.html` (`aq-card`/`aq-session-card`),
`conversation_detail.html` (`conv-cust-card`).

## Requirements
- Migrate one template at a time, not all at once — each is an independent, revertible
  change (file ownership is clear, no shared state between templates).
- Keep old CSS classes (`.tcard`, `.note-card`, etc.) in place until ALL call sites for
  that class are migrated, then remove the now-dead CSS rule in the same commit as the
  last template migrated off it — don't leave orphaned CSS.
- Do not touch `btn` or unrelated `bdg` usages in these templates — scope is card markup only.

## Files
- Modify: `crm/src/adapters/inbound/web/templates/customer_360.html`,
  `order_detail.html`, `conversation_detail.html`, `tasks_board.html`,
  `fragments/note_card.html`, `fragments/note_card_typed.html`,
  `fragments/c360_insight_panel.html`
- Modify (remove dead rules once orphaned): `crm/src/adapters/inbound/web/static/ds-app.css`,
  `ds-extra.css`, `ds-crm.css` (wherever each old class is defined — grep before removing)
- Reference: `macros/card.html` from Phase 1 (do not redesign the API mid-rollout — if a
  template exposes a gap in the macro, go back and extend the macro signature, then
  re-verify Phase 1's pilot still renders correctly before continuing).

## Implementation Steps
1. Per template: read current card markup, swap to `{% from "macros/card.html" import
   card %}` + `{{ card(...) }}` calls, restart CRM, click through the affected screen in
   all 3 themes.
2. After each template migration, grep remaining usages of that template's old card class
   across the codebase to confirm zero call sites remain before deleting its CSS rule.
3. Repeat for all 5 remaining templates.

## Tests
- Manual click-through per migrated screen, 3 themes, same as Phase 1.
- Grep for the old class name (`tcard`, `note-card`, `aq-card`, `conv-cust-card`) after
  each migration to confirm no orphaned references before deleting CSS.

## Risks / Rollback
- Each template migration is independently revertible via git — do not batch multiple
  templates into one commit.
- If a template's card usage turns out functionally different enough to need a new
  macro variant param, extend `macros/card.html` rather than forking a second macro.
