# Thiết Kế Mô Hình Dữ Liệu Target (Mục Tiêu) Toàn Diện - V2

Tài liệu này là phiên bản nâng cấp, giải thích sâu về cơ chế Thời gian (Period), Định danh (Identity) và tính mở rộng dài hạn cho bảng `fact_targets`.

## 1. Triết Lý Cốt Lõi: "Unified Dimension Conformance"

Để hệ thống Target tồn tại lâu dài và "sống" chung được với dữ liệu Thực tế (Actuals), nguyên tắc vàng là: **Target và Actual phải dùng chung các Dimensions**.

Nếu `fact_orders` dùng `dim_date`, `dim_store`, `dim_product`, thì `fact_targets` cũng bắt buộc phải dùng chính các `dim` đó (hoặc tập hợp con của chúng).

## 2. Giải Mã Về Thời Gian (Time & Period)

### Câu hỏi lớn: Tại sao lại là "Ngày Đầu Tháng" (First Day of Month)?

Chúng ta **không nên** tạo thêm `dim_period` riêng biệt (ví dụ: bảng chứa `M01-2024`, `Q1-2024`) trừ khi thực sự cần thiết cho tài chính kế toán phức tạp.

**Lý do nên map Target vào `dim_date` thông qua "Ngày đầu kỳ" (Snapshot Date):**

1.  **Dễ dàng Join và Visualize trong BI (Metabase/PowerBI):**
    - Khi vẽ biểu đồ, trục hoành là `dim_date.month`.
    - Dữ liệu thực tế (`orders`) diễn ra ngày `2024-01-15`. Khi Group by Month -> BI tool tự động convert thành `2024-01-01` (đại diện cho tháng 1).
    - Dữ liệu Target lưu ngày `2024-01-01`.
    - => Hai dữ liệu này tự động "khớp" nhau trên biểu đồ mà không cần tính toán phức tạp.
2.  **Tính liên tục (Continuous Time):**
    - `dim_date` cho phép tính toán trượt (Rolling/Moving Average). Nếu lưu dạng text 'Jan-2024', engine không hiểu tháng 12/2023 liền trước tháng 1/2024.
3.  **Tại sao không phải Cuối tháng?**
    - Ngày cuối tháng thay đổi (28, 29, 30, 31). Code xử lý phức tạp (`LAST_DAY`, `EOMONTH`).
    - Ngày đầu tháng luôn là `01`. Tư duy lập trình "Month Start" chuẩn hơn.

### Cấu trúc Time trong bảng `fact_targets`:

| Column         | Type    | Value Example | Explanation                                                                             |
| :------------- | :------ | :------------ | :-------------------------------------------------------------------------------------- |
| `date_key`     | Integer | `20240101`    | FK trỏ tới `dim_date`. Đại diện cho **Toàn bộ Tháng 1/2024**.                           |
| `period_date`  | Date    | `2024-01-01`  | Giá trị Date thực tế để visualize.                                                      |
| `period_grain` | String  | `'month'`     | (Optional) Để sau này mở rộng nếu có Target theo Quý (`'quarter'`) hoặc Năm (`'year'`). |

---

## 3. Định Danh & Quản Lý Phiên Bản (Target Identity)

Một bản ghi Target "sống" cần nhiều hơn một cái hash `target_id`. Chúng ta cần quản lý việc: "Sửa lại target", "Target bản Draft", "Target chốt".

### Đề xuất cấu trúc Primary Key & Versioning:

Thay vì chỉ `target_id`, ta dùng bộ 3 cột định danh logic:

1.  **`target_code` (Semantic Key):** Định danh duy nhất cho **ngữ nghĩa** của target đó.
    - Format: `TGT-{YYYYMM}-{METRIC}-{SCOPE_HASH}`
    - Ví dụ: `TGT-202401-GMV-HN_STORE_01` (Chỉ tiêu GMV tháng 1 của Store HN1).
2.  **`version`:** Phiên bản của target.
    - Values: `v1` (Ban đầu), `v2` (Điều chỉnh giữa tháng), `v_final` (Chốt).
    - Hoặc đơn giản là số nguyên: `1, 2, 3`.
3.  **`is_active` (Cờ hiệu lực):** Chỉ lấy dòng `True` để báo cáo.

### Cấu trúc bảng `fact_targets` Hoàn Chỉnh (V2):

| Group          | Column Name    | Data Type | Description                                                                |
| :------------- | :------------- | :-------- | :------------------------------------------------------------------------- |
| **Identity**   | `target_key`   | String    | Surrogate Key (Hash MD5 của toàn bộ row) để DBT quản lý duplicate.         |
|                | `target_code`  | String    | Human-readable ID (VD: `TGT-202401-STORE01-GMV`). Dữ liệu này đi suốt đời. |
|                | `version`      | Integer   | Phiên bản (Mặc định `1`). Tăng lên khi upload lại đè lên Period cũ.        |
|                | `is_current`   | Boolean   | `True` nếu đây là bản target mới nhất cần dùng report.                     |
| **Time**       | `date_key`     | Integer   | `20240101` (FK `dim_date`).                                                |
|                | `period_type`  | String    | `'month'` (Mặc định), `'quarter'`, `'year'`.                               |
| **Dimensions** | `location_key` | String    | (FK) Default `'-1'`.                                                       |
|                | `staff_key`    | String    | (FK) Default `'-1'`.                                                       |
|                | `channel_key`  | String    | (FK) Default `'-1'`.                                                       |
|                | `product_key`  | String    | (FK) Default `'-1'`.                                                       |
| **Metrics**    | `metric_code`  | String    | `'gmv'`, `'profit'`, `'new_customers'`, `'aov'`.                           |
|                | `target_val`   | Decimal   | Giá trị mục tiêu.                                                          |
| **Metadata**   | `created_at`   | Timestamp | Thời điểm tạo/upload target này.                                           |
|                | `source`       | String    | `'google_sheet'`, `'excel_upload'`, `'system_gen'`.                        |
|                | `description`  | String    | Ghi chú (VD: "Mục tiêu đã điều chỉnh do Tết").                             |

## 4. Trả Lời Các Câu Hỏi Cụ Thể

### _"Mình có thể nhét rất nhiều target vào đúng không?"_

**ĐÚNG.** Đây là mô hình "Narrow and Long" (Hẹp về cột, Dài về dòng - EAV model biến thể).

- Bạn có thể thêm Metric mới (`metric_code` = 'churn_rate') -> Thêm dòng mới, không sửa cấu trúc bảng.
- Bạn có thể thêm Chiều mới -> Lúc đó mới cần thêm cột FK (ví dụ thêm `marketing_campaign_key`).

### _"Target ID có vẻ không đầy đủ lắm?"_

Đúng, MD5 thuần túy chỉ tốt cho máy.
Trong mô hình V2 trên, tôi đề xuất tách thành:

1.  **Technical Key (`target_key`)**: Để join/update.
2.  **Business Code (`target_code`)**: Để con người đọc và trace (VD: `TARGET_JAN24_STORE_A`).
3.  **Versioning**: Để lưu lịch sử thay đổi.

### _"Tại sao Period Date là ngày đầu tháng?"_

Như đã giải thích ở mục 2:

- Để **tận dụng `dim_date`** có sẵn.
- Để khớp với hàm `DATE_TRUNC('month', created_at)` của dữ liệu thực tế.
- Để biểu đồ Time Series liền mạch.
- Không dùng Chu kỳ (ví dụ string 'Cycle 1') vì nó biến trục thời gian thành trục Categories (Rời rạc), làm mất khả năng phân tích xu hướng (Trendline) tự nhiên của các tool BI.

## 5. Ví Dụ Dữ Liệu Demo (Dạng Bảng Phẳng)

| date_key | target_code   | version | is_current | location | staff | metric   | value  | desc               |
| :------- | :------------ | :------ | :--------- | :------- | :---- | :------- | :----- | :----------------- |
| 20240101 | T-2401-S1-GMV | 1       | False      | Store 1  | All   | gmv      | 1 tỷ   | Bản đầu năm        |
| 20240101 | T-2401-S1-GMV | 2       | True       | Store 1  | All   | gmv      | 1.2 tỷ | Đã điều chỉnh      |
| 20240101 | T-2401-S1-NV1 | 1       | True       | Store 1  | NV A  | gmv      | 200 tr | Chỉ tiêu cá nhân   |
| 20240101 | T-2401-S1-NV1 | 1       | True       | Store 1  | NV A  | new_cust | 50     | Chỉ tiêu khách mới |

Mô hình này đủ "chắc" để dùng cho cả năm tài chính và mở rộng cho nhiều năm sau.
