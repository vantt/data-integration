// interpret-wireframe.mjs — ui-spec wireframe interpreter v2 (region-box layout).
// NEW tool — does NOT modify interpret.mjs (that file is untouched).
//
// Usage:
//   node interpret-wireframe.mjs [--root <spec-root>]
//   npm run interpret:wf
//
// Output: generated/wireframe-v2.html (separate from interpret.mjs's wireframe.html)

import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, sep } from "node:path";
import { exec } from "node:child_process";
import { specRoot, contractTag } from "./config.mjs";
import { extractAll } from "./extract.mjs";
import { extractProse, findAsciiBlock } from "./wireframe/extract-prose.mjs";
import { normalizeAsciiBlock } from "./wireframe/ascii-normalize.mjs";
import { buildHtml } from "./wireframe/html-shell.mjs";

// ─── Build surface data ───────────────────────────────────────────────────────

/**
 * Read all spec surfaces via extractAll(), attach prose + ASCII block.
 * Returns enriched surface objects: { file, id, meta, contract, prose, asciiLayout, errors }.
 * Note: item.file uses '/' separators (from extract.mjs relative()). We normalise to
 * platform sep for readFileSync — without the require_sep() join quirk in interpret.mjs.
 */
function buildSurfaceData() {
  const surfaces = [];
  for (const item of extractAll()) {
    // Normalise '/' → platform sep for Windows readFileSync
    const rawPath = join(specRoot, item.file.replace(/\//g, sep));
    let prose = "";
    let asciiLayout = null;
    try {
      const raw = readFileSync(rawPath, "utf8");
      prose = extractProse(raw, contractTag);
      const raw_ascii = findAsciiBlock(prose);
      asciiLayout = raw_ascii ? normalizeAsciiBlock(raw_ascii) : null;
    } catch {
      /* file unreadable — prose stays empty, asciiLayout stays null */
    }

    surfaces.push({
      file: item.file,
      id: item.id,
      meta: item.meta,
      contract: item.contract,
      prose,
      asciiLayout,
      errors: item.errors,
    });
  }
  return surfaces;
}

// ─── Open in browser ──────────────────────────────────────────────────────────

/** Open a local file path in the default browser. Mirrors interpret.mjs verbatim. */
function openBrowser(filePath) {
  const normalized = filePath.replace(/\\/g, "/");
  const fileUrl = `file:///${normalized}`;
  const cmd =
    process.platform === "win32" ? `start "" "${fileUrl}"` :
    process.platform === "darwin" ? `open "${fileUrl}"` :
    `xdg-open "${fileUrl}"`;
  exec(cmd, (err) => {
    if (err) console.warn("Could not open browser automatically:", err.message);
  });
}

// ─── Main ─────────────────────────────────────────────────────────────────────

console.log(`ui-spec wireframe v2 — reading spec from: ${specRoot}`);

const surfaces = buildSurfaceData();
console.log(`  Found ${surfaces.length} surface(s)`);

const genDir = join(specRoot, "generated");
if (!existsSync(genDir)) mkdirSync(genDir, { recursive: true });

const outPath = join(genDir, "wireframe-v2.html");
const html = buildHtml(surfaces);
writeFileSync(outPath, html, "utf8");

console.log(`  Wireframe v2 written: ${outPath}`);
console.log("  Opening in browser...");
openBrowser(outPath);
