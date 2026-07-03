# Phase 02 — Search + Hash Routing — Implementation Report

**Date:** 2026-07-02  
**Branch:** feature/task-detail-cockpit-backend  
**Skill root:** `.agents/skills/ui-spec/tools/wireframe/`

---

## Changes Made

### `client/app.js` (+39 lines → 231 total)

- `highlightAction(actionId)` — scrolls to and flashes `.action-btn[data-id=…]` with `.action-highlight` CSS class; `scrollIntoView` call guarded with `typeof` check for jsdom compatibility.
- `resolveInitialHash()` — reads `location.hash` on init; action-id pattern (`/^[A-Za-z]+-([A-Z]{1,2}\d+)/`) navigates to owning surface and highlights action; surface-id pattern navigates directly; invalid hash silently ignored.
- `navigateTo()` — appended `try { history.replaceState(null, "", "#" + surfaceId); } catch(e) {}` to sync URL hash without history spam.
- Init block — `resolveInitialHash()` called after initial render.

### `client/app-chrome.js` (+31 lines → 144 total)

- `buildSidebar()` — after `content.innerHTML = html`, creates `.sidebar-search` div with `#sidebar-search-input` and prepends it; wires `input` event to `filterSidebar`.
- `filterSidebar(term)` — hides/shows `.sidebar-item` elements by `data-sid` and name span substring (case-insensitive); if term exactly matches an action ID via `edgeById()`, calls `navigateTo` + `highlightAction`.

### `styles-phase2.mjs` (+18 lines)

- `.sidebar-search` / `input[type=search]` — dark-themed search box matching sidebar palette; `:focus` border highlight.
- `@keyframes action-flash` + `.action-highlight` — outline pulse + yellow background flash at 50% for 1.8s.

### `verify-runtime.mjs` (+62 lines)

- Added `url: "http://localhost/"` to JSDOM constructor — required for `history.replaceState` and `location.hash` assignment to work (jsdom same-origin check fails on `about:blank`).
- **Section E: hash routing** (3 assertions)
  - E1: `window.navigateTo(sid)` → `location.hash === "#sid"` + `.sidebar-item.active` present.
  - E2: `window.location.hash = "#sid"` → `resolveInitialHash()` → `.sidebar-item.active` present.
  - E3: iterates sidebar items to find first surface with `[data-id]` action buttons; sets action-id hash → `resolveInitialHash()` → owning surface active (waits 120ms for `highlightAction` setTimeout).
- **Section F: search filter** (2 assertions)
  - F1: type first surface ID into `#sidebar-search-input` → visible item count < total (1/54 for `S01`).
  - F2: clear input → visible count restored to total (54/54).

---

## Verification Output

```
node .agents/skills/ui-spec/tools/build.mjs --root crm/docs/ui-spec
  surfaces=54 actions=311 flows=6
  Wireframe v2 written: crm/docs/ui-spec/generated/wireframe-v2.html

node .agents/skills/ui-spec/tools/wireframe/verify-runtime.mjs --root crm/docs/ui-spec
  Section E: hash routing ...
    E1 navigateTo('F06') sets hash + sidebar active: OK
    E2 resolveInitialHash('#S01'): sidebar active OK
    E3 action hash '#A-S01-004' -> surface 'S01' active: OK
  Section F: search filter ...
    F1 search 'S01': 1/54 items visible -- OK
    F2 clear search: 54/54 items restored -- OK
  Surfaces exercised: 54 | Flows exercised: 6 | Errors: 0
  RESULT: PASS
```

---

## Implementation Notes

- `window.surfaceById` is a `const` declaration and is NOT a jsdom window global — all Section E assertions use DOM (`data-sid` attributes) to discover surface IDs.
- `scrollIntoView` is unimplemented in jsdom; guarded with `typeof` check so the highlight still fires in jsdom while working normally in real browsers.
- Line counts: `app.js` 231, `app-chrome.js` 144 — both under 250, no module extraction needed.
- `filterSidebar` references `surfaceById`, `edgeById`, `navigateTo`, `highlightAction` — all safe at event-handler time (all scripts are inlined and fully executed before any user input fires).

---

## Unresolved Questions

None.
