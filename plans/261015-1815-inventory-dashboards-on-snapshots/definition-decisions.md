---
title: "Sổ quyết định: dashboard tồn kho trên ảnh chụp hằng đêm"
status: "đã chốt (7/7)"
updated: 2026-10-15
---

# Sổ quyết định: dashboard tồn kho trên ảnh chụp hằng đêm

Mỗi dòng là **một** chỗ đổi định nghĩa hoặc đổi số, có số mẫu đo. Người làm plan không tự chọn. Cùng quy ước với [sổ quyết định của report-productization](../261014-2225-report-productization/definition-decisions.md).

**Nguồn số mẫu:** truy vấn tổng hợp chỉ đọc ngày 15/10/2026 trên parquet rolling mới nhất (DuckDB trong container `data_platform`). Ảnh chụp hằng đêm **chưa có** (D1 của plan lịch sử chưa deploy), nên cột "sau" là **ước lượng**: lấy mọi cặp (variant, kho) trong `fact_inventory_snapshot` hiện tại, tức là mọi cặp có mặt nhưng số còn cũ. Phase 3 sẽ thay các số này bằng số thật đo trên shadow (lake-A so với lake-B) trước khi user duyệt lần cuối.

**Trạng thái:** `chờ user` → `đã chốt: <lựa chọn>, <ngày>` → `đã áp: <commit>`.

**Thứ tự cần chốt:** QĐ-TK-01 đến 05 ảnh hưởng SQL, nên phải chốt trước phase 1. QĐ-TK-06 và 07 chốt trước phase 3.

| # | Chỗ đổi | Số mẫu (15/10/2026) | Lựa chọn | Đề xuất | Đổi số? | Trạng thái |
|---|---|---|---|---|---|---|
| QĐ-TK-01 | **Nguồn gốc của `on_hand`** trên dashboard | `available = on_hand − committed` ở 2.052/2.052 dòng ảnh chụp. 71 cặp có hàng (8.534 đơn vị) không có dòng sổ kho nào. 25 cặp lệch sổ kho, cả 25 do snapshot cũ (sổ kho có biến động sau ngày snapshot). Tổng `on_hand` của sổ kho (`is_current`) là 221.976; của snapshot là 218.678 | (a) Ảnh chụp là gốc, sổ kho dùng để đối soát. (b) Sổ kho là gốc, các trường còn lại lấy từ ảnh chụp. (c) Lấy số mới hơn giữa hai nguồn | (a): phủ mọi cặp, giữ đẳng thức `available`, một nguồn cho một thời điểm. (b) làm mất 71 cặp và phá đẳng thức. (c) làm hai cột trên cùng một dòng đến từ hai thời điểm khác nhau | **Có**, mọi card tồn kho (xem phase 3) | đã chốt: (a), 15/10/2026 |
| QĐ-TK-02 | **Dòng trước ngày chụp đầu tiên** trong `fact_inventory_snapshot` (2.052 dòng hiện có, `snapshot_date` = ngày sửa sản phẩm cuối cùng, 2023–09/2026) | Trong 90 ngày gần nhất chỉ có 3 dòng, 1 ngày. 2023: 1.542 dòng; 2024: 315; 2025: 63; 2026: 132 | (a) Bỏ: bảng chỉ còn các ngày đã chụp; lịch sử `on_hand` trước đó xem ở `fact_inventory_balance`. (b) Giữ, gắn cờ nguồn cũ. (c) Lấp `on_hand` từ sổ kho cho các ngày trước khi chụp, các trường khác để NULL | (a): các dòng cũ không phải tồn của ngày đó, và (b) sẽ làm card xu hướng có điểm sai. (c) là tính năng mới, có thể làm sau qua plan report | **Có**: số dòng giảm ở ngày cũ; card xu hướng bắt đầu từ ngày chụp đầu tiên | đã chốt: (a), 15/10/2026 |
| QĐ-TK-03 | **Card "OOS SKUs" và "Danh Sách SKU OOS"** (dashboard Product Inventory & Stock Health) đếm SKU có **bất kỳ** kho nào `on_hand ≤ 0`, không lọc SKU còn kinh doanh | Hôm nay 1. Khi mọi cặp có mặt, giữ định nghĩa: **684 = mọi SKU**. Theo (b): 82. Theo (c): 43 | (a) Giữ. (b) SKU có kho `on_hand ≤ 0` **và** có bán trong 90 ngày (`NOT is_dead_stock`). (c) SKU có tổng `on_hand` trên các kho đang lọc ≤ 0 **và** có bán trong 90 ngày | (c): khi lọc một kho thì (c) bằng (b); khi không lọc kho thì SKU còn hàng ở kho khác không bị tính là hết. Chỉ sửa SQL card, không thêm cột dbt | **Có**, 2 card | đã chốt: (c), 15/10/2026 |
| QĐ-TK-04 | **"Tồn mới nhất" trong `mart_product_health`**: hiện lấy dòng mới nhất theo từng cặp (product, kho) | Sau khi chuyển, cặp bị xoá ở Sapo (không còn trong ảnh chụp) vẫn giữ số tồn cũ mãi mãi. Hiện 99 sản phẩm, tổng giá trị tồn 1.025,1 tr | (a) Giữ theo cặp. (b) Lấy ngày chụp mới nhất chung (`snapshot_date = MAX`) | (b): đúng nghĩa "hôm nay", bỏ được cặp đã xoá | **Có**: `mart_product_health` → `mart_product_action_queue`, `mart_deadstock_target_queue`, CRM | đã chốt: (b), 15/10/2026 |
| QĐ-TK-05 | **`is_oos` của `mart_product_health` = có kho nào hết** (`MAX(is_oos)`, `mart_product_health.sql:102`), làm `oos_risk` và hành động `RESTOCK_NOW` tính cả SKU còn hàng ở kho khác | Hiện 99/99 sản phẩm có `is_oos = true`; `oos_risk` 7; `RESTOCK_NOW` 7 | (a) Giữ. (b) Hết hàng khi **tổng** `on_hand` của sản phẩm ≤ 0 | (b): một SKU còn hàng ở kho khác là chuyển kho, không phải nhập hàng. Có thể tách sang đợt sau nếu user muốn giữ phạm vi hẹp | (b): **có**, `is_oos`, `oos_risk`, số `RESTOCK_NOW`, card "SP rui ro het hang OOS RISK" và "RESTOCK NOW count" | đã chốt: (b), 15/10/2026 |
| QĐ-TK-06 | **Card xu hướng hàng chậm/tồn chết** áp tốc độ bán **hiện tại** cho mọi ngày trong quá khứ (`mart_inventory_health` nối với tháng bán gần nhất, `mart_inventory_health.sql:67-91`) | Trước đây không lộ ra vì xu hướng gần như rỗng; sau khi chuyển, card "Slow-Mover Value Trend 90 Ngày" sẽ có một điểm mỗi ngày | (a) Giữ, thêm chú thích "theo tốc độ bán hiện tại". (b) Dùng tốc độ bán của tháng tương ứng | (a): không đổi số; (b) đổi định nghĩa, để plan report làm sau nếu cần | (a): không. (b): có | đã chốt: (a), 15/10/2026 |
| QĐ-TK-07 | **Ngưỡng và kênh cảnh báo đối soát** `on_hand` | Chưa có ảnh chụp để đo. Ước lượng tham khảo: trong 25 cặp lệch, 13 cặp vẫn lệch khi so với số dư sổ kho **cùng ngày** snapshot, tức khoảng 1% của 1.285 cặp so được | Ngưỡng: (a) cảnh báo khi số cặp `mismatch` ở ngày mới nhất > max(5, p95 của 7 đêm hiệu chỉnh). (b) Một số cố định do user chọn. Kênh: (x) chỉ asset check trong Dagster và card nguồn dữ liệu. (y) Thêm một dòng vào digest buổi sáng trên Lark | (a) + (x). Asset check mức warn không làm hỏng build | Không | đã chốt: (a) + (x), 15/10/2026 |

## Ghi nhận, không cần quyết định

- **Card "Chu kỳ báo cáo"** (3 tab của dashboard tồn kho) đang hiện `current_date` thay vì ngày của dữ liệu. Sẽ đổi sang `MAX(snapshot_date)`. Đây là sửa nhãn, không đổi số.
- **Giá trị tồn theo `mac`** (snapshot 1.025,1 tr với `on_hand > 0`) khác tổng `inventory_value` của sổ kho (1.539,0 tr với `is_current`). Phase 0 đo lại khi đã có ảnh chụp, và phase 3 ghi chênh lệch vào báo cáo đối soát để tham khảo. Công thức `stock_value_at_mac` giữ nguyên.
