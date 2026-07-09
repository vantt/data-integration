# Review: c360_call_cockpit_panel.html freshness-badge → .bdg

## Scope
- File: `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (line 700, uncommitted/working-tree diff)
- Change: `<span class="freshness-badge" data-ts="{{ insight.insight.refreshed_at }}">` → `<span class="bdg">`
- 1 line changed, no logic touched. Part of `plans/260709-1034-card-badge-macro-consolidation` phase 3.

## Verification of requester's 4 claims

1. **`.freshness-badge` had zero CSS rules — confirmed.** Grep across `crm/src/adapters/inbound/web/static/` for `freshness-badge` returns no matches. It rendered unstyled.
2. **`data-ts` attribute had no JS consumer — confirmed.** Repo-wide grep for literal `data-ts` (not `data-ts-*`) returns zero hits outside this line. The only other `data-ts*` occurrences are `data-ts-theme`, `data-ts-accent`, `data-ts-font`, `data-ts-density`, `data-ts-numfont` in `layout.html`, all distinct attribute names consumed via `querySelectorAll('[data-ts-theme]')` etc. — genuinely unrelated.
3. **Zero remaining `freshness-badge` code references after this change — confirmed.** Only hits left repo-wide are documentation/generated artifacts (`crm/docs/ui-spec/00-overview.md`, `crm/docs/ui-spec/generated/surface-registry.yaml`, `crm/docs/ui-spec/generated/wireframe-v2.html` — all naming a component doc `C06-freshness-badge.md`, not the CSS class) and the phase-03 plan file itself. No second live template call site.
4. **Pre-existing "ICT ICT" double-suffix bug — confirmed pre-existing, confirmed not touched by this diff.** `git blame` on the surrounding lines shows line 701 (`{{ ... | format_datetime_ict }} ICT`) blames to commit `0cf6e763b` (2026-07-02), while only line 700 (the class attribute) is uncommitted. `fmt_date.py::format_datetime_ict` already appends `"%d/%m/%Y %H:%M ICT"` — the template's literal trailing `" ICT"` is redundant, producing the "ICT ICT" seen in the live-fetched output. This is correctly out of scope for this change; do not silently fix it here.

## Additional checks

5. **Plain `.bdg` (no modifier) is appropriate.** `.bdg` base rule at `ds-app.css:390` sets visible border, `text-transform: uppercase`, `font-weight: medium`, opaque `color: var(--fg-2)` (not faded/hidden) — it is not a deemphasized style. Grepping other templates (`c360_insight_panel.html` and 12 others) shows plain unmodified `class="bdg"` is the established convention for neutral/informational badges (channel preference, lifecycle stage, cohort, insight-type labels) with domain modifiers (`--good/--warn/--bad/--accent`) reserved for status/severity semantics. A timestamp caption is informational, not a status signal, so no modifier is correct and consistent with existing usage — no R2-visibility concern (the base class is not visually suppressed).
6. **No other CSS-adjacent code references to `freshness-badge` remain.** Only remaining hits are unrelated doc/generated-artifact references to a differently-named UI-spec component file `C06-freshness-badge.md` and the phase-03 plan's own task description — neither is a CSS class or template reference, no action needed.

## Assessment

No blockers. Single-line, git-revertible class-name swap; removes dead attribute and unstyled class; converges onto documented `.bdg` pattern consistent with 13+ other call sites. All requester claims independently verified against source (grep + git blame), not taken on faith.

## Unresolved Questions

- None for this change. The "ICT ICT" double-suffix bug (fmt_date.py `format_datetime_ict` already appends "ICT"; template appends a redundant literal " ICT" at line 701) is a real, separately-scoped, pre-existing bug worth a follow-up ticket/phase — flagging for awareness only, not asking for action here.
