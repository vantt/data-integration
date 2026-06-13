// extract.mjs — read surface Markdown files -> contracts (in-memory).
// Only parses: (1) frontmatter, (2) fenced blocks with the configured contract tag.
// All other prose is ignored — Markdown variety does not affect parsing.
// Auto-generates action IDs for interactions missing an `id` field: A-{surfaceId}-{001,002,...}

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, basename } from "node:path";
import matter from "gray-matter";
import MarkdownIt from "markdown-it";
import yaml from "js-yaml";
import { SPEC_ROOT, contractTag, surfaceDirs, crossCutting } from "./config.mjs";

const md = new MarkdownIt();

/** Recursively list *.md files in configured surface dirs + cross-cutting files. */
export function listSpecFiles() {
  const files = [];

  for (const dir of surfaceDirs) {
    const abs = join(SPEC_ROOT, dir);
    let entries = [];
    try { entries = readdirSync(abs); } catch { continue; }
    for (const e of entries) {
      const p = join(abs, e);
      if (statSync(p).isFile() && e.endsWith(".md")) files.push(p);
    }
  }

  for (const f of crossCutting) {
    // Support both bare filenames (relative to spec root) and absolute paths
    const p = f.startsWith("/") || /^[A-Za-z]:/.test(f) ? f : join(SPEC_ROOT, f);
    try { if (statSync(p).isFile()) files.push(p); } catch { /* optional */ }
  }

  return files;
}

/** Extract all fenced code blocks whose info-string is `yaml <contractTag>`. */
function extractContractBlocks(markdownBody) {
  const tokens = md.parse(markdownBody, {});
  const blocks = [];
  for (const t of tokens) {
    if (t.type !== "fence") continue;
    const parts = (t.info || "").trim().split(/\s+/);
    if (parts[0] === "yaml" && parts.includes(contractTag)) {
      blocks.push(t.content);
    }
  }
  return blocks;
}

/** Auto-generate IDs for interactions that have no `id` field.
 *  Pattern: A-{surfaceId}-{sequence padded to 3 digits}
 *  Only applies to interactions[], not emits[] (emit IDs always required).
 */
function assignMissingInteractionIds(interactions, surfaceId) {
  if (!surfaceId || !Array.isArray(interactions)) return interactions;
  let seq = 0;
  return interactions.map((it) => {
    if (it.id) return it;
    seq++;
    return { ...it, id: `A-${surfaceId}-${String(seq).padStart(3, "0")}`, _autoId: true };
  });
}

/** Parse one file -> { file, id, meta, contract, blockCount, errors[] } */
export function extractFile(absPath) {
  const raw = readFileSync(absPath, "utf8");
  const rel = relative(SPEC_ROOT, absPath).replace(/\\/g, "/");
  const errors = [];

  const fm = matter(raw);
  const meta = fm.data || {};
  const blocks = extractContractBlocks(fm.content);

  let contract = null;
  if (blocks.length === 0) {
    errors.push(`no \`yaml ${contractTag}\` block found`);
  } else if (blocks.length > 1) {
    errors.push(`expected exactly 1 contract block, found ${blocks.length}`);
  } else {
    try {
      contract = yaml.load(blocks[0]) || {};
      // Auto-assign IDs to interactions missing an id
      if (contract.interactions) {
        contract.interactions = assignMissingInteractionIds(contract.interactions, meta.id);
      }
    } catch (e) {
      errors.push(`YAML parse error: ${e.message}`);
    }
  }

  return {
    file: rel,
    fileBase: basename(absPath),
    id: meta.id,
    meta,
    contract,
    blockCount: blocks.length,
    errors,
  };
}

/** Extract all spec files. */
export function extractAll() {
  return listSpecFiles().map(extractFile);
}

export { SPEC_ROOT };

// Allow direct execution for debug: `node extract.mjs [--root <path>]`
if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("extract.mjs")) {
  const all = extractAll();
  for (const f of all) {
    const autoIds = (f.contract?.interactions || []).filter((i) => i._autoId).length;
    const autoNote = autoIds ? ` (${autoIds} auto-id)` : "";
    console.log(`${f.id ?? "?"}\t${f.file}\tblocks=${f.blockCount}\terrors=${f.errors.length}${autoNote}`);
  }
  console.log(`\nTotal files: ${all.length}`);
}
