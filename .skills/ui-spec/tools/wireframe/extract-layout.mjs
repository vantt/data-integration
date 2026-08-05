// wireframe/extract-layout.mjs — parse ```yaml ui-layout fence from surface markdown.
// Returns layout model object or null if fence absent / unparseable.
//
// Exported API:
//   extractLayout(rawMarkdown) → model | null
//   layoutAreaNames(model) → Set<string>  (areas + variant rows + floating + children)
//   nonRectRegions(model)  → string[]     (regions whose cells don't form a solid rectangle in areas matrix)

import yaml from "js-yaml";
import { LAYOUT_KEYS } from "./layout-schema.mjs";

/** Known top-level keys (single writer: layout-schema.mjs) — anything else is a parse warning. */
const KNOWN_KEYS = new Set(LAYOUT_KEYS);

// Fence regex: handles CRLF (\r?\n) and optional leading spaces (up to 3, per CommonMark).
// Info string must be exactly "yaml ui-layout" (any trailing whitespace allowed).
const FENCE_RE = /^ {0,3}```yaml\s+ui-layout\s*\r?\n([\s\S]*?)^ {0,3}```/m;

/**
 * Parse a ```yaml ui-layout fence from raw markdown.
 * Returns the layout model or null when the fence is absent or unparseable.
 * Unknown top-level keys are collected into model._warnings[].
 */
export function extractLayout(rawMarkdown) {
  const m = rawMarkdown.match(FENCE_RE);
  if (!m) return null;
  try {
    const model = yaml.load(m[1]);
    if (!model || typeof model !== "object" || !Array.isArray(model.areas)) return null;
    // Collect unknown keys as parse warnings — don't crash, just annotate.
    const unknownKeys = Object.keys(model).filter((k) => !KNOWN_KEYS.has(k));
    if (unknownKeys.length) {
      model._warnings = unknownKeys.map((k) => `unknown top-level key: ${k}`);
    }
    return model;
  } catch {
    // YAML parse error — caller decides whether to warn.
    return null;
  }
}

/**
 * Distinguish "no fence" from "fence present but broken" — extractLayout() returns
 * null for BOTH, which let malformed YAML silently skip validate/build (stale ASCII,
 * no warning). Callers that gate on correctness must check this first.
 * @param {string} rawMarkdown
 * @returns {{hasFence: boolean, parseError: string|null}}
 *   parseError also set when YAML parses but `areas` is missing/invalid (unusable model).
 */
export function layoutFenceInfo(rawMarkdown) {
  const m = rawMarkdown.match(FENCE_RE);
  if (!m) return { hasFence: false, parseError: null };
  try {
    const model = yaml.load(m[1]);
    if (!model || typeof model !== "object" || !Array.isArray(model.areas)) {
      return { hasFence: true, parseError: "fence parsed but has no valid `areas` matrix" };
    }
    return { hasFence: true, parseError: null };
  } catch (e) {
    return { hasFence: true, parseError: e.message ? e.message.split("\n")[0] : "YAML parse error" };
  }
}

/**
 * Collect all unique region names from:
 *   - model.areas matrix (base rows)
 *   - model.variants[*].prepend_rows + append_rows
 *   - model.floating[*].region
 *   - model.children (1-level nested layouts: their areas + variant rows)
 *
 * Returns a Set<string>.
 */
export function layoutAreaNames(model) {
  const names = new Set();

  // Helper: add all cells from a matrix of rows.
  function addRows(rows) {
    for (const row of rows || []) {
      for (const cell of row || []) {
        if (cell != null) names.add(String(cell));
      }
    }
  }

  // 1. Base areas matrix.
  addRows(model.areas);

  // 2. Variant rows (prepend + append).
  for (const v of Object.values(model.variants || {})) {
    addRows(v.prepend_rows);
    addRows(v.append_rows);
  }

  // 3. Floating region names.
  for (const f of model.floating || []) {
    if (f && f.region != null) names.add(String(f.region));
  }

  // 4. Children (1-level, per spec) — their areas + variant rows.
  for (const child of Object.values(model.children || {})) {
    if (!child || typeof child !== "object") continue;
    addRows(child.areas);
    for (const v of Object.values(child.variants || {})) {
      addRows(v.prepend_rows);
      addRows(v.append_rows);
    }
  }

  return names;
}

/**
 * Find regions in model.areas whose cells do not form a solid rectangle.
 * Only the base areas matrix is checked — variant rows and floating are excluded
 * (they are not area-cells and have no rectangle requirement).
 *
 * Returns an array of offending region names (empty when all regions are valid rectangles).
 */
export function nonRectRegions(model) {
  const areas = model.areas || [];
  const cellMap = new Map(); // name -> [[r, c], ...]

  for (let r = 0; r < areas.length; r++) {
    const row = areas[r] || [];
    for (let c = 0; c < row.length; c++) {
      const cell = row[c];
      if (cell == null) continue;
      const name = String(cell);
      if (!cellMap.has(name)) cellMap.set(name, []);
      cellMap.get(name).push([r, c]);
    }
  }

  const offending = [];
  for (const [name, cells] of cellMap) {
    if (!cells.length) continue;
    const minR = Math.min(...cells.map(([r]) => r));
    const maxR = Math.max(...cells.map(([r]) => r));
    const minC = Math.min(...cells.map(([, c]) => c));
    const maxC = Math.max(...cells.map(([, c]) => c));
    const expected = (maxR - minR + 1) * (maxC - minC + 1);
    if (cells.length !== expected) offending.push(name);
  }

  return offending;
}
