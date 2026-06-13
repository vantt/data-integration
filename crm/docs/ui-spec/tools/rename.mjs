// rename.mjs — safely rename a token (surface ID, action ID, or event name) across the WHOLE
// spec: word-boundary replace in every .md (skips generated/ + node_modules) + renames matching
// files. DRY RUN by default — pass --apply to write. After --apply, run `npm run check` so the
// validator confirms referential integrity (no dangling targets/hosts/listens/steps).
//
// Usage:
//   node rename.mjs <old> <new> [--root <spec-root>]            # preview (default)
//   node rename.mjs <old> <new> [--root <spec-root>] --apply    # execute
//
// Notes:
//   - `\b<old>\b` matches the standalone token AND inside action IDs, e.g. renaming `S05`→`S07`
//     also rewrites `A-S05-001`→`A-S07-001`. Renaming a full action ID (`A-S05-001`) works too.
//   - This is a textual rename: review the dry-run list before --apply. Distinctive IDs (S05, M03,
//     event names) rarely collide; if `<old>` is a common word, expect over-matches.

import { readFileSync, writeFileSync, readdirSync, statSync, renameSync } from "node:fs";
import { join, basename, dirname } from "node:path";
import { specRoot } from "./config.mjs";

// ── Args (config.mjs already consumed --root <value>) ──────────────────────────
const argv = process.argv.slice(2);
const apply = argv.includes("--apply");
const positionals = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === "--apply") continue;
  if (argv[i] === "--root") { i++; continue; } // skip the --root value
  positionals.push(argv[i]);
}
const [oldTok, newTok] = positionals;
if (!oldTok || !newTok) {
  console.error("Usage: node rename.mjs <old> <new> [--root <spec>] [--apply]");
  process.exit(1);
}

const esc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const tokenRe = new RegExp("\\b" + esc(oldTok) + "\\b", "g");

// ── Collect .md files (skip generated/, node_modules) ──────────────────────────
function walk(dir, out = []) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) {
      if (e !== "generated" && e !== "node_modules") walk(p, out);
    } else if (e.endsWith(".md")) {
      out.push(p);
    }
  }
  return out;
}

const files = walk(specRoot);
let totalHits = 0, filesChanged = 0, filesRenamed = 0;

console.log(`${apply ? "APPLY" : "DRY RUN"} — rename \`${oldTok}\` -> \`${newTok}\`  (spec: ${specRoot})\n`);

for (const p of files) {
  const content = readFileSync(p, "utf8");
  const hits = (content.match(tokenRe) || []).length;
  const base = basename(p);
  const newBase = base.replace(tokenRe, newTok);
  const willRename = newBase !== base;
  if (!hits && !willRename) continue;

  const rel = p.slice(specRoot.length + 1).replace(/\\/g, "/");
  console.log(`  ${rel}: ${hits} occurrence(s)${willRename ? `  [file -> ${newBase}]` : ""}`);
  if (hits) { totalHits += hits; filesChanged++; }
  if (willRename) filesRenamed++;

  if (apply) {
    if (hits) writeFileSync(p, content.replace(tokenRe, newTok), "utf8");
    if (willRename) renameSync(p, join(dirname(p), newBase));
  }
}

console.log(`\nTotal: ${totalHits} occurrence(s) in ${filesChanged} file(s), ${filesRenamed} file(s) renamed.`);
console.log(apply
  ? "Done. Now run `npm run check` to validate referential integrity."
  : "Re-run with --apply to execute, then `npm run check`.");
