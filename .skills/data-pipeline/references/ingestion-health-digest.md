# Ingestion Health Digest — Pattern Reference

Reusable pattern for **observability over a multi-asset ingestion platform**: persist one row per asset run, compose a daily "morning digest" card (green/yellow/red per source), deliver via chat. Surfaces stale pipelines, source drift, zero-row streaks, and revenue mismatches BEFORE stakeholders notice missing data.

Extracted from `orchestration/ops/morning_digest.py` + `orchestration/ops/ingestion_health.py` + `orchestration/ops/dlt_metrics.py` after post-mortems 2026-04-15 (design) and 2026-04-22 (accuracy fix).

---

## When to use

Trigger this pattern when **all** of the following hold for the target project:

- Pipeline has ≥ 3 independent data assets on different cadences (batch + cursor + file-drop).
- Freshness matters — a silently-failed ingest becomes a downstream data quality incident within 24 hours.
- A stakeholder (ops / analyst / lead) already asks "did X run last night?" in chat. Automate the answer.
- The orchestrator (Dagster, Airflow, Prefect…) does not already provide a source-level daily digest. Its built-in dashboards track JOB status, not **business-source** status ("Sapo orders" vs "run 42 of sapo_orders_batch_asset").

Skip if: fewer than 3 assets, or stakeholders read a live dashboard (Metabase, Grafana) daily and that's sufficient.

---

## Architecture

```
        ┌─────────────────────────────────────────────────────┐
        │  Ingestion assets (dlt, API, file-drop, webhook...) │
        └───────────────────────────┬─────────────────────────┘
                                    │ every run calls
                                    ▼ record_run(...)
                     ┌──────────────────────────────┐
                     │  ingestion_health.duckdb     │
                     │  (dedicated DB, not serving) │
                     │  table: ingestion_runs       │
                     │  PK: (asset_key, run_id)     │
                     └──────────────┬───────────────┘
                                    │ scheduled read
                                    ▼
                     ┌──────────────────────────────┐
                     │  Morning digest job          │
                     │  06:00 ICT / local biz time  │
                     │  Window: yesterday 0h-24h    │
                     └──────────────┬───────────────┘
                                    │
                                    ▼
                     ┌──────────────────────────────┐
                     │  Lark / Slack / Email card   │
                     └──────────────────────────────┘
```

**Design invariants:**

1. **Health DB is separate** from the serving DB — Metabase locks the serving DB, so recorder writes must not contend. Use a dedicated DuckDB file.
2. **`record_run` must never fail the asset**. Wrap in `try/except`, log warning, let the ingestion job complete. Health is observability, not a blocker.
3. **Digest failures must never fail Dagster**. Same principle: if Lark is down, log and return.
4. **Classification lives in query time**, not persist time. Store raw facts; derive green/yellow/red in digest code.

---

## Schema

```sql
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       VARCHAR NOT NULL,       -- "sapo/sapo_orders_batch_asset"
    run_id          VARCHAR NOT NULL,       -- Dagster/Airflow run UUID
    run_started_at  TIMESTAMPTZ NOT NULL,   -- UTC-native, display in biz TZ later
    run_ended_at    TIMESTAMPTZ,
    duration_s      DOUBLE,
    status          VARCHAR NOT NULL,       -- success | skipped | failed | partial
    rows_fetched    BIGINT,                 -- from source (nullable)
    rows_written    BIGINT,                 -- to destination (see section below)
    rows_new        BIGINT,
    rows_updated    BIGINT,
    cursor_before   VARCHAR,
    cursor_after    VARCHAR,
    schema_hash     VARCHAR,
    file_sha256     VARCHAR,
    file_mtime      TIMESTAMPTZ,
    metadata_json   JSON,                   -- escape hatch: dlt LoadInfo, drift_pct, etc.
    PRIMARY KEY (asset_key, run_id)
);
```

### Composite PK is load-bearing — always filter BOTH columns in UPDATE/DELETE

Dagster (and most orchestrators) fan out ONE `run_id` across multiple assets in the same scheduled job. A daily batch job that runs orders + customers + products + accounts gives you 4 rows sharing the same `run_id`, distinguished by `asset_key`. Any DML that filters only on `run_id` hits every sibling and silently corrupts them. **This bug cost us 182 corrupted rows on 2026-04-22**; we had to restore from daily backup.

```sql
-- ✅ Correct
UPDATE ingestion_runs SET rows_written = ? WHERE asset_key = ? AND run_id = ?;

-- ❌ Silent data corruption
UPDATE ingestion_runs SET rows_written = ? WHERE run_id = ?;
```

### Status values

| Value | Meaning | Example |
|-------|---------|---------|
| `success` | Ran OK, wrote ≥ 1 row | dlt loaded 500 new orders |
| `skipped` | Ran OK, source had nothing new — **not an error** | Cursor advanced but API returned 0 rows |
| `failed` | Exception before completion | HTTP 401, parser error |
| `partial` | Some rows failed, some succeeded | Rare — optional for sources that support per-row reporting |

The `last_ok` freshness query **includes both `success` AND `skipped`** — a cursor poll that correctly reports "nothing new" is still a healthy heartbeat.

---

## Component breakdown

### 1. The recorder — `ingestion_health.record_run(...)`

Single public API. Idempotent on `(asset_key, run_id)` via `INSERT ... ON CONFLICT DO UPDATE`. Lazy DDL (CREATE TABLE IF NOT EXISTS on first write) so the module never fails at import time.

Template: [`templates/ingestion-health-recorder-template.py`](templates/ingestion-health-recorder-template.py)

Path resolution priority:

1. `INGESTION_HEALTH_DB` — explicit full path override
2. `DBT_DATA_LAKE_PATH` — append `/monitoring/ingestion_health.duckdb`
3. **Fail loud** — refuse to write to a hardcoded fallback that can diverge between host and container.

### 2. Asset instrumentation pattern

```python
@asset(...)
def my_ingestion_asset(context):
    asset_key_str = "source/my_asset_name"
    started = datetime.now(timezone.utc)
    status = "failed"
    rows_written = None
    info_dict = {}
    try:
        load_info = run_pipeline(...)
        info_dict = load_info.asdict() if hasattr(load_info, "asdict") else {}
        rows_written = extract_rows_written(info_dict)
        status = "success" if extract_loaded_packages(info_dict) else "skipped"
        return Output(value="OK", metadata={...})
    finally:
        try:
            record_run(
                asset_key=asset_key_str,
                run_id=context.run_id,
                run_started_at=started,
                status=status,
                rows_written=rows_written,
                metadata={"load_info": info_dict, ...},
            )
        except Exception as e:
            context.log.warning(f"health recorder failed: {e}")
```

**Key point:** `try/finally` ensures health is recorded even when the asset fails. `started` is captured BEFORE the work — if the asset crashes at second 3 of 60, the row says `status='failed', run_started_at=t0` not `t0+3`.

### 3. Row count extraction — **the accuracy trap**

**dlt's `LoadInfo.asdict()` does NOT expose row counts** for the filesystem destination (plain parquet or Delta Lake) in current versions. Both `jobs[].metrics.items_count` and top-level `job_metrics[].items_count` are absent. `file_size` is the only payload hint per job.

Naïve `extract_rows_written(info_dict)` that relies on metrics returns `0` even when an 8 MB parquet was written — and **the digest reports "không có đơn mới / no new data" for days while source is healthy**. This masked real orders for ~6 weeks in our Sapo integration until stakeholders escalated.

**Solution: 3-layer fallback** in `extract_rows_written`:

```
Layer 1: metrics walk        — load_packages[].jobs[].metrics.items_count
         └── works for: dlt versions that DO populate it, future-proof
Layer 2: file_id glob        — {DBT_DATA_LAKE_PATH}/{dataset}/{table}/**/{file_id}.parquet
         └── works for: plain-parquet filesystem destination
         └── DuckDB COUNT(*) reads parquet footer only — O(1) per file
Layer 3: _dlt_load_id scan   — scan ALL parquets under table dir, filter by load's ids
         └── works for: Delta Lake destination (file_id ≠ on-disk name)
         └── every dlt row carries _dlt_load_id, always reliable
```

Template: [`templates/dlt-row-count-extractor-template.py`](templates/dlt-row-count-extractor-template.py)

**Performance note for Layer 3:** grows O(N files) per call. At current scale (hundreds of files per table) it's ~100ms. After a year of 10-min polls it could be 1-3 seconds per run. Optimization path (YAGNI until needed): filter glob by file mtime > `loads_ids[0]` (epoch seconds at load start).

### 4. Time window — business calendar day, not rolling 24h

Most stakeholders read "hôm qua" / "yesterday" as a **complete calendar day in business time zone**, not a rolling 24-hour window ending when the digest fires. The difference matters at boundaries:

- Rolling 24h, fired at 06:00 ICT on 22 April: covers 06:00 21 April → 06:00 22 April (straddles two business days)
- Calendar day: covers 00:00 21 April → 24:00 21 April ICT (one complete business day)

Schedule the digest AFTER the business day has closed — typically 06:00 local time works. All downstream batch and recon jobs complete by then, and people read it with their first coffee.

SQL pattern (DuckDB, ICU extension auto-loaded):

```sql
-- Rows from yesterday's business-day (Asia/Ho_Chi_Minh) window
WHERE (run_started_at AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE
    = ((now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::DATE - 1)
```

`AT TIME ZONE <iana_name>` applied to TIMESTAMPTZ gives wall-clock TIMESTAMP in that TZ; cast to DATE for calendar day. Subtract INTEGER (not INTERVAL) to get yesterday as DATE.

**Freshness (`last_ok` / SLA age) stays absolute** — not windowed. A pipeline that last ran 15 hours ago is stale at any time zone.

### 5. Classification — severity rules

Keep these in code (not config) so the rules are discoverable by anyone reading the digest. Ranking: `green < gray < yellow < red` (worst wins).

```python
def classify(row: DigestRow) -> Literal["green", "yellow", "red", "gray"]:
    # 1. Drift overrides everything (including "never run") — it's actionable
    if row.drift_pct is not None:
        if abs(row.drift_pct) > 5.0: return "red"
        if abs(row.drift_pct) > 1.0: return "yellow"

    # 2. No-data state
    if row.note in ("never run", "health DB unreachable"):
        return "gray"

    # 3. Stale beyond SLA — SLA_HOURS typically 12
    if row.fresh_age_min is not None and row.fresh_age_min > SLA_HOURS * 60:
        return "red"

    # 4. Volume vs 7d median
    if row.median_7d and row.median_7d > 0 and row.rows_yday is not None:
        if row.rows_yday / row.median_7d < 0.5:
            return "yellow"

    # 5. Zero-row streaks (cursor advanced but returned 0 rows N times in a row)
    if row.zero_streak >= 3: return "red"
    if row.zero_streak >= 2: return "yellow"

    # 6. Most recent run failed
    if row.note == "last run failed": return "red"

    return "green"
```

Why these rules, in this order:

- **Drift first, even for gray:** recon may run daily and catch source-warehouse mismatch even when the asset itself never ran today. Actionable.
- **SLA before volume:** a 20h-old success is worse than a fresh "only 10% of median".
- **Zero-streak:** cursor assets legitimately return 0 rows during quiet hours; ≥ 3 consecutive is suspicious (source outage or cursor bug).

### 6. Asset-type-aware messaging

Same "rows = 0" means different things per asset type. Label each asset with a type in the registry:

| Type | Cadence | `rows = 0` means | Message template |
|------|---------|------------------|------------------|
| `cursor` | Every few min | Source had nothing new — **normal** | `Không có {unit} mới (đã chạy {runs} lần hôm qua)` |
| `batch` | Daily | Either no new rows OR job skipped | `Batch hôm qua: không có {unit} mới` |
| `file_drop` | On file arrival | Upstream file unchanged | `File nguồn chưa thay đổi` |

Do **not** reuse a single "0 rows" template for all types. `batch: 0` on a consumer e-commerce platform is alarming; `cursor: 0` at 3am is routine. Wrong messaging produces alert fatigue.

Template: [`templates/ingestion-health-digest-template.py`](templates/ingestion-health-digest-template.py)

### 7. Business-KPI integration (optional but high-value)

Beyond per-asset stats, add ONE line at the top that answers the stakeholder's real question: **"did yesterday's revenue match between source and warehouse?"**

```
💰 Doanh thu hôm qua: ✅ Sapo: 45.123.000 ₫ · Warehouse: 45.100.000 ₫ · lệch: -0.05%
```

- Run a nightly KPI-closure job (source API ↔ warehouse count/sum) that writes its own row into `ingestion_runs` with `asset_key='kpi/revenue_daily'` and drift_pct in metadata.
- Digest pulls that row and renders above the per-asset table.
- Green < 0.1%, yellow 0.1-0.5%, red > 0.5% — stricter than per-asset drift because this is revenue.

This single line is what stops escalations.

### 8. Delivery — graceful degradation

```python
try:
    send_lark_card(title=title, fields=fields, color=color)
except Exception as exc:
    logger.error(f"digest: Lark send raised: {exc}")
    # MUST NOT re-raise — Dagster run must succeed even when Lark is down
```

Provide `DIGEST_DRY_RUN=1` env to print the card to stdout instead of sending. Always use dry-run when iterating.

---

## Production checklist

When adopting this pattern in a new project, verify each item:

- [ ] Health DB path resolves correctly in **both** host dev (`.env.local`) and container (`.env.docker`). Mis-matched paths = silent empty digest.
- [ ] Health DB is included in daily backup rotation. The 2026-04-22 incident recovered from `app_data/backups/YYYYMMDD-HHMMSS/…/ingestion_health.duckdb` — do not skip this.
- [ ] `record_run` is wrapped in try/except at every call site. Grep `record_run` and verify.
- [ ] `extract_rows_written` runs with `DBT_DATA_LAKE_PATH` set. Without it, Layer 2/3 silently return None → persistent 0 rows.
- [ ] Digest schedule is AFTER recon/KPI-closure. Typical ordering: recon 04:30 → KPI 04:45 → digest 06:00, all in business TZ.
- [ ] Digest wrapped in try/except around `send_*_card`. Log, don't raise.
- [ ] Dry-run via `DIGEST_DRY_RUN=1` verified before enabling schedule.
- [ ] Asset registry includes ALL known assets with correct `asset_type` (cursor / batch / file_drop) and `unit_label`.
- [ ] SLA hours chosen per pipeline cadence. 12h works for daily batches; cursor pipelines may want 6h or lower.
- [ ] Zero-streak detection has an N >= 2 threshold. Lower than that = noisy alerts during quiet business hours.
- [ ] Backfill script exists (one-shot) with composite-PK UPDATE. See [`scripts/maintenance/backfill-ingestion-health-rows-written.py`](../../scripts/maintenance/backfill_ingestion_health_rows_written.py).
- [ ] Every UPDATE/DELETE on `ingestion_runs` has BOTH `asset_key` and `run_id` in WHERE. Code review rule.

---

## Backfill strategy (when you deploy a row-count fix)

Existing rows stay at their stored value. If those values are wrong (bug in the OLD extractor persisted zeros), the next digest is still wrong **until each asset runs again with the fixed code** and overwrites its row. For daily batches that's a full day of wrong reporting — unacceptable for business-facing dashboards.

Solution: replay the stored `metadata_json.load_info` through the FIXED extractor and UPDATE in place. The backfill script [`backfill-ingestion-health-rows-written.py`](../../scripts/maintenance/backfill_ingestion_health_rows_written.py) does this:

1. Iterate `ingestion_runs` WHERE `status IN ('success', 'skipped') AND (rows_written IS NULL OR rows_written = 0)`.
2. For each row: `n = extract_rows_written(metadata_json.load_info)`.
3. If `n > 0`: `UPDATE ... WHERE asset_key = ? AND run_id = ?` (composite PK — critical).
4. Otherwise skip.

**Idempotent** — re-running excludes already-backfilled rows via the WHERE filter.

**Dry-run first** with `--dry-run` to preview impact.

---

## Post-mortem index

| Date | Incident | Lesson file |
|------|----------|-------------|
| 2026-04-15 | Design: need per-source digest | `lessons-learned.md` L18 (phase-04 plan) |
| 2026-04-22 AM | `rows_written=0` for ~6 weeks because dlt LoadInfo doesn't expose row counts | `lessons-learned.md` L20 |
| 2026-04-22 AM | Window was rolling 24h, stakeholder expected "yesterday 0h-24h" calendar day | `lessons-learned.md` L21 |
| 2026-04-22 AM | Backfill UPDATE filtered only on `run_id` → corrupted 182 sibling rows | `lessons-learned.md` L22 |

---

## Related docs

- [`lessons-learned.md`](lessons-learned.md) — detailed post-mortem notes
- [`templates/ingestion-health-recorder-template.py`](templates/ingestion-health-recorder-template.py)
- [`templates/dlt-row-count-extractor-template.py`](templates/dlt-row-count-extractor-template.py)
- [`templates/ingestion-health-digest-template.py`](templates/ingestion-health-digest-template.py)
- [`templates/backfill-health-rows-written-template.py`](templates/backfill-health-rows-written-template.py)
