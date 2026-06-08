/**
 * add-chu-ky-bao-cao-widget.js
 *
 * For each Metabase dashboard missing a "chu kỳ báo cáo" text widget,
 * insert one at the top of the first tab (row 0), shift existing cards down,
 * and patch the corresponding blueprint markdown file.
 *
 * Usage:
 *   node tools/add-chu-ky-bao-cao-widget.js [--dry-run]
 */

const http = require('http');
const fs = require('fs');
const path = require('path');

const BASE_HOST = '127.0.0.1';
const BASE_PORT = 3001;
const API_KEY = process.env.METABASE_API_KEY || 'mb_buAQN9X7jRNYeum74PRgIJIirdmXM9hy2IDLDJtAmmA=';
const BLUEPRINTS_DIR = path.join(__dirname, '..', 'docs', 'analytics-handbook', 'blueprints');
const DRY_RUN = process.argv.includes('--dry-run');

// ── Reporting-period metadata per dashboard ID ────────────────────────────────

const DASHBOARD_PERIODS = {
  // Daily — rolling đến thời điểm hiện tại
  49: { period: 'Hôm nay (rolling đến hiện tại, ICT)',     comparison: 'Hôm qua (D-1)',           freq: 'Real-time' },
  41: { period: 'Hôm nay (rolling đến hiện tại, ICT)',     comparison: 'Hôm qua (D-1)',           freq: 'Real-time' },
   2: { period: 'Hôm nay (rolling đến hiện tại, ICT)',     comparison: 'Hôm qua (D-1)',           freq: 'Real-time' },
  51: { period: 'Hôm nay (rolling đến hiện tại, ICT)',     comparison: 'Hôm qua (D-1)',           freq: 'Real-time' },
  27: { period: 'Hôm nay (rolling đến hiện tại, ICT)',     comparison: 'Hôm qua (D-1)',           freq: 'Real-time' },
  28: { period: 'Hôm nay (rolling đến hiện tại, ICT)',     comparison: 'Hôm qua (D-1)',           freq: 'Real-time' },

  // Yesterday — D-1
  42: { period: 'Hôm qua (D-1, ICT)',                      comparison: 'Hôm qua -7 ngày (WoW)',   freq: 'Hàng ngày' },
   5: { period: 'Hôm qua (D-1, ICT)',                      comparison: 'Hôm qua -7 ngày (WoW)',   freq: 'Hàng ngày' },

  // Weekly
  11: { period: 'Tuần qua (T2–CN, ICT)',                   comparison: 'Tuần trước đó (WoW)',      freq: 'Hàng tuần' },
  43: { period: 'Tuần qua (T2–CN, ICT)',                   comparison: 'Tuần trước đó (WoW)',      freq: 'Hàng tuần' },
   8: { period: 'Tuần qua (T2–CN, ICT)',                   comparison: 'Tuần trước đó (WoW)',      freq: 'Hàng tuần' },
  10: { period: 'Tuần qua (T2–CN, ICT)',                   comparison: 'Tuần trước đó (WoW)',      freq: 'Hàng tuần' },
  47: { period: 'Tuần qua (T2–CN, ICT)',                   comparison: 'Tuần trước đó (WoW)',      freq: 'Hàng tuần' },

  // Monthly
  12: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  44: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
   9: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  31: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  33: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  15: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  34: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  13: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  30: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  37: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },

  // Operational — rolling 30 ngày
   4: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },
  48: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },
  14: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },
  50: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },
  36: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },
  29: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },
  46: { period: '30 ngày gần nhất (rolling, ICT)',          comparison: '30 ngày trước đó',         freq: 'Hàng ngày' },

  // Ingestion Health Monitor
  40: { period: 'Hôm nay (ICT) + 30 ngày gần nhất (trend)', comparison: 'N/A (monitoring wall)',     freq: 'Real-time' },

  // Shopee settlement
  32: { period: 'Kỳ quyết toán Shopee (billing cycle)',     comparison: 'Kỳ trước đó',              freq: 'Theo settlement' },

  // Order-level detail / listing
  38: { period: 'Theo đơn hàng được chọn (không cố định)', comparison: 'N/A',                      freq: 'On-demand' },
  26: { period: 'Hôm nay / khoảng thời gian được lọc',     comparison: 'N/A (custom filter)',      freq: 'On-demand' },

  // Order profitability
  35: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },
  45: { period: 'Tháng trước (1/M–cuối tháng, ICT)',       comparison: 'Tháng trước đó (MoM)',     freq: 'Hàng tháng' },

  // Legacy
   1: { period: 'Rolling (MoM so sánh, ICT)',               comparison: 'Tháng trước đó',          freq: 'Hàng ngày' },
};

// ── Blueprint filename per dashboard ID ──────────────────────────────────────

const BLUEPRINT_MAP = {
  49: 'b2b_sales_daily.md',
  50: 'b2b_orders_tracking.md',
  12: 'ceo_monthly_scorecard.md',
  44: 'ceo_monthly_scorecard.md',
  11: 'ceo_weekly_pulse.md',
  43: 'ceo_weekly_pulse.md',
  33: 'channel_profitability_monthly.md',
  15: 'customer_intelligence_monthly.md',
  48: 'customer_operational_dashboard.md',
   4: 'customer_operational_dashboard.md',
  14: 'customer_retention_dashboard.md',
  41: 'sales_today_operation.md',
   2: 'sales_today_operation.md',
  34: 'finance_pl.md',
  28: 'logistics_operations.md',
  13: 'marketing_monthly_analysis.md',
  37: 'marketing_roi.md',
  10: 'marketing_weekly_tracker.md',
  47: 'marketing_weekly_tracker.md',
  38: 'order_detail.md',
  26: 'order_listing.md',
  35: 'order_profitability.md',
  45: 'order_profitability.md',
  30: 'product_performance.md',
  36: 'product_profitability.md',
  29: 'sales_promotion_analysis.md',
  46: 'sales_promotion_analysis.md',
  31: 'sales_monthly_review.md',
   9: 'sales_ops_monthly_summary.md',
   8: 'sales_ops_weekly_review.md',
  32: 'shopee_channel_economics.md',
  27: 'customer_support_social_commerce.md',
  51: 'us_crossborder_operations.md',
  42: 'sales_daily_retail.md',
   5: 'sales_daily_retail.md',
  40: 'ingestion_health.md',
   1: null,  // E-commerce Insights — legacy, no blueprint
};

// ── HTTP helpers ──────────────────────────────────────────────────────────────

function apiGet(urlPath) {
  return new Promise((resolve, reject) => {
    const opts = {
      hostname: BASE_HOST, port: BASE_PORT, path: urlPath, method: 'GET',
      headers: { 'x-api-key': API_KEY },
    };
    http.request(opts, res => {
      let data = '';
      res.on('data', c => (data += c));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(new Error('JSON parse error: ' + data.slice(0, 300))); }
      });
    }).on('error', reject).end();
  });
}

function apiPut(urlPath, body) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify(body);
    const opts = {
      hostname: BASE_HOST, port: BASE_PORT, path: urlPath, method: 'PUT',
      headers: {
        'x-api-key': API_KEY,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    };
    const req = http.request(opts, res => {
      let data = '';
      res.on('data', c => (data += c));
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch (e) { resolve({ status: res.statusCode, body: data }); }
      });
    });
    req.on('error', reject);
    req.write(payload);
    req.end();
  });
}

// ── Text card builder ─────────────────────────────────────────────────────────

const TEXT_ID_SLUG = 'chu-ky-bao-cao';

function buildChuKyText(meta) {
  const line = `📅 **Chu kỳ báo cáo:** ${meta.period} | **So sánh:** ${meta.comparison} | **Cập nhật:** ${meta.freq}`;
  return `${line}\n<!-- text-id:${TEXT_ID_SLUG} -->`;
}

// ── Blueprint patch ───────────────────────────────────────────────────────────

function patchBlueprint(blueprintFile, firstTabName, textContent) {
  const filePath = path.join(BLUEPRINTS_DIR, blueprintFile);
  if (!fs.existsSync(filePath)) {
    console.log(`  ⚠️  Blueprint not found: ${blueprintFile}`);
    return false;
  }

  let content = fs.readFileSync(filePath, 'utf8');

  if (content.includes(TEXT_ID_SLUG)) {
    console.log(`  ℹ️  Blueprint already patched: ${blueprintFile}`);
    return false;
  }

  // Snippet to insert
  const snippet =
    `#### 📝 Text: Chu kỳ báo cáo\n\n` +
    `${textContent}\n\n` +
    `\`\`\`json metabase-pos\n` +
    `{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }\n` +
    `\`\`\`\n\n`;

  // Try inserting just after the first tab heading (or dashboard heading)
  let inserted = false;

  if (firstTabName) {
    // Match "### Tab: <name>" or "### 📑 Tab: <name>"
    const escaped = firstTabName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const tabRe = new RegExp(`(### (?:📑 )?Tab:.*?${escaped}[^\\n]*\\n(?:[\\s\\S]*?---\\n)?)`, 'm');
    const m = content.match(tabRe);
    if (m) {
      const insertAt = content.indexOf(m[0]) + m[0].length;
      // Skip blank lines right after the heading block
      let skip = insertAt;
      while (skip < content.length && content[skip] === '\n') skip++;
      // Insert before the first #### in this tab
      const nextSection = content.indexOf('\n####', skip);
      if (nextSection !== -1) {
        content = content.slice(0, nextSection + 1) + snippet + content.slice(nextSection + 1);
        inserted = true;
      }
    }
  }

  if (!inserted) {
    // Fallback: before the very first #### section
    const idx = content.indexOf('\n####');
    if (idx !== -1) {
      content = content.slice(0, idx + 1) + snippet + content.slice(idx + 1);
      inserted = true;
    }
  }

  if (!inserted) {
    console.log(`  ⚠️  Could not find insertion point in ${blueprintFile}`);
    return false;
  }

  if (!DRY_RUN) {
    fs.writeFileSync(filePath, content, 'utf8');
  }
  console.log(`  📄 Blueprint patched: ${blueprintFile}`);
  return true;
}

// ── Per-dashboard processor ───────────────────────────────────────────────────

async function processDashboard(dash, meta) {
  const detail = await apiGet(`/api/dashboard/${dash.id}`);
  const tabs = (detail.tabs || []).sort((a, b) => a.position - b.position);
  const dashcards = detail.dashcards || [];

  const firstTab = tabs.length > 0 ? tabs[0] : null;
  const firstTabId = firstTab ? firstTab.id : null;
  const firstTabName = firstTab ? firstTab.name : null;

  // Check idempotency — already has the widget?
  const scope = firstTabId !== null
    ? dashcards.filter(c => c.dashboard_tab_id === firstTabId)
    : dashcards;

  const alreadyHas = scope.some(c =>
    !c.card_id &&
    ((c.visualization_settings || {}).text || '').includes(TEXT_ID_SLUG)
  );
  if (alreadyHas) {
    return { added: false, reason: 'already_exists' };
  }

  const textContent = buildChuKyText(meta);

  // Shift all first-tab cards down 1 row to make room at row 0
  const shiftedCards = dashcards.map(c => {
    const inScope = firstTabId !== null ? c.dashboard_tab_id === firstTabId : true;
    return inScope ? { ...c, row: c.row + 1 } : c;
  });

  // New text dashcard at row 0
  const newCard = {
    id: -9999,
    card_id: null,
    row: 0,
    col: 0,
    size_x: 18,
    size_y: 1,
    visualization_settings: {
      virtual_card: {
        name: null,
        display: 'text',
        visualization_settings: {},
        dataset_query: {},
        archived: false,
      },
      text: textContent,
    },
    parameter_mappings: [],
    series: [],
    ...(firstTabId !== null ? { dashboard_tab_id: firstTabId } : {}),
  };

  const cardPayload = [...shiftedCards, newCard].map(c => {
    const obj = {
      id: c.id,
      card_id: c.card_id ?? null,
      row: c.row,
      col: c.col,
      size_x: c.size_x,
      size_y: c.size_y,
      visualization_settings: c.visualization_settings || {},
      parameter_mappings: c.parameter_mappings || [],
      series: c.series || [],
    };
    if (c.dashboard_tab_id !== undefined) obj.dashboard_tab_id = c.dashboard_tab_id;
    return obj;
  });

  const putBody = { dashcards: cardPayload };
  if (tabs.length > 0) {
    putBody.tabs = tabs.map(t => ({ id: t.id, name: t.name }));
  }

  if (DRY_RUN) {
    console.log(`  [DRY-RUN] PUT /api/dashboard/${dash.id} — ${cardPayload.length} cards, new text at row 0`);
    console.log(`  [DRY-RUN] Text: "${textContent.replace(/\n.*/s, '')}"`);
  } else {
    const res = await apiPut(`/api/dashboard/${dash.id}`, putBody);
    if (res.status !== 200) {
      const errMsg = `PUT failed status=${res.status}: ${JSON.stringify(res.body).slice(0, 300)}`;
      console.error(`  ❌ ${errMsg}`);
      return { added: false, reason: errMsg };
    }
    console.log(`  ✅ Text widget inserted (HTTP ${res.status})`);
  }

  // Patch blueprint
  const blueprintFile = BLUEPRINT_MAP[dash.id];
  if (blueprintFile) {
    patchBlueprint(blueprintFile, firstTabName, textContent);
  } else {
    console.log(`  ℹ️  No blueprint for dashboard ${dash.id} — skip blueprint patch`);
  }

  return { added: true, text: textContent };
}

// ── Main ──────────────────────────────────────────────────────────────────────

async function main() {
  console.log(DRY_RUN
    ? '🔍  DRY-RUN mode — no writes will occur\n'
    : '🚀  Live mode — will modify Metabase + blueprints\n');

  const all = await apiGet('/api/dashboard?f=all');
  const dashboards = (Array.isArray(all) ? all : all.data || [])
    .sort((a, b) => a.id - b.id);

  const results = [];
  const patchedBlueprints = new Set();

  for (const dash of dashboards) {
    const meta = DASHBOARD_PERIODS[dash.id];
    if (!meta) {
      console.log(`[${String(dash.id).padStart(3)}] ${dash.name} — ⚠️  no period defined, SKIP`);
      results.push({ id: dash.id, name: dash.name, status: 'no_period_defined' });
      continue;
    }

    console.log(`[${String(dash.id).padStart(3)}] ${dash.name}`);
    try {
      const r = await processDashboard(dash, meta);
      const bp = BLUEPRINT_MAP[dash.id];
      if (r.added && bp) patchedBlueprints.add(bp);
      results.push({ id: dash.id, name: dash.name, status: r.added ? 'added' : r.reason });
    } catch (e) {
      console.error(`  ❌ Error: ${e.message}`);
      results.push({ id: dash.id, name: dash.name, status: 'error', error: e.message });
    }
  }

  // ── Summary ───────────────────────────────────────────────────────────────
  const added    = results.filter(r => r.status === 'added');
  const skipped  = results.filter(r => r.status !== 'added' && r.status !== 'error');
  const errors   = results.filter(r => r.status === 'error');

  console.log('\n══════════════════════════════════════════════════════');
  console.log(`✅  Widget added:         ${added.length}`);
  console.log(`⏭️   Skipped:              ${skipped.length}`);
  console.log(`❌  Errors:               ${errors.length}`);
  console.log(`📄  Blueprints patched:   ${patchedBlueprints.size}`);
  if (errors.length > 0) {
    errors.forEach(r => console.log(`    ❌ [${r.id}] ${r.name}: ${r.error}`));
  }

  const outFile = path.join(__dirname, '..', 'plans', 'reports',
    `agent-260514-1529-add-chu-ky-bao-cao-results.json`);
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, JSON.stringify(results, null, 2));
  console.log(`\nFull results → ${outFile}`);
}

main().catch(err => { console.error('Fatal:', err); process.exit(1); });
