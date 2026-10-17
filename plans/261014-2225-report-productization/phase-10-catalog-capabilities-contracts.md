---
phase: 10
title: "Catalog chuẩn đầy đủ (19 + 2), mở khoá theo khả năng 3 mức, registry toàn bộ, metrics.md sinh ra, contract: enforced cho mart registry dựa vào"
status: pending
priority: P2
effort: "4d"
dependencies: [9, "plan pack mechanism"]
---

# Phase 10: Catalog, khả năng dữ liệu, registry đầy đủ, contract

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: ghi lưới 7 × 3, catalog và luật mở khoá vào `analytics/README.md` và `docs/architecture/modules.md`; ghi danh sách mart có contract vào §7/§11. Trong lúc làm: tài liệu đi cùng commit.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md` (catalog, khả năng, cách thêm report chuẩn); `docs/architecture/modules.md` (§7 Core: contract; §11 Serving; mục Analytics); `docs/analytics-handbook/semantic/metrics.md` (**trở thành file sinh ra**, banner "generated", CI so diff); xoá `metric-registry.md` tạm của phase 01; `docs/analytics-handbook/README.md` và `AGENTS.md` của handbook (registry là nguồn chuẩn); `transformation/AGENTS.md` (mart có contract).

## Mục tiêu

Bắt đầu chỉ sau khi thí điểm đạt (thiết kế §8). Biến catalog một mục thành catalog chuẩn đầy đủ, mở khoá theo tập khả năng, đưa mọi định nghĩa còn lại vào registry, và cưỡng chế cột của các mart registry dựa vào (quyết định 9).

## Phụ thuộc vào plan cơ chế pack

Plan `plans/261014-2225-pack-mechanism/` (đang viết) cung cấp: biến `enabled_packs`, macro `pack_ref`, khai báo "connector cung cấp gì", và lớp ánh xạ nhãn → mã chuẩn sinh cột `*_std`. Phase này **đọc** các thứ đó, không tự làm. Bước 1 đối chiếu tên thật của các giao diện trên với plan pack đã chốt; tên trong file này là tên dự kiến [UNVERIFIED cho tới khi plan pack xong].

## Thiết kế

### Catalog (`analytics/catalog/catalog.yml`)

Mỗi report: `id`, `title`, `cell` + `primary_cell` (đúng một ô chính), `question`, `metrics` (validator suy ra từ spec), `requires`/`enhances` (**suy ra** từ hợp khả năng của metric, không gõ tay; chỉ được khai báo thêm), `kpi_tiles`, `spec`, `engine ∈ {evidence, metabase}`, `area`, `status ∈ {planned, pilot, active, deprecated}`, `default_install` (bộ ngày đầu).

19 report chuẩn + 2 tiện ích theo đề xuất của trưởng BI (hội đồng BI §(c)), hai ô cố ý để trống (Điều hành × ngày: trang chủ chủ shop; Marketing × ngày). Engine theo nhịp (quyết định 3):

| Engine | Report |
|---|---|
| `evidence` (định kỳ, build sau nightly) | EXE-M, EXE-W, SAL-M, SAL-W, MKT-M, MKT-W, FIN-M, FIN-W, INV-M, INV-W, LOG-M, LOG-W, CUS-M, CUS-W |
| `metabase` (tương tác, tác nghiệp) | SAL-D, FIN-D, INV-D, LOG-D, CUS-D, UTL-1 Sức khoẻ dữ liệu, UTL-2 Tra cứu và đối soát đơn với Sapo |

Phần riêng FJ không vào catalog chuẩn (sang overlay FJ ở phase 12): `finance_services_revenue`, `b2b_sales_daily`, `b2b_orders_tracking`, Rill `orders_b2b_ops`, `us_crossborder_operations`, `welcome_landing`. Explorer chuyển thành phân tích tự do trên Rill, không là report. `crm_outreach_effort_weekly` chờ chuẩn hoá CRM. Bộ ngày đầu (`default_install`) theo câu hỏi mở 7 của plan.

### Khả năng dữ liệu 3 mức

| Mức | Nguồn | Dùng để |
|---|---|---|
| Khai báo | Khai báo connector của plan pack | Lúc cài: report nào đưa vào |
| Bật | `enabled_packs` | Lúc cài |
| Quan sát được | Model dbt mới `mart_capabilities` (`capability, declared, enabled, coverage_pct, last_seen_at`; ví dụ % đơn có giá vốn, % đơn có `delivered_at`, độ tươi chi phí quảng cáo) | Lúc hiển thị: dưới ngưỡng → thẻ hiện "–" kèm "cần dữ liệu X" |

Danh sách khả năng: `orders, order_lines, products, customers, staff, stores, promotions, targets, inventory_snapshot, fulfillment_events, return_events, marketplace_settlement, cash_settlement, unit_cost, shipping_cost, ledger, ad_spend, crm_contacts, care_tasks` (hội đồng BI §(c)).

### Registry đầy đủ

Đưa mọi định nghĩa còn lại của `metrics.md` (~56) và measure Rill (~53) vào registry theo các quyết định ở phase 00 (đã áp ở phase 09). Chiều chuẩn: khi plan pack có `order_scope_std`, `channel_std`…, ràng buộc chuẩn của gate `in_sales_scope` chuyển sang cột chuẩn; hồ sơ FJ vẫn giữ ràng buộc `scope_sales` cho tới khi so số cho thấy hai cột cho cùng tập đơn (không đổi số). Metric dùng `*_std` có `status: preview` cho tới khi có doanh nghiệp thứ hai (hội đồng data-architect §5.1).

### `contract: enforced` (quyết định 9)

Chỉ cho các mart mà registry hoặc report chuẩn tham chiếu (danh sách sinh từ registry, dự kiến: `fact_orders`, `fact_order_economics`, `fact_order_returns`, `fact_revenue_events`, `fact_targets`, `dim_customers`, `dim_channels`, cộng mart mà catalog dùng). Khai báo đủ cột và kiểu trong yml; `access: public`. Validator đổi kiểm cột từ "cảnh báo" sang **lỗi cứng**, đọc danh sách cột từ contract. Mart còn lại để Đợt 3.

## Các bước

1. Đối chiếu giao diện plan pack; ghi tên thật vào `analytics/README.md`.
2. Catalog đầy đủ (mục `planned` cho report chưa có spec), schema mở rộng, validator suy `requires`.
3. Registry đầy đủ; sinh `metrics.md`; so nội dung với bản cũ theo bảng phase 00 (mọi định nghĩa cũ có chỗ đi hoặc có lý do bỏ).
4. `mart_capabilities` + contract: chạy spike `dbt parse`/`dbt build` có contract trên shadow trước (dbt-duckdb 1.10.1, model external/rolling) để biết contract có áp được cho model ghi parquet không [UNVERIFIED]; nếu không áp được, dùng test schema (cột + kiểu) mức error thay thế và ghi lý do.
5. Gate M trên shadow (contract và model mới không đổi số); deploy theo runbook, tạo view `mart_capabilities` trong khung dừng Metabase ngay sau bản sao nguội.

## Files

- Sửa: `analytics/catalog/catalog.yml`, `analytics/schema/catalog.schema.json`, `analytics/registry/**`, `analytics/compiler/validate.py`, `analytics/renderers/docs.py`.
- Tạo: `transformation/models/core/marts/mart_capabilities.sql` (vị trí chính xác theo `model_buckets.yaml`), yml contract cho các mart trong danh sách.
- Sinh: `docs/analytics-handbook/semantic/metrics.md`, `glossary.md`. Xoá: `metric-registry.md`.
- Sửa: `scripts/checks/public_models.yaml` (thêm `mart_capabilities`), tài liệu ở đầu file.

## Verification

- Validator: mọi cột registry có trong contract; `requires` của report ⊇ hợp `requires` metric; không metric `cost_sensitive` nào thiếu cờ; `metrics.md` sinh lại không diff; mã `*_std` trong bộ lọc thuộc bộ mã chuẩn hiện hành.
- Gate M sạch: golden bảng public cũ không đổi; inventory chỉ thêm `mart_capabilities` và config contract.
- Nightly sau deploy xanh; cố ý đổi kiểu một cột trên shadow → `dbt build` dừng đúng (contract có hiệu lực).
- Harness Weekly Pulse vẫn 30/30 trên một `as_of` mới.

## Đổi số?

Không. Hợp nhất định nghĩa đổi số đã được xử lý riêng ở phase 09.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Contract làm nightly dừng | Thấp × Cao | Gate M; chỉ mart trong danh sách; rollback gỡ config |
| Plan pack đổi tên giao diện | Trung bình × Thấp | Bước 1 đối chiếu |
| Catalog mang khuôn FJ | Trung bình × Trung bình | `status: preview` cho metric dùng `*_std`; thử trên khách thứ hai trước khi gọi là ổn định |

## Rollback

Revert commit registry/catalog. Contract: revert commit yml theo runbook (gỡ `contract`), không đổi dữ liệu. `mart_capabilities`: revert, xoá view trong khung dừng Metabase.
