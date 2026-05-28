#!/usr/bin/env node
/**
 * Rollback: Remove text widgets added by add-date-range-widgets.js that don't
 * conform to skill standard (Chu kỳ báo cáo must be SQL scalar, not text card).
 *
 * Detection: text dashcards whose content starts with "📅 **", "🔍 **Cơ chế filter",
 *            "📍 **Onboarding" — markers from add-date-range-widgets.js
 *
 * Strategy: Fetch each dashboard, filter dashcards array to drop matching widgets,
 *           PUT back (with tabs payload to preserve FK refs).
 */

const URL = process.env.METABASE_URL || "http://127.0.0.1:3001";
const KEY = process.env.METABASE_API_KEY;
if (!KEY) { console.error("METABASE_API_KEY required"); process.exit(1); }

// All dashboard IDs from add-date-range-widgets.js TOP_HINTS map
const DASHBOARD_IDS = [73, 43, 44, 31, 34, 35, 36, 33, 15, 30, 32, 38, 26, 27, 41, 42, 40, 28, 51, 8, 9, 49, 50, 13, 14, 37, 47, 46, 48, 74, 75, 76, 77, 78];

function isWrongWidget(dc) {
  if (dc.card_id) return false; // skip real questions
  const text = (dc.visualization_settings?.text || "").trim();
  return text.startsWith("📅 **") ||
         text.startsWith("🔍 **Cơ chế filter") ||
         text.startsWith("📍 **Onboarding");
}

function preserveDashcard(dc) {
  return {
    id: dc.id,
    dashboard_tab_id: dc.dashboard_tab_id,
    card_id: dc.card_id || null,
    row: dc.row,
    col: dc.col,
    size_x: dc.size_x,
    size_y: dc.size_y,
    visualization_settings: dc.visualization_settings || {},
    parameter_mappings: dc.parameter_mappings || [],
    series: dc.series || [],
    inline_parameters: dc.inline_parameters || []
  };
}

async function processDashboard(id) {
  const res = await fetch(`${URL}/api/dashboard/${id}`, {
    headers: {"x-api-key": KEY}
  });
  const d = await res.json();
  if (d.archived) { console.log(`[${id}] SKIP archived`); return; }

  const dashcards = d.dashcards || [];
  const wrongWidgets = dashcards.filter(isWrongWidget);
  if (wrongWidgets.length === 0) {
    console.log(`[${id}] ${d.name} — no wrong widgets`);
    return;
  }

  const keep = dashcards.filter(dc => !isWrongWidget(dc)).map(preserveDashcard);
  const tabs = (d.tabs || []).map(t => ({id: t.id, name: t.name, position: t.position}));

  const body = {dashcards: keep};
  if (tabs.length > 0) body.tabs = tabs;

  const putRes = await fetch(`${URL}/api/dashboard/${id}`, {
    method: "PUT",
    headers: {"x-api-key": KEY, "Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  if (putRes.ok) {
    console.log(`[${id}] ${d.name} ✓ removed ${wrongWidgets.length} widgets (was ${dashcards.length}, now ${keep.length})`);
  } else {
    const err = await putRes.text();
    console.log(`[${id}] ${d.name} ✗ HTTP ${putRes.status}: ${err.slice(0, 200)}`);
  }
}

async function main() {
  console.log(`Rollback ${DASHBOARD_IDS.length} dashboards...\n`);
  for (const id of DASHBOARD_IDS) {
    await processDashboard(id);
    await new Promise(r => setTimeout(r, 150));
  }
  console.log("\nDone.");
}

main().catch(e => { console.error(e); process.exit(1); });
