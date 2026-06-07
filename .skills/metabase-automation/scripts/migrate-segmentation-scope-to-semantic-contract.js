#!/usr/bin/env node
/**
 * One-time migration: replace ## Segmentation Scope with ## Semantic Contract
 * in all blueprint files.
 *
 * Usage: node migrate-segmentation-scope-to-semantic-contract.js [--dry-run]
 *
 * What it does:
 *   1. Parse frontmatter (primary_scope, scope_indicator, layer, uses_concepts)
 *   2. Find ## Segmentation Scope section
 *   3. Extract "Why" text + SQL guidance line
 *   4. Replace with ## Semantic Contract format (overview link + scope + why + concepts)
 *   5. Write back (or print diff in --dry-run)
 */

const fs = require('fs');
const path = require('path');

const BLUEPRINTS_DIR = path.resolve(__dirname, '../../../docs/analytics-handbook/blueprints');
const DRY_RUN = process.argv.includes('--dry-run');

// Maps concept names to their semantic file + anchor.
const CONCEPT_FILE_MAP = {
  scope_sales: 'segments.md#scope_sales',
  scope_retail: 'segments.md#scope_retail',
  scope_b2b: 'segments.md#scope_b2b',
  filter_us: 'segments.md#filter_us',
  filter_internal: 'segments.md#filter_internal',
  filter_social: 'segments.md#filter_social',
  filter_has_cogs: 'segments.md#filter_has_cogs',
  net_revenue: 'metrics.md#net_revenue',
  gross_revenue: 'metrics.md#gross_revenue',
  total_collected: 'metrics.md#total_collected',
  gross_profit: 'metrics.md#gross_profit',
  cogs_amount: 'metrics.md#cogs_amount',
  aov: 'metrics.md#aov',
  discount_rate: 'metrics.md#discount_rate',
  discount_amount: 'metrics.md#discount_amount',
  orders_count: 'metrics.md#orders_count',
  return_rate: 'metrics.md#return_rate',
  channel_net_profit: 'metrics.md#channel_net_profit',
  customer_acquisition: 'metrics.md#customer_acquisition',
  retention_rate: 'metrics.md#retention_rate',
  repeat_buyer_rate: 'metrics.md#repeat_buyer_rate',
  marketing_spend: 'metrics.md#marketing_spend',
  roas: 'metrics.md#roas',
  service_fee_revenue: 'metrics.md#service_fee_revenue',
  shopee_service_fee: 'metrics.md#shopee_service_fee',
  fulfillment_status: 'dimensions.md#fulfillment_status',
  inventory_quantity: 'metrics.md#inventory_quantity',
  inventory_value: 'metrics.md#inventory_value',
};

function buildConceptLinks(concepts) {
  if (!concepts || concepts.length === 0) return null;
  return concepts.map(c => {
    const file = CONCEPT_FILE_MAP[c] || `segments.md#${c}`;
    return `[\`${c}\`](../semantic/${file})`;
  }).join(' · ');
}

// Parse simple YAML frontmatter (key: value or key: [a, b, c] or key:\n  - a\n  - b)
function parseFrontmatter(content) {
  // Normalize CRLF — JavaScript's `.` doesn't match `\r`, breaking `(.*)$` on CRLF lines.
  const c = content.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  if (!c.startsWith('---')) return null;
  const end = c.indexOf('\n---', 3);
  if (end === -1) return null;
  const fm = c.slice(4, end);
  const result = {};
  const lines = fm.split('\n');
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    const kvMatch = line.match(/^(\w+):\s*(.*)$/);
    if (!kvMatch) { i++; continue; }
    const key = kvMatch[1];
    let val = kvMatch[2].trim();

    if (val === '[]') {
      result[key] = [];
      i++;
      continue;
    } else if (val === '') {
      // Check for multi-line list (- item)
      const items = [];
      i++;
      while (i < lines.length && lines[i].match(/^\s+-\s+(.+)$/)) {
        items.push(lines[i].match(/^\s+-\s+(.+)$/)[1].trim());
        i++;
      }
      // If no list items follow, it's an empty scalar (not an empty array)
      result[key] = items.length > 0 ? items : '';
      continue;
    } else if (val.startsWith('[') && val.endsWith(']')) {
      val = val.slice(1, -1).split(',').map(s => s.trim()).filter(Boolean);
      result[key] = val;
    } else {
      result[key] = val;
    }
    i++;
  }
  return result;
}

// Extract "Why" text from existing section content
function extractWhy(sectionBody) {
  // Look for > **Why:** text (single line)
  const whyMatch = sectionBody.match(/>\s*\*\*Why:\*\*\s*(.+)/);
  if (whyMatch) return whyMatch[1].trim();
  return null;
}

// Extract the SQL guidance line(s) — preserve verbatim
function extractSqlLines(sectionBody) {
  const lines = [];
  for (const line of sectionBody.split('\n')) {
    // Catch "All SQL:", "Revenue SQL:", "P&L SQL:", "Inventory queries..."
    if (/^(All|Revenue|P&L|[A-Z][a-z]+ (?:SQL|queries))/i.test(line.trim()) && line.trim().length > 3) {
      lines.push(line.trim());
    }
  }
  return lines.length > 0 ? lines : null;
}

// Build the scope declaration line for the blockquote
function buildScopeLine(fm) {
  const primary = (fm.primary_scope || '').trim();
  const indicator = (fm.scope_indicator || '').replace(/"/g, '').trim();
  const layer = (fm.layer || '').trim();
  const concepts = Array.isArray(fm.uses_concepts) ? fm.uses_concepts : [];

  if (!primary || primary === 'none') {
    return null; // caller handles N/A case
  }

  // Build scope string with optional filter_has_cogs
  let scopeStr = `\`${primary}\``;
  if (concepts.includes('filter_has_cogs') && primary !== 'filter_has_cogs') {
    scopeStr += ' + `filter_has_cogs`';
  }

  // Layer display
  const layerDisplay = layer || 'TODO';

  // Ref links for primary scope + filter_has_cogs if applicable
  const refParts = [primary];
  if (concepts.includes('filter_has_cogs') && primary !== 'filter_has_cogs') {
    refParts.push('filter_has_cogs');
  }
  const refLinks = refParts.map(s => {
    const file = CONCEPT_FILE_MAP[s] || `segments.md#${s}`;
    return `[\`segments.md#${s}\`](../semantic/${file})`;
  }).join(' · ');

  const indicatorPart = indicator ? ` \`${indicator}\`` : '';
  return `> **Scope:** ${scopeStr} · Layer ${layerDisplay}${indicatorPart} · ${refLinks}`;
}

// Build the full ## Semantic Contract section
function buildSemanticContractSection(fm, existingBody) {
  const primary = (fm.primary_scope || '').trim();
  const concepts = Array.isArray(fm.uses_concepts) ? fm.uses_concepts : [];
  const why = extractWhy(existingBody);
  const sqlLines = extractSqlLines(existingBody);

  const overviewLine = '> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.';
  const scopeLine = buildScopeLine(fm);

  let blockquote;
  if (!scopeLine) {
    // N/A scope (none, empty, L0/Internal with no scope)
    // Try to preserve the plain N/A description
    const naDesc = existingBody
      .replace(/##\s+Segmentation Scope\s*/i, '')
      .split('\n')
      .filter(l => !l.startsWith('>') && l.trim().length > 0)
      .slice(0, 1)
      .join(' ')
      .trim();
    const naLine = naDesc.length > 0 ? `N/A — ${naDesc.replace(/^N\/A\s*—?\s*/i, '')}` : 'N/A';
    blockquote = `${overviewLine}\n> **Scope:** ${naLine}`;
  } else if (why) {
    const conceptLinks = buildConceptLinks(concepts);
    if (conceptLinks) {
      blockquote = `${overviewLine}\n${scopeLine}\n> **Why:** ${why}\n>\n> **Concepts used:**\n> ${conceptLinks}`;
    } else {
      blockquote = `${overviewLine}\n${scopeLine}\n> **Why:** ${why}`;
    }
  } else {
    // No why extracted (inventory, US crossborder with no why line extracted? check)
    const conceptLinks = buildConceptLinks(concepts);
    if (conceptLinks) {
      blockquote = `${overviewLine}\n${scopeLine}\n>\n> **Concepts used:**\n> ${conceptLinks}`;
    } else {
      blockquote = `${overviewLine}\n${scopeLine}`;
    }
  }

  let section = `## Semantic Contract\n\n${blockquote}\n`;
  if (sqlLines && sqlLines.length > 0) {
    section += `\n${sqlLines.join('\n')}\n`;
  }

  return section;
}

// Find the start/end of ## Segmentation Scope section in the file content
function findSectionBounds(content) {
  const startMatch = content.match(/\n## Segmentation Scope\s*\n/);
  if (!startMatch) return null;

  const start = startMatch.index; // points to the \n before ##
  const sectionStart = start + 1; // skip leading \n

  // Find next ## heading after this section
  const afterSection = content.slice(sectionStart + '## Segmentation Scope'.length);
  const nextHeadingMatch = afterSection.match(/\n## /);

  let sectionEnd;
  if (nextHeadingMatch) {
    sectionEnd = sectionStart + '## Segmentation Scope'.length + nextHeadingMatch.index + 1;
    // +1 to include the \n before next ## but exclude the ##
  } else {
    sectionEnd = content.length;
  }

  return { start: sectionStart, end: sectionEnd };
}

function migrateFile(filePath) {
  const content = fs.readFileSync(filePath, 'utf8');
  const name = path.basename(filePath);

  // Skip if already migrated
  if (/## Semantic Contract/.test(content)) {
    console.log(`  ✅ Already migrated: ${name}`);
    return false;
  }

  if (!/## Segmentation Scope/.test(content)) {
    console.log(`  ⚠️  No Segmentation Scope section: ${name}`);
    return false;
  }

  const fm = parseFrontmatter(content);
  if (!fm) {
    console.log(`  ⚠️  No frontmatter: ${name}`);
    return false;
  }

  const bounds = findSectionBounds(content);
  if (!bounds) {
    console.log(`  ⚠️  Could not find section bounds: ${name}`);
    return false;
  }

  const existingBody = content.slice(bounds.start, bounds.end);
  const newSection = buildSemanticContractSection(fm, existingBody);

  const newContent =
    content.slice(0, bounds.start) +
    newSection +
    content.slice(bounds.end);

  if (DRY_RUN) {
    console.log(`\n--- ${name} ---`);
    console.log('OLD:');
    console.log(existingBody.slice(0, 400));
    console.log('\nNEW:');
    console.log(newSection);
    return true;
  }

  fs.writeFileSync(filePath, newContent, 'utf8');
  return true;
}

// Run
const files = fs.readdirSync(BLUEPRINTS_DIR)
  .filter(f => f.endsWith('.md') && f !== 'README.md')
  .map(f => path.join(BLUEPRINTS_DIR, f));

console.log(`Migrating ${files.length} blueprint files...${DRY_RUN ? ' [DRY RUN]' : ''}\n`);

let migrated = 0;
let skipped = 0;

for (const file of files) {
  const result = migrateFile(file);
  if (result) migrated++;
  else skipped++;
}

console.log(`\n${'─'.repeat(50)}`);
console.log(`Migrated: ${migrated} | Skipped: ${skipped}`);
if (!DRY_RUN && migrated > 0) {
  console.log('\nRun validate-analytics-artifacts.js --blueprints-only to verify.');
}
