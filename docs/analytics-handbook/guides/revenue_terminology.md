# Thuật ngữ Doanh thu & Tài chính Đơn hàng

> **Đối tượng:** CEO, Sales Ops, Marketing, Kế toán
> **Cập nhật:** 2026-06-03

## Mục đích

Tài liệu này thống nhất cách gọi tên các chỉ số tài chính trong báo cáo. Mỗi khi đọc dashboard hoặc thảo luận về doanh thu, mọi người dùng chung một ngôn ngữ.

> **Phạm vi dữ liệu:** Tất cả đơn hàng từ **mọi kênh** (sàn TMĐT, social, website, cửa hàng, B2B) đều qua Sapo và nằm trong cùng bảng dữ liệu (`fact_orders`). Các thuật ngữ dưới đây áp dụng **xuyên suốt mọi kênh** — dùng filter kênh khi cần xem riêng từng kênh.

---

## 1. Dòng chảy doanh thu (Revenue Waterfall)

Mỗi đơn hàng đi qua các bước sau, từ giá bán gốc (đã gồm VAT) cho đến doanh thu thuần P&L (đã trừ VAT):

```
┌──────────────────────────────────────────────────────────────┐
│  ① Gross Revenue (Doanh thu gộp)                             │
│     = Giá bán × Số lượng (trước chiết khấu, ĐÃ gồm VAT)     │
│     Con số lớn nhất, chưa trừ chiết khấu.                    │
│     Dùng để đánh giá quy mô giao dịch trước chiết khấu.      │
├──────────────────────────────────────────────────────────────┤
│  − ② Discount Amount (Chiết khấu)                            │
│     Coupon, khuyến mãi, combo, giảm giá nhân viên...         │
├──────────────────────────────────────────────────────────────┤
│  = ③ Total Collected (Tổng thu từ khách)                     │
│     = $.total (total_amount) — số tiền khách thực trả.       │
│     Giá bán sau chiết khấu, VAT ĐÃ nhúng bên trong.          │
│     Đây là con số hiển thị trên hóa đơn.                     │
├──────────────────────────────────────────────────────────────┤
│  − ④ Tax Amount (VAT nhúng trong giá bán)                    │
│     VAT Sapo tính sẵn trong giá bán: 8/108 hoặc 10/110.      │
│     0 cho đơn xuất khẩu / mặt hàng không chịu thuế.          │
├──────────────────────────────────────────────────────────────┤
│  = ⑤ Net Revenue (Doanh thu thuần)                           │
│     Sau chiết khấu, ĐÃ TRỪ VAT — con số P&L kế toán.         │
│     Đây là con số quan trọng nhất cho phân tích kinh doanh.   │
├──────────────────────────────────────────────────────────────┤
│  − ⑥ Returns / Refunds (Trả hàng / Hoàn tiền)                │
│     Giá trị các đơn bị trả lại.                              │
├──────────────────────────────────────────────────────────────┤
│  = ⑦ Realized Revenue (Thực thu ròng)                        │
│     = Total Collected − Returns.                             │
│     ⚠ Vẫn gồm VAT (thuế phải nộp Nhà nước).                 │
│     Đây là góc nhìn dòng tiền, KHÔNG phải doanh thu kế toán. │
└──────────────────────────────────────────────────────────────┘
```

### Ví dụ minh họa

| Bước              | Mô tả                                          | Đơn hàng A | Đơn hàng B |
| ------------------- | ------------------------------------------------ | ------------- | ------------- |
| ① Gross Revenue    | Giá bán × SL (trước CK, đã gồm VAT)         | 1,000,000     | 500,000       |
| ② Discount         | Coupon 20%                                       | −200,000     | 0             |
| ③ Total Collected  | Tổng thu từ khách (= $.total, VAT đã trong đó) | 800,000       | 500,000       |
| ④ Tax (10/110)     | VAT nhúng trong giá bán (Sapo tính sẵn)         | −72,727      | −45,455      |
| ⑤ Net Revenue      | Sau chiết khấu, ĐÃ TRỪ VAT (P&L)               | 727,273       | 454,545       |
| ⑥ Returns          | Trả hàng                                        | 0             | −500,000     |
| ⑦ Realized Revenue | Thực thu ròng                                  | 800,000       | 0             |

> **⚠ Lưu ý về mô hình VAT nhúng (embedded VAT):**
>
> - Sapo **giá bán đã gồm VAT**. `$.total` (→ `total_amount`) là số tiền khách trả thực tế — VAT **nhúng bên trong**, không cộng thêm bên ngoài.
> - `$.total_tax` (→ `vat_amount`) là VAT Sapo tính sẵn theo từng đơn: 8/108 cho mặt hàng 8%, 10/110 cho mặt hàng 10%, 0 cho xuất khẩu / không chịu thuế.
> - **Net Revenue = total_amount − vat_amount** (doanh thu P&L, so sánh như-cho-như với giá vốn không VAT).
> - **~60% đơn có tax = 0** (đơn US xuất khẩu chiếm 99.6% zero-tax, cộng đơn bán lẻ Sapo không ghi VAT). Với những đơn này, net_revenue = total_amount (không có gì để trừ). Pipeline tin vào `$.total_tax` của Sapo — nó xử lý tự động 8%/10%/0%.
> - Realized Revenue là **góc nhìn dòng tiền** (bao nhiêu tiền thu được từ khách sau trả hàng), **không phải doanh thu kế toán**.
> - Field Realized Revenue **không có sẵn** trong `fact_orders`. Muốn tính, dùng: `total_collected − giá trị đơn trả hàng`.
> - Để phân tích kinh doanh (so sánh kênh, tính AOV...), luôn dùng **Net Revenue** — không dùng Realized Revenue.

---

## 2. Các chỉ số phái sinh thường dùng

| Chỉ số                            | Công thức                                 | Ý nghĩa                                                                                                    |
| ----------------------------------- | ------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| **GMV**                       | = Gross Revenue                             | Đồng nghĩa Doanh thu gộp (theo hệ thống của ta). GMV theo sàn TMĐT tính rộng hơn — xem mục 3.1 |
| **AOV** (Average Order Value) | = Net Revenue ÷ Số đơn                  | Giá trị trung bình mỗi đơn                                                                             |
| **Discount Rate**             | = Discount ÷ Gross Revenue × 100%         | Tỷ lệ chiết khấu so với giá gốc                                                                       |
| **Return Rate**               | = Số đơn trả ÷ Tổng đơn × 100%     | Tỷ lệ trả hàng (tính theo số đơn, không theo giá trị)                                             |
| **Basket Size**               | = Tổng sản phẩm ÷ Số đơn             | Số sản phẩm trung bình mỗi đơn                                                                        |
| **Completion Rate**           | = Đơn hoàn thành ÷ Tổng đơn × 100% | Tỷ lệ hoàn tất đơn hàng                                                                               |
| **Revenue per Customer**      | = Net Revenue ÷ Số khách                 | Doanh thu trung bình mỗi khách                                                                            |

---

## 3. Thuật ngữ theo kênh bán hàng

### 3.1. Sàn thương mại điện tử (Shopee, Lazada, Tiki, TikTok Shop)

| Thuật ngữ sàn                          | Nghĩa thực tế                                                          | Tương đương của ta                                                                 |
| ----------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **GMV** (theo sàn)                 | Tổng giá trị đơn hàng trên sàn (bao gồm phí ship, voucher sàn) | Không hoàn toàn = GMV của ta. Sàn tính rộng hơn.                                 |
| **Doanh thu** (trên Seller Center) | Tiền seller nhận sau khi sàn trừ phí                                 | ≈ Net Revenue − Commission                                                             |
| **Commission / Phí sàn**          | Phí % sàn thu trên mỗi đơn                                          | Chúng ta**không có** field này — Sapo không track                            |
| **Phí vận chuyển**               | Phí ship khách trả hoặc seller chịu                                  | Chúng ta**không có** field này                                                 |
| **Voucher sàn**                    | Sàn tự chi trả, không ảnh hưởng seller                             | Không nằm trong discount của ta                                                       |
| **Voucher seller**                  | Seller tự chi, nằm trong discount                                       | Nằm trong Discount Amount của ta (cùng với coupon, combo, giảm giá nhân viên...) |
| **Freeship**                        | Miễn phí vận chuyển                                                   | Không track riêng                                                                      |

**Lưu ý quan trọng khi đối soát:**

> - **"Doanh thu đơn hàng"** trên Seller Center (tổng giá trị đơn, gồm phí ship) thường **cao hơn** Net Revenue của ta.
> - **"Số tiền nhận về"** trên Seller Center (sau khi sàn trừ commission) thường **thấp hơn** Net Revenue của ta.
> - Cần xác định rõ đang so sánh **con số nào** trên Seller Center với **con số nào** trong dashboard nội bộ.

### 3.2. Social Commerce (Facebook, Instagram, Zalo)

| Thuật ngữ                         | Nghĩa                                              | Ghi chú                                                                                                        |
| ----------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Doanh thu social**          | Đơn hàng đến từ kênh Facebook/Zalo/Instagram | = Net Revenue filter theo `platform IN ('Facebook', 'Zalo', 'Instagram')` hoặc `channel_format = 'Social'` |
| **Inbox order**               | Đơn nhân viên CS tạo từ tin nhắn             | Tạo trên Sapo POS, gán kênh Facebook/Zalo                                                                   |
| **COD**                       | Thanh toán khi nhận hàng                         | Phổ biến trên social, xem payment_status                                                                     |
| **Chi phí quảng cáo**      | Facebook Ads, Zalo Ads                              | Chưa có trong pipeline (planned:`fact_marketing_spend`)                                                     |
| **ROAS** (Return on Ad Spend) | Net Revenue ÷ Chi phí quảng cáo                 | Chưa tính tự động — cần `fact_marketing_spend` (planned)                                               |

### 3.3. Website (weborder)

| Thuật ngữ               | Nghĩa                                   | Ghi chú                                      |
| ------------------------- | ---------------------------------------- | --------------------------------------------- |
| **Doanh thu web**   | Đơn qua website                        | = Net Revenue filter `platform = 'Website'` |
| **Payment gateway** | Cổng thanh toán online (VNPAY, OnePay) | Xem `fact_payments`                         |
| **Abandoned cart**  | Giỏ hàng bỏ dở                       | Sapo**không track**                    |

### 3.4. Cửa hàng (POS / Retail)

| Thuật ngữ                         | Nghĩa                   | Ghi chú                                           |
| ----------------------------------- | ------------------------ | -------------------------------------------------- |
| **Doanh thu cửa hàng**      | Đơn tại quầy         | = Net Revenue filter `channel_format = 'Retail'` |
| **Tiền mặt**                | Thanh toán cash         | Xem payment method = "Tiền mặt"                  |
| **Quẹt thẻ**                | POS card payment         | Xem payment method = "Quẹt thẻ"                  |
| **Chuyển khoản**            | Bank transfer tại quầy | Xem payment method chứa "Chuyển khoản"          |
| **Doanh thu theo chi nhánh** | Phân theo cửa hàng    | Filter `branch_location_name`                    |

**Chi nhánh hiện có:** VVT (Trương Định), HG (Hậu Giang), MMA (MM Market An Phú), HUS (TheHealthyUs), ST (Showroom VVT)

### 3.5. Đại lý & Bán sỉ (B2B / Wholesale)

| Thuật ngữ             | Nghĩa                        | Ghi chú                                                                  |
| ----------------------- | ----------------------------- | ------------------------------------------------------------------------- |
| **Doanh thu B2B** | Đơn bán sỉ cho đại lý  | = Net Revenue filter `channel_format = 'B2B'`                           |
| **Công nợ**     | Đại lý mua chịu, trả sau | Xem payment_status = 'UNPAID' hoặc payment method "Giảm trừ công nợ" |
| **Giá sỉ**      | Giá ưu đãi cho đại lý  | Phản ánh qua discount cao hơn bình thường                           |

### 3.6. Nội bộ & Đặc biệt

| Thuật ngữ                   | Nghĩa                                                                                                                                                                     | Ghi chú                             |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------ |
| **Đơn nội bộ**      | Ưu đãi nhân viên, quà tặng, test, CS, Telesale (tất cả kênh `channel_format = 'System'`)                                                                       | `channel_category = 'Internal'`    |
| **Đơn 100% discount** | total_collected = 0, toàn bộ là chiết khấu                                                                                                                            | Quà tặng, sampling, đơn nội bộ |
| **Đơn US (Export)**   | Đơn xuất khẩu B2B, 100% discount (chuyển hàng nội bộ tập đoàn).**Không phải** `channel_category = 'Internal'` — filter bằng `channel_name = 'US'` | `channel_name = 'US'`              |

> **Quy ước báo cáo — Bộ lọc mặc định:**
>
> - **Tất cả dashboard doanh thu** mặc định lọc:
>   - Loại đơn hủy/void: `status != 'CANCELLED'` và `payment_status != 'VOIDED'`
>   - `channel_category != 'Internal'` — loại đơn nội bộ (nhân viên, quà tặng, test)
> - **Dashboard Executive** thêm lọc:
>   - Loại đơn kênh **US** (`channel_name = 'US'` trong dim_channels) — đơn xuất khẩu B2B, 100% discount, làm méo chỉ số doanh thu
>
> Mỗi dashboard chọn tổ hợp bộ lọc phù hợp — xem Business Constraints trong Design Spec hoặc Blueprint tương ứng.

---

## 4. Thuật ngữ chúng ta KHÔNG dùng (nhưng hay gặp)

Các thuật ngữ dưới đây phổ biến trong ngành nhưng **không có trong dữ liệu của chúng ta** vì Sapo không track hoặc chưa tích hợp:

| Thuật ngữ                                | Nghĩa                           | Lý do không có                             |
| ------------------------------------------ | -------------------------------- | --------------------------------------------- |
| **Commission / Phí sàn**           | % sàn thu trên mỗi đơn      | Sapo không nhận dữ liệu phí từ sàn     |
| **Shipping Fee / Phí vận chuyển** | Phí ship                        | Sapo không tách riêng shipping fee         |
| **CAC (Customer Acquisition Cost)**  | Chi phí để có 1 khách mới  | Cần tích hợp đầy đủ chi phí marketing |
| **CLV:CAC Ratio**                    | Lifetime Value ÷ CAC            | Thiếu CAC chính xác                        |
| **Abandoned Cart Rate**              | Tỷ lệ bỏ giỏ hàng           | Sapo không track giỏ hàng bỏ dở          |
| **Conversion Rate (Web)**            | % visitor → buyer               | Cần Google Analytics, chưa tích hợp       |
| **NPS (Net Promoter Score)**         | Chỉ số hài lòng khách hàng | Chưa có khảo sát                          |
| **Voucher sàn (Platform subsidy)**  | Sàn tự trợ giá               | Không nằm trong data Sapo                   |

> **COGS & Gross Profit nay đã có:** Pipeline inventory-v2 (moving-average cost / MAC) + COGS reconciliation (Sapo-MAC primary, MISA TK632 đối soát) cung cấp COGS theo từng đơn. Chuỗi P&L đầy đủ: Net Revenue − **COGS** = **Gross Profit** − phí/chiết khấu kênh = **Channel net profit (lãi đóng góp)** − overhead phân bổ = **Fully-loaded net profit**. Xem `docs/architecture/order-pl/` (cogs-reconciliation-design.md, order-pl-schema-design.md, overhead-cost-allocation-design.md).

---

## 5. Tóm tắt nhanh cho báo cáo

Khi đọc dashboard, nhớ:

| Bạn thấy                 | Nghĩa là                              | Gồm VAT?    | Gồm discount? |
| -------------------------- | --------------------------------------- | ------------- | -------------- |
| **Gross Revenue**    | Giá bán × SL (trước CK, đã gồm VAT) | **Có** | Chưa trừ     |
| **Total Collected**  | Tiền khách trả (= $.total, đã gồm VAT) | **Có** | Đã trừ      |
| **Net Revenue**      | Sau chiết khấu, ĐÃ TRỪ VAT — P&L     | Không        | Đã trừ      |
| **Realized Revenue** | Thực thu ròng (sau trả hàng, vẫn gồm VAT) | **Có** | Đã trừ      |
| **Discount Amount**  | Số tiền giảm giá                      | —            | —             |
| **Tax Amount**       | VAT nhúng trong giá bán               | —            | —             |

**Quy tắc ngón tay cái:**

- So sánh hiệu quả kinh doanh → dùng **Net Revenue**
- Đối soát với ngân hàng/kế toán → dùng **Total Collected**
- Đánh giá quy mô thị trường → dùng **Gross Revenue (GMV)**
- Phân tích chính sách giá → dùng **Discount Rate** (= Discount ÷ Gross Revenue)

---

## 6. Mapping kỹ thuật

### 6.1. Dữ liệu gốc Sapo → Thuật ngữ chuẩn

| Sapo API field              | Sapo field name                   | Thuật ngữ chuẩn        | Ghi chú                                                                                        |
| --------------------------- | --------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------- |
| `$.total`                 | `total_amount`                  | **Total Collected** | Tổng tiền khách trả, ĐÃ gồm VAT, sau chiết khấu. Đây là field gốc từ Sapo.              |
| `$.total_discount`        | `total_discount_amount`         | **Discount Amount** | Tổng chiết khấu                                                                              |
| `$.total_tax`             | `vat_amount`                    | **Tax Amount**      | VAT nhúng trong giá bán: 8/108 hoặc 10/110 theo mặt hàng; 0 cho xuất khẩu / không VAT    |
| *Computed*             | `total_amount + total_discount_amount` | **Gross Revenue**   | Giá bán × SL trước chiết khấu (đã gồm VAT), phải tự tính                              |
| *Computed*             | `total_amount − vat_amount`            | **Net Revenue**     | Doanh thu thuần P&L: sau chiết khấu, ĐÃ TRỪ VAT. Không có sẵn trong Sapo — tự tính    |

### 6.2. Pipeline: Sapo → Staging → Mart

```
Sapo API                   std_orders                 fact_orders
─────────────────────────────────────────────────────────────────
$.total                 →  total_amount            →  total_collected (= total_amount; VAT đã trong đó)
$.total_discount        →  total_discount_amount   →  discount_amount
$.total_tax             →  vat_amount              →  vat_amount
(computed)              →  (computed)              →  gross_revenue = total_amount + total_discount_amount
(computed)              →  (computed)              →  net_revenue   = total_amount − vat_amount
```

### 6.3. Công thức trong fact_orders

```sql
-- Tổng thu từ khách (sau chiết khấu, VAT đã nhúng trong giá bán) — field gốc từ Sapo $.total
total_collected  = total_amount

-- Doanh thu thuần P&L (sau chiết khấu, ĐÃ TRỪ VAT) — dùng để so sánh với giá vốn không VAT
net_revenue      = total_amount - vat_amount
-- Lưu ý: ~60% đơn có vat_amount = 0 (xuất khẩu US + đơn bán lẻ không ghi VAT)
--         → với những đơn đó: net_revenue = total_amount (không có gì để trừ)
--         Pipeline tin vào $.total_tax của Sapo; nó tự xử lý 8%/10%/0% theo từng đơn.

-- Giá bán × số lượng (trước chiết khấu, đã gồm VAT)
gross_revenue    = total_amount + total_discount_amount

-- Tỷ lệ chiết khấu (công thức tham khảo, không phải column trong fact_orders)
-- discount_rate = discount_amount / gross_revenue × 100%
```

### 6.4. Line-item level (fact_sales)

| Field                           | Nghĩa                                                     |
| ------------------------------- | ---------------------------------------------------------- |
| `quantity`                    | Số lượng mua                                            |
| `net_revenue`                 | =`line_amount` (giá trị dòng sau line-level discount) |
| `discount_amount`             | Chiết khấu trực tiếp trên dòng                       |
| `distributed_discount_amount` | Phần chiết khấu order-level phân bổ xuống dòng      |

### 6.5. Trường KHÔNG dùng từ Sapo (có trong raw nhưng không cần)

| Sapo field                                   | Lý do không dùng                                                 |
| -------------------------------------------- | ------------------------------------------------------------------- |
| `financial_status`                         | Đã normalize thành `payment_status` trong std_orders           |
| `packed_status`, `received_status`       | Đã gộp vào logic `fulfillment_status`                         |
| `assignee_*`                             | Normalize thành `seller_staff_key` (người chốt/giao đơn — primary)        |
| `account_*`, `user_name`                 | Normalize thành `creator_staff_key` (người tạo đơn — operational/fallback) |
| `issued_on`, `finalized_on`              | Ít dùng trong báo cáo, giữ `created_at` và `completed_at` |

---

## 7. Dòng `net_revenue = 0` nghĩa là gì

`net_revenue` ở cấp dòng đơn (`fact_sales`) bằng 0 khi và chỉ khi `line_amount = 0` trong Sapo — tức **giá bán bị giảm 100%**. **43.9% tổng số dòng đơn** rơi vào đây, gồm hai loại:

| Loại | Ví dụ | Bản chất |
|---|---|---|
| **A. SP thật được tặng kèm** | Cordyceps Plus, Metabo Green Tea, Fine Collagen | Khách không trả tiền → không phản ánh sở thích mua |
| **B. Swag / giấy tờ không bán** | Dù in logo công ty FG & Fine Japan, "Công Văn Giấy Tờ", Bát tre, Túi vải logo | Không bao giờ bán → noise thuần túy |

Cả hai loại bị loại bởi **một điều kiện duy nhất** `net_revenue > 0`.

### Ảnh hưởng đến các tín hiệu phân tích

| Tín hiệu | Có loại dòng 0đ không? | Lý do |
|---|---|---|
| `product_affinity` (brand-level) | Có (gián tiếp) | Rank theo `SUM(net_revenue)` share → dòng 0đ đóng góp 0 |
| `top_affinity_product` / `second_affinity_product` | Có (tường minh `net_revenue > 0`) | Tần suất tái mua chỉ tính đơn **trả tiền** |
| `last_purchased_product` | Có (tường minh `net_revenue > 0`) | "Đơn mua gần nhất" = đơn paid gần nhất, không phải đơn nhận quà gần nhất |

### NULL = khách chỉ nhận quà (all-0đ)

Khách có toàn bộ dòng `net_revenue = 0` (ví dụ: người nhận quà CrossBorder/US) sẽ có `last_purchased_product`, `top_affinity_product`, `second_affinity_product` = NULL. Đây là **đúng** — họ chưa từng mua, thuộc play gifting/conversion riêng, không nên chạy script reorder.
