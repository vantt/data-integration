# Phase 3: Pill/Badge Convergence

## Status
Done (2026-07-09). Classification of all 4 families:
- **`dedup-card__tag`** — already converged as a SIDE EFFECT of Phase 1 (`scard__tag` in
  `macros/card.html` composes with `bdg`/`bdg--{{variant}}`). No separate work needed.
- **`radio-pill`/`radio-pill__dot`** — confirmed genuinely different widget: a segmented
  radio-selector control used in 16+ files, with real JS wiring (`layout.html:774-780`
  syncs `.radio-pill--on` with actual `<input type="radio">` checked state). Left alone —
  forcing this into the read-only `bdg` badge system would break real interactivity.
- **`aq-session-card__pill`** — displays a raw count ("N việc"), not a categorical status
  value — doesn't fit the `bdg_cls`/`bdg_tip` domain-filter mechanism (no "domain" for an
  integer). Left alone. Side finding (out of scope, noted for a future phase): at least 2
  OTHER count-pill implementations exist with the same shape-drift pattern the card family
  had — `wl-band__count` and `ship-count` (both `border-radius: var(--radii-pill)`,
  different colors/sizing each). Worth its own consolidation pass later.
- **`freshness-badge`** — converged to plain `bdg` (`0114ff2e`). Turned out to have ZERO
  CSS rules anywhere (rendered as unstyled plain text) — this wasn't really "drift into a
  parallel family," it was closer to a missing-styles bug; fixed by adopting the existing
  system instead of writing new CSS for it. Also removed its unused `data-ts` attribute
  (zero JS consumers anywhere).

Incidental finding (out of scope, not fixed): the surrounding Jinja expression for
`freshness-badge`'s content (`{{ ... | format_datetime_ict }} ICT`) renders "ICT ICT" —
`format_datetime_ict` (`fmt_date.py`) already appends "ICT" itself, making the template's
literal `" ICT"` redundant. Pre-existing (blames to `0cf6e763b`, 2026-07-02), unrelated to
this plan's scope — flagged for a separate fix, not touched here.


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
