# Phân tích Gom nhóm Kênh & Bản chất Đơn hàng

> **Ngày:** 2026-04-13
> **Dữ liệu:** 51,300 đơn completed từ warehouse

## Mục đích & TL;DR

Tài liệu này trả lời những câu hỏi nào?

1. **Tại sao discount trung bình bị phồng?** — US channel, khách sỉ ẩn, nội bộ lẫn vào
2. **Làm sao phân biệt bán sỉ vs promotion?** — Đại Lý (46.8%) có giá sỉ cố định, không phải KM
3. **CS/Telesale là doanh thu hay nội bộ?** — Doanh thu bán hàng thật, cần chuyển category
4. **"Other" là gì?** — Thùng rác chứa khách VIP, CTV, khách sỉ ẩn, đơn không rõ
5. **Làm sao fix?** — Thêm `order_nature` dimension + customer tagging

**Executive Summary:**

- **ĐÃ XÁC NHẬN (2026-04-13):** Telesale & CS = bán thật, chuyển sang Offline/Direct Sales
- **ĐÃ XÁC NHẬN:** US channel = cross-border fulfillment (0đ doanh thu), không phải bán hàng VN
- **ĐỀ XUẤT:** Thêm `order_nature` để tách retail_sale, wholesale, cross_border_fulfillment, staff_benefit, gift, test
- **ĐỀ XUẤT:** Customer tagging để identify khách sỉ ẩn trên Zalo/Facebook (~20-50 khách)
- **Hành động:** 4 phase: seed changes (1-2 tuần), customer tagging, order_nature derivation, report templates

---

## Decision Log

| Quyết định | Trạng thái | Ngày | Xác nhận bởi | Ghi chú |
|-----------|----------|------|----------|---------|
| US channel = cross-border fulfillment, không tính doanh thu VN | ĐÃ XÁC NHẬN | 2026-04-13 | Business | Chuyển `is_sales_channel = false`, doanh thu = 0đ |
| Telesale & CS = bán hàng thật (Offline/Direct Sales) | ĐÃ XÁC NHẬN | 2026-04-13 | Business | Chuyển sang `is_sales_channel = true` |
| Thêm `order_nature` dimension | ĐỀ XUẤT | — | — | 7 giá trị: retail_sale, wholesale, cross_border_fulfillment, staff_benefit, gift, test, affiliate |
| Customer tagging cho khách sỉ ẩn | ĐÃ SCAN | 2026-05-26 | Data | 36 khách tìm được, chờ Sales xác nhận (file: wholesale-customers-review-260526.csv) |
| Gosumo, POPS, Leflair, Selly, Chiaki có nên giữ hay archive? | CẦN XÁC NHẬN | — | Business | Các kênh inactive |

---

## Phân tích vấn đề

### Vấn đề 1: "US" channel — Cross-border fulfillment bị lẫn vào doanh thu VN

| Metric                     | Giá trị                 |
| -------------------------- | ------------------------- |
| Số đơn                  | 11,540                    |
| Gross revenue              | 514 tỷ                   |
| Discount                   | 473 tỷ (82.7%)           |
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

### Vấn đề 2: "Đại Lý" — Giá sỉ bị coi như discount promotion

| Metric       | Giá trị |
| ------------ | --------- |
| Số đơn    | 11,152    |
| AOV          | 6.17M     |
| Avg discount | 46.8%     |

**Bản chất:** Discount 40-50% là **giá sỉ cố định**, không phải promotion.

**Hậu quả:** Khi mix với Shopee (D% 29%), Lazada (D% 14%), metric "discount rate" trung bình bị sai bản chất. Không thể so sánh "hiệu quả promotion" giữa kênh sỉ và kênh lẻ.

### Vấn đề 3: Internal channels — Rủi ro lọt vào báo cáo

| Channel            | Đơn | Gross      | Net        | Avg D% | Bản chất                             | Phân loại                                                     |
| ------------------ | ----- | ---------- | ---------- | ------ | -------------------------------------- | --------------------------------------------------------------- |
| Quà Tặng         | 788   | 9.2 tỷ    | 6.5 triệu | 78.7%  | Cho hàng miễn phí                   | Internal —`is_sales_channel = false`                         |
| Ưu đãi NV       | 1,292 | 6.6 tỷ    | 594 triệu | 77.8%  | Giá nhân viên                       | Internal —`is_sales_channel = false`                         |
| Test SP            | 76    | 274 triệu | 78 triệu  | 77.9%  | Đơn test                             | Internal —`is_sales_channel = false`                         |
| **Telesale** | 36    | 291 triệu | 115 triệu | 42.4%  | **Bán thật** qua điện thoại | **Offline / Direct Sales** — `is_sales_channel = true` |
| **CS**       | 88    | 252 triệu | 145 triệu | 32.9%  | **Bán thật** qua chat/hotline  | **Offline / Direct Sales** — `is_sales_channel = true` |

**ĐÃ XÁC NHẬN (2026-04-13):** Telesale và CS là team bán hàng, không phải hoạt động nội bộ. Đơn do staff tạo thủ công khi khách mua trực tiếp → doanh thu thật. Chuyển sang `Offline / Direct Sales`.

**Lưu ý dual-dimension:** CS/Telesale là team (ai chốt đơn), không phải kênh (khách đến từ đâu). Khi CS tạo đơn thủ công trong Sapo, thông tin kênh gốc (Shopee, FB...) bị mất. Mô hình dual-dimension (track cả channel + team) được cân nhắc nhưng **chưa cần** với volume hiện tại (124 đơn, 0.2% tổng). Nếu CS/Telesale scale lên → nâng cấp bằng quy ước source name (`CS-Shopee`, `Telesale-Zalo`).

Với các source Internal còn lại: `is_sales_channel = false` — báo cáo cần **luôn luôn** filter theo nó. Nếu quên → sai lệch nặng, đặc biệt Quà Tặng (9.2 tỷ gross bị inflate).

### Vấn đề 4: "Other" channel — Thùng rác không phân loại

| Metric       | Giá trị |
| ------------ | --------- |
| Số đơn    | 2,568     |
| Net revenue  | 5.2 tỷ   |
| Avg discount | 26.5%     |

**Mix lẫn nhiều loại:**

- Khách VIP mua qua DM/điện thoại (Huynh Tri Bao, Trần Thị Thanh Trang)
- CTV/cộng tác viên (Anh Long - CTV OTC: 100% discount, Fine Japan-USA: 100% discount)
- Đơn không xác định source
- Khách sỉ ẩn (Quang: D% 65%, chị Quyên: D% 52%)

**Hậu quả:** Không thể phân tích "Other" vì bản chất đơn quá khác nhau.

### Vấn đề 5: Khách sỉ ẩn trên kênh B2C (Zalo, Facebook, Other, Web, POS)

> **Scan thực tế 2026-05-26** trên 14,640 đơn completed/finalized. Tiêu chí: ≥3 đơn, avg_net ≥2M, avg_disc ≥40%, kênh không phải Marketplace/B2B. Tất cả đang label `RETAIL` trong Sapo.

**Nhóm 1 — Chắc sỉ (D% ≥ 55%):** cần tag ngay

| Tên | customer_id | Kênh | Đơn | Avg net | D% | Tổng net | Suggest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Nguyễn Hiếu | 79472464 | Web/Social/Other | 17 | 5.0M | 72.9% | 85.6M | WHOLESALE |
| Quang | 149453741 | POS | 21 | 3.9M | 68.4% | 81.7M | WHOLESALE |
| Huynh Tri Bao | 78229451 | Other | 4 | 41.3M | 64.4% | 165.1M | WHOLESALE |
| Huỳnh Thị Tuyết Trinh | 68945207 | Web/CS | 27 | 3.6M | 62.1% | 96.0M | WHOLESALE |
| Petter Phạm (Tuấn) | 86375978 | Facebook | 6 | 16.9M | 59.9% | 101.1M | WHOLESALE |
| Lê Sơn | 70316860 | Other/Web | 27 | 2.7M | 59.1% | 72.1M | WHOLESALE |
| Lê Sơn *(trùng account)* | 70335461 | Web | 15 | 4.1M | 58.0% | 61.8M | WHOLESALE |
| chị Quyên | 95370464 | Zalo/Other | 15 | 4.0M | 57.9% | 59.6M | WHOLESALE |
| Boilam Vo Xuan | 65532663 | Zalo | 5 | 10.0M | 56.2% | 49.9M | WHOLESALE |
| Chị Lan | 239274863 | Facebook | 6 | 19.4M | 55.0% | 116.6M | WHOLESALE |

**Nhóm 2 — Cần Sales xác nhận (D% 40–55%):**

| Tên | customer_id | Kênh | Đơn | Avg net | D% | Tổng net | Suggest |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Chị Phúc | 172107018 | Other | 6 | 5.6M | 52.5% | 33.8M | WHOLESALE |
| Chị Hương | 319507511 | POS | 5 | 22.0M | 50.0% | 110.0M | WHOLESALE |
| Nguyễn Hữu Tin-Vy | 90666716 | Other | 6 | 14.7M | 50.0% | 88.0M | WHOLESALE |
| chị Uyên - Q.10 | 97171938 | Other | 9 | 8.9M | 50.0% | 80.1M | WHOLESALE |
| Hoa | 88153319 | Web | 6 | 13.0M | 50.0% | 78.0M | WHOLESALE |
| Lê Như Quỳnh | 92267253 | Other | 6 | 12.0M | 50.0% | 72.0M | WHOLESALE |
| Mr. Tùng Lương | 177458829 | POS | 6 | 10.8M | 50.0% | 64.8M | WHOLESALE |
| Oanh (Em chị Thúy) | 88477834 | Other | 6 | 8.9M | 50.0% | 53.4M | WHOLESALE |
| Chị Oanh Trần | 148469182 | Web | 6 | 7.4M | 50.0% | 44.5M | WHOLESALE |
| Chị Chi | 79187492 | Zalo | 6 | 6.0M | 50.0% | 36.0M | WHOLESALE |
| Chị Hân | 74157070 | Zalo | 6 | 5.4M | 50.0% | 32.4M | WHOLESALE |
| Đỗ Công Hoàng | 82948658 | Other | 5 | 4.0M | 50.0% | 20.0M | WHOLESALE |
| Mỹ Linh | 84750850 | Zalo | 6 | 3.1M | 50.0% | 18.9M | WHOLESALE |
| Nguyễn Phước | 65145138 | Facebook | 6 | 2.2M | 50.0% | 13.2M | WHOLESALE |
| Hải Yến | 76922905 | Facebook | 3 | 4.2M | 50.0% | 12.6M | WHOLESALE |
| Chị Hạnh | 245989142 | CS | 6 | 4.7M | 46.7% | 28.5M | WHOLESALE |
| Anh Bảo | 162655294 | POS | 6 | 6.6M | 41.3% | 39.6M | WHOLESALE |
| Thanh Phi | 80771948 | Zalo/Other | 12 | 6.0M | 41.1% | 71.8M | WHOLESALE |
| Mai Huong Nguyen Thi | 509658015 | Facebook | 6 | 2.2M | 40.0% | 13.0M | WHOLESALE |
| Thảo | 78799140 | Zalo | 6 | 2.2M | 40.0% | 13.0M | WHOLESALE |
| Anh Khoa | 77450203 | Facebook | 6 | 2.2M | 40.0% | 13.0M | WHOLESALE |

**Nhóm 3 — Business account (tên shop/nhà thuốc):** tag PARTNER

| Tên | customer_id | Kênh | Đơn | D% | Tổng net | Suggest |
| --- | --- | --- | --- | --- | --- | --- |
| Gosumo - Hạ Vàng | 271015099 | Other | 6 | 49.7% | 13.0M | PARTNER |
| Michiko Shop | 317992826 | Web | 12 | 47.0% | 77.5M | PARTNER |
| PHANO | 64548474 | POS | 6 | 44.8% | 36.4M | PARTNER |
| JAPANA | 64552850 | Web/POS | 12 | 43.3% | 101.1M | PARTNER |
| Nhà thuốc Helios | 219286557 | Web | 6 | 43.3% | 28.2M | PARTNER |

**Đặc điểm chung:** discount cố định 40–73%, mua lặp lại, AOV cao.

**Ghi chú kỹ thuật:**
- Lê Sơn có 2 customer_id — cùng 1 người, trùng account Sapo
- File xác nhận Sales: `plans/reports/wholesale-customers-review-260526.csv`

**Hậu quả:** Kênh Zalo, Facebook, Other, Web bị kéo lệch D% bởi nhóm này → discount analysis B2C sai nếu không filter `customer_type = 'RETAIL'`.

---

## Tổng hợp phân bổ doanh thu hiện tại

| Category               | Segment | Market   | Đơn  | Net (tỷ) | Disc% | Ghi chú                                                 |
| ---------------------- | ------- | -------- | ------ | --------- | ----- | -------------------------------------------------------- |
| Ecommerce              | B2C     | Domestic | 22,168 | 38.5      | 28.8% | Kênh bán lẻ chính                                    |
| Offline                | B2B     | Domestic | 11,156 | 68.8      | 46.8% | Đại Lý — giá sỉ                                    |
| Other                  | B2B     | Export   | 11,540 | 41.0      | 82.7% | **US — inter-company**                            |
| Other                  | B2C     | Domestic | 2,584  | 5.2       | 26.7% | Thùng rác                                              |
| Offline                | B2C     | Domestic | 1,560  | 2.6       | 25.5% | POS retail                                               |
| Offline / Direct Sales | B2C     | Domestic | 124    | 0.3       | 38.0% | **Telesale + CS — bán thật**                    |
| Internal               | B2C     | Domestic | 2,156  | 0.6       | 78.5% | Không phải bán hàng (Quà Tặng, Ưu đãi NV, Test) |

---

## Đề xuất giải pháp

### Thêm lớp "Bản chất đơn hàng" (Order Nature)

#### Định nghĩa order_nature

Bổ sung cho hệ thống channel hiện tại, không thay thế.

| order_nature                       | Mô tả                                                   | Cách xác định                                        |
| ---------------------------------- | --------------------------------------------------------- | -------------------------------------------------------- |
| **retail_sale**              | Bán lẻ, giá thị trường                              | Kênh B2C + customer_type != wholesale                   |
| **wholesale**                | Bán sỉ, giá chiết khấu cố định                    | Đại Lý, Chợ sỉ + khách sỉ ẩn trên Zalo/FB/Other |
| **cross_border_fulfillment** | Giao hàng tại VN cho khách FG Care US, doanh thu = 0đ | US channel — thanh toán theo hợp đồng B2B riêng    |
| **staff_benefit**            | Ưu đãi nhân viên                                     | Ưu đãi Nhân Viên                                    |
| **gift**                     | Quà tặng, hàng cho                                     | Quà Tặng                                               |
| **test**                     | Đơn test                                                | Test Sản Phẩm                                          |
| **affiliate**                | CTV bán hàng                                            | Khách có tag CTV, discount ~100%                       |

#### Cách identify "khách sỉ ẩn" trên kênh B2C

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

#### Xử lý US channel

| Thuộc tính     | Hiện tại      | Đề xuất                             |
| ---------------- | --------------- | -------------------------------------- |
| channel_format   | Other           | **CrossBorder** (giá trị mới) |
| is_sales_channel | true (implicit) | **false**                        |
| channel_category | Other           | **Internal**                     |
| order_nature     | (chưa có)     | **cross_border_fulfillment**     |

**Lý do:** US không phải bán hàng của FG Care VN. Doanh thu thuộc FG Care US, VN chỉ thực hiện fulfillment theo hợp đồng B2B riêng. Ghi nhận doanh thu = 0đ.

→ Mặc định loại khỏi mọi báo cáo doanh thu VN.

#### Xử lý "Other" channel

Tách "Other" thành các nguồn cụ thể hơn nếu có thể identify qua tags/notes trong Sapo:

| Nhóm          | Cách identify                                    | Xử lý                     |
| -------------- | ------------------------------------------------- | --------------------------- |
| Khách VIP/DM  | customer_type = retail, AOV cao                   | Giữ nguyên B2C            |
| Khách sỉ ẩn | customer_type = wholesale (từ ref_customer_tags) | Gom vào wholesale          |
| CTV            | customer_type = ctv                               | Tách riêng affiliate      |
| Không rõ     | Còn lại                                         | Giữ "Other" nhưng monitor |

---

## Report Grouping khuyến nghị

### Báo cáo doanh thu bán hàng (mặc định)

```
WHERE is_sales_channel = true
  AND order_nature IN ('retail_sale', 'wholesale')
```

Loại: US, Internal, Gift, Test, CTV 100%.

### Hiệu quả kênh Ecommerce (B2C thuần)

```
WHERE channel_category = 'Online-Ecommerce'
  AND order_nature = 'retail_sale'
```

Loại: khách sỉ ẩn trên Zalo/Facebook → so sánh discount giữa các kênh mới chính xác.

### Báo cáo kênh sỉ (tách riêng)

```
WHERE order_nature = 'wholesale'
```

Gom: Đại Lý + Chợ sỉ + khách sỉ ẩn trên Zalo/FB/Other. Metric discount ở đây là giá sỉ, không phải promotion.

### P&L tổng hợp

```
WHERE is_sales_channel = true
  AND order_nature NOT IN ('test', 'gift')
```

Gồm cả wholesale, staff benefit. Loại test và gift.

### Discount analysis

**PHẢI** tách riêng:

- **Retail discount:** promotion/coupon thật → so sánh Shopee vs Lazada vs Web
- **Wholesale discount:** giá sỉ cố định → không so sánh với retail
- **Internal discount:** giá NV, quà tặng → loại khỏi analysis

---

## Implementation Roadmap

**Phase 1 — Quick wins** (1-2 tuần, seed changes)
- Sửa `ref_order_sources.csv`: US → `channel_format = 'CrossBorder'`, `is_sales_channel = false`
- Sửa `ref_order_sources.csv`: Telesale, CS → `channel_format = 'Direct'`, `channel_type = 'Direct Sales'`, `is_sales_channel = true`
- Cập nhật `dim_channels.sql`: thêm `CrossBorder` → `channel_category = 'Internal'`, `Direct Sales` → `channel_category = 'Offline'`

**Phase 2 — Customer tagging** (1 tuần)
- Tạo `ref_customer_tags.csv` với danh sách khách sỉ/CTV đã biết (~20-50 khách)
- Thêm `customer_type` vào `dim_customers` (LEFT JOIN ref_customer_tags)

**Phase 3 — Order nature derivation** (1 tuần, code mới)
- Thêm `order_nature` vào `fact_orders` / `fact_sales`, derive từ channel + customer_type
- Logic: CrossBorder/Internal/Staff/Gift/Test → trực tiếp; customer_type wholesale → wholesale; còn lại → retail_sale

**Phase 4 — Report templates** (1 tuần)
- Cập nhật Metabase dashboards với filter mặc định theo order_nature
- Tạo dashboard riêng cho kênh sỉ

---

## Những hiểu nhầm thường gặp

1. **"Discount sỉ ≠ discount promotion"** — Đại Lý có D% 46.8% là giá cố định, không phải KM. Không so sánh với Shopee D% 29%.

2. **"US channel = bán hàng VN ≠ US channel = fulfillment"** — FG Care VN chỉ giao hàng tại VN cho khách FG Care US. Doanh thu = 0đ, thanh toán theo hợp đồng B2B riêng.

3. **"Other = kênh ≠ Other = chưa phân loại"** — Other chứa khách VIP, CTV, khách sỉ ẩn, đơn không rõ. Cần tách riêng, không thể so sánh metric.

4. **"Doanh thu gross ≠ doanh thu thật khi US inflate"** — US có gross 514 tỷ nhưng net ~0đ. Filter `is_sales_channel = true` bắt buộc trong báo cáo doanh thu.

---

## Câu hỏi cần xác nhận từ Business

| Câu hỏi | Trạng thái | Ghi chú |
|--------|-----------|---------|
| US channel: Có đơn US nào là bán thật cho khách Mỹ không? | **ĐÃ XÁC NHẬN** | 100% cross-border fulfillment, doanh thu = 0đ |
| Telesale + CS: Nên tính là doanh thu bán hàng hay internal? | **ĐÃ XÁC NHẬN** | Doanh thu bán hàng thật, chuyển Offline/Direct Sales |
| Khách sỉ Zalo/Facebook/Other/Web/POS: Danh sách bao nhiêu người? | **ĐÃ SCAN** | 36 khách, xem Vấn đề 5. Chờ Sales xác nhận từng người |
| Discount 40-73% trên B2C channels: Giá sỉ cố định hay promotion từng đơn? | **CẦN XÁC NHẬN** | Sales điền cột xac_nhan_sales trong CSV |
| "Gosumo", "POPS", "Leflair", "Selly", "Chiaki" nên giữ hay archive? | **CẦN XÁC NHẬN** | Các kênh inactive |
| "Other" channel: Có tag/note nào trong Sapo phân biệt VIP/CTV/sỉ? | **CẦN XÁC NHẬN** | Giúp tách "Other" dễ hơn |

---

## Kết luận

**"Để báo cáo doanh thu chính xác, ta cần tách riêng bán sỉ, bán lẻ, nội bộ thay vì trộn chung — đó là bước đầu nâng cấp từ channel classification sang business classification."**
