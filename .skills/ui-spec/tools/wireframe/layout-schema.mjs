// wireframe/layout-schema.mjs — SINGLE WRITER for the `yaml ui-layout` fence schema.
// Every tool that reads the layout model (extract-layout, validate, generate-ascii,
// chip-audit) imports from here; the browser bundle gets this file inlined by
// html-shell.mjs with `export ` prefixes stripped. Because of that inlining:
//   - ZERO imports allowed in this file (must run standalone in a <script> block)
//   - only top-level `export const` / `export function` declarations (the strip
//     regex in html-shell.mjs handles nothing else)

// ─── Top-level fence keys ──────────────────────────────────────────────────────

/** Known top-level keys of the ui-layout fence. Anything else = parse warning. */
export const LAYOUT_KEYS = [
  "columns",     // string[] — CSS fr column widths
  "row_heights", // string[] — CSS track heights, one per base areas row
  "areas",       // string[][] — grid-template-areas matrix (required)
  "floating",    // {region, when, replaces[]}[] — overlay banners
  "variants",    // {name: {prepend_rows, append_rows}} — alternate layouts
  "samples",     // {region: "text [chip]"} — 1-line fallback content
  "children",    // {region: {areas, variants}} — 1-level sub-layouts
  "elements",    // {"chip text": actionId} — chip → contract map (samples path)
  "content",     // {region: element[]} — typed wireframe content (preferred path)
];

// ─── Content primitive registry ────────────────────────────────────────────────

/**
 * Content element primitives. Each element in content[region][] is an object
 * whose FIRST key matching this registry is its type; remaining keys are opts.
 *   { btn: "Gọi", action: "A-S14-006", primary: true }
 *
 * Registry values declare shared semantics:
 *   actionable   — element may carry an `action:` opt (chip-audit: flag btn/tabs
 *                  entries missing it; badge/chips/text are display-only by type)
 *   value        — expected YAML shape of the type key's value (doc + validation aid)
 */
export const CONTENT_TYPES = {
  h:         { actionable: false, value: "string — heading text" },
  text:      { actionable: false, value: "string — body text" },
  btn:       { actionable: true,  value: "string — button label; opts: action, primary" },
  input:     { actionable: false, value: "string — placeholder text" },
  select:    { actionable: false, value: "string — selected value / placeholder" },
  checklist: { actionable: false, value: "string[] — items; prefix '[x] ' marks checked" },
  chips:     { actionable: false, value: "string[] — chip labels (display-only)" },
  badge:     { actionable: false, value: "string — status badge label" },
  tabs:      { actionable: true,  value: "string[] — tab labels; opts: active (label), action (whole bar) OR actions {label: action-id} (per tab)" },
  table:     { actionable: false, value: "{cols: string[], rows: number} — skeleton table" },
  list:      { actionable: false, value: "{item: string, rows: number} — repeated item template" },
  kpi:       { actionable: false, value: "{label: string, value: string} — big-number stat" },
  divider:   { actionable: false, value: "true — horizontal rule" },
  slot:      { actionable: false, value: "string — hatched placeholder (hosted panel etc.)" },
  row:       { actionable: false, value: "element[] — horizontal group (no nesting of row in row)" },
};

// ─── Element helpers ───────────────────────────────────────────────────────────

/**
 * Resolve the primitive type of a content element object.
 * The type is the first own key present in CONTENT_TYPES (insertion order of the
 * element object). Returns null for non-objects or when no key matches.
 * @param {object} el
 * @returns {string|null}
 */
export function contentElementType(el) {
  if (!el || typeof el !== "object" || Array.isArray(el)) return null;
  for (const k of Object.keys(el)) {
    if (Object.prototype.hasOwnProperty.call(CONTENT_TYPES, k)) return k;
  }
  return null;
}

/**
 * Walk every element of a content map, recursing one level into `row` groups.
 * @param {object} content - layout.content ({region: element[]})
 * @param {(info: {region: string, el: object, type: string|null}) => void} cb
 */
export function walkContent(content, cb) {
  if (!content || typeof content !== "object") return;
  for (const [region, elements] of Object.entries(content)) {
    if (!Array.isArray(elements)) continue;
    for (const el of elements) {
      const type = contentElementType(el);
      cb({ region, el, type });
      if (type === "row" && Array.isArray(el.row)) {
        for (const child of el.row) {
          cb({ region, el: child, type: contentElementType(child) });
        }
      }
    }
  }
}

/**
 * Collect all action references declared on content elements.
 * @param {object} content - layout.content
 * @returns {Array<{region: string, type: string|null, label: string, actionId: string}>}
 */
export function contentActionRefs(content) {
  const refs = [];
  walkContent(content, ({ region, el, type }) => {
    if (type === "row") return; // children visited separately by walkContent
    if (!el || typeof el !== "object") return;
    if (el.action != null) {
      refs.push({ region, type, label: contentElementLabel(el, type), actionId: String(el.action) });
    }
    // tabs per-label map: actions: {"Tab label": action-id}
    if (el.actions && typeof el.actions === "object") {
      for (const [label, id] of Object.entries(el.actions)) {
        refs.push({ region, type, label, actionId: String(id) });
      }
    }
  });
  return refs;
}

/**
 * Whether an actionable element (btn/tabs) actually carries an action mapping —
 * either a single `action:` or a non-empty per-label `actions:` map (tabs).
 * Used by chip-audit to classify mapped/unmapped.
 * @param {object} el
 * @returns {boolean}
 */
export function contentElementHasAction(el) {
  if (!el || typeof el !== "object") return false;
  if (el.action != null) return true;
  return !!(el.actions && typeof el.actions === "object" && Object.keys(el.actions).length > 0);
}

/**
 * Human-readable label of an element (for audit reports and flatten output).
 * @param {object} el
 * @param {string|null} type
 * @returns {string}
 */
export function contentElementLabel(el, type) {
  if (!type) return "?";
  const v = el[type];
  if (typeof v === "string") return v;
  if (Array.isArray(v)) return v.join(" · ");
  if (v && typeof v === "object") {
    if (type === "table") return "table " + (Array.isArray(v.cols) ? v.cols.join("|") : "") + " ×" + (v.rows ?? "?");
    if (type === "list")  return "list ×" + (v.rows ?? "?") + (v.item ? ": " + v.item : "");
    if (type === "kpi")   return (v.label ? v.label + " " : "") + (v.value ?? "");
  }
  return type;
}

// ─── ASCII flatten ─────────────────────────────────────────────────────────────

/**
 * Flatten a region's content element list into ONE deterministic text line for
 * the ASCII blueprint. Interactive elements keep [brackets] so the blueprint
 * stays visually consistent with the legacy samples grammar.
 * @param {object[]} elements - content[region]
 * @returns {string}
 */
export function flattenContentLine(elements) {
  if (!Array.isArray(elements)) return "";
  const parts = [];
  for (const el of elements) {
    const type = contentElementType(el);
    if (type === "row" && Array.isArray(el.row)) {
      const inner = el.row.map((c) => flattenOneElement(c, contentElementType(c))).filter(Boolean);
      parts.push(inner.join(" "));
    } else {
      const t = flattenOneElement(el, type);
      if (t) parts.push(t);
    }
  }
  return parts.join(" · ");
}

/**
 * Flatten a single (non-row) element to text. Shared by flattenContentLine.
 * @param {object} el
 * @param {string|null} type
 * @returns {string}
 */
export function flattenOneElement(el, type) {
  if (!type) return "";
  const v = el[type];
  switch (type) {
    case "h":         return String(v);
    case "text":      return String(v);
    case "btn":       return "[" + String(v) + "]";
    case "input":     return "[input: " + String(v) + "]";
    case "select":    return "[" + String(v) + " v]";
    case "checklist": return (Array.isArray(v) ? v : []).map((i) => (String(i).startsWith("[x] ") ? String(i) : "[ ] " + String(i))).join(" ");
    case "chips":     return (Array.isArray(v) ? v : []).map((c) => "[" + String(c) + "]").join(" ");
    case "badge":     return "[" + String(v) + "]";
    case "tabs":      return (Array.isArray(v) ? v : []).map((t) => (el.active === t ? "|*" + String(t) + "*|" : "| " + String(t) + " |")).join("");
    case "table":     return "tbl(" + (Array.isArray(v?.cols) ? v.cols.join(" | ") : "") + ") ×" + (v?.rows ?? "?");
    case "list":      return "list ×" + (v?.rows ?? "?") + (v?.item ? " {" + String(v.item) + "}" : "");
    case "kpi":       return (v?.label ? String(v.label) + ": " : "") + String(v?.value ?? "");
    case "divider":   return "────";
    case "slot":      return "<<" + String(v) + ">>";
    default:          return "";
  }
}
