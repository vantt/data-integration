/**
 * Stable identity helpers for Metabase text cards.
 *
 * Text cards get a hidden HTML comment marker <!-- text-id:<slug> -->
 * injected into their markdown content. This allows syncCards() to match
 * existing text dashcards on redeploy instead of always recreating them.
 */

// Matches <!-- text-id:some-slug-123 -->
const TEXT_ID_REGEX = /<!-- text-id:([a-z0-9-]+) -->/;

/**
 * Convert a text card name to a stable slug.
 * Handles Vietnamese diacritics, strips non-alphanumeric, collapses hyphens.
 * Example: "Doanh thu & Target" → "doanh-thu-target"
 */
function slugify(name) {
  return name
    .normalize("NFD")                       // decompose diacritics
    .replace(/[\u0300-\u036f]/g, "")        // strip combining marks
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")           // non-alnum → hyphen
    .replace(/^-+|-+$/g, "");              // trim leading/trailing
}

/**
 * Extract the text-id slug from a text card's markdown content.
 * Returns the slug string or null if no marker found.
 */
function extractTextId(markdownText) {
  if (!markdownText) return null;
  const m = markdownText.match(TEXT_ID_REGEX);
  return m ? m[1] : null;
}

/**
 * Inject a text-id marker into text card content if not already present.
 * Marker is appended at the end so it survives most manual UI edits.
 */
function injectTextId(markdownText, slug) {
  if (!markdownText) return `<!-- text-id:${slug} -->`;
  const existing = extractTextId(markdownText);
  if (existing === slug) return markdownText;
  // Strip any old marker, then append the correct one
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
    if (TEXT_ID_REGEX.test(trimmed)) continue;
    // Strip markdown heading prefix: "# Foo" → "Foo"
    return trimmed.replace(/^#+\s*/, "") || "Untitled";
  }
  return "Untitled";
}

module.exports = { TEXT_ID_REGEX, slugify, extractTextId, injectTextId, deriveNameFromText };
