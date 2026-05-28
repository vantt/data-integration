#!/usr/bin/env node
/**
 * Apply skill-compliant per-tab widgets:
 *   - Chu kỳ báo cáo: SQL Question display=scalar, row 0, size_x 18, size_y 2
 *   - Source & Freshness: Text card, last row, size_x 18, size_y 1
 *
 * Per skill (.skills/metabase-automation/templates/blueprint_template.md §"Tab Structure Standards")
 *
 * Idempotency: text-id markers on text cards; SQL Question matched by name "Chu kỳ báo cáo".
 *
 * Reads: plans/260527-1327-metabase-collection-restructure/audit-report.json
 */

const URL = process.env.METABASE_URL || "http://127.0.0.1:3001";
const KEY = process.env.METABASE_API_KEY;
const DB_ID = parseInt(process.env.METABASE_DB_ID || "2", 10);
if (!KEY) { console.error("METABASE_API_KEY required"); process.exit(1); }

const fs = require("fs");
const audit = JSON.parse(fs.readFileSync("plans/260527-1327-metabase-collection-restructure/audit-report.json", "utf8"));

// Per-dashboard cadence + source metadata (manually curated)
const META = {
  73: { cadence: "none", source: "(text only)", scope: "All users", caveats: "" },
  43: { cadence: "weekly", source: "fact_orders + fact_order_economics", scope: "is_sales_channel=true, exclude CANCELLED/Voided", caveats: "has_cogs=~65% coverage" },
  44: { cadence: "monthly", source: "fact_orders + fact_order_economics + fact_order_costs", scope: "is_sales_channel=true", caveats: "" },
  31: { cadence: "monthly", source: "fact_orders + fact_order_economics", scope: "is_sales_channel=true, exclude CANCELLED/Voided", caveats: "" },
  34: { cadence: "monthly", source: "fact_orders + int_misa_sales_lines", scope: "is_sales_channel=true", caveats: "MISA COGS coverage ~65%" },
  35: { cadence: "custom", source: "fact_order_economics", scope: "has_cogs, status=COMPLETED, is_sales_channel", caveats: "Period filter parametric" },
  36: { cadence: "rolling-30d", source: "int_misa_sales_lines", scope: "NOT is_promo_line", caveats: "SKU-level COGS" },
  33: { cadence: "monthly", source: "fact_order_economics + dim_channels", scope: "is_sales_channel + has_cogs", caveats: "MISA coverage gap" },
  15: { cadence: "monthly", source: "dim_customers + fact_orders", scope: "customer_type='RETAIL'", caveats: "" },
  30: { cadence: "rolling-30d", source: "int_misa_sales_lines + fact_sales", scope: "NOT is_promo_line", caveats: "" },
  32: { cadence: "payout-period", source: "int_shopee_order_fees", scope: "payout_released_at IS NOT NULL", caveats: "Shopee fee data only" },
  38: { cadence: "single-order", source: "fact_orders + fact_order_items", scope: "selected order_code", caveats: "Single order detail" },
  26: { cadence: "rolling-30d", source: "fact_orders + dim_*", scope: "Period filter", caveats: "" },
  27: { cadence: "daily", source: "fact_orders", scope: "channel_format='Social'", caveats: "" },
  41: { cadence: "daily", source: "fact_orders + dim_customers", scope: "customer_type='RETAIL'", caveats: "Today only" },
  42: { cadence: "yesterday", source: "fact_orders + dim_customers", scope: "customer_type='RETAIL'", caveats: "Yesterday only" },
  40: { cadence: "rolling-7d", source: "dagster_run_logs", scope: "Pipeline runs", caveats: "Internal monitoring" },
  28: { cadence: "daily", source: "fact_orders + dim_logistics", scope: "Active fulfillment", caveats: "Realtime + 7d trend" },
  51: { cadence: "daily", source: "fact_orders", scope: "channel='US CrossBorder'", caveats: "Export arrangement" },
  8: { cadence: "weekly", source: "fact_orders + fact_order_economics", scope: "customer_type='RETAIL'", caveats: "" },
  9: { cadence: "monthly", source: "fact_orders + fact_order_economics", scope: "customer_type='RETAIL'", caveats: "" },
  49: { cadence: "daily", source: "fact_orders + dim_customers", scope: "customer_type IN ('WHOLESALE','PARTNER')", caveats: "" },
  50: { cadence: "rolling-30d", source: "fact_orders + dim_customers", scope: "customer_type IN ('WHOLESALE','PARTNER')", caveats: "AR aging window" },
  13: { cadence: "monthly", source: "fact_orders + fact_marketing_spend + fact_order_economics", scope: "customer_type='RETAIL'", caveats: "ROAS attribution last-click" },
  14: { cadence: "monthly-cohort", source: "fact_orders + dim_customers", scope: "customer_type='RETAIL'", caveats: "Cohort rolling" },
  37: { cadence: "rolling-30d", source: "fact_marketing_spend + fact_order_economics", scope: "customer_type='RETAIL'", caveats: "" },
  47: { cadence: "weekly", source: "fact_orders + fact_order_economics", scope: "customer_type='RETAIL'", caveats: "" },
  46: { cadence: "rolling-30d", source: "fact_orders + dim_promotions", scope: "customer_type='RETAIL'", caveats: "Baseline = non-promo same-channel-period" },
  48: { cadence: "rolling-30d", source: "fact_orders + dim_customers", scope: "customer_type='RETAIL'", caveats: "MAU window" },
  74: { cadence: "monthly", source: "fact_order_costs", scope: "is_sales_channel=true", caveats: "Long-format cost ledger" },
  75: { cadence: "rolling-90d", source: "fact_order_returns + fact_orders", scope: "is_sales_channel=true", caveats: "Return events, refund recognition" },
  76: { cadence: "rolling-30d", source: "int_misa_sales_lines", scope: "NOT is_promo_line", caveats: "SKU-level margin" },
  77: { cadence: "custom", source: "fact_order_economics + int_misa_sales_lines", scope: "has_cogs, is_sales_channel", caveats: "Period filter parametric" },
  78: { cadence: "rolling-30d", source: "fact_order_economics", scope: "has_cogs proxy for recon", caveats: "Recon mart not yet built — using proxy" }
};

// Cadence → SQL template for Chu kỳ báo cáo
function buildChuKySQL(cadence) {
  switch (cadence) {
    case "daily": return `SELECT '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') || '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "yesterday": return `SELECT '📅 Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') || '  ·  Hôm kia: ' || strftime(current_date - 2, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "weekly": return `SELECT '📅 Tuần này: ' || strftime((date_trunc('week', current_date))::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  WoW: ' || strftime((date_trunc('week', current_date) - INTERVAL '7 days')::DATE, '%d/%m/%Y') || ' – ' || strftime((date_trunc('week', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "monthly": return `SELECT '📅 Tháng này: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') || '  ·  MoM: ' || strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' || strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "monthly-cohort": return `SELECT '📅 Cohort tháng: ' || strftime(date_trunc('month', current_date)::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "rolling-30d": return `SELECT '📅 30 ngày gần nhất: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "rolling-7d": return `SELECT '📅 7 ngày gần nhất: ' || strftime((current_date - INTERVAL '7 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "rolling-90d": return `SELECT '📅 90 ngày gần nhất: ' || strftime((current_date - INTERVAL '90 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "payout-period": return `SELECT '📅 Kỳ payout Shopee 30 ngày: ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    case "single-order": return `SELECT '📅 Chi tiết đơn hàng — chọn order_code ở filter' AS "Chu kỳ báo cáo"`;
    case "custom": return `SELECT '📅 Period filter ở đầu — mặc định ' || strftime((current_date - INTERVAL '30 days')::DATE, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') AS "Chu kỳ báo cáo"`;
    default: return `SELECT '📅 Phạm vi thay đổi theo filter — xem playbook' AS "Chu kỳ báo cáo"`;
  }
}

function buildSourceFreshnessText(meta) {
  const parts = [
    `**Source:** ${meta.source}`,
    `**Cadence:** ${meta.cadence}`,
    `**Scope:** ${meta.scope}`
  ];
  if (meta.caveats) parts.push(`**Caveats:** ${meta.caveats}`);
  return parts.join(" · ") + "\n<!-- text-id:source-freshness -->";
}

function preserveDashcard(dc) {
  return {
    id: dc.id, dashboard_tab_id: dc.dashboard_tab_id, card_id: dc.card_id||null,
    row: dc.row, col: dc.col, size_x: dc.size_x, size_y: dc.size_y,
    visualization_settings: dc.visualization_settings||{},
    parameter_mappings: dc.parameter_mappings||[],
    series: dc.series||[],
    inline_parameters: dc.inline_parameters||[]
  };
}

async function api(path, opts={}) {
  const res = await fetch(`${URL}${path}`, {
    ...opts,
    headers: {"x-api-key": KEY, "Content-Type": "application/json", ...(opts.headers||{})}
  });
  return res;
}

async function createCard(name, sql, collectionId) {
  const body = {
    name,
    description: "Auto-added per tab standard (.skills/metabase-automation/templates/blueprint_template.md)",
    dataset_query: { type: "native", native: { query: sql }, database: DB_ID },
    display: "scalar",
    visualization_settings: { "card.title": "", "dashcard.background": false },
    collection_id: collectionId,
    type: "question"
  };
  const res = await api("/api/card", { method: "POST", body: JSON.stringify(body) });
  return res.json();
}

async function processDashboard(report) {
  const meta = META[report.id];
  if (!meta) { console.log(`[${report.id}] no META, skip`); return; }
  if (meta.cadence === "none") { console.log(`[${report.id}] cadence=none, skip`); return; }

  // Fetch fresh
  const dRes = await api(`/api/dashboard/${report.id}`);
  const d = await dRes.json();
  if (d.archived) return;

  const dashcards = (d.dashcards||[]).map(preserveDashcard);
  const tabs = d.tabs || [];
  const tabList = tabs.length > 0 ? tabs : [{id:null,name:"(no tabs)"}];

  let added = 0;

  for (const tab of tabList) {
    const tabCards = dashcards.filter(dc => dc.dashboard_tab_id === tab.id);
    // Check existing
    const hasChuKy = tabCards.some(dc => {
      if (!dc.card_id) return false;
      // We don't have card name in dashcard object after preserveDashcard, lookup via full dashboard data
      const full = (d.dashcards||[]).find(x => x.id === dc.id);
      return full?.card?.name?.toLowerCase().includes("chu kỳ báo cáo") ||
             full?.card?.name?.toLowerCase().includes("chu ky bao cao");
    });
    const hasSource = tabCards.some(dc => {
      const t = (dc.visualization_settings?.text || "").toLowerCase();
      return t.startsWith("**source:**") || t.includes("<!-- text-id:source-freshness -->");
    });

    if (!hasChuKy) {
      // Shift existing cards on this tab down by 2 rows
      tabCards.forEach(tc => {
        const original = dashcards.find(dc => dc.id === tc.id);
        if (original) original.row += 2;
      });

      // Create Chu kỳ báo cáo card
      const cardName = tab.id ? `Chu kỳ báo cáo · ${tab.name}` : `Chu kỳ báo cáo`;
      const sql = buildChuKySQL(meta.cadence);
      const card = await createCard(cardName, sql, d.collection_id);
      if (!card.id) {
        console.log(`[${report.id}] tab="${tab.name}" ✗ failed to create card: ${JSON.stringify(card).slice(0,200)}`);
        continue;
      }
      dashcards.push({
        id: -1 * (added + 1),
        dashboard_tab_id: tab.id,
        card_id: card.id,
        row: 0, col: 0, size_x: 18, size_y: 2,
        visualization_settings: { "card.title":"", "dashcard.background":false },
        parameter_mappings: [], series: [], inline_parameters: []
      });
      added++;
      console.log(`  tab="${tab.name}" + Chu kỳ báo cáo (card ${card.id})`);
    }

    if (!hasSource) {
      // Find max row on this tab (after potential shift)
      const updatedTabCards = dashcards.filter(dc => dc.dashboard_tab_id === tab.id);
      const maxRow = updatedTabCards.reduce((m, dc) => Math.max(m, dc.row + (dc.size_y||0)), 2);
      const text = buildSourceFreshnessText(meta);
      dashcards.push({
        id: -1 * (added + 100),
        dashboard_tab_id: tab.id,
        card_id: null,
        row: maxRow, col: 0, size_x: 18, size_y: 1,
        visualization_settings: {
          "virtual_card": {"name":null,"display":"text","visualization_settings":{},"dataset_query":{},"archived":false},
          "text": text,
          "dashcard.background": false,
          "text.align_vertical": "top"
        },
        parameter_mappings: [], series: [], inline_parameters: []
      });
      added++;
      console.log(`  tab="${tab.name}" + Source & Freshness`);
    }
  }

  if (added === 0) { console.log(`[${report.id}] ${d.name} — already compliant`); return; }

  // PUT updated dashboard
  const tabsPayload = tabs.map(t => ({id: t.id, name: t.name, position: t.position}));
  const body = { dashcards };
  if (tabsPayload.length > 0) body.tabs = tabsPayload;
  const putRes = await api(`/api/dashboard/${report.id}`, { method: "PUT", body: JSON.stringify(body) });
  if (putRes.ok) {
    console.log(`[${report.id}] ${d.name} ✓ +${added} widgets`);
  } else {
    const err = await putRes.text();
    console.log(`[${report.id}] ${d.name} ✗ HTTP ${putRes.status}: ${err.slice(0,200)}`);
  }
}

async function main() {
  console.log(`Processing ${audit.length} dashboards...\n`);
  for (const r of audit) {
    await processDashboard(r);
    await new Promise(res => setTimeout(res, 200));
  }
  console.log("\nDone.");
}

main().catch(e => { console.error(e); process.exit(1); });
