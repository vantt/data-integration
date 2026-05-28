#!/usr/bin/env node
/**
 * Audit per-tab widget compliance against skill standard.
 *
 * Per skill (.skills/metabase-automation/templates/blueprint_template.md §"Tab Structure Standards"):
 *   Each tab BẮT BUỘC có 2 widgets:
 *   - Chu kỳ báo cáo: SQL Question display=scalar, row 0, size_x 18, size_y 2
 *   - Source & Freshness: Text card, last row, size_x 18, size_y 1
 *
 * This script: read-only. Report gaps. Output to JSON for follow-up.
 */

const URL = process.env.METABASE_URL || "http://127.0.0.1:3001";
const KEY = process.env.METABASE_API_KEY;
if (!KEY) { console.error("METABASE_API_KEY required"); process.exit(1); }

const DASHBOARD_IDS = [73, 43, 44, 31, 34, 35, 36, 33, 15, 30, 32, 38, 26, 27, 41, 42, 40, 28, 51, 8, 9, 49, 50, 13, 14, 37, 47, 46, 48, 74, 75, 76, 77, 78];

function isChuKyBaoCao(dc) {
  if (!dc.card_id) return false; // must be SQL question, not text
  const name = (dc.card?.name || "").toLowerCase();
  return name.includes("chu kỳ báo cáo") || name.includes("chu ky bao cao") || name === "chu kỳ";
}

function isSourceFreshness(dc) {
  if (dc.card_id) return false; // must be text card
  const text = (dc.visualization_settings?.text || "").trim().toLowerCase();
  return text.startsWith("source:") || text.includes("source:") && text.includes("scope:");
}

async function audit(id) {
  const res = await fetch(`${URL}/api/dashboard/${id}`, { headers: {"x-api-key": KEY} });
  const d = await res.json();
  if (d.archived) return null;

  const tabs = d.tabs || [];
  const dashcards = d.dashcards || [];

  // If no tabs, treat as single "tab" with id=null
  const tabList = tabs.length > 0
    ? tabs.map(t => ({id: t.id, name: t.name}))
    : [{id: null, name: "(no tabs)"}];

  const report = {
    id: d.id,
    name: d.name,
    tabs: []
  };

  for (const tab of tabList) {
    const tabCards = dashcards.filter(dc => dc.dashboard_tab_id === tab.id);
    const hasChuKy = tabCards.some(isChuKyBaoCao);
    const hasSource = tabCards.some(isSourceFreshness);
    const maxRow = tabCards.reduce((m, dc) => Math.max(m, dc.row + (dc.size_y||0)), 0);
    report.tabs.push({
      id: tab.id,
      name: tab.name,
      cards: tabCards.length,
      maxRow,
      hasChuKyBaoCao: hasChuKy,
      hasSourceFreshness: hasSource
    });
  }
  return report;
}

async function main() {
  const reports = [];
  for (const id of DASHBOARD_IDS) {
    const r = await audit(id);
    if (r) reports.push(r);
    await new Promise(res => setTimeout(res, 100));
  }

  // Print summary
  let totalTabs = 0, missingChuKy = 0, missingSource = 0;
  console.log("\n=== AUDIT REPORT ===\n");
  for (const r of reports) {
    const gaps = r.tabs.filter(t => !t.hasChuKyBaoCao || !t.hasSourceFreshness);
    if (gaps.length === 0) {
      console.log(`✓ [${r.id}] ${r.name} (${r.tabs.length} tabs all compliant)`);
    } else {
      console.log(`✗ [${r.id}] ${r.name}`);
      for (const t of r.tabs) {
        const missing = [];
        if (!t.hasChuKyBaoCao) { missing.push("ChuKy"); missingChuKy++; }
        if (!t.hasSourceFreshness) { missing.push("Source"); missingSource++; }
        if (missing.length > 0) {
          console.log(`    tab="${t.name}" cards=${t.cards} missing: ${missing.join(", ")}`);
        }
        totalTabs++;
      }
    }
  }
  console.log(`\n=== TOTAL: ${reports.length} dashboards, ${totalTabs} tabs ===`);
  console.log(`Missing Chu kỳ báo cáo: ${missingChuKy} tabs`);
  console.log(`Missing Source & Freshness: ${missingSource} tabs`);

  // Save JSON for downstream
  require("fs").writeFileSync(
    "plans/260527-1327-metabase-collection-restructure/audit-report.json",
    JSON.stringify(reports, null, 2)
  );
  console.log("\nSaved: plans/260527-1327-metabase-collection-restructure/audit-report.json");
}

main().catch(e => { console.error(e); process.exit(1); });
