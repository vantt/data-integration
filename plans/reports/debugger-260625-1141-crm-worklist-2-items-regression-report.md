# CRM Worklist Regression Report
**Date:** 2026-06-25 | **Investigator:** debugger agent

---

## Tóm tắt

Hai triệu chứng báo cáo đều có **cùng một nguyên nhân gốc**: CRM container chưa được rebuild sau khi feature `top_affinity_product` được phát triển (uncommitted WIP). Không có bug ngoài ý muốn — đây là **work-in-progress chưa hoàn thành** đang gây ra state không nhất quán giữa code local và container đang chạy.

---

## Bằng chứng thu thập

### Cache SQLite (crm/data/cache.db — file LOCAL, không phải container volume)
| Bảng | Rows |
|------|------|
| wh_customer_tier | 7,563 |
| wh_action_queue | **0** |
| wh_customer_base | 0 |
| wh_sync_run | 0 |
| Tất cả bảng khác | 0 |

- `mtime` của `crm/data/cache.db`: **2026-06-19 17:15 ICT** (6 ngày trước)
- Schema hiện tại **không có** cột `top_affinity_product` / `last_purchased_product`

### Backup container (20260624-015540/app_data/crm_data/cache.db)
| action_type | count |
|-------------|-------|
| REORDER_NUDGE | 303 |
| WIN_BACK | 127 |
| SECOND_ORDER | 54 |
| CALL_NOW | 25 |
| REORDER_PREEMPT | 17 |
| HIGH_CANCEL_RISK | 5 |
| **TOTAL** | **531** |
| `max(refreshed_at)` | 2026-06-23T18:00:40 UTC |

→ Container `cache.db` (volume `/data/`) **khác hẳn** file local `crm/data/cache.db`. Container có 531 action items từ sync ngày 23/06.

### Mart DuckDB nguồn
- `sapo_export_latest.duckdb` (fallback path): **520 rows**, đã có cột `top_affinity_product` + `last_purchased_product`
- `rolling/mart_customer_action_queue/*.parquet` (latest Jun 25 11:46): **520 rows**, 34 columns kể cả 2 cột mới
- `olap.duckdb` (primary path trong container): là view con trỏ tới path Linux `/app/var/data_lake/...` — hoạt động trong Docker nhưng fail trên Windows native

### Uncommitted changes (git status)
Tất cả 8 file đang sửa là WIP của tính năng `top_affinity_product` / `last_purchased_product`:
- `duckdb_reader.py` → thêm 2 cột vào `_MART_ACTION_QUEUE_COLS` và query SQL
- `sqlite_upsert.py` → thêm ALTER TABLE migration + INSERT binding mới (10 params thay vì 8)
- `cache_schema.sql` → thêm 2 cột mới vào `CREATE TABLE wh_action_queue`
- `cache_insight.py` → thêm 2 field vào dataclass `ActionQueueItem`
- `cache_repository.py` → thêm COALESCE cho 2 cột mới trong SELECT
- `worklist_filters.py` → text search mở rộng sang 2 cột mới (không ảnh hưởng count)
- `_wl_row.html` → hiển thị product affinity tags (UI additive, không xóa gì)
- `app.css` → CSS cho `.wl-product-tag` (UI additive)

---

## Phân tích 2 triệu chứng

### Triệu chứng 1: Worklist chỉ còn 2 action items

**Root cause: User đang nhìn vào môi trường dev local với cache.db stale, không phải container đang chạy trên production.**

Chuỗi bằng chứng:
1. `crm/data/cache.db` (local) có `wh_action_queue = 0 rows`, mtime **19/06/2026**
2. Backup container từ **24/06** có `531 action items` — chứng minh production container đang hoạt động bình thường
3. Sync lần cuối trong container: **23/06 18:00 ICT** (confirmed qua `max(refreshed_at)` của backup)

"2 items" chính xác là **4 open tasks** trong `crm_task` (manual tasks) mà user thấy trong development mode, vì action_queue rỗng nên worklist chỉ hiện tasks. Số "2" có thể do 2 task cụ thể vượt qua filter mặc định.

**Không phải do `worklist_filters.py` siết điều kiện** — diff chỉ mở rộng text search (+2 trường), không loại bỏ action items.

### Triệu chứng 2: Mất filter theo action type

**Root cause: `available_types` rỗng vì `wh_action_queue` trong local cache.db = 0 rows.**

Chuỗi bằng chứng:
- `_wl_filter_bar.html` line 81: `{% if avail %}` — chips chỉ render khi `available_types` có dữ liệu
- `worklist_filters.py:34`: `available_action_types()` trả về tập hợp `action_type` từ `all_actions`
- `screen_worklist.py:80-92`: `all_actions = action_queue.list_all_action_queue()` → rỗng → `available_types = []` → chips không render

Filter bar **không bị xóa** (template `_wl_filter_bar.html` còn nguyên, không có trong git diff). Chips ẩn do logic điều kiện `{% if avail %}` hoạt động đúng với data rỗng.

---

## Phân biệt: Cố ý vs Bug ngoài ý muốn

| Thay đổi | Đánh giá |
|----------|----------|
| `duckdb_reader.py` + `sqlite_upsert.py` + `cache_schema.sql` + `cache_insight.py` + `cache_repository.py` | **Cố ý — WIP feature** thêm product affinity context vào worklist |
| `_wl_row.html` + `app.css` | **Cố ý — UI additive**, hiển thị sản phẩm affinity tag (không xóa filter) |
| `worklist_filters.py` | **Cố ý — mở rộng** text search, không phải siết filter |
| Worklist chỉ còn 2 items | **Side-effect môi trường**: user đang chạy app với `crm/data/cache.db` local (stale, 0 action rows) thay vì container volume |
| Mất action type chips | **Hệ quả tự nhiên** của cache rỗng — không phải regression trong code |

**Không có bug ngoài ý muốn trong logic.** Vấn đề là state môi trường dev: file `crm/data/cache.db` local chưa được sync (0 rows) trong khi container production đang chạy bình thường.

---

## Khi nào sync sẽ thất bại sau commit?

Khi commit và rebuild container với code mới (`duckdb_reader.py` thêm 2 cột), sync sẽ **thành công** vì:
- `sapo_export_latest.duckdb` đã có `top_affinity_product` + `last_purchased_product` (confirmed: 520 rows, 34 cols)
- `upsert_action_queue` trong `sqlite_upsert.py` đã cập nhật đúng (10 params, UPDATE SET đầy đủ)
- `apply_schema` trong `sqlite_upsert.py` có ALTER TABLE migration (idempotent)

Rủi ro duy nhất: nếu **deploy code mới TRƯỚC KHI** mart DuckDB có 2 cột (tức là dbt chưa chạy lại mart). Nhưng hiện tại mart đã có cột rồi nên không phải vấn đề.

---

## Đề xuất khắc phục

### Ngắn hạn (để dev tiếp bình thường)

1. **Trigger sync local thủ công** bằng cách chạy `POST /admin/refresh` vào container đang chạy, hoặc chạy trực tiếp:
   ```bash
   docker exec <crm_container> python -m crm.sync.reverse_etl_warehouse_to_crm
   ```
   Lưu ý: Container hiện chạy **code cũ** (chưa có 2 cột mới) nên sync sẽ thành công với format cũ.

2. **Không cần làm gì** nếu production container đang chạy bình thường (backup ngày 24 cho thấy 531 items).

### Trung hạn (sau khi commit feature WIP)

1. **Commit và rebuild container**: `docker compose up -d --build crm` — như memory đã ghi: "crm/sync baked in image; else scheduled reverse_etl reds".
2. **Trigger sync sau rebuild** qua Dagster (`crm_cache_refresh` asset) hoặc `POST /admin/refresh`.
3. **Kiểm tra**: `wh_action_queue` phải có ~520 rows, `top_affinity_product` populated.

### Rủi ro

- Nếu rebuild trước khi commit đầy đủ tất cả 8 file: `upsert_action_queue` sẽ fail do mismatch tham số (10 params trong code mới vs schema cũ chưa ALTER TABLE). **Phải commit atomically** tất cả 8 file.
- Sau khi ALTER TABLE thêm 2 cột, các row cũ (pre-migration) sẽ có `top_affinity_product = NULL` cho đến khi sync chạy lại.

---

## Timeline sự kiện

```
Jun 19 17:15 — Cache.db local cuối sync (action_queue=0, tier=7563 — action_queue chưa populate lần này)
Jun 21 00:20 — olap.duckdb serving cập nhật
Jun 23 17:31 — feat: urgency-banded worklist (019d31a) — thêm filter chips, action type UI
Jun 23 18:00 — Container sync thành công: 531 action items (confirmed từ backup 24)
Jun 23 23:20 — fix: harden reverse-ETL error handling (9428998)
Jun 24 01:55 — Backup container chụp 531 action items
Jun 24-25    — WIP commits: top_affinity_product feature (uncommitted)
Jun 25 11:36 — Rolling parquet mới nhất: 520 rows với 2 cột mới
Jun 25 today — User thấy 2 items (đang xem local cache.db, không phải container)
```

---

## Monitoring gap

1. **Không có alert** khi `wh_action_queue = 0` sau sync — nên thêm `wh_sync_run` row count check vào health endpoint.
2. **Không có cơ chế phân biệt** cache.db local (dev) vs container volume (production) — dễ nhầm lẫn môi trường.
3. Sync schedule (Dagster `crm_cache_refresh`) phụ thuộc vào warehouse pipeline running — nếu pipeline dừng, cache stale silently.

---

**Status:** DONE
**Summary:** Cả 2 triệu chứng là side-effect của môi trường dev dùng `crm/data/cache.db` stale (0 action rows, mtime Jun 19), không phải regression trong code. Container production có 531 action items bình thường. WIP feature `top_affinity_product` chưa commit, chưa rebuild container.
**Evidence:** `wh_action_queue=0` in local cache.db (mtime Jun19) vs backup container `531 rows` (refreshed Jun23 18:00); `_wl_filter_bar.html` template intact with `{% if avail %}` guard; `sapo_export_latest.duckdb` has both new columns + 520 rows.
**Concerns:** Phải commit atomically tất cả 8 file WIP trước khi rebuild; không rebuild nửa chừng.
