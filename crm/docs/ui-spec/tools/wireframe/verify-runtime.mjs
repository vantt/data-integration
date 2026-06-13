// wireframe/verify-runtime.mjs
// NODE: Runtime smoke-test for wireframe-v2.html using jsdom.
// Drives every surface + flow via real DOM events — catches handler crashes that
// static analysis cannot. Exit 0 = clean, Exit 1 = errors found.
// Usage: node wireframe/verify-runtime.mjs  |  npm run verify:wf

import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { JSDOM, VirtualConsole } from "jsdom";

const __dir = dirname(fileURLToPath(import.meta.url));
// __dir = .agents/skills/ui-spec/tools/wireframe → 5 levels up to git root
const HTML_PATH = resolve(__dir, "../../../../../frontend/docs/ui-spec/generated/wireframe-v2.html");

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
  dom = new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, virtualConsole: vc });
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
//   (a) Real browser / canvas available  → Cytoscape mounts, #view-graph contains <canvas>
//   (b) jsdom / no canvas               → graceful fallback <p>, no crash = PASS
// We do NOT assert svg/canvas presence — we only assert: no thrown errors + tab switch works.
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
    console.log("  Graph: Cytoscape canvas unavailable (jsdom/no-canvas) — graceful fallback rendered, OK");
  } else {
    fail("ASSERT: #view-graph empty after Graph tab switch — expected canvas or fallback <p>");
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
  console.log("\nRESULT: PASS — all assertions clean, zero runtime errors");
}
console.log("========================================");
process.exit(errors.length ? 1 : 0);
