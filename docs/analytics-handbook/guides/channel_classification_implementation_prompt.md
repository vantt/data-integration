# Prompt: Triển khai Channel Classification

Dùng prompt bên dưới để bắt đầu một chat session mới với Claude Code.

---

```
Đọc tài liệu `docs/analytics-handbook/guides/channel_classification.md` — đặc biệt phần 6 (Tài liệu kỹ thuật). Đây là kết quả thiết kế đã được duyệt. Hãy triển khai theo đúng thiết kế, không thay đổi kiến trúc.

## Phạm vi triển khai

### Bước 1: ref_order_sources.csv — Thêm 3 cột
- Thêm `channel_brand`, `market`, `customer_segment` vào seed file hiện có
- Giữ nguyên tất cả cột cũ, không đổi tên, không xóa
- Điền giá trị cho TẤT CẢ dòng hiện có theo bảng mapping trong phần 6.2.1
- Cập nhật `transformation/seeds/properties.yml` nếu cần

### Bước 2: ref_brands.csv — Tạo seed mới
- Tạo file `transformation/seeds/ref_brands.csv` theo schema phần 6.2.2
- Tạo properties trong `transformation/seeds/properties.yml`
- Trước khi viết, query dữ liệu thực tế vendor từ `std_order_items` (hoặc stg) để biết tất cả giá trị vendor đang có, rồi tạo mapping đầy đủ

### Bước 3: dim_products.sql — Thêm brand
- LEFT JOIN ref_brands để map vendor → brand_name, brand_code
- Join condition: UPPER(vendor) = UPPER(vendor_raw)
- Fallback: COALESCE(ref_brands.brand_name, vendor) as brand_name
- Thêm brand_name và brand_code vào output, kể cả Unknown Member
- Cập nhật schema.yml

### Bước 4: dim_channels.sql — Thêm cột mới
- Expose `channel_brand`, `market`, `customer_segment` từ ref_order_sources
- Derive `channel_category` bằng CASE WHEN trên platform_group (xem logic phần 6.3.1)
- Derive `is_sales_channel` bằng platform_group != 'System'
- Thêm tất cả cột mới vào cả specific_channels, generic_channels, và Unknown Member
- Cập nhật schema.yml

### Bước 5: Kiểm tra
- Chạy `dbt build --select ref_order_sources ref_brands dim_channels dim_products`
- Kiểm tra không có lỗi
- Query dim_channels xác nhận channel_category, channel_brand, market, customer_segment có giá trị đúng
- Query dim_products xác nhận brand_name, brand_code có giá trị đúng

## Lưu ý quan trọng
- KHÔNG thay đổi fact tables
- KHÔNG rename dimension tables
- KHÔNG thay đổi surrogate key logic
- KHÔNG thay đổi cột hiện có (chỉ THÊM cột mới)
- Giữ backward compatibility hoàn toàn — báo cáo hiện tại không bị ảnh hưởng
```
