---
phase: 14
title: "Chuyển dần report định kỳ còn lại từ Metabase sang Evidence: chạy song song, so số, rồi tắt bản Metabase"
status: pending
priority: P2
effort: "5d (lặp theo từng report, kéo dài theo chu kỳ so số)"
dependencies: [5, 10, 12]
---

# Phase 14: Report định kỳ sang Evidence

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Trước khi code: mỗi report cập nhật bảng trạng thái chuyển đổi trong `analytics/README.md` (đang song song / đã chuyển / bản Metabase đã lưu trữ). Trong lúc làm: playbook, catalog và bảng trạng thái đổi cùng commit với spec.
>
> **Tài liệu phải cập nhật trong phase này:** `analytics/README.md` (bảng trạng thái chuyển đổi); playbook của từng report trong `docs/analytics-handbook/playbooks/` (bản chính là Evidence, link mới); blueprint Metabase cũ ghi banner "thay bởi trang Evidence `<link>`"; `docs/analytics-handbook/README.md`, `collection_registry.yml`; `evidence/README.md` (trang legacy còn lại).

## Mục tiêu

User định chuyển dần report định kỳ, ít thay đổi từ Metabase sang Evidence (quyết định 3). Mỗi report đi theo cùng một vòng: spec v2 theo bản đang chạy → render Evidence → chạy song song → so số → chuyển người dùng → tắt bản Metabase giữ id và link.

## Danh sách (catalog `engine: evidence`)

| Report | Mốc hiện có | Ghi chú |
|---|---|---|
| EXE-W Nhịp tuần | Weekly Pulse (đã đạt ở phase 05) | Chỉ còn bước tắt bản Metabase và trang Evidence cũ |
| EXE-M Scorecard tháng | `ceo_monthly_scorecard` | |
| SAL-M, SAL-W | `sales_monthly_review` + `sales_ops_monthly_summary`; `sales_ops_weekly_review` + `social_commerce_ops` (phần chuẩn) | Gộp cụm trùng #30 |
| MKT-M, MKT-W | `marketing_roi` + `marketing_monthly_analysis`; `marketing_weekly_tracker` + khối khuyến mãi `sales_promotion_analysis` | Cần `ad_spend`; thiếu thì khối hiện "–" kèm lý do |
| FIN-M | `finance_pl` + `finance_cost_ledger` + `channel_profitability_monthly` + `channel_p_l_deep_dive` + `order_profitability_all` + `product_profitability` + `finance_return_impact` | Gộp cụm trùng #6; khu vực `tai-chinh`, chi phí |
| FIN-W | `finance_cashflow` (Metabase) + trang Evidence `finance-cashflow` + `finance_cashflow_budget` | Trang legacy Evidence được thay |
| INV-M, INV-W | `product_health_overview` + phần SKU `shopee_channel_economics`; `product_performance_velocity` + `inventory_stock_health` | |
| LOG-M, LOG-W | `logistics_shipping`; khối vận hành `finance_return_impact` + `order_lifecycle_transitions` | Gộp cụm trùng #36 |
| CUS-M, CUS-W | `customer_retention_cohorts` + 2 blueprint cohort + `customer_profitability`; `customer_intelligence` | Gộp cụm trùng #21 |

Thứ tự đề xuất: EXE-W (tắt bản cũ), FIN-W (bỏ trang legacy), EXE-M, rồi theo mức dùng (hỏi user).

## Vòng chuyển cho mỗi report

1. **Spec theo bản đang chạy** (capture-first, chỉ đọc), ánh xạ `card_id` ↔ question cũ. Report gộp nhiều dashboard: mỗi card mới ghi rõ mốc từ dashboard nào.
2. **Render + build** vào khu vực chức năng; thẻ chi phí chỉ ở khu vực có quyền.
3. **So số bằng harness:** backtest 4 kỳ đã đóng của nhịp report (tuần hoặc tháng), có ranh giới tháng/quý, rồi **1 kỳ chạy thật** khớp. (Weekly Pulse cần 4 chu kỳ thật vì là thí điểm; các report sau dùng backtest vì kỳ đã đóng không đổi và harness chạy được `as_of` lịch sử.)
4. **Chuyển người dùng:** tin tóm tắt (nếu report có lịch) chuyển sang link Evidence; báo người dùng chính, ghi đồng ý.
5. **Tắt bản Metabase giữ id:** kiểm kê phụ thuộc (phase 07); adopt dashboard cũ (phase 12) rồi deploy một text card đầu dashboard "Report đã chuyển tới <link Evidence>" (bản sao nguội → `--plan` → duyệt → `--apply`); subscription Metabase của report đó được user quyết tắt hay giữ (thay bằng tin tóm tắt). Sau 90 ngày, archive dashboard (không xoá), một lần deploy riêng có kế hoạch.
6. Trang Evidence legacy tương ứng (`ceo-weekly-pulse`, `finance-cashflow`) gỡ khỏi khu vực `legacy` khi bản mới đã chuyển; `theme-mvp` (dữ liệu giả) gỡ sau khi user xác nhận; khi khu vực `legacy` trống thì bỏ khu vực và source "cả bảng" cũ trong `evidence/sources/datalake/`.

## Files

- Tạo: `analytics/specs/{exe_m,sal_m,sal_w,mkt_m,mkt_w,fin_m,fin_w,inv_m,inv_w,log_m,log_w,cus_m,cus_w}.yml`, trang/source sinh ra trong `evidence/areas/*`, baseline harness cho từng report.
- Sửa: `analytics/catalog/catalog.yml` (trạng thái), `tenants/fine_japan/analytics/{profile.yml,adopt/*.yml}`, tài liệu ở đầu file.
- Xoá (khi tới bước 6): `evidence/pages/{ceo-weekly-pulse,finance-cashflow,theme-mvp}`, source cũ trong `evidence/sources/datalake/` không còn trang nào dùng.

## Verification

- Mỗi report: file so số của 4 kỳ backtest + 1 kỳ thật đều `match` trên mọi card có mốc.
- Text card chuyển hướng: id dashboard không đổi; subscription còn trỏ đúng (hoặc đã tắt theo quyết định user); `--plan` lần hai `noop`.
- Không object Metabase nào ngoài danh sách bị đổi (kiểm kê trước/sau).
- Build Evidence sau nightly vẫn xong trước 05:30 khi thêm khu vực (đo thời gian, chỉnh timeout).

## Đổi số?

Không. Report gộp có thẻ mới không có mốc thì ghi rõ là thẻ mới, không gọi là đổi số.

## Rủi ro

| Rủi ro | Khả năng × Tác động | Giảm thiểu |
|---|---|---|
| Report định kỳ cần tương tác (bộ lọc tuỳ ý) | Trung bình × Trung bình | Ở lại Metabase (đổi `engine` trong catalog; spec không đổi) |
| Thời gian build tăng theo số khu vực | Trung bình × Thấp | Đo mỗi lần thêm; build tuần tự có timeout; cảnh báo khi quá hạn |
| Người dùng mất subscription email quen thuộc | Trung bình × Trung bình | Tin tóm tắt thay thế; giữ subscription nếu user muốn |

## Rollback

Từng report độc lập: bỏ text card bằng `rollback <deploy_id>`; người dùng quay lại dashboard Metabase (id không đổi, chưa archive trong 90 ngày); trang Evidence mới gỡ khỏi khu vực. Revert commit spec.
