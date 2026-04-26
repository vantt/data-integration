# Phase 4 — Morning Lark Digest

## Context Links
- Parent: [../plan.md](./plan.md)
- Depends on: [phase-01-metadata-contract.md](./phase-01-metadata-contract.md), [phase-02-asset-checks.md](./phase-02-asset-checks.md), [phase-03-reconciliation.md](./phase-03-reconciliation.md)
- Lark client: `orchestration/notifications/lark_client.py::send_lark_card`
- Pattern reference: `orchestration/sensors/failure_alerting.py` (Lark-using sensor)

## Overview
- **Priority:** P1 — this is the user's "glance once" surface
- **Status:** ✅ DONE (commit `5d171fe`)
- **Effort:** ~3h
- **Summary:** Dagster schedule at 08:00 Asia/Ho_Chi_Minh runs a job that queries `ingestion_health.duckdb`, composes one Lark interactive card summarizing every source's 24h status, posts via existing `send_lark_card`. No new Lark plumbing — reuse existing webhook.

## Key Insights
- User wants ONE card, not one-per-source (noise avoidance).
- Digest is the USER-FACING contract: per source = one emoji + rows + median + freshness + drift.
- Must gracefully handle: source-missing-from-DB (never ran), source-has-run-but-zero-rows, recon-failed.
- `send_lark_card` has stub fallback when `LARK_ALERT_WEBHOOK` unset — dev machine stays quiet.

## Requirements

### Functional
- Post at 08:00 ICT, Mon–Sun, one interactive card with header "Data Ingestion Morning Report — <date>".
- For each asset in a known set, card row format: `<emoji> <short_name> · 24h: <rows> (med <n>, <±%>) · fresh: <age> <recon>`.
- Emoji rules:
  - `green` if last run success AND 24h_rows ≥ 50% of 7d_median AND (no recon or |drift| ≤ 1%).
  - `yellow` if WARN condition (trend below threshold, or 1% < drift ≤ 5%).
  - `red` if ERROR (past freshness SLA, status=failed, or drift > 5%).
- Card header color = worst-severity across all rows.

### Non-functional
- Total query cost to build card < 2s.
- Card delivery failure must not fail the job (log-stub fallback already in client).
- Must be idempotent: running twice same day posts twice (acceptable — no dedup logic needed).

## Architecture

```
┌─────────────────────────────────────────┐
│ @schedule morning_digest_schedule       │
│   cron = 0 8 * * *                      │
│   target = morning_digest_job           │
└──────────────┬──────────────────────────┘
               ▼
┌─────────────────────────────────────────┐
│ @op compose_and_send_digest             │
│  1. read ingestion_health               │
│  2. build DigestRow per asset           │
│  3. compose fields dict                 │
│  4. send_lark_card(title, fields, color)│
└─────────────────────────────────────────┘
```

Implemented as an `@op`-based job (simpler than an asset since it has no downstream data) but could also be an `@asset` for consistency. Choose op+job to avoid cluttering the asset graph.

## Related Code Files

### Create
- `orchestration/ops/morning_digest.py` — ~150 lines; contains `build_digest_rows()`, `compose_card_fields()`, the `@op`, and `morning_digest_job = job(...)`.

### Modify
- `orchestration/definitions.py` — register the job + schedule.

### Delete
- None.

## Data Model (internal)

```python
@dataclass
class DigestRow:
    short_name: str                  # "sapo_orders"
    asset_key: str                   # "sapo/sapo_orders_batch_asset"
    status: Literal["green","yellow","red","gray"]
    rows_24h: int | None
    median_7d: int | None
    pct_vs_median: float | None
    fresh_age_min: int | None        # minutes since last success
    drift_pct: float | None          # from recon, if applicable
    note: str | None                 # e.g. "never run", "recon failed"
```

Known asset list lives in the same module (hard-coded dict — one place to maintain):
```python
KNOWN_ASSETS = [
    ("sapo_webhook",  "sapo/sapo_webhook_consumer_asset",  None),
    ("sapo_history",  "sapo/sapo_history_log_asset",       None),
    ("sapo_orders",   "sapo/sapo_orders_batch_asset",      "recon/sapo_orders_daily"),
    ("sapo_customers","sapo/sapo_customers_batch_asset",   "recon/sapo_customers_daily"),
    ("sapo_products", "sapo/sapo_products_batch_asset",    None),
    ("sapo_accounts", "sapo/sapo_accounts_batch_asset",    None),
    ("shopee",        "shopee/shopee_income_file_drop_asset","recon/shopee_daily"),
    ("misa",          "misa_amis/misa_sales_file_drop_asset","recon/misa_daily"),
    ("sheet_targets", "sheets/sheets_targets_asset",       None),
    ("sheet_spend",   "sheets/sheets_marketing_spend_asset",None),
]
```

## Implementation Steps

1. **SQL query** in `build_digest_rows()`:
   ```sql
   WITH recent AS (
     SELECT asset_key,
            MAX(run_started_at) FILTER (WHERE status='success') AS last_ok,
            SUM(rows_written) FILTER (WHERE run_started_at >= now()-INTERVAL 1 DAY) AS r_24h
     FROM ingestion_runs GROUP BY asset_key
   ),
   daily AS (
     SELECT asset_key, date_trunc('day', run_started_at) d, SUM(rows_written) r
     FROM ingestion_runs
     WHERE run_started_at >= now() - INTERVAL 7 DAY AND status='success'
     GROUP BY 1,2
   ),
   med AS (SELECT asset_key, median(r) med7 FROM daily GROUP BY 1)
   SELECT r.asset_key, r.last_ok, r.r_24h, m.med7
   FROM recent r LEFT JOIN med m USING (asset_key);
   ```
2. **Recon query** (separate, small):
   ```sql
   SELECT asset_key, (metadata_json->>'drift_pct')::DOUBLE
   FROM ingestion_runs
   WHERE asset_key LIKE 'recon/%'
     AND run_started_at >= now() - INTERVAL 1 DAY
   QUALIFY row_number() OVER (PARTITION BY asset_key ORDER BY run_started_at DESC) = 1;
   ```
3. **Classify** each row into green/yellow/red per rules above.
4. **Compose** fields dict preserving order from `KNOWN_ASSETS`. Each value formatted as:
   `"✅ 12,430 (med 11,800, +5%) · 3m"` or `"⚠️ 0 (med 120) · 7h"` or `"❌ RECON DRIFT src/dst -13%"`.
5. **Header color** = worst severity seen → `red|orange|green` mapped to Lark template.
6. **Call** `send_lark_card(title, fields, color)`. Title = `f"Data Ingestion Morning Report — {today_ict()}"`.
7. **Register** in `definitions.py`:
   ```python
   from orchestration.ops.morning_digest import morning_digest_job
   @schedule(job=morning_digest_job, cron_schedule="0 8 * * *", execution_timezone="Asia/Ho_Chi_Minh")
   def morning_digest_schedule(context):
       return RunRequest(run_key=None)
   ```
8. **Smoke test**:
   - Unset `LARK_ALERT_WEBHOOK` → materialize op → verify stdlib logger shows card content.
   - Set webhook → trigger manually → verify card in Lark chat.
9. **Unit test** `classify()` with synthetic DigestRow inputs covering each color transition boundary.

## Todo List

- [ ] Create `orchestration/ops/morning_digest.py` with op + job
- [ ] Implement 2 SQL queries (recent/median, recon drift)
- [ ] Implement `DigestRow` dataclass + `classify()` function
- [ ] Implement card field formatter
- [ ] Register job + schedule in `definitions.py`
- [ ] Unit test `classify()` with 6+ boundary cases
- [ ] Manual dev test (log-stub mode)
- [ ] Manual prod test (real webhook)
- [ ] Add to `orchestration/docs/` — how to adjust thresholds / add new source

## Success Criteria

- At 08:00 ICT daily, Lark chat has one card.
- If sapo_customers returns 0 rows across 24h with 7d median > 100 → card row renders yellow ⚠️.
- If raw DB file missing → job doesn't crash Dagster; posts a red card with "health DB unreachable" note.
- Unsetting `LARK_ALERT_WEBHOOK` → job still succeeds, logs card content.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Lark card character limit (fields truncated) | Low | Low | Keep each value < 80 chars; 10 rows fits |
| Digest posts during server downtime & silently skipped | Low | Med | Lark failure returns False but logged; Dagster run shows as succeeded — acceptable (user will notice no card) |
| `KNOWN_ASSETS` drifts from actual registered assets | Med | Low | Add a lint test: iterate `defs.get_asset_graph()` and assert every `*_ingestion` group asset is in `KNOWN_ASSETS` |
| Classification thresholds hard-coded, not in SLA YAML | Med | Low | Future improvement — for now, keep in module; re-reading SLA YAML works because Phase 2 already loads it |
| Timezone mismatch: `now() - INTERVAL 1 DAY` in DuckDB returns UTC | Med | Low | Use `TIMESTAMPTZ` throughout (enforced by Phase 0 schema); display times in ICT only in card body |

## Next Steps

- This is the user's primary daily touchpoint. After a week of running, reassess which signals are most/least valuable — may trim or expand rows.
- Phase 5 (KPI closure) if pursued would add a revenue-invariant line to this same card.
