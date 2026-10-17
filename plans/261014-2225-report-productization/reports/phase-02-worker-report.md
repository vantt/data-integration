# Phase 02 — báo cáo worker

**Trạng thái:** xong, trừ bước 1 (capture dashboard đang chạy) **chưa chạy được**: không có `METABASE_API_KEY` trong môi trường của worker, và worker không được đọc `.env*` hay `app_data/secrets`. Spec ghi rõ mốc tạm là blueprint (`baseline.verified_against_live: false`).

## File của phase này (worktree `/home/vantt/app/fg-dw-report`)

Mới:
- `analytics/schema/report-spec.schema.json`, `analytics/schema/catalog.schema.json`
- `analytics/catalog/catalog.yml` (1 mục: `ceo_weekly_pulse`, `EXE-W`, `engine: evidence`, `area: dieu-hanh`, `status: pilot`)
- `analytics/specs/ceo_weekly_pulse.yml` (3 tab, 30 question đúng thứ tự/tên blueprint, `baseline_name` + `baseline_columns` từng card)
- `analytics/compiler/spec_validate.py` (kiểm spec + catalog; tách khỏi `validate.py` cho gọn)
- `analytics/tests/test_spec_validate.py`
- `.skills/analytics-design/templates/report_spec_v2_template.yml`

Sửa (chỉ phase này):
- `.skills/analytics-design/SKILL.md` (dòng 12: spec v2 bắt buộc cho report sản phẩm, Phase 4–5 chọn metric id; bảng template), `.skills/metabase-automation/STRATEGY.md` (bỏ "Forthcoming `deploy_from_design_spec.js`", trỏ plan này)

Sửa **cả ở phase 01 và 02** (không tách được theo dòng; coordinator commit chung hoặc dùng snapshot dưới):
- `analytics/compiler/validate.py` (gọi kiểm catalog, mức INFO, `--catalog`), `analytics/compiler/loader.py` (`load_catalog`, `load_spec`, `spec_file`)
- `analytics/schema/semantic-model.schema.json` (trường `axis` bắt buộc cho time dimension; file được ghi lại định dạng JSON thụt 2), `analytics/schema/tenant-profile.schema.json` (`tenant_params`; cũng ghi lại định dạng)
- `analytics/registry/semantic/{orders,order_economics,order_returns,customers}.yml` (thêm `axis`)
- `tenants/fine_japan/analytics/profile.yml` (`tenant_params.monthly_target_goal = 600000000`, `detailview_url_template`)
- `analytics/README.md` (mục "Spec v2 và catalog"), `docs/architecture/modules.md` (§13 + bảng trạng thái)

Snapshot toàn bộ file thay đổi lúc hết phase 02: `scratchpad/rp/worktree-end-phase02.tgz` (+ danh sách `p2-files.txt`), để tách phase 03 khi commit.

## Kiểm chứng

- Validator: 0 lỗi; INFO `ceo_weekly_pulse: 2/24 data cards use inline_sql` (8%, đúng dự kiến: "Đơn hàng tuần này", "Loss-Making Channel Count").
- 30 card ↔ 30 question của blueprint: cùng tab, cùng thứ tự, cùng tên (test `test_spec_follows_the_blueprint_order_and_names`).
- Fixture hỏng đều lỗi: metric_ref lạ, `card_id` trùng, `inline_sql` thiếu `outputs`, `inline_sql` đọc đồng hồ, chiều lạ, sai trục thời gian (card phiếu hoàn), `metrics` catalog lệch spec, cờ chi phí sai, `kpi_tile` lạ, thiếu tham số khách; quá 30% `inline_sql` thì cảnh báo. Template của skill cũng qua schema + registry.
- `pytest analytics/tests`: 108 passed. `run-all.sh` (SHADOW_ROOT ở scratchpad): `RUN-ALL: PASS`.
- Bước 1: đã đọc code `capture_dashboard.js` + `lib/metabase_core.js`: chỉ GET (`/api/user/current`, `/api/session/properties`, `/api/dashboard/:id`, `/api/card/:id`, `/api/collection/:id`), chỉ ghi file đầu ra cục bộ. Lưu ý: client tắt kiểm TLS (`rejectUnauthorized: false`, lỗi D4 của phase 06); với URL `http://` nội bộ không ảnh hưởng.

## Việc cần coordinator/user

Chạy capture chỉ đọc (cần API key và id dashboard "CEO Weekly Pulse [All]" trong collection Executive), rồi so SQL từng card với blueprint:

```bash
METABASE_URL=<url> METABASE_API_KEY=<key> node .skills/metabase-automation/scripts/capture_dashboard.js <dashboard_id> /tmp/ceo_weekly_pulse_live.md
```

Nếu lệch: mốc so số là bản đang chạy; sửa `analytics/specs/ceo_weekly_pulse.yml` (và registry nếu định nghĩa khác), đặt `baseline.kind: metabase_live`, `verified_against_live: true`.

## Quyết định thiết kế cần biết

- `cell` trong catalog là danh sách (report có thể nằm nhiều ô), `primary_cell` là một ô; mã chức năng cho phép `EXE|SAL|MKT|FIN|INV|LOG|OPS|CUS|UTL`.
- `metrics` của catalog vẫn ghi trong file nhưng validator bắt buộc bằng hợp `metric_ref` của spec và in danh sách đúng khi lệch.
- Text card tiêu đề của blueprint thành `blocks[].title`; text "Source & Freshness" không chép vào spec vì chân trang quy ước doanh thu do renderer sinh từ registry/hồ sơ.
- MTD GMV vs Target và Forecast dùng `comparison: target` + `goal: {param: monthly_target_goal}` (tenant param, như plan).

## Bổ sung 15/10/2026: bước 1 (capture-first) đã xong

Coordinator chụp chỉ đọc dashboard đang chạy "CEO Weekly Pulse [All]" (Metabase id 43, collection `Phân tích của chúng tôi > Executive`) ra `scratchpad/capture/weekly-pulse-43.md`. So từng question theo (tab, tên) với blueprint và spec:

| Hạng mục | Kết quả |
|---|---|
| Số question | Live 28, blueprint 30. **Live không có** "Forecasted Month-End GMV" và "Cần Đạt Mỗi Ngày (Required Daily Run-Rate)" |
| SQL của 28 question chung | Trùng blueprint từng ký tự sau khi chuẩn hoá khoảng trắng: không có định nghĩa nào khác |
| Vị trí (row/col/size) | Trùng ở cả 28 |
| Visualization | Trùng sau khi chuẩn hoá khoá `column_settings` (`["name","X"]` ↔ `X`), trừ: (a) bảng "Đơn hàng tuần này" trên live không có định dạng tiền VND cho cột Gross, Chiết khấu, Net Revenue (chỉ còn link `detailview`, ẩn `order_id`); (b) 6 card meta không có `card.title: ""` (bản chụp bỏ khoá rỗng). Chỉ là trình bày, không đổi số |
| Text card, tab, tiêu đề | Trùng |

Theo quy tắc mốc là bản đang chạy, đã sửa (worktree, chưa commit):
- `analytics/specs/ceo_weekly_pulse.yml`: bỏ khối `du_bao_thang` (2 card trên); `baseline.kind: metabase_live`, `verified_against_live: true`, ghi chú nguồn. Spec còn 28 card, 22 card dữ liệu, `inline_sql` 2/22 (9%).
- `analytics/catalog/catalog.yml`: bỏ `gmv_month_end_forecast`, `gmv_required_daily_run_rate` khỏi `metrics`.
- `analytics/registry/metrics/sales.yml`: hai chỉ tiêu trên chuyển `status: draft` (giữ định nghĩa, ghi chú "có trong blueprint, không có trên dashboard đang chạy"); không chỉ tiêu nào đổi định nghĩa.
- Sinh lại `docs/analytics-handbook/semantic/metric-registry.md` và `evidence/areas/dieu-hanh/` (xoá 2 file SQL; các file khác chỉ đổi hash đầu vào trong banner).
- `analytics/tests/test_spec_validate.py` (so thứ tự/tên với blueprint trừ 2 question không có trên live; 28 card; 2/22), `analytics/tests/test_render_evidence.py` (22 + meta), `analytics/README.md`, `docs/architecture/modules.md`.
- Bảng đơn hàng trên Evidence vẫn định dạng tiền (trình bày, không đổi số); ghi nhận để user biết.

So số lại trên SQL **live** (bản chụp chỉ đọc 15/10/2026 09:57 ICT, 4 ngày tham chiếu 11/10, 04/10, 15/09, 01/10): **128/128 khớp** (136 cũ trừ 2 card × 4 ngày). Lần chạy đầu gặp file parquet đang được thay (rolling refresh lúc 09:57) nên chạy lại; bản chụp tạm đã xoá.

`scripts/checks/run-all.sh` (SHADOW_ROOT trong scratchpad): `RUN-ALL: PASS` (pytest có một test đã biết là flaky `test_concurrent_writes_no_lock_error`, lần chạy lại xanh); `pytest analytics/tests` 113 passed.

Câu hỏi cho user: hai card Forecast / Run-rate có trong blueprint nhưng không còn trên dashboard. Bỏ hẳn (xoá khỏi blueprint và registry) hay đưa lại lên trang Evidence? Hiện để `draft`.
