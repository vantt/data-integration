# Phase 3: Pill/Badge Convergence

## Context
Canonical badge already has a server-side component layer (`fmt_badge.py` →
`badge_catalog.py`, exposed as Jinja filters `| bdg_cls('domain')` / `| bdg_tip('domain')`)
— this phase does NOT touch that mechanism. It converges the 4 parallel pill families
that grew alongside it back onto `bdg` (or a thin macro wrapper where the filter
mechanism doesn't fit): `radio-pill`/`radio-pill__dot` (`fragments/modal_log_activity.html`,
`fragments/m15_identity_edit_form.html`), `freshness-badge`
(`fragments/c360_call_cockpit_panel.html:700`), `aq-session-card__pill`
(`fragments/c360_insight_panel.html`), `dedup-card__tag` (`dedup_review.html`).

Independent of Phase 1/2 (different CSS classes, different templates in most cases) —
can run in parallel with card migration.

## Requirements
- For each of the 4 families: determine if it's semantically a status badge (→ migrate
  to `bdg_cls`/`bdg_tip` filters + `badge_catalog.py` entry) or a genuinely different
  widget (e.g. `radio-pill` looks like a selectable radio control, not a status
  indicator — likely stays separate, confirm by reading its usage context first).
- Do not force a selectable-input widget (`radio-pill`) into the read-only status badge
  system — only converge things that are actually the same concept with different names.

## Files
- Modify: `crm/src/adapters/inbound/web/fmt_badge.py`, `badge_catalog.py` (add new
  domain entries only if a family is confirmed to be a true badge variant)
- Modify: `fragments/c360_call_cockpit_panel.html`, `fragments/c360_insight_panel.html`,
  `dedup_review.html` (swap confirmed-badge usages to `bdg_cls`/`bdg_tip` filters)
- Reference (read-only): `fragments/modal_log_activity.html`,
  `fragments/m15_identity_edit_form.html` (confirm `radio-pill` is an input control, not
  a badge, before deciding to leave it alone)

## Implementation Steps
1. Read all 4 families' template usage + CSS to classify: true badge drift vs.
   legitimately different widget.
2. For confirmed badge drift: add domain entry to `badge_catalog.py`, replace template
   markup with the filter-based pattern, restart CRM, click through affected screens.
3. For non-badge widgets (expected: `radio-pill`): leave as-is, document why in this
   file's Unresolved Questions or a short note — do not migrate for the sake of migrating.

## Tests
- Manual click-through of affected screens (call cockpit, insight panel, dedup review),
  3 themes.

## Risks / Rollback
- Misclassifying `radio-pill` as a badge would break its interactive/selectable
  behavior — verify by reading the JS/HTMX wiring around it before touching.
- Each family's migration is independently revertible.
