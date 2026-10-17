# Tham khảo: Shopify tổ chức phân loại như thế nào

> Tài liệu tham khảo cho thiết kế cơ chế phân loại chuẩn (feature → rules-as-data → tenant label + canonical value).
> Nghiên cứu ngày 2026-10-14. Mọi khẳng định có mã nguồn `[Sx]` (danh sách ở cuối). Điểm chưa chắc chắn đánh dấu **(chưa xác minh)**.
> Admin API tham chiếu bản `latest` = `2026-10` tại ngày truy cập [S11]. REST Admin API là legacy từ 2024-10-01 [S47], nên tài liệu này lấy GraphQL làm chuẩn.

## TL;DR

1. **Shopify tách hai lớp.** Mỗi lớp có trường riêng: **lớp canonical do nền tảng cố định** (enum, cây taxonomy, metric có công thức) và **lớp merchant tự định nghĩa** (tags, `productType`, `vendor`, collections, segments, metafields). Shopify không bắt merchant chọn một trong hai. Ví dụ: một product có cả `category` (taxonomy chuẩn) lẫn `productType` (chuỗi tự do) [S7][S9]. Mô hình "tenant label + canonical value bắt buộc" của chúng ta khớp với cách làm này.
2. **Canonical thường là giá trị *tính ra*, không phải nhập tay.** Các trường `displayFinancialStatus`, `displayFulfillmentStatus`, `rfmGroup`, `predictedSpendTier`, `is_pos_sale`, `is_b2b_order`, `new_or_returning_customer`, `discount_class` và `discount_method` đều do Shopify suy ra từ dữ liệu giao dịch. Merchant không sửa được [S37][S38][S21][S50].
3. **Rules-as-data đã có sẵn ở ba chỗ.** (a) Smart collection dùng bộ ba `column / relation / condition`, với 15 column và 10 relation [S59][S60]. (b) Customer segment lưu dưới dạng *chuỗi query* ShopifyQL trong `Segment.query` [S25][S28]. (c) Mapping giữa các taxonomy là file YAML `from_shopify.yml` / `to_shopify.yml` có version [S4]. Cả ba đều là dữ liệu, không phải code.
4. **Cầu nối giữa phần merchant tự định nghĩa và báo cáo chuẩn.** Metafield definition bật capability `analyticsQueryable` thì xuất hiện như một dimension trong ShopifyQL, với cú pháp `<owner>.metafields.<namespace>.<key>`. Shopify lấy ví dụ chính là `is_gift_order` [S49][S50]. Đây là cách Shopify cho báo cáo chuẩn group theo nhãn riêng của từng merchant.
5. **Kênh bán dùng "handle ổn định + displayName đổi được".** Order attribution definition có `handle` cố định, được ghi vào `sourceName`, và `displayName` có thể đổi tên. Order không khớp definition nào thì rơi về attribution mặc định của app [S14][S13]. Tương đương với "mã canonical + nhãn tenant + `UNMAPPED`" của chúng ta.
6. **Những gì Shopify KHÔNG chuẩn hoá** (chúng ta phải tự làm canonical): loại khách ngoài cặp B2B/không B2B, mục đích đơn (quà tặng, nội bộ, KOL), nhóm thương hiệu, phân loại lý do giảm giá theo nghiệp vụ. Shopify chỉ có `test: Boolean` cho đơn test [S11] và để phần còn lại cho tags hoặc metafields. **Bài học:** bộ domain canonical của chúng ta phải rộng hơn Shopify, vì khách Việt Nam phụ thuộc nhiều vào phân loại thủ công trên Sapo/MISA.

---

## 1. Standard Product Taxonomy

### 1.1 Cấu trúc

| Khía cạnh | Chi tiết | Nguồn |
|---|---|---|
| Thực thể | Category (cây), Attribute, Value, Return reason, Disclosure (cảnh báo pháp lý theo khu vực), Integration mapping, Localization | [S1][S2] |
| Vertical (gốc) | 26 file trong `data/categories/`: `aa` Apparel & Accessories, `ae` Arts & Entertainment, `ap` Animals & Pet Supplies, `bi` Business & Industrial, `bt` Baby & Toddler, `bu` Bundles, `co` Cameras & Optics, `el` Electronics, `fb` Food, Beverages & Tobacco, `fr` Furniture, `gc` Gift Cards, `ha` Hardware, `hb` Health & Beauty, `hg` Home & Garden, `lb` Luggage & Bags, `ma` Mature, `me` Media, `na` Uncategorized, `os` Office Supplies, `pa` Product Add-Ons, `rc` Religious & Ceremonial, `se` Services, `sg` Sporting Goods, `so` Software, `tg` Toys & Games, `vp` Vehicles & Parts | [S2] |
| ID category | Nối chuỗi theo đường đi trên cây: `hb` → `hb-1` (Health Care) → `hb-1-1` (Acupuncture) → `hb-1-1-1`. GID trên API: `gid://shopify/TaxonomyCategory/aa`. Ví dụ lá: `aa-1-13-7` | [S2][S4][S10] |
| Quy mô (nhánh `main`, VERSION `2026-11-unstable`, đếm ngày 14/10/2026) | ~14.600 node category, sâu tối đa 8 tầng (tầng 0 có 26 node, tầng 4 nhiều nhất với ~5.159 node); 8.233 base attribute + 316 extended attribute; ~73.500 value. Các con số này do chúng tôi tự đếm từ YAML, không phải số Shopify công bố | [S2][S3] |
| Attribute | `id` dạng số, `name`, `handle`, `friendly_id`, `description`, `values` (danh sách handle value). Ví dụ: `color` có các value `color__black`, `color__blue`... | [S3] |
| Extended attribute | Attribute "con" dùng chung tập value với base attribute qua trường `values_from`. Ví dụ: `frame_material` lấy value từ `furniture/fixture_material` | [S3] |
| Value | `id`, `name`, `handle`, `friendly_id` theo dạng `<attribute>__<value>` | [S3] |
| Gắn attribute vào category | Mỗi node category khai báo `attributes:` và `return_reasons:`. Ví dụ `hb` có `care_instructions`, `hb-1` có `age_group`, `allergen_information`... | [S2] |
| Node "chưa phân loại" | `na` Uncategorized: không có con, không có attribute. Help center ghi rằng product không gán category sẽ bị lưu là "uncategorized" | [S2][S7] |
| Field trên API | `TaxonomyCategory`: `id`, `name`, `fullName` (vd. "Animals & Pet Supplies > Pet Supplies > Dog Supplies > Dog Beds"), `parentId`, `ancestorIds`, `childrenIds`, `level`, `isRoot`, `isLeaf`, `isArchived`, `attributes` | [S8] |

### 1.2 Version, phát hành, license

| Khía cạnh | Chi tiết | Nguồn |
|---|---|---|
| Version | CalVer, đồng bộ lịch phát hành API, đặt tên theo tháng (`2024-07`...). Bản stable ra tối đa mỗi quý, vào đầu quý | [S1] |
| Bản đã phát hành | `shopify/2022-02` (legacy), `2024-07`, `2024-10`, `2025-03`, `2025-09`, `2025-12`, `2026-02`, `2026-05`, `2026-08`. Release GitHub mới nhất: `v2026-08` (24/08/2026) | [S4][S6] |
| Category bị gỡ | Không xoá mà đánh dấu `isArchived`. Mapping từ legacy sang mới nằm trong integration `shopify/*`, ví dụ `126 → aa` | [S8][S4] |
| Quy mô thay đổi | Bản 2026-05 thêm hơn 2.000 category và hơn 4.000 attribute | [S5] |
| Định dạng phân phối | Asset gzip trên GitHub Releases, tên theo mẫu `<basename>.<locale>.<format>.gz` (`txt`, `json`), vd. `categories.en.json.gz`, `integrations.all_mappings.en.json.gz`. URL stable: `releases/latest/download/<asset>` hoặc `releases/download/v<version>/<asset>`. URL unstable: `releases/download/unstable/<asset>` | [S1][S5] |
| Cảnh báo | Thư mục `dist/` đang commit trong repo đã deprecated và **sẽ bị xoá khỏi `main` ngày 31/10/2026**. Pipeline nào đang đọc `dist/` phải chuyển sang release asset | [S1][S5] |
| Bản dịch | `data/localizations/{categories,attributes,values,return_reasons,disclosures}`. Chưa kiểm tra có tiếng Việt hay không **(chưa xác minh)** | [S1] |
| License | MIT. Đóng góp phải ký Shopify CLA | [S1] |
| Đóng góp | Gửi PR vào `data/`; maintainer sinh lại phần phân phối. Tool ETL viết bằng Ruby (`bin/product_taxonomy dist|docs|release`) | [S1] |

### 1.3 Mapping sang taxonomy khác (integrations)

- Cấu trúc thư mục: `data/integrations/<integration>/<version>/mappings/{from_shopify.yml,to_shopify.yml}` cùng `full_names.yml`. Danh sách integration và version nằm trong `integrations.yml` [S4].
- Integration đang hỗ trợ: **Google** (`google/2021-09-21`) và **Shopify** (bản legacy `2022-02` và các bản sau). Mapping giữa các version Shopify với nhau cũng được coi là một integration [S4].
- Mỗi luật có dạng `input: {product_category_id: aa}` → `output: {product_category_id: ['166']}`. Output là danh sách nên một category có thể map ra nhiều category [S4].
- **Bài học:** mapping giữa hai hệ phân loại được quản lý như dữ liệu, có version và có chiều (from/to). Đây đúng là hình dạng của "rules-as-data: direct mapping".

### 1.4 Merchant dùng taxonomy thế nào

| Trường trên Product | Loại | Ý nghĩa | Nguồn |
|---|---|---|---|
| `category` | `TaxonomyCategory` (canonical) | Mỗi product có một category. Shopify dùng nó để tính thuế (Shopify Tax), đẩy lên các kênh như Google/Facebook, làm điều kiện collection, lọc danh sách và phân tích lý do trả hàng. Khi tạo product, AI gợi ý category; merchant chấp nhận hoặc chọn category khác | [S7][S9] |
| `productType` | `String!` (tenant) | "The product type that merchants define", trường tuỳ ý của merchant. `customProductType` đã deprecated | [S9] |
| `vendor` | `String!` (tenant) | Nhà cung cấp / thương hiệu | [S9] |
| `tags` | `[String!]!` (tenant) | Từ khoá tự do. Ghi đè toàn bộ khi update; muốn thêm thì dùng `tagsAdd` | [S9][S61] |
| `collections` | thủ công hoặc smart (rule) | Xem 1.5 | [S59] |
| Category metafields | metafield gắn theo category | "Product attributes" của taxonomy. Value có sẵn mặc định, merchant đổi tên được (vd. đổi tên màu), và có thể liên kết với variant option để hiện swatch | [S7] |

**Cách attribute đi vào dữ liệu product.** Value của attribute được lưu trong metaobject. Metaobject đó có trường tham chiếu `TaxonomyValue` (trong ví dụ chính thức là `color_taxonomy_reference` và `pattern_taxonomy_reference`), và một metafield kiểu `list.metaobject_reference` trên Product trỏ tới metaobject này. Product option có thể liên kết với metafield qua `linkedMetafield {namespace, key}` [S10]. Ví dụ chính thức dùng namespace `custom` (`custom.color-pattern`, type metaobject `custom--color-pattern`) [S10]. Một số nguồn bên thứ ba cho rằng category metafield thật nằm ở `shopify.<attribute>` → metaobject `shopify--<attribute>` → `TaxonomyValue` **(chưa xác minh, nguồn bên thứ ba [S65])**. Ngoài ra, `MetafieldDefinition.constraints {key, values}` giới hạn definition theo "subtype" của resource, và đây có thể là cơ chế gắn metafield theo category **(suy luận từ mô tả field [S56], chưa xác minh)**.

### 1.5 Smart collection: rules-as-data cho product

`CollectionRule = {column, relation, condition}` [S59][S60]:

| `CollectionRuleColumn` | `CollectionRuleRelation` |
|---|---|
| `TAG`, `TITLE`, `TYPE`, `VENDOR`, `VARIANT_PRICE`, `VARIANT_COMPARE_AT_PRICE`, `VARIANT_WEIGHT`, `VARIANT_INVENTORY`, `VARIANT_TITLE`, `IS_PRICE_REDUCED`, `PRODUCT_CATEGORY_ID`, `PRODUCT_CATEGORY_ID_WITH_DESCENDANTS`, `PRODUCT_TAXONOMY_NODE_ID`, `PRODUCT_METAFIELD_DEFINITION`, `VARIANT_METAFIELD_DEFINITION` | `EQUALS`, `NOT_EQUALS`, `CONTAINS`, `NOT_CONTAINS`, `STARTS_WITH`, `ENDS_WITH`, `GREATER_THAN`, `LESS_THAN`, `IS_SET`, `IS_NOT_SET` |

Điểm đáng chú ý: `PRODUCT_CATEGORY_ID_WITH_DESCENDANTS` cho phép một rule khớp cả cây con. Đây là luật phân cấp chạy trên taxonomy canonical. Metafield muốn dùng làm điều kiện collection thì definition phải bật `useAsCollectionCondition` / capability `smartCollectionCondition` [S54][S55].

---

## 2. Kênh bán và attribution đơn hàng

### 2.1 Các trường trên `Order`

| Field | Kiểu | Ý nghĩa | Nguồn |
|---|---|---|---|
| `sourceName` | `String` | Mô tả: "the name of the source associated with the order, such as `web`, `mobile_app`, or `pos`". Khi tạo đơn qua API, trường này nhận *handle của order attribution definition* (vd. `youtube`, `channel:amazon-us`) | [S11][S13] |
| `sourceIdentifier` | `String` | ID đơn ở hệ thống gốc (POS, marketplace) | [S11] |
| `sourceUrl` | `URL` | Link tới đơn trên hệ thống gốc, hiển thị trong admin | [S13] |
| `app` | `OrderApp {id, name, icon}` | App đã tạo đơn, vd. Online Store, Point of Sale hoặc app tuỳ chỉnh | [S11] |
| `publication` | `Publication` | Kênh bán mà đơn đến từ (Online Store, POS...). `channelInformation` đã deprecated | [S11] |
| `retailLocation` | `Location` | Điểm bán vật lý. Trả `null` với đơn draft POS được "mark as paid" từ admin | [S11] |
| `staffMember` | `StaffMember` | Nhân viên tạo hoặc chịu trách nhiệm đơn (đơn gọi điện, đơn thủ công) | [S11] |
| `merchantOfRecordApp` | `OrderApp` | App đóng vai merchant of record (thu và nộp thuế) | [S11] |
| `customerJourneySummary` | xem 2.3 | Các lượt truy cập trước khi đặt đơn | [S11][S16] |
| `test` | `Boolean!` | Đơn test (Bogus Gateway hoặc cổng thanh toán ở test mode). Không đổi qua lại giữa đơn test và đơn thật được | [S11] |

**Giá trị `source_name` thường gặp.** Trong filter `orders(query:)`, Shopify lấy ví dụ `source_name:web` và `source_name:shopify_draft_order`, kèm mô tả "web orders, POS sales, draft orders, or third-party channels" [S12]. Danh sách "protected values" (`web`, `pos`, `shopify_draft_order`, `iphone`, `android`, app khác không được ghi các giá trị này) và hành vi "mặc định là app ID nếu không truyền" chỉ có trong tài liệu cũ và thread cộng đồng; trang hiện hành không còn liệt kê **(chưa xác minh với tài liệu hiện hành [S62][S63])**. Shopify cũng không có API liệt kê mọi `source_name` có thể có [S63]. **Hệ quả:** không nên coi `source_name` là enum đóng.

### 2.2 Order attribution definition (connector marketplace)

| Thành phần | Chi tiết | Nguồn |
|---|---|---|
| `handle` | Định danh ổn định, phạm vi một app trên một store. Ví dụ: `google-shopping`, `youtube`. Definition do `channelCreate` sinh ra có dạng `channel:<channel.handle>` (vd. `channel:amazon-us-a1b2c3`) | [S14] |
| `displayName` | Tên hiển thị. Muốn đổi tên thì sửa trường này, **không đổi handle**, vì đổi handle làm khó tra ngược lịch sử | [S14] |
| `icon` | SVG, viewBox `0 0 20 20` | [S14] |
| Khai báo | Extension TOML `order_attribution_config`, hoặc gọi `orderAttributionDefinitionUpsert` / `Delete` lúc runtime | [S14] |
| Fallback | Đơn không khớp definition nào thì `Order.attribution` trả attribution mặc định của app | [S14] |
| Hiển thị | Bộ lọc kênh trong admin, analytics và Admin API | [S14] |
| `Channel` | `handle`, `name`, `app`, `accountId` (vd. Amazon Seller ID, Google Merchant Center ID), `accountName`, `activeRegions`, `markets` | [S15] |

### 2.3 UTM và customer journey

- `CustomerJourneySummary`: `firstVisit`, `lastVisit`, `moments`, `momentsCount`, `daysToConversion`, `customerOrderIndex` (thứ tự đơn của khách, không tính đơn test), `ready` [S16].
- `CustomerVisit`: `source` (nền tảng, email, direct, domain, QR code, unknown), `sourceType: MarketingTactic`, `sourceDescription`, `referrerUrl`, `landingPage`, `referralCode` (đọc từ tham số `ref`/`source`/`r`), `utmParameters`, `marketingEvent` [S17].
- `UTMParameters`: `campaign`, `content`, `medium`, `source`, `term` [S19].
- Enum `MarketingTactic`: `ABANDONED_CART`, `AD`, `AFFILIATE`, `LINK`, `LOYALTY`, `MESSAGE`, `NEWSLETTER`, `NOTIFICATION`, `POST`, `RETARGETING`, `SEO`, `STOREFRONT_APP`, `TRANSACTIONAL` [S18].

### 2.4 Kênh trong analytics (ShopifyQL `sales`)

Phân biệt hai trục: **kênh bán** (đơn được đặt ở đâu) và **kênh marketing** (cái gì đưa khách tới) [S50].

| Trục | Dimension | Nguồn |
|---|---|---|
| Kênh bán | `sales_channel`, `order_sales_channel` (vd. "Online Store", "POS"), `order_sales_channel_id`, `channel_id`, `sale_sales_channel_id`, `first_order_sales_channel` | [S50] |
| POS | `is_pos_sale`, `pos_location_id`, `pos_location_name`, `is_physical_storefront`, `assisting_staff_id`, `staff_member_name` | [S50] |
| AI agent | `agentic_sales_channel` (Google AI Mode and Gemini, Microsoft Copilot, Shop), `agentic_referring_channel` (thêm ChatGPT) | [S50] |
| Marketing | `referring_channel`, `referring_medium`, `referring_platform`, `traffic_type` (organic/paid/direct), `marketing_channel` (đã chuẩn hoá), `marketing_campaign`, `order_utm_*`, `order_referrer_*`, `order_marketing_event_type`, `is_shop_referral_order` | [S50] |
| Attribution | Mệnh đề `WITH LAST_CLICK_ATTRIBUTION` sinh metric `total_sales__last_click` | [S48] |

---

## 3. Tổ chức khách hàng

### 3.1 Trường trên `Customer`

| Field | Kiểu | Canonical hay tenant | Nguồn |
|---|---|---|---|
| `tags` | `[String!]!` | tenant | [S20] |
| `amountSpent` | `MoneyV2!` (lifetime) | canonical (tính ra) | [S20] |
| `numberOfOrders` | `UnsignedInt64!` (lifetime) | canonical (tính ra) | [S20] |
| `statistics.rfmGroup` | `CustomerRfmGroup` | canonical (Shopify tính) | [S21] |
| `statistics.predictedSpendTier` | `CustomerPredictedSpendTier` | canonical (Shopify tính) | [S21] |
| `state` | `CustomerState`: `DECLINED`, `DISABLED`, `ENABLED`, `INVITED` | canonical | [S24] |
| `companyContactProfiles` | `[CompanyContact!]!` | cầu nối sang B2B | [S20] |
| `taxExempt`, `taxExemptions` | | canonical | [S20] |
| `metafields` | | tenant (có thể dùng definition chuẩn, vd. `facts.birth_date`) | [S20][S53] |
| `lastOrder`, `lifetimeDuration`, `createdAt` | | dữ kiện | [S20] |

### 3.2 RFM và predicted spend tier (canonical do Shopify tính)

`CustomerRfmGroup` có 11 giá trị cố định [S22]:

| Giá trị | Mô tả ngắn (tóm tắt từ docs) |
|---|---|
| `CHAMPIONS` | Mua rất gần đây, nhiều đơn nhất, chi nhiều nhất |
| `LOYAL` | Mua gần đây, nhiều đơn, chi cao |
| `ACTIVE` | Mua gần đây, số đơn và mức chi vừa phải |
| `NEEDS_ATTENTION` | Mua gần đây, số đơn và mức chi trung bình |
| `PROMISING` | Mua gần đây, ít đơn, chi thấp |
| `NEW` | Mua rất gần đây, ít đơn, chi thấp |
| `AT_RISK` | Lâu chưa mua nhưng lịch sử mua mạnh |
| `PREVIOUSLY_LOYAL` | Lâu chưa mua, lịch sử mua rất mạnh |
| `ALMOST_LOST` | Lâu chưa mua, ít đơn, chi thấp |
| `DORMANT` | Không hoạt động, ít đơn, chi thấp |
| `PROSPECTS` | Chưa có đơn nào |

- Shopify **không công bố** cách chấm điểm R/F/M. Nguồn bên thứ ba cho rằng mỗi chiều được chấm 1–5 theo nhóm 20% *trong chính store đó* **(chưa xác minh [S66])**. Nếu đúng, ngưỡng là *tương đối theo từng store*, còn tên nhóm thì cố định.
- `CustomerPredictedSpendTier`: `HIGH` (dự báo chi tiêu ở mức cao nhất của store trong năm tới), `MEDIUM` (mức bình thường), `LOW` (bằng 0 hoặc thấp nhất) [S23]. Điều kiện dùng: store đã có hơn 100 lượt bán, và chỉ tính khách đã mua ít nhất 1 lần. Mô hình dựa trên tần suất mua, giá trị đơn so với AOV của store, số đơn và độ gần của đơn cuối [S26].

### 3.3 Segments: phân nhóm khách dạng rules-as-data

- `Segment {id, name, query, creationDate, lastEditDate}`. Membership là *động*: khách tự vào hoặc ra khỏi segment khi thoả hay hết thoả điều kiện [S28][S25].
- Cú pháp chỉ có phần `WHERE` của ShopifyQL, dạng `<attribute> <operator> <value>`, kết hợp bằng `AND`/`OR`, tối đa 10 mệnh đề mỗi nhóm [S25].
- Operator theo kiểu dữ liệu: Boolean/Enum/String dùng `=`, `!=`; Date/Integer/Float dùng thêm `>`, `>=`, `<`, `<=`, `BETWEEN`; List dùng `CONTAINS`, `NOT CONTAINS`; Function dùng `MATCHES`, `NOT MATCHES` [S25].

| Nhóm attribute | Attribute | Nguồn |
|---|---|---|
| Giá trị / tần suất | `amount_spent`, `number_of_orders`, `orders_placed(...)`, `first_order_date`, `last_order_date`, `predicted_spend_tier`, `rfm_group` | [S25] |
| Hành vi | `products_purchased MATCHES (id=…, tag=…, date >= -12m)`, `abandoned_checkout_date`, `storefront_event.product_viewed/collection_viewed`, `shopify_email.opened/clicked/...` | [S25] |
| Hồ sơ | `customer_tags` (CONTAINS), `customer_account_status`, `customer_added_date`, `customer_email_domain`, `customer_language`, `customer_cities/countries/regions`, `customer_within_distance(...)`, `created_by_app_id` | [S25] |
| Đồng ý nhận marketing | `email_subscription_status` (vd. `'SUBSCRIBED'`), `sms_subscription_status`, `product_subscription_status` | [S25] |
| B2B | `companies` (ID company mà khách là contact) | [S25] |
| Ngày tuỳ chỉnh | `anniversary('metafields.facts.birth_date') = today` | [S25] |

Ví dụ ghép hai trường canonical: `predicted_spend_tier = 'HIGH' AND email_subscription_status = 'SUBSCRIBED'` [S26]. Trang reference không liệt kê đầy đủ tập giá trị của các enum subscription; nhãn hiển thị lấy từ schema ShopifyQL ở mục 5 [S25][S50].

### 3.4 Customer tags

- Merchant tự định nghĩa, không phân biệt hoa/thường. Gắn thủ công hoặc hàng loạt. Khi gộp hồ sơ khách, tổng số tag sau gộp không quá 250 [S27].
- `tagsAdd` dùng được cho Order, DraftOrder, Customer, Product, Article và DiscountNode [S61].
- Segment không kiểm tra tag có tồn tại hay không [S25]. **Bài học:** tag là chuỗi tự do, không có từ điển. Đây là lý do chúng ta cần bảng ánh xạ tag → canonical và cơ chế giám sát `UNMAPPED`.

### 3.5 B2B: tách bán sỉ khỏi bán lẻ bằng *thực thể*, không bằng tag

| Thực thể | Field chính | Nguồn |
|---|---|---|
| `Company` | `name`, `externalId`, `contacts`, `mainContact`, `contactRoles`, `locations`, `orders`, `totalSpent`, `customerSince`, `metafields`, `note` | [S29] |
| `CompanyLocation` | `company`, `name`, `externalId`, `billingAddress`, `shippingAddress`, `currency`, `locale`, `catalogs`, `buyerExperienceConfiguration` (cấu hình checkout B2B), `taxSettings`, `staffMemberAssignments`, `metafields` | [S30] |
| `Catalog` (interface) | `title`, `status`, `priceList`, `publication`. Ba kiểu cài đặt: `CompanyLocationCatalog`, `MarketCatalog`, `AppCatalog`. Enum `CatalogType`: `APP`, `COMPANY_LOCATION`, `MARKET`, `NONE` | [S31][S32] |
| `PriceList` | `currency`, `parent` (điều chỉnh tương đối), `prices` (giá cố định), `quantityRules` | [S33] |
| `Order.purchasingEntity` | Union `Customer` hoặc `PurchasingCompany`. Đơn B2B có thêm `poNumber` | [S34][S11] |

- Mỗi khách sỉ phải được tạo thành một **company**. Store có thể bán cả B2B lẫn D2C (blended) hoặc tách riêng store B2B [S35].
- Catalog gán cho company hoặc location. Khi nhiều catalog cho các giá khác nhau, khách thấy giá thấp nhất. Plan Basic/Grow/Advanced giới hạn 3 catalog active; Plus không giới hạn [S36].
- Trong analytics: `is_b2b_order`, `company_id`, `company_name`, `company_location_name`, `billing_company` [S50].
- **Bài học:** "sỉ hay lẻ" ở Shopify là **dữ kiện cấu trúc** (đơn có `PurchasingCompany` hay không), không phải luật dò tag. Sapo/MISA không có thực thể này, nên phía chúng ta phải suy ra `customer_type = WHOLESALE` bằng luật. Dù vậy, giá trị canonical nên giữ nguyên ý nghĩa nhị phân B2B/B2C như Shopify, còn các tầng chi tiết (đại lý cấp 1, CTV...) để ở tenant label.

---

## 4. Tổ chức đơn hàng

### 4.1 Enum trạng thái (canonical)

| Enum | Giá trị | Nguồn |
|---|---|---|
| `OrderDisplayFinancialStatus` | `PENDING`, `AUTHORIZED`, `PARTIALLY_PAID`, `PAID`, `PARTIALLY_REFUNDED`, `REFUNDED`, `VOIDED`, `EXPIRED` | [S37] |
| `OrderDisplayFulfillmentStatus` | `UNFULFILLED`, `PARTIALLY_FULFILLED`, `FULFILLED`, `IN_PROGRESS`, `ON_HOLD`, `SCHEDULED`, `REQUEST_DECLINED`, `FULFILLMENT_NOT_REQUIRED`; đã deprecated: `OPEN`, `PENDING_FULFILLMENT`, `RESTOCKED` | [S38] |
| `OrderCancelReason` | `CUSTOMER`, `DECLINED`, `FRAUD`, `INVENTORY`, `STAFF`, `OTHER` | [S39] |
| Filter `status` | `open`, `closed`, `cancelled`, `not_closed` | [S12] |
| Filter `return_status` | `return_requested`, `in_progress`, `inspection_complete`, `returned`, `return_failed`, `no_return` | [S12] |
| Filter `delivery_method` | `shipping`, `pick-up`, `retail`, `local`, `pickup-point`, `none` | [S12] |
| Filter `risk_level` | `high`, `medium`, `low`, `none`, `pending` | [S12] |
| Filter `chargeback_status` | `accepted`, `charge_refunded`, `lost`, `needs_response`, `prevented`, `under_review`, `won` | [S12] |

Enum có lịch sử deprecate rõ ràng: giá trị cũ được giữ lại, đánh dấu deprecated và chỉ sang giá trị thay thế [S38]. Đây là mẫu tốt cho canonical value của chúng ta: không xoá giá trị, chỉ deprecate kèm giá trị thay thế.

### 4.2 Loại đơn

| Loại | Cách nhận diện | Nguồn |
|---|---|---|
| Online Store | `sourceName = web`; `app.name` = Online Store | [S11][S12] |
| POS | `sourceName = pos`, `retailLocation`, `is_pos_sale` | [S11][S50] |
| Draft order (đơn tạo hộ: điện thoại, chat, sỉ, pre-order) | Tồn tại dạng `DraftOrder` với `status`: `OPEN`, `INVOICE_SENT`, `COMPLETED`; khi thanh toán sẽ sinh `Order` với `source_name:shopify_draft_order`. Có `tags`, `poNumber`, `purchasingEntity`, `paymentTerms`. Draft tạo từ 01/04/2025 bị tự xoá sau 1 năm không hoạt động | [S40][S41][S12] |
| B2B | `purchasingEntity` là `PurchasingCompany`; `is_b2b_order` | [S34][S50] |
| Marketplace / app | `sourceName` = handle của attribution definition; `Channel.accountId` | [S13][S14][S15] |
| Test | `test = true` | [S11] |
| Subscription | `subscription_or_one_time` (analytics) | [S50] |

### 4.3 Discount

| Khái niệm | Giá trị | Nguồn |
|---|---|---|
| `DiscountClass` (giảm vào đâu) | `PRODUCT`, `ORDER`, `SHIPPING` | [S42] |
| Kiểu discount (union `Discount`) | `DiscountCodeBasic`, `DiscountCodeBxgy`, `DiscountCodeFreeShipping`, `DiscountCodeApp`, `DiscountAutomaticBasic`, `DiscountAutomaticBxgy`, `DiscountAutomaticFreeShipping`, `DiscountAutomaticApp`. Hai trục: code hay automatic × basic / BxGy / free shipping / app (Shopify Functions) | [S46] |
| `DiscountStatus` | `ACTIVE`, `EXPIRED`, `SCHEDULED` | [S46] |
| Discount application trên đơn | Interface `DiscountApplication` với các kiểu: automatic, discount code, manual, script. REST cũ ghi `type`: `manual`, `script`, `discount_code` | [S43][S47] |
| `allocationMethod` | `ACROSS` (chia đều cho các dòng được áp), `EACH` (áp vào từng dòng), `ONE` (deprecated) | [S43] |
| `targetSelection` | `ALL`, `ENTITLED`, `EXPLICIT` | [S44] |
| `targetType` | `LINE_ITEM`, `SHIPPING_LINE` | [S45] |
| Analytics | `discount_class` (Order/Shipping/Product), `discount_method` (Automatic/Manual/Discount code/Script), `discount_type` (Fixed amount/Percentage), `price_rule_type` (vd. "Percentage (automatic)", "Buy X Get Y"), `discount_code`, `discount_name`, `is_discounted_sale`; metric `line_item_discounts`, `order_level_discounts`, `shipping_charge_discounts` | [S50] |

**Bài học:** Shopify phân loại discount theo **cơ chế** (áp vào đâu, kích hoạt thế nào, tính ra sao), không theo **mục đích kinh doanh** (khuyến mãi mùa, giảm cho nhân viên, quà KOL). Mục đích kinh doanh là việc của merchant, thường ghi bằng tên/code discount hoặc tag. `primary_discount_type` 10 loại của Fine Japan là phân loại theo mục đích, nên cần lớp canonical riêng. Có thể thêm một trục cơ chế nhỏ (class × method) lấy thẳng từ nguồn khi nguồn có dữ liệu này.

### 4.4 Order tags và mục đích đơn

- `Order.tags` là `[String!]!`, ghi đè toàn bộ khi update. Lọc được bằng `tag:` và `tag_not:` [S11][S12].
- Shopify không có trường canonical cho "mục đích đơn" (quà tặng, nội bộ, mẫu thử...). Ví dụ chính thức của Shopify là tạo metafield `is_gift_order` rồi group báo cáo theo metafield đó [S49][S50].

---

## 5. Mô hình dữ liệu analytics (ShopifyQL)

### 5.1 Cấu trúc

- Cú pháp: `FROM <schema> SHOW <metrics> [WHERE] [GROUP BY] [TIMESERIES] [SINCE/UNTIL/DURING] [COMPARE TO] [WITH ...] [ORDER BY] [LIMIT] [VISUALIZE]`. Chạy được trong editor ở admin, qua `shopifyqlQuery` (GraphQL), Python SDK hoặc web component [S48].
- Schema là dataset theo nghiệp vụ: `sales`, `customers`, `chargebacks`, `fees`, `gift_cards`, `payments`, `payouts`... Mỗi schema định nghĩa metric và dimension cố định [S49].
- Schema `sales` ghi theo **sự kiện**: mỗi dòng là một event, nên một đơn có thể sinh nhiều dòng (refund, chỉnh sửa đơn). Cờ phân biệt: `order_or_sales_reversal`, `is_sales_reversal`, `is_sale_adjustment`, `line_type` (Product, Shipping, Duty, Tip...) [S50].

### 5.2 Định nghĩa metric chuẩn (giống nhau ở mọi merchant)

| Metric | Định nghĩa (tóm tắt) | Nguồn |
|---|---|---|
| `gross_sales` | Doanh thu đầu (top-line), trước khi trừ discount và reversal | [S50] |
| `discounts` | Phần giảm giá, chia thành `line_item_discounts` và `order_level_discounts` | [S50] |
| `sales_reversals` | Giá trị bị rút khỏi đơn do refund, trả hàng, huỷ hoặc chỉnh sửa. Từ 2026-10 thay cho `returns` (deprecated) | [S50] |
| `net_sales` | `gross_sales − discounts − sales_reversals`; không gồm thuế, phí ship, duty, phí khác | [S50] |
| `shipping_charges` | Phí ship sau discount ship, trước thuế ship | [S50] |
| `total_sales` | `net_sales + additional_fees + duties + shipping_charges + taxes` | [S50] |
| `average_order_value` | `(gross_sales − discounts) / orders` | [S50] |
| `gross_profit`, `gross_margin` | `net_sales − cost_of_goods_sold`; chỉ tính trên phần sales có ghi nhận COGS (`net_sales_with_cost_recorded`) | [S50] |
| `orders`, `customers`, `new_customers`, `returning_customers`, `returning_customer_rate` | Đếm đơn/khách; `returning_customer_rate = returning / customers` | [S50] |

Lưu ý: tháng 10/2026 Shopify đổi tên cả nhóm metric `returns` → `sales_reversals` (`gross_returns` → `gross_sales_reversals`, `quantity_returned` → `reversed_quantity`...). Tên cũ được giữ ở trạng thái deprecated [S50]. Tức là cả *tên metric chuẩn* cũng có version và lộ trình deprecate.

### 5.3 Dimension: canonical vs tenant cùng nằm trong một schema

| Loại | Dimension (ví dụ) | Nguồn |
|---|---|---|
| Canonical do Shopify tính | `sales_channel`, `is_pos_sale`, `is_b2b_order`, `is_canceled_order`, `order_payment_status`, `order_fulfillment_status`, `order_cancellation_reason`, `order_risk_level`, `new_or_returning_customer`, `months_since_first_purchase`, `rfm_group`, `predicted_spend_tier`, `discount_class`, `discount_method`, `line_type`, `return_reason` (lấy từ taxonomy return reasons), `product_variant_abc_grade` (A ≈ 80% doanh thu, B 15%, C 5%), `traffic_type`, `marketing_channel` | [S50] |
| Tenant tự định nghĩa | `order_tag(s)`, `customer_tag(s)`, `product_tag(s)`, `product_type`, `product_vendor`, `product_collection(s)`, `market`, `company_name`, `staff_member_name`, `pos_location_name`, `order_utm_*` | [S50] |
| Snapshot tại thời điểm bán | `product_type_at_time_of_sale`, `product_vendor_at_time_of_sale`, `product_title_at_time_of_sale`, `product_variant_sku_at_time_of_sale` | [S50] |
| Mở rộng theo merchant | `customer.metafields.<ns>.<key>`, `order.metafields…`, `product.metafields…`, `product_variant.metafields…` (schema `sales`); `customer.metafields…` (schema `customers`). Điều kiện: definition bật `analyticsQueryable` | [S49] |

**Cách Shopify giữ báo cáo chuẩn mà vẫn cho merchant tuỳ biến.** Metric và tập dimension canonical cố định nên report mẫu chạy được ở mọi store. Phần riêng của từng merchant chỉ đi vào dưới dạng *dimension bổ sung*: tags, các trường text tự do và metafield đã khai báo. Phần này không bao giờ làm thay đổi định nghĩa metric.

---

## 6. Metafields và metaobjects: cơ chế mở rộng

| Khía cạnh | Chi tiết | Nguồn |
|---|---|---|
| Metafield | Thêm một trường vào resource có sẵn (vd. hạng loyalty trên customer, luật routing trên order) | [S51] |
| Metaobject | Kiểu record mới do người dùng định nghĩa (size chart, nguyên liệu, review...). Thường đi kèm metafield tham chiếu tới nó | [S51] |
| Definition | `namespace`, `key`, `name`, `type`, `validations`, `ownerType`, `access`, `capabilities`, `constraints`, `standardTemplate`, `useAsCollectionCondition`, `pinnedPosition` | [S54] |
| Metafield không có definition | Lưu như chuỗi thô: không validate, không tìm kiếm được trong admin | [S51] |
| Owner type | `PRODUCT`, `PRODUCTVARIANT`, `COLLECTION`, `CUSTOMER`, `COMPANY`, `COMPANY_LOCATION`, `ORDER`, `DRAFTORDER`, `DISCOUNT`, `LOCATION`, `MARKET`, `SHOP`... | [S57] |
| Capability | `adminFilterable`, `analyticsQueryable`, `smartCollectionCondition`, `uniqueValues`, `cartToOrderCopyable` | [S55] |

**Namespace và quyền sở hữu** [S52]:

| Quyền sở hữu | Namespace | Ai đọc/ghi |
|---|---|---|
| App-owned | `$app` (GraphQL) / `app` (TOML), lưu thực tế với tiền tố `app--…` | App quản lý cấu trúc và giá trị; merchant mặc định `MERCHANT_READ`, có thể mở `MERCHANT_READ_WRITE` |
| Merchant-owned | Namespace không bị giữ chỗ, vd. `custom` | Merchant và mọi app có scope phù hợp |
| Shopify-reserved | `shopify--…` và namespace của các definition chuẩn | Shopify quản lý cấu trúc |
| App-data | Gắn trên `AppInstallation` | Chỉ app sở hữu; ẩn khỏi admin |

Access theo bề mặt: `admin`, `storefront` (`NONE` hoặc `PUBLIC_READ`), `customer_accounts` (`NONE`, `READ`, `READ_WRITE`) [S52].

**Standard definitions** là template có namespace và key đã được Shopify giữ chỗ cho "ý nghĩa cố định". Ví dụ: `descriptors.subtitle`, `descriptors.care_guide`, `facts.isbn`, `facts.upc`, `facts.ean`, `reviews.rating`, `reviews.rating_count`, `facts.birth_date` (CUSTOMER), `shopify--discovery--product_recommendation.related_products`, `shopify.unavailable_reason` [S53][S58]. Đây là tầng trung gian: merchant *chọn bật* một trường, nhưng tên và ý nghĩa của trường đó là chuẩn chung.

---

## 7. Bài học cho thiết kế của chúng ta

### 7.1 Canonical vs merchant-defined ở Shopify

| Domain | Canonical (nền tảng cố định) | Merchant-defined | Cầu nối |
|---|---|---|---|
| Danh mục sản phẩm | `category` (taxonomy, MIT, có version) | `productType`, `vendor`, `tags`, collections | AI gợi ý category; smart collection rule theo category hoặc cây con; mapping YAML có version |
| Thuộc tính sản phẩm | Attribute và value của taxonomy | Đổi tên value, thêm metaobject entry | Metaobject giữ tham chiếu `TaxonomyValue` |
| Kênh bán | `sales_channel`, `is_pos_sale`, `app`, `publication` | `displayName` của attribution | `handle` ổn định ghi vào `sourceName`; fallback về app |
| Kênh marketing | `MarketingTactic`, `traffic_type`, `marketing_channel` | Giá trị UTM tự đặt | Chuẩn hoá UTM/referrer sang `marketing_channel` |
| Khách: vòng đời / giá trị | `rfmGroup` (11), `predictedSpendTier` (3), `new_or_returning_customer` | Tags, segment | Segment query kết hợp được cả hai loại |
| Khách: sỉ / lẻ | `PurchasingCompany`, `is_b2b_order` | Tên company, catalog | Gán catalog cho company/location |
| Trạng thái đơn | Enum financial, fulfillment, cancel, return | Không có | Không cần cầu nối |
| Mục đích đơn | Chỉ có `test` | Tags, metafield `is_gift_order` | Metafield `analyticsQueryable` |
| Discount | `DiscountClass`, method, type, allocation | Tên và code discount | Không có canonical theo mục đích |

### 7.2 Mười nguyên tắc rút ra

1. **Luôn có hai cột, không gộp làm một.** Shopify giữ `category` và `productType` song song. Chúng ta giữ `<domain>_label` (tenant) cạnh `<domain>` (canonical), và report chuẩn chỉ group theo cột canonical. [S7][S9]
2. **Tập canonical nhỏ, cố định, có mô tả nghiệp vụ cho từng giá trị.** Ví dụ `CustomerRfmGroup` có đúng 11 giá trị, mỗi giá trị có một câu định nghĩa. Ngưỡng tính có thể tương đối theo từng tenant, nhưng tên nhóm thì không đổi. [S22]
3. **Có giá trị "chưa phân loại" chính thức.** Taxonomy có node `na`; attribution có fallback về app. Với chúng ta là `UNMAPPED` / `UNCATEGORIZED`, không để `NULL`. [S2][S14]
4. **Khoá ổn định tách khỏi nhãn hiển thị.** Handle dùng làm khoá và không đổi; muốn đổi nhãn thì sửa `displayName`. Seed của chúng ta nên có `code` bất biến và `label` sửa được. [S14]
5. **Deprecate, không xoá.** Enum giữ giá trị cũ kèm giá trị thay thế; category dùng `isArchived`; metric đổi tên có lộ trình chuyển. [S38][S8][S50]
6. **Version hoá bộ phân loại canonical** (CalVer theo quý) và **version hoá mapping** (`from`/`to`). Canonical của chúng ta nên có version, và mỗi bộ luật của tenant nên ghi rõ nó viết cho version canonical nào. [S1][S4]
7. **Luật có ba hình dạng khai báo** và cả ba đều có tiền lệ ở Shopify: mapping trực tiếp (integration YAML), điều kiện có toán tử (smart collection `column/relation/condition`) và biểu thức boolean (segment query). Thứ tự ưu tiên giữa các luật thì Shopify **không** có, vì segment cho phép một khách thuộc nhiều nhóm. Phần ưu tiên là của riêng chúng ta, vì domain của chúng ta là phân loại loại trừ lẫn nhau (mỗi bản ghi chỉ một nhãn). [S4][S59][S25]
8. **Cầu nối giữa tenant và report chuẩn là "dimension bổ sung có khai báo".** Một trường riêng của tenant chỉ được dùng trong analytics khi đã có definition (bật `analyticsQueryable`). Trường không khai báo thì không xuất hiện trong report. [S49][S51]
9. **Snapshot tại thời điểm giao dịch.** `*_at_time_of_sale` giữ phân loại sản phẩm theo lúc bán. Chúng ta cần quyết định domain nào phân loại theo point-in-time (vd. loại khách lúc đặt đơn) và domain nào lấy giá trị hiện tại. [S50]
10. **Bộ canonical của chúng ta phải rộng hơn Shopify.** Shopify dựa vào dữ kiện cấu trúc (company, POS, attribution handle). Sapo/MISA/Shopee không có những dữ kiện này, nên nhiều domain mà Shopify *không cần* chuẩn hoá (loại khách chi tiết, mục đích đơn, mục đích discount) lại là canonical bắt buộc ở phía chúng ta.

---

## 8. Ánh xạ sang mô hình của chúng ta

Mô hình của chúng ta gồm: **feature** (dữ kiện sản phẩm định nghĩa sẵn, lấy từ nguồn) → **rule form** (dạng luật) → **tenant label** (nhãn của doanh nghiệp) → **canonical value** (giá trị chuẩn bắt buộc).

| Khái niệm Shopify | Feature (đầu vào) | Rule form | Tenant label | Canonical value | Ghi chú |
|---|---|---|---|---|---|
| Product `category` + `productType` | Tên SP, `productType`, `vendor`, tags | Direct mapping (type → category) + pattern có ưu tiên (tên SP) | `productType` | Node category (có thể dùng nguyên taxonomy Shopify, MIT) | Nên cân nhắc dùng taxonomy Shopify làm canonical cho danh mục sản phẩm, chỉ lấy tới tầng 1–2 (218 node tầng 1) để báo cáo |
| Smart collection rule | `TAG`, `TYPE`, `VENDOR`, price, metafield | Điều kiện `column/relation/condition`; `…_WITH_DESCENDANTS` = luật phân cấp | Tên collection | Không có (collection là nhãn tenant) | Mẫu tốt cho schema của bảng luật "pattern" |
| `sourceName` + attribution definition | `source_name` (Sapo), mã kênh MISA, shop Shopee | Direct mapping theo handle | `displayName` | `sales_channel` canonical (vd. `ONLINE_STORE`, `POS`, `MARKETPLACE`, `SOCIAL`, `B2B_DIRECT`...) | Thiếu khớp → `UNMAPPED` (tương tự fallback của Shopify) |
| `is_pos_sale`, `retailLocation` | ID chi nhánh hoặc kho | Direct mapping | Tên chi nhánh | Cờ `is_offline_sale` | |
| `MarketingTactic`, `marketing_channel`, `traffic_type` | UTM, referrer | Pattern có ưu tiên | Giá trị UTM | Tập kênh marketing canonical (13 giá trị của `MarketingTactic` là tham khảo tốt) | Sapo/Shopee ít dữ liệu UTM; ưu tiên thấp |
| `PurchasingCompany` / `is_b2b_order` | Nhóm khách Sapo, mã kênh MISA, tag | Pattern + threshold (vd. số lượng mỗi đơn) + manual override | `ĐẠI LÝ CẤP 1`, `CTV`… | `customer_type` canonical; tối thiểu phải tách được B2B và B2C | Shopify có sẵn dữ kiện cấu trúc, chúng ta phải suy luận |
| `rfmGroup` | recency, frequency, monetary | Threshold (phân vị theo tenant) + decision table R×F×M | Tên nhóm tiếng Việt của tenant | 11 nhóm RFM (có thể dùng nguyên tập của Shopify) | Ngưỡng tương đối theo tenant là mặc định hợp lý; cách chấm của Shopify chưa xác minh |
| `predictedSpendTier` | Lịch sử mua | Model hoặc threshold | | `HIGH/MEDIUM/LOW` | Chỉ tham khảo; có điều kiện tối thiểu > 100 lượt bán |
| `new_or_returning_customer`, `months_since_first_purchase` | Ngày đơn đầu | Luật tính (cố định trong sản phẩm) | | `NEW/RETURNING` | Canonical thuần, không cần luật tenant |
| Customer tags / segment | Tag và các thuộc tính ở 3.3 | Biểu thức boolean (segment) | Tên segment | Không bắt buộc canonical | Segment = nhãn *nhiều-nhiều*, khác với domain *loại trừ* |
| Financial / fulfillment / cancel enum | Trạng thái gốc của nguồn | Direct mapping theo nguồn (thuộc connector, không phải tenant) | Trạng thái gốc | Enum Shopify (8 / 8 / 6 giá trị) là bộ tham chiếu tốt | Mapping do sản phẩm sở hữu, không phải tenant |
| `DiscountClass`, `discount_method` | Loại khuyến mãi của nguồn | Direct mapping (connector) | | `PRODUCT/ORDER/SHIPPING` × `CODE/AUTOMATIC/MANUAL` | Trục cơ chế |
| Mục đích discount (không có ở Shopify) | Tên CTKM, ghi chú, mã | Pattern có ưu tiên + manual override | Tên CTKM | `discount_purpose` canonical do chúng ta định nghĩa | 10 loại của Fine Japan là đầu vào |
| `test` + metafield `is_gift_order` | Tag đơn, ghi chú, nhân viên tạo đơn, khách | Pattern + kết hợp (luật cross-domain) + override | Tag gốc | `order_purpose` canonical (`SALE/GIFT/SAMPLE/STAFF/TEST/INTERNAL`...) do chúng ta định nghĩa | Shopify chỉ chuẩn hoá `test` |
| Metafield `analyticsQueryable` | Trường riêng của tenant | Khai báo definition | Giá trị tự do | Không có (dimension bổ sung) | Mẫu cho "tenant extension dimension" trong mart, nằm ngoài canonical |
| `*_at_time_of_sale` | Thuộc tính tại thời điểm giao dịch | | | | Quyết định point-in-time cho từng domain |
| Taxonomy integration mapping | Category gốc của sàn (Shopee) | Direct mapping có version, from/to | Category sàn | Category canonical | Mapping Shopee → canonical đặt ở tầng sản phẩm, dùng chung cho mọi tenant |

**Khuyến nghị xếp hạng cho Đợt 4 (rút từ Shopify):**

1. **Áp dụng ngay:** cặp cột `label` + canonical cho mọi domain; giá trị `UNMAPPED` chính thức; seed có `code` bất biến tách khỏi `label`; chỉ deprecate, không xoá. Chi phí thấp, mỗi điểm đều có tiền lệ rõ ở Shopify.
2. **Áp dụng khi thiết kế bảng luật:** schema luật dạng `(domain, feature, operator, value, priority, output_code)`, lấy cảm hứng từ `CollectionRule` và thêm `priority` (Shopify không có). Decision table cho RFM. Override thủ công là một luật có priority cao nhất.
3. **Cân nhắc:** dùng Shopify Product Taxonomy (MIT) làm canonical cho danh mục sản phẩm thay vì tự dựng. Ưu điểm: có sẵn mapping sang Google và version theo quý. Rủi ro: cây rất lớn (~14.600 node), không có bản dịch tiếng Việt (chưa kiểm), nhiều nhánh không liên quan tới bán lẻ Việt Nam. Nên lấy tới tầng 1–2 và giữ nguyên ID (`hb-1`...).
4. **Không áp dụng:** segment nhiều-nhiều thay cho domain loại trừ. Report chuẩn của chúng ta cần mỗi bản ghi đúng một nhãn.

---

## Giới hạn của nghiên cứu này

- Không có store Shopify thật để chạy thử. Toàn bộ thông tin lấy từ tài liệu và repo, chưa kiểm chứng hành vi thực tế (vd. giá trị `source_name` thật của từng kênh).
- Help center chặn tải tự động một số trang (403). Các trang về báo cáo bán hàng trong help center chưa đọc trực tiếp; định nghĩa metric lấy từ schema ShopifyQL trên shopify.dev, vốn là nguồn chính thức hơn.
- Chưa đọc schema `customers` của ShopifyQL và chưa đọc chi tiết Markets (một trục phân khúc khác: theo địa lý hoặc nhóm khách).
- Số đếm taxonomy lấy từ nhánh `main` (unstable), không phải bản stable `v2026-08`.

## Câu hỏi còn mở

1. Danh sách `source_name` "protected" hiện hành và giá trị mặc định khi app không truyền `sourceName`: tài liệu hiện tại không nói rõ (mục 2.1).
2. Namespace thật của category metafields (`shopify.<attr>` hay khác) và vai trò của `MetafieldDefinition.constraints` (mục 1.4).
3. Thuật toán RFM của Shopify (cách chấm điểm, chu kỳ làm mới): không có trong tài liệu chính thức (mục 3.2).
4. Taxonomy có localization tiếng Việt hay không: chưa kiểm tra thư mục `data/localizations/categories`.

## Nguồn (truy cập 2026-10-14)

Độ tin cậy: **A** = tài liệu chính thức hoặc repo Shopify; **B** = help center Shopify; **C** = cộng đồng hoặc bên thứ ba.

- [S1] A: Shopify/product-taxonomy README — https://github.com/Shopify/product-taxonomy
- [S2] A: `data/categories/*.yml` — https://github.com/Shopify/product-taxonomy/tree/main/data/categories
- [S3] A: `data/attributes.yml`, `data/values.yml` — https://github.com/Shopify/product-taxonomy/tree/main/data
- [S4] A: Integrations README và `integrations.yml` — https://github.com/Shopify/product-taxonomy/blob/main/data/integrations/README.md
- [S5] A: CHANGELOG — https://github.com/Shopify/product-taxonomy/blob/main/CHANGELOG.md
- [S6] A: Releases — https://github.com/Shopify/product-taxonomy/releases
- [S7] B: Shopify's product taxonomy (help) — https://help.shopify.com/en/manual/products/details/product-category
- [S8] A: `TaxonomyCategory` — https://shopify.dev/docs/api/admin-graphql/latest/objects/TaxonomyCategory
- [S9] A: `Product` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Product
- [S10] A: Metafield-linked product options — https://shopify.dev/docs/apps/build/product-merchandising/products-and-collections/metafield-linked
- [S11] A: `Order` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Order
- [S12] A: `orders` query (filters) — https://shopify.dev/docs/api/admin-graphql/latest/queries/orders
- [S13] A: `OrderCreateOrderInput` — https://shopify.dev/docs/api/admin-graphql/latest/input-objects/OrderCreateOrderInput
- [S14] A: Order attribution guide — https://shopify.dev/docs/apps/build/sales-channels/order-attribution
- [S15] A: `Channel` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Channel
- [S16] A: `CustomerJourneySummary` — https://shopify.dev/docs/api/admin-graphql/latest/objects/CustomerJourneySummary
- [S17] A: `CustomerVisit` — https://shopify.dev/docs/api/admin-graphql/latest/objects/CustomerVisit
- [S18] A: `MarketingTactic` — https://shopify.dev/docs/api/admin-graphql/latest/enums/MarketingTactic
- [S19] A: `UTMParameters` — https://shopify.dev/docs/api/admin-graphql/latest/objects/UTMParameters
- [S20] A: `Customer` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Customer
- [S21] A: `CustomerStatistics` — https://shopify.dev/docs/api/admin-graphql/latest/objects/CustomerStatistics
- [S22] A: `CustomerRfmGroup` — https://shopify.dev/docs/api/admin-graphql/latest/enums/CustomerRfmGroup
- [S23] A: `CustomerPredictedSpendTier` — https://shopify.dev/docs/api/admin-graphql/latest/enums/CustomerPredictedSpendTier
- [S24] A: `CustomerState` — https://shopify.dev/docs/api/admin-graphql/latest/enums/CustomerState
- [S25] A: Segment query language reference — https://shopify.dev/docs/api/shopifyql/segment-query-language-reference
- [S26] B: Predicted spend tier — https://help.shopify.com/en/manual/customers/customer-segmentation/predicted-spend-tier
- [S27] B: Customer tags — https://help.shopify.com/en/manual/customers/manage-customers/customer-tags
- [S28] A: `Segment` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Segment
- [S29] A: `Company` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Company
- [S30] A: `CompanyLocation` — https://shopify.dev/docs/api/admin-graphql/latest/objects/CompanyLocation
- [S31] A: `Catalog` interface — https://shopify.dev/docs/api/admin-graphql/latest/interfaces/Catalog
- [S32] A: `CatalogType` — https://shopify.dev/docs/api/admin-graphql/latest/enums/CatalogType
- [S33] A: `PriceList` — https://shopify.dev/docs/api/admin-graphql/latest/objects/PriceList
- [S34] A: `PurchasingEntity` — https://shopify.dev/docs/api/admin-graphql/latest/unions/PurchasingEntity
- [S35] B: B2B overview — https://help.shopify.com/en/manual/b2b
- [S36] B: B2B catalogs — https://help.shopify.com/en/manual/b2b/catalogs
- [S37] A: `OrderDisplayFinancialStatus` — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderDisplayFinancialStatus
- [S38] A: `OrderDisplayFulfillmentStatus` — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderDisplayFulfillmentStatus
- [S39] A: `OrderCancelReason` — https://shopify.dev/docs/api/admin-graphql/latest/enums/OrderCancelReason
- [S40] A: `DraftOrder` — https://shopify.dev/docs/api/admin-graphql/latest/objects/DraftOrder
- [S41] A: `DraftOrderStatus` — https://shopify.dev/docs/api/admin-graphql/latest/enums/DraftOrderStatus
- [S42] A: `DiscountClass` — https://shopify.dev/docs/api/admin-graphql/latest/enums/DiscountClass
- [S43] A: `DiscountApplicationAllocationMethod` — https://shopify.dev/docs/api/admin-graphql/latest/enums/DiscountApplicationAllocationMethod
- [S44] A: `DiscountApplicationTargetSelection` — https://shopify.dev/docs/api/admin-graphql/latest/enums/DiscountApplicationTargetSelection
- [S45] A: `DiscountApplicationTargetType` — https://shopify.dev/docs/api/admin-graphql/latest/enums/DiscountApplicationTargetType
- [S46] A: `Discount` union và `DiscountStatus` — https://shopify.dev/docs/api/admin-graphql/latest/unions/Discount , https://shopify.dev/docs/api/admin-graphql/latest/enums/DiscountStatus
- [S47] A: REST Order (legacy) — https://shopify.dev/docs/api/admin-rest/latest/resources/order
- [S48] A: ShopifyQL overview — https://shopify.dev/docs/api/shopifyql
- [S49] A: ShopifyQL schemas — https://shopify.dev/docs/api/shopifyql/2026-10/schemas
- [S50] A: ShopifyQL `sales` schema — https://shopify.dev/docs/api/shopifyql/latest/schemas/sales_revenue/sales
- [S51] A: Custom data overview — https://shopify.dev/docs/apps/build/custom-data
- [S52] A: Custom data ownership — https://shopify.dev/docs/apps/build/custom-data/ownership
- [S53] A: List of standard metafield definitions — https://shopify.dev/docs/apps/build/custom-data/metafields/list-of-standard-definitions
- [S54] A: `MetafieldDefinition` — https://shopify.dev/docs/api/admin-graphql/latest/objects/MetafieldDefinition
- [S55] A: `MetafieldCapabilities` — https://shopify.dev/docs/api/admin-graphql/latest/objects/MetafieldCapabilities
- [S56] A: `MetafieldDefinitionConstraints` — https://shopify.dev/docs/api/admin-graphql/latest/objects/MetafieldDefinitionConstraints
- [S57] A: `MetafieldOwnerType` — https://shopify.dev/docs/api/admin-graphql/latest/enums/MetafieldOwnerType
- [S58] A: `StandardMetafieldDefinitionTemplate` — https://shopify.dev/docs/api/admin-graphql/latest/objects/StandardMetafieldDefinitionTemplate
- [S59] A: `CollectionRuleColumn` — https://shopify.dev/docs/api/admin-graphql/latest/enums/CollectionRuleColumn
- [S60] A: `CollectionRuleRelation` — https://shopify.dev/docs/api/admin-graphql/latest/enums/CollectionRuleRelation
- [S61] A: `tagsAdd` — https://shopify.dev/docs/api/admin-graphql/latest/mutations/tagsAdd
- [S62] C: Community, `source_name` cho headless orders — https://community.shopify.dev/t/orders-create-source-name-value-for-headless-storefront-orders/20588 ; https://community.shopify.com/t/list-of-enumerated-shopify-gateways-and-or-order-sources/169684
- [S63] C: Klaviyo, phân biệt dữ liệu POS và Web — https://help.klaviyo.com/hc/en-us/articles/115005253248
- [S64] A: `Location` — https://shopify.dev/docs/api/admin-graphql/latest/objects/Location
- [S65] C: Thảo luận cộng đồng về category metafields — https://community.shopify.com/t/graphql-support-for-product-category-attributes-metafields/339771
- [S66] C: Hướng dẫn RFM bên thứ ba — https://fullmetrix.com/en/guides/segmentation-rfm-shopify
