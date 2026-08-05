// layout-schema.test.mjs — self-contained node test for layout-schema.mjs.
// No test framework. Uses assert + process.exit(1) on failure count.
// Run: node .skills/ui-spec/tools/wireframe/layout-schema.test.mjs

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  LAYOUT_KEYS,
  CONTENT_TYPES,
  contentElementType,
  walkContent,
  contentActionRefs,
  flattenContentLine,
} from "./layout-schema.mjs";

let passed = 0;
let failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  ✓ ${name}`);
    passed++;
  } catch (e) {
    console.error(`  ✗ ${name}\n    ${e.message}`);
    failed++;
  }
}

// ─── key sets ────────────────────────────────────────────────────────────────

test("LAYOUT_KEYS contains legacy + new keys", () => {
  for (const k of ["columns", "areas", "floating", "variants", "samples", "children", "elements", "row_heights", "content"]) {
    assert.ok(LAYOUT_KEYS.includes(k), `missing ${k}`);
  }
});

// ─── contentElementType ──────────────────────────────────────────────────────

test("contentElementType resolves first registry key", () => {
  assert.equal(contentElementType({ btn: "Gọi", action: "A-1" }), "btn");
  assert.equal(contentElementType({ table: { cols: ["a"], rows: 3 } }), "table");
  assert.equal(contentElementType({ unknown_thing: 1 }), null);
  assert.equal(contentElementType("just text"), null);
  assert.equal(contentElementType(null), null);
});

// ─── walkContent / contentActionRefs ─────────────────────────────────────────

test("walkContent recurses one level into row", () => {
  const content = {
    bar: [
      { row: [{ h: "Tên" }, { btn: "Gọi", action: "A-S14-006" }] },
      { badge: "GOLD" },
    ],
  };
  const seen = [];
  walkContent(content, ({ region, type }) => seen.push(region + ":" + type));
  assert.deepEqual(seen, ["bar:row", "bar:h", "bar:btn", "bar:badge"]);
});

test("contentActionRefs collects action opts incl. inside rows", () => {
  const content = {
    bar: [{ row: [{ btn: "Gọi", action: "A-S14-006" }] }, { tabs: ["A", "B"], action: "A-S14-010" }],
  };
  const refs = contentActionRefs(content);
  assert.deepEqual(refs.map((r) => r.actionId), ["A-S14-006", "A-S14-010"]);
});

test("contentActionRefs collects tabs per-label actions map", () => {
  const content = {
    tab_bar: [{ tabs: ["Đơn", "Chat"], actions: { "Đơn": "A-S03-005", "Chat": "A-S03-009" } }],
  };
  const refs = contentActionRefs(content);
  assert.deepEqual(refs.map((r) => [r.label, r.actionId]), [["Đơn", "A-S03-005"], ["Chat", "A-S03-009"]]);
});

// ─── flattenContentLine ──────────────────────────────────────────────────────

test("flattenContentLine renders each primitive deterministically", () => {
  const line = flattenContentLine([
    { row: [{ h: "Hoàng Thức" }, { badge: "GOLD" }, { btn: "Gọi", action: "A-1" }] },
    { checklist: ["[x] Nhắc chu kỳ", "Ưu đãi"] },
    { table: { cols: ["Tên", "SĐT"], rows: 4 } },
    { slot: "P01" },
  ]);
  assert.equal(
    line,
    "Hoàng Thức [GOLD] [Gọi] · [x] Nhắc chu kỳ [ ] Ưu đãi · tbl(Tên | SĐT) ×4 · <<P01>>"
  );
});

test("flattenContentLine is stable for empty/invalid input", () => {
  assert.equal(flattenContentLine(null), "");
  assert.equal(flattenContentLine([]), "");
  assert.equal(flattenContentLine([{ bogus: 1 }]), "");
});

// ─── browser-inline contract ─────────────────────────────────────────────────

test("module source is import-free and top-level-export-only (browser inline contract)", () => {
  const src = readFileSync(fileURLToPath(new URL("./layout-schema.mjs", import.meta.url)), "utf8");
  assert.ok(!/^import /m.test(src), "must not import anything");
  // Every export must be strippable by html-shell's regex.
  const badExports = src.match(/^export (?!(const|function)\b).*$/gm);
  assert.equal(badExports, null, `unstrippable exports: ${badExports}`);
});

test("export-stripped source evaluates in a bare scope (simulated browser)", () => {
  const src = readFileSync(fileURLToPath(new URL("./layout-schema.mjs", import.meta.url)), "utf8")
    .replace(/^export (?=(const|function|let|class)\b)/gm, "");
  // Evaluate stripped source; return one symbol from it to prove definitions exist.
  const fn = new Function(src + "\nreturn { CONTENT_TYPES, flattenContentLine };");
  const api = fn();
  assert.ok(api.CONTENT_TYPES.btn);
  assert.equal(api.flattenContentLine([{ btn: "X" }]), "[X]");
});

console.log(`\nlayout-schema: ${passed} passed, ${failed} failed`);
if (failed > 0) process.exit(1);
