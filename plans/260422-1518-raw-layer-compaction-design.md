# Raw Layer Compaction — Design Note

**Status:** Proposal (chưa implement)
**Created:** 2026-04-22
**Context:** Daily ingest kéo cả tháng data → raw trùng lặp lớn. Cần cơ chế consolidate + dedup định kỳ để raw gọn, tiết kiệm storage, giảm cost dbt dedup. Chấp nhận duplication nhỏ ở hot zone.

---

## 1. Vấn đề

- Nhiều nguồn (Sapo, Shopee, ...) ingest **rolling window theo tháng mỗi ngày** → mỗi record xuất hiện ~30 lần trong raw.
- dbt dedup trên read → đúng data nhưng phải scan toàn bộ duplicates mỗi lần build.
- Storage parquet phình theo thời gian, cost DuckDB scan tăng.
- **Risk đặc biệt Sapo:** history_log truncation ở nguồn → cần giữ raw lâu đủ để catch late edits **trước khi Sapo quên**.

## 2. Đề xuất: Tiered Hot / Warm / Cold

Binary hot/cold bỏ phí thông tin. Tiered giảm granularity dần theo tuổi:

| Tier | Age | Grain | Mục đích |
|------|-----|-------|----------|
| Hot | 0–14 ngày | Daily snapshots (nguyên) | Debug gần, catch mutations |
| Warm | 14–45 ngày | Weekly consolidated (1 row/natural_key/tuần) | Giữ SCD-lite trong close window |
| Cold | 45+ ngày | Monthly consolidated (1 row/natural_key/tháng) | Final dedup, bảo tàng history |

**Per-source override:** Sapo hot zone = 30 ngày (không phải 14) vì truncation risk.

## 3. Cơ sở grace period

`grace_period ≥ max(mutation_window, close_cycle) + buffer`
Với Sapo thêm constraint: `grace_period < source_truncation_window`.

Các mốc giải thích:
- **14 ngày hot** = phủ 99% mutation window (ship, return sớm) của e-commerce order.
- **45 ngày warm→cold** = M-close (10) + return window (30) + buffer (5).
- **Sapo hot 30 ngày** = buffer lớn hơn vì nguồn có thể xóa history bất kỳ lúc nào.

## 4. Quyết định thiết kế cần chốt khi implement

1. **Natural key dedup**
   `(source, entity_type, entity_id)` — giữ row có `source_updated_at` mới nhất, tiebreaker `ingestion_ts`.
   KHÔNG dùng `_dlt_id` (sẽ không dedup gì cả).

2. **Watermark tracking**
   Bảng `compaction_log(source, period, tier, compacted_at, rows_before, rows_after, ratio)`.
   Không dựa Dagster materialization metadata → cần query/rebuild dễ.

3. **Idempotency & rollback**
   Compact → temp file → atomic rename → **giữ source files thêm 7 ngày trước khi xóa**.
   Belt-and-suspenders: nếu compaction sai, rebuild từ raw được.

4. **Re-compaction overlap (late-arriving data)**
   Khi record cũ có snapshot mới ở hot: cold zone stale. Mỗi lần compact tháng M phải `JOIN cold[M] UNION hot-rows-for-M → dedup lại`, không compact chỉ-từ-hot.

5. **Anomaly guardrail**
   `reduction_ratio < 10%` hoặc `> 95%` → alert, KHÔNG auto-delete source. Có thể schema/key đổi.

6. **Asset shape trong Dagster**
   **Partitioned asset riêng** (weekly partition cho warm, monthly cho cold), KHÔNG step trong ingestion job.
   - Rerun độc lập
   - Không block daily ingest
   - Lineage rõ ràng trên UI

## 5. Rủi ro phải check trước khi bật

- **Schema drift** giữa các tháng → monthly compact fail hoặc mất cột. Cần `UNION BY NAME` + NULL fill, hoặc schema registry.
- **Downstream hard-code path** `raw/sapo/2026-03-15/*.parquet` → vỡ sau compact. Grep kỹ codebase trước khi bật.
- **DuckDB view binder error** (xem memory `duckdb_view_rebuild`) → rebuild `bootstrap_serving_views.py` sau compaction nếu có view trỏ trực tiếp vào raw files.

## 6. Trade-off chấp nhận

- **Mất daily-level replay ở warm/cold:** không xem lại được "API ngày X trả gì cho record Y ở tháng cũ". Nếu business logic + source ổn định → chấp nhận được.
- **Compaction job = compute cost mới** (rewrite parquet) — nhưng chỉ tuần/tháng 1 lần, rẻ hơn nhiều lần dbt full-refresh scan daily duplicates.

## 7. Alternatives đã cân nhắc (và vì sao không chọn)

| Alt | Tại sao không chọn |
|-----|--------------------|
| Retention-only (giữ N snapshots gần, xóa cũ) | Thô, mất history |
| SCD2 tại raw (chỉ ghi khi đổi) | Phức tạp hóa dlt, phải hash-compare mỗi ingest |
| dlt `merge` write disposition | Mất snapshot history luôn, không replay được gì |

## 8. Open questions (chốt trước khi implement)

1. **POC trên nguồn nào trước?** Shopee (ít nhạy cảm) hay Sapo (lợi ích lớn nhất do truncation)?
2. **Audit trail:** xóa thẳng daily snapshots sau compact, hay giữ compressed archive ở cold storage?
3. **Tiered 3 lớp vs binary hot/cold (14/45):** overkill cho giai đoạn đầu không?
4. **Storage target:** compaction viết về đâu — đè chính raw parquet, hay ra layer `raw_compacted/` song song?
5. **Schema registry:** cần build trước, hay ad-hoc xử lý drift khi gặp?
6. **Trigger:** cron-based (weekly/monthly) hay event-based (sau khi close kỳ)?

## 9. Next steps khi pick up lại

1. Trả lời 6 open questions ở section 8.
2. Scout codebase: tìm mọi chỗ đọc raw parquet trực tiếp (grep path pattern).
3. Design `compaction_log` schema + Dagster asset signatures.
4. POC 1 nguồn (Shopee hoặc Sapo) trên 1 tháng dữ liệu, đo reduction_ratio + verify dbt output không đổi.
5. Rollout per-source với monitoring.

## 10. Liên quan

- Memory: `project_sapo_history_log_truncation.md` — constraint grace period cho Sapo.
- Memory: `feedback_duckdb_view_rebuild.md` — phải rebuild view sau khi đụng raw.
- Memory: `project_timezone_architecture.md` — TIMESTAMPTZ cho `source_updated_at` dedup ordering.
