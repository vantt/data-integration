// validate.mjs — gate. Non-conforming files -> exit code 1 (red build).
// Run before build. All structural/cross-file rules live here.
// Supports: --root <spec-root> CLI arg (forwarded to config.mjs).

import { readFileSync, existsSync, readdirSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv";
import { extractAll, SPEC_ROOT } from "./extract.mjs";
import { schemaPath } from "./config.mjs";

// Surface ID pattern: one or two uppercase letters + digits (e.g. S01, M2, P10, OV3)
const SURFACE_ID_RE = /^[A-Z]{1,2}\d+$/;
const RESERVED_TARGETS = new Set(["self", "return_to_invoker"]);

// ---- Schema setup ----
if (!existsSync(schemaPath)) {
  console.error(`ERROR: Schema not found at ${schemaPath}\n  Create schema/surface-contract.schema.json in your spec root.`);
  process.exit(1);
}
const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const ajv = new Ajv({ allErrors: true, strict: false });
const validateSchema = ajv.compile(schema);

const errors = [];
const warns = [];
const err  = (file, msg) => errors.push(`✗ [${file}] ${msg}`);
const warn = (file, msg) => warns.push(`⚠ [${file}] ${msg}`);

const files = extractAll();

// ---- Pass 1: per-file structural + schema ----
const knownSurfaceIds   = new Set();
const actionIndex       = new Map();   // actionId -> file
const allInteractions   = [];          // flat list with file/surfaceId context
const emittedEvents     = new Set();
const listenedEvents    = new Set();
const ruleMappings      = [];          // { id, surfaces[], file }
const surfaceRulesDeclared = new Map();// surfaceId -> Set(ruleId)
const surfaceRegions    = new Map();   // surfaceId -> string[] (from frontmatter regions[])

for (const f of files) {
  // Extractor-level errors (missing/duplicate block, yaml parse)
  for (const e of f.errors) err(f.file, e);
  if (!f.contract) continue;

  // VR-FRONTMATTER: required frontmatter fields
  const m = f.meta || {};
  if (!m.id)   err(f.file, "frontmatter missing `id`");
  if (!m.type) err(f.file, "frontmatter missing `type`");
  if (!m.name) err(f.file, "frontmatter missing `name`");

  // VR-FILE-ID: frontmatter id must match filename prefix for surface files
  if (m.id && SURFACE_ID_RE.test(m.id)) {
    knownSurfaceIds.add(m.id);
    if (!f.fileBase.startsWith(m.id + "-")) {
      err(f.file, `frontmatter id \`${m.id}\` does not match filename \`${f.fileBase}\``);
    }
  }

  // Collect declared rules and regions for cross-file checks
  if (Array.isArray(m.rules))   surfaceRulesDeclared.set(m.id, new Set(m.rules));
  if (Array.isArray(m.regions)) surfaceRegions.set(m.id, m.regions);

  // VR-SCHEMA: validate contract block against JSON schema
  if (!validateSchema(f.contract)) {
    for (const e of validateSchema.errors) {
      err(f.file, `schema ${e.instancePath || "/"} ${e.message}`);
    }
  }

  // Collect interactions, emits, rule mappings
  const c = f.contract;
  for (const it of c.interactions || []) {
    allInteractions.push({ file: f.file, surfaceId: m.id, type: m.type, regions: m.regions, ...it });
    if (it.event && it.action === "emit_event") emittedEvents.add(it.event);
    if (it.listens_to) listenedEvents.add(it.listens_to);
  }
  for (const em of c.emits || []) {
    allInteractions.push({ file: f.file, surfaceId: m.id, type: m.type, ...em, action: "emit_event" });
    if (em.event) emittedEvents.add(em.event);
  }
  for (const rm of c.rules || []) ruleMappings.push({ ...rm, file: f.file });
}

// ---- Pass 2: cross-file rules ----

// VR-ID-UNIQUE: action IDs must be globally unique
for (const it of allInteractions) {
  if (!it.id) continue;
  if (actionIndex.has(it.id)) {
    err(it.file, `duplicate action id \`${it.id}\` (also in ${actionIndex.get(it.id)})`);
  } else {
    actionIndex.set(it.id, it.file);
  }
}

// VR-ID-PREFIX: action ID prefix must match its surface (e.g. A-S01 lives in S01)
for (const it of allInteractions) {
  if (!it.id || !it.surfaceId) continue;
  // Auto-generated IDs (A-{surfaceId}-NNN) already conform; check manually assigned ones
  const prefixMatch = it.id.match(/^[A-Za-z]+-([A-Z]{1,2}\d+)/);
  if (prefixMatch && prefixMatch[1] !== it.surfaceId) {
    warn(it.file, `action \`${it.id}\` has prefix for ${prefixMatch[1]} but lives in ${it.surfaceId}`);
  }
}

// VR-TARGET: target must be a known surface, reserved keyword, external:, or emitted event
for (const it of allInteractions) {
  if (!it.target) continue;
  const t = String(it.target);
  if (RESERVED_TARGETS.has(t) || t.startsWith("external:")) continue;
  if (SURFACE_ID_RE.test(t)) {
    if (!knownSurfaceIds.has(t)) err(it.file, `target \`${t}\` (action ${it.id ?? "?"}) not a known surface`);
  } else {
    // Treat as event name — warn if nobody emits it
    if (!emittedEvents.has(t)) warn(it.file, `target \`${t}\` (action ${it.id ?? "?"}) is not a surface or emitted event`);
  }
}

// VR-MODAL-EXIT: modals must have close_overlay action + return_to_invoker target
const modalIds = [...knownSurfaceIds].filter((s) => {
  const f = files.find((f) => f.meta?.id === s);
  return f?.meta?.type === "modal" || s.startsWith("M");
});
for (const mid of modalIds) {
  const acts = allInteractions.filter((i) => i.surfaceId === mid);
  if (!acts.some((a) => a.action === "close_overlay")) {
    err(mid, `modal ${mid} has no close_overlay/submit exit (VR-MODAL-EXIT-001)`);
  }
  if (!acts.some((a) => a.target === "return_to_invoker")) {
    warn(mid, `modal ${mid} has no return_to_invoker exit (VR-MODAL-EXIT-002)`);
  }
}

// VR-RULE-DRIFT: rule-surface bidirectional consistency
for (const rm of ruleMappings) {
  for (const sid of rm.surfaces || []) {
    const declared = surfaceRulesDeclared.get(sid);
    if (!declared) {
      warn(rm.file, `rule ${rm.id} lists surface ${sid} but ${sid} has no frontmatter (not yet authored?)`);
    } else if (!declared.has(rm.id)) {
      err(rm.file, `rule ${rm.id} requires surface ${sid}, but ${sid} frontmatter \`rules\` omits ${rm.id} (drift)`);
    }
  }
}

// VR-REGION: warn if interaction.region is not in surface frontmatter regions[]
for (const it of allInteractions) {
  if (!it.region || !it.surfaceId) continue;
  const knownRegions = surfaceRegions.get(it.surfaceId);
  if (knownRegions && !knownRegions.includes(it.region)) {
    warn(it.file, `action \`${it.id ?? "?"}\` references region \`${it.region}\` not in surface ${it.surfaceId} frontmatter regions[]`);
  }
}

// VR-EMIT-LISTEN: emitted event has no listener (informational warning)
for (const ev of emittedEvents) {
  if (!listenedEvents.has(ev)) warn("graph", `emitted event \`${ev}\` has no listener (listens_to)`);
}

// VR-HOSTS: frontmatter hosts[] must reference known surfaces (a component's host screens)
for (const f of files) {
  if (!Array.isArray(f.meta?.hosts)) continue;
  for (const h of f.meta.hosts) {
    if (!knownSurfaceIds.has(h)) err(f.file, `hosts[] references \`${h}\` — not a known surface (typo or missing screen)`);
  }
}

// VR-LISTEN-ORPHAN: a `listens_to` event must resolve to an in-spec emitted event OR be an
// external/system signal (dotted namespace, e.g. `upload.done` — emitted by the backend, not
// the UI spec). Anything else is a dangling reference — almost always a typo or missing emitter.
for (const it of allInteractions) {
  if (!it.listens_to) continue;
  const ev = String(it.listens_to);
  if (emittedEvents.has(ev) || ev.includes(".")) continue;
  err(it.file, `listens_to \`${ev}\` (action ${it.id ?? "?"}) is not emitted by any surface and is not an external (dotted) signal — likely a typo or missing emitter`);
}

// VR-STATE: a surface's prose state references (ST-*) must exist in the 30-states-and-errors.md
// catalog (its `### ST-*` headings ARE the registry). States are documentation-level → warn, not
// error. Catalog + references both live in prose, so we scan raw markdown on both ends.
// The states catalog (e.g. 30-states-and-errors.md) is a cross-cutting prose file that may
// not be in extractAll()'s list — read it directly from the spec root by name.
const stateCatalog = new Set();
try {
  const catalogName = readdirSync(SPEC_ROOT).find((n) => /states/i.test(n) && n.endsWith(".md"));
  if (catalogName) {
    const raw = readFileSync(join(SPEC_ROOT, catalogName), "utf8");
    for (const mm of raw.matchAll(/^#{2,4}\s+(ST-[A-Za-z0-9-]+)/gm)) stateCatalog.add(mm[1]);
  }
} catch { /* catalog unreadable — skip state checks */ }
if (stateCatalog.size) {
  for (const f of files) {
    if (!f.meta?.id || f.meta.id === "states-errors") continue;
    let raw;
    try { raw = readFileSync(join(SPEC_ROOT, f.file), "utf8"); } catch { continue; }
    const flagged = new Set();
    for (const mm of raw.matchAll(/\bST-[A-Za-z0-9-]+/g)) {
      const id = mm[0];
      if (stateCatalog.has(id) || flagged.has(id)) continue;
      flagged.add(id);
      warn(f.file, `references state \`${id}\` not defined in 30-states-and-errors.md catalog (typo or missing state)`);
    }
  }
}

// VR-OVERVIEW: the 00-overview index tables must list every surface, with no unknown IDs and
// names matching frontmatter (drift guard). Warn-level — overview is a human convenience doc.
const surfaceNameById = new Map();
for (const f of files) {
  if (f.meta?.id && SURFACE_ID_RE.test(f.meta.id)) surfaceNameById.set(f.meta.id, (f.meta.name || "").trim());
}
try {
  const ovName = readdirSync(SPEC_ROOT).find((n) => /overview/i.test(n) && n.endsWith(".md"));
  if (ovName && surfaceNameById.size) {
    const raw = readFileSync(join(SPEC_ROOT, ovName), "utf8");
    const inOverview = new Set();
    for (const mm of raw.matchAll(/^\|\s*([A-Z]{1,2}\d+)\s*\|\s*([^|]+?)\s*\|/gm)) {
      const id = mm[1], name = mm[2].trim();
      inOverview.add(id);
      if (!surfaceNameById.has(id)) { warn(ovName, `index lists \`${id}\` which is not a known surface`); continue; }
      const fmName = surfaceNameById.get(id);
      if (fmName && name && fmName !== name && !fmName.includes(name) && !name.includes(fmName)) {
        warn(ovName, `index name for ${id} is "${name}" but frontmatter name is "${fmName}" (drift)`);
      }
    }
    for (const id of surfaceNameById.keys()) {
      if (!inOverview.has(id)) warn(ovName, `surface ${id} is missing from the index`);
    }
  }
} catch { /* overview unreadable — skip */ }

// VR-FLOW: a flow's contract steps + branch actions must resolve to real action IDs (no dangling
// step refs). Error-level — a flow pointing at a non-existent action is broken. (Prose narration
// may cite related actions for context, so we validate the contract, not the prose.)
for (const f of files) {
  if (f.meta?.type !== "flow" || !f.contract?.flow) continue;
  const flow = f.contract.flow;
  const refs = [...(flow.steps || []), ...((flow.branches || []).map((b) => b.action))];
  for (const aid of refs) {
    if (aid && !actionIndex.has(aid)) err(f.file, `flow references action \`${aid}\` which does not exist (dangling step/branch)`);
  }
}

// ---- Report ----
console.log(`Scanned ${files.length} spec files, ${actionIndex.size} actions, ${knownSurfaceIds.size} surfaces.`);
for (const w of warns) console.log(w);
if (errors.length) {
  console.error(`\n${errors.length} ERROR(S):`);
  for (const e of errors) console.error(e);
  process.exit(1);
}
console.log(`\n✓ validation passed (${warns.length} warning(s)).`);
