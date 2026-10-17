# Deploy cơ chế pack phase 1–6 (D1 + D2) — 15/10/2026 10:34

## Kết quả

Phase 1–6 đã lên prod và chạy xanh. `main` fast-forward `8eb9920f` → `b6bb06b6` theo runbook
§ Refactor deploys; user duyệt deploy D1 + D2 chung một lần dừng (15/10 ~10:29). `main` đã push.

| Mốc | Giờ (ICT) |
|---|---|
| Snapshot instigator 26/26, không run đang chạy | 10:34 |
| Stop `data_platform` (sau tick realtime 10:33) | 10:34:05 |
| `git merge --ff-only b6bb06b6` | 10:34 |
| Start `data_platform` | 10:34:16 |

Rollback point `8eb9920f`; dải revert nếu cần `8eb9920f..b6bb06b6`. Sau rollback còn lại (vô hại):
bảng `int_sku_sales_monthly` và 3 seed `*__default` trong warehouse.

## Nội dung

| Phase | Commit | Thay đổi |
|---|---|---|
| 2 | `a4082fab` | Công tắc pack: `enabled_packs`, `+enabled` theo thư mục, `pack_ref`/`pack_contracts`, test `pack_contract`, rule `module-config` |
| 3 | `3c5419d6` | 4 hook lõi (`dim_customers`, `dim_staff`, `dim_sku_alias`, `mart_data_quality`) đọc pack qua `pack_ref` |
| 4 | `5a8f4168` | Tách `int_sku_sales_monthly` (lõi) khỏi `mart_sku_economics_monthly` (finance); gate có bước "lõi trần" |
| 5 | `0d87fd6f` | `tenant_ref` cho 3 seed tenant mà lõi đọc, seed mặc định rỗng có kiểu |
| 6 | `b6bb06b6` | `crm_cache_refresh` do pack crm tự đăng ký qua `after_serving_selection()` |

Phase 1 là spike, không đổi file repo. Phase 7 (`dcf311cd`) và 8 (`f981af59`) chưa deploy: phase 7
cần sửa để `mart_capabilities` chỉ chạy trong nightly (quyết định user 15/10).

## Trước deploy

Mỗi phase qua gate M trên shadow (baseline là commit được chấp nhận ngay trước, build cùng ngày):
golden 83/83 0 khác biệt, compiled SQL Fine Japan không đổi (trừ 5 model phase 4 tách theo thiết
kế), boundaries sạch, taxonomy 0 cảnh báo, Dagster inventory 0 khác biệt (phase 4–5 chỉ thêm asset
và selection mới, báo INFO), pytest pass, bước "lõi trần" build xanh từ phase 4. `run-all.sh` pass sau
mỗi phase (324 test ở phase 6). Hai nới lỏng của dbt inventory dưới `--allow-code-change` (phụ thuộc
chuyển sang model tách ra; mô tả model đổi = INFO) đã được user duyệt 15/10.

## Sau deploy

- Healthy; instigator 26/26, `instigator_state.py diff` 0; serving 152 view; log không lỗi.
- Run đầu trên code mới: `pipeline_sapo_v2_realtime_job`, `pipeline_hug_realtime_job` SUCCESS; không
  run FAILURE/CANCELED nào từ 10:34.
- **Nightly chạy tay** `770f86bd-4cfd-4d95-ab8a-166a1595ff6f`: SUCCESS, 55/55 step, 498 check (thêm
  11 check mới, đều xanh). So với nightly lịch `ffb92b66` (03:00): một WARN mới
  `ingest_sapo_v2_orders_batch_asset` `row_count_within_trend`, hiện tượng đã biết khi chạy nightly
  lần thứ hai trong ngày (lần 03:00 đã nạp hết đơn); `customers_batch` row_count_within_trend lần này
  xanh. Còn lại 4 đỏ có từ trước (`products_batch` freshness ERROR, 3 check sheets WARN).

## Theo dõi tiếp

- Nightly lịch 16/10 03:00: phải xanh, không check mới đỏ ngoài các check theo thời điểm.
- `crm_cache_refresh` giờ nằm trong selection qua `after_serving_selection()`; CRM tiếp tục nhận
  refresh sau mỗi lần dựng serving.

---

# Deploy D3 (phase 7, 8, 9 + chỉ chạy `mart_capabilities` ở nightly) + sửa freshness — 15/10/2026 11:28

User duyệt deploy ngay (15/10 11:27). `main` fast-forward `b6bb06b6` → `9c25d02a` theo runbook:
`32fcaa17` (D3 của plan này) và `9c25d02a` (`fix/freshness-counts-skipped`, freshness tính cả run
`skipped`, rebase lên `32fcaa17`). Stop `data_platform` 11:28:09 (sau tick 11:27), start 11:28:20.
Rollback point `b6bb06b6`; dải revert `b6bb06b6..9c25d02a`. Sau rollback còn lại (vô hại): bảng
`mart_capabilities`, `lbl_*` và các seed capability/nhãn trong warehouse.

Trước deploy:
- D3: gate M `--allow-new --allow-code-change` với baseline là bản prod `b6bb06b6` (build 15/10):
  PASS. Golden 83/83 0 khác biệt, compiled SQL của model cũ 0 đổi, Dagster inventory 0 khác biệt
  (INFO: thêm `lbl_*`, seed nhãn, `mart_capabilities` ở nightly/fullrefresh), `labels_mapped` 5/5,
  "lõi trần" xanh. So với `f981af59` thì 6 job connector "nhỏ đi" (gỡ `mart_capabilities`), đúng ý;
  so với prod thì không đổi.
- Freshness: gate M PASS, 0 khác biệt. `run-all.sh` trên `9c25d02a`: 337 test pass.

Sau deploy:
- Healthy; instigator 26/26 `diff` 0; log không lỗi; không run FAILURE/CANCELED từ 11:28.
- **Nightly chạy tay** `bf000c1b-7e7c-4326-85f1-3819085a4498`: SUCCESS, 55/55 step, 539 check. So với
  `770f86bd`: 0 đỏ mới; **`products_batch` freshness ERROR hết đỏ** (bản sửa có hiệu lực). Còn 4 cảnh
  báo có từ trước hoặc theo thời điểm (`orders_batch` row_count_within_trend do chạy nightly lần thứ
  hai trong ngày, 3 check sheets).
- Kiểm thêm theo yêu cầu user: full refresh `products_batch` trên prod và so dữ liệu
  (`plans/reports/investigation-261015-1145-products-full-refresh-compare.md`): cursor không kẹt,
  danh mục Sapo không đổi từ 15/09.

`main` đã push (`origin/main` = `9c25d02a`).
