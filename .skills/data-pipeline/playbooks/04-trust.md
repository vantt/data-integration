# TRUST Playbook — Độ tin cậy dữ liệu

## Trách nhiệm

TRUST là nhóm đảm bảo mọi assertion về dữ liệu (freshness, volume, recon, KPI closure) được verify và phát hiện trước khi stakeholder hỏi. TRUST nhận đầu vào từ mọi ingestion asset (INGEST group), ghi kết quả vào health DB riêng biệt (không phải serving DB), và phát cảnh báo qua digest hàng ngày. Đầu ra là "morning digest card" (Lark/Slack/email) phân loại từng data source theo mức độ nghiêm trọng (green/yellow/red).

Không có TRUST, pipeline bị lỗi im lặng có thể kéo dài nhiều tuần mà không ai hay (thực tế đã xảy ra với Sapo integration: `rows_written=0` suốt ~6 tuần).

---

## Pre-flight Checklist (đọc TRƯỚC khi implement)

- [ ] Health recorder: composite PK `(asset_key, run_id)` — UPDATE/DELETE phải filter BOTH columns (L44). Dagster fan-out 1 `run_id` cho nhiều assets → filter chỉ `run_id` = silent data corruption (182 rows bị corrupt 2026-04-22)
- [ ] datetime serialization: dùng ISO string cho `run_started_at/run_ended_at`; dùng `or 0.0` (float, không phải int) fallback cho `MetadataValue.float()` (L41, L66). `or 0` returns `int(0)` → type error
- [ ] Row count extraction 3-layer fallback: (1) metrics walk → (2) file_id glob → (3) `_dlt_load_id` scan (L42). Naive single-layer returns 0 cho filesystem destination vì dlt LoadInfo không expose row counts ở phiên bản hiện tại
- [ ] Digest window: business-TZ calendar day (`yesterday 0h-24h ICT`), KHÔNG rolling 24h (L43). Rolling 24h straddles 2 ngày → stakeholder đọc sai
- [ ] Dashboard SQL handle "asset chưa từng chạy" — không cross join gây missing rows (L37). Test với fresh environment
- [ ] Runner entry point MUST `return run_pipeline(...)` — thiếu `return` = silent skip, pipeline không chạy nhưng không báo lỗi (L36)
- [ ] `asset_check_executions` cleanup trong purge job (L55) — thiếu = table tích lũy không giới hạn
- [ ] Health checks job: `in_process_executor`, exclude dbt tests, mutual-exclude với ingestion jobs (L40, L65, Lesson 11 dagster-patterns)
- [ ] Trust pyramid: Tier 1 (got it? — freshness/not-empty) + Tier 2 (reasonable? — row-trend/cursor-stall) + Tier 3 (matches? — recon) + Tier 4 (correct? — KPI closure)

---

## ⭐ Production Checklist (12 items)

**Preserve verbatim từ `../references/ingestion-health-digest.md` "Production checklist".**
Bắt buộc verify TẤT CẢ 12 items trước khi enable digest schedule production:

1. Health DB path resolves correctly in **both** host dev (`.env.local`) and container (`.env.docker`). Mis-matched paths = silent empty digest.
2. Health DB is included in daily backup rotation. The 2026-04-22 incident recovered from `app_data/backups/YYYYMMDD-HHMMSS/…/ingestion_health.duckdb` — do not skip this.
3. `record_run` is wrapped in try/except at every call site. Grep `record_run` and verify.
4. `extract_rows_written` runs with `DBT_DATA_LAKE_PATH` set. Without it, Layer 2/3 silently return None → persistent 0 rows.
5. Digest schedule is AFTER recon/KPI-closure. Typical ordering: recon 04:30 → KPI 04:45 → digest 06:00, all in business TZ.
6. Digest wrapped in try/except around `send_*_card`. Log, don't raise.
7. Dry-run via `DIGEST_DRY_RUN=1` verified before enabling schedule.
8. Asset registry includes ALL known assets with correct `asset_type` (cursor / batch / file_drop) and `unit_label`.
9. SLA hours chosen per pipeline cadence. 12h works for daily batches; cursor pipelines may want 6h or lower.
10. Zero-streak detection has an N >= 2 threshold. Lower than that = noisy alerts during quiet business hours.
11. Backfill script exists (one-shot) with composite-PK UPDATE. See `../references/ingestion-health-digest.md` "Backfill strategy".
12. Every UPDATE/DELETE on `ingestion_runs` has BOTH `asset_key` and `run_id` in WHERE. Code review rule.

---

## Mental model & patterns

### 4-tier Trust Pyramid

```
Tier 4: KPI closure         — Revenue match Sapo ↔ warehouse (drift_pct < 0.1%)
Tier 3: Recon               — Row count source API ↔ warehouse table
Tier 2: Row trend           — Volume vs 7-day median; zero-streak cursor detection
Tier 1: Freshness/not-empty — last_ok < SLA_HOURS; latest run rows_written > 0
```

Higher tier = more expensive + delayed. Tiers are additive — green at Tier 1 doesn't exclude yellow at Tier 3.

### Asset-type-aware messaging

| Type | Cadence | `rows = 0` means | Message template |
|------|---------|------------------|------------------|
| `cursor` | Every few min | Source had nothing new — **normal** | `Không có {unit} mới (đã chạy {runs} lần hôm qua)` |
| `batch` | Daily | Either no new rows OR job skipped | `Batch hôm qua: không có {unit} mới` |
| `file_drop` | On file arrival | Upstream file unchanged | `File nguồn chưa thay đổi` |

Do NOT reuse a single "0 rows" template for all types. Wrong messaging produces alert fatigue.

### Graceful degrade — `RECON_LIVE_API`

When live API unavailable (rate-limit, maintenance window), recon can fall back to last known count with a staleness label rather than erroring out. Set `RECON_LIVE_API=false` to skip API call; report `gray` status (not `red`) with note "live API skipped".

### Composite-PK recovery playbook

If corruption detected (rows_written mismatch across siblings):
1. Stop all write paths (pause Dagster ingestion jobs).
2. `ATTACH 'backup.duckdb' AS bak (READ_ONLY)`.
3. `UPDATE live SET rows_written = bak.rows_written FROM bak WHERE live.asset_key = bak.asset_key AND live.run_id = bak.run_id`.
4. Verify `COALESCE(live, -1) != COALESCE(bak, -1)` = 0.
5. Fix the bug. Re-run backfill.

---

## Templates

| Template | Khi nào dùng |
|----------|-------------|
| `../templates/trust/ingestion-health-recorder-template.py` | Ghi `record_run` sau mỗi ingestion asset. Includes DDL + composite PK + try/finally pattern |
| `../templates/trust/dlt-row-count-extractor-template.py` | 3-layer fallback extraction từ dlt LoadInfo. Copy vào asset trước khi call `record_run` |
| `../templates/trust/ingestion-health-digest-template.py` | Morning digest op: window query + classify + send card. Customize `ASSET_REGISTRY` và `SLA_HOURS` |
| `../templates/trust/backfill-health-rows-written-template.py` | One-shot script để backfill rows_written sau khi fix extractor bug. Composite-PK-safe UPDATE |

---

## Supporting scripts

Xem `../references/supporting-scripts.md` "Khi Nào Gọi Script Nào" để tra bảng tình huống → script chain.

Scripts liên quan trực tiếp đến TRUST:
- `scripts/maintenance/backfill_ingestion_health_rows_written.py` — Recovery script khi extractor fix, cần backfill rows cũ
- `scripts/testing/verify_hops_readonly.py` — Smoke test row counts qua các hops (INGEST → MODEL → SERVE đều nhất quán)

---

## Debug recipes

Xem `../references/troubleshooting.md` section "Health Monitoring DB" — symptom → cause → fix cụ thể cho:
- Health DB file not found / path mismatch
- `rows_written` consistently 0 despite data flowing
- Digest sends but all sources show gray
- SQLite lock conflict during digest read

---

## Lessons cross-reference

| ID | Summary | Source |
|----|---------|--------|
| L36 | Runner entry point MUST `return run_pipeline(...)` — không `return` = silent skip | `../references/lessons-learned.md` |
| L37 | Dashboard SQL handle "asset chưa từng chạy" — tránh cross join | `../references/lessons-learned.md` |
| L40 | Health checks job exclude dbt tests + mutual-exclude với ingestion | `../references/lessons-learned.md` |
| L41 | datetime serialization: ISO string + `or 0.0` cho MetadataValue.float | `../references/lessons-learned.md` |
| L42 | Row count 3-layer fallback: metrics → file_id glob → `_dlt_load_id` scan | `../references/lessons-learned.md` |
| L43 | Digest window: business-TZ calendar day, KHÔNG rolling 24h | `../references/lessons-learned.md` |
| L44 | Composite PK `(asset_key, run_id)` — filter BOTH trong mọi UPDATE/DELETE | `../references/lessons-learned.md` |
| L55 | `asset_check_executions` cleanup trong purge | `../references/lessons-learned.md` |
| L66 | `MetadataValue.float()` int trap: `or 0` returns `int(0)` → dùng `or 0.0` | `../references/lessons-learned.md` |
| dagster-Lesson-11 | Health checks job: `in_process_executor` + AssetSelection exclude dbt tests | `../references/dagster-patterns.md` |
| dbt-Lesson-11 | (Related: dbt test anatomy relevant to exclusion logic) | `../references/dbt-patterns.md` |
| Full doc | Canonical TRUST reference: architecture, schema, component breakdown, post-mortem index | `../references/ingestion-health-digest.md` |

---

## Common pitfalls

| Symptom | Cause | Fix |
|---------|-------|-----|
| Digest shows gray for all assets | `INGESTION_HEALTH_DB` path mismatch host vs container | Verify path resolves same in `.env.local` và `.env.docker` |
| `rows_written` = 0 persistently | dlt LoadInfo không expose row counts (filesystem destination) | Deploy 3-layer extractor (L42) + backfill script |
| Window mismatch vs stakeholder expectation | Rolling 24h vs calendar day | Switch to `AT TIME ZONE` calendar day (L43) |
| 182-row data corruption event | UPDATE filter chỉ `run_id`, bỏ `asset_key` | Enforce composite PK WHERE clause, code review rule (L44) |
| Digest fires before KPI/recon completes | Schedule order wrong | Reorder: recon 04:30 → KPI 04:45 → digest 06:00 (item 5 của Production Checklist) |
| `ChildProcessCrashException` trên health jobs | Per-step subprocess overhead (OOM) | Dùng `in_process_executor` cho lightweight read-only jobs (L65) |

---

## When this group interacts with others

- **INGEST → TRUST**: every ingestion asset must call `record_run()` in `try/finally`. TRUST depends on INGEST for raw data.
- **OPS → TRUST**: OPS purge job phải cleanup `asset_check_executions` (L55). OPS scheduler phải start digest schedule explicitly.
- **MODEL/SERVE → TRUST**: Recon (Tier 3) queries mart/serving tables to compare against source API. TRUST reads from serving DB (read-only, no lock).
- **TRUST → stakeholder**: Digest fires 06:00 ICT, after all batch/recon jobs complete.

---

## Backfill strategy

Khi deploy row-count extractor fix, existing rows vẫn giữ giá trị cũ (sai). Digest tiếp theo vẫn sai **cho đến khi mỗi asset chạy lại với code đã fix**. Với daily batch = phải chờ 1 ngày — không acceptable cho business-facing dashboard.

**Solution:** replay stored `metadata_json.load_info` qua extractor đã fix, UPDATE in-place:
1. Iterate `ingestion_runs WHERE status IN ('success', 'skipped') AND (rows_written IS NULL OR rows_written = 0)`
2. `n = extract_rows_written(metadata_json.load_info)` với extractor mới
3. If `n > 0`: `UPDATE ... WHERE asset_key = ? AND run_id = ?` (composite PK — critical)
4. Otherwise skip (đã đúng hoặc không có data)

Idempotent — re-run safe. Dùng `--dry-run` để preview trước.

**Template:** `../templates/trust/backfill-health-rows-written-template.py`
**Full doc:** `../references/ingestion-health-digest.md` "Backfill strategy" section

---

## Health DB Schema (quick ref)

```sql
CREATE TABLE IF NOT EXISTS ingestion_runs (
    asset_key       VARCHAR NOT NULL,   -- "sapo/sapo_orders_batch_asset"
    run_id          VARCHAR NOT NULL,   -- Dagster run UUID (shared across assets in same job)
    run_started_at  TIMESTAMPTZ NOT NULL,
    run_ended_at    TIMESTAMPTZ,
    duration_s      DOUBLE,
    status          VARCHAR NOT NULL,   -- success | skipped | failed | partial
    rows_fetched    BIGINT,
    rows_written    BIGINT,
    rows_new        BIGINT,
    rows_updated    BIGINT,
    cursor_before   VARCHAR,
    cursor_after    VARCHAR,
    schema_hash     VARCHAR,
    file_sha256     VARCHAR,
    file_mtime      TIMESTAMPTZ,
    metadata_json   JSON,               -- dlt LoadInfo, drift_pct, etc.
    PRIMARY KEY (asset_key, run_id)
);
```

Path resolution priority:
1. `INGESTION_HEALTH_DB` env var (explicit full path)
2. `DBT_DATA_LAKE_PATH` + `/monitoring/ingestion_health.duckdb`
3. **Fail loud** — no hardcoded fallback (diverges between host and container)

---

## Post-mortem index

| Date | Incident | Lesson |
|------|----------|--------|
| 2026-04-15 | Design: need per-source digest | `../references/lessons-learned.md` L18 |
| 2026-04-22 AM | `rows_written=0` ~6 weeks (dlt LoadInfo no row counts) | L42 |
| 2026-04-22 AM | Rolling 24h window vs calendar day stakeholder expectation | L43 |
| 2026-04-22 AM | Backfill UPDATE on `run_id` only → 182 corrupted rows | L44 |

Full post-mortem detail: `../references/ingestion-health-digest.md` "Post-mortem index" section.

---

## Related cross-cutting concerns

- `cross-cutting.md#sqlite-wal-safety` — health DB là SQLite-based; WAL safety quan trọng khi purge/cleanup chạy
- `cross-cutting.md#composite-pk-update-trap` — canonical home cho `(asset_key, run_id)` rule; TRUST là nhóm bị ảnh hưởng trực tiếp nhất
