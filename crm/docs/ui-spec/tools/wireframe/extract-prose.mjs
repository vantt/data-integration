// wireframe/extract-prose.mjs
// Duplicates extractProse + findAsciiBlock from interpret.mjs (interpret.mjs does not export
// them). ~40-line accepted dup to keep interpret.mjs byte-identical. See plan phase-01.

/**
 * Strip frontmatter (---...---) and contract fenced block from raw markdown.
 * Returns remaining prose text.
 * @param {string} raw - raw file content
 * @param {string} contractTag - the contract fence tag (e.g. "sao-ke-contract")
 */
export function extractProse(raw, contractTag) {
  // Strip YAML frontmatter
  let text = raw.replace(/^---[\s\S]*?---\n?/, "");
  // Strip fenced contract blocks: ```yaml <contractTag> ... ```
  const fenceRe = new RegExp("```yaml\\s+" + contractTag + "[\\s\\S]*?```", "g");
  text = text.replace(fenceRe, "");
  return text;
}

/**
 * Find the first ASCII art block in prose.
 * Looks for lines containing box-drawing chars or +--+ table patterns.
 * @param {string} prose
 * @returns {string|null}
 */
export function findAsciiBlock(prose) {
  const lines = prose.split("\n");
  const boxChars = /[┌┐└┘│─┬┴├┤┼╔╗╚╝║═]/;
  const pseudoBox = /\+[-=+]{2,}/;

  let blockStart = -1;
  let blockEnd = -1;
  let inBlock = false;

  for (let i = 0; i < lines.length; i++) {
    const hasBox = boxChars.test(lines[i]) || pseudoBox.test(lines[i]);
    if (hasBox && !inBlock) {
      blockStart = i;
      inBlock = true;
    } else if (inBlock && !hasBox && lines[i].trim() === "") {
      // Allow one blank line inside block
      if (i + 1 < lines.length && (boxChars.test(lines[i + 1]) || pseudoBox.test(lines[i + 1]))) {
        continue;
      }
      blockEnd = i;
      break;
    }
  }

  if (blockStart === -1) return null;
  if (blockEnd === -1) blockEnd = lines.length;

  // Include a few lines before/after for context
  const start = Math.max(0, blockStart - 1);
  const end = Math.min(lines.length, blockEnd + 1);
  return lines.slice(start, end).join("\n");
}
