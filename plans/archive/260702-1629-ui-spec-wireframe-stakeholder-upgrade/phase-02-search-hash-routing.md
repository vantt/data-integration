# Phase 02 — Search + Hash Routing

## Context links
- `tools/wireframe/client/app.js` — `navigateTo(surfaceId)`, `surfaceById` index, `edgeById` (from region-model.js), init block at bottom
- `tools/wireframe/client/app-chrome.js` — `buildSidebar()` generates `.sidebar-item[data-sid]` divs; `updateSidebarActive()`
- `tools/wireframe/client/region-model.js` — `edgeById(id)` returns interaction object; `esc`, `escAttr`
- `tools/wireframe/html-shell.mjs` — HTML markup, `<div id="sidebar-header">`, `<div id="sidebar-content">`
- `tools/wireframe/styles.mjs` — CSS constants exported as `CSS`

## Requirements
1. `#S14` in URL hash → navigate to surface S14 on load.
2. `#A-S14-009` in URL hash → navigate to its surface, visually highlight the action button.
3. Search box above sidebar content filters `.sidebar-item` by surface id or name substring (case-insensitive).
4. If search term matches an action id exactly, scroll to that surface and flash the matching region row.
5. Hash updated in `history.replaceState` on every `navigateTo` call (no page reload).

## Files to modify / create

| File | Change |
|---|---|
| `tools/wireframe/client/app.js` | Hash read on init; hash write in `navigateTo`; action highlight helper |
| `tools/wireframe/client/app-chrome.js` | Search input markup injection into `buildSidebar`; filter logic |
| `tools/wireframe/styles.mjs` | Search box styles; action-highlight flash animation |
| `tools/wireframe/html-shell.mjs` | No markup change needed — search input injected by `buildSidebar` at runtime |
| `tools/wireframe/verify-runtime.mjs` | Extend with hash + search assertions |

## Implementation steps

### 1. Hash routing — `app.js`

**Read hash on init** (add before `initFlowBar()` call):
```js
function resolveInitialHash() {
  const hash = location.hash.slice(1); // e.g. "S14" or "A-S14-009"
  if (!hash) return;
  // action id pattern: starts with a letter, contains a dash and a surface id segment
  const actionMatch = hash.match(/^[A-Za-z]+-([A-Z]{1,2}\d+)/);
  if (actionMatch) {
    const sid = actionMatch[1];
    navigateTo(sid);
    highlightAction(hash);
  } else if (surfaceById[hash]) {
    navigateTo(hash);
  }
}
```

**Hash write** — append to `navigateTo`:
```js
history.replaceState(null, "", "#" + surfaceId);
```

**Action highlight helper**:
```js
function highlightAction(actionId) {
  // Wait one tick for renderMain to complete
  setTimeout(() => {
    const btn = document.querySelector(`[data-id="${CSS.escape(actionId)}"]`);
    if (!btn) return;
    btn.scrollIntoView({ behavior: "smooth", block: "center" });
    btn.classList.add("action-highlight");
    setTimeout(() => btn.classList.remove("action-highlight"), 1800);
  }, 50);
}
```

Call `resolveInitialHash()` at end of init block (after `renderMain()` + sidebar calls).

### 2. Search box — `app-chrome.js`

**Inject input** at top of `buildSidebar()` before the groups loop:
```js
const searchWrap = document.createElement("div");
searchWrap.className = "sidebar-search";
searchWrap.innerHTML = `<input id="sidebar-search-input" type="search" placeholder="Search surfaces…" autocomplete="off">`;
content.prepend(searchWrap);
document.getElementById("sidebar-search-input")?.addEventListener("input", e => filterSidebar(e.target.value));
```

**Filter function** (add to app-chrome.js):
```js
function filterSidebar(term) {
  const q = term.trim().toLowerCase();
  for (const item of document.querySelectorAll(".sidebar-item")) {
    const sid = (item.dataset.sid || "").toLowerCase();
    const name = (item.querySelector("span:last-child")?.textContent || "").toLowerCase();
    const show = !q || sid.includes(q) || name.includes(q);
    item.style.display = show ? "" : "none";
  }
  // Action-id exact match: navigate + highlight
  if (q && surfaceById) {
    const edge = edgeById(term.trim()); // edgeById from region-model.js
    if (edge?.from && surfaceById[edge.from]) {
      navigateTo(edge.from);
      highlightAction(term.trim()); // highlightAction from app.js
    }
  }
}
```

### 3. CSS additions — `styles.mjs`

Append to the CSS template literal:
```css
/* Sidebar search */
.sidebar-search { padding:8px 10px 4px; }
.sidebar-search input[type=search] {
  width:100%; box-sizing:border-box; padding:5px 8px;
  background:#1e293b; border:1px solid #334155; border-radius:6px;
  color:#e2e8f0; font-size:12px; outline:none;
}
.sidebar-search input[type=search]:focus { border-color:#60a5fa; }

/* Action highlight flash */
@keyframes action-flash {
  0%,100% { background: inherit; }
  30%      { background: #fde68a; }
}
.action-highlight { animation: action-flash 1.8s ease; }
```

### 4. Verify-runtime extensions

Add two new test blocks after existing assertions:
- **Hash navigation test:** `page.evaluate(() => location.hash = "#S14")` → reload → `page.waitForSelector('.sidebar-item.active[data-sid="S14"]')`.
- **Search filter test:** type `"S14"` into `#sidebar-search-input` → assert visible `.sidebar-item` count < total count; clear → assert count restored.

## Validation
1. Open wireframe with `#S14` appended → S14 loads as active surface.
2. Open with `#A-S14-009` → navigates to S14, action button flashes.
3. Type `"task"` in search box → only surfaces with "task" in id/name visible.
4. Type exact action id `A-S14-003` → navigates to S14 + highlights action.
5. `node tools/wireframe/verify-runtime.mjs` → green including new assertions.

## Risks & rollback
- **Risk:** `edgeById` may not index by action id if called before `initFlowBar()` warms the index — ensure `filterSidebar` guard-checks `edgeById` presence.
- **Risk:** `CSS.escape` not available in older Playwright browser — use attribute selector with quotes: `[data-id="${actionId.replace(/"/g, '\\"')}"]`.
- **Risk:** `history.replaceState` throws in file:// protocol on some browsers — wrap in try/catch.
- **Rollback:** changes are additive; removing search input and hash calls restores prior behavior exactly.
