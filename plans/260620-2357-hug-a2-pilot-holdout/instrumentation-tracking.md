# Instrumentation & Tracking

## Cohort Label Table

A single lightweight table created before pilot launch. Written once at assignment time; never updated (immutable cohort record).

**Table: `hug_pilot_cohorts` in `crm.db`**

```sql
CREATE TABLE IF NOT EXISTS hug_pilot_cohorts (
    customer_key     TEXT NOT NULL,          -- mart_customer_tier.customer_key
    arm              TEXT NOT NULL,          -- 'A' | 'B'
    group_           TEXT NOT NULL,          -- 'treatment' | 'control'
    pilot_start_date DATE NOT NULL,          -- date cohort was frozen
    exclusion_reason TEXT,                   -- NULL if eligible; 'b2b' | 'aov_lt500k' | 'zero_net_revenue' | 'zone3' if excluded
    notes            TEXT,
    PRIMARY KEY (customer_key, arm)
);
```

Populate via a one-time Python script (not dbt — crm.db is write-only from CRM jobs, not dbt):

```python
# Pseudocode — run once before pilot launch
import duckdb, sqlite3, hashlib

olap = duckdb.connect("/app/var/data_lake/serving/olap.duckdb", read_only=True)
crm  = sqlite3.connect("/app/crm/crm.db")

# Pull eligible customers per arm from mart
arm_a_eligible = olap.execute("""
    SELECT customer_key
    FROM main_marts.mart_customer_tier
    WHERE source_contact_quality = 'masked'
      AND order_count >= 2
      AND recency_days <= 90
      AND lifetime_value / order_count >= 1000000
      AND lifetime_value > 0
      AND customer_key NOT IN (/* B2B exclusion list */)
""").fetchall()

for (ck,) in arm_a_eligible:
    h = int(hashlib.md5(ck.encode()).hexdigest(), 16) % 100
    group = 'treatment' if h < 65 else 'control'
    crm.execute("INSERT OR IGNORE INTO hug_pilot_cohorts VALUES (?,?,?,date('now'),NULL,NULL)",
                (ck, 'A', group))

# Similar block for Arm B (Zone 2 marketplace, excl Bucket A + outliers)
crm.commit()
```

**Run once; never re-run** (hash is deterministic but re-running would be confusing). Verify row counts match expected N before pilot launch.

---

## Data Sources Per Metric

### Arm A metrics

| Metric | Query anchor | Join path |
|--------|-------------|-----------|
| Opt-in rate | `hug_identities` (crm.db) | `hug_identities.customer_id` → `hug_pilot_cohorts.customer_key` via `mart_customer_tier.customer_id` |
| Repeat purchase 60d | `fact_orders` | `fact_orders.customer_id` + `ordered_at BETWEEN pilot_start AND pilot_start + 60` + cohort join |
| Redemption rate | `fact_orders.order_coupon_code = 'HUG50'` | Joined to treatment cohort; count distinct customer_key |
| Incremental CM | `fact_orders.contribution_margin` | By arm/group; exclude `net_revenue = 0` rows |
| Scan rate | `hug_scans` log (crm.db or Cloudflare D1 event log) | `campaign_id` filter for A2 campaign; count distinct scans / tems shipped |
| Tem coverage | Warehouse shipment log (manual or WMS export) | Cross-reference treatment customer_key list vs parcels shipped |

### Arm B metrics

| Metric | Query anchor | Join path |
|--------|-------------|-----------|
| Reactivation rate R | `fact_orders` | `ordered_at BETWEEN broadcast_date AND broadcast_date + 120` + cohort join; binary per customer |
| Redemption rate | `fact_orders.order_coupon_code = 'HUGVIP'` | Treatment cohort only |
| Incremental CM | `fact_orders.contribution_margin` | By arm/group; zero-net-revenue excluded |
| Time-to-reactivation | `MIN(ordered_at) − broadcast_date` | Per treatment customer; only reactivated customers |

---

## Exclusion Filters (apply to ALL metric calculations)

These must be applied at query time in every readout, not just at cohort assignment:

```sql
-- Zero-net-revenue orders (artifact / export accounts)
AND fo.net_revenue > 0

-- B2B/export accounts
AND fo.customer_id NOT IN (
    SELECT customer_id FROM main_marts.mart_customer_tier
    WHERE customer_key IN (/* confirmed B2B exclusion list */)
)

-- Outlier accounts (CHANNEL_OTHER / CHANNEL_SOCIAL negative-CM)
AND fo.customer_id NOT IN (/* Fine Japan-USA customer_id, ~3 outlier accounts */)
```

---

## Weekly Readout Query Template

Run weekly by Data team. Output to Markdown table in `plans/260620-2357-hug-a2-pilot-holdout/reports/`.

```sql
-- Arm A weekly snapshot
SELECT
    hpc.group_,
    COUNT(DISTINCT hpc.customer_key)                                    AS cohort_n,
    COUNT(DISTINCT hi.customer_id)                                      AS opted_in,
    ROUND(100.0 * COUNT(DISTINCT hi.customer_id)
          / COUNT(DISTINCT hpc.customer_key), 1)                        AS opt_in_pct,
    COUNT(DISTINCT CASE WHEN fo.ordered_at >= :pilot_start
                        AND fo.ordered_at <= :pilot_start + INTERVAL 60 DAY
                        AND fo.net_revenue > 0
                   THEN fo.customer_id END)                             AS repeat_buyers_60d,
    SUM(CASE WHEN fo.ordered_at >= :pilot_start
             AND fo.net_revenue > 0
             THEN fo.contribution_margin END)                           AS total_cm,
    COUNT(CASE WHEN fo.order_coupon_code = 'HUG50' THEN 1 END)         AS hug50_redemptions
FROM hug_pilot_cohorts hpc
LEFT JOIN hug_identities hi      ON hi.customer_id = /* map customer_key → customer_id */
LEFT JOIN main_marts.fact_orders fo ON fo.customer_id = /* same map */
WHERE hpc.arm = 'A'
GROUP BY hpc.group_;
```

```sql
-- Arm B weekly snapshot
SELECT
    hpc.group_,
    COUNT(DISTINCT hpc.customer_key)                                    AS cohort_n,
    COUNT(DISTINCT CASE WHEN fo.ordered_at >= :broadcast_date
                        AND fo.ordered_at <= :broadcast_date + INTERVAL 120 DAY
                        AND fo.net_revenue > 0
                   THEN fo.customer_id END)                             AS reactivated,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN fo.ordered_at >= :broadcast_date
                                      AND fo.net_revenue > 0
                                 THEN fo.customer_id END)
          / COUNT(DISTINCT hpc.customer_key), 1)                        AS reactivation_rate_pct,
    SUM(CASE WHEN fo.ordered_at >= :broadcast_date
             AND fo.net_revenue > 0
             THEN fo.contribution_margin END)                           AS total_cm,
    COUNT(CASE WHEN fo.order_coupon_code = 'HUGVIP' THEN 1 END)        AS hugvip_redemptions
FROM hug_pilot_cohorts hpc
LEFT JOIN main_marts.fact_orders fo ON fo.customer_id = /* map */
WHERE hpc.arm = 'B'
GROUP BY hpc.group_;
```

**Note on customer_key → customer_id mapping:** `mart_customer_tier.customer_key` is the mart's canonical key; `fact_orders.customer_id` is the CRM integer FK. The join must go through `mart_customer_tier` or the `dim_customers` bridge. Verify the correct join key before first readout run.

---

## Coupon Code Registry

| Code | Arm | Sapo config | Purpose |
|------|-----|------------|---------|
| `HUG50` | A (Hug parcel) | 50K off, min order 1M, `once_per_customer=true`, 60d expiry from issuance | Identity-capture offer; issued at opt-in |
| `HUGVIP` | B (Shopee broadcast) | 50K off, min order 1M, `once_per_customer=true`, 120d expiry from broadcast date | Reactivation offer; embedded in broadcast message |

Both codes must be created in Sapo admin **before** pilot launch. Distinct codes are the only reliable way to attribute redemptions to the correct arm in `fact_orders.order_coupon_code` without a complex join.

---

## Artifact Storage

| Artifact | Location | Updated |
|----------|---------|---------|
| Cohort assignment table | `crm.db: hug_pilot_cohorts` | Once at pilot start |
| Weekly readout reports | `plans/260620-2357-hug-a2-pilot-holdout/reports/readout-YYYYMMDD.md` | Weekly by Data |
| Broadcast send log | Shopee Seller Center export + `plans/.../reports/broadcast-send-log.md` | Day 1, Day 8 |
| Decision gate write-up | `plans/260620-2357-hug-a2-pilot-holdout/reports/decision-gate-arm-a-YYYYMMDD.md` | Day 60–90 |
| Decision gate write-up | `plans/260620-2357-hug-a2-pilot-holdout/reports/decision-gate-arm-b-YYYYMMDD.md` | Day 120–180 |
