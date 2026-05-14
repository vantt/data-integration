/**
 * upgrade-chu-ky-to-dynamic-sql.js
 *
 * Replaces the static text card "Chu kỳ báo cáo" in each blueprint with a
 * SQL question card that dynamically computes the full date range at query time.
 * Also fixes first-tab row positions (+1) so that layout matches what the
 * previous add-chu-ky-bao-cao-widget.js script already applied in Metabase.
 *
 * After patching blueprints, runs deploy_from_markdown.js for each unique file.
 *
 * Usage:
 *   node tools/upgrade-chu-ky-to-dynamic-sql.js [--dry-run]
 */

const fs   = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const BLUEPRINTS_DIR = path.join(__dirname, '..', 'docs', 'analytics-handbook', 'blueprints');
const DEPLOY_SCRIPT  = path.join(__dirname, '..', '.skills', 'metabase-automation', 'scripts', 'deploy_from_markdown.js');
const DRY_RUN        = process.argv.includes('--dry-run');

// ── SQL templates per period type ─────────────────────────────────────────────

const SQL = {
  daily: `\
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"`,

  yesterday: `\
SELECT
  '📅 Hôm qua: ' || strftime(current_date - 1, '%d/%m/%Y') ||
  '  ·  So sánh: ' || strftime(current_date - 8, '%d/%m/%Y') || ' (D-8, WoW)'
  AS "Chu kỳ báo cáo"`,

  weekly: `\
SELECT
  '📅 Tuần qua: ' ||
  strftime(date_trunc('week', current_date)::DATE - 7, '%d/%m/%Y') || ' – ' ||
  strftime(date_trunc('week', current_date)::DATE - 1, '%d/%m/%Y') ||
  '  ·  WoW: ' ||
  strftime(date_trunc('week', current_date)::DATE - 14, '%d/%m/%Y') || ' – ' ||
  strftime(date_trunc('week', current_date)::DATE - 8, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"`,

  monthly: `\
SELECT
  '📅 Tháng trước: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 day')::DATE, '%d/%m/%Y') ||
  '  ·  MoM: ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '2 months')::DATE, '%d/%m/%Y') || ' – ' ||
  strftime((date_trunc('month', current_date) - INTERVAL '1 month' - INTERVAL '1 day')::DATE, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"`,

  rolling30: `\
SELECT
  '📅 30 ngày gần nhất: ' ||
  strftime(current_date - 29, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  So sánh: ' ||
  strftime(current_date - 59, '%d/%m/%Y') || ' – ' || strftime(current_date - 30, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"`,

  ingestion: `\
SELECT
  '📅 Hôm nay: ' || strftime(current_date, '%d/%m/%Y') ||
  '  ·  Trend 30 ngày: ' ||
  strftime(current_date - 29, '%d/%m/%Y') || ' – ' || strftime(current_date, '%d/%m/%Y')
  AS "Chu kỳ báo cáo"`,

  shopee: `\
SELECT '📅 Kỳ quyết toán Shopee — xem tab Settlement để biết ngày chính xác'
  AS "Chu kỳ báo cáo"`,

  on_demand: `\
SELECT '📅 Chu kỳ: Theo filter được chọn (không cố định)'
  AS "Chu kỳ báo cáo"`,
};

// ── Blueprint → period type ────────────────────────────────────────────────────

const BLUEPRINT_PERIOD = {
  'b2b_sales_daily.md':                    'daily',
  'b2b_orders_tracking.md':                'rolling30',
  'ceo_monthly_scorecard.md':              'monthly',
  'ceo_weekly_pulse.md':                   'weekly',
  'channel_profitability_monthly.md':      'monthly',
  'customer_intelligence_monthly.md':      'monthly',
  'customer_operational_dashboard.md':     'rolling30',
  'customer_retention_dashboard.md':       'rolling30',
  'customer_support_social_commerce.md':   'daily',
  'finance_pl.md':                         'monthly',
  'ingestion_health.md':                   'ingestion',
  'logistics_operations.md':               'daily',
  'marketing_monthly_analysis.md':         'monthly',
  'marketing_roi.md':                      'monthly',
  'marketing_weekly_tracker.md':           'weekly',
  'order_detail.md':                       'on_demand',
  'order_listing.md':                      'on_demand',
  'order_profitability.md':                'monthly',
  'product_performance.md':                'monthly',
  'product_profitability.md':              'rolling30',
  'sales_daily_operation.md':              'daily',
  'sales_monthly_review.md':               'monthly',
  'sales_ops_monthly_summary.md':          'monthly',
  'sales_ops_weekly_review.md':            'weekly',
  'sales_promotion_analysis.md':           'rolling30',
  'sales_yesterday_operation.md':          'yesterday',
  'shopee_channel_economics.md':           'shopee',
  'us_crossborder_operations.md':          'daily',
};

// ── Blueprint transformer ──────────────────────────────────────────────────────

/**
 * Detect where the first tab's content ends (before the second tab heading or end of file).
 * Returns the index in `lines` of the first line that is NOT in the first tab.
 */
function firstTabEndLine(lines) {
  let seenFirstTab = false;
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (/^###\s+(?:📑\s+)?Tab:/.test(t)) {
      if (!seenFirstTab) { seenFirstTab = true; continue; }
      return i; // second tab heading → first tab ends here
    }
  }
  return lines.length; // no second tab → whole file is first tab
}

/**
 * Build the replacement snippet for the chu-ky SQL question card.
 */
function buildQuestionSnippet(sql) {
  return [
    '#### ❓ Question: Chu kỳ báo cáo',
    '',
    '```sql',
    sql,
    '```',
    '',
    '```json metabase-viz',
    '{ "display": "scalar", "visualization_settings": {} }',
    '```',
    '',
    '```json metabase-pos',
    '{ "row": 0, "col": 0, "size_x": 18, "size_y": 1 }',
    '```',
    '',
  ].join('\n');
}

/**
 * Patch a blueprint file:
 *  1. Replace the chu-ky text card section with a SQL question card.
 *  2. Increment "row" by 1 for all other first-tab metabase-pos blocks.
 */
function patchBlueprint(filePath, periodType) {
  const original = fs.readFileSync(filePath, 'utf8');
  const lines = original.split('\n');

  // ── Step 1: locate and replace the chu-ky text card section ─────────────
  // The section starts at '#### 📝 Text: Chu kỳ báo cáo' and ends just before
  // the next '####' heading.
  let chuKyStart = -1;
  let chuKyEnd   = -1;

  for (let i = 0; i < lines.length; i++) {
    if (/^####\s+(?:📝\s+)?Text:\s*Chu kỳ báo cáo/.test(lines[i])) {
      chuKyStart = i;
      // find next #### heading or end of file
      for (let j = i + 1; j < lines.length; j++) {
        if (/^####/.test(lines[j])) { chuKyEnd = j; break; }
      }
      if (chuKyEnd === -1) chuKyEnd = lines.length;
      break;
    }
  }

  if (chuKyStart === -1) {
    console.log(`  ⚠️  No chu-ky text card found in ${path.basename(filePath)}`);
    return false;
  }

  // Build replacement snippet lines
  const snippet = buildQuestionSnippet(SQL[periodType]);
  const snippetLines = snippet.split('\n');
  // Remove trailing blank line from snippet to avoid double blank
  while (snippetLines.length && snippetLines[snippetLines.length - 1] === '') snippetLines.pop();

  // Replace chu-ky section with question snippet
  const rebuilt = [
    ...lines.slice(0, chuKyStart),
    ...snippetLines,
    '',
    ...lines.slice(chuKyEnd),
  ];

  // ── Step 2: increment rows of other first-tab metabase-pos blocks ────────
  // Determine first-tab boundary in rebuilt array
  const tabEnd = firstTabEndLine(rebuilt);

  // Adjust chuKyEnd in rebuilt coords: snippet replaced lines[chuKyStart..chuKyEnd)
  const newChuKyEnd = chuKyStart + snippetLines.length + 1; // +1 for blank line

  for (let i = newChuKyEnd; i < tabEnd; i++) {
    if (rebuilt[i].trim() === '```json metabase-pos') {
      // Next line should be the JSON
      const j = i + 1;
      if (j < rebuilt.length) {
        try {
          const pos = JSON.parse(rebuilt[j]);
          pos.row += 1;
          rebuilt[j] = JSON.stringify(pos).replace(/,/g, ', '); // compact but readable
        } catch (_) { /* skip malformed */ }
      }
    }
  }

  const patched = rebuilt.join('\n');

  if (!DRY_RUN) {
    fs.writeFileSync(filePath, patched, 'utf8');
  }
  return true;
}

/**
 * Find the line index where first-tab content begins (the first #### after
 * the first ### Tab: heading, skipping --- separators and blank lines).
 * For blueprints without tab headings, returns the first #### in the file.
 */
function firstTabContentStart(lines) {
  let foundFirstTab = false;
  for (let i = 0; i < lines.length; i++) {
    const t = lines[i].trim();
    if (/^###\s+(?:📑\s+)?Tab:/.test(t)) {
      foundFirstTab = true;
      // Scan forward: skip blank lines and --- separators
      for (let j = i + 1; j < lines.length; j++) {
        const jt = lines[j].trim();
        if (jt === '' || jt === '---') continue;
        if (/^####/.test(jt)) return j;   // first #### in first tab
        if (/^###/.test(jt)) break;        // hit next ### before any #### — stop
      }
      break;
    }
  }
  // No tab heading: find first #### in file
  for (let i = 0; i < lines.length; i++) {
    if (/^####/.test(lines[i].trim())) return i;
  }
  return lines.length;
}

/**
 * Fully reposition the chu-ky SQL question card into the correct slot:
 *  1. Extract the chu-ky question section from wherever it currently is.
 *  2. Re-insert it as the very first card in the first tab.
 *  3. Apply +1 to all other first-tab metabase-pos rows.
 */
function fixChuKyPlacement(filePath, periodType) {
  let lines = fs.readFileSync(filePath, 'utf8').split('\n');

  // ── 1. Remove existing chu-ky question section ──────────────────────────
  let chuKyStart = -1, chuKyEnd = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^####\s+(?:❓\s+)?Question:\s*Chu kỳ báo cáo/.test(lines[i])) {
      chuKyStart = i;
      for (let j = i + 1; j < lines.length; j++) {
        if (/^####/.test(lines[j]) || /^###/.test(lines[j])) { chuKyEnd = j; break; }
      }
      if (chuKyEnd === -1) chuKyEnd = lines.length;
      break;
    }
  }

  // Remove stale static text card too (in case it still exists)
  let textStart = -1, textEnd = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^####\s+(?:📝\s+)?Text:\s*Chu kỳ báo cáo/.test(lines[i])) {
      textStart = i;
      for (let j = i + 1; j < lines.length; j++) {
        if (/^####/.test(lines[j]) || /^###/.test(lines[j])) { textEnd = j; break; }
      }
      if (textEnd === -1) textEnd = lines.length;
      break;
    }
  }

  if (chuKyStart === -1 && textStart === -1) {
    console.log(`  ⚠️  No chu-ky section found at all — skip`);
    return false;
  }

  // Remove both (higher index first to preserve lower indices)
  const removals = [];
  if (chuKyStart !== -1) removals.push([chuKyStart, chuKyEnd]);
  if (textStart  !== -1) removals.push([textStart,  textEnd]);
  removals.sort((a, b) => b[0] - a[0]);
  for (const [s, e] of removals) {
    // Also strip surrounding blank lines
    let start = s, end = e;
    while (start > 0 && lines[start - 1].trim() === '') start--;
    lines.splice(start, end - start);
  }

  // ── 2. Build fresh snippet ───────────────────────────────────────────────
  const snippetLines = buildQuestionSnippet(SQL[periodType]).split('\n');
  while (snippetLines.length && snippetLines[snippetLines.length - 1] === '') snippetLines.pop();

  // ── 3. Insert at start of first tab ─────────────────────────────────────
  const insertAt = firstTabContentStart(lines);
  lines.splice(insertAt, 0, ...snippetLines, '');

  // ── 4. Apply +1 to all first-tab cards AFTER the inserted chu-ky ─────────
  const newChuKyEnd = insertAt + snippetLines.length + 1;
  const tabEnd = firstTabEndLine(lines);

  let changed = 0;
  for (let i = newChuKyEnd; i < tabEnd; i++) {
    if (lines[i].trim() === '```json metabase-pos') {
      const j = i + 1;
      if (j < lines.length) {
        try {
          const pos = JSON.parse(lines[j]);
          pos.row += 1;
          lines[j] = JSON.stringify(pos).replace(/,/g, ', ');
          changed++;
        } catch (_) { /* skip */ }
      }
    }
  }

  if (!DRY_RUN) fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
  console.log(`  ✅ Repositioned chu-ky to tab 1 + fixed ${changed} row(s)`);
  return true;
}

/**
 * Fix rows-only: for already-correctly-placed blueprints, apply +1 to all
 * first-tab metabase-pos blocks that come AFTER the chu-ky question section.
 */
function fixRowsOnly(filePath) {
  const original = fs.readFileSync(filePath, 'utf8');
  const lines = original.split('\n');

  // Find end of chu-ky question section
  let chuKySectionEnd = -1;
  for (let i = 0; i < lines.length; i++) {
    if (/^####\s+(?:❓\s+)?Question:\s*Chu kỳ báo cáo/.test(lines[i])) {
      for (let j = i + 1; j < lines.length; j++) {
        if (/^####/.test(lines[j]) || /^###/.test(lines[j])) { chuKySectionEnd = j; break; }
      }
      break;
    }
  }
  if (chuKySectionEnd === -1) {
    console.log(`  ⚠️  No chu-ky question in tab 1 — use --reposition instead`);
    return false;
  }

  const tabEnd = firstTabEndLine(lines);
  const patched = [...lines];
  let changed = 0;

  for (let i = chuKySectionEnd; i < tabEnd; i++) {
    if (patched[i].trim() === '```json metabase-pos') {
      const j = i + 1;
      if (j < patched.length) {
        try {
          const pos = JSON.parse(patched[j]);
          pos.row += 1;
          patched[j] = JSON.stringify(pos).replace(/,/g, ', ');
          changed++;
        } catch (_) { /* skip */ }
      }
    }
  }

  if (changed === 0) {
    console.log(`  ℹ️  Rows already correct`);
    return false;
  }

  if (!DRY_RUN) fs.writeFileSync(filePath, patched.join('\n'), 'utf8');
  console.log(`  ✅ Fixed ${changed} row positions (+1)`);
  return true;
}

// ── Deploy runner ──────────────────────────────────────────────────────────────

function deploy(blueprintFile) {
  const filePath = path.join(BLUEPRINTS_DIR, blueprintFile);
  const env = {
    ...process.env,
    METABASE_URL:     process.env.METABASE_URL     || 'http://127.0.0.1:3001/',
    METABASE_API_KEY: process.env.METABASE_API_KEY || 'mb_buAQN9X7jRNYeum74PRgIJIirdmXM9hy2IDLDJtAmmA=',
    METABASE_DB_NAME: process.env.METABASE_DB_NAME || 'Sapo',
  };
  try {
    const out = execSync(
      `node "${DEPLOY_SCRIPT}" "${filePath}"`,
      { env, encoding: 'utf8', stdio: 'pipe' }
    );
    // Show last few lines of deploy output
    const tail = out.trim().split('\n').slice(-4).join('\n');
    console.log(`  🚀 Deployed:\n${tail.split('\n').map(l=>'     '+l).join('\n')}`);
    return true;
  } catch (e) {
    const errOut = (e.stdout || '') + (e.stderr || '');
    console.error(`  ❌ Deploy failed:\n${errOut.slice(0, 600)}`);
    return false;
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────

function main() {
  const deployOnly  = process.argv.includes('--deploy-only');
  const fixRowsMode = process.argv.includes('--fix-rows');
  const mode = DRY_RUN ? 'DRY-RUN' : deployOnly ? 'deploy-only' : fixRowsMode ? 'fix-rows+deploy' : 'full';
  console.log(`🚀  Mode: ${mode}\n`);

  const files = Object.keys(BLUEPRINT_PERIOD);
  let patched = 0, rowFixed = 0, deployed = 0, errors = 0;

  for (const bpFile of files) {
    const periodType = BLUEPRINT_PERIOD[bpFile];
    const filePath   = path.join(BLUEPRINTS_DIR, bpFile);

    if (!fs.existsSync(filePath)) {
      console.log(`[SKIP] ${bpFile} — file not found`);
      continue;
    }

    console.log(`\n[${bpFile}]`);

    if (!deployOnly && !fixRowsMode) {
      // Full patch: replace text card + shift rows
      const ok = patchBlueprint(filePath, periodType);
      if (ok) { patched++; console.log(`  ✅ Blueprint patched`); }
      else       console.log(`  ℹ️  Already patched or no chu-ky text section found`);
    }

    if (fixRowsMode) {
      // Row-fix only (blueprints already have the SQL question card)
      const ok = fixRowsOnly(filePath);
      if (ok) {
        rowFixed++;
      } else {
        // chu-ky is in wrong tab — reposition it
        const ok2 = fixChuKyPlacement(filePath, periodType);
        if (ok2) rowFixed++;
      }
    }

    if (!DRY_RUN) {
      const ok2 = deploy(bpFile);
      if (ok2) deployed++;
      else errors++;
    }
  }

  console.log('\n══════════════════════════════════════════════════════');
  if (!deployOnly && !fixRowsMode) console.log(`✅  Blueprints patched:  ${patched}`);
  if (fixRowsMode)                  console.log(`🔧  Row positions fixed: ${rowFixed}`);
  console.log(`🚀  Deployed:            ${deployed}`);
  console.log(`❌  Errors:              ${errors}`);
}

main();
