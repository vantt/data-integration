#!/usr/bin/env node
/**
 * Analytics Artifact Validator
 *
 * Validates playbooks, design specs, and blueprints for required sections,
 * actionability, archetype compliance, and text card usage.
 *
 * Usage:
 *   node validate-analytics-artifacts.js [--fix-suggestions]
 *   node validate-analytics-artifacts.js --playbooks-only
 *   node validate-analytics-artifacts.js --designs-only
 *   node validate-analytics-artifacts.js --blueprints-only
 */

const fs = require("fs");
const path = require("path");

const HANDBOOK = path.resolve(__dirname, "../../../docs/analytics-handbook");
const PLAYBOOKS_DIR = path.join(HANDBOOK, "playbooks");
const DESIGNS_DIR = path.join(HANDBOOK, "designs");
const BLUEPRINTS_DIR = path.join(HANDBOOK, "blueprints");

// ---------------------------------------------------------------------------
// Validation rules
// ---------------------------------------------------------------------------

function validatePlaybook(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const name = path.basename(filePath);
  const issues = [];

  // Required sections
  if (!/##\s+How to Read/i.test(content)) {
    issues.push({ severity: "warn", msg: "Missing '## How to Read' section" });
  }
  if (!/Action|Operational Actions|Action Triggers/i.test(content)) {
    issues.push({ severity: "warn", msg: "Missing action/decision guidance (Action Triggers, Operational Actions, or similar)" });
  }
  if (!/##\s+Overview/i.test(content)) {
    issues.push({ severity: "error", msg: "Missing '## Overview' section" });
  }
  if (!/Archetype:/i.test(content)) {
    issues.push({ severity: "warn", msg: "Missing archetype declaration in Overview" });
  }

  return { name, type: "playbook", issues };
}

function validateDesignSpec(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const name = path.basename(filePath);
  const issues = [];

  // Frontmatter
  if (!content.startsWith("---")) {
    issues.push({ severity: "error", msg: "Missing YAML frontmatter (---)" });
  } else {
    if (!/archetype:/i.test(content)) {
      issues.push({ severity: "error", msg: "Missing 'archetype' in frontmatter" });
    }
    if (!/status:/i.test(content)) {
      issues.push({ severity: "warn", msg: "Missing 'status' in frontmatter" });
    }
  }

  // Required sections
  if (!/###\s+View|###\s+Views/i.test(content)) {
    issues.push({ severity: "error", msg: "Missing Views section" });
  }
  if (!/Role.*Viz Type|Composition/i.test(content)) {
    issues.push({ severity: "error", msg: "Missing composition table (Role | Viz Type columns)" });
  }

  // Archetype compliance
  const archetypeMatch = content.match(/archetype:\s*(.+)/i);
  if (archetypeMatch) {
    const archetype = archetypeMatch[1].trim().toLowerCase();
    if (archetype.includes("pulse") || archetype.includes("executive")) {
      // Count views (### View N headers)
      const viewCount = (content.match(/###\s+View\s+\d/g) || []).length;
      if (viewCount > 3) {
        issues.push({ severity: "warn", msg: `Executive Pulse has ${viewCount} views (recommend ≤3)` });
      }
      // Check for detail tables
      if (/detail.table|detail-table/i.test(content)) {
        issues.push({ severity: "warn", msg: "Executive Pulse should avoid detail tables" });
      }
    }
  }

  return { name, type: "design", issues };
}

function validateBlueprint(filePath) {
  const content = fs.readFileSync(filePath, "utf8");
  const name = path.basename(filePath);
  const issues = [];

  // --- Semantic contract compliance ---
  // See: docs/analytics-handbook/semantic/README.md → Blueprint Integration Standard
  if (!content.startsWith("---")) {
    issues.push({ severity: "error", msg: "Missing YAML frontmatter — add primary_scope, scope_indicator, layer, uses_concepts" });
  } else {
    if (!/primary_scope:/i.test(content)) {
      issues.push({ severity: "error", msg: "Frontmatter missing 'primary_scope' (scope_sales|scope_retail|scope_b2b|filter_us|none)" });
    } else if (/primary_scope:\s*TODO/i.test(content)) {
      issues.push({ severity: "error", msg: "Frontmatter 'primary_scope' not filled in (still TODO)" });
    }
    if (!/uses_concepts:/i.test(content)) {
      issues.push({ severity: "warn", msg: "Frontmatter missing 'uses_concepts' — list semantic concepts this blueprint uses" });
    }
  }
  // Accept both new name (## Semantic Contract) and old name (## Segmentation Scope) during migration
  const hasSemanticContract = /##\s+Semantic Contract/i.test(content);
  const hasOldScopeSection = /##\s+Segmentation Scope/i.test(content);

  if (!hasSemanticContract && !hasOldScopeSection) {
    issues.push({ severity: "error", msg: "Missing '## Semantic Contract' section — add semantic layer overview + scope + concept links" });
  } else if (hasOldScopeSection && !hasSemanticContract) {
    issues.push({ severity: "warn", msg: "Has legacy '## Segmentation Scope' — migrate to '## Semantic Contract' format (add semantic/README.md link + concept links)" });
  } else if (hasSemanticContract) {
    // Check for semantic/README.md overview link
    const contractBlock = content.match(/## Semantic Contract[\s\S]{0,600}/)?.[0] || '';
    if (!/semantic\/README\.md/i.test(contractBlock)) {
      issues.push({ severity: "warn", msg: "'## Semantic Contract' missing link to semantic/README.md overview" });
    }
    // Check for at least one concept link into semantic/
    // Skip for N/A scope blueprints (infra/onboarding with no analytics concepts)
    const isNAScope = /\*\*Scope:\*\*\s*N\/A/i.test(contractBlock);
    if (!isNAScope && !/\]\(\.\.\/semantic\/(segments|metrics|dimensions|entities|rules)\.md/i.test(contractBlock)) {
      issues.push({ severity: "warn", msg: "'## Semantic Contract' missing concept links (e.g. [scope_retail](../semantic/segments.md#scope_retail))" });
    }
    // Check for TODO placeholders not filled in
    if (/Scope.*TODO|WHERE TODO|TODO_concept/i.test(contractBlock)) {
      issues.push({ severity: "warn", msg: "'## Semantic Contract' has unfilled TODO placeholders" });
    }
  }

  // Warn on SQL scope anti-patterns (re-deriving what pre-computed columns already express)
  if (/status\s+NOT\s+IN\s*\(\s*['"]CANCELLED['"]/i.test(content)) {
    issues.push({ severity: "warn", msg: "SQL re-derives cancellation filter inline — use pre-computed scope column (WHERE scope_sales / scope_retail / scope_b2b)" });
  }
  if (/customer_type\s*=\s*['"]RETAIL['"]/i.test(content)) {
    issues.push({ severity: "warn", msg: "SQL uses raw customer_type='RETAIL' — use pre-computed WHERE scope_retail instead" });
  }
  if (/customer_type\s+IN\s*\([^)]*WHOLESALE/i.test(content)) {
    issues.push({ severity: "warn", msg: "SQL uses raw customer_type IN (WHOLESALE,...) — use pre-computed WHERE scope_b2b instead" });
  }

  // --- Legacy artifact checks ---
  if (/Text annotations to add manually/i.test(content)) {
    issues.push({ severity: "error", msg: "Contains 'Text annotations to add manually' — migrate to #### 📝 Text: blocks" });
  }
  if (/add manually after deploy/i.test(content)) {
    issues.push({ severity: "error", msg: "Contains 'add manually after deploy' comment — use real text card blocks" });
  }

  // --- Structure checks (skip for text-only/onboarding dashboards: layer L0 or primary_scope none) ---
  const isTextOnly = /layer:\s*(L0|Internal)/i.test(content) && !/```sql/i.test(content);
  const hasTextCards = /####\s+(?:📝\s+)?Text:/i.test(content);
  const hasTabs = /###\s+(?:📑\s+)?Tab:/i.test(content);
  if (hasTabs && !hasTextCards) {
    issues.push({ severity: "warn", msg: "Has tabs but no text card annotations — consider adding section headings" });
  }
  if (!/###\s+(?:🖥️\s*)?Dashboard:/i.test(content)) {
    issues.push({ severity: "error", msg: "Missing Dashboard header" });
  }
  if (!isTextOnly) {
    if (!/####\s+(?:❓\s+)?Question:/i.test(content)) {
      issues.push({ severity: "error", msg: "No questions found in blueprint" });
    }
    if (!/```sql/i.test(content)) {
      issues.push({ severity: "error", msg: "No SQL blocks found" });
    }
  }

  return { name, type: "blueprint", issues };
}

// ---------------------------------------------------------------------------
// Runner
// ---------------------------------------------------------------------------

function listMdFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir)
    .filter(f => f.endsWith(".md") && f !== "README.md")
    .map(f => path.join(dir, f));
}

function run() {
  const args = process.argv.slice(2);
  const playbooksOnly = args.includes("--playbooks-only");
  const designsOnly = args.includes("--designs-only");
  const blueprintsOnly = args.includes("--blueprints-only");
  const all = !playbooksOnly && !designsOnly && !blueprintsOnly;

  const results = [];

  if (all || playbooksOnly) {
    for (const f of listMdFiles(PLAYBOOKS_DIR)) results.push(validatePlaybook(f));
  }
  if (all || designsOnly) {
    for (const f of listMdFiles(DESIGNS_DIR)) results.push(validateDesignSpec(f));
  }
  if (all || blueprintsOnly) {
    for (const f of listMdFiles(BLUEPRINTS_DIR)) results.push(validateBlueprint(f));
  }

  // Report
  let totalErrors = 0;
  let totalWarnings = 0;
  let cleanCount = 0;

  for (const r of results) {
    const errors = r.issues.filter(i => i.severity === "error");
    const warnings = r.issues.filter(i => i.severity === "warn");
    totalErrors += errors.length;
    totalWarnings += warnings.length;

    if (r.issues.length === 0) {
      cleanCount++;
      continue;
    }

    console.log(`\n${r.type}/${r.name}:`);
    for (const i of r.issues) {
      const icon = i.severity === "error" ? "❌" : "⚠️";
      console.log(`  ${icon} ${i.msg}`);
    }
  }

  console.log(`\n${"─".repeat(50)}`);
  console.log(`Scanned: ${results.length} artifacts (${cleanCount} clean)`);
  console.log(`Errors: ${totalErrors} | Warnings: ${totalWarnings}`);

  if (totalErrors > 0) {
    console.log("\n❌ Validation FAILED — fix errors before deploy.");
    process.exit(1);
  } else if (totalWarnings > 0) {
    console.log("\n⚠️ Validation passed with warnings.");
  } else {
    console.log("\n✅ All artifacts valid.");
  }
}

run();
