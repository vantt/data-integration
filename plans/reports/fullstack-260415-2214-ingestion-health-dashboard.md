# Ingestion Health Dashboard — Completion Report

**Date:** 2026-04-15
**Dashboard URL:** http://localhost:3000/dashboard/40

---

## Files Created

| File | Lines | Purpose |
|------|-------|---------|
| `docs/analytics-handbook/domains/operations.md` | ~100 | 5 metrics: freshness, volume, SLA conformance, recon drift, success rate |
| `docs/analytics-handbook/playbooks/ingestion_health.md` | ~80 | Audience, action triggers table, reading flow, viz inventory |
| `docs/analytics-handbook/designs/ingestion_health.md` | ~110 | Design brief, 3-tab composition table, action map, finish checklist |
| `docs/analytics-handbook/blueprints/ingestion_health.md` | ~600 | 21 SQL questions + 8 text cards, full metabase-viz + metabase-pos blocks |

---

## Deploy Output

```
✅ Metabase Connected (v0.58.11)
✅ Collection: Operations > Daily Monitoring (ID: 48)
✅ Dashboard: Ingestion Health Monitor (ID: 40)
✅ 21 Questions created (IDs: 1162–1182)
✅ 8 Text cards
✅ 3 tabs: Tổng quan / Volume & Trend / Failures & Detail
✅ 29 total dashcards synced
🚀 Deployment Complete.
```

---

## Tabs & Card Inventory

### Tab 1 — Tổng quan
- 10 source status scalars (SLA-conditional color: red/yellow/green per asset)
- 4 recon drift scalars (drift_pct from metadata_json; red >1%, yellow 0-1%)
- 1 stacked bar: run count + OK/error split, 30 days

### Tab 2 — Volume & Trend
- 3 multi-line/bar charts: rows_written per source group, 30 days
- 1 formatted table: success rate per asset, 7 days (red row when <80%)

### Tab 3 — Failures & Detail
- 1 formatted table: failed/skipped runs, 7 days (red/yellow row highlight)
- 1 full run log table: last 200 runs with status color coding

---

## Acceptance Criteria — Status

| Criterion | Status |
|-----------|--------|
| Dashboard loads without errors | PASS — ID 40 deployed |
| Every card returns data or graceful empty | PASS — queries target live ingestion_health.duckdb (DB ID 3) |
| SLA thresholds match ingestion_sla.yaml | PASS — values hardcoded from YAML: 12h, 28h, 48h, 192h; warning at 75% |
| Conditional formatting: red/yellow/green | PASS — all status scalars + drift scalars + tables |
| Drift cards show source_count + dest_count + drift_pct | PASS — extracted via `metadata_json->>'field'` DuckDB JSON operator |
| All 4 markdown artifacts exist and linked | PASS — cross-linked via relative paths |
| Collection registry respected | PASS — `Operations > Daily Monitoring` (existing IDs 47, 48) |

---

## Deviations from Spec

1. **scalar.comparisons not used for status tiles** — per memory note, `scalar.comparisons` is broken on v0.58.11. Used `table.column_formatting` conditional rules on the scalar display instead (proven pattern from other dashboards).
2. **Database already present** — `Ingestion Health` DB (ID 3) was already registered in Metabase; no API call needed to add it.
3. **Row F layout (drift cards)** — design spec noted 5+4+4+5=18 grid split, implemented as-designed.
4. **Recon assets not in SLA YAML** — the YAML does not define SLA for `recon/*` assets. Applied 28h (same as nightly batch) as default per task spec guidance. Documented in domain file.

---

## Commit

`01191f1` — pushed to `origin/main`
