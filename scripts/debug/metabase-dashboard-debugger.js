#!/usr/bin/env node
/**
 * Metabase Dashboard Debugger
 *
 * Fetches a dashboard with active filters, executes every data card via the
 * Metabase API (parameter substitution happens server-side), and prints a
 * structured debug report designed to be fed to a Claude skill for analysis.
 *
 * Usage:
 *   node scripts/debug/metabase-dashboard-debugger.js "<dashboard_url>" [--card <card_id>]
 *
 * Modes:
 *   (no flag)           Summary: list all cards with row counts — pick which to deep-dive
 *   --card <card_id>    Deep-dive: full SQL + results for one specific card
 *   --all               Full report for every card (verbose, large output)
 *
 * Examples:
 *   node scripts/debug/metabase-dashboard-debugger.js "http://bi.lan.fwg.vn/dashboard/43?scope=SHOPEE_VN"
 *   node scripts/debug/metabase-dashboard-debugger.js "http://bi.lan.fwg.vn/dashboard/43?scope=SHOPEE_VN" --card 1246
 *
 * Env vars (same as other metabase scripts):
 *   METABASE_URL      e.g. http://127.0.0.1:3001
 *   METABASE_API_KEY  API key (preferred) or METABASE_SESSION_ID
 */

'use strict';

const path = require('path');
const fs   = require('fs');

const MetabaseCore   = require(
  path.join(__dirname, '../../.skills/metabase-automation/lib/metabase_core')
);
const DashboardCache = require(path.join(__dirname, 'lib/dashboard-cache'));

const CACHE_DIR = path.join(__dirname, '../../.cache/metabase');

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const SQL_PREVIEW_LINES = 20;   // max lines of SQL to show in deep-dive
const MAX_SAMPLE_ROWS   = 5;    // max result rows to print

// ---------------------------------------------------------------------------
// Env + CLI
// ---------------------------------------------------------------------------

function loadEnv() {
  const envPath = path.join(__dirname, '../../.env.docker');
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (m && !process.env[m[1]])
      process.env[m[1]] = m[2].trim().replace(/^["']|["']$/g, '');
  }
}

function parseArgs() {
  const args = process.argv.slice(2);
  if (!args.length || args[0].startsWith('--')) {
    console.error('Usage: node metabase-dashboard-debugger.js "<dashboard_url>" [--card <card_id>] [--all]');
    process.exit(1);
  }
  const rawUrl   = args[0];
  const cardIdx   = args.indexOf('--card');
  const targetCard = cardIdx !== -1 ? parseInt(args[cardIdx + 1], 10) : null;
  const allMode   = args.includes('--all');
  const noCache   = args.includes('--no-cache');
  return { rawUrl, targetCard, allMode, noCache };
}

// ---------------------------------------------------------------------------
// URL parsing
// ---------------------------------------------------------------------------

function parseDashboardUrl(rawUrl) {
  let url;
  try { url = new URL(rawUrl); }
  catch { url = new URL(rawUrl, 'http://localhost'); }

  const match = url.pathname.match(/\/dashboard\/(\d+)/);
  if (!match) throw new Error(`Cannot extract dashboard ID from: ${rawUrl}`);

  const dashboardId  = parseInt(match[1], 10);
  const filterParams = {};
  for (const [k, v] of url.searchParams.entries()) filterParams[k] = v;
  return { dashboardId, filterParams };
}

// ---------------------------------------------------------------------------
// Parameter mapping
// ---------------------------------------------------------------------------

function buildQueryParameters(dashParams, filterParams) {
  const matched = [], unmatched = [];
  for (const [slug, value] of Object.entries(filterParams)) {
    const param = dashParams.find(p => p.slug === slug || p.name === slug);
    if (!param) { unmatched.push(slug); continue; }
    matched.push({ id: param.id, type: param.type, value, slug: param.slug, name: param.name });
  }
  return { matched, unmatched };
}

// ---------------------------------------------------------------------------
// SQL + result extraction
// ---------------------------------------------------------------------------

function extractNativeSql(queryResponse, cardInfo) {
  const q = queryResponse?.json_query;
  if (q?.dataset_query?.native?.query) return q.dataset_query.native.query;
  if (queryResponse?.data?.native_form?.query) return queryResponse.data.native_form.query;
  return cardInfo?.dataset_query?.native?.query
      || cardInfo?.dataset_query?.stages?.[0]?.native
      || null;
}

function extractResults(queryResponse) {
  const data = queryResponse?.data;
  if (!data) return { columns: [], rows: [], total: 0 };
  const columns = (data.cols || []).map(c => c.display_name || c.name);
  const rows    = data.rows || [];
  const total   = data.results_metadata?.rowcount ?? rows.length;
  return { columns, rows: rows.slice(0, MAX_SAMPLE_ROWS), total };
}

function truncateSql(sql, maxLines) {
  if (!sql) return '(unavailable)';
  const lines = sql.trim().split('\n');
  if (lines.length <= maxLines) return sql.trim();
  return lines.slice(0, maxLines).join('\n') + `\n  ... (+${lines.length - maxLines} more lines)`;
}

// ---------------------------------------------------------------------------
// Output helpers
// ---------------------------------------------------------------------------

const SEP  = '═'.repeat(70);
const DASH = '─'.repeat(70);

function printSql(label, sql, maxLines = SQL_PREVIEW_LINES) {
  console.log(`\n[${label}]`);
  console.log(truncateSql(sql, maxLines).split('\n').map(l => '  ' + l).join('\n'));
}

function printResults(columns, rows, total) {
  console.log(`\n[KẾT QUẢ]`);
  console.log(`  Tổng rows : ${total}`);
  console.log(`  Columns   : ${columns.join(', ')}`);
  if (!rows.length) {
    console.log('  ⚠️  0 rows — filter có thể quá hẹp hoặc thiếu data');
    return;
  }
  const header = '  ' + columns.join(' | ');
  const lines  = rows.map(r => '  ' + r.map(v => v === null ? 'NULL' : String(v)).join(' | '));
  console.log([header, ...lines].join('\n'));
}

function printMappings(mappings, dashParams, matched) {
  if (!mappings.length) {
    console.log('\n[PARAMETER MAPPINGS] không có — card này không bị ảnh hưởng bởi dashboard filters');
    return;
  }
  console.log('\n[PARAMETER MAPPINGS]');
  for (const pm of mappings) {
    const dashParam    = dashParams.find(p => p.id === pm.parameter_id);
    const activeFilter = matched.find(p => p.id === pm.parameter_id);
    const status       = activeFilter ? `→ value="${activeFilter.value}"` : '→ (không có filter active)';
    console.log(`  param slug="${dashParam?.slug || '?'}" | target=${JSON.stringify(pm.target)} ${status}`);
  }
}

// ---------------------------------------------------------------------------
// Execute one card via Metabase API
// ---------------------------------------------------------------------------

async function executeCard(core, dashboardId, dashcard, queryParams) {
  const cardId     = dashcard.card_id;
  const dashcardId = dashcard.id;
  const card       = dashcard.card;

  let queryResponse = null, execError = null;
  try {
    queryResponse = await core.request(
      `/api/dashboard/${dashboardId}/dashcard/${dashcardId}/card/${cardId}/query`,
      'POST',
      { parameters: queryParams }
    );
  } catch (err) {
    execError = err.message;
  }

  return { card, cardId, dashcardId, queryResponse, execError };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  loadEnv();
  const { rawUrl, targetCard, allMode, noCache } = parseArgs();
  const { dashboardId, filterParams }            = parseDashboardUrl(rawUrl);

  const metabaseUrl = (process.env.METABASE_URL || 'http://127.0.0.1:3001').replace(/\/$/, '');
  const apiKey      = process.env.METABASE_API_KEY || process.env.METABASE_SESSION_ID;
  const authHeader  = process.env.METABASE_API_KEY ? 'x-api-key' : 'X-Metabase-Session';

  if (!apiKey) { console.error('❌  Set METABASE_API_KEY or METABASE_SESSION_ID'); process.exit(1); }

  const core  = new MetabaseCore(metabaseUrl, apiKey, { authHeader });
  const cache = new DashboardCache(CACHE_DIR);

  // ── Fetch dashboard (cache-aware) ────────────────────────────────────────
  console.log(`${SEP}\nMETABASE DASHBOARD DEBUGGER\nURL: ${rawUrl}\n${SEP}`);

  let dashboard;
  const cached = !noCache && cache.get(dashboardId);
  if (cached) {
    dashboard = cached;
    console.log(`[cache] Dashboard ${dashboardId} loaded from cache (age: ${cache.age(dashboardId)}). Use --no-cache to refresh.`);
  } else {
    if (noCache) cache.invalidate(dashboardId);
    try { dashboard = await core.request(`/api/dashboard/${dashboardId}`); }
    catch (err) { console.error(`❌  Dashboard ${dashboardId} not found: ${err.message}`); process.exit(1); }
    cache.set(dashboardId, dashboard);
    console.log(`[api] Dashboard ${dashboardId} fetched and cached.`);
  }

  const dashParams = dashboard.parameters || [];
  const dashcards  = (dashboard.dashcards || dashboard.ordered_cards || []);
  const dataCards  = dashcards.filter(dc => dc.card_id !== null && dc.card != null);
  const tabs       = dashboard.tabs || [];

  console.log(`Dashboard : "${dashboard.name}" (ID: ${dashboardId})`);
  if (dashboard.description) console.log(`Mô tả     : ${dashboard.description}`);

  // ── Filter mapping ───────────────────────────────────────────────────────
  const { matched, unmatched } = buildQueryParameters(dashParams, filterParams);

  console.log(`\nDashboard parameters (${dashParams.length}):`);
  if (!dashParams.length && !Object.keys(filterParams).length) {
    console.log('  (không có filter nào — dashboard dùng date cứng trong SQL)');
  }
  for (const p of matched)
    console.log(`  ✓ [${p.type}] "${p.slug}" = "${p.value}"`);
  for (const slug of unmatched)
    console.log(`  ⚠️  slug="${slug}" không có trong dashboard parameters`);
  for (const p of dashParams) {
    if (!matched.find(m => m.id === p.id))
      console.log(`  ○ [${p.type}] "${p.slug}" = (không filter — show all)`);
  }

  console.log(`\nCards: ${dataCards.length} data cards | ${dashcards.length - dataCards.length} text/heading`);

  // ── Build parameter payload ───────────────────────────────────────────────
  const queryParams = matched.map(p => ({ id: p.id, type: p.type, value: p.value }));

  // ── SUMMARY mode (default) ───────────────────────────────────────────────
  if (!targetCard && !allMode) {
    console.log(`\n${'─'.repeat(70)}`);
    console.log('SUMMARY — chạy tất cả cards để lấy row count\n');

    const summary = [];
    let idx = 0;
    for (const dc of dataCards) {
      idx++;
      const cardId   = dc.card_id;
      const cardName = dc.card?.name || `Card ${cardId}`;
      const tab      = tabs.find(t => t.id === dc.dashboard_tab_id);
      const tabName  = tab ? tab.name : '—';

      process.stdout.write(`  [${idx}/${dataCards.length}] ${cardName}... `);

      const { queryResponse, execError } = await executeCard(core, dashboardId, dc, queryParams);

      let status, rowCount = 0;
      if (execError) {
        status = `❌ ERROR: ${execError.slice(0, 80)}`;
      } else {
        const r = extractResults(queryResponse);
        rowCount = r.total;
        status = rowCount === 0 ? '⚠️  0 rows' : `✓  ${rowCount} row(s)`;
      }
      console.log(status);
      summary.push({ cardId, cardName, tabName, rowCount, error: execError || null });
    }

    console.log(`\n${SEP}`);
    console.log('BẢNG TÓM TẮT:');
    console.log(`${'Card ID'.padEnd(10)} ${'Tab'.padEnd(22)} ${'Rows'.padEnd(8)} Card name`);
    console.log('─'.repeat(70));
    for (const s of summary) {
      const flag = s.error ? '❌' : s.rowCount === 0 ? '⚠️ ' : '✓ ';
      console.log(`${String(s.cardId).padEnd(10)} ${s.tabName.padEnd(22)} ${String(s.rowCount).padEnd(8)} ${flag} ${s.cardName}`);
    }
    console.log(`\n${SEP}`);
    console.log('→ Để deep-dive một card cụ thể:');
    console.log(`  node scripts/debug/metabase-dashboard-debugger.js "${rawUrl}" --card <card_id>`);
    console.log(SEP);
    return;
  }

  // ── DEEP-DIVE mode (--card <id> hoặc --all) ──────────────────────────────
  const targetCards = targetCard
    ? dataCards.filter(dc => dc.card_id === targetCard)
    : dataCards;

  if (targetCard && !targetCards.length) {
    console.error(`❌  Card ID ${targetCard} không tìm thấy trong dashboard này.`);
    console.log(`Cards có sẵn: ${dataCards.map(dc => `${dc.card_id}(${dc.card?.name})`).join(', ')}`);
    process.exit(1);
  }

  let idx = 0;
  for (const dc of targetCards) {
    idx++;
    const tab      = tabs.find(t => t.id === dc.dashboard_tab_id);
    const tabName  = tab ? tab.name : '—';
    const cardName = dc.card?.name || `Card ${dc.card_id}`;

    console.log(`\n${DASH}`);
    console.log(`Card ${idx}/${targetCards.length}: "${cardName}"`);
    console.log(`card_id=${dc.card_id} | dashcard_id=${dc.id} | tab="${tabName}"`);

    printMappings(dc.parameter_mappings || [], dashParams, matched);

    const { card, queryResponse, execError } = await executeCard(core, dashboardId, dc, queryParams);

    const templateSql = card?.dataset_query?.native?.query
      || card?.dataset_query?.stages?.[0]?.native;
    if (templateSql) printSql('SQL TEMPLATE', templateSql);

    if (execError) {
      console.log(`\n[KẾT QUẢ] ❌ Lỗi: ${execError}`);
      continue;
    }

    const actualSql = extractNativeSql(queryResponse, card);
    if (actualSql && actualSql !== templateSql)
      printSql('SQL THỰC TẾ (sau substitute)', actualSql);

    const { columns, rows, total } = extractResults(queryResponse);
    printResults(columns, rows, total);
  }

  console.log(`\n${SEP}\nDebug hoàn tất.\n${SEP}`);
}

main().catch(err => { console.error('Fatal:', err.message); process.exit(1); });
