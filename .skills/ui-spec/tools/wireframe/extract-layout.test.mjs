// extract-layout.test.mjs — self-contained node test for extract-layout.mjs.
// No test framework. Uses assert + process.exit(1) on first failure.
// Run: node .skills/ui-spec/tools/wireframe/extract-layout.test.mjs

import assert from "node:assert/strict";
import { extractLayout, layoutAreaNames, nonRectRegions } from "./extract-layout.mjs";

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ✗ ${name}`);
    console.error(`    ${e.message}`);
    failed++;
  }
}

// ─── Test 1: valid 2-column grid model parses correctly ──────────────────────
test("valid 2-column grid — extractLayout returns model", () => {
  const md = `
## Layout

\`\`\`yaml ui-layout
columns: [3fr, 2fr]
areas:
  - [header, header]
  - [sidebar, main]
  - [footer, footer]
floating:
  - region: overlay
    when: "show_overlay == true"
variants:
  full_screen:
    prepend_rows:
      - [topbar, topbar]
samples:
  header: "Page Title"
  sidebar: "Nav"
  main: "Content"
  footer: "Footer"
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null, "model should not be null");
  assert.deepEqual(model.columns, ["3fr", "2fr"]);
  assert.equal(model.areas.length, 3);
  assert.deepEqual(model.areas[0], ["header", "header"]);
  assert.deepEqual(model.areas[1], ["sidebar", "main"]);
  assert.deepEqual(model.areas[2], ["footer", "footer"]);
});

// ─── Test 2: layoutAreaNames returns the correct complete set ─────────────────
test("layoutAreaNames — includes areas + variant rows + floating + children", () => {
  const md = `
\`\`\`yaml ui-layout
areas:
  - [header, header]
  - [sidebar, main]
  - [footer, footer]
floating:
  - region: overlay
variants:
  full_screen:
    prepend_rows:
      - [topbar, topbar]
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null);
  const names = layoutAreaNames(model);
  assert.ok(names instanceof Set, "should return a Set");
  // From areas
  assert.ok(names.has("header"), "header from areas");
  assert.ok(names.has("sidebar"), "sidebar from areas");
  assert.ok(names.has("main"), "main from areas");
  assert.ok(names.has("footer"), "footer from areas");
  // From floating
  assert.ok(names.has("overlay"), "overlay from floating");
  // From variant prepend_rows
  assert.ok(names.has("topbar"), "topbar from variant prepend_rows");
  assert.equal(names.size, 6, "exactly 6 unique names");
});

// ─── Test 3: non-rectangular region detected ─────────────────────────────────
test("nonRectRegions — detects L-shaped region", () => {
  // 'bad' appears at (0,0), (1,0), (1,1) → L-shape, not a rectangle
  const md = `
\`\`\`yaml ui-layout
areas:
  - [bad, ok]
  - [bad, bad]
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null);
  const bad = nonRectRegions(model);
  assert.ok(Array.isArray(bad), "should return an array");
  assert.ok(bad.includes("bad"), "L-shaped 'bad' region should be flagged");
  assert.ok(!bad.includes("ok"), "'ok' spans 1 cell — valid rectangle, not flagged");
});

// ─── Test 4: header spanning 2 columns is a valid rectangle ──────────────────
test("nonRectRegions — header spanning full row is a valid rectangle", () => {
  const md = `
\`\`\`yaml ui-layout
areas:
  - [header, header]
  - [sidebar, main]
  - [footer, footer]
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null);
  const bad = nonRectRegions(model);
  assert.deepEqual(bad, [], "no non-rectangular regions in a clean 2-col grid");
});

// ─── Test 5: missing areas key → returns null ────────────────────────────────
test("extractLayout — missing areas key → null", () => {
  const md = `
\`\`\`yaml ui-layout
columns: [1fr, 2fr]
samples:
  header: "Hi"
\`\`\`
`;
  const model = extractLayout(md);
  assert.equal(model, null, "model without areas[] must return null");
});

// ─── Test 6: YAML parse error → returns null ────────────────────────────────
test("extractLayout — YAML parse error → null", () => {
  const md = `
\`\`\`yaml ui-layout
areas: [unclosed bracket
  - oops
\`\`\`
`;
  const model = extractLayout(md);
  assert.equal(model, null, "malformed YAML must return null");
});

// ─── Test 7: no fence → returns null ────────────────────────────────────────
test("extractLayout — no yaml ui-layout fence → null", () => {
  const md = `
## Layout

Just some ASCII art here, no YAML fence.

\`\`\`yaml crm-contract
interactions: []
\`\`\`
`;
  const model = extractLayout(md);
  assert.equal(model, null, "absent fence must return null");
});

// ─── Test 8: region spanning multiple rows forms a valid rectangle ────────────
test("nonRectRegions — region spanning 2 rows in same column is a valid rectangle", () => {
  const md = `
\`\`\`yaml ui-layout
areas:
  - [left, right]
  - [left, bottom_right]
\`\`\`
`;
  // 'left' at (0,0) and (1,0) → 2×1 rectangle, valid
  const model = extractLayout(md);
  assert.ok(model !== null);
  const bad = nonRectRegions(model);
  assert.ok(!bad.includes("left"), "'left' spanning 2 rows in col 0 is a valid rectangle");
});

// ─── Test 9: unknown key collected as warning, model still parsed ─────────────
test("extractLayout — unknown key stored as _warnings, model not rejected", () => {
  const md = `
\`\`\`yaml ui-layout
areas:
  - [header, header]
  - [body, body]
mystery_key: something
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null, "unknown key should not cause null return");
  assert.ok(Array.isArray(model._warnings), "_warnings should be an array");
  assert.ok(model._warnings.some((w) => w.includes("mystery_key")), "_warnings should mention mystery_key");
});

// ─── Test 10: elements: map parsed as model.elements ─────────────────────────
test("extractLayout — elements: map parsed as model.elements", () => {
  const md = `
\`\`\`yaml ui-layout
areas:
  - [header, header]
  - [body, body]
elements:
  "📞Gọi": A-S14-006
  "360": A-S14-007
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null, "model should not be null");
  assert.ok(typeof model.elements === "object" && model.elements !== null, "model.elements should be an object");
  assert.equal(model.elements["📞Gọi"], "A-S14-006", "emoji chip key mapped correctly");
  assert.equal(model.elements["360"], "A-S14-007", "plain chip key mapped correctly");
  // elements is a known key — no _warnings for it
  assert.ok(
    !model._warnings || !model._warnings.some((w) => w.includes("elements")),
    "elements should not appear in _warnings (it is a known key)"
  );
});

// ─── Test 11: absent elements key → model.elements is undefined ───────────────
test("extractLayout — absent elements key → model.elements is undefined", () => {
  const md = `
\`\`\`yaml ui-layout
areas:
  - [header, header]
  - [body, body]
\`\`\`
`;
  const model = extractLayout(md);
  assert.ok(model !== null, "model should not be null");
  assert.equal(model.elements, undefined, "model.elements should be undefined when absent from fence");
});

// ─── Summary ─────────────────────────────────────────────────────────────────
console.log(`\nextract-layout.test: ${passed} passed, ${failed} failed`);
if (failed > 0) {
  process.exit(1);
}

// ─── layoutFenceInfo — broken-fence detection (batch-2 silent-failure fix) ────
import { layoutFenceInfo } from "./extract-layout.mjs";

test("layoutFenceInfo: no fence → hasFence=false", () => {
  const r = layoutFenceInfo("# Just prose\nno fence here");
  assert.deepEqual(r, { hasFence: false, parseError: null });
});

test("layoutFenceInfo: valid fence → no parseError", () => {
  const r = layoutFenceInfo("```yaml ui-layout\nareas:\n  - [a]\n```");
  assert.equal(r.hasFence, true);
  assert.equal(r.parseError, null);
});

test("layoutFenceInfo: broken YAML (block-mapping-with-comma) → parseError set", () => {
  const md = "```yaml ui-layout\nareas:\n  - [a]\ncontent:\n  a:\n    - btn: \"x\", action: A-1\n```";
  const r = layoutFenceInfo(md);
  assert.equal(r.hasFence, true);
  assert.ok(r.parseError, "expected a parse error message");
  // And extractLayout must return null for the same input (legacy behavior unchanged)
  assert.equal(extractLayout(md), null);
});

test("layoutFenceInfo: parses but no areas → parseError set", () => {
  const r = layoutFenceInfo("```yaml ui-layout\nsamples:\n  a: \"x\"\n```");
  assert.equal(r.hasFence, true);
  assert.ok(/areas/.test(r.parseError));
});

console.log(`\nextract-layout(+fenceInfo): ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
