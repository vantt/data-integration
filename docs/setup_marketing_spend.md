# Hướng Dẫn Setup & Sử Dụng Marketing Spend Input

Tài liệu này hướng dẫn cách thiết lập Google Sheet để nhập liệu Chi phí Marketing, đảm bảo dữ liệu tự động map đúng vào hệ thống Data Warehouse.

## 1. Cấu Trúc Google Sheet

Bạn hãy tạo một Google Sheet mới (hoặc dùng Sheet hiện tại) với **2 Sheet** (Tab):

### Sheet 1: `Input` (Nơi nhập liệu)

Tạo các cột theo đúng thứ tự sau:

| Cột | Tên Cột (Header) | Mô Tả                  | Cách Nhập              |
| :-- | :--------------- | :--------------------- | :--------------------- |
| A   | Date             | Ngày chi tiêu          | Nhập ngày (DD/MM/YYYY) |
| B   | Spend Category   | Loại chi phí           | **Chọn từ Dropdown**   |
| C   | Target Channel   | Kênh mục tiêu          | **Chọn từ Dropdown**   |
| D   | Campaign ID      | Mã chiến dịch (nếu có) | Nhập tay (Optional)    |
| E   | Spend Amount     | Số tiền đã chi (VND)   | Nhập số                |
| F   | Clicks           | Số lượt Click          | Nhập số                |
| G   | Impressions      | Số lượt hiển thị       | Nhập số                |
| H   | Notes            | Ghi chú thêm           | Nhập tay (Optional)    |

### Sheet 2: `Validation` (Dữ liệu Dropdown)

Sheet này dùng để chứa danh sách các tùy chọn cho cột B và C ở Sheet Input. **Không nhập liệu ở đây.**

---

## 2. Cách Tạo Dropdown (Data Validation)

Để đảm bảo dữ liệu chuẩn xác, bạn cần copy dữ liệu từ hệ thống vào Sheet `Validation`, sau đó cài đặt Dropdown cho Sheet `Input`.

### Bước 1: Lấy Dữ Liệu Dropdown Mới Nhất

1. Yêu cầu IT/Data Team chạy tool `generate_dropdown.py` để lấy danh sách mới nhất.
2. Mở file `ingestion/src/dropdown_options.csv` được gửi tới.
3. Copy toàn bộ cột `spend_category_options` và `target_channel_options`.

### Bước 2: Paste vào Sheet `Validation`

1. Mở Google Sheet, sang tab `Validation`.
2. Paste dữ liệu vào 2 cột A (Spend Category) và B (Target Channel).

### Bước 3: Cài Đặt Dropdown cho Sheet `Input`

1. Sang tab `Input`.
2. **Cài Dropdown cho Cột B (Spend Category)**:
   - Bôi đen cột B (từ dòng 2 trở đi).
   - Chọn menu `Data` > `Data Validation`.
   - Criteria: Chọn `Dropdown (from a range)`.
   - Chọn vùng dữ liệu: `'Validation'!$A$2:$A$1000`.
   - Click `Done`.
3. **Cài Dropdown cho Cột C (Target Channel)**:
   - Bôi đen cột C (từ dòng 2 trở đi).
   - Làm tương tự, nhưng chọn vùng dữ liệu: `'Validation'!$B$2:$B$1000`.

---

## 3. Quy Trình Nhập Liệu Hàng Ngày

1. Mở Sheet `Input`.
2. Nhập Ngày (Date).
3. **Quan Trọng**: Chọn `Spend Category` và `Target Channel` từ Dropdown. **Không tự gõ tên mới**.
   - Nếu bạn chọn tên không có trong danh sách, hệ thống sẽ báo lỗi hoặc không map được dữ liệu.
4. Nhập số tiền và các chỉ số (Clicks, Impressions).

## 4. Xử Lý Khi Cần Thêm Kênh Mới / Loại Chi Phí Mới

Nếu bạn cần nhập cho một Kênh hoặc Loại Chi Phí chưa có trong Dropdown:

1. **Liên hệ Data Team** để thêm vào hệ thống gốc (file Seeds).
2. Data Team sẽ chạy lại tool update và gửi lại danh sách `dropdown_options.csv`.
3. Bạn update lại Sheet `Validation` theo hướng dẫn ở **Mục 2**.

---

## 5. Chi Tiết Kỹ Thuật (Dành cho Data Team)

### A. Kiến Trúc Dữ Liệu

1. **Ingestion Layer (Python)**
   - **Script**: `ingestion/src/gsheet_marketing_spend.py`
   - **Input**: Google Sheet (CSV Export)
   - **Logic Mapping**:
     - `Spend Category` (Name) -> `ref_spend_category` (Code)
     - `Target Channel` (Display Name) -> `source_id` + `location_id`
   - **Output**: Parquet files partitioned by Year/Month.

2. **Transformation Layer (dbt)**
   - **Staging**: `stg_marketing_spend`
     - Casts IDs to String.
     - Generates Surrogate Key (`spend_id`).
   - **Mart**: `fact_marketing_spend`
     - Joins with `dim_channels` using explicit `source_id` and `location_id`.
     - **Logic Thay đổi**: Loại bỏ hoàn toàn bảng mapping thủ công `ref_marketing_spend_map`. Thay vào đó, sự chính xác được đảm bảo ngay từ khâu Ingestion nhờ Dropdown chuẩn.

### B. Quy Trình Bảo Trì (Maintenance)

Khi có sự thay đổi về cấu trúc kinh doanh (Thêm Cửa hàng, Thêm Nguồn bán, Thêm Loại chi phí):

1. **Update Seeds**: Cập nhật các file CSV trong `transformation/seeds/` (ref_branch_locations, ref_order_sources, ref_spend_category).
2. **Run Generator**: Chạy script tạo Dropdown:
   ```bash
   python ingestion/src/generate_dropdown.py
   ```
3. **Update Sheet**: Copy nội dung từ `ingestion/src/dropdown_options.csv` vào Sheet Validation.
4. **Deploy**: Commit code lên Git để pipeline Ingestion nhận diện các ID mới.

### C. Debugging

Nếu dữ liệu vào Warehouse bị `Unknown Channel` hoặc `Unknown Spend`:

- Kiểm tra logs của Ingestion Job. Warning sẽ cho biết giá trị nào trong Google Sheet không khớp với hệ thống.
- Yêu cầu người nhập liệu sửa lại giá trị đó theo đúng Dropdown.
