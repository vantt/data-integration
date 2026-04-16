const MetabaseClient = require("./metabase_client");
const parseMarkdownConfig = require("../lib/markdown_parser");
const { slugify, injectTextId } = require("../lib/text-card-helpers");
const path = require("path");
const fs = require("fs");

/**
 * Literate Deployment Script
 * Usage: node deploy_from_markdown.js <path-to-docs.md> [--dry-run]
 */

/**
 * Flatten a viz block from the blueprint into Metabase's expected format.
 * Blueprints may nest settings under "visualization_settings" for readability,
 * but Metabase expects them flat at the top level.
 * Also strips "display" since it's a separate card property, not a viz setting.
 */
/**
 * Auto-detect {{variable}} placeholders in SQL and build Metabase template-tags.
 * Maps common variable names to appropriate types (date, number, text).
 */
function buildTemplateTags(sql) {
  const tags = {};
  const regex = /\{\{(\w+)\}\}/g;
  let match;
  while ((match = regex.exec(sql)) !== null) {
    const name = match[1];
    if (tags[name]) continue;
    // Infer type from name
    let type = 'text';
    if (/date|day|month|year|start|end|from|to/i.test(name)) type = 'date';
    else if (/id|count|num|amount|limit|offset/i.test(name)) type = 'number';
    tags[name] = {
      id: name,
      name: name,
      'display-name': name.charAt(0).toUpperCase() + name.slice(1).replace(/_/g, ' '),
      type: type
    };
  }
  return tags;
}

function flattenViz(viz) {
  if (!viz) return {};
  const { display, visualization_settings, ...rest } = viz;
  const merged = visualization_settings && typeof visualization_settings === 'object'
    ? { ...rest, ...visualization_settings }
    : rest;
  // Transform column_settings keys from plain names to Metabase's ["name","X"] format
  if (merged.column_settings && typeof merged.column_settings === 'object') {
    const transformed = {};
    for (const [key, value] of Object.entries(merged.column_settings)) {
      // If key is already in JSON array format, keep it; otherwise wrap it
      const newKey = key.startsWith('[') ? key : JSON.stringify(["name", key]);
      transformed[newKey] = value;
    }
    merged.column_settings = transformed;
  }
  return merged;
}

async function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes("--dry-run");
  const filePath = args.find((a) => !a.startsWith("--"));

  if (!filePath) {
    console.error(
      "Usage: node deploy_from_markdown.js <path-to-docs.md> [--dry-run]",
    );
    process.exit(1);
  }

  if (dryRun) {
    console.log("🔍 DRY RUN — no changes will be made to Metabase.");
  }

  const absPath = path.resolve(process.cwd(), filePath);
  if (!fs.existsSync(absPath)) {
    console.error(`File not found: ${absPath}`);
    process.exit(1);
  }

  console.log(`📖 Parsing blueprint: ${path.basename(absPath)}`);
  const config = parseMarkdownConfig(absPath);

  // 2. Auth (Shared with deploy_from_config)
  const METABASE_URL = process.env.METABASE_URL;
  const sessionToken =
    process.env.METABASE_SESSION_ID || process.env.METABASE_SESSION_TOKEN;
  const apiKey = process.env.METABASE_API_KEY;

  if (!METABASE_URL) {
    console.error("❌ METABASE_URL env var is missing.");
    process.exit(1);
  }

  let client;
  if (sessionToken) {
    client = new MetabaseClient(METABASE_URL, sessionToken, {
      authHeader: "X-Metabase-Session",
    });
  } else if (apiKey) {
    client = new MetabaseClient(METABASE_URL, apiKey);
  } else {
    console.error(
      "❌ No Auth Token/Key found (METABASE_SESSION_ID or METABASE_API_KEY).",
    );
    process.exit(1);
  }

  try {
    if (!(await client.connect())) throw new Error("Connection failed");
    console.log("✅ Metabase Connected");
  } catch (e) {
    console.error(`❌ Connection Error: ${e.message}`);
    process.exit(1);
  }

  // 3. Execution

  // Resolve target database: blueprint > env var > fallback
  const dbName = config.database || process.env.METABASE_DB_NAME || "Sapo DuckDB";
  const defaultDbId = await client.findDatabaseId(dbName);
  if (!defaultDbId) {
    console.error("❌ Could not find target Database. Set METABASE_DB_NAME.");
    process.exit(1);
  }

  // A. Collections (supports nested paths via "parent" field from parser)
  const colMap = {}; // name -> id
  for (const col of config.collections) {
    const parentId = col.parent ? colMap[col.parent] || null : null;
    const pathLabel = col.parent ? `${col.parent} > ${col.name}` : col.name;
    if (dryRun) {
      console.log(`📂 [DRY] Would ensure Collection: ${pathLabel}`);
      colMap[col.name] = -1; // placeholder
    } else {
      console.log(`📂 Ensuring Collection: ${pathLabel}`);
      const remote = await client.collection.ensure(col.name, { parent_id: parentId });
      colMap[col.name] = remote.id;
    }
  }

  // B. Models & Metrics
  for (const col of config.collections) {
    if (!col.models) continue;
    for (const model of col.models) {
      console.log(`🧊 Ensuring Model: ${model.name}`);

      if (!model.sql) {
        console.warn(`⚠️ Skipping model '${model.name}': No SQL found.`);
        continue;
      }

      // Ensure Model (Dataset)
      if (dryRun) {
        console.log(`🧊 [DRY] Would ensure Model: ${model.name}`);
      } else {
        await client.model.ensure(
          model.name,
          model.sql,
          defaultDbId,
          colMap[col.name],
          {
            description: model.metadata ? model.metadata.description : null,
            visualization_settings: model.metadata || {},
          },
        );
      }

      // Metrics (Experimental)
      if (model.metrics && model.metrics.length > 0) {
        console.warn(
          `⚠️ Metrics for '${model.name}' found but Metric deployment from Markdown is experimental.`,
        );
      }
    }
  }

  // C. Dashboards & Questions
  // We iterate collections because hierarchies might be cleaner,
  // but the parser gave us a flat list of dashboards too?
  // Actually parser attached questions to dashboards.

  for (const dashboard of config.dashboards) {
    const colId = colMap[dashboard.collection_name];
    console.log(`🖥️  Ensuring Dashboard: ${dashboard.name}`);
    // Build dashboard-level parameters from parsed filters
    const dashParams = (dashboard.filters || []).map(f => ({
      id: f.id || f.slug,
      name: f.name,
      slug: f.slug,
      type: f.type || 'date/all-options',
      default: f.default || null,
      sectionId: f.sectionId || undefined,
    }));

    if (dryRun) {
      console.log(`🖥️  [DRY] Would ensure Dashboard: ${dashboard.name} (${dashboard.questions.length} questions, ${(dashboard.textCards || []).length} text cards)`);
      if (dashParams.length > 0) {
        console.log(`🔍 [DRY] Would sync ${dashParams.length} filter(s): ${dashParams.map(p => p.name).join(', ')}`);
      }
      for (const q of dashboard.questions) {
        console.log(`   [DRY] Question: ${q.name} (display: ${q.viz?.display || 'table'})${q.tab ? ` [tab: ${q.tab}]` : ''}`);
      }
      for (const tc of (dashboard.textCards || [])) {
        console.log(`   [DRY] Text: "${tc.name}"${tc.tab ? ` [tab: ${tc.tab}]` : ''}`);
      }
      continue;
    }

    const dashRemote = await client.dashboard.ensure(dashboard.name, "", colId, dashParams);

    // If filters exist and dashboard was pre-existing, update parameters via PUT
    if (dashParams.length > 0) {
      console.log(`🔍 Syncing ${dashParams.length} filter(s): ${dashParams.map(p => p.name).join(', ')}`);
      await client.core.request(`/api/dashboard/${dashRemote.id}`, 'PUT', {
        parameters: dashParams
      });
    }

    // Fetch existing dashboard cards to scope updates by dashboard (not just collection)
    const dashDetail = await client.core.request(`/api/dashboard/${dashRemote.id}`);
    const existingDashCards = dashDetail.dashcards || dashDetail.ordered_cards || [];
    const existingTabs = dashDetail.tabs || [];

    // Build tab ID lookup from existing dashboard tabs
    const existingTabIdByName = {};
    for (const t of existingTabs) {
      existingTabIdByName[t.name] = t.id;
    }

    // Build dashcard map scoped by (tab_id, card_name) for tab-aware lookup
    // Each dashcard entry includes the card object AND the dashcard's tab assignment
    const dashCardByTabAndName = {}; // "tabId::name" -> { card, dashcard }
    const dashCardByName = {};       // "name" -> { card, dashcard } (fallback for non-tabbed)
    const usedCardIds = new Set();   // track card IDs already claimed
    for (const dc of existingDashCards) {
      if (dc.card && dc.card.name) {
        const key = `${dc.dashboard_tab_id || ''}::${dc.card.name}`;
        dashCardByTabAndName[key] = { card: dc.card, dashcard: dc };
        if (!dashCardByName[dc.card.name]) {
          dashCardByName[dc.card.name] = { card: dc.card, dashcard: dc };
        }
      }
    }

    const tabNames = dashboard.tabs || [];
    if (tabNames.length > 0) {
      console.log(`📑 Dashboard has ${tabNames.length} tab(s): ${tabNames.join(', ')}`);
    }

    const cardConfigs = [];

    // Process Questions — tab-aware: each tab gets its own card
    for (const q of dashboard.questions) {
      if (!q.sql) {
        console.warn(`⚠️ Skipping question '${q.name}': No SQL found.`);
        continue;
      }

      // Resolve existing card scoped by tab
      const tabId = q.tab ? (existingTabIdByName[q.tab] || null) : null;
      const scopedKey = `${tabId || ''}::${q.name}`;
      const existing = dashCardByTabAndName[scopedKey];
      const existingCard = existing && !usedCardIds.has(existing.card.id) ? existing.card : null;
      if (existingCard) usedCardIds.add(existingCard.id);

      let card;
      if (existingCard) {
        // Update existing card already on this dashboard tab
        console.log(`ℹ️ Question '${q.name}' exists on tab '${q.tab || '-'}' (ID: ${existingCard.id})`);
        try {
          await client.core.request(`/api/card/${existingCard.id}`, 'PUT', { archived: false });
        } catch (e) { /* ignore */ }

        card = await client.core.request(`/api/card/${existingCard.id}`, 'PUT', {
          name: q.name,
          collection_id: colId,
          dataset_query: {
            type: "native",
            native: { query: q.sql, "template-tags": buildTemplateTags(q.sql) },
            database: defaultDbId
          },
          display: q.viz ? q.viz.display : "table",
          visualization_settings: flattenViz(q.viz)
        });
        console.log(`✅ Updated Question '${q.name}' (ID: ${card.id})`);
      } else {
        // Create new card for this tab
        const payload = {
          name: q.name,
          collection_id: colId,
          dataset_query: {
            type: "native",
            native: { query: q.sql, "template-tags": buildTemplateTags(q.sql) },
            database: defaultDbId
          },
          display: q.viz ? q.viz.display : "table",
          visualization_settings: flattenViz(q.viz)
        };
        card = await client.core.request('/api/card', 'POST', payload);
        console.log(`✅ Created Question '${q.name}' (ID: ${card.id})`);
      }

      // Prepare for Dashboard Sync
      const pos = q.pos || { row: 0, col: 0, size_x: 4, size_y: 4 };
      const cardConfig = { id: card.id, ...pos };

      // Propagate click_behavior from card viz settings to dashcard level.
      // Metabase stores click_behavior on the dashcard, not the card itself.
      const flatVizSettings = flattenViz(q.viz);
      if (flatVizSettings.column_settings) {
        const clickEntries = {};
        for (const [key, val] of Object.entries(flatVizSettings.column_settings)) {
          if (val && val.click_behavior) {
            clickEntries[key] = { click_behavior: val.click_behavior };
          }
        }
        if (Object.keys(clickEntries).length > 0) {
          cardConfig.visualization_settings = { column_settings: clickEntries };
        }
      }

      // Pass tab name — syncCards will resolve to tab ID
      if (q.tab) {
        cardConfig.tab = q.tab;
      }

      // Auto-wire parameter_mappings: match dashboard filters to SQL template tags
      if (dashParams.length > 0 && q.sql) {
        const templateTags = buildTemplateTags(q.sql);
        const mappings = [];
        for (const param of dashParams) {
          // Match by slug: dashboard filter slug should match SQL {{variable_name}}
          const tagName = Object.keys(templateTags).find(t =>
            t === param.slug || t === param.slug.replace(/-/g, '_')
          );
          if (tagName) {
            mappings.push({
              parameter_id: param.id || param.slug,
              card_id: card.id,
              target: ["variable", ["template-tag", tagName]]
            });
          }
        }
        if (mappings.length > 0) {
          cardConfig.parameter_mappings = mappings;
        }
        // Warn about unmatched filters for this question
        const unmapped = dashParams.filter(p => !mappings.find(m => m.parameter_id === (p.id || p.slug)));
        if (unmapped.length > 0) {
          console.warn(`   ⚠️ '${q.name}': ${unmapped.length} filter(s) not mapped (no matching {{template_tag}}): ${unmapped.map(p => p.slug).join(', ')}`);
        }
      }

      cardConfigs.push(cardConfig);
    }

    // Process Text Cards (section headings, annotations)
    // slugCounts is scoped per-tab to prevent slug shifts when removing/reordering
    // cards in one tab from affecting slugs in other tabs.
    const slugCounts = {}; // key = `${tab}::${slug}` or slug if no tab
    for (const tc of (dashboard.textCards || [])) {
      const pos = tc.pos || { row: 0, col: 0, size_x: 18, size_y: 1 };
      // Build text content with stable identity marker for idempotent redeploy
      const rawText = tc.text || `# ${tc.name}`;
      let slug = slugify(tc.name);
      const scopeKey = tc.tab ? `${tc.tab}::${slug}` : slug;
      slugCounts[scopeKey] = (slugCounts[scopeKey] || 0) + 1;
      if (slugCounts[scopeKey] > 1) slug = `${slug}-${slugCounts[scopeKey]}`;
      const textContent = injectTextId(rawText, slug);
      const textCardConfig = {
        id: null, // null = text card (no backing question)
        ...pos,
        visualization_settings: {
          virtual_card: {
            name: null,
            display: "text",
            visualization_settings: {},
            dataset_query: {},
            archived: false
          },
          text: textContent
        },
        parameter_mappings: []
      };
      if (tc.tab) textCardConfig.tab = tc.tab;
      cardConfigs.push(textCardConfig);
      console.log(`📝 Text card: "${tc.name}" at row ${pos.row}, col ${pos.col}`);
    }

    // Sync to Dashboard (tabs and cards in one PUT)
    if (cardConfigs.length > 0) {
      await client.dashboard.syncCards(dashRemote.id, cardConfigs, tabNames);
    }
  }

  console.log(dryRun ? "🔍 Dry run complete — no changes made." : "🚀 Deployment Complete.");
}

main().catch(console.error);
