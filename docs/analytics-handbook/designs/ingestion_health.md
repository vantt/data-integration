---
title: Ingestion Health Monitor
archetype: Operational Cockpit
status: final
last_modified: 2026-04-15
domain_refs: [domains/operations.md]
---

# Design Spec: Ingestion Health Monitor

**Playbook**: [ingestion_health.md](../playbooks/ingestion_health.md)
**Domain**: [operations.md](../domains/operations.md)

---

## Design Brief (Phase 3)

| Field | Value |
|-------|-------|
| **Audience** | Data engineer / ops — single operator checking pipeline health daily |
| **Primary Question** | "Did every source move data today, is volume sane, is anything drifting?" |
| **Decision Enabled** | Investigate/escalate vs. proceed with confidence |
| **Hero Metric** | Per-source SLA status (existence confirmation) |
| **Comparison Frame** | SLA threshold (hours since last success vs. SLA ceiling) |
| **Time Budget** | Glanceable — < 10 seconds for healthy state, 1-2 min for triage |
| **Archetype** | Operational Cockpit (multi-tab; >10 cards; action-oriented) |

**Key design principle:** Existence confirmation > latency precision. "Ran today: ✓" matters more than "ran 5 min ago". Status tiles must be impossible to misread at a glance.

---

## Constraints & Filters (Phase 4e)

### Business Constraints

| Constraint | Rule | Applies To | Rationale |
|-----------|------|-----------|-----------|
| Success/partial only for freshness | `status IN ('success', 'partial')` | All freshness cards | `failed`/`skipped` runs don't prove data moved |
| Recon assets only for drift | `asset_key LIKE 'recon/%'` | Drift cards | Only recon assets store drift_pct in metadata_json |
| SLA values from config | Hardcoded in SQL CTE per asset | Status wall | DRY — sourced from ingestion_sla.yaml values |

### Interactive Filters

None. This is a monitoring wall. Time windows are hardcoded per card (freshness = live, sparklines = 30d, failures = 7d).

---

## Views / Tabs (Phase 4d)

Multi-tab layout (Operational Cockpit pattern):

| Tab | Narrative | Purpose |
|-----|-----------|---------|
| **Tổng quan** | Status wall → Drift alerts → Run timeline | "Is everything OK right now?" |
| **Volume & Trend** | 30d volume sparklines → success rate table | "Is volume normal over time?" |
| **Failures & Detail** | Recent failures table → full run log | "What broke and when?" |

---

## Composition (Phase 4a-4c)

### Tab 1: Tổng quan

| Row | Card Name | Role | Viz Type | Color Token | Size (18-grid) |
|-----|-----------|------|----------|-------------|---------------|
| A | *Header annotation* | Annotation | `text-annotation` | structural | 18 |
| B | Sapo Batch — Orders | Supporting KPI | `single-value` | conditional: positive/warning/negative | 6 |
| B | Sapo Batch — Customers | Supporting KPI | `single-value` | conditional | 6 |
| B | Sapo Batch — Products | Supporting KPI | `single-value` | conditional | 6 |
| C | Sapo Batch — Accounts | Supporting KPI | `single-value` | conditional | 6 |
| C | Sapo Realtime — Webhook | Hero | `single-value` | conditional | 6 |
| C | Sapo Incremental — History Log | Supporting KPI | `single-value` | conditional | 6 |
| D | Google Sheets — Targets | Supporting KPI | `single-value` | conditional | 6 |
| D | Google Sheets — Marketing Spend | Supporting KPI | `single-value` | conditional | 6 |
| D | MISA File Drop | Supporting KPI | `single-value` | conditional | 6 |
| D-extra | Shopee File Drop | Supporting KPI | `single-value` | conditional | 6 (row E col 0) |
| E | *Drift section annotation* | Annotation | `text-annotation` | structural | 18 |
| F | Drift — Sapo Orders | Supporting KPI | `single-value` | conditional: positive/warning/negative | 4.5→ use 5 |
| F | Drift — Sapo Customers | Supporting KPI | `single-value` | conditional | 4 |
| F | Drift — MISA | Supporting KPI | `single-value` | conditional | 4 |
| F | Drift — Shopee | Supporting KPI | `single-value` | conditional | 5 |
| G | *Run timeline annotation* | Annotation | `text-annotation` | structural | 18 |
| H | Run Count per Day (30d) | Trend | `vertical-bar` | primary | 18 |

**Row B-D layout note:** 3 cards × 6 col = 18 ✓. Row D has 3 cards (6+6+6); Shopee goes on a new short row (6 wide, col 0).

**Row F layout:** 4 drift scalars. Use 5+4+4+5 = 18 ✓.

### Tab 2: Volume & Trend

| Row | Card Name | Role | Viz Type | Color Token | Size (18-grid) |
|-----|-----------|------|----------|-------------|---------------|
| A | *Volume annotation* | Annotation | `text-annotation` | structural | 18 |
| B | Rows Written per Asset (30d) — Sapo Batch | Trend | `multi-line-chart` | series-1/2/3/accent | 18 |
| C | Rows Written — Other Sources (30d) | Trend | `multi-line-chart` | series-1/2/3 | 18 |
| D | *Success rate annotation* | Annotation | `text-annotation` | structural | 18 |
| E | Success Rate per Asset (7d) | Breakdown | `data-table-formatted` | positive/negative | 18 |

### Tab 3: Failures & Detail

| Row | Card Name | Role | Viz Type | Color Token | Size (18-grid) |
|-----|-----------|------|----------|-------------|---------------|
| A | *Failures annotation* | Annotation | `text-annotation` | structural | 18 |
| B | Runs Failed/Skipped (7d) | Detail | `data-table-formatted` | negative highlight | 18 |
| C | *Full run log annotation* | Annotation | `text-annotation` | structural | 18 |
| D | Full Run Log (last 200 runs) | Detail | `data-table-formatted` | conditional by status | 18 |

---

## Action Map (Phase 6d)

| Card | Signal | Threshold | Viz Response | Playbook Action |
|------|--------|-----------|-------------|-----------------|
| Source status tiles | hours_since_success | ≥ SLA → red; ≥ 75% SLA → yellow; < 75% → green | Background color of scalar cell | Investigate Dagster, re-trigger |
| Drift scalars | drift_pct | > 1 → red; 0 < x ≤ 1 → yellow; 0 → green | Scalar color | Compare source_count vs dest_count |
| Failures table | status = failed/skipped | Any in 7d | Red row highlight | Check asset logs |
| Run timeline | run_count per day | 0 → gap bar | Missing bar | Check Dagster scheduler |
| Success rate table | success_rate_pct | < 80% → red | Red cell | Investigate recurring failures |

---

## Dashboard Finish Checklist (Phase 6e)

- [x] Every card has exactly 1 role
- [x] Exactly 1 Hero (Sapo Webhook — highest-frequency, realtime)
- [x] Row widths all sum to 18
- [x] Status colors: green/yellow/red consistently applied via conditional formatting
- [x] All KPIs have comparison frame (vs SLA threshold)
- [x] Annotations are specific (not "Overview")
- [x] Detail tables at bottom of each tab
- [x] No `donut` with > 5 slices
- [x] No `gauge` without clear range (using `single-value` + conditional color instead)
- [x] DuckDB SQL dialect throughout (no MySQL/Postgres-only syntax)
- [x] NULLIF used in all divisions
- [x] TIMESTAMPTZ preserved; displayed in Asia/Ho_Chi_Minh via Metabase timezone setting
