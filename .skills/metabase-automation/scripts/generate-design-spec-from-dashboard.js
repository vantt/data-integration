#!/usr/bin/env node
/**
 * Reverse-flow: Generate a draft Design Spec from a live Metabase dashboard.
 *
 * Captures dashboard structure and reverse-translates Metabase display types
 * back to standard analytics vocabulary, producing a composition table per view.
 *
 * Usage:
 *   node generate-design-spec-from-dashboard.js <dashboard_id> [output.md]
 *
 * Environment:
 *   METABASE_URL     - Base URL (default: http://127.0.0.1:3000/)
 *   METABASE_API_KEY - API Key
 */

const MetabaseClient = require("./metabase_client");
const { deriveNameFromText } = require("../lib/text-card-helpers");
const fs = require("fs");
const path = require("path");

const METABASE_URL = process.env.METABASE_URL || "http://127.0.0.1:3000/";
const API_KEY = process.env.METABASE_API_KEY;

if (!API_KEY) { console.error("❌ METABASE_API_KEY missing."); process.exit(1); }

const args = process.argv.slice(2);
if (args.length < 1) { console.error("Usage: node generate-design-spec-from-dashboard.js <dashboard_id> [output.md]"); process.exit(1); }

const DASHBOARD_ID = parseInt(args[0]);
const OUTPUT_FILE = args[1] || null;

// ---------------------------------------------------------------------------
// Reverse mapping: Metabase display → standard vocab
// ---------------------------------------------------------------------------

function reverseVizType(card, dc) {
  const display = card.display || "table";
  const viz = { ...(card.visualization_settings || {}), ...(dc.visualization_settings || {}) };

  if (display === "scalar") {
    return viz["scalar.comparisons"] ? "single-value-with-trend" : "single-value";
  }
  if (display === "progress") return "progress-toward-goal";
  if (display === "gauge") return "gauge";
  if (display === "line") return "line-chart";
  if (display === "area") {
    return viz["stackable.stack_type"] === "stacked" ? "stacked-area" : "area-chart";
  }
  if (display === "bar") {
    if (viz["stackable.stack_type"] === "stacked") return "stacked-bar";
    return "vertical-bar";
  }
  if (display === "row") return "horizontal-bar";
  if (display === "combo") return "combo-chart";
  if (display === "pie") return "donut";
  if (display === "funnel") return "funnel";
  if (display === "waterfall") return "waterfall";
  if (display === "pivot") return "pivot-table";
  if (display === "table") return viz["table.column_formatting"] ? "data-table-formatted" : "data-table";
  return display;
}

// Infer card role from position and viz type
function inferRole(vizType, dc, isFirst) {
  if (vizType === "text-annotation") return "annotation";
  if (isFirst && (vizType.startsWith("single-value") || vizType === "progress-toward-goal")) return "hero";
  if (vizType.startsWith("single-value") || vizType === "gauge") return "supporting";
  if (vizType.includes("chart") || vizType.includes("area") || vizType === "line-chart") return "trend";
  if (vizType.includes("bar") || vizType === "donut") return "breakdown";
  if (vizType.includes("table")) return "detail";
  return "supporting";
}

// Map grid size to size token
function sizeToken(sizeX, sizeY) {
  let w = "full-width";
  if (sizeX <= 6) w = "one-third";
  else if (sizeX <= 9) w = "half";
  else if (sizeX <= 12) w = "two-thirds";

  let h = "medium";
  if (sizeY <= 2) h = "minimal";
  else if (sizeY <= 4) h = "short";
  else if (sizeY >= 8) h = "tall";

  return `${w} × ${h}`;
}

// ---------------------------------------------------------------------------
// Generate design spec
// ---------------------------------------------------------------------------

async function main() {
  const client = new MetabaseClient(METABASE_URL, API_KEY);
  await client.connect();
  console.error(`✅ Connected to Metabase`);

  const dash = await client.core.request(`/api/dashboard/${DASHBOARD_ID}`);
  const dashcards = dash.dashcards || dash.ordered_cards || [];
  const tabs = dash.tabs || [];

  console.error(`📊 Dashboard: ${dash.name} (ID: ${DASHBOARD_ID})`);
  console.error(`📑 Tabs: ${tabs.length || "none"}, Cards: ${dashcards.length}`);

  // Fetch card details
  const cardCache = {};
  for (const dc of dashcards) {
    if (dc.card_id && !cardCache[dc.card_id]) {
      try { cardCache[dc.card_id] = await client.core.request(`/api/card/${dc.card_id}`); }
      catch (e) { console.error(`⚠️ Could not fetch card ${dc.card_id}`); }
    }
  }

  // Group by tab
  const views = [];
  if (tabs.length > 0) {
    for (const tab of tabs) {
      const cards = dashcards.filter(dc => dc.dashboard_tab_id === tab.id).sort((a, b) => a.row - b.row || a.col - b.col);
      views.push({ name: tab.name, cards });
    }
  } else {
    views.push({ name: null, cards: [...dashcards].sort((a, b) => a.row - b.row || a.col - b.col) });
  }

  // Build spec
  const lines = [];
  const today = new Date().toISOString().split("T")[0];

  // Frontmatter
  lines.push("---");
  lines.push(`title: "${dash.name}"`);
  lines.push("archetype: TODO");
  lines.push("status: draft-from-capture");
  lines.push(`last_modified: ${today}`);
  lines.push("domain_refs: []");
  lines.push("---");
  lines.push("");
  lines.push(`## Design Spec: ${dash.name}`);
  lines.push("");

  // Brief
  lines.push("### Brief");
  lines.push("");
  lines.push("- **Audience:** TODO");
  lines.push("- **Time budget:** TODO");
  lines.push("- **Primary question:** TODO");
  lines.push("- **Decision enabled:** TODO");
  lines.push("- **Comparison frame:** TODO");
  lines.push("- **Archetype:** TODO");
  if (dash.description) lines.push(`- **Description:** ${dash.description}`);
  lines.push("");

  // Views
  lines.push("### Views");
  lines.push("");
  if (views.length > 1) {
    lines.push(`Multi-view — ${views.length} views:`);
    views.forEach((v, i) => lines.push(`${i + 1}. **${v.name}**`));
  } else {
    lines.push("Single view");
  }
  lines.push("");
  lines.push("---");
  lines.push("");

  // Composition tables per view
  let cardNum = 1;
  for (let vi = 0; vi < views.length; vi++) {
    const view = views[vi];
    const viewLabel = view.name || "Main";

    lines.push(`### View ${vi + 1} — ${viewLabel}`);
    lines.push("");
    lines.push("**Narrative flow:** TODO");
    lines.push("");
    lines.push("| # | Row | Card | Role | Viz Type | Size | Communication | Comparison |");
    lines.push("|---|-----|------|------|----------|------|---------------|------------|");

    let isFirstData = true;
    let lastRow = -1;
    const rowLetters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    let rowIdx = 0;

    for (const dc of view.cards) {
      // Determine row letter
      if (dc.row !== lastRow) { lastRow = dc.row; rowIdx = Math.min(rowIdx + (cardNum > 1 ? 1 : 0), 25); }
      const rowLetter = rowLetters[rowIdx] || "Z";

      if (dc.card_id === null) {
        // Text card
        const text = (dc.visualization_settings || {}).text || "";
        const name = deriveNameFromText(text);
        lines.push(`| ${cardNum} | ${rowLetter} | "${name}" | annotation | text-annotation | ${sizeToken(dc.size_x, dc.size_y)} | Section heading | — |`);
      } else {
        const card = cardCache[dc.card_id];
        if (!card) continue;
        const vizType = reverseVizType(card, dc);
        const role = inferRole(vizType, dc, isFirstData);
        if (isFirstData) isFirstData = false;
        lines.push(`| ${cardNum} | ${rowLetter} | ${card.name} | ${role} | ${vizType} | ${sizeToken(dc.size_x, dc.size_y)} | TODO | TODO |`);
      }
      cardNum++;
    }

    lines.push("");
    lines.push("---");
    lines.push("");
  }

  const markdown = lines.join("\n");

  if (OUTPUT_FILE) {
    const dir = path.dirname(OUTPUT_FILE);
    if (dir && !fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(OUTPUT_FILE, markdown, "utf8");
    console.error(`✅ Design spec written to: ${OUTPUT_FILE}`);
  } else {
    process.stdout.write(markdown);
  }
  console.error("🚀 Reverse capture complete.");
}

main().catch(e => { console.error(`❌ ${e.message}`); process.exit(1); });
