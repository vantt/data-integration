# Plan: Sapo Orders Batch Re-ingestion

**Goal:** Re-ingest toàn bộ orders từ Sapo API qua `batch_sync` để nạp lại các orders bị thiếu (đặc biệt Shopee). So sánh before/after.

**Status:** Ready to execute
(updated 2026-06-24: untouched by 260623 audit work; pre-flight Dagster asset fix still required before running)

---

## Baseline (2026-06-12, trước khi re-ingest)

| Nguồn | Distinct orders (raw lake) |
|---|---|
| channel=None (walk-in/direct) | 2,801 |
| Shopee | **559** |
| POS | 45 |
| Sapoweb | 23 |
| sapo_social | 19 |
| Lazada | 9 |
| **TỔNG** | **3,456** |

**Shopee gap đáng ngờ:**

| ingest_method | Shopee orders | Khoảng thời gian |
|---|---|---|
| batch_sync | 254 | 2023-04-25 → 2026-06-11 |
| history_log | 556 | 2025-12-29 → 2026-06-11 |
| text | 21 | 2026-04-06 → 2026-04-15 |
| **Distinct (cross-method)** | **559** | — |

batch_sync thiếu toàn bộ Shopee trước 2023. Re-ingest từ đầu để Sapo API trả lại đầy đủ.

---

## Pre-flight: Fix Dagster asset (cần làm trước)

`pipeline_batch_fullrefresh_job` hiện pass tag `full_refresh=true` → asset gọi `--full-refresh` → **bị block bởi guardrail mới**.

Cần sửa `orchestration/assets/sapo_assets.py` line 54:

```python
# Trước (bị block):
argv = ["--full-refresh"] if is_full_refresh else []

# Sau (dùng --reset-cursor — safe):
argv = ["--reset-cursor"] if is_full_refresh else []
```

---

## Cơ chế chạy không treo hệ thống

### Tại sao không treo
- Re-ingest chỉ **write parquet files** — không lock `sapo_warehouse.duckdb`
- Tốc độ giới hạn sẵn: `request_delay=0.5s/request`
- Hệ thống có thể chờ → nâng lên `1.0s` để không tranh API quota

### Safe window
| Thời gian ICT | Trạng thái hệ thống |
|---|---|
| 00:00–03:00 | Incremental schedule chạy mỗi 10 phút |
| **03:00–05:00** | ⚠️ Nightly batch (orders + dbt) — TRÁNH |
| 05:00–23:59 | ✅ **An toàn** — chạy re-ingest ở đây |

### Cách chạy (không dùng Dagster scheduler)

Re-ingest chạy trực tiếp qua Docker exec, **ngoài Dagster**, để tránh overlap với `dbt_rw=1` concurrency tag:

```bash
# Bước 1: Pause incremental schedule trong Dagster UI
# (hoặc chạy lúc sau 08:00 khi incremental đã drain)

# Bước 2: Reset cursor + re-ingest (trong container)
docker exec -it data_platform bash -c "
  cd /app/ingestion &&
  SAPO_REQUEST_DELAY=1.0 python run_orders_batch.py --reset-cursor
"

# Bước 3: Resume incremental schedule sau khi ingest xong
```

> Ước tính thời gian: ~3,500 orders × 100/page = 35 pages × 1s delay ≈ **35–60 phút** (tuỳ Sapo API response time).

---

## Steps

### Step 1 — Fix Dagster asset
- [ ] Sửa `orchestration/assets/sapo_assets.py`: `--full-refresh` → `--reset-cursor`
- [ ] Commit

### Step 2 — Snapshot baseline
- [ ] Chạy `check_sapo_raw_orders.py` (hoặc query bên dưới) để lưu số liệu pre-ingest
- [ ] Ghi vào file `plans/260612-1042-orders-batch-reingestion/baseline.md`

```bash
docker exec data_platform python3 -c "
import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')
con = duckdb.connect('/app/var/data_lake/sapo_warehouse.duckdb', read_only=True)
# nếu bị lock thì dùng parquet trực tiếp
"
```

### Step 3 — Re-ingest (safe window: sau 08:00 ICT)

```bash
docker exec -it data_platform bash -c "
  cd /app/ingestion &&
  python run_orders_batch.py --reset-cursor
"
```

Monitor output: theo dõi `📄 Page X: Y/100 new` — nếu thấy `Old stream: 500/500` thì đã đủ safety buffer.

### Step 4 — Đếm lại raw lake

```bash
docker exec data_platform python3 << 'EOF'
import duckdb, sys
sys.stdout.reconfigure(encoding='utf-8')
con = duckdb.connect(':memory:')
r = con.execute("""
SELECT
    json_extract_string(payload, '$.channel') AS channel,
    COUNT(DISTINCT entity_id) AS orders
FROM read_parquet([
    '/app/var/data_lake/sapo_raw/order/ingest_method=batch_sync/**/*.parquet',
    '/app/var/data_lake/sapo_raw/order/ingest_method=history_log/**/*.parquet',
    '/app/var/data_lake/sapo_raw/order/ingest_method=text/**/*.parquet'
], hive_partitioning=true, union_by_name=true)
GROUP BY 1 ORDER BY 2 DESC
""").fetchall()
for row in r: print(row)
EOF
```

### Step 5 — Chạy dbt để rebuild marts

```bash
# Chờ nightly batch tiếp theo (03:00 ICT tự chạy), HOẶC trigger thủ công:
docker exec data_platform bash -c "
  cd /app/transformation &&
  dbt run --select src_sapo_orders_v2+ --target prod
"
```

### Step 6 — So sánh before/after

So sánh fact_orders sau dbt với baseline:
- Total unique orders
- Shopee orders
- Orders by year

---

## Success Criteria

| Metric | Pre | Post (target) |
|---|---|---|
| Total distinct orders | 3,456 | ≥ 3,456 |
| Shopee orders | 559 | > 559 (nếu API trả thêm) |
| Shopee batch_sync coverage | 2023+ only | 2021+ nếu Sapo còn giữ |
| Không mất data cũ | — | history_log + text vẫn nguyên |

---

## Unresolved Questions

1. Sapo API có còn giữ Shopee orders từ 2021–2022 hay đã xoá? Re-ingest sẽ trả lời câu này.
2. `channel=None` (2,801 orders) là gì — có phải do Sapo không map channel cho đơn direct/web không?
3. Nếu re-ingest không tăng được Shopee count → gap là do Sapo API không còn trả về data cũ → cần tìm nguồn khác (Shopee income file drop).
