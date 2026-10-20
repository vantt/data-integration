---
phase: 6
title: "Chạy song song trên prod 14 đêm (bộ máy chưa nối mart)"
status: pending
priority: P2
effort: "0.75d công + 14 đêm"
dependencies: [5]
---

# Phase 6: Chạy song song trên prod

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/taxonomy-engine.md` (trạng thái: "chạy song song trên prod từ <ngày>", số nền thời gian/RAM, cách đọc log đối chiếu); `docs/architecture/modules.md` §9 (trạng thái module); `transformation/docs/TAXONOMY.md` mục `customer_type` (trạng thái). Commit tài liệu trạng thái lên nhánh sau khi đủ 14 đêm, deploy cùng phase 7.

## Mục tiêu

Đưa phase 1–5 lên prod với `taxonomy_engine_customer_type = false`: `lbl_*` và các monitor chạy mỗi lần build, mart vẫn chạy SQL cũ. Đếm 14 đêm liên tiếp không khác biệt, đồng thời đo thời gian và RAM so với số nền.

## Bối cảnh đã kiểm

- Job realtime (mỗi 3 phút) và incremental (mỗi 10 phút) chọn **toàn bộ** asset dbt (`orchestration/connectors/sapo_v2/jobs.py` L13–25), nightly lúc 03:00 cũng vậy (`orchestration/definitions.py` L94–107, L168–176). Vì vậy `lbl_*` và monitor chạy nhiều lần mỗi ngày, không chỉ ban đêm.
- Runbook deploy: `docs/operations/deployment.md` § "Refactor deploys (shadow-verified)" (dừng `data_platform`, commit seed đang sống, fast-forward, start, `instigator_state.py` diff, theo dõi nightly).
- Phase 4 bước 6 đã chứng minh khi biến tắt, mart không phụ thuộc `lbl_*`.

## Các bước

1. **Số nền (bắt đầu ngay khi phase 1 khởi động, đủ 7 đêm trước deploy):**
   - thời gian chạy `pipeline_batch_nightly_job` 7 đêm gần nhất (Dagster UI hoặc GraphQL đọc-chỉ, như `instigator_state.py`), và trung vị thời gian `pipeline_sapo_v2_realtime_job`;
   - RAM đỉnh của `data_platform` trong khung nightly. Phương pháp đề xuất: đặt lại và đọc `memory.peak` của cgroup container trước 02:55 và sau khi nightly xong (kernel cho phép ghi để đặt lại); nếu không có quyền, lấy mẫu `docker stats --no-stream` mỗi 30 giây trong khung nightly. Chốt **một** phương pháp và dùng y hệt trước và sau deploy. [UNVERIFIED: quyền đọc/ghi cgroup trên máy prod]
   - phân bố `customer_type` của `dim_customers` và số khách rơi vào `ELSE` (bằng số `RETAIL`).
   - Chốt cách đọc bảng DuckDB trên prod mà không tranh khoá với job (ví dụ kết nối `read_only` trong khoảng giữa hai lần chạy, hoặc truy vấn trong lần dừng container). [UNVERIFIED]
2. **Trước deploy:** rebase nhánh lên `main`; `git log main -- transformation/models/core/marts/dim_customers.sql transformation/models/core/marts/sales/fact_orders.sql transformation/models/core/marts/intermediate/int_customer_benchmarks.sql` không có commit mới chưa vào nhánh; chạy lại `gate.sh S --allow-new` trên commit sẽ deploy (dựng lại baseline theo harness §9.2 nếu `main` đã đổi). Kiểm nightly prod đang xanh.
3. **Deploy** theo runbook (thay tên nhánh), ngoài khung 02:30–04:00. Dải commit đổi `docker-compose.yml` (thêm `DBT_EXCLUDE_RESOURCE_TYPES=unit_test` cho `data_platform`, user chốt 15/10/2026: unit test không chạy trên prod), nên bước 5 của runbook dùng `docker compose up -d data_platform` (tạo lại container), không phải `start`; kiểm biến có trong container (`docker inspect data_platform`, chỉ đọc tên biến). Sau khi start: `instigator_state.py diff` không đổi; chạy một `pipeline_sapo_v2_realtime_job` và xác nhận xanh; kiểm bảng `lbl_customer_type`, `lbl_customer_type__group_blob` có số dòng bằng `dim_customers_base`, log đối chiếu có dòng đầu tiên.
4. **Theo dõi mỗi sáng (khoảng 10 phút, sau khi nightly xong, ngoài 02:30–04:00):**
   - nightly xanh, `row_trend_checks` trong ngưỡng, không asset check mới đỏ;
   - đọc **`monitor_taxonomy_parity_daily`** (view trên `monitor_taxonomy_parity_log`, **một dòng mỗi đêm và domain**; log có một dòng mỗi lần build, job realtime chạy mỗi 3 phút): `max_label_diff`, `max_flag_diff`, `n_ruleset_versions`, `n_engine_default + n_unmapped + n_unknown` so với `n_legacy_else` (bộ đếm của lần chạy cuối trong ngày), `ruleset_version` không đổi giữa các ngày;
   - một **đêm đạt** là một ngày (giờ Việt Nam) có `is_pass = true` cho **cả hai** domain (mọi lần chạy trong ngày `n_label_diff = 0`, `n_flag_diff = 0`, một bộ luật);
   - ghi kết quả từng ngày vào bảng nhật ký ở cuối file này.
5. **Quy tắc đếm:** có ngày khác biệt → đếm lại từ 0 và điều tra bằng `monitor_taxonomy_parity` (danh sách khách lệch); reset lần thứ hai → dừng, quay về phase 3–4 trên shadow. `ruleset_version` đổi (không được xảy ra vì không đổi luật) → đếm lại.
6. **Hiệu năng sau 7 đêm:** so thời gian nightly và RAM đỉnh với số nền; vượt 10% hoặc 10 phút (mức nhỏ hơn), hoặc RAM vượt 20% → điều kiện dừng 4: không chuyển cột, tối ưu hoặc huỷ.
7. Sau 14 đêm đạt: commit tài liệu trạng thái (deploy cùng phase 7).

## Verification

- 14 ngày liên tiếp đạt theo bước 4; mọi nightly xanh; hai action queue CRM có số dòng bình thường (không bị ảnh hưởng vì mart chưa đổi).
- Thời gian và RAM trong ngưỡng điều kiện dừng 4.
- `n_engine_default + n_unmapped + n_unknown ≤ n_legacy_else` mỗi ngày (điều kiện dừng 6; với 0 khác biệt thì bằng nhau).

## Đổi số?

**Không.** Mart chạy SQL cũ; bảng mới không được serving.

## Rollback

Theo runbook: dừng `data_platform`, commit seed đang sống, `git revert` dải commit đã deploy, start. Bảng `lbl_*`, `feat_*`, `monitor_taxonomy_parity_log` còn lại trong DuckDB không ai đọc; xoá bằng `DROP TABLE` ở lần dừng container kế tiếp. Seed luật bị revert cùng commit.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| `lbl_*` chạy mỗi 3 phút làm job realtime chậm | Đo ở bước 1 và 6; bảng khách khoảng 7 nghìn dòng; nếu đáng kể, cân nhắc gắn tag và loại khỏi realtime (đổi orchestration, cần duyệt) |
| Unit test chạy trong mỗi `dbt build` | Đã chốt (15/10/2026): `DBT_EXCLUDE_RESOURCE_TYPES=unit_test` cho `data_platform` trong `docker-compose.yml`, đi cùng deploy này (`docker compose up -d`); đã kiểm trên shadow với dbt và dagster-dbt |
| Đọc log trên prod tranh khoá DuckDB | Chốt cách đọc ở bước 1 trước deploy |
| Analyst sửa ba file mart trên `main` trong 14 đêm | Mọi sửa đổi đó phải cập nhật cả bản sao trong `monitor_taxonomy_parity` (inventory báo); nếu sửa đổi làm đổi logic, đếm lại |

## Effort

0.75 ngày công: 0.25 số nền và chuẩn bị, 0.25 deploy, khoảng 10 phút mỗi sáng trong 14 ngày.

## Nhật ký 14 đêm

| Ngày | Nightly | n_label_diff (max) | n_flag_diff (max) | default+UNMAPPED+UNKNOWN / ELSE | Thời gian nightly | RAM đỉnh | Đếm |
|---|---|---|---|---|---|---|---|
| 15/10 (từ 15:20, chưa tính) | tay `93ad3580` SUCCESS 55/55, 0 đỏ mới | 0 | 0 | 6030/6030 · 6395/6395 | 5,3 phút | 6,66 GiB | — |
| 16/10 (cả ngày, chốt 17/10) | lịch `3af400cf` 03:01 SUCCESS 59/59, 0 đỏ mới | 0 (615 lần chạy) | 0 | 6033/6033 · 6398/6398 | 5,3 phút | memory.peak 8,01 GiB (từ 15/10 18:52, gồm page cache; oom_kill 0) | 1 |
| 17/10 (cả ngày, chốt 18/10) | lịch `5ee65cf2` 03:01 SUCCESS 59/59, 567 check, 0 đỏ mới (so với tập đỏ đã biết: 3 check sheets) | 0 (615 lần chạy) | 0 | 6034/6034 · 6399/6399 | 5,4 phút | memory.peak 8,01 GiB (không đổi); lấy mẫu 02:52–03:40: anon đỉnh **3,53 GiB**, current đỉnh 8,00 GiB (file cache 4,72 GiB), oom_kill 0 | 2 |
| 18/10 (cả ngày, chốt 19/10) | lịch `d0b09efb` 03:01 SUCCESS 59/59, 567 check, 0 đỏ mới (3 check sheets đã biết) | 0 (610 lần chạy) | 0 | 6034/6034 · 6399/6399 | **13,9 phút** (vượt ngưỡng 10 phút, nguyên nhân ngoài, xem ghi chú 18/10) | bỏ đo; oom_kill 0 | 3 |
| 19/10 (cả ngày, chốt 20/10) | lịch `7928f479` 03:00 SUCCESS 59/59, 567 check; ngoài 3 check sheets đã biết có thêm `orders_batch` `row_count_within_trend` WARN (5 đơn so với trung vị 7 ngày 21, đêm Chủ nhật; check theo thời điểm) | 0 (612 lần chạy) | 0 | 6034/6034 · 6399/6399 | 5,2 phút | bỏ đo; oom_kill 0 | 4 |
| 20/10 (kiểm 09:4x, ngày chưa hết) | lịch `c633a631` 03:00 SUCCESS 60/60, 615 check (thêm check của bảng lịch sử giá/tồn, đều xanh), 0 đỏ mới (3 check sheets đã biết) | 0 (247 lần chạy) | 0 | 6036/6036 · 6401/6401 | bước dbt 36,5 s (19/10: 32,8 s; 18/10: 33,2 s; tăng vì 3 model lịch sử giá/tồn mới); tổng 2,4 phút (`approach_script_autogen` đã tắt) | bỏ đo; oom_kill 0 | 5 |

## Deploy lần 1 (15/10/2026 15:19)

User duyệt làm ngay (15/10 15:12). `main` fast-forward `9c25d02a` → `d31d51f2` (phase 1–5, biến
`taxonomy_engine_customer_type` = false). Stop `data_platform` 15:19:09, `git merge --ff-only`,
`docker compose up -d data_platform` (tạo lại container, áp `DBT_EXCLUDE_RESOURCE_TYPES=unit_test`;
đã kiểm biến có trong container) 15:19:24. Rollback point `9c25d02a`; dải revert
`9c25d02a..d31d51f2`, rồi `docker compose up -d data_platform`.

**Số nền (bước 1).** Lịch sử Dagster chỉ còn 1 nightly theo lịch (các run cũ hơn đã bị job dọn
dẹp xoá), nên số nền thời gian lấy từ 8 run `pipeline_batch_nightly_job` gần nhất (1 theo lịch,
7 chạy tay, 14–15/10): 5,0–5,5 phút, **trung vị 5,2 phút**; `pipeline_sapo_v2_realtime_job` trung
vị **40,8 giây** (60 run). RAM: `memory.peak` của cgroup container (đọc được, không ghi để đặt lại
được; tự về 0 khi container được tạo lại) — **6,54 GiB** từ 11:28 tới 15:15 (gồm một nightly và một
full refresh sản phẩm). Phương pháp cố định cho 14 đêm: đọc `memory.peak` sau nightly, so với số nền
này. Phân bố `dim_customers.customer_type` trước deploy: RETAIL 6.030, CROSSBORDER 1.538,
WHOLESALE 160, PARTNER 11. Đọc bảng DuckDB prod: chép `sapo_warehouse.duckdb` vào `/tmp/<dir>/`
trong container giữa hai lần chạy, mở `read_only` (tên file phải là `sapo_warehouse.duckdb` vì view
tham chiếu catalog đó), xoá sau khi đọc.

**Trước deploy (bước 2).** Nhánh ff được lên `main`; không có commit mới trên `main` đụng ba file
mart. Gate S `--allow-new` trên `d31d51f2` với baseline là bản prod `9c25d02a`: mọi bước dữ liệu
xanh — golden 83/83 0 khác biệt (cả rolling trống và sau full refresh), `labels_mapped` 6/6,
"lõi trần" xanh, pytest pass. Ba bước báo khác biệt đúng là các khác biệt đã chấp nhận: checksum
file của ba mart (nhánh `{% if %}`, compiled SQL không đổi), nội dung `lbl_customer_type` (thay bằng
bộ máy) và 3 job file-drop không còn chọn `lbl_customer_type`. Nightly prod xanh trước deploy.

**Sau deploy (bước 3).** Healthy; instigator 26/26 `diff` 0; log không lỗi; không run
FAILURE/CANCELED từ 15:19. Nightly chạy tay `93ad3580-fd1c-41ce-b148-25a7c5ef342e`: SUCCESS, 55/55
step, 562 check (thêm 23, đều xanh), 0 đỏ mới so với `bf000c1b`; 5,3 phút (+2 % so với trung vị);
RAM đỉnh 6,66 GiB (+2 %). `lbl_customer_type`, `lbl_customer_type__group_blob` và
`dim_customers_base` đều 7.739 dòng. `monitor_taxonomy_parity_daily` ngày 15/10: cả hai domain
`is_pass = true`, `max_label_diff = 0`, `max_flag_diff = 0`, một bộ luật; `n_engine_default` =
`n_legacy_else` (6.030 và 6.395), 0 UNMAPPED, 0 UNKNOWN.

**Đếm từ 16/10** (15/10 chỉ có dữ liệu từ 15:20, không có nightly theo lịch). **User rút ngắn (15/10 16:50): đủ 7 đêm liên tiếp đạt** (sớm nhất 22/10) thay vì 14; quy tắc đếm lại không đổi; phase 7 vẫn cần user duyệt giờ, đường cũ giữ 30 ngày như cũ.

**Ghi chú đo (17/10):** Dagster purge run sau khoảng 1 ngày nên run tham chiếu `93ad3580` không còn để so; từ 17/10 so tập check đỏ của nightly với tập đỏ đã biết (3 check `sheets_*` `not_empty_when_expected`). RAM: `memory.peak` của cgroup gồm page cache và chạm trần 8 GiB của container (kernel thu hồi cache, `oom_kill` = 0); RAM tiến trình (anon) đỉnh trong khung nightly đo bằng lấy mẫu 30 s. Số nền 6,54 GiB là `memory.peak` nên không so trực tiếp được với anon. Cách đo chính thức chờ user chốt.


**Ghi chú 18/10 (nightly 13,9 phút):** chậm do hai bước không liên quan bộ máy phân loại. (1) `sapo__ingest_sapo_v2_orders_batch_asset` mất 9 phút 23 giây (các đêm trước cả nightly chỉ 5,3–5,4 phút): Sapo tự sửa hàng loạt đơn cũ đúng lúc 03:02–03:11 (`modified_on` của 2.606 đơn rơi vào khung đó; đơn tạo từ 2023 đến 10/2026, trạng thái completed/finalized/cancelled), nên lần đồng bộ tăng dần kéo về 2.615 đơn (đêm trước 22 đơn, đêm 16/10 8 đơn). So 400 đơn với bản đã chụp trước đó: chỉ `modified_on` đổi ở cả 400, `customer_data` đổi ở 113, `fulfillments` ở 53. Không code nào trong repo ghi đơn lên Sapo (chỉ webhook consumer gửi ack). `resource-meter` cho thấy container gần như rảnh trong 9 phút đó (CPU khoảng 14%, không áp lực bộ nhớ hay IO), tức là chờ API Sapo. (2) `approach_script_autogen` mất 3 phút vì cả 10 lần gọi codex đều lỗi `rc=1`. Phần dbt (`sapo_dbt_assets`) 33 giây, bình thường. Đêm vẫn đạt theo quy tắc đếm (parity 0 khác biệt); điều kiện dừng 4 xét ở bước 6 sau 7 đêm, đêm này là ngoại lệ có nguyên nhân bên ngoài.
