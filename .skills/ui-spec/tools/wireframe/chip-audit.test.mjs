// chip-audit.test.mjs — self-contained node tests for chip-audit.mjs.
// No test framework. Uses assert + process.exit(1) on first failure.
// Run: node .agents/skills/ui-spec/tools/wireframe/chip-audit.test.mjs

import assert from "node:assert/strict";
import { auditChips, renderChipAuditMd } from "./chip-audit.mjs";

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

// ─── Test 1: surfaces without layout are skipped ──────────────────────────────
test("surfaces with null layout are skipped — audited count = 0", () => {
  const result = auditChips([
    { surfaceId: "S01", layout: null },
    { surfaceId: "S02", layout: null },
  ]);
  assert.equal(result.totals.surfaces, 0);
  assert.equal(result.totals.tokens, 0);
  assert.equal(result.entries.length, 0);
});

// ─── Test 2: surface without samples key → audited but 0 tokens ──────────────
test("layout without samples → surface counted, 0 tokens", () => {
  const result = auditChips([
    { surfaceId: "S03", layout: { areas: [["header"]] } },
  ]);
  assert.equal(result.totals.surfaces, 0, "no samples → not counted as audited");
  assert.equal(result.totals.tokens, 0);
});

// ─── Test 3: basic mapped vs unmapped classification ─────────────────────────
test("mapped vs unmapped classification", () => {
  const layout = {
    areas: [["header"], ["body"]],
    samples: {
      header: "Title [Save] [Cancel]",
      body: "Content [Delete]",
    },
    elements: { Save: "A-S01-001" },
  };
  const result = auditChips([{ surfaceId: "S01", layout }]);
  assert.equal(result.totals.tokens, 3);
  assert.equal(result.totals.mapped, 1);
  assert.equal(result.totals.unmapped, 2);
  const mapped = result.entries.filter((e) => e.status === "mapped");
  assert.equal(mapped.length, 1);
  assert.equal(mapped[0].token, "Save");
  const unmapped = result.entries.filter((e) => e.status === "unmapped");
  const unmappedTokens = unmapped.map((e) => e.token).sort();
  assert.deepEqual(unmappedTokens, ["Cancel", "Delete"]);
});

// ─── Test 4: Vietnamese text and emoji in tokens ──────────────────────────────
test("Vietnamese diacritics and emoji tokens extracted correctly", () => {
  const layout = {
    areas: [["topbar"]],
    samples: {
      topbar: "Tasks  [+ Tạo task]  [Priority ▼]  [Party 🔍]  [Status ▼]",
    },
    elements: { "+ Tạo task": "A-S07-001" },
  };
  const result = auditChips([{ surfaceId: "S07", layout }]);
  assert.equal(result.totals.tokens, 4);
  assert.equal(result.totals.mapped, 1);
  assert.equal(result.totals.unmapped, 3);
  const unmapped = result.entries
    .filter((e) => e.status === "unmapped")
    .map((e) => e.token);
  assert.ok(unmapped.includes("Priority ▼"), "Priority ▼ unmapped");
  assert.ok(unmapped.includes("Party 🔍"), "Party 🔍 unmapped");
  assert.ok(unmapped.includes("Status ▼"), "Status ▼ unmapped");
});

// ─── Test 5: deterministic ordering in renderChipAuditMd ─────────────────────
test("renderChipAuditMd — deterministic sort: surfaceId → region → token", () => {
  const surfaces = [
    {
      surfaceId: "S02",
      layout: {
        areas: [["body"]],
        samples: { body: "[Zebra] [Apple]" },
        elements: {},
      },
    },
    {
      surfaceId: "M01",
      layout: {
        areas: [["actions"]],
        samples: { actions: "[Beta] [Alpha]" },
        elements: {},
      },
    },
  ];
  const result = auditChips(surfaces);
  const md = renderChipAuditMd(result);

  // M01 should appear before S02 (lexicographic)
  const idxM01 = md.indexOf("### M01");
  const idxS02 = md.indexOf("### S02");
  assert.ok(idxM01 < idxS02, "M01 before S02 in output");

  // Within S02: Apple should appear before Zebra
  const idxApple = md.indexOf("`Apple`");
  const idxZebra = md.indexOf("`Zebra`");
  assert.ok(idxApple < idxZebra, "Apple sorted before Zebra within S02");
});

// ─── Test 6: two runs produce byte-identical output ──────────────────────────
test("renderChipAuditMd — same inputs → identical output (idempotent)", () => {
  const surfaces = [
    {
      surfaceId: "P02",
      layout: {
        areas: [["toolbar"]],
        samples: { toolbar: "[Xem thêm →]" },
        elements: {},
      },
    },
  ];
  const r1 = renderChipAuditMd(auditChips(surfaces));
  const r2 = renderChipAuditMd(auditChips(surfaces));
  assert.equal(r1, r2, "two renders of same data must be identical");
});

// ─── Test 7: no [token] in samples → 0 tokens ────────────────────────────────
test("samples with no bracket tokens → 0 tokens extracted", () => {
  const layout = {
    areas: [["body"]],
    samples: { body: "plain text, no brackets here" },
    elements: {},
  };
  const result = auditChips([{ surfaceId: "S05", layout }]);
  assert.equal(result.totals.tokens, 0);
});

// ─── Test 8: empty elements object — all chips unmapped ──────────────────────
test("empty elements: {} — all chips are unmapped", () => {
  const layout = {
    areas: [["header"]],
    samples: { header: "[← Quay lại]  [Save]" },
    elements: {},
  };
  const result = auditChips([{ surfaceId: "S15", layout }]);
  assert.equal(result.totals.unmapped, 2);
  assert.equal(result.totals.mapped, 0);
});

// ─── Test 9: mixed surfaces — one with layout, one without ───────────────────
test("mixed surfaces: one with layout, one null — only one audited", () => {
  const surfaces = [
    { surfaceId: "S01", layout: null },
    {
      surfaceId: "M13",
      layout: {
        areas: [["body"]],
        samples: { body: "[+ Thêm tùy chọn] [Hủy]" },
        elements: { "Hủy": "A-M13-002" },
      },
    },
  ];
  const result = auditChips(surfaces);
  assert.equal(result.totals.surfaces, 1, "only M13 audited");
  assert.equal(result.totals.tokens, 2);
  assert.equal(result.totals.mapped, 1);
  assert.equal(result.totals.unmapped, 1);
  const unmapped = result.entries.find((e) => e.status === "unmapped");
  assert.equal(unmapped.token, "+ Thêm tùy chọn");
  assert.equal(unmapped.surfaceId, "M13");
});

// ─── Summary ─────────────────────────────────────────────────────────────────
console.log(`\nchip-audit.test: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
