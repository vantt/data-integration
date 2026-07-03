// interpret-wireframe.mjs — ui-spec wireframe interpreter v2 (region-box layout).
// NEW tool — does NOT modify interpret.mjs (that file is untouched).
//
// Usage:
//   node interpret-wireframe.mjs [--root <spec-root>] [--no-open]
//   npm run interpret:wf
//
// Output: generated/wireframe-v2.html (separate from interpret.mjs's wireframe.html)
//
// Exports: generateWireframe(rootDir, { open? }) — reusable from build.mjs and other tools.
// The --no-open flag suppresses browser launch (useful in CI / build pipeline).

import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, sep, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { exec } from "node:child_process";
import { specRoot, contractTag } from "./config.mjs";
import { extractAll } from "./extract.mjs";
import { extractProse, findAsciiBlock } from "./wireframe/extract-prose.mjs";
import { normalizeAsciiBlock } from "./wireframe/ascii-normalize.mjs";
import { extractStates, readErrCatalog } from "./wireframe/extract-states.mjs";
import { extractLayout } from "./wireframe/extract-layout.mjs";
import { buildHtml } from "./wireframe/html-shell.mjs";

// ─── Build surface data ───────────────────────────────────────────────────────

/**
 * Read all spec surfaces via extractAll(), attach prose + ASCII block + states.
 * Returns { surfaces, errCatalog }.
 * Note: item.file uses '/' separators (from extract.mjs relative()). We normalise to
 * platform sep for readFileSync — without the require_sep() join quirk in interpret.mjs.
 */
function buildSurfaceData() {
  // Read ERR-* catalog once — used for tooltip enrichment in the States subtab.
  const errCatalog = readErrCatalog(specRoot);

  const surfaces = [];
  for (const item of extractAll()) {
    // Normalise '/' → platform sep for Windows readFileSync
    const rawPath = join(specRoot, item.file.replace(/\//g, sep));
    let prose = "";
    let asciiLayout = null;
    let states = [];
    let layout = null;
    try {
      const raw = readFileSync(rawPath, "utf8");
      prose = extractProse(raw, contractTag);
      const raw_ascii = findAsciiBlock(prose);
      asciiLayout = raw_ascii ? normalizeAsciiBlock(raw_ascii) : null;
      ({ states } = extractStates(prose));
      try { layout = extractLayout(raw); } catch { /* ignore parse failures */ }
    } catch {
      /* file unreadable — prose stays empty, asciiLayout stays null, states stays [] */
    }

    surfaces.push({
      file: item.file,
      id: item.id,
      meta: item.meta,
      contract: item.contract,
      prose,
      asciiLayout,
      layout,
      states,
      errors: item.errors,
    });
  }
  return { surfaces, errCatalog };
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

// ─── Core generation function (exported for reuse by build.mjs etc.) ─────────

/**
 * Generate generated/wireframe-v2.html from the spec at rootDir.
 * rootDir must match specRoot already loaded by config.mjs (same --root CLI arg).
 * @param {string} rootDir - absolute path to spec root
 * @param {{ open?: boolean }} opts - open: true opens browser after writing (default true)
 */
export function generateWireframe(rootDir, { open = true } = {}) {
  console.log(`ui-spec wireframe v2 — reading spec from: ${rootDir}`);

  const { surfaces, errCatalog } = buildSurfaceData();
  console.log(`  Found ${surfaces.length} surface(s)`);

  const genDir = join(rootDir, "generated");
  if (!existsSync(genDir)) mkdirSync(genDir, { recursive: true });

  const outPath = join(genDir, "wireframe-v2.html");
  const html = buildHtml(surfaces, { errCatalog });
  writeFileSync(outPath, html, "utf8");

  console.log(`  Wireframe v2 written: ${outPath}`);
  if (open) {
    console.log("  Opening in browser...");
    openBrowser(outPath);
  }
}

// ─── CLI entry point ──────────────────────────────────────────────────────────

// Detect if this module is the direct entry point (not imported by another module).
// When imported by build.mjs, isMain = false → CLI block is skipped.
const isMain =
  Boolean(process.argv[1]) &&
  fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (isMain) {
  // --no-open suppresses automatic browser launch (used in CI / build pipeline)
  const open = !process.argv.includes("--no-open");
  generateWireframe(specRoot, { open });
}
