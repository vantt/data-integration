# Phase 2: Card Migration Rollout

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
