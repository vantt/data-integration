// wireframe/extract-states.mjs — parse ## States section from surface prose.
// Returns { states: [{id, label, description, errRefs}], errIds: Set<string> }
// Also reads the global 30-states-and-errors.md catalog for ERR-* descriptions.

import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

// Matches a bullet line starting with an optional bold-wrapped ST-* id
// Handles:  "- ST-WORKLIST-EMPTY: text"  and  "- **ST-CALL-NO-SCRIPT**: text"
const ST_SECTION_RE = /^##\s+States?\s*$/im;
const NEXT_H2_RE    = /^##\s+/m;
const ST_BULLET_RE  = /^\s*[-*]\s+\*{0,2}(ST-[A-Za-z0-9-]+)\*{0,2}[:\s—–-]+(.+)/;
const ERR_REF_RE    = /ERR-[A-Za-z0-9-]+/g;

/**
 * Extract state entries from a surface's prose (already stripped of contract block).
 * @param {string} prose - prose text for one surface
 * @returns {{ states: {id, label, description, errRefs}[], errIds: Set<string> }}
 */
export function extractStates(prose) {
  const sectionStart = prose.search(ST_SECTION_RE);
  if (sectionStart === -1) return { states: [], errIds: new Set() };

  // Slice from the matched header onward, then drop the header line itself
  const afterHeader = prose.slice(sectionStart).replace(ST_SECTION_RE, "");
  // Stop at the next ## heading
  const nextH2 = afterHeader.search(NEXT_H2_RE);
  const section = nextH2 === -1 ? afterHeader : afterHeader.slice(0, nextH2);

  const states = [];
  const errIds = new Set();

  for (const line of section.split("\n")) {
    const m = line.match(ST_BULLET_RE);
    if (!m) continue;
    const id   = m[1];
    const rest = m[2].trim();

    // Optional split: "label — description" or "label: detail"
    const sepIdx   = rest.search(/ [—–-] | :\s/);
    const label       = sepIdx === -1 ? rest : rest.slice(0, sepIdx).trim();
    const description = sepIdx === -1 ? ""   : rest.slice(sepIdx).replace(/^[—–:\s-]+/, "").trim();

    // Collect ERR-* refs from both label and description
    const combined = label + " " + description;
    const errRefs  = [...combined.matchAll(ERR_REF_RE)].map(x => x[0]);
    errRefs.forEach(e => errIds.add(e));

    states.push({ id, label, description, errRefs });
  }
  return { states, errIds };
}

/**
 * Read 30-states-and-errors.md (auto-detected by filename) and return a catalog
 * mapping ERR-* ids to their first-line description text.
 * @param {string} specRoot - absolute path to the ui-spec directory
 * @returns {Record<string, string>}
 */
export function readErrCatalog(specRoot) {
  const catalog = {};
  try {
    const name = readdirSync(specRoot).find(n => /states/i.test(n) && n.endsWith(".md"));
    if (!name) return catalog;
    const raw = readFileSync(join(specRoot, name), "utf8");

    // Split file on heading boundaries (##, ###, ####) and process each segment
    const segments = raw.split(/\n(?=#{2,4}\s)/);
    for (const seg of segments) {
      const headMatch = seg.match(/^#{2,4}\s+(ERR-[A-Za-z0-9-]+)/m);
      if (!headMatch) continue;
      const errId = headMatch[1];
      // Take first non-empty line after the heading as the description
      const lines = seg.split("\n").slice(1).filter(l => l.trim());
      catalog[errId] = (lines[0] ?? "").trim().replace(/^[-*]\s+/, "");
    }
  } catch {
    /* catalog file unreadable — return empty, graceful degradation */
  }
  return catalog;
}
