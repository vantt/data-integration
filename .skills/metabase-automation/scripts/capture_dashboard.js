#!/usr/bin/env node
/**
 * Capture a Metabase dashboard and generate a blueprint markdown file.
 *
 * Reads dashboard layout, card SQL, visualization settings, and positions
 * from Metabase API and outputs a deployable blueprint markdown.
 *
 * Usage:
 *   node capture_dashboard.js <dashboard_id> [output_file.md]
 *   node capture_dashboard.js 11                              # prints to stdout
 *   node capture_dashboard.js 11 blueprints/ceo_weekly.md     # writes to file
 *
 * Environment:
 *   METABASE_URL     - Base URL (default: http://127.0.0.1:3000/)
 *   METABASE_API_KEY - API Key
 */

const MetabaseClient = require("./metabase_client");
const fs = require("fs");
const path = require("path");

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------
const METABASE_URL = process.env.METABASE_URL || "http://127.0.0.1:3000/";
const API_KEY = process.env.METABASE_API_KEY;
const DB_NAME = process.env.METABASE_DB_NAME || "Sapo";

if (!API_KEY) {
  console.error("❌ METABASE_API_KEY env var is missing.");
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length < 1) {
  console.error("Usage: node capture_dashboard.js <dashboard_id> [output_file.md]");
  process.exit(1);
}

const DASHBOARD_ID = parseInt(args[0]);
const OUTPUT_FILE = args[1] || null;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function jsonBlock(tag, obj) {
  const json = JSON.stringify(obj, null, 2);
  return "```json " + tag + "\n" + json + "\n```";
}

function sqlBlock(sql) {
  return "```sql\n" + sql + "\n```";
}

/**
 * Extract the native SQL from various Metabase query formats.
 */
function extractSQL(datasetQuery) {
  if (!datasetQuery) return null;

  // Classic format: { type: "native", native: { query: "..." } }
  if (datasetQuery.type === "native" && datasetQuery.native) {
    return datasetQuery.native.query || null;
  }

  // pMBQL format: { stages: [{ "lib/type": "mbql.stage/native", native: "..." }] }
  if (datasetQuery.stages && Array.isArray(datasetQuery.stages)) {
    for (const stage of datasetQuery.stages) {
      if (stage["lib/type"] === "mbql.stage/native" && stage.native) {
        return typeof stage.native === "string" ? stage.native : null;
      }
    }
  }

  return null;
}

/**
 * Build clean viz settings object from card + dashcard overrides.
 * Dashcard viz settings override card-level ones.
 * Output format matches what deploy_from_markdown expects:
 *   { "display": "scalar", "visualization_settings": { ... } }
 */
function buildVizSettings(card, dashcard) {
  const cardViz = card.visualization_settings || {};
  const dcViz = dashcard.visualization_settings || {};

  // Unwrap nested visualization_settings if present
  // (deploy script sometimes saves viz settings inside a "visualization_settings" key)
  const unwrap = (obj) => {
    if (obj.visualization_settings && typeof obj.visualization_settings === "object" && !Array.isArray(obj.visualization_settings)) {
      return { ...obj, ...obj.visualization_settings, visualization_settings: undefined };
    }
    return obj;
  };

  // Merge: dashcard overrides card-level settings
  const merged = { ...unwrap(cardViz), ...unwrap(dcViz) };

  // Remove redundant keys that are top-level in our format
  delete merged.display;
  delete merged.visualization_settings;

  // Build output
  const result = { display: card.display || "table" };

  // Only include visualization_settings if there are meaningful settings
  const cleanKeys = Object.keys(merged).filter(
    (k) => !["virtual_card", "card.title", "card.description"].includes(k)
  );
  if (cleanKeys.length > 0) {
    const clean = {};
    for (const k of cleanKeys) clean[k] = merged[k];
    result.visualization_settings = clean;
  }

  return result;
}

/**
 * Build position object from dashcard.
 */
function buildPosition(dashcard) {
  return {
    row: dashcard.row || 0,
    col: dashcard.col || 0,
    size_x: dashcard.size_x || 4,
    size_y: dashcard.size_y || 4,
  };
}

/**
 * Get collection path string from collection ancestors.
 */
async function getCollectionPath(client, collectionId) {
  if (!collectionId) return "Root";
  try {
    const col = await client.core.request(`/api/collection/${collectionId}`);
    const ancestors = col.effective_ancestors || [];
    const parts = [...ancestors.map((a) => a.name), col.name];
    return parts.join(" > ");
  } catch (e) {
    return "Unknown";
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

(async () => {
  try {
    const client = new MetabaseClient(METABASE_URL, API_KEY);
    await client.connect();
    console.error(`✅ Connected to Metabase`);

    // Fetch dashboard
    const dash = await client.core.request(`/api/dashboard/${DASHBOARD_ID}`);
    const dashcards = dash.dashcards || dash.ordered_cards || [];
    const tabs = dash.tabs || [];
    const params = dash.parameters || [];
    const collectionPath = await getCollectionPath(client, dash.collection_id);

    console.error(`📊 Dashboard: ${dash.name} (ID: ${DASHBOARD_ID})`);
    console.error(`📁 Collection: ${collectionPath}`);
    console.error(`📑 Tabs: ${tabs.length || "none"}`);
    console.error(`🃏 Cards: ${dashcards.length}`);

    // Fetch full card details for each dashcard
    const cardCache = {};
    for (const dc of dashcards) {
      if (dc.card_id && !cardCache[dc.card_id]) {
        try {
          cardCache[dc.card_id] = await client.core.request(`/api/card/${dc.card_id}`);
        } catch (e) {
          console.error(`⚠️ Could not fetch card ${dc.card_id}: ${e.message}`);
        }
      }
    }

    // ---------------------------------------------------------------------------
    // Generate Markdown
    // ---------------------------------------------------------------------------
    const lines = [];

    lines.push(`# 📘 Blueprint: ${dash.name}`);
    lines.push("");
    lines.push(`> **Target Collection:** \`${collectionPath}\``);
    lines.push(`> **Captured from:** Metabase Dashboard ID ${DASHBOARD_ID}`);
    lines.push(`> **Captured at:** ${new Date().toISOString().split("T")[0]}`);
    lines.push("");
    lines.push(`## 📂 Collection: ${collectionPath}`);
    lines.push("");
    lines.push(dash.description || "");
    lines.push("");
    lines.push("---");
    lines.push("");
    lines.push(`### 🖥️ Dashboard: ${dash.name}`);
    lines.push("");
    if (dash.description) {
      lines.push(`**Description**: ${dash.description}`);
      lines.push("");
    }

    // Parameters
    if (params.length > 0) {
      for (const p of params) {
        lines.push(`#### Filter: ${p.name}`);
        lines.push("");
        lines.push(jsonBlock("metabase-filter", {
          name: p.name,
          slug: p.slug,
          type: p.type,
          default: p.default || null,
        }));
        lines.push("");
      }
      lines.push("---");
      lines.push("");
    }

    // Group cards by tab
    const tabGroups = [];
    if (tabs.length > 0) {
      for (const tab of tabs) {
        const tabCards = dashcards
          .filter((dc) => dc.dashboard_tab_id === tab.id)
          .sort((a, b) => a.row - b.row || a.col - b.col);
        tabGroups.push({ name: tab.name, cards: tabCards });
      }
    } else {
      // No tabs — all cards in one group
      const sorted = [...dashcards].sort((a, b) => a.row - b.row || a.col - b.col);
      tabGroups.push({ name: null, cards: sorted });
    }

    // Render each tab/group
    for (const group of tabGroups) {
      if (group.name) {
        lines.push(`### 📑 Tab: ${group.name}`);
        lines.push("");
      }

      let lastRow = -1;
      for (const dc of group.cards) {
        const card = cardCache[dc.card_id];
        if (!card) continue;

        const sql = extractSQL(card.dataset_query);
        if (!sql) {
          console.error(`⚠️ Skipping non-SQL card: ${card.name} (ID: ${dc.card_id})`);
          continue;
        }

        // Add separator between row groups
        const pos = buildPosition(dc);
        if (lastRow >= 0 && pos.row > lastRow + 1) {
          lines.push("---");
          lines.push("");
        }
        lastRow = pos.row;

        // Question header
        lines.push(`#### ❓ Question: ${card.name}`);
        lines.push("");

        // Description (if any)
        if (card.description) {
          lines.push(card.description);
          lines.push("");
        }

        // SQL
        lines.push(sqlBlock(sql));
        lines.push("");

        // Viz settings
        const viz = buildVizSettings(card, dc);
        lines.push(jsonBlock("metabase-viz", viz));
        lines.push("");

        // Position
        lines.push(jsonBlock("metabase-pos", pos));
        lines.push("");
      }

      if (group.name) {
        lines.push("---");
        lines.push("");
      }
    }

    // ---------------------------------------------------------------------------
    // Output
    // ---------------------------------------------------------------------------
    const markdown = lines.join("\n");

    if (OUTPUT_FILE) {
      const outDir = path.dirname(OUTPUT_FILE);
      if (outDir && !fs.existsSync(outDir)) {
        fs.mkdirSync(outDir, { recursive: true });
      }
      fs.writeFileSync(OUTPUT_FILE, markdown, "utf8");
      console.error(`✅ Blueprint written to: ${OUTPUT_FILE}`);
    } else {
      process.stdout.write(markdown);
    }

    console.error(`\n🚀 Capture Complete.`);
  } catch (e) {
    console.error(`❌ Error: ${e.message}`);
    process.exit(1);
  }
})();
