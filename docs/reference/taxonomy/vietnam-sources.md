# Từ vựng phân loại gốc của các nguồn TMĐT Việt Nam (đầu vào cho connector rule pack)

> Ngày nghiên cứu: 2026-10-14. Phạm vi: Sapo, Haravan, Nhanh.vn, Pancake POS, KiotViet, Shopee Open Platform, TikTok Shop Partner API, Lazada Open Platform. MISA không thuộc phạm vi.
> Tài liệu liên quan: [standards-and-patterns.md](standards-and-patterns.md) (chuẩn và pattern liên ngành), [taxonomy-engine.md](../../architecture/taxonomy-engine.md).
>
> **Quy ước độ tin cậy** dùng trong toàn bài:
> - **[Docs]**: đọc trực tiếp từ tài liệu chính thức (trang docs, OpenAPI, help center).
> - **[Mirror]**: bản sao tài liệu/SDK chính thức trên GitHub, vì cổng chính thức render bằng JS và không đọc được bằng máy. Nội dung khớp tên trường chính thức nhưng chưa đối chiếu được với trang gốc.
> - **[Repo]**: xác nhận bằng code/seed/doc trong repo này (dữ liệu Sapo thật đang chạy).
> - **[Suy luận]**: chưa có tài liệu xác nhận; cần kiểm bằng payload thật trước khi đưa vào rule pack.

---

## TL;DR

1. **Mọi hệ thống đều tách "kênh" thành hai lớp.** Lớp 1 là mã nền tảng do hệ thống cố định (Nhanh `saleChannel` = 42 Shopee, 48 TikTok Shop…; Pancake `marketplace_id` = -3 Shopee…; Haravan `source_name` = `web`/`pos`/`iphone`/`android`/`haravan_draft_order`). Lớp 2 là nguồn đơn do merchant tự tạo (Sapo "Nguồn đơn hàng" tùy chỉnh, tối đa 250 nguồn; Nhanh `trafficSource`; Pancake `order_sources`; KiotViet `salechannel`). Connector pack chỉ map chắc chắn được lớp 1. Lớp 2 luôn cần tenant override; pack chỉ gợi ý bằng pattern tên.
2. **Sapo đã có sẵn một taxonomy nguồn đơn.** Help center (2026) mô tả "Danh mục nguồn" bắt buộc khi tạo nguồn tùy chỉnh: Sàn TMĐT, Website, Ứng dụng di động, Mạng xã hội, Livestream, Quảng cáo, Bán tại cửa hàng, Hotline, Gọi điện bán hàng, Đối tác & CTV, Khách hàng giới thiệu, Nhân viên tự tạo (Nội bộ), Nhân viên kinh doanh, KOC/KOL [S1]. Nếu API trả được danh mục này, Sapo pack map `danh mục → channel_format` mà không cần đọc tên nguồn. **Chưa xác nhận API có trả trường danh mục hay không** (developers.sapo.vn bắt đăng nhập).
3. **Loại khách sỉ/đại lý chỉ có sẵn ở Nhanh.** Nhanh có `customer.type` (1 lẻ, 2 sỉ, 3 đại lý) [S24]. Sapo, Pancake, KiotViet, Haravan dùng nhóm/cấp/tag do merchant tự đặt. Cẩn thận với KiotViet: `customer.type` (0 cá nhân, 1 tổ chức) dùng cho hóa đơn điện tử, **không** có nghĩa là khách sỉ [S40].
4. **Cả 3 sàn đều tách ai chịu chi phí giảm giá.** Shopee: `voucher_from_seller`, `voucher_from_shopee`, `seller_discount`, `shopee_discount`, `coins` [S52]. TikTok: `seller_discount`, `platform_discount`, `shipping_fee_seller_discount`, `shipping_fee_platform_discount` [S60]. Lazada: `voucher_seller`, `voucher_platform`, `shipping_fee_discount_seller`, `shipping_fee_discount_platform` [S70]. Pancake gộp lại thành `advanced_platform_fee.marketplace_voucher` ("Sàn trợ giá") [S30]; Nhanh chỉ có tổng `ecomFee` [S21]. Domain canonical `discount_funder` (SELLER/PLATFORM/…) nên là domain chuẩn của sản phẩm.
5. **Cờ fulfillment có sẵn trên cả 3 sàn.** Shopee `fulfillment_flag` (`fulfilled_by_shopee`/`fulfilled_by_cb_seller`/`fulfilled_by_local_seller`) [S50]. TikTok `fulfillment_type` (`FULFILLMENT_BY_SELLER`/`FULFILLMENT_BY_TIKTOK`/…) [S60]. Lazada `is_fbl` (0/1) và `shipping_type` (Drop-shipping/Warehouse) [S70]. Các OMS Việt Nam không có trường tương đương.
6. **Có vài trường "đơn không phải doanh thu" cần đưa vào `order_nature` ngay từ pack.** TikTok `is_sample_order` (đơn mẫu cho creator), `is_replacement_order`, `is_exchange_order` [S60]. Nhanh `type` 5 "Đổi quà", 12 "Đổi sản phẩm", 14 "Khách trả lại hàng", 15 "Hàng chuyển kho", 17 "Đền bù mất hàng" [S20]. Pancake `type` = `accessory` (phụ kiện đi kèm, giá 0) [S30]. Lazada `gift_option` chỉ là gói quà, **không** phải hàng tặng [S70].
7. **Rủi ro lớn nhất về kiến trúc: một đơn sàn đến hai lần.** Đơn Shopee có thể về qua OMS (Sapo/Nhanh/Pancake đều đồng bộ sàn) và qua connector Shopee trực tiếp. Pack phải khai báo khóa ghép (`order_sn` ↔ `channel.appOrderId` của Nhanh / mã đơn sàn trong Sapo) và quy tắc nguồn nào là bản ghi chính.

**Xếp hạng độ tin cậy của tín hiệu kênh** (dùng để chọn luật mặc định trong pack):
1. Mã enum nền tảng do hệ thống cố định (Nhanh `saleChannel`, Pancake `marketplace_id`, connector sàn trực tiếp). Xác định hoàn toàn, nên ship trong pack.
2. Nguồn mặc định có cờ hệ thống (Sapo nguồn "Mặc định" không sửa được tên [S1]; KiotViet `isNotDelete=true` [S40]). Gần như xác định; map theo id/tên cố định.
3. Nguồn tùy chỉnh và danh mục nguồn (Sapo), nhãn/tag đơn. Phụ thuộc tenant; pack chỉ gợi ý.
4. UTM và referral (`utm_source`, `landing_site_ref`, `p_utm_source`). Chỉ dùng cho attribution, không dùng làm kênh bán.

---

## 1. Phương pháp và giới hạn truy cập

| Hệ thống | Tài liệu đọc được | Trạng thái |
|---|---|---|
| Sapo | help.sapo.vn (help center, đọc được); developers.sapo.vn chuyển sang trang đăng nhập đối tác [S7] | API reference **không đọc được**. Tên trường lấy từ repo (Sapo v2 admin API đang ingest) |
| Haravan | docs.haravan.com/docs/omni-apis/* (Docusaurus, đọc được) [S10–S16] | Đầy đủ cho order/customer/product/discount/location |
| Nhanh.vn | apidocs.nhanh.vn/v3 (GitBook, có bản `.md`) [S20–S28] | Đầy đủ, có bảng hằng số (model constant) |
| Pancake POS | docs.pancake.biz/pos/api/openapi.json (OpenAPI 3.1, ~1.3 MB) [S30] | Đầy đủ, máy đọc được |
| KiotViet | kiotviet.vn hướng dẫn Public API Retail [S40] | Đọc được; nhiều enum chỉ nằm trong comment ví dụ |
| Shopee | open.shopee.com, đọc qua endpoint JSON của trang docs (`/opservice/api/v1/doc/api/?api_name=…`) [S50–S56] | Đầy đủ |
| TikTok Shop | partner.tiktokshop.com render bằng JS, không đọc được. Dùng SDK model sinh từ docs chính thức (mirror GitHub) [S60–S62] | [Mirror] |
| Lazada | open.lazada.com render bằng JS. Dùng bản JSON thô của trang docs (mirror GitHub) [S70] | [Mirror] |

---

## 2. Sapo (nguồn hiện tại)

### 2.1 Kênh và nguồn đơn
- **Ba chiều kênh tách biệt** trong báo cáo lợi nhuận của Sapo: *kênh bán hàng* (sàn, web, POS…), *gian/trang* (gian hàng sàn hoặc trang mạng xã hội cụ thể), *nguồn đơn hàng*, và *chi nhánh* [S5]. Các khoản không có nguồn đơn bị gom vào `N/A` [S5].
- **Nguồn đơn hàng** (Cấu hình > Xử lý đơn hàng > Nguồn đơn hàng) [S1]:
  - Loại nguồn: **Mặc định** (hệ thống tạo sẵn: Facebook, POS, Shopee…; chỉ được bật/tắt, không sửa tên/danh mục, không xóa) và **Tùy chỉnh** (merchant tự tạo, tối đa 250 nguồn).
  - Trạng thái: Đang sử dụng / Ngừng sử dụng (dữ liệu lịch sử giữ nguyên).
  - **Danh mục nguồn** (bắt buộc khi tạo nguồn): Sàn TMĐT; Website; Ứng dụng di động; Mạng xã hội; Livestream; Quảng cáo; Bán tại cửa hàng; Hotline; Gọi điện bán hàng; Đối tác & Cộng tác viên; Khách hàng giới thiệu; Nhân viên tự tạo (Nội bộ); Nhân viên kinh doanh; Người nổi tiếng (KOC/KOL).
- **Trường trên đơn** [Repo, `src_sapo_v2_orders.sql`]: `source_id` (id nguồn), `channel` (tên kênh; repo lưu thành `channel_name`), `location_id` (chi nhánh), `assignee_id`/`account_id` (NV phụ trách/tạo đơn), `tags`, `client_details`.
- **API "public" kiểu Shopify/Bizweb** dùng `source_name` (ví dụ `"web"`) [Repo: `ingestion/docs/SOURCES.md`]. Một MCP bên thứ ba lọc theo `source_name` ∈ {facebook, web, pos} [S8, bên thứ ba]. Pipeline hiện tại **không** dùng `source_name`; nó dùng `source_id` + seed.
- **Phân biệt nhiều gian hàng sàn** [Repo]: seed `ref_order_sources.csv` có cột `mapping_tag` (vd. `Shopee_JPC SHOP`, `Lazada_FG CARE`). `stg_sapo_v2_orders.sql` match `o.tags LIKE '%' || mapping_tag || '%'` trước rồi mới fallback về `source_id`. Repo coi đây là quy ước thực tế: đơn sàn Sapo mang tag `<Sàn>_<Tên gian>`. **[Suy luận]** Quy ước này có phải mặc định của Sapo cho mọi shop hay chỉ do tenant cấu hình thì chưa xác nhận. Phải kiểm trên tenant thứ hai.
- **Giá trị thực tế ở Fine Japan** [Repo, seed]: nguồn mặc định có id liên tiếp 3988152–3988159 (Web, Facebook, Zalo, Lazada, Tiki, Pos, Shopee, Other), thêm Sendo 3988160. Đây là ứng viên tốt cho "nguồn mặc định" của Sapo, **[Suy luận]** nhưng id gần như chắc chắn khác nhau giữa các tenant. Pack nên match theo tên nguồn mặc định chứ không theo id.

### 2.2 Khách hàng
- `customer_group` là object `{id, code, name}` nhúng trong customer [Repo, `stg_sapo_v2_customers.sql`]. Entity nhóm có thêm `status`, `group_type`, `condition_type`, `is_default`, `count_customer`, `note` [Repo, `src_sapo_v2_customer_groups.sql`].
- Nhóm có hai kiểu: **thủ công** và **tự động** [S2]. Nhóm tự động lọc theo trạng thái tài khoản, ngày tạo, tag, tổng chi tiêu, tổng đơn, tỉnh/thành, nhận email quảng cáo [S2]. **[Suy luận]** `condition_type` là kiểu nhóm (thủ công/tự động) hoặc quan hệ AND/OR; chưa xác nhận.
- Mỗi khách chỉ có **một** nhóm (object đơn, không phải mảng) [Repo]. Fine Japan dùng `code` để mã hóa loại khách (`TYPE_RETAIL`, `TYPE_WHOLESALE`, `BANBUON`, `KY_GUI`, `CTN00014`…) [Repo, staff guide §8.2]. Đây là quy ước của tenant, không phải của Sapo.
- Trường khác [Repo]: `tags`, `loyalty_point`, `loyalty_customer` (JSON), `default_price_list_id`, `default_discount_rate`, `assignee_id`, `total_expense`, `order_count`, `social_customers`.
- **Hạng thành viên** (app Sapo Loyalty) [S3]: tên hạng do merchant đặt (vd. Vàng, Bạc, Kim cương). Tiêu chí xếp hạng theo **chi tiêu** hoặc **điểm xếp hạng**. Mỗi hạng có % chiết khấu, trần, giá trị đơn tối thiểu. Có thể xét lại hạng 1 hoặc 2 lần/năm. Hạng là nhãn do tenant đặt nên pack không ship giá trị cố định.
- **Bảng giá** (price list): `price_list.code`, `is_cost` [Repo]; khách có `default_price_list_id`. Đây là tín hiệu sỉ mạnh, **[Suy luận]** nếu tenant có bảng giá sỉ riêng.

### 2.3 Đơn hàng: trạng thái, loại, giảm giá
- Trạng thái tách 5 trường [Repo]: `status`, `payment_status`, `fulfillment_status`, `packed_status`, `received_status`.
  - Giá trị `status` thấy trong repo: `draft`, `completed`, `cancelled`, `archived`; các giá trị khác được gom thành OPEN [Repo, `std_orders.sql`]. **[Suy luận]** Có `finalized` (vì tồn tại `finalized_on`).
  - `payment_status`: `paid`, `partial`, `refunded`, `pending`, phần còn lại coi là unpaid. `fulfillment_status`: `restocked`, `partial`, `shipped`. `packed_status` = `packed`. `received_status` = `received` [Repo].
- **Đơn nháp**: `status = draft`. **Đổi/trả**: entity riêng `order_returns` (`reason`, `refund_status`, `status`, `order_id`) [Repo].
- **Giảm giá** [Repo]:
  - `discount_codes`; `order_coupon_code` = `{coupon_code, coupon_promotion_id, order_total_required, discount_amount…}`.
  - `discount_items[]` = `{source, rate, value, amount, reason, promotion_redemption_id, promotion_condition_item_id}`.
  - Repo phát hiện dòng `reason=''` và `rate=100` là chênh lệch giá sỉ B2B, không phải khuyến mại (`stg_sapo_v2_order_discount_items.sql`). Pack Sapo nên ship luật loại trừ này.
- **Khuyến mại** [S4]: hai họ là *mã khuyến mại* (khách nhập mã) và *chương trình khuyến mại* (tự áp dụng). Có 4 loại: giảm giá đơn, giảm giá sản phẩm, mua X tặng Y, miễn phí vận chuyển.
- **Đơn quà tặng/nội bộ**: Sapo không có cờ riêng. Fine Japan dùng nguồn tùy chỉnh ("Quà Tặng", "Ưu đãi Nhân Viên", "Test Sản Phẩm") [Repo, seed `source_type=purpose`]. Danh mục nguồn "Nhân viên tự tạo (Nội bộ)" của Sapo [S1] là chỗ map tự nhiên cho nhóm này.

### 2.4 Sản phẩm
- [Repo, `src_sapo_v2_products.sql`]: `category`, `category_id`, `category_code`, `brand`, `brand_id`, `product_type`, `tags`, `options`, `variants` (`opt1..opt3`), `medicine`.
- "Danh mục sản phẩm" trong help center là **collection website** (thủ công hoặc tự động theo điều kiện; một sản phẩm thuộc nhiều danh mục) [S6]. **[Suy luận]** Đây không phải `product.category` (loại hàng nội bộ, đơn trị). Chưa xác nhận.

---

## 3. Haravan (dạng Shopify)

### 3.1 Kênh và nguồn
- `source_name` chỉ ghi được lúc tạo đơn. Giá trị kênh Haravan **được bảo vệ**: `web`, `pos`, `haravan_draft_order`, `iphone`, `android`. Đơn tạo qua API nhận chuỗi tùy ý; nếu không truyền thì mặc định là **app ID** của app tạo đơn [S10].
- Trường liên quan [S10]: `source` (vd. `"web"`), `landing_site`, `landing_site_ref`, `utm_source/medium/campaign/term/content`, `location_id` (nơi xử lý đơn), `user_id` (nhân viên POS), `device_id`, `assigned_location_id`, `processing_method` ∈ {`checkout`, `direct`, `manual`, `offsite`} [S16].
- **Đơn sàn**: Haravan quảng cáo kết nối Shopee, Lazada, Tiki, TikTok Shop [S80]. **[Suy luận]** Giá trị `source_name` của đơn sàn có thể là tên/app id của connector; tài liệu không liệt kê. Phải lấy mẫu thật.
- Có thể tạo nguồn tùy biến không? Có, bằng `source_name` tùy ý qua API [S10]. Không có danh mục nguồn tự quản lý như Sapo (không thấy trong docs).

### 3.2 Khách hàng
- `tags` (chuỗi phân tách dấu phẩy), `group_name`, `state` (`disabled`/…), `accepts_marketing`, `total_spent`, `orders_count` [S11].
- Nhóm khách: mã giảm giá có `applies_customer_group_id` [S14], tức là có khái niệm nhóm. **[Suy luận]** Không thấy endpoint nhóm khách trong Omni APIs; `group_name` trên customer thường null trong ví dụ [S11].
- Loyalty/hạng thành viên: không có trong Omni APIs (không thấy).

### 3.3 Đơn hàng
- `financial_status`: `pending`, `authorized`, `partially_paid`, `paid`, `partially_refunded`, `refunded`, `voided` [S10].
- `fulfillment_status`: `fulfilled`, `null`/`notfulfilled`, `partial`, `restocked` [S10].
- Trạng thái vòng đời tách riêng: `confirmed_status` (`unconfirmed`…), `closed_status` (`unclosed`…), `cancelled_status` (`uncancelled`…), `order_processing_status` (thấy `confirmed`, `out_of_stock_confirm`; docs không liệt kê đủ [S16]).
- `cancel_reason`: `customer`, `fraud`, `inventory`, `declined`, `other` [S10].
- `tags` (mỗi tag ≤ 40 ký tự) và `note_attributes` (name/value tự do) [S10].
- Đơn nháp: `source_name = haravan_draft_order`. Đơn liên quan: `prev_order_id`/`prev_order_number` [S10]. **[Suy luận]** Hai trường này chỉ đơn gốc khi đổi/sao chép đơn.
- Giảm giá: `discount_codes[] {code, amount, type}`, line item có `price_original`, `price_promotion` [S10]. Promotion có `discount_type` ∈ {`fixed_amount`, `percentage`, `same_price`}, `applies_to_resource` ∈ {null, `product`, `collection`, `product_variant`}, `promotion_apply_type` (1 = SL tối thiểu, 2 = giá trị tối thiểu) [S13]. Discount code thêm loại `shipping` [S14].

### 3.4 Sản phẩm và chi nhánh
- `product_type` (chuỗi tự do), `vendor` (hãng/thương hiệu), `tags` (≤250 tag), `options` (≤3 thuộc tính) [S12]. Collection: `custom_collections` và `smart_collections` (theo luật) [S10 sitemap].
- Location: `location_type` ∈ {`default` (kho mặc định), `ontheroad` (kho đi đường)}, `is_primary` [S15].

---

## 4. Nhanh.vn

### 4.1 Kênh và nguồn (rõ ràng nhất trong các OMS)
- `channel.saleChannel` (enum cố định) [S20]:

| Mã | Kênh | Mã | Kênh |
|---|---|---|---|
| 1 | Admin | 43 | Sendo |
| 2 | Website | 45 | Tiki |
| 10 | API | 48 | Tiktok Shop |
| 20 | Facebook | 49 | Zalo OA |
| 21 | Instagram | 50 | Shopee chat |
| 41 | Lazada | 51 | Lazada chat |
| 42 | Shopee | 52 | Zalo cá nhân |

- `channel.trafficSource` = **Nguồn đơn hàng** do merchant định nghĩa; endpoint `/v3.0/order/source` trả `{id, name, status (1 active, 2 inactive), createdAt}` [S21, S22]. Đây là lớp tùy biến.
- Các trường khác trong `channel` [S21]: `appOrderId` (mã đơn sàn/website), `shopId`, `shopName` (gian hàng sàn), `pageId`, `conversationId`, `fbAdsId`, `domain`, `affiliate {code, value, bonus, bonusRate}`, `marketting {utmSource, utmMedium, utmCampaign}`.
- Gian hàng sàn: `/v3.0/ecom/shop` trả `{appId, shop {id, name}}`. `appId` sàn: 8142 Lazada, 8195 Shopee, 8237 Sendo, 8238 Tiki, 8855 Tiktok [S20, S23].
- Kho/chi nhánh: `depotId`, `pickupDepotId`; nhân viên: `saleId`, `saleName` [S21].
- **Đơn bán lẻ tại quầy là chứng từ riêng** (`/v3/bill/retail`, "hóa đơn bán lẻ"), ngoài `order/list` [S20 sitemap]. Connector phải gộp cả hai mới đủ doanh thu POS. **[Suy luận]** Cần kiểm chứng khi xây connector.

### 4.2 Loại đơn, trạng thái, lý do
- `type` (Order Type) [S20]: 1 Giao hàng tận nhà, 2 Mua tại quầy, 3 Đặt trước, 5 Đổi quà, 10 Xin báo giá, 12 Đổi sản phẩm, 14 Khách trả lại hàng, 15 Hàng chuyển kho, 16 Đơn hoàn một phần, 17 Đền bù mất hàng.
- `status` [S20]: 54 Đơn mới, 55 Đang xác nhận, 56 Đã xác nhận, 57 Chờ khách xác nhận, 42 Đang đóng gói, 40 Đã đóng gói, 43 Chờ thu gom, 59 Đang chuyển, 60 Thành công, 61 Thất bại, 63 Khách hủy, 64 Hệ thống hủy, 58 Hãng vận chuyển hủy đơn, 68 Hết hàng, 71 Đang chuyển hoàn, 72 Đã chuyển hoàn, 73 Đổi kho xuất hàng, 74 Xác nhận hoàn.
- `reason` (lý do hủy/thất bại): 24 mã cố định, vd. 1 Đặt nhầm SP, 4 Đơn trùng, 5 Không gọi được khách, 6 Hết hàng, 18 Lý do khác, 25 HVC làm mất hàng [S20].
- `tags[]` = nhãn đơn hàng `{id, name, status, bgColor, textColor}` [S25], do merchant tự đặt.
- Thanh toán [S21]: `payment.discount {percent, amount}`, `couponCode`, `usedPoints {points, amount}`, `deposit`, `transfer`, `credit`, `codAmount`. `ecomFee` = tổng các loại phí sàn (không tách loại).
- Quà tặng: `gifts[] {productId, orderProductId (>0 tặng theo SP, =0 tặng theo đơn), name, quantity, price}` [S21].

### 4.3 Khách hàng, sản phẩm, giá
- Khách [S24]: `type` (1 Khách lẻ, 2 Khách sỉ/buôn, 3 Đại lý), `group {id, name}`, `level {id, name}`, `points`, `saleName`, `totalAmount`, `business {name, address}`, `taxCode`. Có endpoint tag khách (`/v3/customer/tags`).
- Sản phẩm [S20, S26, S27]:
  - `typeId`: 1 thường, 2 voucher, 3 cân đo, 4 IMEI, 5 gói SP, 6 dịch vụ, 7 dụng cụ, 8 theo lô, 9 combo, 10 nhiều ĐVT.
  - Danh mục là cây `{id, parentId, code, name}`; thêm danh mục nội bộ (`internalcategory`).
  - Thương hiệu là cây `{id, parentId, code, name}`; có tag sản phẩm.
- Bảng giá `/promotion/pricelist` `{id, name, status, startDate, endDate}`, lọc theo `depotIds` [S28].
- Kế toán có mode "Bán sỉ"/"Trả lại bán sỉ"; kho có mode "bán sỉ", "quà tặng ở đơn hàng" [S20]. Đây là tín hiệu sỉ/quà ở cấp chứng từ.

---

## 5. Pancake POS

### 5.1 Kênh và nguồn
- `order_sources` = id nguồn đơn (chuỗi). `/shops/{id}/order_source` trả `{id, name, parent_id, link}` dạng cây; id có thể là **page id** Facebook [S30].
  - Ví dụ trong spec: `{id:-3, name:"Shopee"}`, con `{id:4, name:"40999897", parent_id:-3}` (một gian hàng Shopee); `{name:"Pancake.vn", parent_id:-1}` (một page); `{name:"Landing ABC", parent_id:-7, link:…}` (landing Webcake) [S30].
  - **[Suy luận]** Nguồn gốc âm cố định: -1 = Facebook page, -3 = Shopee, -7 = Webcake. Chỉ -3 có tên trong ví dụ; -1/-7 suy từ ngữ cảnh.
- `marketplace_id` (enum) [S30]: -2 Tiki, -3 Shopee, -4 Lazada, -9 TikTok, -16 WooCommerce, -17 Shopify, -20 Line Shopping, -25 Tokopedia, -27 Mercado Libre, -28 Tiendanube. Có thêm `is_from_ecommerce`, `is_live_shopping`, `received_at_shop` (true = bán tại quầy).
- Attribution [S30]: `ads_source`, `p_utm_source`, `utm_affiliate`, `marketer {…}`, `customer_referral_code`, `shopify_order_id`.
- Kho: `warehouse_id`, `warehouse_info`.

### 5.2 Trạng thái, trả hàng, phí sàn
- `status` [S30]: 0 Mới, 17 Chờ xác nhận, 11 Chờ hàng, 12 Chờ in, 13 Đã in, 20 Đã đặt hàng, 1 Đã xác nhận, 8 Đang đóng hàng, 9 Chờ chuyển hàng, 2 Đã gửi hàng, 3 Đã nhận, 16 Đã thu tiền, 4 Đang hoàn, 15 Hoàn một phần, 5 Đã hoàn, 6 Đã hủy, 7 Đã xóa.
- `returned_reason`: 1 Khách, 2 Nhân viên, 3 Lỗi SP, 4 Nhà vận chuyển, 5 Đổi hàng; giá trị khác là lý do tùy biến của shop (`returned_reason_name`) [S30].
- `tags[]` (thẻ đơn, có `tag_groups`) [S30].
- Phí sàn `advanced_platform_fee` [S30]: `platform_commission`, `affiliate_commission`, `payment_fee`, `seller_transaction_fee`, `service_fee`, `sfp_service_fee`, `marketplace_voucher` ("Sàn trợ giá"), `diff_shipping_fee`, `ads_top_up`. Đây là phân loại phí đầy đủ nhất trong các OMS.
- Giảm giá: `total_discount`, `discount`, `discount_by_customer_level`, `activated_promotion_advances[]`, `prepaid_by_point` [S30].

### 5.3 Khách hàng và sản phẩm
- Khách [S30]: `level_id` (`/customer_levels` trả `{id, name, discount, discount_type, color}`), `tags[]`, `reward_point`, `is_discount_by_level`, `referral_code`, `assigned_user_id`, `order_count`, `succeed_order_count`.
- Khuyến mại có thể giới hạn theo `customer_tags`, `order_sources`, cấp khách [S30]. Pancake coi tag khách và nguồn đơn là chiều phân khúc chính thức.
- Sản phẩm [S30]: `category_ids[]` (đa danh mục), `brand_id`, `tags[]`, `type` ∈ {`product`, `accessory` (đi kèm, giá 0, không tính SL bán), `service`, `LOT`}.

---

## 6. KiotViet (Public API Retail)

- **Kênh bán**: `/salechannel` trả `{id, name, isActive, img, isNotDelete}`; `isNotDelete=true` là kênh hệ thống [S40]. Hóa đơn/đặt hàng có `saleChannelId`; **nếu không truyền thì mặc định "kênh khác"**. Object `SaleChannel {Id, Name, IsNotDelete, IsActivate, Position}` chỉ được trả khi request có `IncludeSaleChannel=true` [S40].
- Chi nhánh `branchId/branchName`; nhân viên bán `soldById/soldByName`; thu ngân `cashierId` [S40].
- **Hai chứng từ**: đặt hàng (`/orders`) và hóa đơn (`/invoices`). Doanh thu nằm ở hóa đơn [S40].
  - Trạng thái hóa đơn: 1 hoàn thành, 2 đã hủy, 3 đang xử lý, 5 không giao được.
  - Trạng thái vận đơn (`invoiceDelivery.status`): 1 Chờ xử lý … 6 Đã hủy, mở rộng tới 12 Chờ chuyển hoàn lại.
  - Trạng thái đặt hàng có `status/statusValue`, nhưng docs không liệt kê giá trị.
- Trả hàng: `/returns` (`invoiceId`, `returnDate`, `branchId`) [S40].
- Giảm giá: `discount`, `discountRatio` cấp đơn và dòng; voucher là phương thức thanh toán (`Method:"Voucher"`, `VoucherId`, `VoucherCampaignId`); có `surchages` (thu khác) [S40].
- Khách [S40]:
  - Nhóm `groupIds[]` / `customerGroupDetails[]`, tức **đa nhóm**. `/customers/group` trả `{id, name, description, discount}`.
  - `rewardPoint`, `totalPoint`, `totalRevenue`.
  - `type` 0 = Cá nhân, 1 = Tổ chức/Hộ kinh doanh (cho HĐĐT; không phải sỉ/lẻ).
- Bảng giá `pricebook` (`IsGlobal`, `StartDate`, `EndDate`, gán cho người dùng/chi nhánh) [S40].
- Sản phẩm: `categoryId` (cây `parentId`, `hasChild`), `tradeMarkId/tradeMarkName`, `hasVariants`, thuộc tính [S40].
- **[Suy luận]** Đơn sàn đồng bộ vào KiotViet (KV Sync, MyKiot gắn header `Partner`) có lẽ mang `saleChannelId` riêng cho từng sàn; docs không xác nhận.

---

## 7. Shopee Open Platform (v2)

- **Định danh gian hàng**: token theo `shop_id`. `get_shop_info` có `shop_name`, `region`, `is_cb` (xuyên biên giới), `is_sip`, `merchant_id`, `shop_fulfillment_flag` (Pure-FBS / Pure-3PF / …) [S56].
- **Trạng thái** `order_status`: `UNPAID`, `READY_TO_SHIP`, `PROCESSED`, `SHIPPED`, `COMPLETED`, `IN_CANCEL`, `CANCELLED`, `INVOICE_PENDING`; thêm `PENDING` nếu gửi `request_order_status_pending` (`pending_terms`: `SYSTEM_PENDING`, `KYC_PENDING`, `ARRANGE_SHIPMENT_PENDING`) [S50, S51].
- `cancel_by` ∈ {buyer, seller, system, Ops}; `buyer_cancel_reason`, `cancel_reason` [S50].
- **Fulfillment**: `fulfillment_flag` ∈ {`fulfilled_by_shopee`, `fulfilled_by_cb_seller`, `fulfilled_by_local_seller`}; `booking_sn`, `advance_package` (advance fulfilment); `item_list.product_location_id` (kho, multi-warehouse); `package_list.logistics_channel_id`, `shipping_carrier`, `checkout_shipping_carrier` [S50].
- **Khuyến mại cấp dòng** [S50]:
  - `promotion_type` ∈ {`product_promotion`, `flash_sale`, `bundle_deal`, `add_on_deal_main`, `add_on_deal_sub`}.
  - `promotion_list[].promotion_type` gồm `low_price_promotion`, `deep_discount`, `platform_sale`, `seller_discount`, `flash_sale`, `wholesale`, `welcome_package_free_gift`, `brand_flash_sale`, `in_shop_flash_sale`, `synced_promo`, `platform_streaming_price`, `seller_streaming_price`, `exclusive_streamer_price`, `price_bidding_with_rebate`.
  - `wholesale` (bool, mua theo giá sỉ), `add_on_deal`, `is_b2c_owned_item`.
- **Thu nhập/phí** (`get_escrow_detail.order_income`) [S52]:
  - Giảm giá theo bên tài trợ: `seller_discount`, `shopee_discount`, `voucher_from_seller`, `voucher_from_shopee`, `voucher_from_external_party`, `coins`, `seller_coin_cash_back`, `payment_promotion`, `credit_card_promotion`, `seller_voucher_code[]`.
  - Phí: `commission_fee`, `service_fee`, `seller_transaction_fee`, `seller_order_processing_fee`, `ams_commission_fee`/`order_ams_commission_fee` (affiliate), `campaign_fee`, `fbs_fee`, `ads_escrow_top_up_fee_or_technical_support_fee`, `pay_per_sale`.
  - Vận chuyển: `actual_shipping_fee`, `shopee_shipping_rebate`, `seller_shipping_discount`, `final_shipping_fee`, `reverse_shipping_fee`, `final_return_to_seller_shipping_fee`.
  - Thuế khấu trừ VN: `withholding_vat_tax`, `withholding_pit_tax`, `withholding_cit_tax`.
  - Điều chỉnh: `order_adjustment.adjustment_reason`; `escrow_amount`, `escrow_amount_after_adjustment`.
- **Voucher**: `voucher_type` 1 = shop voucher, 2 = product voucher; `reward_type` 1 = số tiền cố định, 2 = %, 3 = hoàn xu; `display_channel_list` (1 all, 2 order page, 3 feed, 4 livestream) [S55].
- **Danh mục/thương hiệu**: `get_category` trả cây `{category_id, parent_category_id, original_category_name, display_category_name, has_children}`; `get_brand_list` trả `{brand_id, original_brand_name, display_brand_name}` theo danh mục [S53, S54]. Cây danh mục áp cho cả sàn theo region; seller không tạo được danh mục.

---

## 8. TikTok Shop Partner API (202309) [Mirror]

- **Trạng thái** `status`: `UNPAID`, `ON_HOLD`, `AWAITING_SHIPMENT`, `PARTIALLY_SHIPPING`, `AWAITING_COLLECTION`, `IN_TRANSIT`, `DELIVERED`, `COMPLETED`, `CANCELLED` [S60]. `cancellation_initiator` ∈ {SELLER, BUYER, SYSTEM}; `cancel_reason`; `is_buyer_request_cancel`.
- **Fulfillment**: `fulfillment_type` ∈ {`FULFILLMENT_BY_SELLER`, `FULFILLMENT_BY_TIKTOK`, `FULFILLMENT_BY_DILAYANI_TOKOPEDIA`}; `shipping_type` ∈ {`TIKTOK`, `SELLER`, `TIKTOK_DIGITAL`}; `delivery_type` ∈ {`HOME_DELIVERY`, `COLLECTION_POINT`}; `warehouse_id` [S60].
- **Loại đơn**: `order_type` (`NORMAL`, `ZERO_LOTTERY`; US có thêm `PRE_ORDER`, `MADE_TO_ORDER`, `BACK_ORDER`, `VIRTUAL_ORDER`). Cờ: `is_sample_order`, `is_replacement_order`, `is_exchange_order` (US/UK), `is_on_hold_order`, `is_subscription_order`, `is_cod`. `commerce_platform` ∈ {TIKTOK_SHOP, TOKOPEDIA} (ID) [S60].
- **Thanh toán** (`payment`) [S60]:
  - `original_total_product_price`, `seller_discount`, `platform_discount`, `sub_total`.
  - `original_shipping_fee`, `shipping_fee_seller_discount`, `shipping_fee_platform_discount`, `shipping_fee_cofunded_discount`, `shipping_fee`.
  - `payment_platform_discount`, `total_amount`, `tax`.
- **Phí quyết toán** (Finance 202501 `fee_tax_breakdown.fee`) [S61]: `platform_commission_amount`, `referral_fee_amount`, `transaction_fee_amount`, `affiliate_commission_amount`, `affiliate_ads_commission_amount`, `affiliate_partner_commission_amount`, `sfp_service_fee_amount`, `flash_sales_service_fee_amount`, `voucher_xtra_service_fee_amount`, `live_specials_fee_amount`, `gmv_max_ad_fee_amount`, `vn_fix_infrastructure_fee` (phí riêng VN), `refund_administration_fee_amount`, `failed_delivery_shipping_fee`… (khoảng 60 loại).
- **Danh mục/thương hiệu** [S62]: danh mục `{id, parent_id, local_name, is_leaf, permission_statuses (AVAILABLE/INVITE_ONLY…)}`; thương hiệu `{id, name, authorized_status (AUTHORIZED/UNAUTHORIZED), brand_status (AVAILABLE/UNAVAILABLE)}`.
- **Gian hàng**: token theo shop được ủy quyền (`/authorization/202309/shops`) [S63, Odoo, thứ cấp].

---

## 9. Lazada Open Platform [Mirror]

- **Trạng thái**: đơn có `statuses[]` (tập trạng thái của các dòng); dòng có `status`. Bộ lọc nhận `unpaid`, `pending`, `canceled`, `ready_to_ship`, `delivered`, `returned`, `shipped`, `failed`, `topack`, `toship`, `shipping`, `lost` [S70]. Dòng có `return_status`, `is_cancel_pending`.
- **Loại đơn** (dòng): `order_type` ∈ {Normal, PreSale, Coupon, O2O, InStoreO2O}; `order_flag` ∈ {GUARANTEE, NORMAL, GLOBAL_COLLECTION}; `stage_pay_status` (presale); `is_digital` [S70].
- **Fulfillment**: `is_fbl` (0/1, Fulfilled by Lazada), `shipping_type` (Drop-shipping / Warehouse), `shipping_provider_type` ∈ {EXPRESS, STANDARD, ECONOMY, INSTANT, SELLER_OWN_FLEET, PICKUP_IN_STORE, DIGITAL}, `warehouse_code`, `biz_group` (70100 = MP seller tự giao; 70020 = Choice kho) [S70].
- **Giảm giá theo bên tài trợ**: đơn có `voucher`, `voucher_platform`, `voucher_seller`, `voucher_code`, `shipping_fee_original`, `shipping_fee_discount_seller`, `shipping_fee_discount_platform`; dòng có thêm `voucher_seller_lpi`/`voucher_platform_lpi` (Lazada Bonus), `voucher_code_seller`/`voucher_code_platform` [S70].
- **Quà**: `gift_option` (1 = gói quà), `gift_message`, `gift_wrapping` [S70]. Đây là gói quà, không phải hàng tặng 0đ.
- **Phí**: `/finance/transaction/details/get` trả `fee_type` (id loại giao dịch), `fee_name`, `transaction_type` [S70]. Danh sách loại phí **không liệt kê** trong docs đọc được (cần lấy mẫu).
- **Danh mục/thương hiệu**: cây `{category_id, name, leaf, var, children}`; thương hiệu `{brand_id, name, name_en, global_identifier}` [S70].
- Thuế VN: `tax_code` của người mua [S70].

---

## 10. Bảng so sánh xuyên hệ thống

### 10.1 Kênh/nguồn đơn (input chính của rule pack kênh)

| Khái niệm | Sapo | Haravan | Nhanh | Pancake | KiotViet | Shopee/TikTok/Lazada |
|---|---|---|---|---|---|---|
| Mã nền tảng cố định | Nguồn "Mặc định" (Facebook, POS, Shopee…) qua `source_id` [S1, Repo] | `source_name` ∈ {web, pos, iphone, android, haravan_draft_order} [S10] | `saleChannel` enum 14 giá trị [S20] | `marketplace_id` enum 10 giá trị; `received_at_shop` [S30] | Kênh `isNotDelete=true` [S40] | Ngầm định theo connector |
| Nguồn do merchant tạo | Có, ≤250, kèm *danh mục nguồn* bắt buộc [S1] | Chuỗi `source_name` tùy ý qua API [S10] | `trafficSource` (`/order/source`) [S22] | `order_sources` dạng cây (page, landing, gian) [S30] | Có (`/salechannel`) [S40] | Không |
| Gian hàng sàn | Tag `<Sàn>_<gian>` [Repo; Suy luận về tính phổ quát]; chiều "gian/trang" trong báo cáo [S5] | Chưa rõ | `shopId`, `shopName` + `/ecom/shop` [S21, S23] | Nguồn con của nguồn sàn (vd. parent -3) [S30] | Chưa rõ | `shop_id` (Shopee), shop ủy quyền (TikTok), seller (Lazada) |
| Chi nhánh/kho | `location_id` [Repo] | `location_id`, `assigned_location_id` [S10] | `depotId` [S21] | `warehouse_id` [S30] | `branchId` [S40] | `product_location_id` / `warehouse_id` / `warehouse_code` |
| NV bán | `assignee_id`, `account_id` [Repo] | `user_id` (POS) [S10] | `saleId` [S21] | `marketer` (đơn), `assigned_user_id` (khách) [S30] | `soldById` [S40] | — |
| Affiliate/CTV | Danh mục nguồn "Đối tác & CTV", "KOC/KOL" [S1] | `utm_*` [S10] | `affiliate {code, bonus…}` [S21] | `utm_affiliate`, `customer_referral_code` [S30] | — | Phí affiliate (Shopee `ams_commission_fee`, TikTok `affiliate_*`) |
| Custom-able? | Cao | Trung bình | Thấp (enum) + cao (traffic source) | Cao | Trung bình | Không |

### 10.2 Khách hàng

| Khái niệm | Sapo | Haravan | Nhanh | Pancake | KiotViet |
|---|---|---|---|---|---|
| Loại khách có sẵn (lẻ/sỉ) | Không (qua nhóm) | Không | **`type` 1 lẻ / 2 sỉ / 3 đại lý** [S24] | Không | Không (`type` là cá nhân/tổ chức cho HĐĐT) [S40] |
| Nhóm | 1 nhóm `{id, code, name}`, thủ công/tự động [Repo, S2] | `group_name`, `applies_customer_group_id` [S11, S14] | `group {id, name}` [S24] | (dùng tag) | **Đa nhóm** `groupIds[]`, nhóm có `discount` [S40] |
| Cấp/hạng | Sapo Loyalty: hạng tự đặt theo chi tiêu/điểm [S3] | — | `level {id, name}` [S24] | `level_id` + `/customer_levels` (có discount) [S30] | — (`rewardPoint`) |
| Tag | `tags` [Repo] | `tags` [S11] | Có endpoint tag [S24] | `tags[]` [S30] | — |
| Bảng giá sỉ | `price_list`, `default_price_list_id` [Repo] | — | `pricelist` theo kho [S28] | — | `pricebook` [S40] |

Sàn chỉ trả người mua đã che (`buyer_user_id`, `buyer_username`), không có nhóm khách. Shopee có `item.wholesale` ở cấp dòng [S50].

### 10.3 Trạng thái đơn → giá trị canonical đề xuất

| Canonical | Sapo [Repo] | Haravan [S10] | Nhanh [S20] | Pancake [S30] | KiotViet (HĐ) [S40] | Shopee [S51] | TikTok [S60] | Lazada [S70] |
|---|---|---|---|---|---|---|---|---|
| DRAFT | `status=draft` | `source_name=haravan_draft_order` | 10 Xin báo giá (type) | — | — | — | — | — |
| PENDING | (open) | `confirmed_status=unconfirmed` | 54, 55, 57 | 0, 17 | 3 | UNPAID, PENDING | UNPAID, ON_HOLD | unpaid, pending |
| CONFIRMED/PROCESSING | (open, `packed_status`) | `order_processing_status=confirmed` | 56, 42, 40, 43, 68, 73 | 1, 11, 12, 13, 20, 8, 9 | 3 | READY_TO_SHIP, PROCESSED | AWAITING_SHIPMENT, PARTIALLY_SHIPPING, AWAITING_COLLECTION | topack, toship, ready_to_ship |
| SHIPPED | `fulfillment_status=shipped` | `fulfillment_status=fulfilled/partial` | 59 | 2 | (vận đơn 2) | SHIPPED | IN_TRANSIT | shipped, shipping |
| DELIVERED | `received_status=received` | — | 60 | 3, 16 | 1 | (TO_CONFIRM_RECEIVE*) | DELIVERED | delivered |
| COMPLETED | `status=completed` | `closed_status` ≠ unclosed | 60 | 16 | 1 | COMPLETED | COMPLETED | delivered* |
| CANCELLED | `status=cancelled` | `cancelled_status` ≠ uncancelled, `cancel_reason` | 58, 63, 64 | 6, 7 | 2 | IN_CANCEL, CANCELLED | CANCELLED | canceled |
| RETURNED | `fulfillment_status=restocked`, `order_returns` | `fulfillment_status=restocked`, refunds | 71, 72, 74, 16 (type) | 4, 15, 5 | `/returns`, 5 không giao được | (returns API) | (return API) | returned, failed, lost |

\* Chưa xác minh trong phạm vi tài liệu đã đọc. Giá trị Shopee `TO_CONFIRM_RECEIVE`/`TO_RETURN` có trong "Data Definition" nhưng tôi chưa đọc trang đó.

### 10.4 Bản chất đơn (đầu vào cho `order_nature`)

| Bản chất | Sapo | Haravan | Nhanh | Pancake | KiotViet | Shopee | TikTok | Lazada |
|---|---|---|---|---|---|---|---|---|
| Bán thường | mặc định | mặc định | type 1, 2, 3 | mặc định | HĐ | mặc định | NORMAL | Normal |
| Bán sỉ | nhóm/bảng giá (tenant) | — | KH type 2/3; kế toán mode "Bán sỉ" | — | pricebook (tenant) | `item.wholesale` | — | — |
| Quà tặng 0đ | nguồn tùy chỉnh (tenant) | — | type 5; `gifts[]` | `type=accessory` (SP) | — | `welcome_package_free_gift` | `ZERO_LOTTERY`? | — |
| Mẫu/sample | — | — | — | — | — | — | `is_sample_order` | — |
| Đổi hàng | — | `prev_order_id`? | type 12 | `returned_reason=5` | — | — | `is_exchange_order`, `is_replacement_order` | — |
| Trả hàng | `order_returns` | refunds | type 14, 16 | status 4/5/15 | `/returns` | returns | returns | `return_status` |
| Chuyển kho/đền bù | — | — | type 15, 17 | — | — | — | — | — |
| Đặt trước | — | — | type 3 | — | đặt hàng | `advance_package` | PRE_ORDER | PreSale |
| Nội bộ/test | nguồn danh mục "Nội bộ" (tenant) | — | — | — | — | — | — | — |

### 10.5 Giảm giá theo bên tài trợ (domain `discount_funder` đề xuất)

| Funder | Sapo | Haravan | Nhanh | Pancake | KiotViet | Shopee | TikTok | Lazada |
|---|---|---|---|---|---|---|---|---|
| SELLER (KM shop) | `discount_items`, `order_coupon_code` | `discount_codes`, promotions | `payment.discount`, `couponCode` | `total_discount`, promotions | `discount`, voucher | `seller_discount`, `voucher_from_seller`, `seller_shipping_discount`, `seller_coin_cash_back` | `seller_discount`, `shipping_fee_seller_discount` | `voucher_seller`, `shipping_fee_discount_seller`, `voucher_seller_lpi` |
| PLATFORM (sàn trợ giá) | — | — | (gộp `ecomFee`) | `marketplace_voucher` | — | `shopee_discount`, `voucher_from_shopee`, `coins`, `shopee_shipping_rebate` | `platform_discount`, `shipping_fee_platform_discount` | `voucher_platform`, `shipping_fee_discount_platform`, `voucher_platform_lpi` |
| CO-FUNDED | — | — | — | — | — | — | `shipping_fee_cofunded_discount` | — |
| PAYMENT/EXTERNAL | — | — | — | — | — | `payment_promotion`, `credit_card_promotion`, `voucher_from_external_party` | `payment_platform_discount` | — |
| LOYALTY (điểm/hạng) | `loyalty_point`; chiết khấu hạng [S3] | — | `usedPoints` | `prepaid_by_point`, `discount_by_customer_level` | voucher | — | — | — |
| PRICE_POLICY (giá sỉ, không phải KM) | `discount_items` reason='' rate=100 [Repo] | — | pricelist | — | pricebook | `wholesale` | — | — |

### 10.6 Phí sàn (domain `fee_type` đề xuất)

| Canonical | Shopee [S52] | TikTok [S61] | Lazada [S70] | Pancake [S30] | Nhanh [S21] |
|---|---|---|---|---|---|
| COMMISSION | `commission_fee` | `platform_commission_amount`, `referral_fee_amount` | `fee_name` (tra mẫu) | `platform_commission` | `ecomFee` (tổng) |
| PAYMENT_FEE | `seller_transaction_fee` | `transaction_fee_amount` | ″ | `payment_fee`, `seller_transaction_fee` | ″ |
| SERVICE_FEE (gói dịch vụ, freeship, voucher xtra) | `service_fee`, `seller_order_processing_fee` | `sfp_service_fee_amount`, `voucher_xtra_service_fee_amount`, `flash_sales_service_fee_amount` | ″ | `service_fee`, `sfp_service_fee` | ″ |
| AFFILIATE | `ams_commission_fee` | `affiliate_commission_amount`, `affiliate_ads_commission_amount` | ″ | `affiliate_commission` | ″ |
| ADS | `ads_escrow_top_up_fee_or_technical_support_fee`, `pay_per_sale` | `gmv_max_ad_fee_amount` | ″ | `ads_top_up` | ″ |
| SHIPPING_NET | `final_shipping_fee`, `reverse_shipping_fee` | `failed_delivery_shipping_fee` | ″ | `diff_shipping_fee` | ″ |
| FULFILLMENT_FEE | `fbs_fee` | (FBT fees) | ″ | — | ″ |
| TAX_WITHHOLDING | `withholding_vat_tax`, `withholding_pit_tax`, `withholding_cit_tax` | (tax breakdown) | ″ | — | ″ |
| OTHER | `campaign_fee`, `order_adjustment` | `vn_fix_infrastructure_fee`, … | ″ | — | ″ |

### 10.7 Sản phẩm

| Khái niệm | Sapo [Repo] | Haravan [S12] | Nhanh [S20, S26, S27] | Pancake [S30] | KiotViet [S40] | Shopee [S53, S54] | TikTok [S62] | Lazada [S70] |
|---|---|---|---|---|---|---|---|---|
| Danh mục nội bộ | `category`, `category_id`, `category_code` (đơn trị) | `product_type` (chuỗi) | cây `categoryId` + danh mục nội bộ | `category_ids[]` (đa trị) | cây `categoryId` | — | — | — |
| Collection (web) | danh mục web thủ công/tự động [S6] | custom/smart collections | — | — | — | — | — | — |
| Thương hiệu | `brand`, `brand_id` | `vendor` | cây brand | `brand_id` | `tradeMarkId` | `brand_id` (brand list) | brand + `authorized_status` | `brand_id`, `global_identifier` |
| Loại hàng (kỹ thuật) | `product_type` | — | `typeId` 1–10 | `type` product/accessory/service/LOT | `hasVariants` | — | — | `is_digital` |
| Tag | `tags` | `tags` (≤250) | tag SP | `tags[]` | — | — | — | — |
| Biến thể | `opt1..3` | `options` ≤3 | — | variations | thuộc tính | model/tier | SKU attributes | SKU |
| Cây danh mục sàn | — | — | — | — | — | global theo region, seller không sửa | `is_leaf`, `permission_statuses` | `leaf`, `var` |

---

## 11. Gợi ý gói luật theo connector

Nguyên tắc chung (đúng mô hình product defaults → connector pack → tenant override):

- **Product defaults** chỉ định nghĩa domain và giá trị canonical. Đề xuất dùng lại từ vựng đang chạy trong repo để không đổi số: `channel_format` ∈ {Marketplace, Social, Web, Retail, B2B, Direct, System, CrossBorder Fulfillment, Other}; `source_type` ∈ {channel, purpose, arrangement, customer_type}; `platform`; `customer_type` ∈ {RETAIL, WHOLESALE, PARTNER, STAFF, KOL, CROSSBORDER} [Repo]. Domain mới nên thêm ở tầng product: `fulfillment_model` {SELLER, PLATFORM}; `discount_funder` (§10.5); `fee_type` (§10.6); `order_nature` (§10.4; repo đã đề xuất cho Đợt 4); `status_canonical` (§10.3).
- **Connector pack** chỉ ship luật dựa trên **giá trị do hệ thống nguồn cố định** (hạng 1–2 trong TL;DR). Luật dựa trên tên do merchant đặt được ship ở dạng **gợi ý có độ tin cậy thấp** (`confidence: suggest`): mặc định tắt, hoặc chỉ dùng để pre-fill màn hình tenant xác nhận.
- **Tenant override** bắt buộc cho: nguồn tùy chỉnh, nhóm/cấp/tag khách, nhãn đơn, quy ước mã nhóm (`TYPE_*`), nguồn quà/test/nội bộ.

### 11.1 Pack `sapo`

| Luật | Match | Kết quả | Độ tin cậy |
|---|---|---|---|
| Nguồn mặc định | tên nguồn ∈ {Shopee, Lazada, Tiki, Sendo, TikTok/TiktokShop} | `channel_format=Marketplace`, `platform=<tên>` | Cao (nguồn mặc định không đổi tên được [S1]) |
| | {Facebook, Instagram, Zalo} | Social | Cao |
| | {Web} | Web | Cao |
| | {POS, Pos} | Retail, `is_generic_source=true` (nở theo `location_id`) | Cao [Repo] |
| | {Other} | Other (không tính doanh thu) | Cao, khớp quyết định hiện tại [Repo] |
| Danh mục nguồn → format (nếu API trả) | Sàn TMĐT → Marketplace; Website / Ứng dụng di động → Web; Mạng xã hội / Livestream / Quảng cáo → Social; Bán tại cửa hàng → Retail; Hotline / Gọi điện bán hàng / Nhân viên kinh doanh → Direct; Đối tác & CTV → B2B hoặc Direct (**tenant chọn**); Khách hàng giới thiệu → Direct; Nhân viên tự tạo (Nội bộ) → System; KOC/KOL → Social | | Trung bình; phụ thuộc việc API có trả danh mục |
| Gian hàng sàn | `tags` chứa `<Platform>_<shop>` | tách `channel_name` theo gian | Trung bình (quy ước repo) |
| Giá sỉ ≠ KM | `discount_items.reason=''` AND `rate=100` | `discount_funder=PRICE_POLICY` | Cao trên Fine Japan [Repo]; kiểm lại trên tenant 2 |
| Trạng thái | §10.3, cột Sapo | `status_canonical` | Cao [Repo] |
| Gợi ý tên (suggest) | tên nguồn ~ `/đại lý|sỉ|buôn/i` → B2B; `/quà|tặng|gift/i` → System + `order_nature=gift`; `/test|thử/i` → System + test; `/nhân viên|nội bộ/i` → System + staff_benefit; `/ctv|cộng tác/i` → affiliate | | Thấp (tenant xác nhận) |
| Gợi ý nhóm khách (suggest) | `customer_group.code/name` ~ `/sỉ|buôn|wholesale/i` → WHOLESALE; `/đại lý|ký gửi|partner/i` → PARTNER; `/nhân viên|staff/i` → STAFF; `/kol|koc/i` → KOL | | Thấp |

### 11.2 Pack `haravan`

| Luật | Match | Kết quả | Độ tin cậy |
|---|---|---|---|
| Kênh bảo vệ | `source_name=web` | Web | Cao [S10] |
| | `pos` | Retail (nở theo `location_id`) | Cao |
| | `iphone`, `android` | Web (app di động; hoặc tách `platform=MobileApp`) | Cao |
| | `haravan_draft_order` | Direct (đơn tạo tay) + cờ draft-origin | Trung bình: đơn nháp đã chốt vẫn là bán thật |
| Kênh khác | `source_name` khác (app id/chuỗi) | **Unknown → tenant map** | — |
| Attribution | `utm_*`, `landing_site_ref` | chỉ dùng cho attribution | — |
| Trạng thái/hủy | §10.3; `cancel_reason` 5 giá trị | canonical | Cao |
| Sản phẩm | `vendor` → brand; `product_type` → category nội bộ | | Cao (ngữ nghĩa Shopify) |

### 11.3 Pack `nhanh`

| Luật | Match | Kết quả | Độ tin cậy |
|---|---|---|---|
| Kênh | `saleChannel` 41/42/43/45/48 | Marketplace + platform (Lazada/Shopee/Sendo/Tiki/TikTok) | Cao [S20] |
| | 20, 21, 49, 52 | Social (Facebook/Instagram/Zalo OA/Zalo cá nhân) | Cao |
| | 50, 51 | Social, `platform=Shopee chat/Lazada chat` (bán qua chat sàn, **không** phải đơn sàn) | Trung bình; cần tenant xác nhận ý nghĩa |
| | 2 | Web | Cao |
| | 1 (Admin), 10 (API) | **Unknown → dùng `trafficSource`** | — |
| Bán tại quầy | `type=2` hoặc chứng từ `bill/retail` | Retail | Cao |
| Gian hàng | `shopId`/`shopName` | `channel_name` theo gian | Cao |
| Bản chất đơn | type 5 → gift; 12 → exchange; 14, 16 → return; 15 → transfer (loại khỏi doanh thu); 17 → compensation; 10 → quote (loại); 3 → preorder | `order_nature` | Cao |
| Loại khách | `customer.type` 1/2/3 | RETAIL / WHOLESALE / PARTNER (đại lý) | Cao [S24] |
| Trạng thái + lý do | §10.3; `reason` 24 mã → nhóm (khách, vận chuyển, hết hàng, trùng) | canonical | Cao |
| Phí sàn | `ecomFee` | `fee_type=MARKETPLACE_TOTAL` (không tách) | Cao, nhưng chi tiết thấp |

### 11.4 Pack `pancake`

| Luật | Match | Kết quả | Độ tin cậy |
|---|---|---|---|
| Kênh sàn | `marketplace_id` -2/-3/-4/-9 | Marketplace + Tiki/Shopee/Lazada/TikTok | Cao [S30] |
| | -16, -17 | Web (WooCommerce/Shopify) | Cao |
| Bán tại quầy | `received_at_shop=true` | Retail | Cao |
| Livestream | `is_live_shopping=true` | Social + cờ live | Cao |
| Nguồn gốc | `order_sources` có gốc -1 (page) | Social/Facebook | Trung bình (id gốc suy luận) |
| | gốc -7 (landing) | Web/Landing | Trung bình |
| | nguồn tùy biến khác | tenant | — |
| Gian sàn | nguồn con của nguồn sàn | `channel_name` theo gian | Trung bình |
| Phí sàn | `advanced_platform_fee.*` | §10.6 | Cao |
| Trả/đổi | `returned_reason` 1–5 | customer, staff, defect, carrier, exchange (giá trị khác là lý do tùy biến → tenant) | Cao |
| Sản phẩm | `type=accessory` → không tính SL bán, `order_nature` line = bundled_gift | Cao |
| Khách | `level_id` → tier (tenant đặt tên); `tags` → tenant | Thấp (tenant) |

### 11.5 Pack `kiotviet`

| Luật | Match | Kết quả | Độ tin cậy |
|---|---|---|---|
| Kênh | `saleChannelId` null hoặc kênh "khác" mặc định | Retail (POS tại chi nhánh) | Trung bình [S40]: mặc định là "kênh khác" khi không truyền |
| | kênh `isNotDelete=true` | map theo tên cố định | Trung bình (chưa có danh sách tên hệ thống) |
| | kênh tùy chỉnh | tenant | — |
| Doanh thu | dùng `invoices` (status 1); `orders` chỉ là đặt hàng | | Cao |
| Trạng thái | invoice 1/2/3/5; vận đơn 1–12 | canonical | Cao |
| Khách | `customer.type` **không** map sang customer_type (chỉ là pháp nhân HĐĐT) | guard rule | Cao |
| | `groupIds[]` đa nhóm → cần luật ưu tiên (precedence) ở tenant | | — |
| Giảm giá | voucher là phương thức thanh toán → `discount_funder=SELLER` | Trung bình |

### 11.6 Pack `shopee` / `tiktok_shop` / `lazada` (connector trực tiếp)

| Luật | Shopee | TikTok | Lazada |
|---|---|---|---|
| Kênh | hằng `Marketplace/Shopee`, `channel_name` = `shop_name` | hằng `Marketplace/TikTok` | hằng `Marketplace/Lazada` |
| Xuyên biên giới | `is_cb`/`is_sip` → cờ cross-border shop | — | `order_flag=GLOBAL_COLLECTION` |
| `fulfillment_model` | `fulfilled_by_shopee` → PLATFORM; còn lại SELLER | `FULFILLMENT_BY_TIKTOK` → PLATFORM | `is_fbl=1` hoặc `shipping_type=Warehouse` → PLATFORM |
| `order_nature` | `item.wholesale` → wholesale line; `welcome_package_free_gift` → gift line | `is_sample_order` → sample (**loại khỏi doanh thu**); `is_exchange_order`/`is_replacement_order` → exchange; `PRE_ORDER` → preorder | `order_type=PreSale` → preorder; `is_digital` → digital |
| `discount_funder` | §10.5 | §10.5 | §10.5 |
| `fee_type` | §10.6, từ escrow | §10.6, từ statement | `fee_name` → tenant/pack map sau khi có mẫu |
| Trạng thái | §10.3 | §10.3 | §10.3 (gộp `statuses[]` theo luật "trạng thái xa nhất") |
| Danh mục | `category_id` → seed cây danh mục sàn (versioned) → map sang danh mục tenant | tương tự | tương tự |

### 11.7 Luật chung bắt buộc khi có cả OMS lẫn connector sàn

- **Khử trùng đơn sàn**: khóa ghép `platform + platform_order_id`. Nguồn khóa phía OMS: Nhanh `channel.appOrderId` [S21]; Pancake (**[Suy luận]** mã đơn sàn nằm trong trường riêng, cần kiểm); Sapo (**[Suy luận]** mã đơn sàn nằm trong `reference`/note/tag, cần kiểm payload).
- **Quy tắc nguồn chính**: số tiền và phí lấy từ connector sàn (có `discount_funder` và `fee_type` chi tiết); kênh, nhân viên, chi nhánh và khách lấy từ OMS. Tenant chọn và pack không quyết thay.

---

## 12. Giới hạn của nghiên cứu

- **Sapo API reference không truy cập được** (developers.sapo.vn yêu cầu đăng nhập đối tác) [S7]. Mọi tên trường Sapo lấy từ repo, tức là chỉ một tenant (Fine Japan) với Sapo v2 admin API. Chưa biết API có trả *danh mục nguồn* và *loại nguồn* (mặc định/tùy chỉnh) hay không. Đây là điểm quyết định chất lượng pack Sapo.
- **TikTok và Lazada dùng bản mirror**. Tên trường khớp SDK chính thức, nhưng phiên bản API có thể đã đổi; TikTok đã có finance 202507/202605 mà tôi chưa đọc.
- Chưa đọc trang "Data Definition" của Shopee (OrderStatus đầy đủ, LogisticsStatus, Payment Methods).
- Chưa lấy **payload thật** của Haravan, Nhanh, Pancake, KiotViet. Mọi cột "Suy luận" cần một lần lấy mẫu từ tenant thử.
- Không nghiên cứu: Tiki, Sendo, GrabMart, Selly (đều có trong seed hiện tại), MISA, Haravan Loyalty, Shopee Ads/TikTok Ads API.
- Không đánh giá giới hạn tốc độ, độ tươi dữ liệu và webhook. Các yếu tố này ảnh hưởng tới thiết kế connector nhưng không ảnh hưởng từ vựng.

## Câu hỏi chưa giải quyết

1. Sapo API có trả *danh mục nguồn* và cờ *mặc định/tùy chỉnh* của nguồn đơn không? Nếu có, pack Sapo có thể bỏ gần hết luật theo tên. Cách kiểm: gọi endpoint nguồn đơn bằng tài khoản Fine Japan.
2. Quy ước tag `<Sàn>_<gian>` trên đơn sàn Sapo là mặc định của Sapo hay do Fine Japan cấu hình?
3. Nhanh `saleChannel` 50/51 (Shopee chat/Lazada chat): đây là đơn sàn hay đơn chốt qua chat rồi giao ngoài sàn? Câu trả lời quyết định mã này map vào Marketplace hay Social.
4. "Đối tác & CTV" nên là B2B hay Direct ở tầng product default? Đây là quyết định của user. Gợi ý: để tenant chọn, vì CTV bán lẻ khác đại lý.
5. Khi tenant dùng cả OMS lẫn connector sàn trực tiếp, nguồn nào là bản ghi chính cho từng nhóm trường (§11.7)?
6. Đơn TikTok `is_sample_order` có cần một giá trị `order_nature=sample` riêng hay gộp vào `gift`?

---

## Nguồn (truy cập 2026-10-14)

**Sapo**
- [S1] Quản lý danh sách nguồn đơn hàng trên Sapo OmniAI: https://help.sapo.vn/quan-ly-danh-sach-nguon-don-hang-tren-phan-mem-sapo-omniai
- [S2] Tạo nhóm khách hàng tự động: https://help.sapo.vn/tao-nhom-khach-hang-tu-dong
- [S3] Quản lý hạng thành viên trên Sapo Loyalty: https://help.sapo.vn/huong-dan-quan-ly-hang-thanh-vien-tren-sapo-loyalty
- [S4] Tổng quan khuyến mại trên Sapo OmniAI: https://help.sapo.vn/tong-quan-ve-khuyen-mai-tren-sapo-omniai
- [S5] Báo cáo lợi nhuận theo kênh, gian/trang, nguồn đơn, chi nhánh: https://help.sapo.vn/xem-bao-cao-loi-nhuan-theo-kenh-gian-hang-trang-mang-xa-hoi-nguon-don-hang-va-chi-nhanh
- [S6] Tổng quan danh mục sản phẩm: https://help.sapo.vn/tong-quan-ve-danh-muc-san-pham-tren-sapo-omniai
- [S7] developers.sapo.vn (chuyển hướng tới https://developers.sapo.vn/services/partners/auth)
- [S8] (Bên thứ ba) Sapo MCP list_orders: https://policylayer.com/tools/nguyennguyenit-sapo-mcp/list-orders
- [Repo] `transformation/models/connectors/sapo_v2/staging/{src_sapo_v2_orders,stg_sapo_v2_orders,src_sapo_v2_customer_groups,stg_sapo_v2_customers,src_sapo_v2_products,stg_sapo_v2_order_discount_items,src_sapo_v2_order_returns,src_sapo_v2_price_lists}.sql`; `transformation/models/cdm/staging/std_orders.sql`; `transformation/seeds/taxonomy/ref_order_sources.csv`; `docs/context/sapo-platform.md`; `docs/context/order-customer-classification-staff-guide.md`; `ingestion/docs/SOURCES.md`

**Haravan**
- [S10] Orders: https://docs.haravan.com/docs/omni-apis/orders/
- [S11] Customer: https://docs.haravan.com/docs/omni-apis/customer/
- [S12] Products: https://docs.haravan.com/docs/omni-apis/products/
- [S13] Promotions: https://docs.haravan.com/docs/omni-apis/discount/promotions/
- [S14] Discount codes: https://docs.haravan.com/docs/omni-apis/discount/discount-codes/
- [S15] Location: https://docs.haravan.com/docs/omni-apis/location/
- [S16] AI toolkit, Orders: https://docs.haravan.com/docs/ai-toolkit/orders/
- [S80] Haravan pricing (kết nối sàn): https://en.haravan.com/pages/pricing

**Nhanh.vn**
- [S20] Model Constant: https://apidocs.nhanh.vn/v3/modelconstant
- [S21] Order list: https://apidocs.nhanh.vn/v3/order/list
- [S22] Order source: https://apidocs.nhanh.vn/v3/order/source
- [S23] Ecom shop: https://apidocs.nhanh.vn/v3/ecom/shop
- [S24] Customer list: https://apidocs.nhanh.vn/v3/customer/list
- [S25] Order tags: https://apidocs.nhanh.vn/v3/order/tags
- [S26] Product category: https://apidocs.nhanh.vn/v3/product/category
- [S27] Product brand: https://apidocs.nhanh.vn/v3/product/brand
- [S28] Price list: https://apidocs.nhanh.vn/v3/promotion/pricelist

**Pancake POS**
- [S30] Pancake POS Open API (OpenAPI 3.1): https://docs.pancake.biz/pos/api/ (spec: https://docs.pancake.biz/pos/api/openapi.json)

**KiotViet**
- [S40] Hướng dẫn Public API Retail: https://www.kiotviet.vn/huong-dan-su-dung-kiotviet/retail-ket-noi-api/public-api/

**Shopee Open Platform** (đọc qua endpoint JSON của trang docs)
- [S50] v2.order.get_order_detail: https://open.shopee.com/documents/v2/v2.order.get_order_detail?module=94&type=1
- [S51] v2.order.get_order_list: https://open.shopee.com/documents/v2/v2.order.get_order_list?module=94&type=1
- [S52] v2.payment.get_escrow_detail: https://open.shopee.com/documents/v2/v2.payment.get_escrow_detail?module=97&type=1
- [S53] v2.product.get_category; [S54] v2.product.get_brand_list; [S55] v2.voucher.get_voucher; [S56] v2.shop.get_shop_info (cùng cổng https://open.shopee.com/documents/v2/)

**TikTok Shop**
- [S60] Get Order Detail 202309 (cổng chính thức, JS): https://partner.tiktokshop.com/docv2/page/get-order-detail-202309. Mirror SDK model: https://github.com/phamconganh/tiktok-shop-sdk/blob/HEAD/model/order/V202309/GetOrderDetailResponseDataOrders.ts và `…OrdersPayment.ts`
- [S61] Finance fee breakdown (mirror SDK): https://github.com/phamconganh/tiktok-shop-sdk/blob/HEAD/model/finance/V202501/GetTransactionsbyStatementResponseDataTransactionsFeeTaxBreakdownFee.ts
- [S62] Categories/Brands (mirror SDK): `model/product/V202309/GetCategoriesResponseDataCategories.ts`, `GetBrandsResponseDataBrands.ts` (cùng repo)
- [S63] (Thứ cấp) Odoo `sale_tiktok/const.py`: https://github.com/maarid/odoo19_enterprise_full/blob/HEAD/odoo/addons/sale_tiktok/const.py

**Lazada**
- [S70] Cổng chính thức (JS): https://open.lazada.com/apps/doc/api?path=%2Forders%2Fget. Mirror JSON thô: https://github.com/lazykern/ecommerce-api-docs/tree/HEAD/data/raw/lazada/apis (order-api/getorders.json, getorderitems.json; finance-api/querytransactiondetails.json; product-api/getcategorytree.json, getbrandbypages.json)
