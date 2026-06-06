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

// Frontmatter + Segmentation Scope section are required by the blueprint integration standard.
// See: docs/analytics-handbook/semantic/README.md → "Blueprint Integration Standard"
// Scope options: scope_sales | scope_retail | scope_b2b | filter_us | none
// Layer options: L1 | L1.5 | L2 | L3 | Internal
const frontmatter = `---
primary_scope: TODO  # scope_sales | scope_retail | scope_b2b | filter_us | none
scope_indicator: "[TODO]"  # [All] | [Retail] | [B2B] | [Cross] | [US] | [Internal]
layer: TODO  # L1 | L1.5 | L2 | L3 | Internal
uses_concepts: []  # e.g. [scope_retail, net_revenue, aov, discount_rate]
---`;

const scopeSection = `## Segmentation Scope

> **Scope:** \`TODO\` · Layer TODO · Suffix \`[TODO]\`
> **Why:** TODO — explain why this scope and not another.
> **Ref:** [segments.md](../semantic/segments.md)

All SQL in this blueprint: \`WHERE TODO\`. Do not re-derive inline.
`;

if (withTabs) {
    template = `${frontmatter}

# ${domainCap} ${purposeCap} Blueprint

**Playbook**: [${domainCap} ${purposeCap}](../playbooks/${domain}_${purpose}.md)

${scopeSection}
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

${scopeSection}
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
