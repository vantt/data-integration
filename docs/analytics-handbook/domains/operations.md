# Operations Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** Data Engineer / Ops
> **Update Frequency:** Daily (ingestion), On-demand (SLA changes)

## Context: Ingestion Health

> **Description:** Metrics that measure the reliability, freshness, and correctness of the data ingestion pipeline. Answers "did data move today, was it the right amount, is anything drifting?"
> **Source:** `ingestion_health.duckdb` — table `ingestion_runs`
> **Grain:** Per asset run (asset_key + run_id)

> **dbt Source:** See Source note above

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Ingestion Health | Is data moving on time, at expected volume, and without reconciliation drift? | 1. Ingestion Freshness, 2. Ingestion Volume, 3. SLA Conformance, 4. Recon Drift, 5. Run Success Rate (7d) | `ingestion_health.duckdb` — table `ingestion_runs` | None documented |

### Analytical Questions

#### Q1. Ingestion Health Readiness

- **Question:** Is data moving on time, at expected volume, and without reconciliation drift?
- **Definition:** This question defines whether `Ingestion Health` is healthy, drifting, or needs deeper investigation based on the metrics in this context.
- **Nature:** data operations, operational quality.
- **Why It Matters:** It gives the reader the business reason for the metric set before they inspect individual KPIs.
- **Tradeoffs / Caveats:** Read the answer together with each metric scope, grain, and source; planned metrics are not official reporting sources until implemented.
- **Insight / Action Enabled:** When the signal deteriorates, the owner should verify data freshness, break down by the relevant dimension, and trigger the related playbook action.
- **Related Metrics:** 1. Ingestion Freshness, 2. Ingestion Volume, 3. SLA Conformance, 4. Recon Drift, 5. Run Success Rate (7d)

### Metrics

#### 1. Ingestion Freshness

- **Business Definition:** How long ago did an asset last run successfully? An asset is "fresh" if `run_ended_at` of its latest `success` or `partial` run is within the asset's SLA window.
- **Logic (SQL):**
  ```sql
  -- Latest successful run per asset
  SELECT asset_key,
         MAX(run_ended_at) AS last_success_at,
         date_diff('hour', MAX(run_ended_at), now()) AS hours_since_last_success
  FROM ingestion_runs
  WHERE status IN ('success', 'partial')
  GROUP BY asset_key
  ```
- **SLA Reference:** `orchestration/config/ingestion_sla.yaml`
  - `sapo/sapo_webhook_consumer_asset`: 12h
  - `sapo/sapo_history_log_asset`: 12h
  - `sapo/sapo_*_batch_asset` (4 assets): 28h
  - `shopee/shopee_income_file_drop_asset`: 48h
  - `sheets/sheets_*_asset` (2 assets): 48h
  - `misa_amis/misa_sales_file_drop_asset`: 192h (8 days)
  - `recon/*` assets: 28h (nightly reconciliation)
- **Status tokens:** `healthy` (< SLA), `warning` (≥ 75% of SLA), `stale` (≥ SLA)

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** hours/days
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 2. Ingestion Volume

- **Business Definition:** How many rows were written in the latest run? Zero rows is suspicious unless the source is genuinely empty.
- **Logic (SQL):**
  ```sql
  SELECT asset_key, run_id, rows_written, rows_fetched, rows_new, rows_updated
  FROM ingestion_runs
  WHERE status IN ('success', 'partial')
  ORDER BY run_started_at DESC
  ```
- **Note:** `rows_written` is the primary signal. `rows_fetched` helps detect source-side truncation. Both can be NULL for assets that don't track volume (e.g., recon assets).

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** count
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 3. SLA Conformance

- **Business Definition:** Binary per asset — did the asset complete a successful run within its SLA window during the current period (rolling 24h or 7d)?
- **Logic (SQL):**
  ```sql
  -- SLA conformance: has asset run successfully within freshness_hours?
  WITH sla AS (
      SELECT asset_key, MAX(run_ended_at) AS last_ok
      FROM ingestion_runs
      WHERE status IN ('success', 'partial')
      GROUP BY asset_key
  )
  SELECT asset_key,
         last_ok,
         date_diff('hour', last_ok, now()) AS hours_stale,
         CASE
             WHEN asset_key IN ('sapo/sapo_webhook_consumer_asset', 'sapo/sapo_history_log_asset')
                  AND date_diff('hour', last_ok, now()) <= 12  THEN 'healthy'
             WHEN asset_key LIKE 'sapo/%batch%'
                  AND date_diff('hour', last_ok, now()) <= 28  THEN 'healthy'
             WHEN asset_key IN ('shopee/shopee_income_file_drop_asset',
                                'sheets/sheets_targets_asset',
                                'sheets/sheets_marketing_spend_asset')
                  AND date_diff('hour', last_ok, now()) <= 48  THEN 'healthy'
             WHEN asset_key = 'misa_amis/misa_sales_file_drop_asset'
                  AND date_diff('hour', last_ok, now()) <= 192 THEN 'healthy'
             WHEN asset_key LIKE 'recon/%'
                  AND date_diff('hour', last_ok, now()) <= 28  THEN 'healthy'
             ELSE 'stale'
         END AS sla_status
  FROM sla
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 4. Recon Drift

- **Business Definition:** Percentage discrepancy between source count and destination count, as measured by reconciliation assets. Drift > 1% requires investigation.
- **Logic (SQL):**
  ```sql
  -- Extract recon metrics from metadata_json (stored as JSON)
  SELECT
      asset_key,
      run_started_at,
      status,
      CAST(metadata_json->>'source_count' AS BIGINT) AS source_count,
      CAST(metadata_json->>'dest_count'   AS BIGINT) AS dest_count,
      CAST(metadata_json->>'drift_pct'    AS DOUBLE) AS drift_pct
  FROM ingestion_runs
  WHERE asset_key LIKE 'recon/%'
    AND status IN ('success', 'partial')
  ORDER BY run_started_at DESC
  ```
- **Thresholds:** `drift_pct = 0` → healthy; `0 < drift_pct ≤ 1` → warning; `drift_pct > 1` → alert.
- **Recon assets:** `recon/recon_sapo_orders_daily`, `recon/recon_sapo_customers_daily`, `recon/recon_misa_daily`, `recon/recon_shopee_daily`

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** business-defined
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.

#### 5. Run Success Rate (7d)

- **Business Definition:** Fraction of runs in the last 7 days that ended in `success` or `partial`, per asset. Persistent failures indicate a broken pipeline leg.
- **Logic (SQL):**
  ```sql
  SELECT
      asset_key,
      COUNT(*) AS total_runs,
      COUNT(CASE WHEN status IN ('success', 'partial') THEN 1 END) AS ok_runs,
      ROUND(COUNT(CASE WHEN status IN ('success', 'partial') THEN 1 END) * 100.0
            / NULLIF(COUNT(*), 0), 1) AS success_rate_pct
  FROM ingestion_runs
  WHERE run_started_at >= now() - INTERVAL '7 days'
  GROUP BY asset_key
  ```

- **Business Logic:** Calculate at the grain and scope documented for this context or metric-level dbt source; apply valid-status filters before aggregation to avoid canceled orders, duplicate records, or join-grain inflation.
- **Formula:** See `Logic (SQL)` for the reusable calculation expression; the the business formula follows the metric definition and source grain above.
- **Unit:** %
- **Common Misunderstandings:** Do not use this metric outside the documented scope; do not compare it with a similarly named metric from another domain when business definition or grain differs.
- **Pitfalls / Edge Cases:** Check null handling, canceled/returned statuses, duplicate keys, and joins that can multiply measures before publishing reports.
