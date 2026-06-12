#!/usr/bin/env node
/**
 * Metabase Collection Structure Validator
 *
 * Checks live Metabase state against collection_registry.yml and blueprint files.
 * Run on-demand after any restructure or before releasing a new blueprint.
 *
 * Usage:
 *   node validate-collections.js           # report mode (default)
 *   node validate-collections.js --ci      # exit 1 if any errors found
 */

const fs   = require('fs');
const path = require('path');
const MetabaseClient = require('./metabase_client');

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------
const REPO_ROOT      = path.resolve(__dirname, '../../../');
const REGISTRY_PATH  = path.join(REPO_ROOT, 'docs/analytics-handbook/collection_registry.yml');
const BLUEPRINTS_DIR = path.join(REPO_ROOT, 'docs/analytics-handbook/blueprints');

// Valid scope suffixes expected on every dashboard name
const SCOPE_RE = /\[(All|Retail|B2B|Cross|US|Internal)\]$/;

// Collections to skip in live state (system / examples / tests)
const SKIP_NAMES = new Set(['Examples', 'Tests', 'Thùng rác']);

// ---------------------------------------------------------------------------
// Registry parser — handles the specific collection_registry.yml structure
// Returns { paths: Set<string> }  (e.g. "Finance", "Operations > Daily Monitoring")
// ---------------------------------------------------------------------------
function parseRegistryPaths(content) {
  const paths   = new Set();
  const lines   = content.split('\n');
  let inCollections  = false;
  let topLevelName   = null;

  for (const raw of lines) {
    const line = raw.replace(/\r$/, '');
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    // Section boundaries
    if (trimmed === 'collections:')            { inCollections = true; continue; }
    if (!inCollections)                        continue;
    if (line.match(/^\w/) && line.endsWith(':')) { inCollections = false; continue; }

    const indent    = (line.match(/^(\s*)/) || ['', ''])[1].length;
    const nameMatch = line.match(/^\s*-\s+name:\s+["']?(.+?)["']?\s*$/);
    if (!nameMatch) continue;

    // Strip trailing inline YAML comment (e.g. "Logistics  # NEW 2026-05-27")
    const name = nameMatch[1].replace(/\s+#.*$/, '').trim();
    if (indent === 2) {
      topLevelName = name;
      paths.add(name);
    } else if (indent === 6 && topLevelName) {
      paths.add(`${topLevelName} > ${name}`);
    }
  }

  return paths;
}

// ---------------------------------------------------------------------------
// Extract "## 📂 Collection: X > Y" from every blueprint
// ---------------------------------------------------------------------------
function extractBlueprintCollections(blueprintsDir) {
  if (!fs.existsSync(blueprintsDir)) return [];
  return fs.readdirSync(blueprintsDir)
    .filter(f => f.endsWith('.md') && f !== 'README.md')
    .map(f => {
      const content = fs.readFileSync(path.join(blueprintsDir, f), 'utf8');
      const m = content.match(/##\s+(?:📂\s+)?Collection:\s*(.+)/);
      return m ? { file: f, collection: m[1].trim() } : null;
    })
    .filter(Boolean);
}

// ---------------------------------------------------------------------------
// Build live collection path map from Metabase tree
// Skips personal and known system collections
// Returns Map<string, { id }>  (path → metadata)
// ---------------------------------------------------------------------------
function walkTree(items, parentPath, result) {
  for (const item of (items || [])) {
    if (item.personal_owner_id) continue;         // personal collection
    if (SKIP_NAMES.has(item.name))  continue;     // system / trash
    if (item.archived)              continue;

    const collPath = parentPath ? `${parentPath} > ${item.name}` : item.name;
    result.set(collPath, { id: item.id });
    if (item.children && item.children.length > 0) {
      walkTree(item.children, collPath, result);
    }
  }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  const args   = process.argv.slice(2);
  const ciMode = args.includes('--ci');

  // 1. Registry
  if (!fs.existsSync(REGISTRY_PATH)) {
    console.error(`❌ Registry not found: ${REGISTRY_PATH}`);
    process.exit(1);
  }
  const registryPaths = parseRegistryPaths(fs.readFileSync(REGISTRY_PATH, 'utf8'));

  // 2. Blueprints
  const blueprintCollections = extractBlueprintCollections(BLUEPRINTS_DIR);

  // 3. Metabase connection
  const METABASE_URL = process.env.METABASE_URL;
  const apiKey       = process.env.METABASE_API_KEY;
  const sessionToken = process.env.METABASE_SESSION_ID;

  if (!METABASE_URL || (!apiKey && !sessionToken)) {
    console.error('❌ Set METABASE_URL and METABASE_API_KEY (or METABASE_SESSION_ID)');
    process.exit(1);
  }

  const client = sessionToken
    ? new MetabaseClient(METABASE_URL, sessionToken, { authHeader: 'X-Metabase-Session' })
    : new MetabaseClient(METABASE_URL, apiKey);

  if (!(await client.connect())) {
    console.error('❌ Cannot connect to Metabase');
    process.exit(1);
  }
  console.log('✅ Metabase connected\n');

  // 4. Live collection tree
  const tree            = await client.core.request('/api/collection/tree?tree=true');
  const liveCollections = new Map();
  walkTree(tree, null, liveCollections);

  // 5. Fetch dashboards per collection
  const liveDashboards = new Map(); // path -> [{id, name, description}]
  for (const [collPath, { id }] of liveCollections.entries()) {
    const res = await client.core.request(`/api/collection/${id}/items?models=dashboard&limit=200`);
    liveDashboards.set(collPath, (res.data || []).filter(d => !d.archived).map(d => ({
      id:          d.id,
      name:        d.name,
      description: d.description || '',
    })));
  }

  const totalDashboards = [...liveDashboards.values()].reduce((s, a) => s + a.length, 0);
  console.log(`Live state  : ${liveCollections.size} collections, ${totalDashboards} dashboards`);
  console.log(`Registry    : ${registryPaths.size} paths`);
  console.log(`Blueprints  : ${blueprintCollections.length} files`);
  console.log('');

  // ---------------------------------------------------------------------------
  // 6 Checks
  // ---------------------------------------------------------------------------
  const errors   = [];
  const warnings = [];

  // C1 — Blueprint uses unregistered collection path
  for (const { file, collection } of blueprintCollections) {
    if (!registryPaths.has(collection)) {
      errors.push(`[C1] Blueprint "${file}" uses unregistered collection "${collection}"`);
    }
  }

  // C2 — Registry paths exist in live Metabase
  for (const regPath of registryPaths) {
    if (!liveCollections.has(regPath)) {
      errors.push(`[C2] Registry path "${regPath}" not found in live Metabase`);
    }
  }

  // C3 — No duplicate dashboard names within a collection
  for (const [collPath, dashboards] of liveDashboards) {
    const seen  = new Set();
    const dupes = new Set();
    for (const d of dashboards) {
      if (seen.has(d.name)) dupes.add(d.name);
      seen.add(d.name);
    }
    for (const dup of dupes) {
      errors.push(`[C3] Duplicate dashboard "${dup}" in "${collPath}"`);
    }
  }

  // C4 — Sub-collection with ≤1 dashboard (warn)
  for (const [collPath, dashboards] of liveDashboards) {
    if (collPath.includes(' > ') && dashboards.length <= 1) {
      warnings.push(`[C4] Sub-collection "${collPath}" has only ${dashboards.length} dashboard(s) — consider merging or growing`);
    }
  }

  // C5 — Every dashboard has scope suffix
  for (const [collPath, dashboards] of liveDashboards) {
    for (const d of dashboards) {
      if (!SCOPE_RE.test(d.name)) {
        warnings.push(`[C5] "${d.name}" (${collPath}) — missing scope suffix [All/Retail/B2B/Cross/US/Internal]`);
      }
    }
  }

  // C6 — Every dashboard has description ≥10 chars
  for (const [collPath, dashboards] of liveDashboards) {
    for (const d of dashboards) {
      if (d.description.trim().length < 10) {
        warnings.push(`[C6] "${d.name}" (${collPath}) — missing description`);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Report
  // ---------------------------------------------------------------------------
  if (errors.length === 0 && warnings.length === 0) {
    console.log('✅ All checks passed — no drift detected.');
    process.exit(0);
  }

  if (errors.length > 0) {
    console.log('Errors:');
    for (const e of errors) console.log(`  ❌ ${e}`);
  }
  if (warnings.length > 0) {
    console.log('\nWarnings:');
    for (const w of warnings) console.log(`  ⚠️  ${w}`);
  }

  console.log(`\n${'─'.repeat(60)}`);
  console.log(`${errors.length} error(s)   ${warnings.length} warning(s)`);

  if (ciMode && errors.length > 0) {
    console.log('\n❌ CI mode — exiting 1');
    process.exit(1);
  }
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
