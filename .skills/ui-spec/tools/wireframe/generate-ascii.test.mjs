// generate-ascii.test.mjs — unit tests for generate-ascii.mjs
// No framework. Run: node .skills/ui-spec/tools/wireframe/generate-ascii.test.mjs

import assert from "node:assert/strict";
import { generateAscii, injectAscii, computeColWidths } from "./generate-ascii.mjs";

let passed = 0, failed = 0;
function test(name, fn) {
  try { fn(); console.log(`  ✓ ${name}`); passed++; }
  catch (e) { console.error(`  ✗ ${name}`); console.error(`    ${e.message}`); failed++; }
}

// ─── computeColWidths ─────────────────────────────────────────────────────────

test("colWidths: [3fr,2fr] total=78 → [45,30]", () => {
  // inner = 78-2-1 = 75; floor(3/5*75)=45; last=75-45=30
  const w = computeColWidths(["3fr", "2fr"], 78);
  assert.deepEqual(w, [45, 30]);
});

test("colWidths: [1fr,1fr] total=78 → [37,38] (last absorbs remainder)", () => {
  // inner=75; floor(1/2*75)=37; last=75-37=38
  const w = computeColWidths(["1fr", "1fr"], 78);
  assert.deepEqual(w, [37, 38]);
});

test("colWidths: sum matches inner (total-2-(M-1))", () => {
  const cols = ["2fr", "1fr", "1fr"];
  const w    = computeColWidths(cols, 78);
  // inner = 78-2-2 = 74
  assert.equal(w.reduce((a, b) => a + b, 0), 74);
});

test("colWidths: deterministic — same inputs produce identical output", () => {
  const a = computeColWidths(["3fr", "2fr"], 78);
  const b = computeColWidths(["3fr", "2fr"], 78);
  assert.deepEqual(a, b);
});

// ─── generateAscii — basic structure ─────────────────────────────────────────

const simple2col = {
  columns: ["1fr", "1fr"],
  areas: [
    ["header", "header"],
    ["left",   "right"],
    ["footer", "footer"],
  ],
  samples: { header: "Page Title", left: "Nav", right: "Content", footer: "Footer" },
};

test("generateAscii: output is non-empty string", () => {
  const out = generateAscii(simple2col);
  assert.equal(typeof out, "string");
  assert.ok(out.length > 0);
});

test("generateAscii: every row is exactly 78 chars wide", () => {
  const out   = generateAscii(simple2col);
  const lines = out.split("\n");
  for (const line of lines) {
    assert.equal(line.length, 78, `Row length mismatch: "${line.slice(0, 20)}…"`);
  }
});

test("generateAscii: top-left char is ┌ and top-right is ┐", () => {
  const out  = generateAscii(simple2col);
  const rows = out.split("\n");
  assert.equal(rows[0][0],  "┌", "top-left");
  assert.equal(rows[0][77], "┐", "top-right");
});

test("generateAscii: bottom-left char is └ and bottom-right is ┘", () => {
  const out  = generateAscii(simple2col);
  const rows = out.split("\n");
  const last = rows[rows.length - 1];
  assert.equal(last[0],  "└", "bottom-left");
  assert.equal(last[77], "┘", "bottom-right");
});

test("generateAscii: region names appear UPPER in output", () => {
  const out = generateAscii(simple2col);
  assert.ok(out.includes("HEADER"),  "HEADER present");
  assert.ok(out.includes("LEFT"),    "LEFT present");
  assert.ok(out.includes("RIGHT"),   "RIGHT present");
  assert.ok(out.includes("FOOTER"),  "FOOTER present");
});

test("generateAscii: sample text prefixed with '· ' appears in output", () => {
  const out = generateAscii(simple2col);
  assert.ok(out.includes("· Page Title"), "header sample");
  assert.ok(out.includes("· Nav"),        "left sample");
  assert.ok(out.includes("· Content"),    "right sample");
});

// ─── Rowspan — interior border suppression ────────────────────────────────────

const rowspanModel = {
  columns: ["1fr", "1fr"],
  areas: [
    ["head",  "side"],
    ["body",  "side"],  // "side" spans rows 0-1
    ["foot",  "foot"],
  ],
  samples: { head: "Head", body: "Body", side: "Side content", foot: "Footer" },
};

test("rowspan: interior horizontal border suppressed for spanning region", () => {
  const out   = generateAscii(rowspanModel);
  const lines = out.split("\n");

  // The separator between rows 0 and 1 is at pixel row 3 (3*1).
  // In col 1 (spanning "side"), hasH[1]=false → segment chars must be " " not "─".
  // Col 1 inner starts at position colLeft[1]+1.
  // colW[0]=37, colW[1]=38, colLeft[0]=0, colLeft[1]=38
  const borderRow = lines[3]; // pixel row 3*1
  // Right side of the border row (positions 39-76) should be spaces (no "─")
  const rightSegment = borderRow.slice(39, 77);
  assert.ok(!rightSegment.includes("─"),
    `Interior of spanning region should have spaces, got: "${rightSegment}"`);
});

test("rowspan: spanning region name appears only once", () => {
  const out = generateAscii(rowspanModel);
  // "SIDE" should appear exactly once (in the name row of its first grid row)
  const matches = [...out.matchAll(/SIDE/g)];
  assert.equal(matches.length, 1, `SIDE should appear once, found ${matches.length}`);
});

test("rowspan: right outer border is │ on suppressed interior row", () => {
  const out   = generateAscii(rowspanModel);
  const lines = out.split("\n");
  // pixel row 3 = separator between rows 0 and 1
  const borderRow = lines[3];
  assert.equal(borderRow[77], "│",
    "Outer right border must be │ (not ┤) when only left col has h-line");
});

// ─── Variant blocks ───────────────────────────────────────────────────────────

test("generateAscii: variant block labelled with [variant: <name>]", () => {
  const model = {
    columns: ["1fr"],
    areas: [["main"]],
    variants: { full_screen: { prepend_rows: [["topbar"]] } },
    samples: { main: "Content", topbar: "Topbar" },
  };
  const out = generateAscii(model);
  assert.ok(out.includes("[variant: full_screen]"), "variant label present");
  assert.ok(out.includes("TOPBAR"), "topbar region in variant block");
});

// ─── Floating blocks ─────────────────────────────────────────────────────────

test("generateAscii: floating block rendered with [STOP variant — when: ...] label", () => {
  const model = {
    columns: ["1fr"],
    areas: [["main"]],
    floating: [{ region: "stop_banner", when: "recommended == false" }],
    samples: {},
  };
  const out = generateAscii(model);
  assert.ok(out.includes("[STOP variant — when: recommended == false]"), "stop label present");
  assert.ok(out.includes("STOP_BANNER"), "region name in floating block");
});

test("generateAscii: floating block includes when: caption inside box", () => {
  const model = {
    columns: ["1fr"],
    areas: [["main"]],
    floating: [{ region: "stop_banner", when: "recommended == false" }],
    samples: { stop_banner: "⛔ STOP MSG" },
  };
  const out = generateAscii(model);
  const floatPart = out.split("\n\n").find((p) => p.includes("STOP_BANNER"));
  assert.ok(floatPart, "floating block present");
  assert.ok(floatPart.includes("when: recommended == false"), "when: caption inside box");
  assert.ok(floatPart.includes("· !! STOP MSG"), "sample line with glyph substitution");
});

test("generateAscii: floating block without when: has no when: caption inside box", () => {
  const model = {
    columns: ["1fr"],
    areas: [["main"]],
    floating: [{ region: "stop_banner" }],
    samples: { stop_banner: "MSG" },
  };
  const out = generateAscii(model);
  const floatPart = out.split("\n\n").find((p) => p.includes("STOP_BANNER"));
  assert.ok(floatPart, "floating block present");
  assert.ok(!floatPart.includes("when:"), "no when: line without condition");
  assert.ok(floatPart.includes("· MSG"), "sample line still rendered");
});

test("generateAscii: floating block is 78 chars wide", () => {
  const model = {
    columns: ["1fr"],
    areas: [["main"]],
    floating: [{ region: "stop_banner", when: "cond" }],
    samples: {},
  };
  const out   = generateAscii(model);
  const parts = out.split("\n\n");
  const floatPart = parts.find((p) => p.includes("STOP_BANNER"));
  assert.ok(floatPart, "floating block present");
  // Lines after the label line must be 78 wide
  const lines = floatPart.split("\n").filter((l) => l.startsWith("┌") || l.startsWith("│") || l.startsWith("└"));
  for (const line of lines) {
    assert.equal(line.length, 78, `Floating line not 78: "${line.slice(0, 20)}"`);
  }
});

// ─── Glyph normalization ──────────────────────────────────────────────────────

test("generateAscii: ⚠ in sample normalized to ! in output", () => {
  const model = {
    columns: ["1fr"],
    areas: [["alert"]],
    samples: { alert: "⚠ Watch out" },
  };
  const out = generateAscii(model);
  assert.ok(out.includes("! Watch out"), "⚠ → ! substitution applied");
  assert.ok(!out.includes("⚠"),          "original ⚠ not in output");
});

test("generateAscii: ★ in sample normalized to * in output", () => {
  const model = {
    columns: ["1fr"],
    areas: [["cell"]],
    samples: { cell: "★ Primary" },
  };
  const out = generateAscii(model);
  assert.ok(out.includes("* Primary"), "★ → * substitution applied");
});

test("generateAscii: ⛔ in sample normalized to !! in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "⛔ STOP" } };
  const out = generateAscii(model);
  assert.ok(out.includes("!! STOP"), "⛔ → !! applied");
  assert.ok(!out.includes("⛔"), "original ⛔ not in output");
});

test("generateAscii: ☑/☐ in sample normalized to [x]/[ ] in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "☑ Done ☐ Pending" } };
  const out = generateAscii(model);
  assert.ok(out.includes("[x] Done"), "☑ → [x] applied");
  assert.ok(out.includes("[ ] Pending"), "☐ → [ ] applied");
});

test("generateAscii: ▸/▾ in sample normalized to >/<v> in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "▸ Item ▾ Sub" } };
  const out = generateAscii(model);
  assert.ok(out.includes("> Item"), "▸ → > applied");
  assert.ok(out.includes("v Sub"), "▾ → v applied");
});

test("generateAscii: emoji 📞/💬/📋/🔍/🛒 normalized to ASCII in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "[📞][💬][📋][🔍][🛒]" } };
  const out = generateAscii(model);
  assert.ok(out.includes("[>][~][#][(?)][$]"), "emoji → ASCII substitutions applied");
  assert.ok(!out.includes("📞") && !out.includes("💬"), "originals not in output");
});

test("generateAscii: ⏱/⏳ in sample normalized to (t) in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "⏱ Timer ⏳ Wait" } };
  const out = generateAscii(model);
  assert.ok(out.includes("(t) Timer"), "⏱ → (t) applied");
  assert.ok(out.includes("(t) Wait"), "⏳ → (t) applied");
});

test("generateAscii: ✅/❌ in sample normalized to [x]/x in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "✅ OK ❌ Fail" } };
  const out = generateAscii(model);
  assert.ok(out.includes("[x] OK"), "✅ → [x] applied");
  assert.ok(out.includes("x Fail"), "❌ → x applied");
});

test("generateAscii: ☎/✉ in sample normalized to T:/@  in output", () => {
  const model = { columns: ["1fr"], areas: [["r"]], samples: { r: "☎ 012 ✉ mail" } };
  const out = generateAscii(model);
  assert.ok(out.includes("T: 012"), "☎ → T: applied");
  assert.ok(out.includes("@ mail"), "✉ → @ applied");
});

// ─── Idempotency ─────────────────────────────────────────────────────────────

test("generateAscii: idempotent — same model produces byte-identical output", () => {
  const out1 = generateAscii(simple2col);
  const out2 = generateAscii(simple2col);
  assert.equal(out1, out2, "two calls with same model must produce identical output");
});

test("generateAscii: idempotent — S14-like model with rowspan and variant", () => {
  const model = {
    columns: ["3fr", "2fr"],
    areas: [
      ["identity_bar", "identity_bar"],
      ["talk_track",   "reason_to_call"],
      ["strategy",     "reason_to_call"],
      ["footer",       "footer"],
    ],
    variants: { full_screen: { prepend_rows: [["topbar", "topbar"]] } },
    floating: [{ region: "stop", when: "x == false" }],
    samples: { identity_bar: "Alice", talk_track: "Hello", reason_to_call: "WHY", footer: "END" },
  };
  assert.equal(generateAscii(model), generateAscii(model));
});

// ─── injectAscii ─────────────────────────────────────────────────────────────

const MARKER_START = "<!-- ui-layout:ascii:start -->";
const MARKER_END   = "<!-- ui-layout:ascii:end -->";

test("injectAscii: inserts markers after ui-layout fence when absent", () => {
  const md = `# Test\n\n\`\`\`yaml ui-layout\nareas:\n  - [main]\n\`\`\`\n\nSome prose.\n`;
  const result = injectAscii(md, "┌──┐\n│  │\n└──┘");
  assert.ok(result.includes(MARKER_START), "start marker added");
  assert.ok(result.includes(MARKER_END),   "end marker added");
  // Markers should come after the fence
  const fenceEnd = md.indexOf("```\n\nSome") + 3;
  const markerIdx = result.indexOf(MARKER_START);
  assert.ok(markerIdx > fenceEnd, "marker after fence");
});

test("injectAscii: replaces existing markers on second call", () => {
  const md = `# T\n\`\`\`yaml ui-layout\nareas:\n  - [m]\n\`\`\`\n`;
  const v1 = injectAscii(md, "┌─┐\n│A│\n└─┘");
  const v2 = injectAscii(v1, "┌─┐\n│B│\n└─┘");
  // v2 should have B and not A in the marked region
  const startIdx = v2.indexOf(MARKER_START);
  const endIdx   = v2.indexOf(MARKER_END);
  const between  = v2.slice(startIdx, endIdx + MARKER_END.length);
  assert.ok(between.includes("│B│"), "new content present");
  assert.ok(!between.includes("│A│"), "old content replaced");
});

test("injectAscii: idempotent — injecting same ascii twice yields identical file", () => {
  const md  = `# T\n\`\`\`yaml ui-layout\nareas:\n  - [m]\n\`\`\`\n`;
  const asc = "┌──────────────────────────────────────────────────────────────────────────────┐\n│ M                                                                            │\n└──────────────────────────────────────────────────────────────────────────────┘";
  const v1  = injectAscii(md, asc);
  const v2  = injectAscii(v1, asc);
  assert.equal(v1, v2, "second injection yields byte-identical file");
});

test("injectAscii: marker count stays at one pair after multiple calls", () => {
  const md  = `# T\n\`\`\`yaml ui-layout\nareas:\n  - [m]\n\`\`\`\n`;
  let current = md;
  for (let i = 0; i < 3; i++) current = injectAscii(current, "┌─┐\n│x│\n└─┘");
  const startCount = [...current.matchAll(/<!-- ui-layout:ascii:start -->/g)].length;
  const endCount   = [...current.matchAll(/<!-- ui-layout:ascii:end -->/g)].length;
  assert.equal(startCount, 1, "only one start marker");
  assert.equal(endCount,   1, "only one end marker");
});

// ─── Summary ──────────────────────────────────────────────────────────────────
console.log(`\ngenerate-ascii.test: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
