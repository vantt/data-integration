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

if (withTabs) {
    template = `# ${domainCap} ${purposeCap} Blueprint

**Playbook**: [${domainCap} ${purposeCap}](../playbooks/${domain}_${purpose}.md)

## 📂 Collection: ${domainCap} Analytics

### 🖥️ Dashboard: ${domainCap} ${purposeCap}

**Description**: TODO

---

### 📑 Tab: Overview

#### ❓ Question: Total Count

\`\`\`sql
SELECT count(*) as "Total" FROM fact_${domain}
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
SELECT * FROM fact_${domain} LIMIT 100
\`\`\`

\`\`\`json metabase-viz
{ "display": "table" }
\`\`\`

\`\`\`json metabase-pos
{ "row": 0, "col": 0, "size_x": 18, "size_y": 8 }
\`\`\`
`;
} else {
    template = `# ${domainCap} ${purposeCap} Blueprint

**Playbook**: [${domainCap} ${purposeCap}](../playbooks/${domain}_${purpose}.md)

## 📂 Collection: ${domainCap} Analytics

### 🖥️ Dashboard: ${domainCap} ${purposeCap}

**Description**: TODO

#### ❓ Question: Total Count

\`\`\`sql
SELECT count(*) as "Total" FROM fact_${domain}
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
