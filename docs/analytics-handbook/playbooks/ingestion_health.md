# Playbook: Ingestion Health Monitor

**Blueprint**: [ingestion_health.md](../blueprints/ingestion_health.md)

## Overview

- **Audience:** Data engineer / ops (single operator). Checked once per day, more often when alerts fire.
- **Goal:** Answer in < 10 seconds — "did every source move data today, is volume sane, and is anything drifting?" This is **trust engineering**: produce *felt confidence* that the pipeline is working, not deep analysis.
- **Archetype:** Operational Cockpit — daily management, action-oriented.
- **Metabase Collection:** `Operations > Data Platform`

## Reading Flow

1. **Start top-left: Status Wall** — scan the colored tiles per source. All green → pipeline is healthy, stop here. Any red/yellow → read that row.
2. **Drift Alert row** — check recon drift scalars. If any show > 1%, investigate source vs destination counts.
3. **Volume Sparklines (30d)** — confirm today's write volume fits the historical pattern. A sudden zero or spike is the anomaly signal.
4. **Recent Failures table** — if status = failed/skipped, find the asset and time, then cross-reference Dagster UI.
5. **Run Timeline** — useful when a whole day has no runs (Dagster scheduler down).

## Filters

- **Date Range:** No interactive filter. All cards use hardcoded time windows appropriate to each signal (freshness = live; sparklines = last 30 days; failures = last 7 days).
- **No user-changeable filters.** This is a monitoring wall, not an exploration tool.

## Action Triggers

| Signal | Threshold | Action | Owner |
|--------|-----------|--------|-------|
| Asset tile red | hours_since_last_success ≥ SLA | Check Dagster run history for that asset. Re-trigger manually if stuck. | Data Engineer |
| Asset tile yellow | hours_since_last_success ≥ 75% of SLA | Monitor — likely will resolve on next scheduled run. Note if pattern persists. | Data Engineer |
| rows_written = 0 (after SLA grace) | 0 rows on a run that normally writes | Investigate source API response / file presence. | Data Engineer |
| drift_pct > 1% | Any recon asset | Compare `source_count` vs `dest_count`. Identify gap in pipeline (transform bug, truncation). | Data Engineer |
| drift_pct 0 < x ≤ 1% | Warning zone | Log and monitor. Recon drift in this range may be eventual-consistency lag. | Data Engineer |
| status = failed, count ≥ 2 in 24h | Repeated failure | Escalate: source API down, auth expired, or infra issue. Check Dagster sensor logs. | Data Engineer |
| No runs all day | Total run count for day = 0 | Dagster scheduler may be down. SSH into server, check `dagster daemon` service status. | Data Engineer |
| schema_hash changed | Distinct hashes in 30d > 1 | Source schema changed silently. Review dbt model compatibility. | Data Engineer |

## Visualizations

### Section 1: Status Wall — Freshness & Volume per Source

| Card Title | Viz Type | Metric Reference | Notes |
|:-----------|:---------|:----------------|:------|
| Sapo Orders — trạng thái | `single-value` with conditional color | [Ingestion Freshness](../domains/operations.md#1-ingestion-freshness) | Red/Yellow/Green by SLA; show hours_since + rows_written |
| Sapo Customers — trạng thái | `single-value` | same | 28h SLA |
| Sapo Products — trạng thái | `single-value` | same | 28h SLA |
| Sapo Accounts — trạng thái | `single-value` | same | 28h SLA |
| Sapo History Log — trạng thái | `single-value` | same | 12h SLA |
| Sapo Webhook — trạng thái | `single-value` | same | 12h SLA |
| Google Sheets Targets — trạng thái | `single-value` | same | 48h SLA |
| Google Sheets Marketing Spend — trạng thái | `single-value` | same | 48h SLA |
| MISA File Drop — trạng thái | `single-value` | same | 192h SLA |
| Shopee File Drop — trạng thái | `single-value` | same | 48h SLA |

### Section 2: Drift Alerts — Reconciliation

| Card Title | Viz Type | Metric Reference | Notes |
|:-----------|:---------|:----------------|:------|
| Drift — Sapo Orders | `single-value` conditional | [Recon Drift](../domains/operations.md#4-recon-drift) | drift_pct; red > 1%, yellow 0-1%, green = 0 |
| Drift — Sapo Customers | `single-value` conditional | same | same |
| Drift — MISA | `single-value` conditional | same | same |
| Drift — Shopee | `single-value` conditional | same | same |

### Section 3: Volume Trend (30d)

| Card Title | Viz Type | Metric Reference | Notes |
|:-----------|:---------|:----------------|:------|
| Rows Written per Source (30d) | `multi-line-chart` | [Ingestion Volume](../domains/operations.md#2-ingestion-volume) | One series per source group; log scale optional |

### Section 4: Failures & Detail

| Card Title | Viz Type | Metric Reference | Notes |
|:-----------|:---------|:----------------|:------|
| Runs récents avec erreurs (7d) | `data-table-formatted` | [Run Success Rate](../domains/operations.md#5-run-success-rate-7d) | failed/skipped runs; red highlight |
| Run Count per Day (30d) | `vertical-bar` | Run count | Detect scheduler-down days |

## Business Constraints

- No constraints that filter source data — this table IS the monitoring table.
- SLA hours are sourced from `orchestration/config/ingestion_sla.yaml` — never hardcode in SQL, derive in CTE.
