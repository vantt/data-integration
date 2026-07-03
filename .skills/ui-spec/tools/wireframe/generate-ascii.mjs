// wireframe/generate-ascii.mjs
// Deterministic ASCII generator from ui-layout model.
// Exports: generateAscii(model, opts?), injectAscii(markdown, asciiBlock)
// CLI: node .skills/ui-spec/tools/wireframe/generate-ascii.mjs --root <spec-root> [--surface SXX]

import { readFileSync, writeFileSync } from "node:fs";
import { basename } from "node:path";
import { displayWidth } from "./ascii-normalize.mjs";
import { extractLayout } from "./extract-layout.mjs";

// ─── Text normalization ────────────────────────────────────────────────────────
// Same substitution table as ascii-normalize.mjs — MUST stay in sync.
// NOTE: regex uses "gu" flag so supplementary-plane emoji (> U+FFFF) match as
// full code points, not surrogate halves.
const GLYPH_MAP = {
  // Geometric / block shapes (already present)
  "▶": ">", "◀": "<", "▲": "^", "▼": "v", "■": "#", "●": "o",
  // Status / misc symbols (already present)
  "⚠": "!", "☁": "*", "✓": "v", "✕": "x", "✗": "x", "★": "*", "☆": "*", "ⓘ": "i",
  // Small triangles (appear in S14 objection list and secondary reasons)
  "▸": ">", "▾": "v",
  // Communication glyphs (S14 identity_bar, talk_track)
  "☎": "T:", "📞": ">", "💬": "~", "✉": "@",
  // Checkboxes (S14 talking_points, reason_to_call)
  "☑": "[x]", "☐": "[ ]", "✅": "[x]", "❌": "x",
  // Action / search (S14 objection_handling, stop_banner, guardrails)
  "🔍": "(?)", "⛔": "!!",
  // Commerce / clipboard / data
  "🛒": "$", "📋": "#", "📊": "#", "🔗": "&",
  // Time (S14 strategy_summary, reason_to_call, outcome_bar)
  "⏱": "(t)", "⏳": "(t)",
};
const GLYPH_RE = new RegExp("[" + Object.keys(GLYPH_MAP).join("") + "]", "gu");

/**
 * Apply glyph substitution (same table as ascii-normalize.mjs) then replace any
 * remaining display-width-2 chars with "?" so output is alignment-safe in any
 * monospace viewer. After this call every character is exactly 1 display column.
 */
function normalizeText(text) {
  if (!text) return "";
  text = text.replace(GLYPH_RE, (ch) => GLYPH_MAP[ch] ?? ch);
  // Replace wide chars (same ranges as displayWidth in ascii-normalize.mjs) with "?".
  let out = "";
  for (const ch of text) {
    const cp = ch.codePointAt(0);
    if (
      (cp >= 0x1100  && cp <= 0x115F)  || (cp >= 0x2E80  && cp <= 0x303E)  ||
      (cp >= 0x3041  && cp <= 0x33FF)  || (cp >= 0x3400  && cp <= 0x4DBF)  ||
      (cp >= 0x4E00  && cp <= 0x9FFF)  || (cp >= 0xA000  && cp <= 0xA4CF)  ||
      (cp >= 0xAC00  && cp <= 0xD7A3)  || (cp >= 0xF900  && cp <= 0xFAFF)  ||
      (cp >= 0xFE30  && cp <= 0xFE4F)  || (cp >= 0xFF00  && cp <= 0xFF60)  ||
      (cp >= 0xFFE0  && cp <= 0xFFE6)  || (cp >= 0x1F000 && cp <= 0x1FAFF) ||
      (cp >= 0x2600  && cp <= 0x27BF)  || (cp >= 0x2B00  && cp <= 0x2BFF)  ||
      (cp >= 0x25A0  && cp <= 0x25FF)
    ) {
      out += "?";
    } else {
      out += ch;
    }
  }
  return out;
}

// ─── Column geometry ───────────────────────────────────────────────────────────

/**
 * Compute column inner char-widths from fr spec array.
 * total = 78 (default). Accounts for 2 outer borders + (M-1) separators.
 * Last column absorbs rounding remainder → output is deterministic.
 * @param {string[]} columns  e.g. ["3fr","2fr"]
 * @param {number}   total
 * @returns {number[]}
 */
export function computeColWidths(columns, total = 78) {
  const frs = (columns || []).map((c) => parseFloat(c) || 1);
  const M = frs.length || 1;
  const sum = frs.reduce((a, b) => a + b, 0);
  const inner = total - 2 - (M - 1); // available inner chars
  const widths = frs.map((fr) => Math.floor((fr / sum) * inner));
  const allocated = widths.slice(0, -1).reduce((a, b) => a + b, 0);
  widths[M - 1] = inner - allocated; // last col absorbs remainder
  return widths;
}

/**
 * Character position of the left-border │ for each column.
 * colLeft[c] = c + Σ(widths[0..c-1])  — c separators + cumulative inner widths.
 */
function computeColLeftBorders(colW) {
  const borders = [];
  let pos = 0;
  for (const w of colW) {
    borders.push(pos);
    pos += 1 + w; // skip border + inner width
  }
  return borders;
}

// ─── Region bounding boxes ─────────────────────────────────────────────────────

/**
 * Bounding box {minR,maxR,minC,maxC} for each unique region name in areas matrix.
 * @param {string[][]} areas
 * @returns {Map<string, {minR,maxR,minC,maxC}>}
 */
function computeRegionBounds(areas) {
  const bounds = new Map();
  for (let r = 0; r < (areas || []).length; r++) {
    for (let c = 0; c < (areas[r] || []).length; c++) {
      if (areas[r][c] == null) continue;
      const key = String(areas[r][c]);
      if (!bounds.has(key)) {
        bounds.set(key, { minR: r, maxR: r, minC: c, maxC: c });
      } else {
        const b = bounds.get(key);
        if (r < b.minR) b.minR = r;
        if (r > b.maxR) b.maxR = r;
        if (c < b.minC) b.minC = c;
        if (c > b.maxC) b.maxC = c;
      }
    }
  }
  return bounds;
}

// ─── Box-drawing helpers ───────────────────────────────────────────────────────

/**
 * Box-drawing junction character based on which of the 4 directions have a line.
 * Bit encoding: bit0=Left, bit1=Right, bit2=Up, bit3=Down.
 */
function junctionChar(L, R, U, D) {
  const k = (L ? 1 : 0) | (R ? 2 : 0) | (U ? 4 : 0) | (D ? 8 : 0);
  // prettier-ignore
  const T = [
    " ", "─", "─", "─",   //  0  1  2  3  (no up/down)
    "│", "┘", "└", "┴",   //  4  5  6  7
    "│", "┐", "┌", "┬",   //  8  9 10 11
    "│", "┤", "├", "┼",   // 12 13 14 15
  ];
  return T[k] ?? "┼";
}

/**
 * Truncate str to maxW characters (after normalizeText all chars are 1-wide,
 * so length == display-width). Appends "…" if truncated.
 */
function truncate(str, maxW) {
  if (!str || maxW <= 0) return "";
  if (str.length <= maxW) return str;
  return str.slice(0, maxW - 1) + "…";
}

// ─── Core renderer ────────────────────────────────────────────────────────────

/**
 * Render an areas matrix to a character matrix (array of strings), each row exactly
 * `total` characters wide. Uses 3 pixel-rows per grid row: border / name / sample.
 *
 * @param {string[][]} areas
 * @param {number[]}   colW      inner column widths
 * @param {number[]}   colLeft   left-border char positions
 * @param {Map}        bounds    region → {minR,maxR,minC,maxC}
 * @param {object}     samples   region → raw sample text
 * @param {number}     total     row width (78)
 * @returns {string}
 */
function renderAreas(areas, colW, colLeft, bounds, samples, total) {
  const N = (areas || []).length;
  const M = colW.length;
  if (N === 0 || M === 0) return "";

  const rightOuter = total - 1;
  // H = 3 pixel-rows per grid row + 1 final border row
  const H = 3 * N + 1;
  // Character matrix: H rows × total cols, initialised to spaces.
  const mat = Array.from({ length: H }, () => new Array(total).fill(" "));

  // Helper: read a cell, coercing to string (null → "")
  const cell = (r, c) => String((areas[r] || [])[c] ?? "");

  // ── Pass 1: Horizontal border rows (3*r for r = 0..N) ─────────────────────
  for (let r = 0; r <= N; r++) {
    const px = 3 * r;

    // For each column segment: is there a horizontal line here?
    const hasH = colW.map((_, c) =>
      r === 0 || r === N ? true : cell(r - 1, c) !== cell(r, c)
    );

    // Fill inner segments with "─" where hasH is true
    for (let c = 0; c < M; c++) {
      if (hasH[c]) {
        const iStart = colLeft[c] + 1;
        const iEnd   = colLeft[c] + colW[c];
        for (let x = iStart; x <= iEnd; x++) mat[px][x] = "─";
      }
    }

    // Left outer border
    mat[px][0] = junctionChar(false, hasH[0], r > 0, r < N);

    // Right outer border
    mat[px][rightOuter] = junctionChar(hasH[M - 1], false, r > 0, r < N);

    // Inner column separators
    for (let c = 1; c < M; c++) {
      const sepPos = colLeft[c];
      const vUp = r > 0 && cell(r - 1, c - 1) !== cell(r - 1, c);
      const vDn = r < N && cell(r,     c - 1) !== cell(r,     c);
      mat[px][sepPos] = junctionChar(hasH[c - 1], hasH[c], vUp, vDn);
    }
  }

  // ── Pass 2: Content rows — vertical borders ────────────────────────────────
  for (let r = 0; r < N; r++) {
    for (const pxOffset of [1, 2]) {
      const px = 3 * r + pxOffset;
      mat[px][0]          = "│";
      mat[px][rightOuter] = "│";
      for (let c = 1; c < M; c++) {
        if (cell(r, c - 1) !== cell(r, c)) mat[px][colLeft[c]] = "│";
      }
    }
  }

  // ── Pass 3: Write region content (name + sample) ──────────────────────────
  for (const [name, b] of bounds) {
    const innerLeft  = colLeft[b.minC] + 1;
    const innerRight = colLeft[b.maxC] + colW[b.maxC];
    const innerW     = innerRight - innerLeft + 1;
    if (innerW <= 0) continue;

    const namePx   = 3 * b.minR + 1;
    const samplePx = 3 * b.minR + 2;

    const nameStr = truncate(name.toUpperCase(), innerW);
    for (let i = 0; i < nameStr.length; i++) mat[namePx][innerLeft + i] = nameStr[i];

    const rawSample = samples[name] || "";
    if (rawSample) {
      const normSample  = normalizeText(rawSample);
      const sampleLine  = truncate("· " + normSample, innerW);
      for (let i = 0; i < sampleLine.length; i++) mat[samplePx][innerLeft + i] = sampleLine[i];
    }
  }

  return mat.map((row) => row.join("")).join("\n");
}

// ─── Public API ───────────────────────────────────────────────────────────────

/**
 * Generate box-drawing ASCII from a ui-layout model.
 * Output: base block, then one labelled block per variant, then floating blocks.
 * Deterministic: same model → byte-identical output.
 *
 * @param {object} model  result of extractLayout()
 * @param {object} opts   optional overrides: { total: 78 }
 * @returns {string}      ASCII art (no surrounding ``` fence)
 */
export function generateAscii(model, opts = {}) {
  const total    = opts.total    ?? 78;
  const areas    = model.areas    || [];
  const floating = model.floating || [];
  const variants = model.variants || {};
  const samples  = model.samples  || {};

  // Derive column spec: explicit columns[] or fall back to uniform 1fr per column
  const M       = Math.max(...(areas.map((r) => (r || []).length)), 1);
  const colSpec = (model.columns || []).length ? model.columns : Array(M).fill("1fr");
  const colW    = computeColWidths(colSpec, total);
  const colLeft = computeColLeftBorders(colW);

  // Base block
  const baseBounds = computeRegionBounds(areas);
  const parts      = [renderAreas(areas, colW, colLeft, baseBounds, samples, total)];

  // Variant blocks
  for (const [varName, variant] of Object.entries(variants)) {
    const varAreas  = [...(variant.prepend_rows || []), ...areas, ...(variant.append_rows || [])];
    const varBounds = computeRegionBounds(varAreas);
    const varBlock  = renderAreas(varAreas, colW, colLeft, varBounds, samples, total);
    parts.push(`[variant: ${varName}]\n${varBlock}`);
  }

  // Floating region blocks (each renders as a standalone single-row box)
  const innerW = total - 2;
  for (const f of floating) {
    if (!f || !f.region) continue;
    const rName    = String(f.region);
    const when     = f.when ? String(f.when) : "";
    const rawSamp  = samples[rName] || "";
    const normSamp = rawSamp ? normalizeText(rawSamp) : "";

    const nameStr = truncate(rName.toUpperCase(), innerW).padEnd(innerW);
    const top     = "┌" + "─".repeat(innerW) + "┐";
    const nameLine = "│" + nameStr + "│";
    const bot     = "└" + "─".repeat(innerW) + "┘";

    const lines = [top, nameLine];
    // Print when: condition inside the box as a caption line
    if (when) {
      const whenStr = truncate("when: " + when, innerW).padEnd(innerW);
      lines.push("│" + whenStr + "│");
    }
    if (normSamp) {
      lines.push("│" + truncate("· " + normSamp, innerW).padEnd(innerW) + "│");
    }
    lines.push(bot);

    const label = when ? `[STOP variant — when: ${when}]\n` : "[STOP variant]\n";
    parts.push(label + lines.join("\n"));
  }

  return parts.join("\n\n");
}

/**
 * Inject/replace the generated ASCII block in a surface markdown file.
 * Markers: <!-- ui-layout:ascii:start --> ... <!-- ui-layout:ascii:end -->
 * - If markers exist: replaces content between them (idempotent).
 * - If absent: inserts right after the yaml ui-layout fence.
 * - Fallback: appends at end.
 *
 * @param {string} markdown    raw surface .md content
 * @param {string} asciiBlock  result of generateAscii()
 * @returns {string}           updated markdown
 */
export function injectAscii(markdown, asciiBlock) {
  const START = "<!-- ui-layout:ascii:start -->";
  const END   = "<!-- ui-layout:ascii:end -->";
  const fence = `\`\`\`\n${asciiBlock}\n\`\`\``;
  const block = `${START}\n${fence}\n${END}`;

  // Escape literal strings for use in RegExp
  const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

  // Update existing markers (non-greedy: only the first pair)
  const markerRe = new RegExp(esc(START) + "[\\s\\S]*?" + esc(END));
  if (markerRe.test(markdown)) {
    return markdown.replace(markerRe, block);
  }

  // No markers — insert right after the yaml ui-layout fence
  // (same fence pattern as extract-layout.mjs FENCE_RE)
  const FENCE_RE = /^ {0,3}```yaml\s+ui-layout\s*\r?\n[\s\S]*?^ {0,3}```/m;
  const fm = markdown.match(FENCE_RE);
  if (fm) {
    const at = fm.index + fm[0].length;
    return markdown.slice(0, at) + "\n\n" + block + markdown.slice(at);
  }

  // Fallback: append at end
  return markdown.trimEnd() + "\n\n" + block + "\n";
}

// ─── CLI entry point ──────────────────────────────────────────────────────────
// Usage: node .skills/ui-spec/tools/wireframe/generate-ascii.mjs
//          --root <spec-root> [--surface S14]

const isCLI =
  import.meta.url === `file://${process.argv[1]}` ||
  process.argv[1]?.replace(/\\/g, "/").endsWith("wireframe/generate-ascii.mjs");

if (isCLI) {
  // Dynamic imports so the module can also be imported as a library
  // without requiring config resolution at that point.
  const { listSpecFiles } = await import("../extract.mjs");

  const args          = process.argv.slice(2);
  const surfaceFilter = (() => {
    const idx = args.indexOf("--surface");
    return idx !== -1 ? args[idx + 1] ?? null : null;
  })();

  const specFiles = listSpecFiles();
  let processed = 0, changed = 0, skipped = 0;

  for (const absPath of specFiles) {
    const base = basename(absPath, ".md");
    if (surfaceFilter && !base.startsWith(surfaceFilter)) { skipped++; continue; }

    let raw;
    try { raw = readFileSync(absPath, "utf8"); } catch { skipped++; continue; }

    const layout = extractLayout(raw);
    if (!layout) { skipped++; continue; }

    const ascii   = generateAscii(layout);
    const updated = injectAscii(raw, ascii);
    processed++;

    if (updated !== raw) {
      writeFileSync(absPath, updated, "utf8");
      changed++;
      console.log(`  ascii written: ${base}`);
    }
  }

  const unchanged = processed - changed;
  console.log(
    `\nascii-generator: ${processed} surface(s) with layout — ` +
    `${changed} written, ${unchanged} unchanged, ${skipped} skipped`
  );
}
