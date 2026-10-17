---
title: "Review thiết kế taxonomy engine: góc nhìn Head of Analytics / BI"
reviewer: brainstormer (persona BI lead phục vụ CEO, CFO, Marketer)
date: 2026-10-14
target: taxonomy-engine-design.md (§3, §5, §8)
---

# Review: bộ mã chuẩn và khả năng giữ report chuẩn có nghĩa

## 0. Kết luận ngắn

Tôi đồng ý với mô hình "nhãn riêng + mã chuẩn bắt buộc". Tôi không đồng ý với giả định ngầm của §5 rằng phạm vi doanh thu (`scope_*`) là thuộc tính của **khách**. Code hiện tại của chính Fine Japan đã cho thấy điều ngược lại: `scope_b2b` trong `fact_orders.sql` (dòng 215–219) là `customer_type IN (WHOLESALE, PARTNER) OR channel_format = 'B2B'`, tức phạm vi là thuộc tính của **đơn**. Tài liệu `segments.md` mô tả sai điều này (chỉ ghi `customer_type`), và đó chính là loại lệch mà bộ máy sinh ra để xoá.

Ba sửa đổi quan trọng nhất, xếp theo tác động lên số liệu báo cáo:

1. Thêm một domain dẫn xuất cấp đơn, `sales_line` (bản chất thương mại của đơn), làm **đầu ra duy nhất** của bảng quyết định. `scope_*` chỉ còn là phép kiểm tra thuộc tập trên `sales_line_std`.
2. Cho phép nhãn riêng **neo vào nút cha** của cây mã chuẩn (không chỉ nút lá hoặc `OTHER`), để report chuẩn chạy ở cấp 1 dù doanh nghiệp không phân biệt được cấp 2.
3. Tách `discount_purpose` theo cây ba nhánh PROMOTIONAL / STRUCTURAL_PRICE / NON_REVENUE. Không có cây này thì không tenant nào làm được báo cáo khuyến mãi đúng nghĩa.

## 1. Giả định bị chất vấn

| Giả định trong bản thiết kế | Vì sao sai hoặc thiếu | Hệ quả nếu giữ nguyên |
|---|---|---|
| `customer_type` quyết định scope | Đại lý chưa gắn nhóm vẫn đặt qua nguồn "Đại Lý"; khách CROSSBORDER mua lẻ trên Shopee bị rơi khỏi cả `scope_retail` lẫn `scope_b2b` nhưng vẫn ở `scope_sales` | Rò doanh thu giữa các scope, không giải thích được với CFO |
| Một bộ mã đóng rút từ một doanh nghiệp là đủ tổng quát | Các bộ §5 lặp lại đúng cách chia của Fine Japan (PARTNER gộp ký gửi + CTV, KOL gộp người mua và người bán hộ) | Doanh nghiệp thứ hai phải neo vào `OTHER`, report chuẩn mất nghĩa |
| "Restate cho mọi kỳ" an toàn với report | Đúng với nhãn sự kiện; sai với chỉ tiêu đã giao, thưởng đã chốt và xu hướng số khách theo hạng/vòng đời | Biểu đồ "số khách AT_RISK theo tháng" không vẽ được; tỷ lệ đạt chỉ tiêu tháng cũ tự đổi |
| "Doanh thu" là một khái niệm | Fine Japan đang có hai: P&L gồm cả Ưu đãi NV (594 triệu net), còn `scope_sales` loại nó | CEO và CFO nhìn hai con số khác nhau mà không biết vì sao |

## 2. (a) Phê bình từng bộ mã chuẩn ở §5

### 2.1 Kênh (§5.1)

**`platform`**: thiếu giá trị đã có trong dữ liệu: Sendo và Grab (`sales-segmentation-guide.md` §3.1). Thêm SENDO, GRAB và một mã cho app giao đồ ăn/đi chợ nhanh (SHOPEE_FOOD hoặc gom chung QUICK_COMMERCE). Nguồn "Wholesale", "Direct", "System" hôm nay không phải nền tảng; cần map sang `NOT_APPLICABLE`. Vì `platform` gần với danh mục id hơn là phân loại, nên cho phép sản phẩm thêm mã nhanh (vẫn có changelog). Nếu không, các nền tảng nhỏ mà merchant thật sự dùng sẽ bị gom vào OTHER và biến mất khỏi báo cáo kênh.

**`channel_format`**: có hai lỗi trục.
- `NON_SALES` là mục đích đơn, không phải hình thức kênh. Khi đã có `order_purpose` thì giữ `NON_SALES` ở đây sẽ tạo ra hai nguồn sự thật cho "đơn này có phải bán hàng không". Đề xuất bỏ `NON_SALES`; các nguồn như Quà Tặng, Test SP map `channel_format = NOT_APPLICABLE` và `order_purpose` mang nghĩa.
- `B2B` vẫn được giữ, nhưng phải định nghĩa hẹp: "kênh đặt hàng chỉ dành cho khách sỉ" (cổng đại lý, sales sỉ nhập đơn). Định nghĩa này có tiền lệ ở Shopify (`is_b2b_order`) và Nhanh. Hệ quả cần ghi rõ: `channel_format = B2B` **tự động** đẩy đơn vào nhánh B2B của `sales_line`, bất kể khách đã được gắn loại hay chưa.
- Đổi `SOCIAL` thành `SOCIAL_CHAT` (đơn chốt qua inbox FB/Zalo/IG) để không nhầm với TikTok Shop. TikTok Shop là `MARKETPLACE` về mặt dữ liệu và phí; yếu tố nội dung thuộc `content_carrier`.

**`channel_category`**: bỏ INTERNAL vì lý do giống trên; chỉ giữ ONLINE / OFFLINE. Quan hệ cha–con với `channel_format` chỉ đúng khi mỗi hình thức có một cha duy nhất. `B2B` và `DIRECT_SALES` có thể online hoặc offline, nên phải chốt theo quy ước (OFFLINE = bán có người hỗ trợ) và ghi quy ước đó vào mô tả mã.

**Thiếu `market`** (DOMESTIC, EXPORT). Seed `ref_order_sources.csv` đã có cột này nhưng §5 bỏ sót. CFO cần doanh thu xuất khẩu riêng vì thuế suất GTGT 0% và chứng từ khác.

**`order_purpose`**: hướng đúng, cấu trúc chưa đúng.
- `STAFF_BENEFIT` trộn mục đích với người mua. Nhân viên mua giá ưu đãi vẫn là **bán hàng có hoá đơn và thu tiền**, nên là `SALE` với khách `STAFF` và chính sách giá `STAFF_PRICE`. Việc loại khỏi báo cáo hiệu quả kinh doanh là quyết định của `sales_line`, không phải của mục đích.
- Cần dạng cây để tenant không phân biệt được chi tiết vẫn neo được:
  - `SALE`
  - `NON_REVENUE` → `GIFT` (biếu, tặng khách), `SAMPLE` (sampling), `KOL_SEEDING` (gửi hàng cho KOL), `TEST`, `INTERNAL_USE`
  - `AFTER_SALES` → `REPLACEMENT`, `EXCHANGE`
  - `SERVICE` → `FULFILLMENT_SERVICE`
  - `STOCK_MOVEMENT` → `CONSIGNMENT_TRANSFER`, `INTERNAL_TRANSFER` (Nhanh type 15, 17)
- Lý do tách `KOL_SEEDING` khỏi `GIFT`: Marketer cần biết giá vốn hàng gửi KOL như một khoản chi marketing, còn quà tặng khách là chi phí chăm sóc khách.
- `order_purpose` để `single` ở cấp đơn là đúng. Quà tặng **dòng hàng** trong đơn bán (Nhanh `gifts[]`, Pancake `accessory`) thuộc tầng dòng hàng, không được làm đơn đổi mục đích.

**`seller_role`**: giữ, nhưng chỉ dành cho **người bán hộ** (affiliate, CTV hưởng hoa hồng). Không được dùng lại để biểu diễn người mua (xem §4).

### 2.2 Khách hàng (§5.2)

**`customer_type`** là chỗ cần sửa nhiều nhất. Bộ đề xuất (RETAIL, WHOLESALE, PARTNER, STAFF, KOL_AFFILIATE, OTHER) có ba vấn đề:
- `PARTNER` gộp ba mô hình kinh tế khác nhau: đại lý nhỏ (mua đứt, bán lại), ký gửi (chưa ghi nhận doanh thu khi xuất hàng theo VAS 14 / IFRS 15) và CTV có hợp đồng. CFO cần tách ký gửi.
- `KOL_AFFILIATE` gộp người **mua** (KOL nhận hàng hoặc mua giá ưu đãi) với người **bán hộ** (affiliate hưởng hoa hồng trên đơn của khách khác). Đây là hai trục khác nhau.
- Thiếu bên liên quan (RELATED_PARTY). Doanh nghiệp nhỏ ở Việt Nam rất thường có nhiều pháp nhân hoặc hộ kinh doanh mua bán chéo; VAS 26 yêu cầu trình bày giao dịch với bên liên quan. "Fine Japan-USA" xuất hiện ở kênh Other với chiết khấu 100% chính là trường hợp này.

Đề xuất cây (cấp 1 dùng cho report chuẩn, cấp 2 tuỳ chọn):

| Cấp 1 | Cấp 2 | Ví dụ nhãn Fine Japan |
|---|---|---|
| CONSUMER | (lá) | RETAIL |
| TRADE | WHOLESALE, RESELLER, CONSIGNEE, CORPORATE | WHOLESALE → WHOLESALE; PARTNER → neo thẳng vào `TRADE` |
| INTERNAL | STAFF, RELATED_PARTY | STAFF; CROSSBORDER (tạm thời, xem §4) |
| CREATOR | KOL | KOL |
| OTHER | | |

Mã `CONSUMER` thay cho `RETAIL` để không trùng chữ với `RETAIL_STORE` của kênh; nhãn riêng của Fine Japan vẫn là `RETAIL` nên hợp đồng cột mart không đổi. `CORPORATE` (doanh nghiệp mua để dùng hoặc làm quà) là B2B nhưng không bán lại; nhóm này phổ biến ở mùa Tết.

Mặc định của domain vẫn nên là CONSUMER, vì phần lớn khách không có tín hiệu. Đổi lại, phải có báo cáo "khách nghi sỉ" dùng luật chia ngưỡng (≥3 đơn, AOV ≥ 2 triệu, chiết khấu ≥ 40%, như bản quét 26/05) sinh **cờ gợi ý**, không sinh nhãn. Nghiệp vụ xác nhận bằng gán tay `manual_wins`.

**`value_tier`**: bộ mã đúng. Có hai điều kiện để report có nghĩa: tính trên cửa sổ 12 tháng gần nhất thay vì trọn đời (Fine Japan hiện tính trọn đời), và tính ngưỡng **trong từng nhánh cấp 1 của `customer_type`**. Nếu không, đại lý chiếm hết hạng TOP và chương trình chăm sóc VIP bán lẻ trở nên vô nghĩa.

**`rfm_segment`**: dùng 8 nhóm Quick Audience là hợp lý. Chỉ tính cho CONSUMER; nhóm khác ra `NOT_APPLICABLE`. Giá trị so sánh (trung bình có trọng số) phải chốt theo kỳ trong `taxonomy_param`.

**`lifecycle_stage`**: bộ mã đúng. Thiếu một quy định quan trọng là **đơn nào được tính**: đơn quà tặng, đơn bảo hành hay đơn nhân viên không được làm khách thành ACTIVE. Đặc trưng `last_order_at`, `order_count`, `total_spend` phải tính trên đơn có `order_purpose_std = SALE` và trạng thái hợp lệ. Ngưỡng 30/90/180 ngày phải là tham số tenant theo chu kỳ mua lại của ngành hàng (china.md §5.4).

**`payment_behavior`** trộn phương thức (PREPAID, COD) với tình trạng công nợ (DELINQUENT). Nên tách thành `payment_preference` (PREPAID, COD, CREDIT_TERMS) cho mọi khách và `credit_status` (CURRENT, OVERDUE) chỉ cho TRADE.

**`acquisition_source`**: đổi tên thành `first_order_channel`. "Nguồn thu hút" theo nghĩa marketing (đến từ KOL, quảng cáo) cần dữ liệu attribution mà dẫn xuất từ đơn đầu không trả lời được. Giữ tên cũ sẽ khiến Marketer hiểu sai.

**`geo_region`**: bảng tỉnh → vùng phải có phiên bản, vì từ 01/07/2025 Việt Nam sáp nhập từ 63 xuống 34 tỉnh. Địa chỉ cũ và mới cùng tồn tại trong dữ liệu đơn.

### 2.3 Đơn, giảm giá, phí (§5.3)

**`order_status`**: thiếu `FAILED_DELIVERY` (giao thất bại, hoàn về). Với đơn COD ở kênh social, tỷ lệ hoàn thường lên hai con số; gộp vào RETURNED làm mất chỉ số vận hành quan trọng nhất của kênh này. Trả hàng một phần cũng không biểu diễn được bằng một trạng thái; nên để trả hàng ở chỉ số đảo doanh thu (giống `sales_reversals` của Shopify) thay vì ép vào trạng thái.

**`discount_purpose`**: trộn **cơ chế** (VOUCHER, BUNDLE) với **mục đích** (CAMPAIGN, STAFF, PRICE_POLICY). Đề xuất cây:

| Cấp 1 | Cấp 2 | Có vào báo cáo khuyến mãi? |
|---|---|---|
| PROMOTIONAL | VOUCHER, MARKDOWN_CAMPAIGN, BUNDLE, LOYALTY_REDEMPTION, SHIPPING_SUBSIDY | Có |
| STRUCTURAL_PRICE | WHOLESALE_PRICE, STAFF_PRICE, CREATOR_PRICE, CONTRACT_REBATE (CK SAU) | Không; là giá theo chính sách |
| DISCRETIONARY | NEGOTIATED | Báo cáo riêng (rò rỉ giá do nhân viên tự giảm) |
| NON_REVENUE | GIFT_FULL, SAMPLING | Không; đơn không phải doanh thu |

10 loại của Fine Japan neo được hết: `wholesale_explicit` → WHOLESALE_PRICE, `employee_internal` → cấp 1 NON_REVENUE hoặc STAFF_PRICE (cần tách CTV ra), `negotiated_*` → NEGOTIATED, `overseas` → NON_REVENUE. Báo cáo khuyến mãi phải cộng ở **cấp dòng giảm giá**, không qua `primary_discount_type` (`MAX_BY`), vì một đơn có thể vừa voucher vừa giá sỉ.

**`discount_funder`**: `LOYALTY` là cơ chế, không phải bên chịu tiền (điểm thưởng do người bán chịu). Chuyển LOYALTY sang `discount_purpose`; thêm `SUPPLIER` (nhà cung cấp hoặc hãng tài trợ, phổ biến ở nhà phân phối).

**`fee_type`**: đạt. Chỉ cần ghi rõ AFFILIATE ở đây là chi phí, khớp với `seller_role` ở cấp đơn để tính ROI affiliate.

## 3. (b) `scope_*` và khuyến mãi có biểu diễn được bằng bảng quyết định cho mọi tenant không?

**Có, nếu thêm `sales_line`.** Ba phương án khác nhau thật sự:

| Phương án | Mô tả | Độ phức tạp | Giải thích cho người dùng | Rủi ro |
|---|---|---|---|---|
| A. Giữ như §5 | `scope_*` là bảng quyết định trên ba domain, tính thẳng ra boolean | Thấp (0 domain mới) | Kém: muốn biết vì sao đơn rơi khỏi retail phải đọc ba cột | Ba boolean có thể chồng hoặc hở mà không ai thấy |
| **B. `sales_line` cấp đơn (khuyến nghị)** | Một bảng quyết định ~8 dòng, `hit_policy = FIRST`, ra một mã; `scope_*` = thuộc tập | Thêm 1 domain, 1 bảng | Tốt: một cột, một `rule_id`, tổng các nhánh luôn khớp tổng đơn | Cần thứ tự DAG đúng (bên dưới) |
| C. Bỏ scope, report luôn tách theo nhánh | Kiểu Shopify: chiều thay vì bộ lọc | Cao: thiết kế lại mọi dashboard | Tốt nhất về đối soát | Biểu đồ AOV, khuyến mãi vẫn cần lọc; chi phí chuyển đổi lớn |

B là phương án đơn giản nhất vẫn đáp ứng yêu cầu. Bảng quyết định đề xuất (sản phẩm sở hữu, chỉ dùng mã chuẩn):

| # | Điều kiện | `sales_line_std` |
|---|---|---|
| 1 | `order_purpose_std` thuộc nhánh NON_REVENUE / AFTER_SALES / STOCK_MOVEMENT | `NON_REVENUE` (giữ mã cấp 2 để drill-down) |
| 2 | `order_purpose_std` = FULFILLMENT_SERVICE hoặc `customer_type_std` = RELATED_PARTY | `INTERCOMPANY` |
| 3 | `channel_format_std` = B2B | `B2B` |
| 4 | `customer_type_std` thuộc nhánh TRADE | `B2B` |
| 5 | `customer_type_std` = STAFF | `STAFF` |
| 6 | `customer_type_std` thuộc nhánh CREATOR | `CREATOR` |
| 7 | `customer_type_std` ∈ {UNMAPPED, UNKNOWN} | `CONSUMER` nhưng ghi `rule_id` riêng để đo độ phủ |
| 8 | Còn lại | `CONSUMER` |

Khi đó: `scope_retail = sales_line_std = CONSUMER`; `scope_b2b = B2B`; `scope_sales = {CONSUMER, B2B} ∪ tham số tenant {STAFF, CREATOR}`. Phần khác nhau giữa tenant (Fine Japan đang tính STAFF và KOL vào `scope_sales`) là **tham số**, không phải luật. Nhờ vậy Fine Japan vẫn ra 0 khác biệt, và tenant khác không phải viết SQL. `is_active_order` là bảng một dòng trên `order_status_std ∉ {CANCELLED, DRAFT}`. Đề xuất thêm `scope_revenue` = mọi `sales_line` có giá > 0 trừ NON_REVENUE, để CFO đối soát với sổ kế toán. Hai con số "doanh thu bán hàng" và "doanh thu kế toán" sẽ có tên khác nhau thay vì lệch ngầm.

Dòng 3 thay luôn cách vá hiện tại ("~92 đại lý vẫn gắn RETAIL" ở `fact_orders.sql`) bằng một luật sản phẩm dùng được cho mọi tenant.

**Thứ tự phụ thuộc phải giữ:** nhãn nguồn đơn → `order_purpose` → đặc trưng khách (chỉ trên đơn SALE) → `customer_type` → `sales_line`. `customer_type` không được dùng đặc trưng tính trên `sales_line`, nếu không sẽ quay lại đúng vòng phụ thuộc mà comment trong `fact_orders.sql` đang né.

**Khuyến mãi** biểu diễn được cho mọi tenant: "chi phí khuyến mãi người bán chịu" = tổng dòng giảm giá có `discount_purpose_std` thuộc PROMOTIONAL và `discount_funder_std = SELLER`, trên đơn `sales_line_std = CONSUMER` và đơn hợp lệ. Hai điều kiện để số có nghĩa: tenant phải nhận diện được STRUCTURAL_PRICE (với Sapo hiện là heuristic `reason='' AND rate=100`, khá mong manh), và report phải hiển thị độ phủ. Đề xuất thêm chỉ số `gross_at_entitled_price` (doanh thu gộp theo giá được hưởng), tức giá niêm yết trừ phần STRUCTURAL_PRICE. Nếu không, doanh thu gộp của đơn sỉ bị phồng 40–50% và tỷ lệ giảm giá toàn công ty mất nghĩa (như số 35% "vô nghĩa" trong `report_segmentation.md` §1).

## 4. (c) Ánh xạ các trường hợp khó

| Trường hợp | `order_purpose` | `channel_format` | `customer_type` (cấp 1 / cấp 2) | `seller_role` | `sales_line` | Ghi chú |
|---|---|---|---|---|---|---|
| CROSSBORDER (nguồn US) | FULFILLMENT_SERVICE | NOT_APPLICABLE | Người nhận: CONSUMER mặc định | SELF | INTERCOMPANY | Loại ở cấp đơn, không ở cấp khách |
| FG Care US / "Fine Japan-USA" làm khách | theo đơn | theo nguồn | INTERNAL / RELATED_PARTY | | INTERCOMPANY | |
| Đại Lý, Chợ sỉ (nguồn) | SALE | B2B | TRADE / WHOLESALE | SELF | B2B | `platform` = NOT_APPLICABLE; giảm giá = WHOLESALE_PRICE |
| Sỉ ẩn trên Zalo/FB/POS | SALE | kênh thật | TRADE / WHOLESALE (gán tay) | SELF | B2B | Cờ "nghi sỉ" → xác nhận → `manual_wins` |
| CTV mua đứt để bán lại | SALE | kênh thật | TRADE / RESELLER | SELF | B2B | |
| CTV giới thiệu, hưởng hoa hồng | SALE | kênh thật | Người mua: CONSUMER | CTV_RESELLER | CONSUMER | Hoa hồng là chi phí, không phải giảm giá |
| CTV nhận hàng 100% (Anh Long) | KOL_SEEDING hoặc CONSIGNMENT_TRANSFER | | TRADE | | NON_REVENUE | Cần nghiệp vụ xác nhận bản chất |
| Ký gửi | CONSIGNMENT_TRANSFER nếu xuất kho chưa bán; SALE nếu bán đứt | | TRADE / CONSIGNEE | | NON_REVENUE hoặc B2B | CFO phải chốt cách ghi nhận doanh thu |
| KOL nhận hàng gửi | KOL_SEEDING | | CREATOR / KOL | | NON_REVENUE | Báo cáo chi phí seeding theo giá vốn |
| KOL mua giá ưu đãi | SALE | | CREATOR / KOL | | CREATOR | Giảm giá = CREATOR_PRICE |
| KOL affiliate TikTok | SALE | MARKETPLACE | Người mua: CONSUMER | AFFILIATE_KOL | CONSUMER | Phí ở `fee_type = AFFILIATE` |
| Ưu đãi Nhân Viên (nguồn) | SALE | NOT_APPLICABLE | INTERNAL / STAFF (suy từ nguồn) | | STAFF | |
| Nhân viên mua trên Shopee | SALE | MARKETPLACE | INTERNAL / STAFF | | STAFF | Hôm nay được tính khác với dòng trên: mâu thuẫn cần thống nhất |

Về câu hỏi §9 "CROSSBORDER neo vào OTHER hay mã riêng": tôi trả lời **không neo ở trục khách**. CROSSBORDER là thoả thuận kinh doanh của **đơn**. Giữ nó ở `customer_type` gây hai lỗi: (1) người nhận hàng hộ sau đó tự mua lẻ thì đơn thật bị đẩy khỏi `scope_retail` (họ không phải RETAIL); (2) Marketer mất một tập khách tiềm năng có giá trị (người thân của khách Việt kiều). Thay vào đó, dùng đặc trưng `has_order_on_source(US)` làm **cờ segment** riêng. Trong bước chứng minh 0 khác biệt, nhãn `CROSSBORDER` tạm neo vào `INTERNAL` (nút cha); sau đó chuyển sang cờ như một thay đổi có đổi số, có danh sách tác động.

## 5. (d) Ý kiến cho 6 quyết định ở §8

1. **Mô hình nhãn riêng + mã chuẩn: đồng ý, kèm ba điều kiện.** (i) Cho phép neo vào nút cha; nếu không, `OTHER` sẽ phình và report chuẩn mất nghĩa đúng ở doanh nghiệp thứ hai. (ii) Mỗi mã chuẩn phải có một câu định nghĩa nghiệp vụ **và** ghi rõ nó rơi vào scope nào, để người dùng tự đọc được vì sao một đơn không vào báo cáo bán lẻ. (iii) Report chuẩn không bao giờ ẩn `UNMAPPED`; nó luôn là một dòng có số tiền, để tổng các nhánh khớp tổng doanh thu. Đây là điều kiện để CFO tin số.
2. **Thời điểm: đặt trước phase 6, nhưng thí điểm cả chuỗi `customer_type` → `sales_line` → `scope_*`.** `customer_type` một mình không làm đổi report nào; giá trị nghiệp vụ nằm ở scope. Thí điểm chuỗi này cũng kiểm luôn thứ tự DAG.
3. **Phase 4 bỏ macro nguyên văn: đồng ý.** Không ảnh hưởng report. Rủi ro duy nhất là tài liệu `segments.md` tiếp tục mô tả sai `scope_b2b`; nên sửa câu đó ngay, không đợi bộ máy.
4. **Tách kênh nhiều trục: đồng ý mạnh, có sửa.** Bỏ `NON_SALES` khỏi `channel_format` và INTERNAL khỏi `channel_category`; thêm `market`; thêm `sales_line` làm cột tổng hợp duy nhất mà dashboard chuẩn dùng. Người dùng nghiệp vụ không nên phải tự ghép ba trục; nhiều trục là để drill-down, còn một cột là để đọc. Một nguồn Sapo sẽ ra giá trị cho nhiều domain cùng lúc (Ưu đãi NV → `order_purpose`, `customer_type`); bộ máy phải hỗ trợ điều đó mà không lặp luật.
5. **Restate làm mặc định: đồng ý cho nhãn sự kiện, không đồng ý cho nhãn trạng thái khách.** Ba ngoại lệ: (i) `lifecycle_stage`, `value_tier`, `rfm_segment` cần **ảnh chụp cuối tháng** (thêm giá trị `periodic_snapshot` cho `time_semantics`); không có thì không vẽ được xu hướng số khách theo hạng và không làm được cohort. (ii) Chỉ tiêu (`seed_channel_targets`) và thưởng đã chốt phải so với số theo bộ luật lúc giao chỉ tiêu, nên cần `freeze_after_close` cho các mart thưởng, không chỉ kế toán. (iii) Mỗi lần đổi luật làm số kỳ đã báo cáo thay đổi quá ngưỡng (ví dụ 1% doanh thu một scope) phải sinh nhật ký điều chỉnh, và footer dashboard hiện `ruleset_version`. Với `customer_type`, "hiện tại" là chấp nhận được: khi phát hiện sỉ ẩn, ta **muốn** lịch sử được phân loại lại. Đánh đổi cần nói rõ: không phân tích được "khách lẻ chuyển thành đại lý" nếu chưa có scd2.
6. **Ai nhập luật: kết hợp, chia theo loại thay đổi.** Nghiệp vụ tự sửa nhãn riêng, gán tay (xác nhận khách sỉ) và ngưỡng trong khoảng cho phép. Việc neo nhãn vào mã chuẩn, bảng `sales_line` và tham số scope do mình duyệt, vì chúng đổi số trên report chuẩn. Bước xem trước bắt buộc phải hiển thị **doanh thu dịch chuyển giữa các scope**, không chỉ số bản ghi đổi nhãn. Đó là thứ CEO hỏi đầu tiên.

## 6. (e) Report nào làm được, report nào không

**Làm được cho mọi tenant (sau các sửa đổi trên):**
- Doanh thu theo `sales_line` × `channel_format` × `platform`, tổng luôn đối soát được với tổng đơn (có dòng UNMAPPED).
- Hiệu quả khuyến mãi bán lẻ, tách bên chịu tiền: % khuyến mãi người bán chịu so với sàn chịu, theo kênh.
- Doanh thu gộp theo giá được hưởng, và tỷ lệ chiết khấu sỉ thực tế so với chính sách.
- Chi phí hàng cho đi theo mục đích (quà, sampling, seeding KOL) theo giá vốn. Marketer hiện chưa có báo cáo này.
- Tỷ lệ giao thất bại / hoàn hàng theo kênh; tỷ lệ phí sàn theo `fee_type`.
- RFM, vòng đời, hạng giá trị trong tập khách CONSUMER; danh sách khách nghi sỉ chờ xác nhận.
- Khối lượng và giá vốn đơn dịch vụ / liên công ty (US) tách riêng khỏi doanh thu, để CFO thấy chi phí phục vụ mà không làm méo margin bán hàng.
- Báo cáo độ phủ phân loại: % doanh thu UNMAPPED hoặc rơi vào luật mặc định, theo domain.

**Không làm được, hoặc chỉ làm được có điều kiện:**
- So sánh giữa các doanh nghiệp theo nhãn riêng (ĐẠI LÝ CẤP 1): chỉ drill-down trong từng tenant. So sánh `value_tier` giữa tenant cũng vô nghĩa vì ngưỡng khác nhau.
- Kênh gốc của đơn do CS/Telesale nhập lại: vẫn là ô mù `DIRECT_SALES`.
- `content_carrier` và `seller_role` cho tenant chỉ dùng Sapo: API không có, nên ra UNKNOWN; ROI KOL/livestream chỉ có ở connector sàn.
- Xu hướng phân khúc khách theo tháng: không làm được nếu chưa có ảnh chụp theo kỳ.
- Chuyển đổi loại khách theo thời gian (lẻ → đại lý): cần scd2.
- Tỷ lệ chiết khấu so sánh được giữa tenant: chỉ khi tenant nhận diện được STRUCTURAL_PRICE; phải hiển thị độ phủ, không thì so sánh sai.
- Hiệu quả tăng thêm (incremental) của khuyến mãi: cần đường cơ sở, ngoài phạm vi bộ máy phân loại.

## 7. Rủi ro và hệ quả bậc hai

- **Đổi số khi thống nhất CROSSBORDER, Ưu đãi NV và scope_b2b.** Mỗi thay đổi dịch chuyển doanh thu giữa scope. Cần danh sách tác động theo tháng và user duyệt riêng từng mục, đúng như §6.4 của thiết kế.
- **Cây mã sâu làm người dùng hoang mang.** Dashboard chuẩn chỉ dùng cấp 1; cấp 2 chỉ hiện khi drill-down.
- **Neo vào nút cha làm test "nhãn → mã chuẩn là hàm" vẫn đúng**, nhưng test độ phủ phải đo theo cấp mà report dùng.
- **Tham số scope theo tenant có thể bị lạm dụng thành luật trá hình.** Nên giới hạn ở danh sách cờ đóng (`include_staff_in_sales`, `include_creator_in_sales`).

## 8. Câu hỏi còn mở cho nghiệp vụ

- Ký gửi của Fine Japan ghi nhận doanh thu lúc xuất hàng hay lúc bán được? Câu trả lời quyết định ký gửi là B2B hay NON_REVENUE.
- Đơn Ưu đãi NV có nên vào `scope_sales` không? Hôm nay đơn qua nguồn này bị loại, còn đơn của khách STAFF ở kênh khác thì được tính.
- "Anh Long - CTV OTC" chiết khấu 100%: đây là seeding, ký gửi hay hoa hồng trả bằng hàng?
- Doanh thu P&L mà CFO dùng có gồm đơn nhân viên và đơn KOL mua không? Câu trả lời xác định `scope_revenue`.

---

Status: DONE_WITH_CONCERNS
Summary: Đồng ý mô hình nhãn riêng + mã chuẩn và tách kênh nhiều trục. Đề xuất thêm domain cấp đơn `sales_line` làm đầu ra duy nhất của bảng quyết định scope, cho phép neo nhãn vào nút cha, tái cấu trúc `customer_type`, `order_purpose`, `discount_purpose` thành cây, và dùng ảnh chụp theo kỳ cho nhãn trạng thái khách.
Concerns: Code `scope_b2b` (có OR `channel_format = 'B2B'`) đã lệch với `segments.md`. Đơn nhân viên đang được xử lý theo hai cách tuỳ nguồn. CROSSBORDER đặt ở trục khách làm rơi đơn bán lẻ thật của người nhận khỏi `scope_retail`. Cả ba sẽ đổi số khi thống nhất, nên cần user duyệt.
