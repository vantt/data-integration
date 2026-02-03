const MetabaseClient = require("./metabase_client");
const parseMarkdownConfig = require("../lib/markdown_parser");
const path = require("path");
const fs = require("fs");

/**
 * Literate Deployment Script
 * Usage: node deploy_from_markdown.js <path-to-docs.md> [--dry-run]
 */

async function main() {
  const args = process.argv.slice(2);
  const filePath = args[0];

  if (!filePath || filePath.startsWith("--")) {
    console.error(
      "Usage: node deploy_from_markdown.js <path-to-docs.md> [--dry-run]",
    );
    process.exit(1);
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

  // A. Collections
  const colMap = {}; // name -> id
  for (const col of config.collections) {
    console.log(`📂 Ensuring Collection: ${col.name}`);
    const remote = await client.collection.ensure(col.name);
    colMap[col.name] = remote.id;
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
      // We use the same defaultDbId as Questions for now.
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

  // We need a Database ID for SQL questions.
  // Limitation: The markdown syntax doesn't explicitly state "Which Database".
  // We assume a default DB or we need to look it up.
  // Let's assume the first available DB for now or env var?
  const defaultDbId = await client.findDatabaseId(
    process.env.METABASE_DB_NAME || "Sapo DuckDB",
  );
  if (!defaultDbId) {
    console.error("❌ Could not find target Database. Set METABASE_DB_NAME.");
    process.exit(1);
  }

  for (const dashboard of config.dashboards) {
    const colId = colMap[dashboard.collection_name];
    console.log(`🖥️  Ensuring Dashboard: ${dashboard.name}`);
    const dashRemote = await client.dashboard.ensure(dashboard.name, "", colId);

    const cardConfigs = [];

    // Process Questions
    for (const q of dashboard.questions) {
      if (!q.sql) {
        console.warn(`⚠️ Skipping question '${q.name}': No SQL found.`);
        continue;
      }

      // Create Card
      const card = await client.card.ensure(q.name, q.sql, defaultDbId, colId, {
        display: q.viz ? q.viz.display : "table",
        visualization_settings: q.viz || {},
      });

      // Prepare for Dashboard Sync
      const pos = q.pos || { row: 0, col: 0, size_x: 4, size_y: 4 };
      cardConfigs.push({
        id: card.id,
        ...pos,
      });
    }

    // Sync to Dashboard
    if (cardConfigs.length > 0) {
      await client.dashboard.syncCards(dashRemote.id, cardConfigs);
    }
  }

  console.log("🚀 Deployment Complete.");
}

main().catch(console.error);
