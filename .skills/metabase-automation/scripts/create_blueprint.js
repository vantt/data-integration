const fs = require('fs');
const path = require('path');

/**
 * usage: node create_blueprint.js <domain> <purpose>
 * example: node create_blueprint.js sales daily
 * result: docs/metabase-workspace/sales-blueprint-daily.md
 */

const args = process.argv.slice(2);
if (args.length < 2) {
    console.error("Usage: node create_blueprint.js <domain> <purpose>");
    console.error("Example: node create_blueprint.js sales daily");
    process.exit(1);
}

const domain = args[0].toLowerCase();
const purpose = args[1].toLowerCase();
const filename = `${domain}-blueprint-${purpose}.md`;

// Target directory: docs/metabase-workspace/
// Assuming we run this from project root or .agent/skills/...
// We'll try to resolve relative to process.cwd()
const targetDir = path.resolve(process.cwd(), 'docs', 'metabase-workspace');

if (!fs.existsSync(targetDir)) {
    console.error(`❌ Target directory not found: ${targetDir}`);
    console.error("Please run this script from the project root.");
    process.exit(1);
}

const targetPath = path.join(targetDir, filename);

if (fs.existsSync(targetPath)) {
    console.error(`❌ File already exists: ${targetPath}`);
    process.exit(1);
}

const template = `# ${domain.charAt(0).toUpperCase() + domain.slice(1)} ${purpose.charAt(0).toUpperCase() + purpose.slice(1)} Blueprint

📖 **Playbook**: [${domain}-playbook.md#key-metrics]

## 📂 Collection: ${domain.charAt(0).toUpperCase() + domain.slice(1)} Analytics

### 🧊 Model: Main Model

Description of the data model.

\`\`\`sql
SELECT * FROM public.fact_${domain}
\`\`\`

#### ⚙️ Settings

\`\`\`json metabase-model
{
  "description": "Core ${domain} data",
  "columns": {
    "id": { "semantic_type": "type/PK" }
  }
}
\`\`\`

---

### 🖥️ Dashboard: ${purpose.charAt(0).toUpperCase() + purpose.slice(1)} Overview

#### ❓ Question: Total Count

\`\`\`sql
SELECT count(*) FROM public.fact_${domain}
\`\`\`

\`\`\`json metabase-viz
{
  "display": "scalar",
  "scalar.field": "count"
}
\`\`\`

\`\`\`json metabase-pos
{
  "row": 0,
  "col": 0,
  "size_x": 4,
  "size_y": 4
}
\`\`\`
`;

fs.writeFileSync(targetPath, template);
console.log(`✅ Created blueprint: ${targetPath}`);
