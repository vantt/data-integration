# Tổng hợp 4 bản phản biện thiết kế bộ máy phân loại (14/10/2026)

Nguồn: `review-product-sme.md`, `review-data-architect.md`, `review-analytics.md`, `review-ops-risk.md`, đánh giá `../../taxonomy-engine-design.md`.

## Kết luận

Cả bốn đồng ý hướng thiết kế (đặc trưng → luật là dữ liệu → nhãn riêng + mã chuẩn). Ba điểm của bản nháp bị bác hoặc phải sửa:

1. **Lý do "đặt bộ máy trước phase 6" sai.** Phase 6 không dời khối phân loại nào (đã kiểm `phase-06-fine-japan-tenant-overlay.md`: chỉ dời HUG, US shipment, CRM, cashflow, overhead, seed FJ; CROSSBORDER chỉ là một dòng allowlist). Ba trên bốn bản khuyên không chặn phase 6.
2. **"0 khác biệt" chỉ đạt được ở golden, không ở compiled SQL**, và chỉ khi pilot tôn trọng nguyên văn ngữ nghĩa cũ: toán tử `LIKE` (dấu `_` là wildcard), đặc trưng thô chưa chuẩn hoá, mặc định `RETAIL` thay vì `UNKNOWN`, logic SQL ba giá trị, không thêm cột vào mart public trong pilot (golden so thứ tự cột), giữ `is_us_gift_recipient` có thể NULL (hai action queue CRM đang dựa vào đó).
3. **Phạm vi doanh thu (`scope_*`) là thuộc tính của đơn, không phải của khách.** Cần một domain cấp đơn (`sales_line`), `scope_*` chỉ còn là kiểm tra thuộc tập; phần khác nhau giữa doanh nghiệp (có tính đơn STAFF/KOL vào doanh thu không) là tham số.

## Sáu quyết định

| # | Quyết định | Đồng thuận | Khuyến nghị |
|---|---|---|---|
| 1 | Nhãn riêng + mã chuẩn bắt buộc | 4/4 đồng ý | Đồng ý. Không đưa `*_std` lên mart public cho tới khi bộ mã được kiểm bằng dữ liệu doanh nghiệp thứ hai. Cho phép neo nhãn vào nút cha của cây mã. `customer_type`, `order_purpose`, `discount_purpose` tổ chức thành cây |
| 2 | Bộ máy trước phase 6? | 3/4 không | Thứ tự: phase 4 rút gọn → 6 → 7 (đóng Đợt 1) → plan riêng cho bộ máy. Spike trên shadow được chạy song song nếu không deploy |
| 3 | Bỏ tách macro nguyên văn ở phase 4 | 4/4 đồng ý | Đồng ý, kèm: sửa tiêu chí nghiệm thu #5 của `plan.md`; `TAXONOMY.md` ghi file:dòng + hash nội dung từng khối CASE; kiểm tra cảnh báo khối CASE phân loại mới; mốc dự phòng ~6 tuần |
| 4 | Kênh nhiều trục | 4/4 đồng ý hướng | MVP chỉ tách mục đích đơn và domain cấp đơn; bỏ `NON_SALES`/`INTERNAL` khỏi trục kênh; `seller_role`, `content_carrier` để sau |
| 5 | Restate mặc định | 4/4 đồng ý có điều kiện | Restate cho nhãn sự kiện; ảnh chụp cuối tháng cho vòng đời, hạng giá trị, RFM; khoá kỳ cho kế toán và thưởng đã chốt; đổi `ruleset_version` kéo theo full-refresh model incremental phía sau |
| 6 | Ai nhập luật | 4/4 gần giống | Trước mắt mình cấu hình hộ qua git + gate. Sheet sau, đi qua lake thô (không ghi seed vào checkout), có kiểm tra cú pháp, báo cáo tác động, giữ bộ luật hợp lệ gần nhất. Luật phải nằm ngoài image |

## Phát hiện mới cần xử lý

- **Tài liệu thiết kế sai so với code:** thứ tự ưu tiên thật của `customer_type` là WHOLESALE > PARTNER > STAFF > KOL > CROSSBORDER; `customer_type` có 2 logic chứ không 3 (`fact_orders` và `int_customer_benchmarks` giống nhau về logic; văn bản chỉ khác tiền tố bí danh `c.` ở bản benchmarks, nên sha256 khác nhau — đính chính 14/10 sau phase 4); hai biến thể `value_group` tương đương.
- **`scope_b2b` trong code** (`fact_orders.sql` 215–219) có thêm `OR channel_format = 'B2B'`, tài liệu không ghi.
- **Rủi ro không tất định đang có trên prod:** 28 dòng `ref_tag_categories` cùng priority 10, `int_order_tags` không có tie-break. Nên sửa độc lập, có thể đổi số nên đi qua gate.
- **Model incremental lưu nhãn:** `int_customer_entry_attributes` (lọc `customer_type = 'RETAIL'`, không cập nhật khách cũ), `int_customer_discount_metrics`, `dim_customers_base`. Restate không tự có.
- **Mặc định sản phẩm khác Fine Japan:** đơn chưa phân loại nên vẫn tính doanh thu dưới dòng "chưa phân loại"; loại "Other" khỏi doanh thu là luật riêng của Fine Japan.
- **CROSSBORDER nên phân loại ở cấp đơn**; ở trục khách nó làm rơi đơn bán lẻ thật của người nhận hàng hộ khỏi `scope_retail` (đổi số, duyệt riêng).

## Công sức và điều kiện dừng thí điểm

- MVP + pilot `customer_type`: 7–9 ngày công (kỹ sư dữ liệu); bản SME đề xuất trần 4 ngày.
- Dừng và rơi về SQL/macro nếu: quá 5 ngày công chưa đạt 0 khác biệt golden; cần quá 3 đặc trưng chỉ Fine Japan dùng; phải dùng SQL tự do trong luật; nightly chậm thêm quá 10% hoặc 10 phút, RAM đỉnh tăng quá 20%; tỉ lệ `UNMAPPED` + `UNKNOWN` cao hơn tỉ lệ rơi vào `ELSE` của SQL cũ.
- Triển khai pilot 4 bước: shadow → chạy song song trên prod chưa nối mart 14 đêm → chuyển cột mart, giữ đường SQL cũ sau `var` 30 ngày → xoá đường cũ.

## Chặn và câu hỏi

- **Chặn việc chốt bộ mã chuẩn:** cần danh sách nguồn đơn và nhóm khách của ít nhất một shop thứ hai (Sapo hoặc khác).
- Nghiệp vụ Fine Japan: báo cáo nào đã dùng để chốt thưởng (ảnh hưởng restate); MISA DAILY/CS; `scope_retail` còn cần loại B2B không; CROSSBORDER cấp đơn.
