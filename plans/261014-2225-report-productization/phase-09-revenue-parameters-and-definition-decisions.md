---
phase: 9
title: "Tham số doanh thu: 2 preset, VAT, net_revenue (sau hoàn), doanh thu đã giao, fact_revenue_events; áp các quyết định đổi số đã duyệt"
status: pending
priority: P1
effort: "3d"
dependencies: [5, 8]
---

# Phase 09: Tham số doanh thu và quyết định định nghĩa

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi thiết kế `fact_revenue_events` vào `docs/architecture/modules.md` §7 Core và data dictionary; ghi bảng tham số và hai preset vào `analytics/README.md`. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/architecture/modules.md` (§7 Core: model mới, §11 Serving: view mới); `docs/architecture/data-dictionary.md` (cột của `fact_revenue_events`); `analytics/README.md` (tham số, preset, quy tắc "ghi tường minh trong hồ sơ"); `docs/analytics-handbook/semantic/metric-registry.md` và `glossary.md` (sinh lại); `plans/261014-2225-report-productization/definition-decisions.md` (trạng thái từng quyết định đã áp).

## Mục tiêu

Hiện thực quyết định 1 và 2 của §11 cho khách mới mà **không đổi số FJ**, rồi áp các quyết định đổi số đã được user duyệt ở phase 00 (mỗi quyết định một commit, qua gate S). Bắt đầu sau khi thí điểm đóng để không làm nhiễu 4 chu kỳ so số.

## Thiết kế

### Tham số doanh thu (áp lúc sinh SQL, không build lại dbt theo khách)

| Tham số | Giá trị | Áp ở đâu |
|---|---|---|
| `revenue_recognized_at` | `order_created` (mặc định), `delivered` | Compiler chọn trục thời gian và gate (`is_delivered`) |
| `return_deducted_at` | `return_completed` (mặc định, vào kỳ hoàn, dòng riêng) | Compiler |
| `vat_mode` | `included_in_price`, `excluded_from_price`, `not_applicable` | Compiler: `net_sales` chưa VAT = `total_amount − vat_amount` (cột mart `net_revenue` hôm nay, `fact_orders.sql:184`); gồm VAT = `total_amount` (`:186`); `not_applicable` = `total_amount`. Thay `/1.08` viết cứng |
| Sàn trợ giá | **Không phải tham số** (§4 ①): phần sàn trả tính là doanh thu, hiện dòng riêng | Registry: chỉ tiêu riêng khi có khả năng `marketplace_settlement` |
| AOV | Cố định: `net_sales` / số đơn tính doanh thu, không gồm ship và VAT | Registry |

Hai preset trong `analytics/registry/presets/`, **đề xuất** (chờ user xác nhận, câu hỏi mở 1): "Như Sapo" (mặc định) = `order_created`, `return_completed`, `included_in_price`; "Theo kế toán" = `delivered`, `return_completed`, `excluded_from_price`. Hồ sơ khách **ghi tường minh từng tham số** (không thừa kế mặc định), để nâng cấp không âm thầm đổi số. Hồ sơ FJ ghi đúng cách hôm nay: `order_created`, `return_completed`, `excluded_from_price`. Validator: hồ sơ thiếu một tham số → lỗi; giá trị cần khả năng mà khách không có (vd. `delivered` khi không có `fulfillment_events`) → lỗi.

### Chỉ tiêu mới (quyết định 1, 2)

- `returns_amount` (hàng bán bị trả lại, trục ngày hoàn), `net_revenue` (nghĩa kế toán) = `net_sales − returns_amount` trong cùng kỳ, `delivered_net_sales` ("doanh thu đã giao", cho shop COD, trục ngày giao thành công). Các thẻ hiện có dùng `net_sales` giữ nguyên số.
- Để `net_revenue` và `delivered_net_sales` cắt được theo kênh/khách mà không ghép hai fact khác grain trong BI (giới hạn cứng phase 01), thêm model dbt **`fact_revenue_events`** (thiết kế §4 ①): một dòng cho mỗi sự kiện có dấu: `sale` (tại `ordered_at`, số tiền chưa và gồm VAT tách cột), `return` (âm, tại ngày hoàn từ `fact_order_returns`), kèm `delivered_at` của đơn (lần giao thành công cuối, từ `fact_fulfillments`), `channel_key`, `customer_key`, `is_active_order`. Mọi biến thể là `SUM(amount)` trên một bảng. Model mới ở `transformation/models/core/marts/sales/`, vị trí rolling như các mart khác; **không sửa model hiện có**.

### Quyết định đổi số đã duyệt (phase 00)

Mỗi quyết định có trạng thái `duyệt` trong `definition-decisions.md` được áp bằng một commit riêng: sửa registry (và mart nếu quyết định nằm ở dbt), chạy gate S, lập **danh sách card/dashboard/trang đổi số** kèm số trước/sau trên kỳ đã đóng, user duyệt danh sách, rồi mới deploy. Quyết định nằm ở Rill để phase 15. Hai lỗi số đã có session khác sửa thì không làm lại.

## Các bước

1. Kiểm cơ chế tạo view serving cho model mới (`scripts/provisioning/bootstrap_serving_views.py`, asset `serving.build_serving_db`) và điều kiện dừng Metabase khi tạo view (hội đồng data-architect E10). Ghi quy trình vào runbook.
2. Viết `fact_revenue_events` + test dbt (unique khoá sự kiện; tổng `sale` theo ngày = tổng `net_revenue` của `fact_orders` cùng bộ lọc; tổng `return` = `fact_order_returns`).
3. Gate M trên shadow: golden các bảng public hiện có không đổi; `dbt_inventory.py` chỉ thêm một relation.
4. Registry: preset, tham số, ba chỉ tiêu mới; compiler xử lý `vat_mode` và trục; validator kiểm hồ sơ.
5. Golden: với hồ sơ FJ, mọi card Weekly Pulse vẫn ra cùng SQL và cùng số (chạy lại harness phase 05 trên `as_of` của 4 chu kỳ đã đóng); với hồ sơ thử "Như Sapo", `net_sales` = tổng `total_amount`.
6. Deploy dbt theo runbook "Refactor deploys" (giờ user duyệt), tạo view serving trong khung có dừng Metabase, **ngay sau** `metabase_cold_backup.sh pre-deploy`.
7. Áp từng quyết định đổi số đã duyệt như mục trên (gate S, danh sách đổi, user duyệt, deploy riêng).

## Files

- Tạo: `transformation/models/core/marts/sales/fact_revenue_events.sql`, khai báo + test trong `_core__models.yml` (hoặc file yml của thư mục), `analytics/registry/presets/{nhu_sapo,theo_ke_toan}.yml`, `analytics/registry/semantic/revenue_events.yml`.
- Sửa: `analytics/registry/metrics/sales.yml`, `analytics/compiler/sql.py`, `analytics/compiler/validate.py`, `analytics/schema/tenant-profile.schema.json`, `tenants/fine_japan/analytics/profile.yml`, `scripts/checks/public_models.yaml` (thêm bảng mới sau khi build), tài liệu ở đầu file.

## Verification

- Gate M sạch cho model mới (bảng cũ không đổi một con số).
- Harness: hồ sơ FJ cho 30/30 card khớp trên 4 `as_of` của thí điểm.
- Test dbt của `fact_revenue_events` xanh; đối soát tổng với `fact_orders` và `fact_order_returns` bằng 0 lệch.
- Validator từ chối hồ sơ thiếu tham số và hồ sơ chọn `delivered` khi thiếu khả năng.
- Mỗi quyết định đổi số: có gate S, danh sách đổi đã duyệt, deploy riêng.
- Nightly sau deploy xanh; 76 serving view cũ còn đủ, có thêm view mới.

## Đổi số?

**Có, chỉ với các quyết định ở phase 00 đã được user duyệt**, mỗi cái một deploy. Model mới và preset không đổi số FJ.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Tạo view mới cần dừng Metabase | Cao × Thấp | Gộp vào khung dừng của bản sao nguội; ngoài giờ cao điểm |
| `delivered_at` của đơn sàn thiếu (độ phủ thấp) | Trung bình × Trung bình | Đo độ phủ ở bước 2; `delivered_net_sales` có `coverage_metric`; preset "Theo kế toán" không chọn được khi khả năng thiếu |
| Người dùng nhầm `net_revenue` mới với nhãn "Net Revenue" cũ | Trung bình × Trung bình | Nhãn tiếng Việt tách bạch ("Doanh thu bán hàng (trước hoàn)" / "Doanh thu thuần"), chú giải sinh từ registry |

## Rollback

Revert commit registry/compiler. Model mới: revert commit dbt theo runbook, xoá view serving `fact_revenue_events` trong khung có dừng Metabase, xoá thư mục rolling của nó. Quyết định đổi số: revert commit riêng của quyết định đó.
