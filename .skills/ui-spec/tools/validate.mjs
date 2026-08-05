// validate.mjs — gate. Non-conforming files -> exit code 1 (red build).
// Run before build. All structural/cross-file rules live here.
// Supports: --root <spec-root> CLI arg (forwarded to config.mjs).

import { readFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import Ajv from "ajv";
import { extractAll, SPEC_ROOT } from "./extract.mjs";
import { schemaPath, config, surfaceDirs } from "./config.mjs";
import { extractLayout, layoutAreaNames, nonRectRegions, layoutFenceInfo } from "./wireframe/extract-layout.mjs";
import { walkContent, contentActionRefs } from "./wireframe/layout-schema.mjs";
import { generateAscii, injectAscii } from "./wireframe/generate-ascii.mjs";

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
const surfaceFileById   = new Map();   // surfaceId -> first declaring file (VR-SURFACE-DUP)
const actionIndex       = new Map();   // actionId -> file
const allInteractions   = [];          // flat list with file/surfaceId context
const emittedEvents     = new Set();
const listenedEvents    = new Set();
const ruleMappings      = [];          // { id, surfaces[], file }
const surfaceRulesDeclared = new Map();// surfaceId -> Set(ruleId)
const surfaceRegions    = new Map();   // surfaceId -> string[] (from frontmatter regions[])

// surfaceTypeById is built in pass-1 for use by pass-2 rules (VR-SHOW-PANEL, VR-HOSTS-BIDIR)
const surfaceTypeById = new Map();

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
  // VR-SURFACE-DUP: same surface id declared in two or more files -> error naming both
  if (m.id && SURFACE_ID_RE.test(m.id)) {
    if (knownSurfaceIds.has(m.id)) {
      err(f.file, `duplicate surface id \`${m.id}\` — also declared in ${surfaceFileById.get(m.id)} (VR-SURFACE-DUP)`);
    } else {
      surfaceFileById.set(m.id, f.file);
    }
    knownSurfaceIds.add(m.id);
    surfaceTypeById.set(m.id, m.type);
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

// VR-SUBDIR: surface dirs must not contain subdirectories that themselves have .md files —
// those files are NOT scanned by listSpecFiles (which is non-recursive by design).
for (const dir of surfaceDirs) {
  const abs = join(SPEC_ROOT, dir);
  let entries = [];
  try { entries = readdirSync(abs); } catch { continue; }
  for (const e of entries) {
    const sub = join(abs, e);
    let st;
    try { st = statSync(sub); } catch { continue; }
    if (!st.isDirectory()) continue;
    let subEntries = [];
    try { subEntries = readdirSync(sub); } catch { continue; }
    if (subEntries.some((f) => f.endsWith(".md"))) {
      warn(`${dir}/${e}`, `contains .md files that are NOT scanned (spec files must sit directly in the surface dir)`);
    }
  }
}

// VR-ENTRY: config.entry_surface (spec.config.yaml), when set, must be a known surface id
if (config.entry_surface && !knownSurfaceIds.has(config.entry_surface)) {
  err("spec.config.yaml", `entry_surface \`${config.entry_surface}\` is not a known surface id (VR-ENTRY)`);
}

// VR-PREFIX-TYPE: a surface's id prefix (leading uppercase letters) must match
// config.surface_id_prefixes[type] when that mapping exists. Skip types without a mapping.
const prefixTypeMap = config.surface_id_prefixes ?? {};
for (const [sid, stype] of surfaceTypeById) {
  const expectedPrefix = prefixTypeMap[stype];
  if (!expectedPrefix) continue; // no mapping for this type (e.g. rules, system_events) — skip
  const actualPrefix = sid.match(/^[A-Z]+/)?.[0] ?? "";
  if (actualPrefix !== expectedPrefix) {
    warn(surfaceFileById.get(sid) ?? sid, `surface \`${sid}\` has type=${stype} (expected id prefix \`${expectedPrefix}\`) but id prefix is \`${actualPrefix}\` (VR-PREFIX-TYPE)`);
  }
}

// VR-ID-UNIQUE: action IDs must be globally unique
for (const it of allInteractions) {
  if (!it.id) continue;
  if (actionIndex.has(it.id)) {
    err(it.file, `duplicate action id \`${it.id}\` (also in ${actionIndex.get(it.id)})`);
  } else {
    actionIndex.set(it.id, it.file);
  }
}

// VR-ELEMENT-UNIQUE: warn if same element name appears >1 time in same surface+region
const elementSeen = new Map(); // `${surfaceId}::${region}::${element}` -> first actionId
for (const it of allInteractions) {
  if (!it.element || !it.surfaceId) continue;
  const key = `${it.surfaceId}::${it.region ?? ""}::${it.element}`;
  if (elementSeen.has(key)) {
    warn(it.file, `element \`${it.element}\` in ${it.surfaceId}${it.region ? "/" + it.region : ""} appears in multiple interactions (action ${it.id ?? "?"}); first seen at ${elementSeen.get(key)}`);
  } else {
    elementSeen.set(key, it.id ?? "?");
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

// VR-MODAL-EXIT: modals must have a valid exit action + return_to_invoker target
const modalIds = [...knownSurfaceIds].filter((s) => {
  const f = files.find((f) => f.meta?.id === s);
  return f?.meta?.type === "modal";
});
for (const mid of modalIds) {
  const acts = allInteractions.filter((i) => i.surfaceId === mid);
  const modalFile = surfaceFileById.get(mid) ?? mid; // use file path for attribution, not bare surface id
  const hasExit = acts.some((a) => a.action === "close_overlay" || a.action === "submit");
  if (!hasExit) {
    err(modalFile, `modal ${mid} has no close_overlay or submit exit action (VR-MODAL-EXIT-001)`);
  }
  if (!acts.some((a) => a.target === "return_to_invoker")) {
    warn(modalFile, `modal ${mid} has no return_to_invoker exit (VR-MODAL-EXIT-002)`);
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

// VR-REGION-PARENT: if regions[] contains a dotted path (e.g. sidebar.core_info),
// warn if the parent segment (e.g. sidebar) is not also declared in regions[].
for (const [surfaceId, regions] of surfaceRegions) {
  for (const r of regions) {
    const dotIdx = r.indexOf(".");
    if (dotIdx === -1) continue;
    const parent = r.slice(0, dotIdx);
    if (!regions.includes(parent)) {
      warn(surfaceId, `region \`${r}\` declared but parent segment \`${parent}\` not in regions[] (add it for layout reference)`);
    }
  }
}

// VR-LAYOUT-*: validate ui-layout fence when present in a surface file.
// Three rules:
//   VR-LAYOUT-UNKNOWN (error) — area/floating/samples region name not in frontmatter regions[]
//   VR-LAYOUT-RECT    (error) — region cells in areas matrix don't form a solid rectangle
//   VR-LAYOUT-ORPHAN  (warn)  — declared region absent from all layout areas + floating + variants + children
for (const f of files) {
  if (!f.meta?.id) continue;
  let raw;
  try { raw = readFileSync(join(SPEC_ROOT, f.file), "utf8"); } catch { continue; }

  // VR-LAYOUT-PARSE (error): fence present but YAML broken / no valid areas.
  // extractLayout() returns null for BOTH "no fence" and "broken fence" — checking
  // layoutFenceInfo first prevents malformed content: YAML from silently skipping
  // every layout rule and leaving stale ASCII in place (batch-2 agent found this).
  const fenceInfo = layoutFenceInfo(raw);
  if (fenceInfo.hasFence && fenceInfo.parseError) {
    err(f.file, `ui-layout fence present but unusable: ${fenceInfo.parseError} (VR-LAYOUT-PARSE)`);
    continue;
  }
  const layout = extractLayout(raw);
  if (!layout) continue; // no fence on this surface — skip all layout rules

  const sid = f.meta.id;
  const declaredRegions = surfaceRegions.get(sid) || [];
  const areaNames = layoutAreaNames(layout); // Set<string> incl. floating + variants + children

  // VR-LAYOUT-UNKNOWN: every name used in layout must be declared in frontmatter regions[].
  // Checks: areas matrix (via areaNames), floating regions (included in areaNames), samples keys.
  const allLayoutNames = new Set(areaNames);
  for (const sampleKey of Object.keys(layout.samples || {})) allLayoutNames.add(sampleKey);
  for (const contentKey of Object.keys(layout.content || {})) allLayoutNames.add(contentKey);
  for (const name of allLayoutNames) {
    if (!declaredRegions.includes(name)) {
      err(f.file, `ui-layout region \`${name}\` not in frontmatter regions[] (VR-LAYOUT-UNKNOWN)`);
    }
  }

  // VR-LAYOUT-ROWS: row_heights must have one track per base areas row.
  if (Array.isArray(layout.row_heights) && layout.row_heights.length !== (layout.areas || []).length) {
    warn(f.file, `ui-layout row_heights has ${layout.row_heights.length} track(s) but areas has ${(layout.areas || []).length} row(s) (VR-LAYOUT-ROWS)`);
  }

  // VR-LAYOUT-RECT: each region in the areas matrix must form a solid rectangle.
  for (const bad of nonRectRegions(layout)) {
    err(f.file, `ui-layout region \`${bad}\` does not form a solid rectangle in areas matrix (VR-LAYOUT-RECT)`);
  }

  // VR-LAYOUT-ORPHAN: warn when a declared region doesn't appear anywhere in the layout.
  // areaNames already includes floating + variant rows + children names.
  for (const r of declaredRegions) {
    if (!areaNames.has(r)) {
      warn(f.file, `region \`${r}\` declared in frontmatter but absent from ui-layout areas+floating+variants (VR-LAYOUT-ORPHAN)`);
    }
  }

  // VR-ASCII-DRIFT: the ASCII between ui-layout:ascii markers must equal what the
  // model generates. Reuses the exact build path (generateAscii + injectAscii): if
  // re-injecting produces a different file, either someone hand-edited the generated
  // block (their edit will be silently overwritten on next build) or the model
  // changed without rebuilding. Layout is the YAML fence; ASCII is derived output.
  try {
    if (injectAscii(raw, generateAscii(layout)) !== raw) {
      warn(f.file, "generated ASCII out of sync with ui-layout model — edit the YAML fence, not the ASCII, then run build (VR-ASCII-DRIFT)");
    }
  } catch { /* generation errors already surface via build */ }
}

// VR-SHOW-PANEL: show_panel target must be a known surface with type=panel
for (const it of allInteractions) {
  if (it.action !== "show_panel") continue;
  const t = String(it.target ?? "");
  if (!knownSurfaceIds.has(t)) {
    err(it.file, `show_panel target \`${t}\` (action ${it.id ?? "?"}) is not a known surface`);
  } else if (surfaceTypeById.get(t) !== "panel") {
    err(it.file, `show_panel target \`${t}\` (action ${it.id ?? "?"}) must be type=panel`);
  }
}

// VR-COMPONENT-NAV: components should only emit_event; navigate/open_overlay allowed only for
// "genuinely self-contained controls" (CONVENTION §7). Warn (not error) to allow documented exceptions.
for (const it of allInteractions) {
  if (it.type !== "component") continue;
  if (it.action !== "navigate" && it.action !== "open_overlay") continue;
  warn(it.file, `component \`${it.surfaceId}\` uses \`${it.action}\` — components should emit_event and let the host navigate; \`navigate\`/\`open_overlay\` allowed only for self-contained controls (CONVENTION §7, VR-COMPONENT-NAV)`);
}

// VR-EFFECT-SURFACE: effect tokens starting with a surface-like prefix must reference known surfaces
const EFFECT_SURFACE_RE = /^([A-Z]{1,2}\d+)\./;
for (const it of allInteractions) {
  for (const eff of it.effects ?? []) {
    const m = String(eff).match(EFFECT_SURFACE_RE);
    if (m && !knownSurfaceIds.has(m[1])) {
      warn(it.file, `effect \`${eff}\` (action ${it.id ?? "?"}) references unknown surface \`${m[1]}\``);
    }
  }
}

// VR-HOSTED-BY: hosted_by[] entries must reference known surfaces
for (const f of files) {
  if (!Array.isArray(f.meta?.hosted_by)) continue;
  for (const h of f.meta.hosted_by) {
    if (!knownSurfaceIds.has(h)) {
      err(f.file, `hosted_by[] references \`${h}\` — not a known surface`);
    }
  }
}

// VR-HOSTS-BIDIR: if X.hosted_by lists Y, then Y.hosts must include X.
// Scope: panels only. Screens curate `hosts:` as their permanently-embedded panels;
// component placement is tracked one-way via the component's own `hosted_by`.
// Modals/overlays/flows are opened via open_overlay, not hosted.
const hostsByFile  = new Map(); // surfaceId -> hosts[]
const hostedByFile = new Map(); // surfaceId -> hosted_by[]
const fileById     = new Map(); // surfaceId -> file path (for warn attribution)
for (const f of files) {
  if (!f.meta?.id) continue;
  fileById.set(f.meta.id, f.file);
  if (Array.isArray(f.meta.hosts))     hostsByFile.set(f.meta.id, f.meta.hosts);
  if (Array.isArray(f.meta.hosted_by)) hostedByFile.set(f.meta.id, f.meta.hosted_by);
}
for (const [childId, parents] of hostedByFile) {
  if (surfaceTypeById.get(childId) !== "panel") continue;
  for (const parentId of parents) {
    const parentHosts = hostsByFile.get(parentId) ?? [];
    if (!parentHosts.includes(childId)) {
      warn(fileById.get(childId) ?? childId, `bidirectional hosting gap: ${childId}.hosted_by lists ${parentId} but ${parentId}.hosts does not include ${childId} (VR-HOSTS-BIDIR)`);
    }
  }
}
// VR-HOSTS-BIDIR (reverse): if a screen's hosts[] includes a panel Pxx,
// then Pxx.hosted_by must also list that screen (panel side must acknowledge host).
for (const [parentId, hostedList] of hostsByFile) {
  for (const childId of hostedList) {
    if (surfaceTypeById.get(childId) !== "panel") continue;
    const childHostedBy = hostedByFile.get(childId) ?? [];
    if (!childHostedBy.includes(parentId)) {
      warn(fileById.get(parentId) ?? parentId, `bidirectional hosting gap: ${parentId}.hosts includes ${childId} but ${childId}.hosted_by does not include ${parentId} (VR-HOSTS-BIDIR)`);
    }
  }
}

// VR-PAYLOAD-GRAMMAR: payload tokens should follow $entity.field or $event.field convention.
// Exception: component emits may use bare $<prop> tokens — inside a component the data context
// is its own props, not a domain entity, so bare prop references are the documented pattern.
// Regex covers lowercase, camelCase, and tokens with digits (e.g. $partyId, $party2).
const BARE_TOKEN_RE = /"\$([A-Za-z_][A-Za-z0-9_]*)"/g;
for (const it of allInteractions) {
  if (!it.payload) continue;
  if (it.type === "component" && it.action === "emit_event") continue; // bare prop tokens are legitimate here
  const payloadStr = JSON.stringify(it.payload);
  for (const m of payloadStr.matchAll(BARE_TOKEN_RE)) {
    warn(it.file, `payload token \`$${m[1]}\` (action ${it.id ?? "?"}) is a bare variable — prefer $entity.field or $event.field (VR-PAYLOAD-GRAMMAR)`);
  }
}

// VR-EMIT-LISTEN: emitted event has no listener (informational warning)
for (const ev of emittedEvents) {
  if (!listenedEvents.has(ev)) warn("graph", `emitted event \`${ev}\` has no listener (listens_to)`);
}

// VR-HOSTS: frontmatter hosts[] must reference known surfaces (a screen's embedded panels)
// VR-HOSTS-TYPE: each hosts[] entry must be type=panel — screens may only embed panels (CONVENTION §11)
for (const f of files) {
  if (!Array.isArray(f.meta?.hosts)) continue;
  for (const h of f.meta.hosts) {
    if (!knownSurfaceIds.has(h)) {
      err(f.file, `hosts[] references \`${h}\` — not a known surface (typo or missing screen)`);
    } else if (surfaceTypeById.get(h) !== "panel") {
      err(f.file, `hosts[] entry \`${h}\` is type=${surfaceTypeById.get(h)}, not panel — screens may only host panels (CONVENTION §11, VR-HOSTS-TYPE)`);
    }
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

// VR-STATE / VR-ERR: prose state and error references must exist in the 30-states-and-errors.md
// catalog. `### ST-*` headings are the state registry (VR-STATE); `### ERR-*` headings are the
// error registry (VR-ERR). Both are documentation-level → warn, not error. Catalog + references
// both live in prose; scan raw markdown on both ends.
// The catalog file sits at the spec root (not in extractAll's list) — read it directly by name.
// Both catalogs share one file read — do not read the file twice.
const stateCatalog = new Set();
const errCatalog   = new Set();
try {
  const catalogName = readdirSync(SPEC_ROOT).find((n) => /states/i.test(n) && n.endsWith(".md"));
  if (catalogName) {
    const raw = readFileSync(join(SPEC_ROOT, catalogName), "utf8");
    for (const mm of raw.matchAll(/^#{2,4}\s+(ST-[A-Za-z0-9-]+)/gm))  stateCatalog.add(mm[1]);
    for (const mm of raw.matchAll(/^#{2,4}\s+(ERR-[A-Za-z0-9-]+)/gm)) errCatalog.add(mm[1]);
  }
} catch { /* catalog unreadable — skip state/error checks */ }
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
      warn(f.file, `references state \`${id}\` not defined in 30-states-and-errors.md catalog (typo or missing state) (VR-STATE)`);
    }
  }
}
if (errCatalog.size) {
  for (const f of files) {
    if (!f.meta?.id || f.meta.id === "states-errors") continue;
    let raw;
    try { raw = readFileSync(join(SPEC_ROOT, f.file), "utf8"); } catch { continue; }
    const flagged = new Set();
    for (const mm of raw.matchAll(/\bERR-[A-Za-z0-9-]+/g)) {
      const id = mm[0];
      if (errCatalog.has(id) || flagged.has(id)) continue;
      flagged.add(id);
      warn(f.file, `references error \`${id}\` not defined in 30-states-and-errors.md catalog (typo or missing error) (VR-ERR)`);
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
    // Only rows whose ID prefix is a configured surface prefix are surface-index rows —
    // other tables in the overview (e.g. domain rules R1..R14) share the |ID|Name| shape.
    const surfacePrefixes = new Set(Object.values(config.surface_id_prefixes ?? {}));
    for (const mm of raw.matchAll(/^\|\s*([A-Z]{1,2}\d+)\s*\|\s*([^|]+?)\s*\|/gm)) {
      const id = mm[1], name = mm[2].trim();
      if (surfacePrefixes.size && !surfacePrefixes.has(id.match(/^[A-Z]{1,2}/)[0])) continue;
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

// VR-ELEMENT-REF: every layout.elements value must be an existing action id (warn-level).
// Prevents chip→action mappings pointing at typo'd or deleted interaction ids.
for (const f of files) {
  if (!f.meta?.id) continue;
  let raw;
  try { raw = readFileSync(join(SPEC_ROOT, f.file), "utf8"); } catch { continue; }
  let layout;
  try { layout = extractLayout(raw); } catch { continue; }
  if (!layout) continue;
  for (const [chipText, actionId] of Object.entries(layout.elements || {})) {
    if (!actionIndex.has(String(actionId))) {
      warn(f.file, `layout.elements["${chipText}"] references unknown action id \`${actionId}\` (VR-ELEMENT-REF)`);
    }
  }

  // VR-CONTENT-TYPE: every content element must use a known primitive type.
  // VR-CONTENT-ACTION: every content element action: must be an existing action id.
  if (layout.content && typeof layout.content === "object") {
    walkContent(layout.content, ({ region, el, type }) => {
      if (type === null) {
        warn(f.file, `layout.content.${region} has an element with no known primitive type (keys: ${el && typeof el === "object" ? Object.keys(el).join(",") : typeof el}) (VR-CONTENT-TYPE)`);
      }
    });
    for (const ref of contentActionRefs(layout.content)) {
      if (!actionIndex.has(ref.actionId)) {
        warn(f.file, `layout.content.${ref.region} ${ref.type} "${ref.label}" references unknown action id \`${ref.actionId}\` (VR-CONTENT-ACTION)`);
      }
    }
  }
}

// VR-WIREFRAME-STALE: warn if generated/wireframe-v2.html is older than any spec .md file.
// Informs the developer to re-run build without blocking the validation gate.
const wireframePath = join(SPEC_ROOT, "generated", "wireframe-v2.html");
if (existsSync(wireframePath)) {
  const wireframeMtime = statSync(wireframePath).mtimeMs;
  let newerCount = 0;
  for (const dir of surfaceDirs) {
    const absDir = join(SPEC_ROOT, dir);
    let entries = [];
    try { entries = readdirSync(absDir); } catch { continue; }
    for (const entry of entries) {
      if (!entry.endsWith(".md")) continue;
      try {
        if (statSync(join(absDir, entry)).mtimeMs > wireframeMtime) newerCount++;
      } catch { /* skip unreadable */ }
    }
  }
  if (newerCount > 0) {
    warn("wireframe", `wireframe-v2.html is older than ${newerCount} spec file(s) — run build to regenerate`);
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
