# Phân tích Gom nhóm Kênh & Bản chất Đơn hàng

> **Ngày:** 2026-04-11
> **Mục đích:** Nhận diện vấn đề classification hiện tại, đề xuất cách gom nhóm dữ liệu chính xác hơn cho báo cáo
> **Dữ liệu:** 51,300 đơn completed từ warehouse (tính đến 2026-04-11)

---

## 1. Vấn đề hiện tại

### 1.1. "US" channel — Cross-border fulfillment bị lẫn vào doanh thu VN

| Metric | Giá trị |
|---|---|
| Số đơn | 11,540 |
| Gross revenue | 514 tỷ |
| Discount | 473 tỷ (82.7%) |
| Discount gần đây (2026) | **100%** mọi đơn |

**Bản chất business:**

FG Care US nhập sản phẩm Fine Japan từ Nhật bán cho Việt Kiều tại Mỹ. Phát hiện hàng ship từ Nhật về VN nhanh và rẻ hơn ship qua Mỹ, FG Care US lập FG Care VN với chức năng chính: **giao hàng tại VN cho người thân của khách hàng Mỹ**.

Mô hình vận hành:
- Khách Việt Kiều mua 12 hộp → dùng 4 hộp tại Mỹ, gửi 8 hộp về VN cho người thân
- FG Care US giao 4 hộp tại Mỹ, FG Care VN giao 8 hộp tại VN
- Khách thanh toán toàn bộ 12 hộp cho FG Care US (giá niêm yết Mỹ, KM theo chương trình Mỹ)
- FG Care US thanh toán cho FG Care VN phần giao tại VN theo **hợp đồng mua bán riêng**

→ Đây **không phải** inter-company transfer đơn thuần. Đây là cross-border fulfillment service — FG Care VN đóng vai trò logistics/fulfillment cho FG Care US, thanh toán theo hợp đồng B2B riêng biệt.

**Ghi nhận doanh thu:** Doanh thu từ nguồn này = **0đ** trong báo cáo FG Care VN. Loại trừ toàn bộ khi đánh giá hiệu quả kinh doanh VN vì cơ chế mua bán khác hoàn toàn so với các kênh/đại lý khác.

**Hiện tại:** classify `Other / Other / Export / B2B` → mix chung với đơn Other thật, kéo lệch mọi metric trung bình.

**Hậu quả:**
- Tổng discount toàn hệ thống bị phồng
- Báo cáo "Export" hay "B2B" vô nghĩa vì phần lớn là cross-border fulfillment
- Gross revenue bị inflate ~500 tỷ nhưng net gần như bằng 0

---

### 1.2. "Đại Lý" — Giá sỉ bị coi như discount promotion

| Metric | Giá trị |
|---|---|
| Số đơn | 11,152 |
| AOV | 6.17M |
| Avg discount | 46.8% |

**Bản chất:** Discount 40-50% là **giá sỉ cố định**, không phải promotion.

**Hậu quả:** Khi mix với Shopee (D% 29%), Lazada (D% 14%), metric "discount rate" trung bình bị sai bản chất. Không thể so sánh "hiệu quả promotion" giữa kênh sỉ và kênh lẻ.

---

### 1.3. Internal channels — Rủi ro lọt vào báo cáo

| Channel | Đơn | Gross | Net | Avg D% | Bản chất |
|---|---|---|---|---|---|
| Quà Tặng | 788 | 9.2 tỷ | 6.5 triệu | 78.7% | Cho hàng miễn phí |
| Ưu đãi NV | 1,292 | 6.6 tỷ | 594 triệu | 77.8% | Giá nhân viên |
| Test SP | 76 | 274 triệu | 78 triệu | 77.9% | Đơn test |
| Telesale | 36 | 291 triệu | 115 triệu | 42.4% | Nội bộ |
| CS | 88 | 252 triệu | 145 triệu | 32.9% | Customer Service |

`is_sales_channel = false` đã tồn tại nhưng báo cáo cần **luôn luôn** filter theo nó. Nếu quên → sai lệch nặng, đặc biệt Quà Tặng (9.2 tỷ gross bị inflate).

---

### 1.4. "Other" channel — Thùng rác không phân loại

| Metric | Giá trị |
|---|---|
| Số đơn | 2,568 |
| Net revenue | 5.2 tỷ |
| Avg discount | 26.5% |

**Mix lẫn nhiều loại:**
- Khách VIP mua qua DM/điện thoại (Huynh Tri Bao, Trần Thị Thanh Trang)
- CTV/cộng tác viên (Anh Long - CTV OTC: 100% discount, Fine Japan-USA: 100% discount)
- Đơn không xác định source
- Khách sỉ ẩn (Quang: D% 65%, chị Quyên: D% 52%)

**Hậu quả:** Không thể phân tích "Other" vì bản chất đơn quá khác nhau.

---

### 1.5. Khách sỉ ẩn trên kênh B2C (Zalo, Facebook, Other)

Nhiều khách mua qua Zalo/Facebook có pattern giống bán sỉ:

| Khách hàng | Kênh | AOV | Discount | Pattern |
|---|---|---|---|---|
| Mr.Bình | Zalo | 24.4M | 50.6% | Sỉ |
| Chị Hạnh Nguyễn | Zalo | 22M | 50.8% | Sỉ |
| chị Thủy | Zalo | 21.2M | 50.5% | Sỉ |
| Chị Yến | Zalo | 19M | 58.2% | Sỉ |
| Petter Phạm | Facebook | — | 53.3% | Sỉ/VIP |
| Cô Sáu US | Zalo | 11.3M | 52.1% | Sỉ |

**Đặc điểm chung:** AOV > 10M, discount cố định ~50%, mua định kỳ.

**Hậu quả:** Kênh Zalo (D% 38.7%) và Facebook (D% 40.6%) bị kéo lệch bởi khách sỉ, không phản ánh đúng hiệu quả kênh B2C.

---

## 2. Tổng hợp phân bổ doanh thu hiện tại

| Category | Segment | Market | Đơn | Net (tỷ) | Disc% | Ghi chú |
|---|---|---|---|---|---|---|
| Ecommerce | B2C | Domestic | 22,168 | 38.5 | 28.8% | Kênh bán lẻ chính |
| Offline | B2B | Domestic | 11,156 | 68.8 | 46.8% | Đại Lý — giá sỉ |
| Other | B2B | Export | 11,540 | 41.0 | 82.7% | **US — inter-company** |
| Other | B2C | Domestic | 2,584 | 5.2 | 26.7% | Thùng rác |
| Offline | B2C | Domestic | 1,560 | 2.6 | 25.5% | POS retail |
| Internal | B2C | Domestic | 2,280 | 0.9 | 75.8% | Không phải bán hàng |

---

## 3. Đề xuất: Thêm lớp "Bản chất đơn hàng" (Order Nature)

### 3.1. Định nghĩa order_nature

Bổ sung cho hệ thống channel hiện tại, không thay thế.

| order_nature | Mô tả | Cách xác định |
|---|---|---|
| **retail_sale** | Bán lẻ, giá thị trường | Kênh B2C + customer_type != wholesale |
| **wholesale** | Bán sỉ, giá chiết khấu cố định | Đại Lý, Chợ sỉ + khách sỉ ẩn trên Zalo/FB/Other |
| **cross_border_fulfillment** | Giao hàng tại VN cho khách FG Care US, doanh thu = 0đ | US channel — thanh toán theo hợp đồng B2B riêng |
| **staff_benefit** | Ưu đãi nhân viên | Ưu đãi Nhân Viên |
| **gift** | Quà tặng, hàng cho | Quà Tặng |
| **test** | Đơn test | Test Sản Phẩm |
| **affiliate** | CTV bán hàng | Khách có tag CTV, discount ~100% |

### 3.2. Cách identify "khách sỉ ẩn" trên kênh B2C

**Approach A: Customer tagging (Khuyến nghị — chính xác, đơn giản)**

Tạo seed `ref_customer_tags.csv`:

```csv
customer_id,customer_type,notes
12345,wholesale,"Mr.Bình - mua sỉ qua Zalo"
12346,wholesale,"Chị Hạnh Nguyễn"
12347,ctv,"Anh Long - CTV OTC"
```

- Ưu: chính xác 100%, business team kiểm soát
- Nhược: maintain thủ công, nhưng số lượng ít (~20-50 khách)

**Approach B: Rule-based screening (Bổ trợ — phát hiện)**

Dùng để phát hiện khách sỉ mới, sau đó xác nhận thủ công:

```
Nếu: AOV > 10M AND avg_discount > 40% AND order_count > 5
→ Flag "likely_wholesale" → review thủ công
```

### 3.3. Xử lý US channel

| Thuộc tính | Hiện tại | Đề xuất |
|---|---|---|
| platform_group | Other | **CrossBorder** (giá trị mới) |
| is_sales_channel | true (implicit) | **false** |
| channel_category | Other | **Internal** |
| order_nature | (chưa có) | **cross_border_fulfillment** |

**Lý do:** US không phải bán hàng của FG Care VN. Doanh thu thuộc FG Care US, VN chỉ thực hiện fulfillment theo hợp đồng B2B riêng. Ghi nhận doanh thu = 0đ.

→ Mặc định loại khỏi mọi báo cáo doanh thu VN.

### 3.4. Xử lý "Other" channel

Tách "Other" thành các nguồn cụ thể hơn nếu có thể identify qua tags/notes trong Sapo:

| Nhóm | Cách identify | Xử lý |
|---|---|---|
| Khách VIP/DM | customer_type = retail, AOV cao | Giữ nguyên B2C |
| Khách sỉ ẩn | customer_type = wholesale (từ ref_customer_tags) | Gom vào wholesale |
| CTV | customer_type = ctv | Tách riêng affiliate |
| Không rõ | Còn lại | Giữ "Other" nhưng monitor |

---

## 4. Report Grouping khuyến nghị

### 4.1. Báo cáo doanh thu bán hàng (mặc định)

```
WHERE is_sales_channel = true
  AND order_nature IN ('retail_sale', 'wholesale')
```

Loại: US, Internal, Gift, Test, CTV 100%.

### 4.2. Hiệu quả kênh Ecommerce (B2C thuần)

```
WHERE channel_category = 'Ecommerce'
  AND order_nature = 'retail_sale'
```

Loại: khách sỉ ẩn trên Zalo/Facebook → so sánh discount giữa các kênh mới chính xác.

### 4.3. Báo cáo kênh sỉ (tách riêng)

```
WHERE order_nature = 'wholesale'
```

Gom: Đại Lý + Chợ sỉ + khách sỉ ẩn trên Zalo/FB/Other. Metric discount ở đây là giá sỉ, không phải promotion.

### 4.4. P&L tổng hợp

```
WHERE is_sales_channel = true
  AND order_nature NOT IN ('test', 'gift')
```

Gồm cả wholesale, staff benefit. Loại test và gift.

### 4.5. Discount analysis

**PHẢI** tách riêng:
- **Retail discount:** promotion/coupon thật → so sánh Shopee vs Lazada vs Web
- **Wholesale discount:** giá sỉ cố định → không so sánh với retail
- **Internal discount:** giá NV, quà tặng → loại khỏi analysis

---

## 5. Implementation Roadmap

### Phase 1: Quick wins (seed changes, không cần code mới)

1. Sửa `ref_order_sources.csv`: US → `platform_group = 'CrossBorder'`, `is_sales_channel = false`
2. Cập nhật `dim_channels.sql`: thêm `CrossBorder` → `channel_category = 'Internal'`

### Phase 2: Customer tagging

1. Tạo `ref_customer_tags.csv` với danh sách khách sỉ/CTV đã biết
2. Thêm `customer_type` vào `dim_customers` (LEFT JOIN ref_customer_tags)

### Phase 3: Order nature derivation

1. Thêm `order_nature` vào `fact_orders` / `fact_sales`, derive từ:
   - channel → CrossBorder (US) / Internal / Staff / Gift / Test
   - customer_type → wholesale / ctv
   - Còn lại → retail_sale

### Phase 4: Report templates

1. Cập nhật Metabase dashboards với filter mặc định theo order_nature
2. Tạo dashboard riêng cho kênh sỉ

---

## 6. Câu hỏi cần xác nhận từ Business

1. **US channel**: ~~Có đơn US nào là bán thật cho khách Mỹ không?~~ **ĐÃ XÁC NHẬN:** 100% là cross-border fulfillment — FG Care VN giao hàng tại VN cho khách của FG Care US, doanh thu = 0đ, thanh toán theo hợp đồng B2B riêng.
2. **"Other" channel**: Có tag hoặc note nào trong Sapo giúp phân biệt khách VIP / CTV / khách sỉ?
3. **Khách sỉ Zalo/Facebook**: Danh sách khoảng bao nhiêu người? Có sẵn list từ sales team không?
4. **Discount 50% trên Zalo/FB**: Là chính sách giá sỉ cố định hay promotion từng đơn?
5. **Telesale + CS**: Nên tính là doanh thu bán hàng hay internal? Hiện tại là `System / Internal`.
6. **"Gosumo", "POPS", "Leflair", "Selly", "Chiaki"**: Các kênh inactive này có cần giữ lại trong báo cáo hay archive?
