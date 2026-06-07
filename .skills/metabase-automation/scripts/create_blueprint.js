const fs = require('fs');
const path = require('path');

/**
 * usage: node create_blueprint.js <domain> <purpose> [--tabs]
 * example: node create_blueprint.js sales daily
 * example: node create_blueprint.js sales daily --tabs
 * result: docs/analytics-handbook/blueprints/<domain>_<purpose>.md
 */

const args = process.argv.slice(2);
const flags = args.filter(a => a.startsWith('--'));
const positional = args.filter(a => !a.startsWith('--'));

if (positional.length < 2) {
    console.error("Usage: node create_blueprint.js <domain> <purpose> [--tabs]");
    console.error("Example: node create_blueprint.js sales daily");
    console.error("Example: node create_blueprint.js sales daily --tabs");
    process.exit(1);
}

const domain = positional[0].toLowerCase();
const purpose = positional[1].toLowerCase();
const withTabs = flags.includes('--tabs');
const filename = `${domain}_${purpose}.md`;

const targetDir = path.resolve(process.cwd(), 'docs', 'analytics-handbook', 'blueprints');

if (!fs.existsSync(targetDir)) {
    fs.mkdirSync(targetDir, { recursive: true });
}

const targetPath = path.join(targetDir, filename);

if (fs.existsSync(targetPath)) {
    console.error(`❌ File already exists: ${targetPath}`);
    process.exit(1);
}

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const domainCap = cap(domain);
const purposeCap = cap(purpose);

let template;

// Maps concept names to their semantic file + anchor.
// Used to auto-generate concept links in ## Semantic Contract.
const CONCEPT_FILE_MAP = {
  // Segments
  scope_sales: 'segments.md#scope_sales',
  scope_retail: 'segments.md#scope_retail',
  scope_b2b: 'segments.md#scope_b2b',
  filter_us: 'segments.md#filter_us',
  filter_internal: 'segments.md#filter_internal',
  filter_social: 'segments.md#filter_social',
  filter_has_cogs: 'segments.md#filter_has_cogs',
  // Metrics
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
};

function buildConceptLinks(concepts) {
  if (!concepts || concepts.length === 0) return '[`TODO_concept`](../semantic/segments.md#TODO)';
  return concepts
    .map(c => {
      const file = CONCEPT_FILE_MAP[c] || `segments.md#${c}`;
      return `[\`${c}\`](../semantic/${file})`;
    })
    .join(' · ');
}

function buildScopeLink(scope) {
  if (!scope || scope === 'TODO' || scope === 'none') return '`TODO`';
  const file = CONCEPT_FILE_MAP[scope] || `segments.md#${scope}`;
  return `[\`${scope}\`](../semantic/${file})`;
}

// Frontmatter + Semantic Contract section are required by the blueprint integration standard.
// See: docs/analytics-handbook/semantic/README.md → "Blueprint Integration Standard"
// Scope options: scope_sales | scope_retail | scope_b2b | filter_us | none
// Layer options: L1 | L1.5 | L2 | L3 | Internal
const frontmatter = `---
primary_scope: TODO  # scope_sales | scope_retail | scope_b2b | filter_us | none
scope_indicator: "[TODO]"  # [All] | [Retail] | [B2B] | [Cross] | [US] | [Internal]
layer: TODO  # L1 | L1.5 | L2 | L3 | Internal
uses_concepts: []  # e.g. [scope_retail, net_revenue, aov, discount_rate]
---`;

const semanticSection = `## Semantic Contract

> **Semantic layer:** [\`semantic/README.md\`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** \`TODO\` · Layer TODO \`[TODO]\` · [segments.md#TODO](../semantic/segments.md#TODO)
> **Why:** TODO — explain why this scope and not another.
>
> **Concepts used:**
> TODO_concept_links

All SQL: \`WHERE TODO_scope\`. Do not re-derive inline.
`;

if (withTabs) {
    template = `${frontmatter}

# ${domainCap} ${purposeCap} Blueprint

**Playbook**: [${domainCap} ${purposeCap}](../playbooks/${domain}_${purpose}.md)

${semanticSection}
## 📂 Collection: ${domainCap} Analytics

### 🖥️ Dashboard: ${domainCap} ${purposeCap}

**Description**: TODO

---

### 📑 Tab: Overview

#### ❓ Question: Total Count

\`\`\`sql
SELECT count(*) as "Total" FROM fact_${domain}
WHERE scope_TODO  -- replace with correct scope column
\`\`\`

\`\`\`json metabase-viz
{ "display": "scalar" }
\`\`\`

\`\`\`json metabase-pos
{ "row": 0, "col": 0, "size_x": 4, "size_y": 3 }
\`\`\`

---

### 📑 Tab: Details

#### ❓ Question: Detail Table

\`\`\`sql
SELECT * FROM fact_${domain}
WHERE scope_TODO  -- replace with correct scope column
LIMIT 100
\`\`\`

\`\`\`json metabase-viz
{ "display": "table" }
\`\`\`

\`\`\`json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 8 }
\`\`\`
`;
} else {
    template = `${frontmatter}

# ${domainCap} ${purposeCap} Blueprint

**Playbook**: [${domainCap} ${purposeCap}](../playbooks/${domain}_${purpose}.md)

${semanticSection}
## 📂 Collection: ${domainCap} Analytics

### 🖥️ Dashboard: ${domainCap} ${purposeCap}

**Description**: TODO

#### ❓ Question: Total Count

\`\`\`sql
SELECT count(*) as "Total" FROM fact_${domain}
WHERE scope_TODO  -- replace with correct scope column
\`\`\`

\`\`\`json metabase-viz
{ "display": "scalar" }
\`\`\`

\`\`\`json metabase-pos
{ "row": 0, "col": 0, "size_x": 4, "size_y": 3 }
\`\`\`
`;
}

fs.writeFileSync(targetPath, template);
console.log(`✅ Created blueprint: ${targetPath}`);
if (withTabs) {
    console.log(`📑 Scaffolded with 2 tabs (Overview, Details). Add more with: ### 📑 Tab: <Name>`);
}

// Run validator immediately after creation so author sees issues right away
try {
  const { execSync } = require('child_process');
  const validatorPath = path.resolve(__dirname, 'validate-analytics-artifacts.js');
  const result = execSync(`node "${validatorPath}" --blueprints-only 2>&1`, {
    cwd: path.resolve(__dirname, '../../..'),
    encoding: 'utf8'
  });
  // Only show lines relevant to the new file
  const filename = path.basename(targetPath);
  const lines = result.split('\n');
  const relevant = [];
  let capture = false;
  for (const line of lines) {
    if (line.includes(filename)) { capture = true; relevant.push(line); continue; }
    if (capture && (line.startsWith('  ') || line === '')) { relevant.push(line); continue; }
    if (capture && line.startsWith('blueprint/')) break;
  }
  if (relevant.length > 0) {
    console.log('\n📋 Validation result:');
    relevant.forEach(l => console.log(l));
  } else {
    console.log('✅ Validation: clean');
  }
} catch (e) {
  // Validator not available — skip silently
}
