#!/usr/bin/env node
/**
 * Capture a Metabase dashboard and generate/merge a blueprint markdown file.
 *
 * Two modes:
 *   FRESH:  Generate new blueprint from scratch (output file doesn't exist)
 *   MERGE:  Update positions/viz/SQL from Metabase, keep existing prose/metadata
 *           (output file already exists)
 *
 * Usage:
 *   node capture_dashboard.js <dashboard_id> [output_file.md]
 *   node capture_dashboard.js 11                              # prints to stdout (fresh)
 *   node capture_dashboard.js 11 blueprints/ceo_weekly.md     # merge if exists, fresh if not
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
  return "```json " + tag + "\n" + JSON.stringify(obj, null, 2) + "\n```";
}

function sqlBlock(sql) {
  return "```sql\n" + sql + "\n```";
}

function extractSQL(datasetQuery) {
  if (!datasetQuery) return null;
  if (datasetQuery.type === "native" && datasetQuery.native) {
    return datasetQuery.native.query || null;
  }
  if (datasetQuery.stages && Array.isArray(datasetQuery.stages)) {
    for (const stage of datasetQuery.stages) {
      if (stage["lib/type"] === "mbql.stage/native" && stage.native) {
        return typeof stage.native === "string" ? stage.native : null;
      }
    }
  }
  return null;
}

function buildVizSettings(card, dashcard) {
  const cardViz = card.visualization_settings || {};
  const dcViz = dashcard.visualization_settings || {};
  const unwrap = (obj) => {
    if (obj.visualization_settings && typeof obj.visualization_settings === "object" && !Array.isArray(obj.visualization_settings)) {
      return { ...obj, ...obj.visualization_settings, visualization_settings: undefined };
    }
    return obj;
  };
  const merged = { ...unwrap(cardViz), ...unwrap(dcViz) };
  delete merged.display;
  delete merged.visualization_settings;
  const result = { display: card.display || "table" };
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

function buildPosition(dashcard) {
  return {
    row: dashcard.row || 0,
    col: dashcard.col || 0,
    size_x: dashcard.size_x || 4,
    size_y: dashcard.size_y || 4,
  };
}

async function getCollectionPath(client, collectionId) {
  if (!collectionId) return "Root";
  try {
    const col = await client.core.request(`/api/collection/${collectionId}`);
    const ancestors = col.effective_ancestors || [];
    return [...ancestors.map((a) => a.name), col.name].join(" > ");
  } catch (e) {
    return "Unknown";
  }
}

// ---------------------------------------------------------------------------
// Parse existing blueprint to extract per-question metadata
// ---------------------------------------------------------------------------

/**
 * Parse an existing blueprint and extract metadata that Metabase doesn't store:
 * - File header (everything before the first Question)
 * - Per-question: description lines, domain references, notes
 *
 * Returns:
 *   { header: string, questions: Map<name, { prose: string[] }>, footer: string }
 */
function parseExistingBlueprint(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const lines = content.split("\n");

  const result = {
    header: [],      // lines before the first #### Question
    questions: {},   // name -> { prose: string[] } (lines between header and ```sql)
    tabHeaders: {},  // tab name -> lines for the tab header section
  };

  let section = "header"; // 'header' | 'question-prose' | 'code-block' | 'between'
  let currentQuestion = null;
  let currentTab = null;
  let inCodeBlock = false;
  let headerDone = false;

  for (const line of lines) {
    const trimmed = line.trim();

    // Track code blocks to avoid false matches inside SQL/JSON
    if (trimmed.startsWith("```")) {
      if (inCodeBlock) {
        inCodeBlock = false;
        continue;
      } else {
        inCodeBlock = true;
        continue;
      }
    }
    if (inCodeBlock) continue;

    // Tab header
    const tabMatch = trimmed.match(/^###\s+📑\s+Tab:\s*(.+)/);
    if (tabMatch) {
      currentTab = tabMatch[1].trim();
      continue;
    }

    // Question header
    const qMatch = trimmed.match(/^####\s+(?:❓\s+)?Question:\s*(.+)/);
    if (qMatch) {
      headerDone = true;
      const name = qMatch[1].trim();
      currentQuestion = name;
      result.questions[name] = { prose: [] };
      section = "question-prose";
      continue;
    }

    // Collect lines
    if (!headerDone) {
      result.header.push(line);
    } else if (section === "question-prose" && currentQuestion) {
      // Collect prose lines until we hit a code block or another question
      // (code blocks are skipped above, so these are pure prose lines)
      if (trimmed === "---") {
        // Section separator — keep as-is, not part of question prose
        continue;
      }
      result.questions[currentQuestion].prose.push(line);
    }
  }

  return result;
}

// ---------------------------------------------------------------------------
// Generate: fresh capture (no existing file)
// ---------------------------------------------------------------------------

function generateFresh(dash, tabGroups, cardCache, collectionPath, params) {
  const lines = [];

  lines.push(`# 📘 Blueprint: ${dash.name}`);
  lines.push("");
  lines.push(`> **Target Collection:** \`${collectionPath}\``);
  lines.push(`> **Captured from:** Metabase Dashboard ID ${dash.id}`);
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

  renderParams(lines, params);
  renderTabGroups(lines, tabGroups, cardCache, null);

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Generate: merge with existing file
// ---------------------------------------------------------------------------

function generateMerged(dash, tabGroups, cardCache, existing, params) {
  const lines = [];

  // Keep existing header (everything before first question)
  lines.push(...existing.header);

  // Ensure we have a blank line before questions
  if (lines.length > 0 && lines[lines.length - 1].trim() !== "") {
    lines.push("");
  }

  renderParams(lines, params);
  renderTabGroups(lines, tabGroups, cardCache, existing.questions);

  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Shared rendering
// ---------------------------------------------------------------------------

function renderParams(lines, params) {
  if (params.length > 0) {
    for (const p of params) {
      lines.push(`#### Filter: ${p.name}`);
      lines.push("");
      lines.push(jsonBlock("metabase-filter", {
        name: p.name, slug: p.slug, type: p.type, default: p.default || null,
      }));
      lines.push("");
    }
    lines.push("---");
    lines.push("");
  }
}

function renderTabGroups(lines, tabGroups, cardCache, existingQuestions) {
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

      const pos = buildPosition(dc);
      if (lastRow >= 0 && pos.row > lastRow + 1) {
        lines.push("---");
        lines.push("");
      }
      lastRow = pos.row;

      // Question header
      lines.push(`#### ❓ Question: ${card.name}`);
      lines.push("");

      // Prose: use existing if available, otherwise use card description
      const existingProse = existingQuestions && existingQuestions[card.name];
      if (existingProse && existingProse.prose.length > 0) {
        // Filter out empty trailing lines
        const prose = [...existingProse.prose];
        while (prose.length > 0 && prose[prose.length - 1].trim() === "") prose.pop();
        if (prose.length > 0) {
          lines.push(...prose);
          lines.push("");
        }
      } else if (card.description) {
        lines.push(card.description);
        lines.push("");
      }

      // SQL (always from Metabase — source of truth for actual query)
      lines.push(sqlBlock(sql));
      lines.push("");

      // Viz settings (always from Metabase)
      const viz = buildVizSettings(card, dc);
      lines.push(jsonBlock("metabase-viz", viz));
      lines.push("");

      // Position (always from Metabase)
      lines.push(jsonBlock("metabase-pos", pos));
      lines.push("");
    }

    if (group.name) {
      lines.push("---");
      lines.push("");
    }
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

    // Fetch full card details
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

    // Group cards by tab
    const tabGroups = [];
    if (tabs.length > 0) {
      const tabIds = new Set(tabs.map((t) => t.id));
      for (const tab of tabs) {
        const tabCards = dashcards
          .filter((dc) => dc.dashboard_tab_id === tab.id)
          .sort((a, b) => a.row - b.row || a.col - b.col);
        tabGroups.push({ name: tab.name, cards: tabCards });
      }
      // Warn about orphaned cards (cards not assigned to any tab)
      const orphaned = dashcards.filter((dc) => !dc.dashboard_tab_id || !tabIds.has(dc.dashboard_tab_id));
      if (orphaned.length > 0) {
        console.error(`⚠️ ${orphaned.length} card(s) not assigned to any tab — placing in first tab:`);
        for (const dc of orphaned) {
          const card = cardCache[dc.card_id];
          console.error(`   - ${card ? card.name : `card_id=${dc.card_id}`}`);
        }
        // Add orphaned cards to first tab so they're not lost
        tabGroups[0].cards.push(...orphaned.sort((a, b) => a.row - b.row || a.col - b.col));
      }
    } else {
      const sorted = [...dashcards].sort((a, b) => a.row - b.row || a.col - b.col);
      tabGroups.push({ name: null, cards: sorted });
    }

    // Decide mode: merge or fresh
    let markdown;
    if (OUTPUT_FILE && fs.existsSync(OUTPUT_FILE)) {
      console.error(`📝 Merge mode: existing file found, preserving prose/metadata`);
      const existing = parseExistingBlueprint(OUTPUT_FILE);
      console.error(`   Found ${Object.keys(existing.questions).length} existing question(s) with prose`);
      markdown = generateMerged(dash, tabGroups, cardCache, existing, params);
    } else {
      console.error(`📝 Fresh mode: generating new blueprint`);
      markdown = generateFresh(dash, tabGroups, cardCache, collectionPath, params);
    }

    // Output
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
