/**
 * Patch visualization_settings on specific dashcards without replacing other cards.
 * Usage: node patch-dashcard-viz.js <dashboard_id> <dashcard_id1,dashcard_id2,...> <json_viz_settings>
 */
const MetabaseClient = require("./metabase_client");

const METABASE_URL = process.env.METABASE_URL || "http://127.0.0.1:3001/";
const API_KEY = process.env.METABASE_API_KEY;

async function main() {
  const dashboardId = parseInt(process.argv[2]);
  const targetDashcardIds = process.argv[3].split(",").map(Number);
  // Accept via env var to avoid shell escaping issues: PATCH_VIZ='{"dashcard.background":false}'
  const newVizSettings = JSON.parse(process.env.PATCH_VIZ || process.argv[4] || "{}");

  const client = new MetabaseClient(METABASE_URL, API_KEY);
  await client.connect();

  // GET current dashboard state
  const dashboard = await client.core.request(`/api/dashboard/${dashboardId}`);
  const currentCards = dashboard.dashcards || [];
  const existingTabs = dashboard.tabs || [];
  console.log(`Dashboard "${dashboard.name}" — ${currentCards.length} dashcards, ${existingTabs.length} tabs`);

  // Build dashcard payload: preserve all cards, patch targets
  const dashcards = currentCards.map(dc => {
    const isTarget = targetDashcardIds.includes(dc.id);
    const vizSettings = isTarget
      ? { ...((dc.visualization_settings) || {}), ...newVizSettings }
      : (dc.visualization_settings || {});

    if (isTarget) {
      console.log(`  Patching dashcard ${dc.id} (card ${dc.card_id}): viz=${JSON.stringify(vizSettings)}`);
    }

    return {
      id: dc.id,
      card_id: dc.card_id,
      row: dc.row,
      col: dc.col,
      size_x: dc.size_x,
      size_y: dc.size_y,
      visualization_settings: vizSettings,
      parameter_mappings: dc.parameter_mappings || [],
      series: [],
      ...(dc.dashboard_tab_id != null ? { dashboard_tab_id: dc.dashboard_tab_id } : {}),
    };
  });

  // Build tabs payload (preserve existing tabs)
  const tabs = existingTabs.map(t => ({ id: t.id, name: t.name }));

  const payload = { dashcards, tabs };
  console.log(`Sending PUT /api/dashboard/${dashboardId} with ${dashcards.length} dashcards...`);

  const result = await client.core.request(`/api/dashboard/${dashboardId}`, "PUT", payload);
  const count = (result.dashcards || []).length;
  console.log(`✅ Done — dashboard now has ${count} dashcards`);
}

main().catch(e => { console.error("❌", e.message); process.exit(1); });
