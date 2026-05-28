#!/usr/bin/env node
/**
 * Batch-add top + bottom date-range hint text widgets to all dashboards.
 * Top: hint about default date range per dashboard.
 * Bottom: generic filter mechanism hint.
 *
 * Usage:
 *   export METABASE_URL=http://127.0.0.1:3001
 *   export METABASE_API_KEY=mb_...
 *   node add-date-range-widgets.js
 */

const URL = process.env.METABASE_URL || "http://127.0.0.1:3001";
const KEY = process.env.METABASE_API_KEY;
if (!KEY) { console.error("METABASE_API_KEY required"); process.exit(1); }

// Per-dashboard top widget text (date-range hint)
const TOP_HINTS = {
  73: "📍 **Onboarding** — Mở đúng folder cho role của bạn. Tất cả dashboard có suffix `[All]/[Retail]/[B2B]/[Cross]/[US]/[Internal]` cho biết scope.",
  43: "📅 **Tuần này so với tuần trước** (Thứ 2 → hiện tại vs 7 ngày trước). KPI scalar dùng cửa sổ tuần cố định.",
  44: "📅 **Tháng này so với tháng trước** (MTD vs same period last month). Một số trend kéo dài 6-12 tháng.",
  31: "📅 **Tháng vừa đóng so với tháng trước** + xu hướng 12 tháng. Có filter Branch + Period cho tables.",
  34: "📅 **Last 30 days vs prior 30 days** (Finance P&L). Period filter áp dụng nhiều cards.",
  35: "📅 **Period filter** (mặc định last 30 days). Channel filter parametric cho table profitability.",
  36: "📅 **Last 30 days** SKU-level profitability. COGS variance dùng rolling 3-month average.",
  33: "📅 **Hàng tháng** (current month vs prior month). Heatmap kéo dài 6 tháng.",
  15: "📅 **Tháng MoM** customer cohort. Retention cohort cumulative.",
  30: "📅 **Last 30 days vs prior 30 days** (Product Performance). Filters: Date Range + Loại SP + Kênh.",
  32: "📅 **Kỳ payout Shopee 30 ngày gần nhất** (filter Payout Period). Settlement margin gauge dùng kỳ filter.",
  38: "📅 **Chi tiết 1 order** (chọn order_code). Không có time window dashboard-level.",
  26: "📅 **Last 30 days orders** (filter Date Range). Hỗ trợ drill-down tới Order Detail.",
  27: "📅 **30-day rolling** social commerce metrics. Mostly fixed-window cards.",
  41: "📅 **Hôm nay** (current_date). So sánh với hôm qua + 7 ngày qua trên trend cards.",
  42: "📅 **Hôm qua** (current_date - 1). So sánh với hôm kia + 7-day comparison.",
  40: "📅 **Last 7 days** pipeline health. Realtime alert + 7-day SLA metrics.",
  28: "📅 **Hôm nay** + last 7 days logistics. Stuck-order escalation real-time.",
  51: "📅 **Hôm nay** US CrossBorder. Weekly + monthly tabs cho period reviews.",
  8: "📅 **Tuần này so với tuần trước** (WoW). Filter Date Range + Branch áp dụng cho hầu hết cards.",
  9: "📅 **Tháng vừa đóng so với tháng trước** (MoM). Filter Date Range + Branch áp dụng cho hầu hết cards.",
  49: "📅 **Hôm nay** B2B daily metrics. Compare với hôm qua + 7-day trend.",
  50: "📅 **30-day rolling** B2B order tracking. AR aging fixed-window.",
  13: "📅 **Tháng vừa đóng** + MoM comparison. Mostly fixed monthly window cards.",
  14: "📅 **Rolling cohort + monthly** retention. Cohort retention cumulative theo tuần.",
  37: "📅 **Last 30 days vs prior 30 days** ROAS analysis. Profitable ROAS dùng rolling 30-day.",
  47: "📅 **Tuần này so với tuần trước** (WoW). Marketing weekly tracker dùng cửa sổ tuần cố định.",
  46: "📅 **Last 30 days vs prior 30 days** promotion ROI. Baseline = non-promo same-channel same-period.",
  48: "📅 **30-day rolling MAU** + MoM segment shift. At-risk customer alert real-time.",
  74: "📅 **MTD + last 6 months** trend. Alert cards dùng cửa sổ cố định (MTD vs trailing).",
  75: "📅 **Last 90 days** return cohort + MTD KPI. Cohort table lag distribution.",
  76: "📅 **Last 30 days** SKU margin + MTD COGS variance alert. Scatter density theo 30-day window.",
  77: "📅 **Period filter** waterfall + 12-month heatmap. Variance dùng rolling period.",
  78: "📅 **Last 30 days** reconciliation. Drift trend 30-day moving average."
};

// Generic bottom widget text (filter mechanism hint)
const BOTTOM_TEXT = `🔍 **Cơ chế filter date-range:**
- Filter ở đầu báo cáo áp dụng cho card có template tag \`{{date_range}}\` trong SQL.
- Card KPI / alert / trend dùng **cửa sổ cố định** (MTD, last 30d, current week, 12-month rolling, etc.) — KHÔNG đổi theo filter (intentional).
- Hover tiêu đề card xem time window cụ thể của card đó.
- Hint phạm vi mặc định ở đầu báo cáo.

📚 Tài liệu chi tiết: \`docs/analytics-handbook/playbooks/{dashboard-name}.md\``;

async function api(path, opts={}) {
  const res = await fetch(`${URL}${path}`, {
    ...opts,
    headers: {
      "x-api-key": KEY,
      "Content-Type": "application/json",
      ...(opts.headers||{})
    }
  });
  return res.json();
}

function preserveDashcard(dc) {
  // Preserve essential fields for existing dashcards
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

function buildTextWidget(text, row, col, sizeX, sizeY, tabId, id) {
  return {
    id,
    dashboard_tab_id: tabId,
    card_id: null,
    row,
    col,
    size_x: sizeX,
    size_y: sizeY,
    visualization_settings: {
      "virtual_card": {"name":null,"display":"text","visualization_settings":{},"dataset_query":{},"archived":false},
      "text": text,
      "dashcard.background": false,
      "text.align_vertical": "top"
    },
    parameter_mappings: [],
    series: [],
    inline_parameters: []
  };
}

async function processDashboard(id) {
  const topText = TOP_HINTS[id];
  if (!topText) {
    console.log(`[${id}] SKIP (no hint defined)`);
    return;
  }

  const d = await api(`/api/dashboard/${id}`);
  if (d.archived) { console.log(`[${id}] SKIP (archived)`); return; }

  const existing = (d.dashcards || []).map(preserveDashcard);
  const tabs = d.tabs || [];
  const firstTabId = tabs.length > 0 ? tabs[0].id : null;

  // Check if widget already added (look for our marker)
  const hasTopMarker = existing.some(dc => {
    const t = dc.visualization_settings?.text;
    return t && t.startsWith("📅 ") && t.length < 300;
  });
  if (hasTopMarker) {
    console.log(`[${id}] ${d.name} → already has top widget, skip`);
    return;
  }

  // Determine target tab (first tab if exists, else null)
  // Filter existing cards to those on target tab for row shifting
  const targetCards = existing.filter(dc => dc.dashboard_tab_id === firstTabId);
  const otherCards = existing.filter(dc => dc.dashboard_tab_id !== firstTabId);

  // Shift all target-tab cards down by 2 rows to make space for top widget
  targetCards.forEach(dc => { dc.row += 2; });

  // Add top widget at row 0
  const topWidget = buildTextWidget(topText, 0, 0, 18, 2, firstTabId, -1);

  // Find max row on target tab to place bottom widget
  const maxRow = targetCards.reduce((m, dc) => Math.max(m, dc.row + (dc.size_y||0)), 2);

  // Add bottom widget below all cards
  const bottomWidget = buildTextWidget(BOTTOM_TEXT, maxRow, 0, 18, 4, firstTabId, -2);

  const newDashcards = [topWidget, ...targetCards, bottomWidget, ...otherCards];

  // CRITICAL: include tabs to preserve FK references when dashboard has tabs
  const tabsPayload = tabs.map(t => ({id: t.id, name: t.name, position: t.position}));

  try {
    const body = {dashcards: newDashcards};
    if (tabsPayload.length > 0) body.tabs = tabsPayload;
    const res = await fetch(`${URL}/api/dashboard/${id}`, {
      method: "PUT",
      headers: {"x-api-key": KEY, "Content-Type": "application/json"},
      body: JSON.stringify(body)
    });
    if (res.ok) {
      console.log(`[${id}] ${d.name} ✓ (was ${existing.length}, now ${newDashcards.length})`);
    } else {
      const err = await res.text();
      console.log(`[${id}] ${d.name} ✗ HTTP ${res.status}: ${err.slice(0, 200)}`);
    }
  } catch (e) {
    console.log(`[${id}] ${d.name} ✗ ${e.message}`);
  }
}

async function main() {
  const ids = Object.keys(TOP_HINTS).map(Number);
  console.log(`Processing ${ids.length} dashboards...\n`);
  for (const id of ids) {
    await processDashboard(id);
    await new Promise(r => setTimeout(r, 200)); // rate limit
  }
  console.log("\nDone.");
}

main().catch(e => { console.error(e); process.exit(1); });
