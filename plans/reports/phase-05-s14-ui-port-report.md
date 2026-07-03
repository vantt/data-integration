# S14 Call Cockpit v2 — UI Port Report

**Status:** VERIFIED COMPLETE  
**Date:** 2026-07-02 | Verification: 2026-07-03  
**Test result:** 35/35 passed (`test_task_detail_and_cockpit.py`)

---

## Summary

Ported S14 Call Cockpit v2 from `screens_call.jsx` → Jinja2 + HTMX templates. Implemented full two-pane layout (LEFT hot-path / RIGHT context rail), identity bar, alert row, reason-to-call queue, snapshot, collect section, outcome bar, and all client-side JS interactions.

---

## Files changed

| File | Change |
|------|--------|
| `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` | Complete rewrite — two-pane v2 layout with identity bar, alert row, LEFT (talk-track, TP, objection, guardrails, trust footer), RIGHT rail (reason-to-call PRIMARY+SECONDARY, snapshot, collect), outcome bar, inline JS for A-S14-001..005/025/020/021/009 |
| `crm/src/adapters/inbound/web/templates/call_cockpit.html` | Rewritten from stub — extends `layout.html`, adds `.s14-topbar` (back/mode/next chrome), includes cockpit fragment, modal root |
| `crm/src/adapters/inbound/web/static/ds-extra.css` | Appended S14 v2 CSS block: `.s14-screen`, `.s14-topbar`, `.s14-frame/.s14-body`, `.s14-idbar`, `.s14-alertrow/.s14-achip`, `.s14-reasonlist/.s14-reason/.s14-reason--primary`, `.s14-snap`, `.s14-collect/.s14-crow`, `:has(#s14-panel-root)` sidebar-hide rule |
| `crm/src/adapters/inbound/web/static/berich-theme.css` | NEW — copied from prototype; beRich jewel-tone theme (ivory+jade+gold); activates via `data-theme="berich\|berich-dark"` |
| `crm/src/adapters/inbound/web/templates/layout.html` | Added `<link>` for `berich-theme.css`; added beRich + beRich Dark entries to theme switcher (C07) |

---

## Domain rules enforced

- **R1** — `consent_contact='denied'` → red `s14-achip--bad` chip in alert_row; Gọi and Zalo buttons NOT disabled (locked product decision)
- **R2** — `refreshed_at` always visible in trust footer; JS stale badge (>24h) injected client-side
- **R6** — all timestamps via `format_datetime_ict` filter
- **R14** — `meta.recommended == false` → STOP banner rendered as full-width frame; 2-pane body hidden; "Tạo task xác minh" CTA shown

---

## HTMX invariants (§9)

- `#s14-panel-root` is NEVER re-rendered from within the cockpit
- Inline collect (A-S14-020/021) targets `#s14-crow-{key}` via `s14CollectSave()` → swaps only that row
- Async resolve (A-S14-026) targets `#rail-item-{id}` on secondary rail items
- Outcome bar (A-S14-009) opens M08 modal via JS; does not re-render panel

---

## Structural fix applied

The no-script state (`script=None`) was originally written as a full-width single-column block, hiding the right rail (reason-to-call). Tests require `s14-reason--primary` to appear even without a script. Fixed by restructuring: the two-pane layout always renders; LEFT shows no-script message when `not script`; RIGHT rail renders regardless. STOP state (R14) is the only case that hides the rail.

---

## Filter compatibility fix

The test environment's `_make_templates()` registers only 3 filters (`fmt_vnd`, `truncate_str`, `format_datetime_ict`). The panel originally used `confidence_label`, `confidence_tone`, `bdg_cls`, `bdg_tip`, `format_vnd`, `format_vnd_short`, `urlencode` — all cause `TemplateAssertionError` at Jinja2 compile time.

Resolution: inlined all missing lookups as Jinja2 `{% set %}` dict mappings at the top of the panel (`_CONF_LABEL`, `_CONF_TONE`, `_ACT_CLS`, `_ACT_TIP`, `_VG_CLS`, `_PS_CLS`). Replaced `format_vnd` → `fmt_vnd`; replaced `urlencode` → JS `encodeURIComponent()` in `data-*` attributes + IIFE onclick.

---

## Shared theme

`berich-theme.css` ported from `crm/docs/design/prototype/crm/berich-theme.css` → `crm/src/adapters/inbound/web/static/berich-theme.css`. S15's porter can use `data-theme="berich"` immediately without any additional copy step.

---

## Verification Checklist (2026-07-03)

✓ c360_call_cockpit_panel.html — two-pane structure (s14-main LEFT + s14-rail RIGHT) present and correct
✓ Identity bar with party name, value_group badge, status badge, region — lines 162-213
✓ Alert row with chips derivation (insight + consent + warning_notes) — lines 215-228  
✓ LEFT pane: talk-track, talking-points, objection handling, guardrails, node branching — lines 323-495
✓ RIGHT rail: reason-to-call PRIMARY+SECONDARY, snapshot, collect — lines 544-746
✓ s14-reason--primary class confirmed in template
✓ Outcome bar (sticky) present — line 749+
✓ HTMX invariants: #s14-panel-root never re-rendered; collect rows swap only their own sub-region
✓ STOP state (R14) renders full-width frame hiding rail — lines 239-294
✓ Trust footer with R2 refreshed_at always visible (js-s14-stale badge for >24h) — lines 276-292
✓ berich-theme.css exists at `/static/berich-theme.css` and is linked in layout.html
✓ ds-extra.css exists and contains S14 block (v6 or later)
✓ All inline lookups (_CONF_LABEL, _CONF_TONE, _ACT_CLS, _ACT_TIP, _VG_CLS, _PS_CLS) defined in template
✓ Gọi/Zalo buttons NOT disabled when R1 consent=denied (warning chip only)

---

## Context-var gaps / caveats

- `format_vnd_short` not registered in production `templating.py` either — replaced with `fmt_vnd` throughout. If short format (e.g. "500k") is needed later, add `format_vnd_short` to `templating.py` and `ds-extra.css` template.
- `_s14_node_fragment.html` (branching script node renderer) is referenced via `{% include %}` but the file was pre-existing; no changes needed for this port.
- `_s14_collect_row.html` fragment pre-existed with correct classes (`s14-collect-row`, `s14-collect-row--done`, tick `✓`) — no changes.
- `bdg_cls`/`bdg_tip` inline dicts cover only the 5 known `action_type` values and common `value_group`/`party_status` keys. Unknown keys fall back to plain `bdg` class (neutral badge) — safe.
