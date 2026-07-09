# Phase 1: Card Macro Design + Pilot

## Status
Done (2026-07-09). `macros/card.html` + `macros/facts.html` created, `dedup_review.html`
migrated (4 call sites), `.scard--survive`/`.scard__tag` CSS added to `ds-app.css`.
Verified via direct Jinja render (byte-diff old vs new output, both `modal_merge` and
candidates-list branches — DB had 0 pending dedup candidates so a live browser
click-through wasn't possible). code-reviewer confirmed: markup equivalent, XSS-safe
(autoescape holds, verified with a `<script>` payload), no dropped attributes.

**Accepted trade-off:** migrated cards render +8px taller (top/bottom) in default density
because `.scard`'s shared `--card-pad` token is uniform, while the old `.dedup-card` used
asymmetric padding (`--sp-4 --sp-5`). User confirmed this is desired — visual convergence
to the same padding as every other `scard` is the point of consolidation, not a bug.
Carries forward to Phase 2: the same padding normalization will apply when
`customer_360.html`/`tasks_board.html`/etc. migrate — no separate decision needed there.

Dead CSS confirmed (0 remaining template usages): `.dedup-card`, `.dedup-card--survive`,
`.dedup-card__tag` in `ds-extra.css:234-236` — left in place per this phase's plan (Phase
2 removes dead CSS once ALL families are migrated, not per-template).


## Context
Read the real markup of all 6 drifted families (2026-07-09). Finding: every family's
DIFFERENCE is in its inner content (facts grid, meta rows, checklist form, button row) —
the OUTER wrapper (a div, optional eyebrow line, optional tag pill, optional state
modifier) is structurally identical everywhere. `scard` is already the canonical name
(`DESIGN_SYSTEM.md` §10). Concrete evidence per family:

| Family | File | Outer shape | Inner content (stays as caller body) |
|---|---|---|---|
| `scard` (plain) | `customer_360.html:108` | `<div class="scard">` | `row-between` header (caption + edit btn) + arbitrary fields |
| `scard` (eyebrow) | `customer_360.html:262-263` | `<div class="scard"><div class="caption scard__eyebrow">Headline</div>` | KPI figures |
| `dedup-card` | `dedup_review.html:15-23,95-104` | `<div class="dedup-card dedup-card--survive">` + `<span class="dedup-card__tag bdg bdg--accent">GIỮ LẠI</span>` | `.facts`/`.fact` k/v list + optional link |
| `tcard` | `tasks_board.html:107-163` | `<div class="tcard">` | `tcard__top` (badges) + title + repeated `tcard__meta` rows |
| `note-card` | `fragments/note_card_typed.html:8` | `<div class="note-card">` | `note-card__head` (who+acts) + `note-card__body` + optional outcome footer |
| `aq-card` | `fragments/c360_insight_panel.html:109-147` | `<div class="aq-card">` | `aq-card__top` (badge+value) + rationale + optional ctx chips + optional `aq-card__foot` |
| `aq-session-card` | `fragments/c360_insight_panel.html:48-100` | `<div class="aq-session-card">` | `<form>` wrapping head/body/cta — fits fine since it's one contiguous block |

Conclusion: a **thin shell macro** using Jinja's `{% call %}` block (one free-form body
slot) fits every case — no family needs to be excluded. Do not build a "kitchen sink"
macro with a param per inner element; that would bloat the signature for content that
isn't actually duplicated CSS, just similar-looking markup.

**Design principle (no dispatch-by-type):** `card()` has no `type`/`kind` param and never
will. There is one shell; every concrete card (dedup card, tcard, note card, ...) calls
`card()` and inserts its own content between `{% call %}`/`{% endcall %}` — either
hand-written HTML (one-off content) or by calling smaller helper macros (see below). The
shell macro never branches on what kind of card it's wrapping.

**Sub-macro extraction (Rule of Three):** inner content that repeats ≥3 times across
*different* templates gets pulled into its own small pure-param macro (call `{{ x(...) }}`
directly, no `{% call %}` needed — it returns fully-formed HTML from its arguments, unlike
the shell). Two candidates identified from the survey, to confirm/build during this phase:
- `facts(items)` — the `.facts`/`.fact` k/v list, seen in `dedup-card` (2 places,
  `dedup_review.html:17-22,97-101,107-110`) and implied for `scard` by `DESIGN_SYSTEM.md`
  §10 grouping `scard`/`facts`/`fact` together — grep `customer_360.html`/`order_detail.html`
  for `.facts` usage during this phase to confirm the real count before extracting.
- `card_header(title, edit_href=none)` — the `row-between` caption+edit-button pattern,
  seen ≥3× in `customer_360.html` (lines 108-111, 162-165, 183-186).
Do NOT extract patterns seen only 1-2× (e.g. `aq-card__foot`'s button row — each instance
has different buttons) — leave those as hand-written content inside `{% call card() %}`.
Both sub-macros, if built, live in `templates/macros/` alongside `card.html` (one file
each, e.g. `macros/facts.html`, `macros/card_header.html`) per the same docstring
convention.

## Macro Design (starting point — confirm during pilot, adjust if reality disagrees)

```jinja
{# @surface DS · Card shell | @kind MACRO
   Usage: {% from "macros/card.html" import card %}
          {% call card(eyebrow="Headline") %} ...body markup... {% endcall %}

   eyebrow      str|None  small accent caption line above body (was scard__eyebrow)
   tag          str|None  short pill label top of card (was dedup-card__tag text)
   tag_variant  str       bdg modifier suffix for the tag, e.g. "accent" → "bdg--accent"
   variant      str       card state modifier, e.g. "survive" → class "scard--survive"
   extra_class  str       escape hatch for one-off spacing/layout needs; do not use to
                          smuggle back a whole parallel class family — if you need this
                          often for the same reason, that's a signal to add a real param
#}
{% macro card(eyebrow=none, tag=none, tag_variant='', variant='', extra_class='') %}
<div class="scard{% if variant %} scard--{{ variant }}{% endif %}{% if extra_class %} {{ extra_class }}{% endif %}">
  {% if tag %}<span class="scard__tag bdg{% if tag_variant %} bdg--{{ tag_variant }}{% endif %}">{{ tag }}</span>{% endif %}
  {% if eyebrow %}<div class="caption scard__eyebrow">{{ eyebrow }}</div>{% endif %}
  {{ caller() }}
</div>
{% endmacro %}
```

Per-family call shape (for the pilot + phase 2 reference):
- `dedup-card--survive` → `{% call card(variant='survive', tag='GIỮ LẠI', tag_variant='accent') %}<div class="facts">...</div><a ...>Xem hồ sơ</a>{% endcall %}`
- `dedup-card` (plain) → `{% call card(tag='GỘP VÀO') %}...{% endcall %}`
- `tcard` → `{% call card() %}<div class="tcard__top">...</div>...{% endcall %}` (inner `tcard__*` class names kept as-is for phase 1 — renaming them to a shared vocabulary is optional, decide after pilot, not required for the CSS-dedup goal)
- `note-card`, `aq-card`, `aq-session-card` → same pattern, no eyebrow/tag needed, all existing inner markup unchanged inside `{% call %}...{% endcall %}`

## Requirements
- Do not add params for anything that isn't actually duplicated CSS across families —
  keep the signature exactly as above unless the pilot proves a gap.
- Follow existing macro docstring convention (see `templates/fragments/_wl_row.html:1-8`
  for the `@surface`/`@kind MACRO`/`Usage:` header format) — already reflected above.
- Create `templates/macros/` as a new directory — first macro file(s) in it (`card.html`,
  plus `facts.html`/`card_header.html` if the Rule-of-Three grep confirms them).
- Definition-site vs call-site: `templates/macros/*.html` files contain ONLY `{% macro %}`
  blocks — never rendered directly by a Flask route, never `{% extends %}` anything. Real
  pages/fragments (`dedup_review.html`, etc.) are the call sites: they `{% from
  "macros/card.html" import card %}` at the top and use `{% call card(...) %}...{% endcall %}`
  or `{{ facts(...) }}` in their body. The import path is always relative to the Jinja
  templates root, not to the calling file's own folder.

## Files
- Create: `crm/src/adapters/inbound/web/templates/macros/card.html`
- Modify (pilot only): `crm/src/adapters/inbound/web/templates/dedup_review.html` — has
  both card variants (`--survive` and plain) in one screen, best single-file proof.
- Reference (read-only): `crm/docs/design/DESIGN_SYSTEM.md`,
  `crm/src/adapters/inbound/web/static/ds-app.css` (`.scard` base rule),
  `.dedup-card`/`.dedup-card--survive` rules (grep for exact file before Phase 2 cleanup).

## Implementation Steps
1. Create `templates/macros/card.html` with the macro above.
2. Migrate `dedup_review.html`'s 4 card instances (2 in the merge modal, 2 in the detail
   view) to `{% from "macros/card.html" import card %}` + `{% call card(...) %}`.
3. Add a `.scard--survive` CSS rule (copy `.dedup-card--survive`'s actual declarations)
   to wherever `.scard` is defined; do not delete `.dedup-card--survive` yet (Phase 2
   handles dead-CSS removal once all call sites are confirmed migrated).
4. Restart CRM (`docker compose restart crm` — bind-mounted templates, no rebuild) and
   click through `/dedup` in all 3 themes (check `layout.html` for the actual theme
   toggle mechanism — `data-theme` attribute per `DESIGN_SYSTEM.md` §"Attribute" table:
   unset=dark, `light`, `finance`).
5. Confirm no visual diff vs. pre-migration.

## Tests
- Manual click-through of `/dedup`, 3 themes — no automated visual regression suite
  exists for CRM templates; do not invent one for this task.
- If `crm/tests/` has anything importing/rendering this template, run that subset.

## Risks / Rollback
- If pilot reveals the shell macro is insufficient for some case, extend the macro
  signature (still additive, no breaking change) rather than forking a second macro.
- Rollback: pilot touches only `dedup_review.html` + new `macros/card.html` — revert via
  git if visual regression found, no other template affected yet.
