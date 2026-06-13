// wireframe/ascii-normalize.mjs
// Node-side, no deps. Re-align an LLM-authored ASCII box so its outer right border
// forms a straight column; also strip the surrounding ``` fence + blank lines.
// API: displayWidth(str) → cell count;  normalizeAsciiBlock(text) → straightened block.

/**
 * Visual display width (monospace <pre> cells) of a string. Best-effort — a few
 * symbol widths are font-dependent. Iterates by Unicode code point.
 *   0 = combining marks / variation-selector-16
 *   2 = CJK & East-Asian blocks + wide emoji/symbol ranges (incl. ▶ U+25A0–25FF,
 *       ⚠ U+2600–27BF, emoji U+1F000–1FAFF)
 *   1 = everything else (Latin, Vietnamese precomposed, box-drawing, arrows, ·, —)
 */
export function displayWidth(str) {
  if (!str) return 0;
  let width = 0;
  for (const ch of str) {
    const cp = ch.codePointAt(0);
    // 0-width: combining marks + emoji variation selector
    if (
      (cp >= 0x0300 && cp <= 0x036F) || (cp >= 0x1AB0 && cp <= 0x1AFF) ||
      (cp >= 0x1DC0 && cp <= 0x1DFF) || (cp >= 0x20D0 && cp <= 0x20FF) ||
      (cp >= 0xFE20 && cp <= 0xFE2F) || cp === 0xFE0F
    ) continue;
    // 2-wide: CJK / East-Asian + wide emoji & symbol ranges
    if (
      (cp >= 0x1100  && cp <= 0x115F)  || (cp >= 0x2E80  && cp <= 0x303E)  ||
      (cp >= 0x3041  && cp <= 0x33FF)  || (cp >= 0x3400  && cp <= 0x4DBF)  ||
      (cp >= 0x4E00  && cp <= 0x9FFF)  || (cp >= 0xA000  && cp <= 0xA4CF)  ||
      (cp >= 0xAC00  && cp <= 0xD7A3)  || (cp >= 0xF900  && cp <= 0xFAFF)  ||
      (cp >= 0xFE30  && cp <= 0xFE4F)  || (cp >= 0xFF00  && cp <= 0xFF60)  ||
      (cp >= 0xFFE0  && cp <= 0xFFE6)  || (cp >= 0x1F000 && cp <= 0x1FAFF) ||
      (cp >= 0x2600  && cp <= 0x27BF)  || (cp >= 0x2B00  && cp <= 0x2BFF)  ||
      (cp >= 0x25A0  && cp <= 0x25FF)
    ) { width += 2; continue; }
    width += 1;
  }
  return width;
}

// Box-drawing chars: horizontal/junction set (for border-row detection) + the set
// that may legitimately be the trailing (rightmost) border of a content row.
const H_BORDER_CHARS = new Set(Array.from("─═┌┐└┘├┤┬┴┼╭╮╯╰+"));
const TRAILING_BORDER_CHARS = new Set(Array.from("│┃║┤┐┘╮╯+"));
const H_FILL = "─";
const isFence = (line) => /^\s*```/.test(line); // markdown code-fence line

// Ambiguous-width symbols → guaranteed 1-cell ASCII, so alignment is font-independent
// (these glyphs render 1 or 2 cells depending on font/OS; ASCII is always 1 cell).
const GLYPH_MAP = {
  "▶": ">", "◀": "<", "▲": "^", "▼": "v", "■": "#", "●": "o",
  "⚠": "!", "☁": "*", "✓": "v", "✕": "x", "✗": "x", "★": "*", "☆": "*", "ⓘ": "i",
};
const GLYPH_RE = new RegExp("[" + Object.keys(GLYPH_MAP).join("") + "]", "g");
const glyphNormalize = (text) => text.replace(GLYPH_RE, (ch) => GLYPH_MAP[ch] ?? ch);

/** True if the whole line is only spaces + box/junction chars (a pure border row). */
function isHBorderLine(line) {
  if (!line.trim()) return false;
  for (const ch of line) if (ch !== " " && !H_BORDER_CHARS.has(ch)) return false;
  return true;
}

/** Right-pad str with padChar (width-1) until displayWidth reaches targetW. */
function padRight(str, targetW, padChar = " ") {
  const cur = displayWidth(str);
  return cur >= targetW ? str : str + padChar.repeat(targetW - cur);
}

/** Index of the last non-space char in a code-point array, or -1. */
function lastNonSpace(chars) {
  for (let i = chars.length - 1; i >= 0; i--) if (chars[i] !== " ") return i;
  return -1;
}

/**
 * Re-align an ASCII box so its outer right border is a straight column.
 * Strips surrounding ``` fences + leading/trailing blank lines first.
 * Horizontal border rows are rebuilt with a continuous fill; content rows are
 * padded before their trailing border — with dashes when the row is a separator
 * (ends in ─/═) so the line stays unbroken, otherwise with spaces. Inner │
 * separators are never moved. Pure, deterministic, best-effort.
 */
export function normalizeAsciiBlock(text) {
  if (!text) return text;

  // Replace ambiguous-width symbols with 1-cell ASCII so alignment holds in any mono font.
  text = glyphNormalize(text);

  // Pre-pass: drop ``` fence lines, then trim leading/trailing blank lines.
  let lines = text.split("\n").filter((l) => !isFence(l));
  while (lines.length && !lines[0].trim()) lines.shift();
  while (lines.length && !lines[lines.length - 1].trim()) lines.pop();
  if (!lines.length) return "";

  let targetW = 0;
  for (const line of lines) { const w = displayWidth(line); if (w > targetW) targetW = w; }
  if (targetW === 0) return lines.join("\n");

  const result = [];
  for (const line of lines) {
    if (displayWidth(line) === targetW) { result.push(line); continue; }
    if (!line.trim()) { result.push(padRight(line, targetW)); continue; }

    // Horizontal border row → rebuild with continuous fill.
    if (isHBorderLine(line)) {
      const chars = [...line];
      const firstIdx = line.search(/\S/);
      const lastIdx = lastNonSpace(chars);
      if (firstIdx === -1 || lastIdx <= firstIdx) { result.push(padRight(line, targetW)); continue; }

      const leading = line.slice(0, firstIdx);
      const firstChar = chars[firstIdx], lastChar = chars[lastIdx];
      const counts = {};
      for (const ch of chars.slice(firstIdx + 1, lastIdx))
        if (ch !== " " && H_BORDER_CHARS.has(ch)) counts[ch] = (counts[ch] ?? 0) + 1;
      let fillChar = H_FILL, fillMax = 0;
      for (const [ch, cnt] of Object.entries(counts)) if (cnt > fillMax) { fillMax = cnt; fillChar = ch; }

      const fillNeeded = targetW - displayWidth(leading) - 2; // firstChar + lastChar are width 1
      if (fillNeeded < 0) { result.push(padRight(line, targetW)); continue; }
      result.push(leading + firstChar + fillChar.repeat(fillNeeded) + lastChar);
      continue;
    }

    // Vertical-bordered content row → pad before the trailing border char.
    const chars = [...line];
    const lastIdx = lastNonSpace(chars);
    if (lastIdx !== -1 && TRAILING_BORDER_CHARS.has(chars[lastIdx])) {
      const trailing = chars[lastIdx];
      const content = chars.slice(0, lastIdx).join("");
      // Dash-extend separators (content ends in ─/═) so the rule reaches the border;
      // otherwise space-pad (normal content cell).
      const padChar = /[─═]$/.test(content) ? content.slice(-1) : " ";
      result.push(padRight(content, targetW - displayWidth(trailing), padChar) + trailing);
      continue;
    }

    // Plain row → right-pad with spaces.
    result.push(padRight(line, targetW));
  }
  return result.join("\n");
}
