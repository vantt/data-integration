---
phase: 12
title: "Report tác nghiệp trên Metabase (SAL-D, FIN-D, INV-D, LOG-D, CUS-D), chuyển giao FJ ghi đè giữ id, gộp bản trùng, phần riêng FJ sang overlay"
status: pending
priority: P2
effort: "4d"
dependencies: [11]
---

# Phase 12: Report tác nghiệp và chuyển giao FJ giữ id

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: viết quy trình "nhận nuôi tại chỗ" (adopt) vào `.skills/metabase-automation/STRATEGY.md` và runbook "Report deploys (Metabase)". Trong lúc làm: mỗi dashboard chuyển giao cập nhật bảng trạng thái ngay.
>
> **Tài liệu phải cập nhật trong phase này:** `docs/operations/deployment.md` (mục adopt và cut-over); `.skills/metabase-automation/STRATEGY.md`; `docs/analytics-handbook/README.md` và `collection_registry.yml` (dashboard nào sinh từ spec, dashboard nào legacy, bản trùng nào đã lưu trữ); blueprint cũ của dashboard đã chuyển giao ghi banner "thay bởi spec `<id>`"; `tenants/fine_japan/analytics/README.md` (report riêng FJ); `docs/architecture/modules.md`.

## Mục tiêu

Hiện thực 5 report tác nghiệp `engine: metabase` của catalog, chuyển người dùng FJ sang bản sinh từ spec **bằng cách ghi đè vào dashboard/card cũ để giữ id** (quyết định 5), gộp các cụm trùng và đưa phần riêng FJ sang overlay.

## Cách chuyển giao (quyết định 5, hội đồng ops §2.2)

1. **Kiểm kê phụ thuộc** (script phase 07, chỉ đọc) của dashboard cũ: subscription, alert, câu hỏi dựa trên câu hỏi, link, quyền.
2. **Chạy song song** bản spec trong collection thí điểm ẩn (deployer, có bản sao nguội), so số tự động bằng harness theo `as_of` (report ngày: 7 ngày đã đóng liên tiếp khớp; có bộ lọc thì thêm ít nhất 3 tổ hợp lọc: một ngày đã đóng, ngày đang chạy cùng thời điểm, ranh giới tháng).
3. **Adopt:** lệnh `deploy_report.js --adopt <dashboard_id> --map <file ánh xạ>` gắn `spec_key` vào dashboard và từng card cũ (ánh xạ card cũ → `card_id`, do người duyệt xác nhận), ghi vào sổ deploy, **không đổi nội dung**. Diễn tập trên Metabase bóng trước.
4. **Cut-over:** `--plan` (chỉ `update` SQL/viz của card đã adopt, không `create` dashboard mới) → user duyệt → bản sao nguội → `--apply`. Id dashboard/card giữ nguyên, nên subscription, alert, bookmark, link, câu hỏi phái sinh không gãy.
5. Xoá bản thí điểm song song (archive). **Không bao giờ xoá** object của người dùng; lưu trữ ≥ 90 ngày.

## Phạm vi

| Report catalog | Dashboard FJ hiện có làm mốc / đích adopt (xác nhận bằng kiểm kê) |
|---|---|
| SAL-D Bán hàng hôm nay và chốt ca | Cụm 4 biến thể `sales_daily_operation`, `yesterday_operation`, `sales_daily_retail`, `sales_today_operation`: adopt dashboard được dùng nhiều nhất (số lượt xem lấy từ API nếu 0.62.3 có, nếu không hỏi user), 3 bản còn lại thêm text card "đã chuyển tới …" rồi archive sau 90 ngày |
| FIN-D Đối soát tiền về | `finance_accounting_recon` + phần thực nhận của `shopee_channel_economics` |
| INV-D Hàng sắp hết hôm nay | `inventory_stock_health` (khối OOS) + `mart_product_action_queue` |
| LOG-D Trung tâm xử lý đơn | `logistics_operations` |
| CUS-D Hàng đợi chăm sóc | `customer_daily_action_queue` |

Gộp các cụm trùng còn lại theo kiểm kê handbook (#6, #21, #30, #33, #36, #44): mỗi cụm chọn bản giữ lại; bản còn lại thêm text card trỏ sang rồi archive sau 90 ngày. Cụm nào là report định kỳ thì làm cùng phase 14.

Phần riêng FJ (`finance_services_revenue`, `b2b_sales_daily`, `b2b_orders_tracking`, `us_crossborder_operations`, `welcome_landing`): **không viết lại**; ghi vào `tenants/fine_japan/analytics/overlay.yml` mục `legacy_dashboards` (giữ blueprint, ngoài sổ deploy chuẩn) để catalog chuẩn không đụng tới. Viết lại thành spec riêng FJ chỉ khi user yêu cầu.

## Files

- Tạo: `analytics/specs/{sal_d,fin_d,inv_d,log_d,cus_d}.yml`, file ánh xạ adopt `tenants/fine_japan/analytics/adopt/<report>.yml`.
- Sửa: `.skills/metabase-automation/scripts/deploy_report.js` và `lib/ledger.js` (chế độ `--adopt`), `analytics/catalog/catalog.yml`, `tenants/fine_japan/analytics/overlay.yml`, tài liệu ở đầu file.

## Verification

- Harness: mỗi report khớp mốc theo tiêu chí ở bước 2 trước khi cut-over.
- Sau adopt: `--plan` = `noop` (adopt không đổi nội dung).
- Sau cut-over: id dashboard/card giống trước (so kiểm kê trước/sau); subscription/alert vẫn trỏ đúng id; `--plan` lần hai = `noop`; không object nào ngoài danh sách bị đổi.
- Rollback cut-over đã diễn tập thành công trên Metabase bóng cho ít nhất một report.

## Đổi số?

Không. Cut-over chỉ khi số khớp; khác biệt nào cũng phải là quyết định đã duyệt ở phase 00/09.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Ánh xạ adopt sai card | Trung bình × Cao | Người duyệt xác nhận file ánh xạ; diễn tập trên bóng; drift guard |
| Người dùng đang sửa dashboard trong lúc cut-over | Thấp × Trung bình | Khung cấm; drift guard từ chối ghi đè chỉnh sửa mới |
| Bản trùng bị archive mà còn người dùng | Trung bình × Thấp | Text card trỏ sang 90 ngày trước khi archive; kiểm kê subscription |

## Rollback

`rollback <deploy_id>` cho lần cut-over (PUT lại SQL/viz cũ từ snapshot, id không đổi); nếu cần, bản sao H2 nguội. Bỏ adopt: xoá `spec_key` khỏi sổ và marker (một lần deploy riêng có kế hoạch).
