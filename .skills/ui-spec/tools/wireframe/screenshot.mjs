// wireframe/screenshot.mjs — headless browser screenshot of wireframe-v2.html surfaces.
// Enables the Visual QA loop: run build, screenshot representative surfaces, read the PNGs
// with your vision, judge against the checklist, fix, repeat. See ui-layout-authoring.md §11.
//
// Usage:
//   node tools/wireframe/screenshot.mjs --root <spec-root> --surface S14[,S03,M01]
//                                        [--out-dir <dir>] [--width 1600] [--height 1400]
//
// Output: <out-dir>/<surface-id>.png per surface.
// Default out-dir: <spec-root>/generated/screenshots/
//
// Browser discovery order:
//   1. UISPEC_BROWSER env var (full exe path)
//   2. msedge.exe — standard install locations
//   3. chrome.exe — standard install locations
//   → not found: exits 1 with a list of all paths checked + env hint.

import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import yaml from "js-yaml";

// ─── CLI argument parsing ─────────────────────────────────────────────────────

function parseArgs() {
  const argv = process.argv.slice(2);
  const args = { root: null, surfaces: [], outDir: null, width: 1600, height: 1400 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if      (a === "--root"    && argv[i + 1]) args.root    = resolve(argv[++i]);
    else if (a === "--surface" && argv[i + 1]) args.surfaces = argv[++i].split(",").map(s => s.trim()).filter(Boolean);
    else if (a === "--out-dir" && argv[i + 1]) args.outDir   = resolve(argv[++i]);
    else if (a === "--width"   && argv[i + 1]) args.width    = parseInt(argv[++i], 10);
    else if (a === "--height"  && argv[i + 1]) args.height   = parseInt(argv[++i], 10);
  }
  return args;
}

// ─── Browser discovery ────────────────────────────────────────────────────────

// Resolve %LOCALAPPDATA% once (empty string on non-Windows so join produces a non-existent path).
const LOCAL = process.env.LOCALAPPDATA ?? "";

/** Ordered list of candidate executable paths to probe (msedge first, then chrome). */
const BROWSER_CANDIDATES = [
  // Microsoft Edge
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  join(LOCAL, "Microsoft\\Edge\\Application\\msedge.exe"),
  // Google Chrome
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  join(LOCAL, "Google\\Chrome\\Application\\chrome.exe"),
];

/**
 * Locate a usable Chromium-based browser.
 * Returns { path } on success, { error } on failure.
 */
function discoverBrowser() {
  // Explicit env override — checked first so CI can pin a specific build.
  const envPath = process.env.UISPEC_BROWSER;
  if (envPath) {
    if (existsSync(envPath)) return { path: envPath };
    return {
      error:
        `UISPEC_BROWSER="${envPath}" is set but the file does not exist.\n` +
        `Unset it or point it to a valid msedge.exe / chrome.exe.`,
    };
  }

  // Auto-detect from standard install locations.
  for (const candidate of BROWSER_CANDIDATES) {
    if (existsSync(candidate)) return { path: candidate };
  }

  const checked = BROWSER_CANDIDATES.map(p => `  ${p}`).join("\n");
  return {
    error:
      `No browser found. Paths checked:\n${checked}\n\n` +
      `Set UISPEC_BROWSER=<full path to msedge.exe or chrome.exe> to override.`,
  };
}

// ─── Screenshot one surface ───────────────────────────────────────────────────

/** Minimum acceptable PNG size. Blank page shells render smaller than this. */
const MIN_PNG_BYTES = 20 * 1024; // 20 KB

/**
 * Launch the browser in headless mode to screenshot one surface and write the PNG.
 * @param {string} browserPath - absolute path to msedge/chrome executable
 * @param {string} htmlAbsPath - absolute path to wireframe-v2.html
 * @param {string} sid         - surface id (appended as URL hash)
 * @param {string} outFile     - absolute destination PNG path
 * @param {number} width       - viewport width in px
 * @param {number} height      - viewport height in px
 * @returns {{ ok: boolean, error?: string }}
 */
function screenshotSurface(browserPath, htmlAbsPath, sid, outFile, width, height) {
  // Chromium requires forward slashes in file:/// URLs even on Windows.
  const fileUrl = "file:///" + htmlAbsPath.replace(/\\/g, "/") + "#" + sid;

  const flags = [
    "--headless=new",
    "--disable-gpu",
    `--window-size=${width},${height}`,
    "--virtual-time-budget=8000",   // let page JS run for 8 s of virtual time before capture
    `--screenshot=${outFile}`,
    fileUrl,
  ];

  const result = spawnSync(browserPath, flags, {
    timeout: 30_000,   // 30 s wall-clock hard cap per surface
    encoding: "utf8",
  });

  if (result.error) {
    return { ok: false, error: `process error: ${result.error.message}` };
  }
  if (result.status !== 0) {
    const stderr = (result.stderr ?? "").slice(0, 400);
    return { ok: false, error: `browser exited with code ${result.status}${stderr ? `. stderr: ${stderr}` : ""}` };
  }

  // Verify the file was actually written — browser can exit 0 without creating the file.
  if (!existsSync(outFile)) {
    return { ok: false, error: "browser exited 0 but the PNG was not written to disk" };
  }

  // Guard against blank-shell captures (CSS grid not rendered = tiny file).
  const bytes = statSync(outFile).size;
  if (bytes < MIN_PNG_BYTES) {
    return { ok: false, error: `PNG is only ${bytes} B (< ${MIN_PNG_BYTES} B threshold) — likely a blank page; check the URL hash` };
  }

  return { ok: true };
}

// ─── Main ─────────────────────────────────────────────────────────────────────

const args = parseArgs();

if (!args.root) {
  console.error("ERROR: --root <spec-root> is required");
  process.exit(1);
}
if (args.surfaces.length === 0) {
  console.error("ERROR: --surface <id[,id,...]> is required (e.g. --surface S14,S03,M01)");
  process.exit(1);
}

// Verify wireframe-v2.html exists — must run build.mjs first.
const htmlPath = join(args.root, "generated", "wireframe-v2.html");
if (!existsSync(htmlPath)) {
  console.error(`ERROR: wireframe-v2.html not found at:\n  ${htmlPath}`);
  console.error("  Run build first: node .skills/ui-spec/tools/build.mjs --root <spec-root>");
  process.exit(1);
}

// Validate surface IDs against the built registry so bogus IDs fail with a clear message.
// surface-registry.yaml is generated by build.mjs; it must exist alongside wireframe-v2.html.
const registryPath = join(args.root, "generated", "surface-registry.yaml");
if (existsSync(registryPath)) {
  let reg;
  try { reg = yaml.load(readFileSync(registryPath, "utf8")); } catch { /* skip on parse error */ }
  const knownIds = new Set(Object.keys(reg?.surfaces ?? {}));
  if (knownIds.size > 0) {
    const unknown = args.surfaces.filter(id => !knownIds.has(id));
    if (unknown.length > 0) {
      console.error(`ERROR: Unknown surface ID(s): ${unknown.join(", ")}`);
      console.error(`  Known IDs: ${[...knownIds].join(", ")}`);
      process.exit(1);
    }
  }
}

// Resolve output directory; default is <spec-root>/generated/screenshots/.
const outDir = args.outDir ?? join(args.root, "generated", "screenshots");
mkdirSync(outDir, { recursive: true });

// Locate browser before processing any surface so we fail early with a clear message.
const browser = discoverBrowser();
if (browser.error) {
  console.error("ERROR: " + browser.error);
  process.exit(1);
}

console.log(`ui-spec screenshot`);
console.log(`  browser:  ${browser.path}`);
console.log(`  wireframe: ${htmlPath}`);
console.log(`  out-dir:   ${outDir}`);
console.log(`  surfaces:  ${args.surfaces.join(", ")}`);
console.log(`  viewport:  ${args.width}×${args.height}\n`);

let failed = 0;
for (const sid of args.surfaces) {
  const outFile = join(outDir, `${sid}.png`);
  process.stdout.write(`  ${sid} → ${outFile} ... `);
  const r = screenshotSurface(browser.path, htmlPath, sid, outFile, args.width, args.height);
  if (r.ok) {
    const kb = Math.round(statSync(outFile).size / 1024);
    console.log(`OK (${kb} KB)`);
  } else {
    console.log(`FAIL — ${r.error}`);
    failed++;
  }
}

if (failed > 0) {
  console.error(`\n${failed}/${args.surfaces.length} surface(s) failed.`);
  process.exit(1);
}
console.log(`\nAll ${args.surfaces.length} screenshot(s) written to: ${outDir}`);
