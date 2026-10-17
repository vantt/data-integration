---
title: "Chuyển dashboard tồn kho sang dữ liệu chụp mới"
description: "Cho fact_inventory_snapshot, mart_inventory_health và các bảng phía sau đọc ảnh chụp tồn kho hằng đêm thay cho payload sản phẩm cũ, kèm đối soát on_hand với sổ kho. Đổi số dashboard tồn kho theo danh sách đã được user duyệt."
status: pending
priority: P1
effort: 2.5d
branch: feat/inventory-on-daily-snapshots
tags: [transformation, inventory, metabase, crm, reconciliation, number-change]
blockedBy: [261015-1730-price-inventory-history]
blocks: []
created: 2026-10-15
---

# Chuyển dashboard tồn kho sang dữ liệu chụp mới

## Overview

Ngày 15/10/2026 user chốt Q6 của plan [lịch sử giá và tồn kho](../261015-1730-price-inventory-history/plan.md): lập plan riêng, ưu tiên, để chuyển `fact_inventory_snapshot`, `mart_inventory_health` và dashboard tồn kho sang ảnh chụp hằng đêm. Việc này **đổi số**, nên mọi thay đổi số đi qua gate S và danh sách đổi phải được user duyệt trước khi deploy.

**Vì sao dashboard đang sai.** `fact_inventory_snapshot` đọc `int_sapo_inventories` (`transformation/models/core/marts/sales/fact_inventory_snapshot.sql:57`). Ở đó `snapshot_date = CAST(source_timestamp AS DATE)` (`transformation/models/core/intermediate/sapo/int_sapo_inventories.sql:123`), tức là ngày sản phẩm được sửa lần cuối, không phải ngày đo tồn. Số đo chỉ đọc ngày 15/10/2026 (DuckDB đọc parquet rolling mới nhất trong container `data_platform`, chỉ đếm tổng):

| Số đo | Giá trị |
|---|---|
| Số dòng `fact_inventory_snapshot` / số `snapshot_date` khác nhau | 2.052 / 103 ngày, từ 05/01/2023 đến 15/09/2026 |
| Số dòng ở `MAX(snapshot_date)`, là bộ lọc mà mọi card "hôm nay" trên Metabase dùng | **3 dòng, 1 SKU** |
| Card "Tổng Giá Trị Tồn Kho" hôm nay so với khi mọi cặp có mặt | 2,1 tr so với 1.025,1 tr |
| Card "Tổng SKU Có Hàng" hôm nay so với khi mọi cặp có mặt | 1 so với 97 |
| Số dòng trong 90 ngày gần nhất mà các card xu hướng đọc | 3 dòng, 1 ngày |
| Cặp (variant, kho) có ở cả hai bảng; lệch `on_hand` so với sổ kho | 1.285; **25 cặp lệch**, và cả 25 cặp sổ kho có biến động **sau** `snapshot_date` (tức là snapshot cũ) |
| Cặp chỉ có trong snapshot, `on_hand ≠ 0` (không có dòng sổ kho nào từ 20/05/2021) | 71 cặp, tổng 8.534 đơn vị |
| `available = on_hand − committed` trong snapshot | 2.052 / 2.052 dòng |

Như vậy, các card Metabase "hôm nay" và "xu hướng" hiện gần như rỗng, còn `mart_product_health` (lấy dòng mới nhất theo từng cặp, `mart_product_health.sql:95-113`) mang tồn kho cũ tới 3 năm.

**Làm gì.**
1. `fact_inventory_snapshot` đọc `fact_inventory_position_daily` (bảng do plan lịch sử giá/tồn tạo ở phase 2). Tên bảng, tên cột, kiểu và thứ tự cột giữ nguyên. Chỉ **thêm** ba cột ở cuối: `captured_at`, `ledger_on_hand`, `on_hand_recon_status`.
2. Đối soát `on_hand` của ảnh chụp với sổ kho (`fact_inventory_movements`, số dư tại `captured_at`), kèm một asset check (dbt test mức warn) chạy từ nay về sau.
3. `mart_product_health` lấy ngày chụp mới nhất chung thay vì dòng mới nhất theo từng cặp.
4. Sửa card Metabase theo các quyết định định nghĩa trong [definition-decisions.md](definition-decisions.md), cập nhật blueprint và tài liệu.

## Nguồn nào là gốc cho từng trường

| Trường | Nguồn gốc cho dashboard | Vai trò của nguồn còn lại | Lý do |
|---|---|---|---|
| `on_hand` (hiện tại và từ ngày chụp đầu tiên) | **Ảnh chụp hằng đêm** (số Sapo trả về) | Sổ kho dùng để **đối soát**, và là lịch sử `on_hand` trước ngày chụp đầu tiên (`fact_inventory_balance`, từ 20/05/2021) | Ảnh chụp phủ mọi cặp; 71 cặp có hàng không có dòng sổ kho nào. Cùng một lần gọi API với `committed`/`available`, nên giữ được đẳng thức `available = on_hand − committed` (đúng ở 100% dòng). Sổ kho có khoảng 4,4% cặp nhảy số không giải thích được (`fact_inventory_balance.sql:23-25`). Chờ user chốt ở QĐ-TK-01 |
| `available`, `committed`, `incoming`, `onway` | Ảnh chụp | Không có nguồn khác | Sổ kho không có các trường này |
| `min_value`, `max_value`, `bin_location`, `wait_to_pack` | Ảnh chụp | Không có | Chỉ có trong payload `inventories` |
| `mac` và `stock_value_at_mac` | Ảnh chụp (`on_hand × mac` như hiện nay, `fact_inventory_snapshot.sql:131-141`) | `moving_avg_cost`/`inventory_value` của sổ kho chỉ có ở ngày có giao dịch; đưa tổng giá trị vào báo cáo đối soát để tham khảo | Giữ nguyên công thức và cột cũ |

**Quy tắc khi hai nguồn lệch nhau** (chi tiết ở [phase-01](phase-01-dbt-switch-and-reconciliation.md)):
- Dashboard luôn dùng số của ảnh chụp. Sổ kho không bao giờ ghi đè.
- `on_hand_recon_status` của mỗi dòng nhận một trong ba giá trị:
  - `match`: bằng số dư sổ kho tại `captured_at`.
  - `no_ledger_history`: cặp chưa có giao dịch nào tới `captured_at`. Đây là trường hợp đã biết, không cảnh báo.
  - `mismatch`: khác số dư sổ kho.
- Asset check `assert_inventory_snapshot_onhand_matches_ledger` (severity warn) báo khi số cặp `mismatch` ở ngày chụp mới nhất vượt ngưỡng. Ngưỡng được hiệu chỉnh ở phase 0 trên N đêm chụp thật (QĐ-TK-07).
- Cách xử lý: một cặp lệch hai đêm liên tiếp được ghi là Sapo sửa không qua sổ (loại đã biết). Nhiều cặp lệch cùng một đêm thì kiểm `coverage_ratio` của bước chụp và độ tươi của job `pipeline_sapo_v2_hourly_job` trước khi tin bất kỳ số nào.

## Yêu cầu bắt buộc

1. Không làm trên checkout prod. Dùng worktree nhánh `feat/inventory-on-daily-snapshots` tạo từ `main` **sau khi** plan lịch sử giá/tồn đã deploy D2. Chỉ thử trên shadow.
2. **Tương thích ngược:** giữ nguyên tên relation, tên, kiểu và thứ tự mọi cột hiện có. Cột mới chỉ thêm ở cuối. Không đổi tên, không xoá cột. `inventory_modified_at` (luôn NULL) và `int_sapo_inventories` được đánh dấu deprecated trong YAML nhưng vẫn giữ.
3. **Mọi thay đổi số đều phải được user duyệt:** mỗi quyết định có số trước/sau ghi ở [definition-decisions.md](definition-decisions.md). Danh sách đổi cuối cùng (bảng, cột, card) phải được user duyệt sau gate S, trước khi deploy.
4. Gate S: các bảng có khác biệt golden phải **khớp đúng** danh sách dự kiến (E-list, [phase-03](phase-03-gate-numbers-and-approval.md)). Mọi bước khác của gate phải PASS.
5. Tài liệu cập nhật cùng commit với code của phase đó.
6. Deploy theo runbook "Refactor deploys (shadow-verified)" (`docs/operations/deployment.md:668-748`), vào giờ user duyệt, ngoài khung 02:30–04:00.
7. Không ghi plan ID, số phase, mã quyết định hay mã finding vào comment code, tên test hay commit message.
8. Không đọc `.env*`. Report và test fixture không chứa dữ liệu khách hàng. Số trước/sau chỉ là số tổng hợp; với `mart_deadstock_target_queue` chỉ đếm dòng và đếm sản phẩm.

## Phụ thuộc: sớm nhất khi nào bắt đầu

| Mốc | Điều kiện | Kiểm bằng |
|---|---|---|
| Bắt đầu phase 0–3 (code, shadow) | Plan lịch sử giá/tồn đã deploy D2 (có `fact_inventory_position_daily` trên `main`); baseline shadow đã làm mới (`docs/operations/refactor-safety-harness.md` §9.2) với lake-base có ≥ 2 đêm chụp | `git log main` có model; `ls lake-base/sapo_v2_raw/product_daily_snapshot` |
| Deploy (phase 4) | **N = 7 đêm chụp liên tiếp** trên prod, mỗi đêm `coverage_ratio ≥ 0,98`; ít nhất một nightly xanh sau D2 | `SELECT count(DISTINCT as_of_date) FROM fact_inventory_position_daily` ≥ 7, không có ngày trống |

**Vì sao N = 7:**
1. Ngưỡng đối soát cần phân bố số cặp lệch trên một chu kỳ tuần đủ, có cả cuối tuần và ngày nhập hàng.
2. Card xu hướng 7 ngày có đủ điểm. Card 30/90 ngày và 12 tháng sẽ bắt đầu từ ngày chụp đầu tiên; điều này được ghi trong card nguồn dữ liệu.
3. Lỗi của bước chụp thường lộ ra trong tuần đầu, khớp với 7 đêm theo dõi của plan lịch sử (phase 3).

Raw được tính từ D1, không phải D2, vì `fact_inventory_position_daily` dựng lại toàn bộ từ raw. Nếu D1 deploy sớm thì 7 đêm có thể đã đủ khi D2 xong. **Hiện trạng 15/10/2026:** thư mục `sapo_v2_raw/product_daily_snapshot/` chưa có, nghĩa là D1 chưa deploy.

## Phases

| # | Phase | File | Effort | Phụ thuộc | Gate | Đụng prod | Cần user |
|---|---|---|---|---|---|---|---|
| 0 | Kiểm tiền điều kiện, hiệu chỉnh đối soát, kiểm kê card thật, gửi quyết định | [phase-00](phase-00-preconditions-and-calibration.md) | 0.25d | Plan lịch sử D2; ≥ 2 đêm chụp | — | Chỉ đọc | Chốt QĐ-TK-01…07 |
| 1 | Đổi model dbt và thêm đối soát | [phase-01](phase-01-dbt-switch-and-reconciliation.md) | 1d | 0 (các QĐ ảnh hưởng SQL đã chốt) | pytest + `run-all.sh` | Không | — |
| 2 | Card Metabase, blueprint, tài liệu | [phase-02](phase-02-dashboards-and-docs.md) | 0.5d | 1 | Validator blueprint (`--dry-run`) | Không | — |
| 3 | Gate S, số trước/sau, user duyệt danh sách đổi | [phase-03](phase-03-gate-numbers-and-approval.md) | 0.5d | 1, 2 | `scripts/shadow/gate.sh S --allow-new --allow-code-change` với E-list | Không | **Duyệt danh sách đổi** |
| 4 | Deploy, cập nhật card, theo dõi 3 đêm, đóng | [phase-04](phase-04-deploy-and-observe.md) | 0.25d + 3 đêm | 3; **N = 7 đêm** | Runbook | Có | **Duyệt giờ deploy** |

```text
[plan lịch sử: D1 ─► ≥2 đêm ─► D2] ─► 0 ─► 1 ─► 2 ─► 3 (user duyệt) ─┐
[plan lịch sử: D1 + 7 đêm liên tiếp] ─────────────────────────────────┴─► 4
```

## Quyền sở hữu file

Các phase chạy tuần tự, nên không có hai phase sửa cùng một file song song.

| Phase | File sở hữu |
|---|---|
| 1 | `transformation/models/core/marts/sales/{fact_inventory_snapshot.sql,mart_inventory_health.sql,_core__models.yml}`, `transformation/models/core/marts/{mart_product_health.sql,_core__models.yml}`, `transformation/models/core/intermediate/sapo/_core__models.yml` (chỉ ghi chú deprecated), `transformation/tests/assert_inventory_snapshot_onhand_matches_ledger.sql` (mới), `transformation/dbt_project.yml` (một biến), `scripts/checks/public_models.yaml` (sinh lại nếu cần). Nếu plan lịch sử chưa đưa `bin_location`/`wait_to_pack` vào: `stg_sapo_v2_inventory_position_captures.sql`, `std_inventory_position_captures.sql`, `fact_inventory_position_daily.sql` (chỉ thêm cột) |
| 2 | `docs/analytics-handbook/blueprints/metabase/{product_inventory_stock_health.md,product_health_overview.md}`, `docs/analytics-handbook/semantic/{freshness.md,entities.md,metrics.md}`, `docs/analytics-handbook/domains/product.md`, `docs/architecture/data-model.md` |
| 3 | Chỉ ghi vào thư mục plan này: `reports/`, `change-list.md`, `definition-decisions.md` |
| 4 | Không sửa code. Ghi `reports/observation.md`. Đổi trạng thái plan bằng CLI `ak plan` |

**Va chạm với plan khác:**
- Plan lịch sử giá/tồn phase 2 cũng sửa comment `fact_inventory_snapshot.sql` và các tài liệu `freshness.md`, `entities.md`, `data-model.md`, `domains/product.md`. Plan này chạy sau, nên chỉ cần rebase.
- Plan report-productization phase 12 (INV-D trên Metabase) và phase 14 (INV-W, INV-M trên Evidence) dùng dashboard `inventory_stock_health`. Phase nào deploy sau thì rebase blueprint `product_inventory_stock_health.md`. Báo coordinator để INV-D/W/M dựng trên số mới.

## Tiêu chí chấp nhận (đo được)

1. **Số đúng ngày:** sau deploy, `MAX(snapshot_date)` của `fact_inventory_snapshot` bằng ngày hôm qua (ICT). Số cặp ở ngày đó bằng số cặp của `fact_inventory_position_daily` cùng `as_of_date` (100%).
2. **Hết dữ liệu cũ:** 0 dòng có `snapshot_date` nhỏ hơn ngày chụp đầu tiên (nếu QĐ-TK-02 = (a)). 25 cặp lệch đo ngày 15/10 đều có `on_hand_recon_status ∈ {match, mismatch}` và không còn cặp nào cũ hơn đêm chụp gần nhất.
3. **Đối soát chạy:** asset check `assert_inventory_snapshot_onhand_matches_ledger` có trên asset `fact_inventory_snapshot` trong Dagster và chạy ở mọi build. Trong 3 đêm theo dõi, số cặp `mismatch` ở ngày mới nhất không vượt ngưỡng đã chốt, hoặc mỗi lần vượt đều có ghi chú nguyên nhân trong `reports/observation.md`.
4. **Gate S:** khác biệt golden đúng bằng E-list (5 bảng ở phase 3). 0 khác biệt ở mọi bảng public còn lại. Build trên lake rỗng, lõi trần và `--full-refresh` đều xanh.
5. **Tương thích:** 100% cột hiện có giữ tên, kiểu và thứ tự (golden schema chỉ báo phần **thêm** ở cuối). `pytest crm/sync` xanh, không đổi cột ghim nào.
6. **Số đã duyệt khớp prod:** sau deploy, chạy lại script số card trên prod với cùng `snapshot_date` dùng ở shadow cho ra đúng số đã duyệt ở `change-list.md` (chênh 0, trừ khi Sapo đã sửa dữ liệu ngày đó).
7. **Card:** mọi card trong danh sách đổi đã cập nhật đúng id (PUT tại chỗ, không tạo card mới). Ba card "Chu kỳ báo cáo" của dashboard tồn kho hiện ngày của dữ liệu (`MAX(snapshot_date)`) thay vì `current_date`. Card nguồn dữ liệu hiện "Dữ liệu tồn đến hết ngày …" và số cặp lệch sổ kho.
8. **Tài liệu:** mô tả `snapshot_date`, `source_timestamp`, nguồn và quy tắc đối soát trong YAML và các tài liệu ở phase 2 khớp với SQL.

## Ma trận test (tổng hợp)

| Mức | Nội dung | Phase |
|---|---|---|
| dbt unit | Đối soát: `match`, `mismatch`, `no_ledger_history`, giao dịch sau `captured_at` không tính, hai kho riêng. `latest_inv` theo ngày chung. `is_oos` mức sản phẩm (nếu chọn QĐ-TK-05 (b)) | 1 |
| dbt data | Unique theo grain; `accepted_values` cho `on_hand_recon_status`; test đối soát (warn) thành asset check | 1 |
| pytest | `crm/sync` (cột ghim), `orchestration` | 1, 3 |
| Tĩnh | Validator blueprint; `deploy_from_markdown.js --dry-run` chỉ có update | 2 |
| Tích hợp (gate S) | Golden đúng E-list ở build thường, rolling rỗng và full refresh; lõi trần xanh; boundaries, dbt và Dagster inventory chỉ có phần thêm | 3 |
| Số trước/sau | Mọi card trong kiểm kê, CRM, đối soát, ở `as_of_pin` | 3 |
| Prod | Số ở `as_of_pin` khớp số đã duyệt; 3 đêm theo dõi | 4 |

## Rủi ro chính

| Rủi ro | Khả năng × tác động | Giảm thiểu |
|---|---|---|
| Card "OOS SKUs" nhảy từ 1 lên 684 (mọi SKU đều có ít nhất một kho bằng 0), gây hoảng | Chắc chắn nếu giữ định nghĩa × Cao | QĐ-TK-03 đổi định nghĩa card trước khi deploy; số mẫu đã đo |
| Nightly lỡ một đêm thì card "hôm nay" vẫn hiện ngày cũ mà không ai biết | Trung bình × Trung bình | Card nguồn dữ liệu hiện ngày; freshness check của raw (plan lịch sử) đã báo Lark |
| Đêm chụp thiếu sản phẩm (coverage < 98%) làm tổng tồn ngày đó tụt | Thấp × Trung bình | Check độ phủ của plan lịch sử; đối soát ở đây báo `no_ledger_history`/`mismatch` tăng; quy trình xử lý ở phase 1 |
| Kiểu cột mới lệch kiểu cũ (`variant_id`, `location_id`, DECIMAL) làm vỡ CRM hoặc card | Trung bình × Cao | Cast tường minh về kiểu cũ; golden so schema; `pytest crm/sync` |
| `mart_inventory_health` lớn dần (khoảng 750 nghìn dòng/năm) mà vẫn build mỗi 3 phút | Chắc chắn × Thấp | Đo thời gian build ở gate. Nếu một model vượt 5 giây/run thì mở việc riêng đưa vào `NIGHTLY_ONLY_ASSETS` |
| CRM (`wh_deadstock_target`, `product_insight.oos_risk`) và hàng đợi hành động đổi danh sách | Chắc chắn × Trung bình | Có trong danh sách đổi; số trước/sau theo số dòng và số sản phẩm; user duyệt |
| Deploy cùng lúc với report-productization phase 12/14 | Thấp × Trung bình | Coordinator xếp lịch; rebase blueprint |

## Rollback

- **Code dbt:** `git revert` phạm vi đã deploy theo runbook (`deployment.md:733-748`). `int_sapo_inventories` không đổi, nên build kế tiếp trả lại đúng số cũ.
- **Metabase:** trước khi deploy card, chụp lại dashboard bằng `capture_dashboard.js` vào `reports/metabase-before/`. Rollback bằng cách deploy lại blueprint ở commit trước (PUT tại chỗ, giữ id).
- **CRM:** lần sync kế tiếp đọc lại mart đã revert. Không cần thao tác gì.
- **Raw ảnh chụp:** không đụng tới.

## Quyết định cần user chốt

Xem [definition-decisions.md](definition-decisions.md): QĐ-TK-01 đến QĐ-TK-07, mỗi quyết định có lựa chọn, đề xuất và số mẫu đo ngày 15/10/2026. Phase 1 chỉ bắt đầu khi QĐ-TK-01 đến 05 đã chốt.

**Đã chốt 15/10/2026:** user duyệt plan và chọn theo đề xuất cho cả 7 quyết định: 01 (a), 02 (a), 03 (c), 04 (b), 05 (b), 06 (a), 07 (a) + (x). **16/10/2026:** user chọn **không sửa tạm** các card "hôm nay" trên prod trước khi deploy plan này. Câu hỏi mở 3 vì vậy đã có trả lời: chỉ asset check trong Dagster và card nguồn dữ liệu, không thêm vào digest Lark.

## Câu hỏi mở cho user

1. Có đồng ý **N = 7 đêm chụp liên tiếp** là điều kiện deploy không, hay muốn deploy sớm hơn (ví dụ 3 đêm) và chấp nhận card xu hướng ít điểm trong tuần đầu?
2. Chọn giờ deploy nào (ngoài 02:30–04:00), và có muốn gộp với đợt deploy của report-productization phase 12 không?
3. ~~Cảnh báo đối soát chỉ hiện ở Dagster (asset check warn) và trên card nguồn dữ liệu là đủ, hay cần thêm một dòng vào digest buổi sáng trên Lark (QĐ-TK-07)?~~ Đã chốt theo QĐ-TK-07 (a) + (x).
4. ~~Plan lịch sử giá/tồn có thể thêm `bin_location` và `wait_to_pack` vào `fact_inventory_position_daily` ngay ở phase 2 của nó không? Nếu không, plan này sẽ tự thêm (chỉ thêm cột).~~ Đã có: commit `15054360` (`feat/price-inventory-history`) thêm `bin_location` và `wait_to_pack` vào `fact_inventory_position_daily`; raw chụp cả hai trường từ 15/10 18:52 (c8 xác nhận 15/10/2026).
