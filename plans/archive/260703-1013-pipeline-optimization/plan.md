# Pipeline Optimization: Index, Partition & Dedup
**Status:** ✅ CLOSED 2026-07-03  
**Date:** 2026-07-03 | **Branch:** feature/task-detail-cockpit-backend  
**Audit source:** `plans/reports/pipeline-optimization-audit-260703-1000-index-partition-dedup-report.md`

---

## Status

| Phase | Title | Status | Ghi chú |
|-------|-------|--------|---------|
| 1 | Quick wins: indexes + metric lookback + dedup tiebreaker + unique test | ✅ done | commit 38d63d15 |
| 2 | Intermediate model partitioning | ❌ closed | Over-engineering: 24KB + 1.1MB, 1 row group, zero benefit |
| 3 | Rolling parquet retention | ✅ đã tồn tại | `refresh_rolling.py` ROLLING_KEEP_VERSIONS=3 |
| 4 | Raw data consolidation | 🔵 deferred | Trigger: history_log > 2000 files (~Q1 2027) |

---

## Acceptance Criteria

- [x] CRM queries giảm latency qua 3 indexes mới (migration 0034)
- [x] `int_customer_metrics` không bỏ sót records do clock-skew (lookback 3 ngày)
- [x] Order dedup deterministic theo `_dlt_load_id` khi `modified_on` tie
- [x] `stg_sapo_v2_orders.order_id` có unique test (pre-condition cho consolidation)
- [x] Rolling parquet retention hoạt động (ROLLING_KEEP_VERSIONS=3)
- [x] Design document cho raw consolidation (`spike-raw-consolidation-findings.md`)
- [n/a] Partition pruning trên int_* — closed, volume quá nhỏ để có ROI

---

## Discoveries

### Phase 3 — Đã tồn tại
`scripts/provisioning/refresh_rolling.py` đã implement rolling GC. Tune qua `ROLLING_KEEP_VERSIONS` env var.

### Phase 2 — Closed (over-engineering)
- `int_shopee_order_fees` = **24 KB** per file → 1 row group → partition pruning không thể skip gì
- `int_misa_sales_lines` = **1.1 MB** per file → ~3K-8K rows → 1 row group
- Serving view dùng `hive_partitioning=0` + `max(filename)` pattern — incompatible với hive partitioning
- Tất cả macro trả về file path (không phải directory) — incompatible với `COPY ... TO (PARTITION_BY ...)`
- Reopen khi `int_misa_sales_lines` > 100MB (vài năm nữa)

### Phase 4 — Deferred
- Webhook data dùng Delta Lake format → compact cần `OPTIMIZE`/`VACUUM`, không phải plain merge
- Normal incremental run không đọc file cũ (cursor-based) → 978 history_log files chỉ ảnh hưởng `--full-refresh` (rare)
- Reopen khi history_log files > 2000 hoặc full-refresh > 5 phút

---

## Phase Files

- [Phase 1: Quick Wins](phase-01-quick-wins.md) ✅
- [Phase 2: Intermediate Partitioning](phase-02-intermediate-partitioning.md) ❌ closed
- ~~Phase 3: Rolling Retention~~ — đã tồn tại, xem `scripts/provisioning/refresh_rolling.py`
- [Phase 4: Raw Consolidation](phase-04-raw-consolidation-spike.md) 🔵 deferred
