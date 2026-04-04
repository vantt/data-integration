/**
 * Stable identity helpers for Metabase text cards.
 *
 * Text cards get a hidden HTML comment marker <!-- text-id:<slug> -->
 * injected into their markdown content. This allows syncCards() to match
 * existing text dashcards on redeploy instead of always recreating them.
 */

// Matches <!-- text-id:some-slug-123 --> (global flag to handle multiple markers)
const TEXT_ID_REGEX = /<!-- text-id:([a-z0-9-]+) -->/g;

/**
 * Convert a text card name to a stable slug.
 * Handles Vietnamese diacritics, strips non-alphanumeric, collapses hyphens.
 * Example: "Doanh thu & Target" → "doanh-thu-target"
 */
function slugify(name) {
  const slug = name
    .normalize("NFD")                       // decompose diacritics
    .replace(/[\u0300-\u036f]/g, "")        // strip combining marks
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")           // non-alnum → hyphen
    .replace(/^-+|-+$/g, "");              // trim leading/trailing
  // Fallback for names that produce empty slug (all symbols, whitespace, etc.)
  return slug || "text";
}

/**
 * Extract the text-id slug from a text card's markdown content.
 * Uses the LAST marker found — markers are appended at end, so last is canonical.
 * Handles edge case where content has multiple markers (e.g. from manual edits).
 */
function extractTextId(markdownText) {
  if (!markdownText) return null;
  const matches = [...markdownText.matchAll(TEXT_ID_REGEX)];
  return matches.length > 0 ? matches[matches.length - 1][1] : null;
}

/**
 * Inject a text-id marker into text card content if not already present.
 * Strips ALL existing markers first to prevent orphaned duplicates.
 * Marker is appended at the end so it survives most manual UI edits.
 */
function injectTextId(markdownText, slug) {
  if (!markdownText) return `<!-- text-id:${slug} -->`;
  const existing = extractTextId(markdownText);
  if (existing === slug) return markdownText;
  // Strip ALL old markers, then append the correct one
  const cleaned = markdownText.replace(TEXT_ID_REGEX, "").trimEnd();
  return `${cleaned}\n<!-- text-id:${slug} -->`;
}

/**
 * Derive a human-readable name from text card content (for capture).
 * Takes the first non-empty line that isn't a text-id marker,
 * strips leading # heading prefix.
 */
function deriveNameFromText(markdownText) {
  if (!markdownText) return "Untitled";
  const lines = markdownText.split("\n");
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (/<!-- text-id:[a-z0-9-]+ -->/.test(trimmed)) continue;
    // Strip markdown heading prefix: "# Foo" → "Foo"
    return trimmed.replace(/^#+\s*/, "") || "Untitled";
  }
  return "Untitled";
}

module.exports = { TEXT_ID_REGEX, slugify, extractTextId, injectTextId, deriveNameFromText };
