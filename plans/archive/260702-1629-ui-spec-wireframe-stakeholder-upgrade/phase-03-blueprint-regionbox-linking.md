# Phase 03 — Blueprint ↔ Region-Box 2-Way Linking (Minimal)

## Context links
- `tools/wireframe/client/app.js` — `switchView(view)` controls `#view-layout` / `#view-blueprint` visibility; `currentSurface`
- `tools/wireframe/client/app-chrome.js` — `switchView` also toggles `.subtab` active state
- `tools/wireframe/html-shell.mjs` — `<pre id="blueprint-pre">` holds ASCII text; `#surface-subtabs` holds subtab buttons
- `tools/wireframe/client/render-regionbox.js` — region boxes rendered into `#view-layout`
- Phase 6 (grid renderer) will supersede most value of this phase — keep implementation minimal

## Decision note
Phase 6 (CSS grid) renders the spatial view far better than Blueprint ASCII linking can. This phase is kept **minimal**: ~1 day budget. If region-name extraction from ASCII proves brittle, ship the region-label → Blueprint tab switch only (half the work) and note the shortcut.

## Requirements
1. **Blueprint → Interactions:** clicking a recognized region name in the `<pre>` text switches subtab to Interactions and flashes the matching region-box header.
2. **Interactions → Blueprint:** clicking a region-box label (`<h3 class="region-title">`) in the Interactions subtab switches subtab to Blueprint and visually highlights the matching region name in the ASCII.
3. Both are cosmetic overlays; no data model changes.

## Files to modify / create

| File | Change |
|---|---|
| `tools/wireframe/client/blueprint-link.js` | New — post-process `<pre>` text; wire region-title clicks |
| `tools/wireframe/client/app.js` | Call `initBlueprintLinks()` after `renderMain()` |
| `tools/wireframe/html-shell.mjs` | Add `"blueprint-link.js"` to inlined file list in `buildClientScript` |
| `tools/wireframe/styles.mjs` | `.bp-region-span` hover/highlight styles; `.region-box-flash` animation |

## Implementation steps

### 1. New `client/blueprint-link.js`

```js
// blueprint-link.js — 2-way linking between Blueprint ASCII and Interactions region-boxes.
// Called from app.js renderMain(). Safe to call multiple times (idempotent via data-linked guard).

function initBlueprintLinks() {
  const pre = document.getElementById("blueprint-pre");
  if (!pre || pre.dataset.linked) return;
  pre.dataset.linked = "1";

  const surface = currentSurface;
  const regions = surface?.meta?.regions || [];
  if (!regions.length || !pre.textContent) return;

  // Replace region-name occurrences in ASCII text with clickable spans.
  // Escape region names for regex; sort longest-first to avoid partial matches.
  const sorted = [...regions].sort((a, b) => b.length - a.length);
  let html = esc(pre.textContent); // already-escaped text
  for (const r of sorted) {
    const escaped = r.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    // Only match whole-word occurrences (surrounded by non-word chars or line boundary)
    html = html.replace(
      new RegExp(`(?<![\\w.])${escaped}(?![\\w.])`, "g"),
      `<span class="bp-region-span" data-region="${escAttr(r)}">${esc(r)}</span>`
    );
  }
  pre.innerHTML = html;

  // Blueprint span → switch to Interactions + flash region box
  for (const span of pre.querySelectorAll(".bp-region-span")) {
    span.addEventListener("click", () => {
      switchView("layout");
      flashRegionBox(span.dataset.region);
    });
  }

  // Region-box title → switch to Blueprint + highlight span
  for (const title of document.querySelectorAll("#view-layout .region-title")) {
    title.style.cursor = "pointer";
    title.addEventListener("click", () => {
      switchView("blueprint");
      flashBlueprintSpan(title.dataset.region || title.textContent.trim());
    });
  }
}

function flashRegionBox(regionName) {
  const box = document.querySelector(`#view-layout [data-region="${CSS.escape(regionName)}"]`);
  if (!box) return;
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  box.classList.add("region-box-flash");
  setTimeout(() => box.classList.remove("region-box-flash"), 1600);
}

function flashBlueprintSpan(regionName) {
  const span = document.querySelector(`#blueprint-pre .bp-region-span[data-region="${CSS.escape(regionName)}"]`);
  if (!span) return;
  span.scrollIntoView({ behavior: "smooth", block: "nearest" });
  span.classList.add("bp-span-active");
  setTimeout(() => span.classList.remove("bp-span-active"), 1600);
}
```

Note: `esc`, `escAttr`, `switchView`, `currentSurface` are all globals from inlined prior files.

### 2. Wire in `app.js`

Add `initBlueprintLinks()` call at the end of `renderMain()`:
```js
// Blueprint ↔ region-box 2-way links (blueprint-link.js)
initBlueprintLinks();
```

Also reset `data-linked` guard when `renderMain` is called for a new surface — add `document.getElementById("blueprint-pre").removeAttribute("data-linked")` at the start of `renderMain` (before blueprint-pre text is set).

### 3. `html-shell.mjs` — add to inlined list

In `buildClientScript`, add `"blueprint-link.js"` after `"render-regionbox.js"`:
```js
const files = [
  "region-model.js",
  "render-regionbox.js",
  "blueprint-link.js",   // ← new
  ...
];
```

### 4. CSS additions — `styles.mjs`

```css
/* Blueprint region spans */
.bp-region-span { cursor:pointer; background:#1e3a5f; border-radius:2px; padding:0 1px; }
.bp-region-span:hover { background:#2563eb; color:#fff; }
.bp-span-active { background:#f59e0b !important; color:#000 !important; }

/* Region box flash */
@keyframes region-flash { 0%,100%{background:inherit} 30%{background:#fde68a} }
.region-box-flash { animation:region-flash 1.6s ease; }
```

## Validation
1. Open wireframe → S14 Blueprint subtab → click a region name in ASCII → switches to Interactions, matching region box flashes.
2. In Interactions subtab → click a region-box title → switches to Blueprint, span highlights.
3. Surfaces with no regions: no spans injected, no errors thrown.
4. `verify-runtime.mjs` → green (no new assertions required; existing tests must not regress).

## Risks & rollback
- **Risk:** region names are short tokens (e.g. `header`) that appear in non-region contexts in ASCII — the whole-word regex guard mitigates most false positives; dotted names (e.g. `sidebar.core_info`) fine since `.` is a non-word char boundary.
- **Risk:** `pre.innerHTML` assignment breaks if `esc()` double-encodes — confirm `esc` returns HTML-safe string; use `textContent` snapshot first.
- **Decision gate:** if linking proves unreliable (>20% false-positive rate on S14 spot-check), ship region-title → Blueprint switch only (lines 46-52 of blueprint-link.js) and skip Blueprint → region-box direction. Document in phase report.
- **Rollback:** remove `"blueprint-link.js"` from inlined list + `initBlueprintLinks()` call; zero residual impact.
