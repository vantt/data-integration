---
phase: 7
title: "Chuyển cột mart sang bộ máy, giữ đường SQL cũ sau var 30 ngày"
status: pending
priority: P2
effort: "0.5d công + 30 ngày theo dõi"
dependencies: [6]
---

# Phase 7: Chuyển cột mart

> **Yêu cầu bắt buộc của user (13/10/2026): làm tới đâu, thiết kế và tài liệu hoá chi tiết tới đó.** Tài liệu đi cùng commit với code.
>
> **Tài liệu phải cập nhật trong phase này:** `transformation/docs/TAXONOMY.md` mục `customer_type`, `is_us_gift_recipient` ("Đã là dữ liệu qua bộ máy từ <ngày>; đường SQL cũ còn sau biến tới <ngày + 30>"), bảng tổng quan §3 (cột "Loại" của `customer_type` thành "Dữ liệu (bộ máy)"); `docs/architecture/taxonomy-engine.md` (trạng thái, cách rollback bằng biến); `docs/architecture/modules.md` §9 (bộ máy đang cấp `customer_type`) và §10 (logic hook CROSSBORDER: luật ở seed tenant, SQL cũ còn sau biến).

## Mục tiêu

Đổi mặc định `taxonomy_engine_customer_type` thành `true`: `dim_customers`, `fact_orders`, `int_customer_benchmarks` đọc `lbl_*`. Đường SQL cũ vẫn nằm trong code để quay lại bằng một dòng trong 30 ngày.

## Điều kiện vào phase

- Phase 6 đủ 14 đêm đạt, không reset quá một lần, thời gian và RAM trong ngưỡng.
- Nightly prod đang xanh (quy tắc đóng băng).

## Files

- Modify: `transformation/dbt_project.yml` — `taxonomy_engine_customer_type: true`, comment ghi ngày hết hạn đường cũ (ngày deploy + 30).
- Modify: tài liệu ở đầu file (gồm tài liệu trạng thái từ phase 6).

## Các bước

1. Rebase lên `main`; kiểm ba file mart không có commit mới trên `main` ngoài nhánh.
2. Đổi biến; chạy `gate.sh S --allow-code-change` (compiled SQL ba model đổi; phụ thuộc mới `lbl_*`). Kết quả phải giống gate bộ máy bật ở phase 4: golden 83/83 0 khác biệt, full-refresh, lake trống pass.
3. Kiểm thêm trên lake-B: số dòng `is_us_gift_recipient IS NULL` của `dim_customers` bằng baseline; số dòng `mart_customer_action_queue`, `mart_customer_sku_action_queue` bằng baseline (golden đã bao gồm, ghi số cụ thể vào commit message).
4. Deploy theo runbook, ngoài 02:30–04:00. Sau start: `instigator_state.py diff`; chạy một realtime job; kiểm `dim_customers` có phân bố `customer_type` bằng số nền phase 6.
5. Theo dõi nightly kế tiếp theo runbook bước 7.
6. **30 ngày theo dõi:** mỗi sáng tiếp tục đọc `monitor_taxonomy_parity_log` (bản sao khối cũ vẫn so với bộ máy) và trạng thái nightly. Mỗi sự cố quy cho bộ máy (nightly đỏ do bộ máy, khác biệt đối chiếu, số mart sai) ghi vào nhật ký cuối file. Sự cố thứ nhất: rollback ngay bằng biến (mục Rollback), điều tra, chỉ bật lại sau khi có bản sửa đi qua gate. Sự cố thứ hai trong 30 ngày: điều kiện dừng 5, giữ biến `false` và quay về chế độ chạy song song hoặc phương án macro.

## Verification

- Gate S `--allow-code-change`: golden 83/83 0 khác biệt.
- Sau deploy: nightly xanh, `row_trend_checks` trong ngưỡng, `instigator_state` không đổi, phân bố `customer_type` và số NULL của `is_us_gift_recipient` bằng số nền.
- Sau 30 ngày: không quá một sự cố; log đối chiếu 0 khác biệt mọi ngày.

## Đổi số?

**Không.** Gate chứng minh 0 khác biệt; 30 ngày đối chiếu tiếp tục giám sát.

## Rollback

Đổi `taxonomy_engine_customer_type` về `false` (một commit một dòng), deploy theo runbook (đổi biến vẫn đổi compiled SQL nên vẫn dừng container). Đường cũ đã chứng minh 14 đêm, chỉ cần `gate.sh M` trên commit rollback để chắc không lẫn thay đổi khác. Hoặc `git revert` commit của phase này theo runbook.

## Rủi ro

| Rủi ro | Giảm thiểu |
|---|---|
| Lỗi build `lbl_*` giờ làm SKIP ba mart | Test `error` chỉ cho tính duy nhất/phủ đủ/nhãn hợp lệ, đã xanh 14 đêm; rollback một dòng |
| Hotfix trên `main` sửa SQL cũ trong 30 ngày mà không sửa luật | Inventory báo `WARN changed`; quy tắc trong `AGENTS.md`: trong 30 ngày, sửa logic `customer_type` phải sửa cả seed luật và bản sao trong monitor |

## Effort

0.5 ngày công, cộng khoảng 5 phút mỗi sáng trong 30 ngày.

## Nhật ký sự cố 30 ngày

| Ngày | Mô tả | Quy cho bộ máy? | Xử lý |
|---|---|---|---|
| | | | |
