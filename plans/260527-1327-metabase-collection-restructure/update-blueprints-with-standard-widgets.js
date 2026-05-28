#!/usr/bin/env node
/**
 * Inject per-tab widget declarations into blueprints so future deploys preserve them:
 *   - #### ❓ Question: Chu kỳ báo cáo (after each Tab header that lacks it)
 *   - #### 📝 Text: Source & Freshness (at end of each tab section that lacks it)
 *
 * Reads audit-report.json + uses META map. Edits blueprint markdown files.
 * Does NOT re-deploy. User can deploy when convenient.
 */

const fs = require("fs");
const path = require("path");

const audit = JSON.parse(fs.readFileSync("plans/260527-1327-metabase-collection-restructure/audit-report.json", "utf8"));

// Dashboard ID → blueprint path
const BLUEPRINT_MAP = {
  43: "ceo_weekly_pulse",
  44: "ceo_monthly_scorecard",
  31: "sales_monthly_review",
  34: "finance_pl",
  35: "order_profitability_all",
  36: "product_profitability",
  33: "channel_profitability_monthly",
  15: "customer_intelligence_monthly",
  30: "product_performance",
  32: "shopee_channel_economics",
  38: "order_detail",
  26: "order_listing",
  27: "customer_support_social_commerce",
  41: "sales_daily_operation",
  42: "sales_yesterday_operation",
  40: "ingestion_health",
  28: "logistics_operations",
  51: "us_crossborder_operations",
  8: "sales_ops_weekly_review",
  9: "sales_ops_monthly_summary",
  49: "b2b_sales_daily",
  50: "b2b_orders_tracking",
  13: "marketing_monthly_analysis",
  14: "customer_retention_dashboard",
  37: "marketing_roi",
  47: "marketing_weekly_tracker",
  46: "sales_promotion_analysis",
  48: "customer_operational_dashboard",
  74: "finance_cost_ledger",
  75: "finance_return_impact",
  76: "finance_product_cost_margin",
  77: "finance_channel_pl",
  78: "finance_accounting_recon"
};

const META = {
  43: { cadence: "weekly", source: "fact_orders + fact_order_economics", scope: "is_sales_channel=true, exclude CANCELLED/Voided", caveats: "has_cogs ~65% coverage (MISA window)" },
  44: { cadence: "monthly", source: "fact_orders + fact_order_economics + fact_order_costs", scope: "is_sales_channel=true", caveats: "" },
  31: { cadence: "monthly", source: "fact_orders + fact_order_economics", scope: "is_sales_channel=true, exclude CANCELLED/Voided", caveats: "" },
  34: { cadence: "monthly", source: "fact_orders + int_misa_sales_lines", scope: "is_sales_channel=true", caveats: "MISA COGS coverage ~65%" },
  35: { cadence: "custom", source: "fact_order_economics", scope: "has_cogs, status=COMPLETED, is_sales_channel", caveats: "Period filter parametric" },
  36: { cadence: "rolling-30d", source: "int_misa_sales_lines", scope: "NOT is_promo_line", caveats: "SKU-level COGS only" },
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

function buildChuKyBlock(cadence) {
  return `#### ❓ Question: Chu kỳ báo cáo

\`\`\`sql
${buildChuKySQL(cadence)}
\`\`\`

\`\`\`json metabase-viz
{ "display": "scalar", "visualization_settings": { "card.title": "", "dashcard.background": false } }
\`\`\`

\`\`\`json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 2 }
\`\`\`
`;
}

function buildSourceBlock(meta) {
  const parts = [`**Source:** ${meta.source}`, `**Cadence:** ${meta.cadence}`, `**Scope:** ${meta.scope}`];
  if (meta.caveats) parts.push(`**Caveats:** ${meta.caveats}`);
  const text = parts.join(" · ") + "\n<!-- text-id:source-freshness -->";
  return `#### 📝 Text: Source & Freshness

${text}

\`\`\`json metabase-pos
{ "row": 99, "col": 0, "size_x": 18, "size_y": 1 }
\`\`\`
`;
}

function escapeRegex(s) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

// Parse blueprint to extract tabs and check widget presence per tab
function parseBlueprintTabs(content) {
  // Find dashboard header position
  const dashHeader = content.match(/^### (🖥️ )?Dashboard:.*$/m);
  if (!dashHeader) return { hasTabs: false, tabs: [] };

  // Find all tab headers after dashboard (accept "### Tab:" OR "### 📑 Tab:")
  const tabsArea = content.slice(dashHeader.index);
  const tabRegex = /^### (?:📑 )?Tab: (.+?)\s*$/gm;
  const tabs = [];
  let m;
  while ((m = tabRegex.exec(tabsArea)) !== null) {
    tabs.push({ name: m[1].trim(), absIndex: dashHeader.index + m.index, headerEnd: dashHeader.index + m.index + m[0].length });
  }

  if (tabs.length === 0) {
    // No tabs — single body
    const headerEnd = dashHeader.index + dashHeader[0].length;
    const body = content.slice(headerEnd);
    const hasChu = /^####\s+❓\s+Question:\s+Chu kỳ báo cáo\s*$/m.test(body);
    const hasSource = /<!--\s*text-id:source-freshness\s*-->/.test(body) || /^####\s+📝\s+Text:\s+Source\s*&\s*Freshness\s*$/m.test(body);
    return { hasTabs: false, tabs: [{ name: "(no tabs)", bodyStart: headerEnd, bodyEnd: content.length, hasChu, hasSource }] };
  }

  // Compute each tab's content range
  for (let i = 0; i < tabs.length; i++) {
    const start = tabs[i].headerEnd;
    let end = content.length;
    if (i < tabs.length - 1) end = tabs[i+1].absIndex;
    else {
      // Look for next ## section
      const afterTab = content.slice(start);
      const nextSection = afterTab.match(/^## /m);
      if (nextSection) end = start + nextSection.index;
    }
    tabs[i].bodyStart = start;
    tabs[i].bodyEnd = end;
    const tabContent = content.slice(start, end);
    tabs[i].hasChu = /^####\s+❓\s+Question:\s+Chu kỳ báo cáo\s*$/m.test(tabContent);
    tabs[i].hasSource = /<!--\s*text-id:source-freshness\s*-->/.test(tabContent) || /^####\s+📝\s+Text:\s+Source\s*&\s*Freshness\s*$/m.test(tabContent);
  }

  return { hasTabs: true, tabs };
}

function updateBlueprint(blueprintFile, meta) {
  const filePath = `docs/analytics-handbook/blueprints/${blueprintFile}.md`;
  if (!fs.existsSync(filePath)) {
    console.log(`✗ ${filePath} not found`);
    return;
  }

  let content = fs.readFileSync(filePath, "utf8");
  const parsed = parseBlueprintTabs(content);
  let modifications = 0;

  // Process tabs in REVERSE order so insertions don't invalidate earlier indices
  const tabsRev = parsed.tabs.slice().reverse();

  for (const tab of tabsRev) {
    if (tab.hasChu && tab.hasSource) continue;

    if (tab.name === "(no tabs)") {
      // Inject Chu kỳ right after Dashboard description (before first #### or ### after dash header)
      if (!tab.hasChu) {
        const dashHeader = content.match(/^### (🖥️ )?Dashboard:.*$/m);
        if (dashHeader) {
          const headerEnd = dashHeader.index + dashHeader[0].length;
          // Skip past description text — find first `#### ` or `--- ` block
          const afterHeader = content.slice(headerEnd);
          const nextBlock = afterHeader.match(/^(#{3,4} |---)/m);
          const inject = nextBlock ? headerEnd + nextBlock.index : content.length;
          content = content.slice(0, inject) + "\n" + buildChuKyBlock(meta.cadence) + "\n" + content.slice(inject);
          modifications++;
        }
      }
      if (!tab.hasSource) {
        content = content.trimEnd() + "\n\n" + buildSourceBlock(meta) + "\n";
        modifications++;
      }
      continue;
    }

    // Tabbed: insert in reverse to preserve indices
    if (!tab.hasSource) {
      const block = "\n" + buildSourceBlock(meta) + "\n";
      content = content.slice(0, tab.bodyEnd) + block + content.slice(tab.bodyEnd);
      modifications++;
    }

    if (!tab.hasChu) {
      content = content.slice(0, tab.headerEnd) + "\n\n" + buildChuKyBlock(meta.cadence) + content.slice(tab.headerEnd);
      modifications++;
    }
  }

  if (modifications === 0) {
    console.log(`= ${blueprintFile}.md (already compliant)`);
    return;
  }

  fs.writeFileSync(filePath, content);
  console.log(`✓ ${blueprintFile}.md (+${modifications} widget declarations)`);
}

function main() {
  let updated = 0, skipped = 0;
  for (const r of audit) {
    const blueprintFile = BLUEPRINT_MAP[r.id];
    const meta = META[r.id];
    if (!blueprintFile || !meta) {
      console.log(`- [${r.id}] ${r.name}: no blueprint mapping, skip`);
      skipped++;
      continue;
    }
    updateBlueprint(blueprintFile, meta);
    updated++;
  }
  console.log(`\nProcessed: ${updated}, Skipped (unmapped): ${skipped}`);
}

main();
