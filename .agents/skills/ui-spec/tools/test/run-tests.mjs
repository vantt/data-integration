// run-tests.mjs — regression harness for ui-spec validator.
// Spawns validate.mjs against the seeded fixture and asserts expected findings fire.
// Also asserts the production crm spec still passes clean.
// Exit 0 = all assertions passed. Exit 1 = any assertion failed.

import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { isDeepStrictEqual } from "node:util";

const __dirname = dirname(fileURLToPath(import.meta.url));
const validateMjs   = resolve(__dirname, "..", "validate.mjs");
const fixtureRoot   = join(__dirname, "fixture-spec");
// repo root is 5 levels above test/ (.agents/skills/ui-spec/tools/test → repo root)
const repoRoot      = resolve(__dirname, "..", "..", "..", "..", "..");
const crmSpecRoot   = join(repoRoot, "crm", "docs", "ui-spec");

// ---- helpers ----

function runValidate(rootPath) {
  const r = spawnSync(process.execPath, [validateMjs, "--root", rootPath], { encoding: "utf8" });
  return {
    code:   r.status ?? 1,
    stdout: r.stdout ?? "",
    stderr: r.stderr ?? "",
    out:    (r.stdout ?? "") + (r.stderr ?? ""),
  };
}

let passed = 0;
let failed = 0;

function assert(label, condition, detail = "") {
  if (condition) {
    console.log(`  PASS  ${label}`);
    passed++;
  } else {
    console.error(`  FAIL  ${label}${detail ? "\n        " + detail : ""}`);
    failed++;
  }
}

function assertContains(out, substring, label) {
  assert(label, out.includes(substring), `expected substring: ${JSON.stringify(substring)}`);
}

// ---- Suite 1: fixture must exit 1 with all expected findings ----

console.log("\n=== Suite 1: seeded fixture (expect exit 1) ===");
const fix = runValidate(fixtureRoot);

assert("exit code is 1", fix.code === 1,
  `got exit code ${fix.code}\nstdout: ${fix.stdout}\nstderr: ${fix.stderr}`);

// New rules (F1, F2, F3)
assertContains(fix.out, "VR-SURFACE-DUP",
  "F1 VR-SURFACE-DUP fires for duplicate surface id S01");
assertContains(fix.out, "duplicate surface id",
  "F1 duplicate surface id message present");
assertContains(fix.out, "VR-COMPONENT-NAV",
  "F2 VR-COMPONENT-NAV fires for C01 navigate action");
assertContains(fix.out, "VR-HOSTS-TYPE",
  "F3 VR-HOSTS-TYPE fires for S01 hosts M01 (modal, not panel)");

// Existing rules — representative set
assertContains(fix.out, "S99",
  "VR-TARGET: dangling target S99");
assertContains(fix.out, "duplicate action id",
  "VR-ID-UNIQUE: duplicate action A-S01-001");
assertContains(fix.out, "VR-MODAL-EXIT-001",
  "VR-MODAL-EXIT-001: M01 has no exit action");
assertContains(fix.out, "drift",
  "VR-RULE-DRIFT: R1 listed surface S01 but S01.rules omits R1");
assertContains(fix.out, "show_panel",
  "VR-SHOW-PANEL: show_panel target M01 is not type=panel");
assertContains(fix.out, "S98",
  "VR-HOSTED-BY: P01 hosted_by unknown surface S98");
assertContains(fix.out, "A-DEAD-999",
  "VR-FLOW: flow step A-DEAD-999 does not exist");
assertContains(fix.out, "ghost_event",
  "VR-LISTEN-ORPHAN: ghost_event not emitted by any surface");

// F4 positive: description field in 20-domain-rules.md must NOT produce a schema error
// (if schema errored on description, we'd see a schema error mentioning "description")
assert("F4 schema allows description in ruleMapping (no schema error for description field)",
  !fix.out.includes('"description" is not allowed') && !fix.out.includes("description') is not allowed"),
  "schema rejected the description field — F4 fix may not have reached the fixture schema");

// Latent-issue round — extended coverage for rules that were previously unasserted
assertContains(fix.out, "side.info",
  "VR-REGION-PARENT: side.info declared but parent segment side missing from regions[]");
assertContains(fix.out, "P99",
  "VR-EFFECT-SURFACE: effect P99.reload references unknown surface P99");
assertContains(fix.out, "S02.hosts includes P01",
  "VR-HOSTS-BIDIR (reverse): S02.hosts includes P01 but P01.hosted_by omits S02");
assertContains(fix.out, "go_btn",
  "VR-ELEMENT-UNIQUE: go_btn appears in multiple interactions in S01");
assertContains(fix.out, "orderId",
  "VR-PAYLOAD-GRAMMAR: bare $orderId token on non-component interaction in S01");
assertContains(fix.out, "VR-ENTRY",
  "VR-ENTRY: entry_surface S77 is not a known surface id");
assertContains(fix.out, "VR-PREFIX-TYPE",
  "VR-PREFIX-TYPE: P02 has type=screen but prefix P (expected S)");
assertContains(fix.out, "screens/nested",
  "VR-SUBDIR: screens/nested contains .md files that are NOT scanned");

// ---- Suite 2: crm spec must still pass clean ----

console.log("\n=== Suite 2: production crm spec (expect exit 0, 0 warnings) ===");
const crm = runValidate(crmSpecRoot);

assert("crm spec exits 0", crm.code === 0,
  `got exit code ${crm.code}\nstdout: ${crm.stdout.slice(0, 800)}\nstderr: ${crm.stderr.slice(0, 800)}`);
assert("crm spec reports 0 warning(s)", crm.out.includes("0 warning"),
  `output: ${crm.stdout.slice(0, 400)}`);

// ---- Suite 3: schema sync ----
// Guard against the skill-template schema and the crm spec schema drifting apart.

console.log("\n=== Suite 3: schema sync (template ↔ crm spec) ===");
const skillSchemaPath = resolve(__dirname, "..", "..", "templates", "schema", "surface-contract.schema.json");
const crmSchemaPath   = join(crmSpecRoot, "schema", "surface-contract.schema.json");

let skillSchema, crmSchema;
try {
  skillSchema = JSON.parse(readFileSync(skillSchemaPath, "utf8"));
  crmSchema   = JSON.parse(readFileSync(crmSchemaPath,  "utf8"));
} catch (e) {
  console.error(`  FAIL  schema files readable\n        ${e.message}`);
  failed++;
}

if (skillSchema && crmSchema) {
  assert(
    "template schema deep-equals crm spec schema",
    isDeepStrictEqual(skillSchema, crmSchema),
    `schemas diverge — sync ${skillSchemaPath} and ${crmSchemaPath}`
  );
}

// ---- Summary ----

console.log(`\n${"─".repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failed > 0) {
  console.error(`\nTest run FAILED — ${failed} assertion(s) did not hold.`);
  process.exit(1);
}
console.log("\nAll assertions passed.");
