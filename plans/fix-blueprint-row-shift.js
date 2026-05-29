#!/usr/bin/env node
/**
 * Fix blueprint metabase-pos row conflicts.
 *
 * In tabs that have BOTH:
 *   - cycle-indicator (Chu kỳ báo cáo) at row=0
 *   - another card also at row=0
 *
 * Shift all non-cycle-indicator pos blocks:
 *   row == 0     → 2
 *   1 <= row <= 89 → row + 2
 *   row >= 90    → unchanged (source-freshness pins stay at 99)
 *
 * Handles both LF and CRLF line endings.
 */

const fs = require('fs');
const path = require('path');

// ---- Config ---------------------------------------------------------------

const BLUEPRINTS_DIR = 'D:/Vantt/app/data-integration/docs/analytics-handbook/blueprints';

const FILES = [
  'sales_ops_weekly_review.md',
  'sales_ops_monthly_summary.md',
  'marketing_monthly_analysis.md',
  'customer_retention_dashboard.md',
  'customer_intelligence_monthly.md',
  'order_listing.md',
  'logistics_operations.md',
  'product_performance.md',
  'sales_monthly_review.md',
  'shopee_channel_economics.md',
  'channel_profitability_monthly.md',
  'finance_pl.md',
  'order_profitability_all.md',
  'ingestion_health.md',
  'sales_daily_operation.md',
  'sales_yesterday_operation.md',
  'ceo_monthly_scorecard.md',
  'sales_promotion_analysis.md',
  'marketing_weekly_tracker.md',
  'customer_operational_dashboard.md',
  'b2b_sales_daily.md',
  'b2b_orders_tracking.md',
];

// ---- Regex Helpers ---------------------------------------------------------

// Matches a complete ```json metabase-pos ... ``` block (CRLF-aware)
// Groups: [1] = inner JSON text (may have trailing \r stripped)
function makePosBlockRe() {
  return /```json metabase-pos\r?\n(\{[^`]+\})\r?\n```/g;
}

// ---- Core Logic ------------------------------------------------------------

/**
 * Find the START index of the metabase-pos block that belongs to the
 * cycle-indicator question within `tabText`.
 *
 * Strategy: find "#### ❓ Question: Chu kỳ báo cáo" then locate the FIRST
 * metabase-pos block before the next #### heading.
 *
 * Returns offset (character index in tabText), or -1 if not found.
 */
function findCycleIndicatorPosOffset(tabText) {
  const cycleHeadingRe = /#### ❓ Question: Chu kỳ báo cáo/;
  const headingMatch = cycleHeadingRe.exec(tabText);
  if (!headingMatch) return -1;

  // Find the next #### heading after cycle-indicator section
  const afterCycleStart = headingMatch.index + headingMatch[0].length;
  const nextHeadingRe = /####/g;
  nextHeadingRe.lastIndex = afterCycleStart;
  const nextHeadingMatch = nextHeadingRe.exec(tabText);
  const sectionEnd = nextHeadingMatch ? nextHeadingMatch.index : tabText.length;

  // Find first metabase-pos block in [afterCycleStart, sectionEnd]
  const posRe = makePosBlockRe();
  posRe.lastIndex = afterCycleStart;
  let m;
  while ((m = posRe.exec(tabText)) !== null) {
    if (m.index < sectionEnd) {
      return m.index;
    }
    break; // past section end
  }
  return -1;
}

/**
 * Collect all metabase-pos blocks in a tab section.
 * Returns array of { index, fullMatch, jsonStr }
 */
function collectPosBlocks(tabText) {
  const blocks = [];
  const re = makePosBlockRe();
  let m;
  while ((m = re.exec(tabText)) !== null) {
    // Strip trailing \r from JSON string if present (CRLF files)
    const jsonStr = m[1].replace(/\r/g, '');
    blocks.push({ index: m.index, fullMatch: m[0], jsonStr });
  }
  return blocks;
}

/**
 * Apply row shift rule:
 *   0 → 2, 1–89 → +2, >=90 → unchanged
 */
function shiftRow(row) {
  if (row === 0) return 2;
  if (row >= 1 && row <= 89) return row + 2;
  return row;
}

/**
 * Rebuild a metabase-pos block string preserving the original formatting style.
 * Detects single-line vs multi-line JSON and replicates the style.
 */
function rebuildPosBlock(originalJsonStr, newObj, originalFullMatch) {
  // Detect formatting by inspecting original full block
  const isMultiLine = originalFullMatch.includes('\n  ') || originalFullMatch.includes('\r\n  ');

  let newJsonStr;
  if (isMultiLine) {
    newJsonStr = JSON.stringify(newObj, null, 2);
  } else {
    // Compact single-line: preserve key order from original
    const keys = Object.keys(newObj);
    const parts = keys.map(k => `"${k}": ${JSON.stringify(newObj[k])}`);
    newJsonStr = '{ ' + parts.join(', ') + ' }';
  }

  // Detect original line ending style
  const lineEnding = originalFullMatch.includes('\r\n') ? '\r\n' : '\n';
  return '```json metabase-pos' + lineEnding + newJsonStr + lineEnding + '```';
}

/**
 * Process a single tab section.
 * Returns { newTabText, changed, fixedBlocks, details[] }
 */
function processTab(tabText, tabName) {
  const result = { newTabText: tabText, changed: false, fixedBlocks: 0, details: [] };

  if (!/#### ❓ Question: Chu kỳ báo cáo/.test(tabText)) {
    return result;
  }

  const cycleOffset = findCycleIndicatorPosOffset(tabText);
  if (cycleOffset === -1) {
    return result;
  }

  const allBlocks = collectPosBlocks(tabText);
  const nonCycleBlocks = allBlocks.filter(b => b.index !== cycleOffset);

  // Check for conflict: any non-cycle block at row=0?
  const hasConflict = nonCycleBlocks.some(b => {
    try { return JSON.parse(b.jsonStr).row === 0; } catch { return false; }
  });

  if (!hasConflict) {
    return result;
  }

  // Apply shifts to non-cycle blocks — process in reverse order to preserve offsets
  let text = tabText;
  const sorted = [...nonCycleBlocks].sort((a, b) => b.index - a.index);

  for (const block of sorted) {
    let obj;
    try { obj = JSON.parse(block.jsonStr); } catch (e) {
      console.warn(`  WARN: JSON parse failed in "${tabName}": ${block.jsonStr.slice(0, 80)}`);
      continue;
    }

    const oldRow = obj.row;
    const newRow = shiftRow(oldRow);
    if (newRow === oldRow) continue; // >=90, skip

    obj.row = newRow;
    const newBlock = rebuildPosBlock(block.jsonStr, obj, block.fullMatch);

    text = text.slice(0, block.index) + newBlock + text.slice(block.index + block.fullMatch.length);
    result.details.push({ oldRow, newRow });
    result.fixedBlocks++;
  }

  if (result.fixedBlocks > 0) {
    result.newTabText = text;
    result.changed = true;
  }

  return result;
}

/**
 * Process a single file.
 * Returns summary object.
 */
function processFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const fileName = path.basename(filePath);

  // Split into tab sections
  // Match tab header lines including the line break
  const TAB_SPLIT_RE = /### 📑 Tab:[^\r\n]*\r?\n/g;
  const tabHeaders = [];
  let m;
  while ((m = TAB_SPLIT_RE.exec(content)) !== null) {
    tabHeaders.push({ index: m.index, header: m[0] });
  }

  if (tabHeaders.length === 0) {
    return { fileName, tabsFixed: 0, fixedTabNames: [], noTabs: true };
  }

  const preamble = content.slice(0, tabHeaders[0].index);
  const tabSections = [];

  for (let i = 0; i < tabHeaders.length; i++) {
    const start = tabHeaders[i].index;
    const end = i + 1 < tabHeaders.length ? tabHeaders[i + 1].index : content.length;
    const tabName = tabHeaders[i].header
      .replace('### 📑 Tab:', '')
      .replace(/\r?\n/, '')
      .trim();
    tabSections.push({ tabName, text: content.slice(start, end) });
  }

  let anyChanged = false;
  const fixedTabNames = [];

  const processedSections = tabSections.map(section => {
    const result = processTab(section.text, section.tabName);
    if (result.changed) {
      anyChanged = true;
      fixedTabNames.push({ name: section.tabName, blocks: result.fixedBlocks, details: result.details });
    }
    return result.newTabText;
  });

  if (anyChanged) {
    const newContent = preamble + processedSections.join('');
    fs.writeFileSync(filePath, newContent, 'utf8');
  }

  return { fileName, tabsFixed: fixedTabNames.length, fixedTabNames, noTabs: false };
}

// ---- Main ------------------------------------------------------------------

function main(testOnly = false) {
  const filesToProcess = testOnly ? ['ceo_monthly_scorecard.md'] : FILES;
  const results = [];

  for (const fileName of filesToProcess) {
    const filePath = path.join(BLUEPRINTS_DIR, fileName);
    if (!fs.existsSync(filePath)) {
      console.log(`SKIP (not found): ${fileName}`);
      results.push({ fileName, skipped: true });
      continue;
    }

    const result = processFile(filePath);
    results.push(result);

    if (result.noTabs) {
      console.log(`OK (no tabs): ${fileName}`);
      continue;
    }

    if (result.tabsFixed === 0) {
      console.log(`OK (no fix needed): ${fileName}`);
    } else {
      console.log(`FIXED: ${fileName} — ${result.tabsFixed} tab(s):`);
      for (const t of result.fixedTabNames) {
        const rowChanges = t.details.map(d => `${d.oldRow}→${d.newRow}`).join(', ');
        console.log(`  - "${t.name}" (${t.blocks} blocks: ${rowChanges})`);
      }
    }
  }

  console.log('\n--- Summary ---');
  const fixed = results.filter(r => !r.skipped && r.tabsFixed > 0);
  const clean = results.filter(r => !r.skipped && r.tabsFixed === 0);
  console.log(`Fixed: ${fixed.length} file(s)`);
  console.log(`Already correct / no change needed: ${clean.length} file(s)`);

  return results;
}

const args = process.argv.slice(2);
const testMode = args.includes('--test');

if (testMode) {
  console.log('=== TEST MODE: ceo_monthly_scorecard.md only ===\n');
}

main(testMode);
