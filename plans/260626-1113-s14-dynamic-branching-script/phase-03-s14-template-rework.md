# Phase 03 — S14 Template Rework: Progressive Node Rendering

**Status:** pending  
**Effort:** 2h  
**Blockers:** Phase 02 (interpreter endpoint live + returning node JSON)  
**File ownership:** `crm/src/adapters/inbound/web/templates/fragments/c360_call_cockpit_panel.html` (sole owner this phase)

---

## The Core Coupling Problem

The current template (`c360_call_cockpit_panel.html`) renders the **entire script as a document** — talk-track, all talking points, all objections, all guardrails visible at once. This is right for the flat v2 schema. For branching, it must instead render **only the current node** and a small set of outcome buttons.

Lines to understand before touching:

| Lines | What they do |
|-------|-------------|
| 36–44 | `{% set ap = script.approach %}` and locals — still needed for STOP gate + trust footer |
| 79–112 | STOP banner (R14) — **unchanged** |
| 115–166 | Talk-track block (opening_message, channel toggle) — **kept for legacy path** |
| 168–199 | Talking-points block — **kept for legacy path** |
| 202–243 | Objection-handling block — **kept for legacy path** |
| 245–257 | Guardrails strip — **kept in branching path too** (see schema Q3 resolution) |
| 261–277 | Trust footer — **unchanged** |
| 279–312 | Outcome bar (sticky) — **kept but wired differently for branching** |
| 321–466 | Inline `<script>` — **extended** with node navigation JS |

---

## Branching Detection (Jinja2)

Add immediately after the existing locals block (line 44), before the `{% if is_stop %}` check:

```jinja2
{# ── Branching detection ──────────────────────────────────────────────── #}
{% set is_branching = (script.nodes is defined and script.entry_node is defined) %}
{% set entry_node_id = script.entry_node | default('root') %}
{% set initial_node = script.nodes[entry_node_id] if is_branching else none %}
```

`is_branching` gates all new branching blocks. Legacy blocks are wrapped in `{% if not is_branching %}`.

---

## New HTML Structure (branching path only)

Inserted after the STOP banner `{% else %}` block (line 114), before the existing talk-track block:

```jinja2
{% if is_branching %}
{# ── BRANCHING: node renderer ─────────────────────────────────────────── #}
<div class="s14-block s14-node-wrap" id="s14-node-area"
     data-entry-node="{{ entry_node_id }}"
     data-party-id="{{ party_id }}">

  {# Initial node rendered server-side; subsequent nodes swapped by HTMX #}
  {% include "fragments/_s14_node_fragment.html" with context %}

</div>{# /#s14-node-area #}

{# Guardrail strip — always visible even in branching mode (schema Q3 resolution) #}
{% if ap.do_not and ap.do_not | length > 0 %}
<div class="s14-guard" role="note" aria-label="Guardrails">
  {# ... identical to existing guardrail block lines 247–257 ... #}
</div>
{% endif %}

{% else %}
{# ── LEGACY FLAT RENDER (existing blocks, untouched) ─────────────────── #}
  {# talk-track block (lines 116–166) #}
  {# talking-points block (lines 168–199) #}
  {# objection-handling block (lines 202–243) #}
  {# guardrails block (lines 245–257) #}
{% endif %}{# /is_branching #}
```

### New fragment: `_s14_node_fragment.html`

This sub-fragment renders a single node. It is both:
- Included server-side on initial page load (via `{% include %}`)
- Returned by the interpreter endpoint as an HTMX response (Phase 02 endpoint returns JSON; the HTMX swap renders this fragment)

**Wait** — there is a mismatch here. The interpreter endpoint (Phase 02) returns **JSON**. HTMX `hx-post` with `hx-swap="innerHTML"` expects **HTML**. Two options:

**Option A (recommended for KISS):** The interpreter endpoint returns an **HTML fragment** directly (render the node fragment server-side in the handler), not JSON. This is the HTMX-native approach — no client-side JSON parsing, no extra JS templating.

**Option B:** Keep the endpoint returning JSON, add JS to construct the HTML client-side. More JS, harder to maintain.

**Decision: Option A.** The `script_nav_handler.py` returns `TemplateResponse("fragments/_s14_node_fragment.html", {node: ..., party_id: ...})` for the HTMX swap. The JSON contract described in Phase 02 is used only when the caller is not HTMX (e.g. unit tests). Add a `HX-Request` header check: if HTMX request → HTML response; else → JSON. This is a FastAPI `Request` header check, one line.

Update Phase 02 endpoint accordingly: check `request.headers.get("HX-Request")` → branch to HTML or JSON response.

---

## `_s14_node_fragment.html` — Node Fragment Spec

```jinja2
{# _s14_node_fragment.html — single node render for S14 branching mode
   Context vars:
     node      : dict  — {id, kind, say, hint, options[{label, outcome, next}]}
     party_id  : str
     terminal  : bool  — true when no further navigation available
#}
{% if terminal %}
<div class="s14-node s14-node--terminal">
  <div class="s14-node__say">Cuộc gọi hoàn thành. Ghi kết quả bên dưới.</div>
</div>
{% else %}
<div class="s14-node s14-node--{{ node.kind }}" data-node-id="{{ node.id }}">
  <div class="s14-node__kind-tag">{{ node.kind }}</div>
  <div class="s14-node__say">"{{ node.say }}"</div>
  {% if node.hint %}
  <div class="s14-node__hint">{{ node.hint }}</div>
  {% endif %}

  <div class="s14-node__options" role="group" aria-label="Phản hồi của khách">
    {% for opt in node.options %}
    <button class="s14-node__opt s14-node__opt--{{ opt.outcome }}"
            type="button"
            hx-post="/api/parties/{{ party_id }}/script-nav"
            hx-vals='{"current_node_id": "{{ node.id }}", "outcome": "{{ opt.outcome }}"}'
            hx-target="#s14-node-area"
            hx-swap="innerHTML"
            hx-headers='{"Content-Type": "application/json"}'
            onclick="s14NavStep('{{ node.id }}', '{{ opt.outcome }}')">
      {{ opt.label }}
    </button>
    {% endfor %}
  </div>
</div>
{% endif %}
```

**Key HTMX wiring:**
- `hx-post` → `POST /api/parties/{party_id}/script-nav`
- `hx-vals` → injects `current_node_id` and `outcome` as JSON body
- `hx-target="#s14-node-area"` → swaps the node area with the returned fragment
- `hx-swap="innerHTML"` → replaces contents, keeps the wrapper div (which holds `data-entry-node` for JS fallback)

---

## Outcome Bar Adaptation (branching mode)

The existing sticky outcome bar (lines 279–312) fires `s14OpenOutcome(outcome)` which opens M08 modal directly. In branching mode, the outcome buttons are **on the node fragment itself** — the outcome bar buttons become **redundant for mid-call navigation** but are still needed for:
1. Terminal node state (call is over → log final outcome via M08)
2. Escape hatch (staff skips the node tree, logs outcome directly)

**Solution:** Keep the outcome bar unchanged. In branching mode, add a CSS class `s14-outcome--secondary` so it visually recedes (lower prominence). Node option buttons are the primary interaction surface. Both paths write to the same M08 → `crm_activity` chain.

The existing `s14OpenOutcome(outcome)` JS function is untouched.

---

## Inline JS Extension

Add to the existing inline `<script>` block (after line 466, before the closing `}());`):

```javascript
// ── Branching: track current node in hidden field + log nav step ─────
var _currentNodeId = {{ initial_node.id | tojson if initial_node else '"root"' }};

window.s14NavStep = function (nodeId, outcome) {
  _currentNodeId = nodeId;
  // After HTMX swap completes, update _currentNodeId from new node's data attr
  document.addEventListener('htmx:afterSwap', function handler(e) {
    if (e.target && e.target.id === 's14-node-area') {
      var newNode = e.target.querySelector('[data-node-id]');
      if (newNode) { _currentNodeId = newNode.getAttribute('data-node-id'); }
      document.removeEventListener('htmx:afterSwap', handler);
    }
  });
};
```

`_currentNodeId` is a module-level JS variable — exactly the "client holds current_node_id" state-light model from the roadmap. It is lost on page refresh (resets to `entry_node`) — acceptable for v1.

---

## Channel Toggle in Branching Mode

The existing channel toggle (calls/Zalo swap via `s14SwitchChannel`) reads `PRIMARY_MSG` / `FALLBACK_MSG` baked at render time. In branching mode, each node's `say` is the channel-primary text. The `approach.fallback_message` (top-level) still applies as a channel-fallback message for the Zalo button — but it is a single global message, not per-node.

**v1 decision:** In branching mode, hide the channel toggle buttons. The branching script is phone-optimised. If staff switches to Zalo, they close the tree and use the flat `fallback_message` from `approach`. This is acceptable for v1 scope.

Implementation: `{% if not is_branching %}` around the channel toggle `<div class="s14-chan">` block (lines 121–139).

---

## Mapping Old Blocks → New Branching Blocks

| Old block | Branching equivalent | Disposition |
|-----------|---------------------|-------------|
| Talk-track (`opening_message`) | `node.say` on `root` node | Legacy only |
| Talking-points tick-list | Distributed into `pitch` node `say` text | Legacy only |
| Objection-handling accordion + search | `objection` kind nodes | Legacy only |
| Guardrail strip (`do_not`) | Kept as global strip above outcome bar | Both paths |
| Trust footer | Unchanged | Both paths |
| Outcome bar | Kept; secondary role in branching | Both paths |
| Channel toggle | Hidden in branching mode | Legacy only |
| STOP banner | Unchanged, fires before branching check | Both paths |

---

## Template State Summary

After this phase, the template has three render paths:

```
script present?
  └─ NO  → ST-CALL-NO-SCRIPT (unchanged, lines 21–31)
  └─ YES
       └─ recommended = false → STOP banner (R14, unchanged, lines 79–112)
       └─ recommended = true
            └─ is_branching = true  → node renderer + guardrail + trust footer + outcome bar
            └─ is_branching = false → legacy flat (unchanged blocks) + trust footer + outcome bar
```

---

## Tests / Validation

| Check | How |
|-------|-----|
| Legacy flat script still renders correctly | Load a customer without `nodes` key in their script; verify all old blocks appear |
| Branching initial render | Load 603264280 (Phase 01 file); verify only `root` node's `say` + 4 option buttons appear |
| HTMX nav step | Tap "Gọi được — khách nghe"; verify `#s14-node-area` swaps to `reached_interest_check` node |
| Terminal node | Tap through to a `next: null` option; verify terminal message and no nav buttons |
| STOP gate still fires | Script with `recommended=false` AND `nodes` present → STOP banner, no node rendered |
| Page refresh resets to root | Refresh mid-tree → `root` node shown again (state-light acceptable) |
| Trust footer always visible | Both branching and legacy paths show freshness + confidence |

---

## Rollback

Revert `c360_call_cockpit_panel.html` to pre-Phase-03 state (git checkout). Delete `_s14_node_fragment.html`. No backend changes needed (Phase 02 endpoint still exists but is never called from the template).

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| HTMX `hx-vals` with JSON body not supported in HTMX v1.x | Medium | High | Check HTMX version in CRM; `hx-vals` sends as form params by default — may need `hx-ext="json-enc"` or JS `fetch` instead |
| `{% include %}` of sub-fragment — Jinja2 context scoping | Low | Medium | Pass explicit vars to include: `{% include ... with {"node": initial_node, "terminal": false, "party_id": party_id} only %}` |
| CRM image rebuild required for template changes | Certain | Low | Expected — document in PoC phase (Phase 05) |

### HTMX version check (important before build)

Verify HTMX version used in CRM before implementing `hx-vals` JSON body:
```bash
grep -r "htmx" crm/src/adapters/inbound/web/templates/ | grep "script src" | head -5
```
If HTMX < 1.9, `hx-vals` only sends form-encoded. In that case, use a small JS `fetch` wrapper in `s14NavStep` instead of declarative `hx-post` on each button. The handler on the server side remains the same.
