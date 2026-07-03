// wireframe/verify-runtime.mjs
// NODE: Runtime smoke-test for wireframe-v2.html using jsdom.
// Drives every surface + flow via real DOM events — catches handler crashes that
// static analysis cannot. Exit 0 = clean, Exit 1 = errors found.
// Usage: node wireframe/verify-runtime.mjs  |  npm run verify:wf

import { readFileSync } from "node:fs";
import { resolve, join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";

const __dir = dirname(fileURLToPath(import.meta.url));

// Support --root <spec-root> so the tool can locate wireframe-v2.html for any spec.
// Without --root, falls back to the legacy hardcoded path for backward compat.
function parseRootArg() {
  const idx = process.argv.indexOf("--root");
  if (idx !== -1 && process.argv[idx + 1]) return resolve(process.argv[idx + 1]);
  return null;
}
const rootArg = parseRootArg();
// __dir = .skills/ui-spec/tools/wireframe → 4 levels up to git root (legacy fallback)
const HTML_PATH = rootArg
  ? join(rootArg, "generated", "wireframe-v2.html")
  : resolve(__dir, "../../../../frontend/docs/ui-spec/generated/wireframe-v2.html");

const errors = [];
function fail(msg) { errors.push(msg); }

// Helpers — all use `dom` which is assigned before any helper is called
function click(el) {
  if (!el) return false;
  el.dispatchEvent(new dom.window.MouseEvent("click", { bubbles: true, cancelable: true }));
  return true;
}
function selectValue(sel, val) {
  if (!sel) return;
  sel.value = val;
  sel.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
}
function fireChange(el) {
  if (!el) return;
  el.dispatchEvent(new dom.window.Event("change", { bubbles: true }));
}
function wait(ms) { return new Promise(r => setTimeout(r, ms)); }

// Load HTML into jsdom
console.log("Loading wireframe-v2.html …");
const html = readFileSync(HTML_PATH, "utf8");
const vc = new VirtualConsole();
const loadErrs = [];
vc.on("jsdomError", e => loadErrs.push("jsdomError: " + e.message));
vc.on("error",      e => loadErrs.push("console.error: " + e));
vc.on("warn",       () => {}); // style warnings expected in headless

let dom;
try {
  // url: "http://localhost/" is required by jsdom to enable history.replaceState and
  // location.hash assignment; without it the document URL is about:blank and both APIs
  // fail silently (same-origin check fails).
  dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc,
                           url: "http://localhost/" });
} catch (e) {
  fail("JSDOM load threw: " + e.message);
  console.error("FATAL:", e.message);
  process.exit(1);
}
const { window } = dom;
window.addEventListener("error", e => fail("window.error: " + (e.message || e)));
window.addEventListener("unhandledrejection", e =>
  fail("unhandledRejection: " + (e.reason?.message || e.reason)));
for (const e of loadErrs) fail(e);
const doc = window.document;

// Post-load assertions
console.log("Checking post-load DOM …");
const viewLayout = doc.getElementById("view-layout");
if (!viewLayout)                       fail("ASSERT: #view-layout missing after load");
else if (!viewLayout.innerHTML.trim()) fail("ASSERT: #view-layout empty after init");
const sidebarContent = doc.getElementById("sidebar-content");
if (!sidebarContent || !sidebarContent.innerHTML.trim()) fail("ASSERT: #sidebar-content empty after init");

// Section A: tab switching
console.log("Section A: tab switching …");
const tabs = [...doc.querySelectorAll(".tab:not([disabled])")];
if (tabs.length === 0) fail("ASSERT: no .tab buttons found");
for (const tab of tabs) {
  const before = errors.length;
  click(tab);
  if (errors.length > before) fail(`Tab '${tab.dataset.view}' click introduced errors`);
  if (!doc.getElementById("view-" + tab.dataset.view))
    fail(`ASSERT: #view-${tab.dataset.view} missing after tab switch`);
}
for (const st of [...doc.querySelectorAll(".subtab")]) {  // surface sub-tabs (Interactions|Blueprint)
  const before = errors.length;
  click(st);
  if (errors.length > before) fail(`Subtab '${st.dataset.view}' click introduced errors`);
  if (!doc.getElementById("view-" + st.dataset.view))
    fail(`ASSERT: #view-${st.dataset.view} missing after subtab switch`);
}
const layoutTab = tabs.find(t => t.dataset.view === "layout");
if (layoutTab) click(layoutTab);

// Section B: every sidebar item
console.log("Section B: sidebar items …");
const sidebarItems = [...doc.querySelectorAll(".sidebar-item")];
console.log(`  Found ${sidebarItems.length} sidebar items`);
if (sidebarItems.length === 0) fail("ASSERT: no .sidebar-item elements found");
let surfacesExercised = 0;
for (const item of sidebarItems) {
  const sid = item.dataset.sid;
  const before = errors.length;
  click(item);
  if (errors.length > before)              fail(`Sidebar click on '${sid}' introduced errors`);
  const lv = doc.getElementById("view-layout");
  if (lv && !lv.innerHTML.trim())         fail(`ASSERT: #view-layout empty after navigating to '${sid}'`);
  surfacesExercised++;
}

// Section C: storyboard + flow play per flow
console.log("Section C: storyboard + flow play …");
const flowSelect = doc.getElementById("flow-select");
const flowOptions = flowSelect ? [...flowSelect.querySelectorAll("option")].filter(o => o.value) : [];
console.log(`  Found ${flowOptions.length} flow options`);
let flowsExercised = 0;
for (const opt of flowOptions) {
  const flowId = opt.value;
  selectValue(flowSelect, flowId);
  const sbTab = tabs.find(t => t.dataset.view === "storyboard");
  if (sbTab) click(sbTab);
  const sbContainer = doc.getElementById("view-storyboard");
  if (!sbContainer || !sbContainer.innerHTML.trim())
    fail(`ASSERT: #view-storyboard empty after selecting flow '${flowId}'`);
  if (!sbContainer?.querySelectorAll(".sb-card").length)
    console.log(`  Note: flow '${flowId}' has no storyboard cards`);

  const before = errors.length;
  click(doc.getElementById("btn-flow-play"));
  await wait(1700); // wait one FLOW_STEP_MS=1500ms tick
  if (errors.length > before) fail(`Flow play '${flowId}' introduced errors`);

  const banner = doc.getElementById("narration-banner");
  if (banner && !banner.classList.contains("hidden")) {
    const nbText = banner.querySelector(".nb-text");
    if (!nbText?.textContent.trim()) fail(`ASSERT: narration .nb-text empty during '${flowId}'`);
  }
  if (!doc.querySelector(".active-region, .active-el"))
    console.log(`  Note: no .active-region/.active-el after tick for '${flowId}'`);

  click(doc.getElementById("btn-flow-stop"));
  if (layoutTab) click(layoutTab);
  flowsExercised++;
}

// Section D: graph view
// NOTE: Cytoscape renders to <canvas>, not <svg>. Under jsdom there is no
// HTMLCanvasElement implementation, so Cytoscape throws at init and falls back
// to a graceful error <p>. We accept either outcome here:
//   (a) Real browser / canvas available  -> Cytoscape mounts, #view-graph contains <canvas>
//   (b) jsdom / no canvas               -> graceful fallback <p>, no crash = PASS
// We do NOT assert svg/canvas presence -- we only assert: no thrown errors + tab switch works.
console.log("Section D: graph view …");
const graphTab = tabs.find(t => t.dataset.view === "graph");
if (graphTab) {
  const before = errors.length;
  click(graphTab);
  if (errors.length > before) fail("Graph tab click introduced errors");

  const gc = doc.getElementById("view-graph");
  const hasCanvas  = !!gc?.querySelector("canvas");
  const hasFallback = !!gc?.querySelector("p");
  if (hasCanvas) {
    console.log("  Graph: Cytoscape canvas mounted successfully");
  } else if (hasFallback) {
    console.log("  Graph: Cytoscape canvas unavailable (jsdom/no-canvas) -- graceful fallback rendered, OK");
  } else {
    fail("ASSERT: #view-graph empty after Graph tab switch -- expected canvas or fallback <p>");
  }

  // Toolbar controls must not throw regardless of canvas availability
  const toggle = doc.getElementById("graph-reaction-toggle");
  if (toggle) {
    toggle.checked = true;
    const bt = errors.length;
    fireChange(toggle);
    if (errors.length > bt) fail("Reaction toggle re-render introduced errors");
  }
  const gfs = doc.getElementById("graph-flow-select");
  const gfOpts = gfs ? [...gfs.querySelectorAll("option")].filter(o => o.value) : [];
  if (gfOpts.length > 0) {
    const bef = errors.length;
    selectValue(gfs, gfOpts[0].value);
    if (errors.length > bef) fail("Flow-highlight select change introduced errors");
    else console.log(`  Graph flow-highlight select: ok (${gfOpts.length} flows available)`);
  }
  console.log("  Graph toolbar: reaction-toggle + flow-select exercised without errors");
}

// Section E: hash routing
// Note: function declarations in non-module <script> blocks become window globals in jsdom
// (runScripts:"dangerously"). const/let/var variables declared with const/let do NOT.
// We therefore read surface IDs from the sidebar DOM, not from window.surfaceById.
console.log("Section E: hash routing …");
if (typeof window.navigateTo !== "function") {
  fail("ASSERT E: navigateTo not found as window global (expected function declaration)");
} else if (typeof window.resolveInitialHash !== "function") {
  fail("ASSERT E: resolveInitialHash not found as window global (expected function declaration)");
} else {
  // Collect surface IDs from sidebar DOM (data-sid attributes set by buildSidebar).
  const sidebarSids = [...doc.querySelectorAll(".sidebar-item[data-sid]")]
    .map(el => el.dataset.sid).filter(Boolean);

  if (sidebarSids.length === 0) {
    fail("ASSERT E: no sidebar items with data-sid -- cannot run hash-routing tests");
  } else {
    // E1: navigateTo(sid) writes location.hash and marks the correct sidebar item active.
    const hashSid1 = sidebarSids[sidebarSids.length - 1]; // last surface (likely differs from current)
    const beforeE1 = errors.length;
    window.navigateTo(hashSid1);
    if (errors.length > beforeE1) fail(`E1 navigateTo('${hashSid1}') introduced errors`);
    if (window.location.hash !== "#" + hashSid1)
      fail(`ASSERT E1: location.hash should be '#${hashSid1}' after navigateTo, got '${window.location.hash}'`);
    const activeE1 = doc.querySelector(`.sidebar-item.active[data-sid="${hashSid1}"]`);
    if (!activeE1) fail(`ASSERT E1: .sidebar-item.active missing for '${hashSid1}' after navigateTo`);
    else console.log(`  E1 navigateTo('${hashSid1}') sets hash + sidebar active: OK`);

    // E2: resolveInitialHash reads location.hash and navigates to the referenced surface.
    const hashSid2 = sidebarSids[0]; // first surface -- different from hashSid1
    try { window.location.hash = "#" + hashSid2; } catch (e) { /* jsdom may restrict assignment */ }
    const beforeE2 = errors.length;
    window.resolveInitialHash();
    if (errors.length > beforeE2) fail(`E2 resolveInitialHash('#${hashSid2}') introduced errors`);
    const activeE2 = doc.querySelector(`.sidebar-item.active[data-sid="${hashSid2}"]`);
    if (!activeE2) fail(`ASSERT E2: .sidebar-item.active missing for '${hashSid2}' after resolveInitialHash`);
    else console.log(`  E2 resolveInitialHash('#${hashSid2}'): sidebar active OK`);

    // E3: action-id hash -> navigate to owning surface + highlight action button.
    // Find ANY surface with [data-id] action buttons by iterating sidebar items (stops on first hit).
    let testActionId = null, testActionExpectedSid = null;
    for (const sid of sidebarSids) {
      window.navigateTo(sid);
      if (layoutTab) click(layoutTab);
      const btn = doc.querySelector("#view-layout .action-btn[data-id]");
      if (btn && btn.dataset.id) { testActionId = btn.dataset.id; testActionExpectedSid = sid; break; }
    }
    if (testActionId) {
      // Derive owning surface from action-id format (e.g. "A-S14-009" -> "S14")
      const actionSidMatch = testActionId.match(/^[A-Za-z]+-([A-Z]{1,2}\d+)/);
      const expectedSid = (actionSidMatch && actionSidMatch[1]) ? actionSidMatch[1] : testActionExpectedSid;
      try { window.location.hash = "#" + testActionId; } catch (e) { /* ignore */ }
      const beforeE3 = errors.length;
      window.resolveInitialHash();
      await wait(120); // allow setTimeout(50ms) in highlightAction to fire
      if (errors.length > beforeE3) fail(`E3 action hash '#${testActionId}' introduced errors`);
      const activeE3 = doc.querySelector(`.sidebar-item.active[data-sid="${expectedSid}"]`);
      if (!activeE3) fail(`ASSERT E3: .sidebar-item.active missing for '${expectedSid}' after action hash '${testActionId}'`);
      else console.log(`  E3 action hash '#${testActionId}' -> surface '${expectedSid}' active: OK`);
    } else {
      console.log("  E3: no [data-id] action buttons found in any surface -- skipping action-id hash test");
    }
  }
}

// Section F: search filter
console.log("Section F: search filter …");
const searchInput = doc.getElementById("sidebar-search-input");
if (!searchInput) {
  fail("ASSERT F: #sidebar-search-input not found");
} else {
  const allSidItems = [...doc.querySelectorAll(".sidebar-item[data-sid]")]
    .map(el => el.dataset.sid).filter(Boolean);
  const totalItems = doc.querySelectorAll(".sidebar-item").length;
  if (totalItems === 0) {
    fail("ASSERT F: no .sidebar-item elements for search test");
  } else {
    // Filter by the first surface ID -- a precise term that matches 1 or a few, never all.
    const filterTerm = allSidItems[0] || "S01";
    searchInput.value = filterTerm;
    searchInput.dispatchEvent(new window.Event("input", { bubbles: true }));
    const afterSearch = [...doc.querySelectorAll(".sidebar-item")]
      .filter(el => el.style.display !== "none").length;
    if (afterSearch >= totalItems)
      fail(`ASSERT F1: search '${filterTerm}' did not filter sidebar (${afterSearch} visible of ${totalItems})`);
    else
      console.log(`  F1 search '${filterTerm}': ${afterSearch}/${totalItems} items visible -- OK`);

    // Clear search -- all items must be restored.
    searchInput.value = "";
    searchInput.dispatchEvent(new window.Event("input", { bubbles: true }));
    const afterClear = [...doc.querySelectorAll(".sidebar-item")]
      .filter(el => el.style.display !== "none").length;
    if (afterClear !== totalItems)
      fail(`ASSERT F2: clearing search restored ${afterClear}/${totalItems} items (expected ${totalItems})`);
    else
      console.log(`  F2 clear search: ${afterClear}/${totalItems} items restored -- OK`);
  }
}

// Section G: Blueprint ↔ region-box 2-way linking
// G1: A surface with regions + ASCII gets .bp-region-span elements in blueprint-pre.
// G2: Clicking a .bp-region-span switches view to Interactions (layout) without crash.
// G3: Clicking a .region-label[data-region] in Interactions switches to Blueprint without crash.
console.log("Section G: Blueprint ↔ region-box linking …");
// Reset to layout tab first so renderMain is in a clean state.
if (layoutTab) click(layoutTab);
// Navigate through surfaces to find one with both regions and ASCII layout text.
let bpTestSurface = null;
for (const sid of [...doc.querySelectorAll(".sidebar-item[data-sid]")].map(el => el.dataset.sid)) {
  window.navigateTo(sid);
  if (layoutTab) click(layoutTab);
  const bpPre = doc.getElementById("blueprint-pre");
  const hasSpan = bpPre && bpPre.querySelector(".bp-region-span");
  if (hasSpan) { bpTestSurface = sid; break; }
}
if (!bpTestSurface) {
  console.log("  G: no surface with bp-region-span found — surfaces may lack ASCII region names (OK, skip)");
} else {
  // G1: spans were injected
  const bpPre = doc.getElementById("blueprint-pre");
  const spans = bpPre ? [...bpPre.querySelectorAll(".bp-region-span")] : [];
  if (spans.length === 0) {
    fail("ASSERT G1: .bp-region-span not found in blueprint-pre for surface '" + bpTestSurface + "'");
  } else {
    console.log("  G1 surface '" + bpTestSurface + "': " + spans.length + " bp-region-span(s) injected -- OK");

    // G2: click a span → switches to layout (Interactions) without crash.
    // First switch to Blueprint so the span is in the active view.
    const bpSubtab = doc.querySelector(".subtab[data-view='blueprint']");
    if (bpSubtab) click(bpSubtab);
    const beforeG2 = errors.length;
    click(spans[0]);
    if (errors.length > beforeG2) {
      fail("G2 bp-region-span click on '" + (spans[0].dataset.region || "?") + "' introduced errors");
    } else {
      const layoutVisible = doc.getElementById("view-layout")?.style.display !== "none";
      if (!layoutVisible) fail("ASSERT G2: #view-layout not visible after bp-region-span click");
      else console.log("  G2 bp-region-span click switches to Interactions -- OK");
    }
  }

  // G3: click a region-label in Interactions → switches to Blueprint without crash.
  if (layoutTab) click(layoutTab); // ensure Interactions is active
  const regionLabel = doc.querySelector("#view-layout .region-label-link[data-region]");
  if (!regionLabel) {
    console.log("  G3: no .region-label-link[data-region] in Interactions (may have no regions) -- skip");
  } else {
    const beforeG3 = errors.length;
    click(regionLabel);
    if (errors.length > beforeG3) {
      fail("G3 region-label click on '" + (regionLabel.dataset.region || "?") + "' introduced errors");
    } else {
      const bpVisible = doc.getElementById("view-blueprint")?.style.display !== "none";
      if (!bpVisible) fail("ASSERT G3: #view-blueprint not visible after region-label click");
      else console.log("  G3 region-label click switches to Blueprint -- OK");
    }
  }
}
// Restore layout tab for any subsequent assertions.
if (layoutTab) click(layoutTab);

// Section H: States subtab
// H1: a surface known to have States (S14) shows >0 state cards when subtab clicked.
// H2: ERR badge exists in at least one surface's States view.
// H3: clicking States subtab on every surface causes no crash.
console.log("Section H: States subtab …");
const statesSubtab = doc.querySelector(".subtab[data-view='states']");
if (!statesSubtab) {
  fail("ASSERT H: .subtab[data-view='states'] button not found in DOM");
} else {
  // H1: Navigate to S14 and verify state cards appear
  const s14Item = doc.querySelector(".sidebar-item[data-sid='S14']");
  if (!s14Item) {
    console.log("  H1: S14 not found in sidebar — skipping H1 (spec root may differ)");
  } else {
    window.navigateTo("S14");
    if (layoutTab) click(layoutTab); // reset to clean state
    const beforeH1 = errors.length;
    click(statesSubtab);
    if (errors.length > beforeH1) {
      fail("H1 States subtab click on S14 introduced errors");
    } else {
      const viewStates = doc.getElementById("view-states");
      const cards = viewStates ? [...viewStates.querySelectorAll(".state-card")] : [];
      if (cards.length === 0) {
        fail("ASSERT H1: #view-states has no .state-card after clicking States on S14");
      } else {
        console.log(`  H1 S14 States subtab: ${cards.length} state card(s) -- OK`);
      }
    }
    if (layoutTab) click(layoutTab);
  }

  // H2: ERR badge exists anywhere across all surfaces
  let errBadgeFound = false;
  const allSidsH2 = [...doc.querySelectorAll(".sidebar-item[data-sid]")].map(el => el.dataset.sid);
  for (const sid of allSidsH2) {
    window.navigateTo(sid);
    if (layoutTab) click(layoutTab);
    click(statesSubtab);
    const vs = doc.getElementById("view-states");
    if (vs && vs.querySelector(".err-chip")) { errBadgeFound = true; break; }
    if (layoutTab) click(layoutTab);
  }
  if (errBadgeFound) {
    console.log("  H2 ERR chip badge found in at least one surface's States view -- OK");
  } else {
    // Not a hard failure — surfaces may genuinely have no ERR refs in States bullets
    console.log("  H2 note: no .err-chip found across surfaces (States may not reference ERR-* codes)");
  }
  if (layoutTab) click(layoutTab);

  // H3: no crash across all surfaces when clicking States subtab
  const allSidsH3 = [...doc.querySelectorAll(".sidebar-item[data-sid]")].map(el => el.dataset.sid);
  let statesCrashes = 0;
  for (const sid of allSidsH3) {
    window.navigateTo(sid);
    if (layoutTab) click(layoutTab);
    const beforeH3 = errors.length;
    click(statesSubtab);
    if (errors.length > beforeH3) {
      statesCrashes++;
      fail(`H3 States subtab on '${sid}' introduced errors`);
    }
    if (layoutTab) click(layoutTab);
  }
  if (statesCrashes === 0) {
    console.log(`  H3 States subtab: no crash across ${allSidsH3.length} surfaces -- OK`);
  }
}
// Restore layout tab after Section H
if (layoutTab) click(layoutTab);

// Section I: Grid renderer (Phase 6)
// (a) S14 default view is Layout (grid subtab active); grid contains "reason_to_call" in grid-template-areas.
// (b) Floating toggle click shows stop_banner + hides at least one replaced cell.
// (c) Variant switch adds topbar cell to grid.
// (d) Spot-check: S01 (no layout) defaults to Interactions, Layout subtab hidden.
// (e) No crash across all surfaces navigating with new renderMain logic.
console.log("Section I: Grid renderer (Phase 6) …");
const s14ItemI = doc.querySelector(".sidebar-item[data-sid='S14']");
if (!s14ItemI) {
  console.log("  I: S14 not found in sidebar — skipping Section I (spec root may differ)");
} else {
  if (layoutTab) click(layoutTab); // reset to clean state

  // (a) Navigate to S14 — expect Layout subtab visible and grid has reason_to_call
  window.navigateTo("S14");
  const viewGridI   = doc.getElementById("view-grid");
  const subtabGridI = doc.getElementById("subtab-grid");

  if (!viewGridI) {
    fail("ASSERT I(a): #view-grid element not found in DOM after S14 navigation");
  } else if (subtabGridI && subtabGridI.style.display === "none") {
    fail("ASSERT I(a): #subtab-grid is hidden after navigating to S14 (expected visible — S14 has layout)");
  } else {
    const viewGridVisible = viewGridI.style.display !== "none";
    if (!viewGridVisible) {
      fail("ASSERT I(a): #view-grid not visible after navigating to S14 (expected Layout as default)");
    } else {
      // Assert on PARSED CSSOM, not the raw HTML string: a quoting bug inside the
      // style attribute leaves grid-template-areas empty after parsing while the
      // raw string still "contains" the property name (cells then auto-stack).
      const containerI = viewGridI.querySelector(".grid-container");
      const parsedAreas = containerI ? containerI.style.gridTemplateAreas || "" : "";
      if (!containerI) {
        fail("ASSERT I(a): .grid-container not found in #view-grid after S14 navigation");
      } else if (!parsedAreas.includes("reason_to_call")) {
        fail("ASSERT I(a): parsed style.gridTemplateAreas does not contain 'reason_to_call' (got: '" + parsedAreas.slice(0, 80) + "')");
      } else if (!(containerI.style.gridTemplateColumns || "").includes("fr")) {
        fail("ASSERT I(a): parsed style.gridTemplateColumns missing fr values");
      } else {
        console.log("  I(a) S14: Layout tab visible, parsed grid-template-areas contains reason_to_call — OK");
      }
    }
  }

  // (g) Inspector panel exists in Layout view after S14 navigation
  {
    // viewGridI was obtained above; S14 should still be current
    const inspectorPanelG = viewGridI ? viewGridI.querySelector("#grid-inspector") : null;
    if (!inspectorPanelG) {
      fail("ASSERT I(g): #grid-inspector not found inside #view-grid after S14 navigation");
    } else {
      console.log("  I(g) inspector panel exists in Layout view: OK");
    }
  }

  // (h) Hovering a mapped chip on S14 populates inspector with the action id
  if (viewGridI) {
    window.navigateTo("S14"); // fresh render to reset pin state
    const mappedChip = viewGridI.querySelector(".gc-inline-chip[data-action-id]");
    if (!mappedChip) {
      console.log("  I(h): no mapped .gc-inline-chip found on S14 — skipping (pilot elements not present)");
    } else {
      const chipText       = mappedChip.dataset.chipText || "";
      const expectedAction = mappedChip.dataset.actionId || "";
      mappedChip.dispatchEvent(new dom.window.MouseEvent("mouseover", { bubbles: true }));
      await wait(50);
      const inspector = doc.getElementById("grid-inspector");
      const inspHtml  = inspector ? inspector.innerHTML : "";
      if (!expectedAction || !inspHtml.includes(expectedAction)) {
        fail(`ASSERT I(h): inspector does not contain action id '${expectedAction}' after hovering mapped chip '${chipText}'`);
      } else {
        console.log(`  I(h) hover mapped chip '${chipText}' → inspector shows '${expectedAction}': OK`);
      }
    }
    // Navigate back to S14 default for subsequent sub-tests
    window.navigateTo("S14");
  }

  // (b) Floating toggle shows stop_banner and hides a replaced cell
  if (viewGridI) {
    const floatingBtn = viewGridI.querySelector(".floating-toggle");
    if (!floatingBtn) {
      console.log("  I(b): no .floating-toggle found in #view-grid — skipping floating test");
    } else {
      const beforeIb = errors.length;
      click(floatingBtn);
      if (errors.length > beforeIb) {
        fail("I(b) .floating-toggle click introduced errors");
      } else {
        const bannerIdent = floatingBtn.dataset.floating;
        const banner      = bannerIdent ? doc.getElementById("floating-" + bannerIdent) : null;
        if (!banner || banner.style.display === "none") {
          fail("ASSERT I(b): floating banner not visible after toggle click (banner id: floating-" + (bannerIdent || "?") + ")");
        } else {
          console.log("  I(b) floating toggle shows banner: OK");
        }
        // Check that at least one replaced cell is hidden
        const replaces = (floatingBtn.dataset.replaces || "").split(",").filter(Boolean);
        if (replaces.length > 0) {
          const anyHidden = replaces.some(r => {
            const cell = viewGridI.querySelector(`.grid-cell[data-region-ident="${r}"]`);
            return cell && cell.style.display === "none";
          });
          if (anyHidden) {
            console.log("  I(b) replaced cell hidden after toggle: OK");
          } else {
            console.log("  I(b) note: no replaced cell detected as hidden (replaces: " + replaces.join(",") + ")");
          }
        }
        // Restore toggle state
        click(floatingBtn);
      }
    }
  }

  // (c) Variant switch adds topbar cell (full_screen variant prepends topbar row)
  if (viewGridI) {
    // Navigate back to S14 in default state before testing variants
    window.navigateTo("S14");
    const inactiveVariantBtn = doc.querySelector("#view-grid .variant-btn:not(.active)");
    if (!inactiveVariantBtn) {
      console.log("  I(c): no inactive .variant-btn found — skipping variant switch test");
    } else {
      const beforeIc = errors.length;
      click(inactiveVariantBtn);
      if (errors.length > beforeIc) {
        fail("I(c) variant-btn click introduced errors");
      } else {
        const topbarCell = viewGridI.querySelector(".grid-cell[data-region-ident='topbar']");
        if (!topbarCell) {
          fail("ASSERT I(c): no .grid-cell[data-region-ident='topbar'] in #view-grid after variant switch");
        } else {
          console.log("  I(c) variant switch adds topbar cell: OK");
        }
      }
    }
  }

  // (d) F01 spot-check: flow surfaces have no layout → Interactions default, Layout subtab hidden.
  // Note: S01 now has a layout (Phase 8 injected markers into all 40 screen/panel/modal/overlay
  // surfaces), so we use F01 (a flow surface) as the no-layout spot-check target.
  const f01ItemI = doc.querySelector(".sidebar-item[data-sid='F01']");
  if (!f01ItemI) {
    console.log("  I(d): F01 not found — skipping spot-check");
  } else {
    window.navigateTo("F01");
    const subtabGridAfterF01 = doc.getElementById("subtab-grid");
    if (subtabGridAfterF01 && subtabGridAfterF01.style.display !== "none") {
      fail("ASSERT I(d): #subtab-grid visible after navigating to F01 (F01 has no layout — should be hidden)");
    } else {
      const viewLayoutAfterF01 = doc.getElementById("view-layout");
      const layoutVisible      = viewLayoutAfterF01 && viewLayoutAfterF01.style.display !== "none";
      if (!layoutVisible) {
        fail("ASSERT I(d): #view-layout not visible after F01 navigation (expected Interactions as default)");
      } else {
        console.log("  I(d) F01 defaults to Interactions, Layout tab hidden: OK");
      }
    }
  }

  // (e) No crash across all surfaces
  const allSidsI = [...doc.querySelectorAll(".sidebar-item[data-sid]")].map(el => el.dataset.sid);
  let iCrashes = 0;
  for (const sid of allSidsI) {
    const beforeIe = errors.length;
    window.navigateTo(sid);
    if (errors.length > beforeIe) {
      iCrashes++;
      fail(`I(e) navigateTo('${sid}') introduced errors`);
    }
  }
  if (iCrashes === 0) {
    console.log(`  I(e) no crash across ${allSidsI.length} surfaces: OK`);
  }

  // (f) S03 sidebar cell renders child sub-layout mini-sections (layout.children).
  // sidebar.warning is floating → skipped in children render; expect the other 5 blocks.
  const s03ItemI = doc.querySelector(".sidebar-item[data-sid='S03']");
  if (!s03ItemI) {
    console.log("  I(f): S03 not found — skipping children render check");
  } else {
    window.navigateTo("S03");
    const sidebarCell = doc.querySelector("#view-grid .grid-cell[data-region-ident='sidebar']");
    const childCount  = sidebarCell ? sidebarCell.querySelectorAll(".gc-child").length : 0;
    if (!sidebarCell) {
      fail("ASSERT I(f): S03 grid cell for 'sidebar' not found");
    } else if (childCount === 0) {
      fail("ASSERT I(f): S03 sidebar cell has 0 .gc-child mini-sections (children sub-layout not rendered)");
    } else {
      console.log(`  I(f) S03 sidebar renders ${childCount} child mini-section(s): OK`);
    }
  }
}
// Restore layout tab after Section I
if (layoutTab) click(layoutTab);

// Section J: Grid render smoke at scale (Phase 8)
// For every surface with a .layout property: assert grid view renders without crash
// and grid-template-areas is non-empty.
// S03 guard: sidebar.warning appears in both children.sidebar.areas and floating —
// render-grid.js skips floating regions in child mini-sections so no double-render;
// floating renders as a toggle banner only. Assertion is: no crash + areas non-empty.
console.log("Section J: Grid render smoke (all surfaces with layout) …");
{
  const allSidsJ = [...doc.querySelectorAll(".sidebar-item[data-sid]")].map(el => el.dataset.sid);
  let jCrashes = 0, jRendered = 0, jNoLayout = 0;
  for (const sid of allSidsJ) {
    window.navigateTo(sid);
    const subtabGrid = doc.getElementById("subtab-grid");
    const hasLayout  = subtabGrid && subtabGrid.style.display !== "none";
    if (!hasLayout) { jNoLayout++; continue; }
    // Click Layout (grid) subtab to force render
    if (subtabGrid) {
      const beforeJ = errors.length;
      click(subtabGrid);
      if (errors.length > beforeJ) {
        jCrashes++;
        fail(`J grid render crash on '${sid}'`);
        continue;
      }
    }
    const vg = doc.getElementById("view-grid");
    const gridHtml = vg ? vg.innerHTML : "";
    if (!gridHtml.includes("grid-template-areas")) {
      fail(`J ASSERT: '${sid}' Layout tab visible but grid-template-areas absent`);
      jCrashes++;
    } else {
      jRendered++;
    }
    // Restore layout tab
    if (layoutTab) click(layoutTab);
  }
  if (jCrashes === 0) {
    console.log(`  J grid smoke: ${jRendered} surfaces rendered without crash, ${jNoLayout} skipped (no layout) — OK`);
  } else {
    console.log(`  J grid smoke: ${jCrashes} crash(es), ${jRendered} OK, ${jNoLayout} no-layout`);
  }
}

// Summary
console.log("\n========================================");
console.log("verify-runtime summary");
console.log("========================================");
console.log(`Surfaces exercised : ${surfacesExercised}`);
console.log(`Flows exercised    : ${flowsExercised}`);
console.log(`Errors             : ${errors.length}`);
if (errors.length > 0) {
  console.log("\nERROR LIST:");
  for (const e of errors) console.log("  [ERR]", e);
  console.log("\nRESULT: FAIL");
} else {
  console.log("\nRESULT: PASS -- all assertions clean, zero runtime errors");
}
console.log("========================================");
process.exit(errors.length ? 1 : 0);
