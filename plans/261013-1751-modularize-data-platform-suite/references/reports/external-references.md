# Tham khảo bên ngoài: danh mục report chuẩn theo persona và "report factory"

> Đầu vào cho Đợt 7 (report chuẩn theo persona) trong [roadmap](../../roadmap.md). Chỉ là tài liệu tham khảo, chưa phải quyết định thiết kế.
> Nghiên cứu ngày 2026-10-14 (Asia/Saigon). Mọi nguồn truy cập ngày 2026-10-14, trừ khi ghi khác.
> Độ tin cậy: **[A]** tài liệu chính thức của nhà cung cấp (help center, developer docs, repo chính chủ). **[B]** trang marketing/changelog của chính hãng, sách, báo lớn. **[C]** bên thứ ba (blog, review, bài tổng hợp). **(chưa xác minh)** là điểm không kiểm được bằng nguồn [A].

## TL;DR

1. **Mọi nền tảng đều chia report theo câu hỏi nghiệp vụ, không theo persona.** Shopify có 11 nhóm (Sales, Orders, Customers, Finance, Profit, Inventory, Acquisition, Behavior, Marketing, Retail sales, Fraud) [S1]. Daasity chia theo mục tiêu (Omnichannel, Ecommerce Performance, Acquisition Marketing, Retention Marketing) [S26]. Persona chỉ xuất hiện ở lớp **mẫu dashboard theo vai trò** (Haravan "Bảng phân tích" gợi ý mẫu theo vai trò/bộ phận [S34]) hoặc ở trang chủ (Daasity Company Overview là trang chủ cho lãnh đạo [S27]). **Bài học:** catalog nên có hai lớp, (a) report theo câu hỏi, gắn tag persona, (b) "trang chủ persona" ghép từ các thẻ KPI của report.
2. **Định nghĩa doanh thu khác nhau giữa các hãng, và hãng Việt cho chủ shop tự cấu hình.** Shopify cố định: Net sales = Gross sales − Discounts − Sales reversals, không gồm ship và thuế [S2][S3]. Pancake cho shop chọn "tính chốt đơn khi", "doanh thu cộng vào thời điểm", "tính đơn hoàn khi", "doanh thu trừ vào thời điểm" [S40]. Haravan có hai trục thời gian: theo ngày tạo đơn và theo ngày phát sinh giao dịch [S37]. **Hệ quả:** các thông số ghi nhận doanh thu (mốc thời gian, trạng thái đơn được tính) phải là **tham số tenant có giá trị mặc định chuẩn**, không hard-code trong SQL.
3. **"Doanh số" và "Doanh thu" là hai khái niệm khác nhau ở thị trường Việt.** Pancake định nghĩa Doanh số = tiền hàng + phí ship thu khách + phụ thu + sàn trợ giá; Doanh thu = Doanh số − chiết khấu − phí sàn − chiết khấu CTV [S41]. Bảng chú giải của chúng ta phải ghi rõ cặp từ Việt ↔ Anh (gross/net) để chủ shop không đối chiếu sai với Sapo/Pancake.
4. **Chuỗi lợi nhuận chuẩn của SaaS lợi nhuận là CM1 → CM2 → CM3.** Triple Whale tính Net Profit = Sales − Blended Ad Spend − (COGS, ship, xử lý, phí cổng thanh toán, thuế, chi phí tuỳ chỉnh) (chưa xác minh trực tiếp: trang KB trả 404, chỉ có trích đoạn qua công cụ tìm kiếm) [S17]. Lifetimely lấy contribution margin và hoàn vốn CAC theo cohort làm đầu ra chính [S21][S22]. **MER bị định nghĩa ngược nhau:** Triple Whale lấy spend/revenue, đa số công cụ khác lấy revenue/spend [S15][S18]. Chúng ta phải chốt một chiều và ghi rõ trong định nghĩa.
5. **Mở khoá theo dữ liệu nên dựa trên tập "capability", không theo bậc tuyến tính.** Thực tế một shop có thể có dữ liệu quảng cáo mà chưa có giá vốn. Shopify ẩn các chỉ số chi tiêu khi kênh không gửi dữ liệu chi phí (hiển thị "-", không phải 0) [S8]. Shopify chỉ tính lợi nhuận cho dòng hàng "có cost lúc bán" [S5]. Bậc (tier) chỉ dùng để trình bày. Điều kiện bật report là `requires: [capability...]`, khớp với "khai báo connector cung cấp gì" đã ghi trong roadmap.
6. **Cá nhân hoá report: mẫu chuẩn khoá cứng, khách tuỳ biến bằng lớp phủ.** Shopify: default report "Save as" thành custom report [S12]. Daasity: hub LookML do Daasity quản lý, khách sửa bằng refinement ở spoke, nên bản nâng cấp không đè lên tuỳ biến của khách [S28]. Rill: derived metrics view kế thừa và chỉ được ẩn hoặc thêm row filter, không được đổi định nghĩa gốc [S58]. **Đây là mẫu nên chép:** base catalog bất biến cộng tenant overlay khai báo (đổi nhãn, ẩn, ngưỡng, report thêm).
7. **Semantic layer: chưa nên thêm service mới.** Mỗi khách SME có một bản cài on-prem riêng, nên lợi thế đa tenant của Cube không có giá trị. Metabase OSS không có serialization (chỉ Pro/Enterprise) [S56], còn metric của Metabase không dùng được trong SQL [S55]. Evidence bản mới (Core/Studio) có metric YAML nhưng self-host bắt buộc dùng direct connector, và danh sách connector **không có DuckDB file cục bộ** (chỉ có MotherDuck) [S61][S63][S64]. **Khuyến nghị:** registry metric + report bằng YAML trong repo (nguồn sự thật) → tính sẵn trong dbt mart → sinh ra Metabase/Evidence/Rill bằng generator đã có.

**Xếp hạng khuyến nghị (chi tiết mục 6.4):** (1) registry YAML tự quản lý + mart dbt + generator theo engine; (2) giữ Rill metrics view làm đích sinh cho phân tích tự do; (3) để MetricFlow làm phương án nâng cấp (Apache 2.0, có extra `dbt-duckdb`), viết registry gần schema của nó; (4) không chọn Cube, Lightdash hay metric native của Metabase làm nguồn sự thật.

---

## 1. Shopify Analytics

### 1.1 Danh mục report mặc định (11 nhóm) [S1]

| Nhóm | Report mặc định (tên gốc) | Nguồn |
|---|---|---|
| Sales | Total sales over time; by product; by product variant; by vendor; Sales by discount codes; Total sales by referrer; by billing location; by currency; Sales by sales channel; Sales by customer name; Average order value over time; nhóm Bundle (4 report); nhóm Subscriptions (5 report) | [S2] |
| Orders | Orders and reversals by product; Orders over time; Shipping and delivery performance; Orders fulfilled over time; Shipping labels over time / by order; Items bought together | [S10] |
| Customers | New customers over time; New vs returning; Customers by location; Returning customers; One-time customers; Customer cohort analysis; Predicted spend tier; RFM customer analysis (11 nhóm); RFM customer list | [S4] |
| Finance | Finance Summary (thẻ sales, gross profit, payments, gift cards, tips); Total sales breakdown; Taxes; Payments (net payments theo phương thức, theo thời gian, theo cổng, theo đơn); Store credit; Gift cards; Tips | [S3] |
| Profit | Average profit margin by market; Profit margin by order; Gross profit by product / variant / POS location | [S5] |
| Inventory | Month-end inventory snapshot / value; Inventory sold daily by product; Products by percentage sold; ABC product analysis; Products by sell-through rate; Inventory remaining per product; Inventory adjustment changes / by count | [S6] |
| Acquisition | Sessions by referrer; by location; Sessions over time; Visitors over time | [S7] |
| Behavior | Conversion rate breakdown; Funnel visualization; Conversion rate over time; Web performance; Product recommendation (2 report); Searches (4 report); Sessions by landing page; by device | [S9] |
| Marketing | Performance by marketing channel; by marketing campaign; Sales attributed to marketing; Sessions attributed to marketing campaigns; Conversion by attribution model | [S8] |
| Retail sales (POS) | POS total sales by product / variant / vendor / product type; by POS location; by staff member; POS staff daily sales total; staff sales total | [S11] |
| Fraud | (không đọc chi tiết, ngoài phạm vi) | [S1] |

### 1.2 Định nghĩa metric chuẩn của Shopify [A]

| Metric | Định nghĩa Shopify | Nguồn |
|---|---|---|
| Gross sales | Giá sản phẩm × số lượng, trước thuế, ship, giảm giá và sales reversal. **Có tính** đơn pending, cancelled, unpaid; không tính đơn test và đơn đã xoá | [S2][S3] |
| Discounts | Giảm giá dòng hàng cộng phần giảm giá cấp đơn được phân bổ theo tỉ lệ; ghi âm | [S2][S3] |
| Sales reversals | Mọi điều chỉnh làm giảm tiền: hàng trả, huỷ, sửa đơn, điều chỉnh ship/thuế/phí/giảm giá. Thuật ngữ "Returns" đã bị thay | [S2] |
| Net sales | Gross sales − Discounts − Sales reversals; không gồm ship và thuế | [S3] |
| Total sales | Gross − discounts − reversals + taxes + shipping + fees; có thể âm | [S3] |
| Net payments | Tiền đã thu − tiền đã hoàn (trục **thanh toán**, khác trục bán hàng) | [S3] |
| AOV | (Gross sales − discounts, đều không tính điều chỉnh) / số đơn | [S2] |
| Units per transaction | Net quantity / total orders | [S2] |
| Gross profit / margin | Net sales − cost; margin = (net sales − cost)/net sales. Chỉ tính dòng hàng **có cost lúc bán** | [S5] |
| Sell-through rate | Đã bán / (đã bán + còn tồn), cửa sổ 30 ngày, trễ khoảng 2 ngày | [S6] |
| Days of inventory remaining | Tồn cuối / bình quân bán mỗi ngày trong 28 ngày | [S6] |
| ABC | A = nhóm tạo 80% doanh thu 28 ngày, B = 15% tiếp theo, C = 5% còn lại; không xét giá vốn | [S6] |
| RFM | Mỗi trục chấm 1–5 **tương đối theo dữ liệu của shop**; 11 nhóm dựa trên điểm R và trung bình F, M | [S4] |
| Cohort | Nhóm khách theo kỳ đơn đầu tiên | [S4] |
| Session | Hết sau 30 phút không hoạt động | [S7] |
| Attribution mặc định | Last non-direct click; người dùng đổi được model. Kênh không gửi chi phí thì cột spend hiện "-" | [S8] |

### 1.3 Cách merchant tuỳ biến

- **Exploration:** Analytics > Reports > New exploration, cần ít nhất 1 metric. Dựng bằng ShopifyQL editor, bằng panel cấu hình, hoặc nhờ Sidekick sinh query từ câu mô tả. Mở default report, sửa, "Save as" thì thành custom report. Có trên mọi gói [S12].
- **Dashboard:** mỗi thẻ là một metric. Custom report tạo ra một thẻ metric tương ứng trong thư viện dashboard [S12][S14].
- **ShopifyQL:** `FROM` (schema: sales, orders, customers, marketing, inventory, payments) `SHOW` metric `GROUP BY` dimension `WHERE` `DURING/SINCE/UNTIL` `TIMESERIES` `COMPARE TO previous_period` `VISUALIZE`. Truy cập qua editor trong admin, GraphQL `shopifyqlQuery`, Python SDK/CLI, hoặc web component thẻ metric [S13].
- Analytics mới là mặc định cho mọi shop từ 11/06/2025 [S14] [B].

**Bài học cho chúng ta:**
- Một metric có tên và công thức cố định, các report chỉ là các cách ghép metric × dimension × bộ lọc. Đây chính là mô hình "report = cấu hình trên metric registry".
- Shopify tách trục **bán hàng** (sales, theo ngày ghi nhận) khỏi trục **thanh toán** (payments). Chúng ta cần tương tự: doanh thu theo đơn khác với tiền về (COD, settlement của sàn).
- Shopify tính gross sales cả đơn huỷ rồi trừ qua reversal, tức là kế toán kiểu "ghi nhận rồi đảo". Shop Việt quen loại đơn huỷ ra ngay (Pancake: "tính chốt đơn khi"). Phải chọn một và ghi rõ.

---

## 2. SaaS phân tích e-commerce

### 2.1 So sánh

| Công cụ | Trọng tâm | Report/dashboard chuẩn | Catalog metric | Cách tuỳ biến theo merchant | Nguồn |
|---|---|---|---|---|---|
| **Triple Whale** | Attribution + lợi nhuận quảng cáo cho DTC | Summary page (các khối Store, Ads, Profit), Pixel/attribution dashboard | Blended ROAS = Order revenue / (ad spend + custom ad spend); NC-ROAS = doanh thu khách mới / blended ad spend; MER = **spend / revenue** (nghịch đảo ROAS) | Custom spend (nhập tay chi phí và cờ `is_ad_spend`), custom metric | [S15][S16][S17] |
| **Polar Analytics** | BI e-commerce + semantic layer | Dashboard dựng sẵn: Acquisition (CAC, ROAS blended), Merchandising, Retention & LTV (cohort); thư viện template theo mục tiêu ("Reduce acquisition cost", "Increase LTV"), theo connector, theo chuyên gia | "Hàng trăm" metric/dimension chuẩn | Custom metric/dimension bằng công thức và if/then; MCP server có `generate_report`, `list_dimensions` | [S19][S20] [B] |
| **Lifetimely (AMP)** | LTV + P&L | LTV Cohort, LTV Drivers, Cohort Breakdown, Predictive LTV, Subscriptions; nhóm P&L | Accumulated sales/customer, gross margin, contribution margin theo cohort; điểm hoàn vốn CAC (khi gross margin cohort vượt CAC) | Prefilter (first order / any order / all orders) | [S21][S22] |
| **BeProfit** | Lợi nhuận theo đơn/sản phẩm | Dashboard 5 khối: profit (gross/net), sales, COGS, shipping & handling, ad spend, fees, refunds, taxes | Net profit gồm ship, giảm giá, marketing, phí sàn | Nhập chi phí cố định, biến đổi và chuyên biệt | [S25] [B]; công thức **(chưa xác minh)** |
| **Peel Insights** | Retention, cohort | Template dựng sẵn ("dozens"), Magic Dash do AI sinh | 150+ metric; trang công khai liệt kê 81 metric trong 12 nhóm: Profit, Revenue, Customers, Subscriptions, Purchases, Cohorts Retention, Cohorts Revenue, Marketing, Orders, Cost, Subscription Activations, Subscription Cohorts | Chọn metric, lọc, phân đoạn | [S23] |
| **Glew** | BI đa nguồn cho SMB/mid-market | Dashboard dựng sẵn cho KPI, kênh marketing, khách, sản phẩm, đơn, tồn kho, subscription; 30 segment khách | "250+ KPI" (bên thứ ba) | Report builder, lịch gửi email | [S24] [B/C] |
| **Daasity** | Data platform omnichannel trên Looker | Report Library: Omnichannel/Company Overview; Ecommerce Performance (Flash "6-pack": Traffic, Conversions, Orders, AOV, Gross Sales, Vendor ROAS; Orders & Revenue; Inventory; Operations; Product; Product Repurchase Rate; Site Funnels); Acquisition Marketing (Attribution, LTV & RFM, Marketing); Retention Marketing; Utility (Account Health); Data Source dashboards (Amazon Settlement…) | 7 Unified Schema (Order, Marketing…), Metrics Dictionary | **Hub-and-spoke:** hub LookML do Daasity quản lý, import vào Looker của khách; khách sửa bằng LookML refinement ở spoke; Daasity đẩy bản nâng cấp mà không đè tuỳ biến. Company Overview cho override "custom Revenue metric" | [S26][S27][S28] |

### 2.2 Bài học

1. **Daasity là hình mẫu kiến trúc gần nhất với nhu cầu "report factory".** Định nghĩa gốc nằm ở một chỗ, khách chỉ được *refine*, và có dashboard "Account Health" về chất lượng dữ liệu đi kèm như một report chuẩn. Chúng ta đã có playbook `ingestion_health`, nên đưa nó vào catalog chuẩn.
2. **Company Overview của Daasity dùng nhịp tuần, không phải nhịp ngày.** Trang này chỉ là "bệ phóng" để drill sang report chi tiết, không dùng để chẩn đoán [S27]. Đây là khuôn đúng cho trang CEO.
3. **Bộ "6-pack" (Traffic, Conversions, Orders, AOV, Gross Sales, ROAS)** là ví dụ một tập KPI tối thiểu cho thẻ flash. Shop Việt không có traffic web ổn định (bán qua sàn và mạng xã hội), nên thay bằng Đơn, Doanh thu thuần, AOV, Tỉ lệ huỷ/hoàn, Khách mới, MER.
4. **Custom spend (chi phí nhập tay) là tính năng chuẩn** ở Triple Whale và BeProfit. Shop SME Việt cần đúng việc này cho giá vốn và chi phí chung. Roadmap đã ghi "bảng giá vốn nhập tay".

---

## 3. POS/OMS Việt Nam: report có sẵn

| Hãng | Nhóm report (theo help center) | Điểm đáng chú ý | Nguồn |
|---|---|---|---|
| **Sapo** | Báo cáo bán hàng, công nợ, nhập hàng, tài chính (doanh thu, lãi lỗ), kho hàng, hiệu quả kinh doanh, báo cáo theo biểu đồ. Báo cáo lợi nhuận (cập nhật 10/07/2026): tổng hợp; theo thời gian, đơn, kênh, gian hàng/trang, nguồn đơn, chi nhánh; thêm chi phí sàn, vận chuyển, chi phí khác. Dashboard "Phân tích kinh doanh sàn" (cập nhật 24/03/2025): doanh thu theo kênh/gian hàng, đơn theo trạng thái, top bán chạy và top bị trả, cho thêm/bớt/kéo thả chỉ số | Trước 07/2026 lợi nhuận của Sapo chỉ là doanh thu − giá vốn. Công thức mới **chưa công bố** | [S29][S30][S31] |
| **Haravan** | Bán hàng (theo nhân viên, theo kho xuất, theo thời gian giao, khuyến mãi, hiệu quả khuyến mãi, tổng doanh thu và VAT); Tài chính (công nợ khách/NCC, kết quả kinh doanh, báo cáo tài chính); Tồn kho (xuất nhập tồn theo sản phẩm/thời gian, điều chỉnh, lô hạn dùng, nhập hàng, trả hàng nhập, sắp hết hàng); Khách hàng (mới/cũ, giới tính, nhóm tuổi, RFM, vị trí, chỉ gói Grow/Scale); Giao hàng (tốc độ xử lý vận đơn, đóng gói, tình trạng giao, tốc độ nhà vận chuyển theo khu vực); Sàn TMĐT; Website; POS cuối ngày/ca | "Bảng phân tích": tối đa 5 bảng/người, **gợi ý mẫu theo vai trò và bộ phận**, mỗi bảng chỉ hiện với người tạo. Danh sách tối đa 300 report (gồm bản nhân bản). Có hai trục: "dòng tiền bán hàng" (theo ngày tạo đơn) và "theo ngày giao dịch". RFM chấm 1–5 với ngưỡng shop tự chỉnh. Report sàn có công thức rõ (bên dưới) | [S32]–[S37] |
| **KiotViet** | Cuối ngày (lọc theo phương thức thanh toán); Bán hàng; Hàng hoá (mối quan tâm: bán hàng, lợi nhuận, giá trị kho, xuất nhập tồn, hạn sử dụng); Khách hàng (bán theo khách, công nợ); Nhà cung cấp (nhập theo NCC, công nợ, VAT đầu vào); Kênh bán hàng; Tài chính (dạng kết quả kinh doanh: doanh thu, giá vốn, chi phí như voucher, lương, điểm thưởng) | Mẫu "một report, nhiều *mối quan tâm*" giúp giảm số report | [S38] |
| **Nhanh.vn** | Tổng quan; Doanh thu (theo thời gian, nhân viên, sản phẩm, khách hàng); Đơn hàng (tăng trưởng, kênh bán, đơn tạo, đơn thành công, theo trạng thái, theo thời gian xử lý, theo nhân viên xử lý, theo hãng vận chuyển); Bán lẻ (tổng quan, theo nhân viên có kiểm kê tiền mặt, theo cửa hàng); Tồn kho (XNT theo sản phẩm, tổng XNK); Sản phẩm (bán chạy, tốc độ bán); Kế toán (KQHĐKD, bảng cân đối kế toán, sổ kế toán); Khách hàng (tổng quan, chu kỳ mua hàng, tỉ lệ khách hàng); Khuyến mại (affiliate) | Có cả báo cáo kế toán chuẩn (B02, bảng cân đối) và báo cáo hoá đơn điện tử | [S39] |
| **Pancake POS** | Thống kê mặc định: Doanh thu, Đơn hàng, Doanh số, Vận chuyển (theo tỉnh thành: tỉ lệ thành công/huỷ/hoàn; theo đơn vị vận chuyển), Khách hàng (khách mới, chi tiêu theo cấp độ, **chu kỳ mua và khách có nguy cơ rời bỏ**), Nhập hàng. Thống kê tuỳ chỉnh: tạo danh mục, sửa từ view mặc định, hoặc lưu cấu hình thành report mới. Tài chính: đối soát, thu chi, công nợ | **Có bảng chú giải công thức đầy đủ nhất trong các hãng Việt**, gồm phí sàn chi tiết, COD đối soát, tỉ lệ chốt, tỉ lệ phát | [S40][S41][S42] |

### 3.1 Công thức đáng chép (nguồn [A])

**Pancake [S41]:**
- Doanh số = Tiền hàng + Tiền VC thu của khách + Phụ thu + Sàn trợ giá + Chênh lệch phí VC (sàn).
- Doanh thu = Doanh số − Chiết khấu − Phí sàn − Chiết khấu CTV.
- Doanh thu bán hàng = Tiền hàng − Chiết khấu + Sàn trợ giá.
- Lợi nhuận = Doanh thu − Phí trả hãng VC − Giá vốn − Chi phí quảng cáo.
- "Lợi nhuận ròng" = Doanh thu − Phí trả hãng VC − Giá vốn. Bảng ghi đây là "lợi nhuận bao gồm chi phí quảng cáo", nhưng công thức lại không trừ quảng cáo. **Nhãn có vẻ bị đảo, đây là dẫn chứng rằng tên gọi lợi nhuận ở thị trường Việt không thống nhất.**
- Tỉ lệ chốt = Đơn chốt / (Đơn tạo mới − Đơn xoá); Tỉ lệ hoàn = Đơn hoàn / Đơn chốt; Tỉ lệ phát = Đơn giao thành công / Đơn đã gửi.
- GTTB (AOV) = Doanh thu không trừ hoàn / Đơn chốt; Tỉ lệ khách quay lại = SL khách cũ / SL khách chốt; Chi phí QC/Doanh thu.
- Thực nhận ĐVVC = COD đối soát − Tổng phí đối soát.

**Haravan, report kênh sàn [S36]:**
- Doanh thu = SL × giá bán.
- Doanh thu thuần = Doanh thu − Giảm giá sản phẩm − Giảm giá của shop.
- Lợi nhuận = Doanh thu thuần − Giá vốn; % LN = LN / Doanh thu (chia cho doanh thu, không phải doanh thu thuần).
- Khấu trừ khác = Doanh thu thuần − Thực nhận − Phí VC shop trả − Phí nền tảng − Phí thanh toán − Phí dịch vụ.

### 3.2 Bài học

1. **Report "đặc sản" Việt mà Shopify không có (hoặc ít dùng):** báo cáo cuối ngày/chốt ca, có kiểm kê tiền mặt; doanh thu và **hoa hồng theo nhân viên**; công nợ khách và NCC; xuất nhập tồn; đối soát COD với hãng vận chuyển; tỉ lệ giao thành công/hoàn theo tỉnh và theo hãng vận chuyển; chu kỳ mua lại. Catalog chuẩn phải có các report này thì chủ shop Việt mới thấy "đủ".
2. **Ai ghi nhận doanh thu, khi nào, ở trạng thái nào là cấu hình của từng shop** (Pancake, Haravan). Catalog phải công bố "quy tắc ghi nhận mặc định" và cho tenant đổi bằng tham số. Báo cáo nào cũng ghi chú đang dùng trục thời gian nào.
3. **Nhân viên là một chiều hạng nhất** (Nhanh, Pancake, KiotViet, Haravan, Shopify POS). Persona "trưởng nhóm sales" là có thật ở thị trường này.
4. **Template theo vai trò đã có ở Haravan.** Đối thủ đã làm, nên điểm khác biệt của chúng ta phải là số liệu **xuyên nguồn** (POS + sàn + MISA + quảng cáo), không chỉ là có template.

---

## 4. Trung Quốc: 生意参谋, 京东商智, 抖音电商罗盘

| Công cụ | Cấu trúc chuẩn người bán nhận được | Độ tin cậy |
|---|---|---|
| **生意参谋 (Shēngyì Cānmóu, Business Advisor, Alibaba)** | Bản 2016: 首页 (trang chủ, KPI cốt lõi), 实时直播 (dữ liệu thời gian thực, top 50 sản phẩm theo khách truy cập, lượt xem, tiền thanh toán, người mua, tỉ lệ chuyển đổi), 经营分析 (phân tích kinh doanh: 流量 traffic → 商品 sản phẩm → 交易 giao dịch → 营销 marketing), 市场行情 (thị trường ngành), 自助取数 (tự rút số), 专题工具 (công cụ chuyên đề) [S43]. Các bài tổng hợp gần đây nhắc thêm 客户 (khách), 服务 (dịch vụ/hậu mãi), 竞争情报 (tình báo cạnh tranh) [S44]. Các module 作战室 (war room), 品类 (ngành hàng), 物流 (logistics) theo tên trong đề bài **chưa xác minh** được bằng nguồn chính thức | [B] (2016, cũ) / [C] |
| **京东商智 (JD Shangzhi)** | Nằm trong app người bán 京麦. Bên thứ ba mô tả các chiều: bán hàng, chuyển đổi, nguồn traffic, giám sát thị trường, so sánh đối thủ | [C] **(chưa xác minh)** |
| **抖音电商罗盘 (Douyin E-commerce Compass)** | Năm 2022 tách thành 策略版 (bản chiến lược) và 经营版 (bản kinh doanh, có gợi ý chẩn đoán cho live, mall, search) [S45b]. App 抖店 mô tả: chỉ số lõi và xu hướng, chi tiết live, sản phẩm, dịch vụ. Quy ước số liệu theo bên thứ ba: 成交金额 (GMV) là số tiền thực trả, **gồm cả đơn sau đó hoàn/huỷ**, gồm ship, không gồm trợ giá nền tảng; hoàn tiền tính theo ngày hoàn thành công (còn trang quản lý đơn tính theo ngày yêu cầu); 商品卡 (thẻ sản phẩm) = mọi đơn không đến từ live hoặc video ngắn [S45][S46] | [B]/[C] |
| **微信小店 (WeChat Shop), đối chứng có nguồn [A]** | API phân tích dữ liệu: tổng quan (GMV, số người mua, số đơn, tiền hoàn, số người click sản phẩm; tách GMV live và video ngắn); 5 nhóm khách (thấy sản phẩm, click, mua, **mua lần đầu, mua lại**) theo giới tính, tuổi, tỉnh, sức chi; sản phẩm (GMV, tiền đặt hàng, hoàn, hoa hồng, tiền quyết toán thực/dự kiến, **tỉ lệ hoàn trước/sau giao**); KOL (达人) và live. Dữ liệu T+1 | [A] [S47] |

**Bài học:**
1. **Tổ chức theo chuỗi câu hỏi phễu:** traffic → sản phẩm → giao dịch → dịch vụ/hậu mãi → marketing, cộng một màn "thời gian thực". Với SME Việt, phần "thời gian thực" tương ứng với màn "hôm nay" cho chủ shop (đơn, doanh thu, đơn chờ xử lý), cập nhật trong ngày.
2. **Tách theo kênh nội dung (载体: live / video ngắn / thẻ sản phẩm) và theo KOL.** Đây là chiều bắt buộc khi thêm TikTok Shop, khớp với khuyến nghị tách trục kênh trong `../taxonomy/china.md`.
3. **GMV kiểu Trung Quốc gồm cả đơn hoàn/huỷ về sau**, sau đó dùng tỉ lệ hoàn trước/sau giao để điều chỉnh. Nên có cả GMV (đặt) lẫn doanh thu thuần (sau hoàn) và hiển thị song song, giống Douyin và WeChat.
4. **Khách mua lần đầu và mua lại là chiều chuẩn ở mọi metric khách hàng**, không phải một report riêng.

---

## 5. Templating, semantic layer, "metrics as code"

### 5.1 Hiện trạng stack (đọc từ repo ngày 2026-10-14)

- Warehouse là DuckDB với dbt-duckdb; mỗi khách là một bản cài on-prem riêng (single-tenant).
- BI gồm Metabase **0.62.3 bản OSS** (tải từ `downloads.metabase.com`) với driver DuckDB của MotherDuck (`Dockerfile.metabase`); Evidence **legacy** (`@evidence-dev/evidence: "latest"`); Rill v0.87.8 với 3 metrics view (`rill/metrics/*.yaml`).
- Định nghĩa metric bằng văn bản đã có ở `docs/analytics-handbook/semantic/metrics.md` (net_revenue, gross_profit, channel_net_profit, fully_loaded_net_profit, retention_rate…). Blueprint Metabase sinh bằng `deploy_from_markdown.js`.
- Roadmap đã chốt: report template là spec không phụ thuộc engine, kèm bản hiện thực theo từng report ("theo report, không theo engine").

### 5.2 Các lựa chọn

| Lựa chọn | Cách định nghĩa | Hợp DuckDB on-prem? | Đa engine (Metabase + Evidence + Rill)? | Tuỳ biến per-tenant | Rủi ro áp dụng | Nguồn |
|---|---|---|---|---|---|---|
| **A. Registry YAML tự quản lý + dbt mart + generator** | `metrics.yml` và `reports/*.yml` trong repo; giá trị tính sẵn trong mart; generator sinh blueprint Metabase, trang Evidence, metrics view Rill | Có, không thêm service | Có, vì generator do ta viết | Overlay YAML (refinement) | Phải tự bảo trì generator; số giữa các engine có thể lệch nếu engine tự tổng hợp → cần test "golden query" | (thiết kế); mẫu: [S28] |
| **B. dbt Semantic Layer / MetricFlow** | YAML semantic_models + metrics trong dbt | CLI `mf` chạy với dbt-duckdb: repo có extra `dbt-duckdb` [S51]. Trang docs dbt chỉ liệt kê Snowflake, BigQuery, Databricks, Postgres, Redshift [S49] | Không có BI nào trong stack đọc trực tiếp; phải sinh SQL (`mf query --explain`) | Không có cơ chế tenant; ghi đè bằng biến dbt | Apache 2.0 từ v0.209 (trước là AGPL rồi BSL) [S50]; bản v0.213.0 phát hành 10/09/2026, repo hoạt động [S51]. Giấy phép đã đổi 2 lần | [S49]–[S51] |
| **C. Cube Core** | Data model YAML/JS; API SQL qua giao thức Postgres; Metabase và Evidence Core kết nối được | Có driver DuckDB (đường dẫn file) [S53] | Có, qua Postgres wire | Mạnh: `repositoryFactory` cho model theo tenant, `contextToAppId`, `driverFactory` [S52] | Thêm một service Node; giá trị đa tenant là thừa vì mỗi khách một bản cài | [S52][S53] |
| **D. Lightdash** | Metric trong YAML của dbt; `lightdash download/upload` cho chart và dashboard as code [S54] | DuckDB cục bộ **chưa xác minh** (tài liệu chỉ nói MotherDuck) | Không, vì sẽ thay Metabase | Theo project | Phải đổi BI | [S54] |
| **E. Metric native của Metabase** | Metric editor (không viết bằng SQL), gắn với một nguồn | Có | Không | Serialization chỉ có ở **Pro/Enterprise** [S56]; Remote Sync cũng chỉ Pro/Enterprise [S57] | Metric không dùng được trong câu SQL và chỉ chạy trên đúng nguồn đã định nghĩa [S55] | [S55]–[S57] |
| **F. Metrics view của Rill** | YAML (dimensions, measures); **derived metrics view** kế thừa parent, chọn tập con hoặc `exclude`, thêm row filter; không định nghĩa lại measure được [S58] | Có (DuckDB nhúng) | Chỉ Rill | Tốt (derived view) | Đã dùng trong stack. Repo hoạt động [S59] | [S58][S59] |
| **G. Evidence Core/Studio (bản mới)** | `metrics/*.yaml` (base, dimension, metric có `filter`, tham chiếu `{revenue}`), partials, custom component [S62] | **Không rõ.** Self-host bắt buộc dùng direct connector; danh sách gồm Snowflake, Fabric, ClickHouse, BigQuery, Databricks, Postgres, Cube, MotherDuck; **không có DuckDB file** [S63][S64] | Chỉ Evidence | Biến, partials | Phải migrate cú pháp (Svelte → Markdoc) [S61]. Package legacy phát hành bản cuối ngày 06/02/2026 (dấu hiệu bảo trì, **chưa xác minh** là đã ngừng) | [S60]–[S64] |
| **H. Templated pages của Evidence legacy** | `pages/customers/[customer].md` sinh một trang cho mỗi giá trị [S60] | Có (đang dùng) | Chỉ Evidence | Một trang cho mỗi giá trị (vd. mỗi kênh, mỗi cửa hàng) | Hướng phát triển đã chuyển sang Core | [S60] |

### 5.3 Nhận định

- **Ngày nay "metrics as code" gần như đồng nghĩa với YAML, gồm base table + dimensions + measures có filter + metric dẫn xuất tham chiếu metric khác.** Evidence Core, Rill, MetricFlow, Cube và Daasity/LookML đều dùng cùng hình dạng này [S28][S49][S58][S62]. Viết registry của ta theo đúng hình dạng đó thì sau này chuyển sang MetricFlow hoặc Cube sẽ rẻ.
- **Không engine nào trong stack có thể làm nguồn sự thật chung cho cả ba BI.** Metabase OSS không xuất định nghĩa được, Rill và Evidence chỉ dùng nội bộ. Vì vậy nguồn sự thật phải nằm ở repo, mỗi engine là một đích sinh.
- **Tính sẵn trong mart là cách duy nhất bảo đảm số khớp nhau giữa các engine.** Các metric tỉ lệ (AOV, margin %, MER) phải được định nghĩa là tỉ số của tổng, không phải trung bình của tỉ lệ. Registry phải ghi rõ `type: ratio(numerator, denominator)` để generator sinh đúng ở mọi engine. MetricFlow có loại `ratio` và Evidence Core có `{a}/{b}`, cùng một ý tưởng.
- **Dashboards-as-code per tenant:** với Metabase OSS, con đường thực tế là dùng API (đã có `deploy_from_markdown.js`, `capture_dashboard.js`). Serialization và Remote Sync cần bản trả phí [S56][S57].

---

## 6. Tổng hợp: catalog chuẩn và kiến trúc report factory

### 6.1 Capability (điều kiện mở khoá) và bậc trình bày

| Bậc (để trình bày) | Capability cần | Nguồn điển hình |
|---|---|---|
| **T0 Bán hàng** | `orders`, `order_lines`, `customers`, `products`; tuỳ chọn `staff`, `stores`, `inventory_snapshot`, `fulfillment_events` | Sapo, Haravan, Nhanh, Pancake, KiotViet |
| **T1 + Sàn** | `marketplace_settlement` (phí, thực nhận, trợ giá), `return_events` | Shopee, TikTok Shop (sau) |
| **T2 + Giá vốn/lợi nhuận** | `unit_cost` (Sapo giá vốn bình quân, MISA, nhập tay), `shipping_cost`; T2b: `ledger` (MISA) cho chi phí chung và P&L | Sapo, MISA, bảng nhập tay |
| **T3 + Quảng cáo** | `ad_spend` (theo ngày × kênh × chiến dịch), tuỳ chọn `ad_attribution` | Meta, Google, Shopee Ads, TikTok Ads |
| **T4 + CRM/loyalty** | `crm_contacts`, `care_tasks`, `loyalty_points` | Pack CRM/HUG |

Quy tắc: report khai báo `requires` (bắt buộc) và `enhances` (tuỳ chọn). Khi thiếu `enhances` thì ẩn phần liên quan và hiện "-" kèm ghi chú (giống Shopify [S5][S8]); không hiện 0.

### 6.2 Catalog đề xuất (15 report)

Persona: **CEO** (chủ doanh nghiệp), **CFO** (kế toán/tài chính), **MKT** (marketer), **OPS** (vận hành/kho), **SOLO** (cá nhân bán hàng/chủ shop nhỏ), **LEAD** (trưởng nhóm sales).

| # | Report | Persona | requires | Câu hỏi chính | Metric lõi | Tham khảo | Playbook hiện có |
|---|---|---|---|---|---|---|---|
| R01 | Hôm nay của shop | SOLO, CEO | T0 | Hôm nay bán được bao nhiêu, đơn nào cần xử lý? | Đơn, doanh thu thuần, AOV, đơn chờ xử lý, đơn huỷ | 实时直播 [S43], Pancake tổng quan [S40], KiotViet cuối ngày [S38] | `sales_daily_retail`, `sales_daily_operation` (một phần) |
| R02 | Nhịp tuần | CEO | T0 (+T2, T3) | Tuần này so với tuần trước và cùng kỳ năm trước? Kênh nào kéo? | Doanh thu thuần, YoY/WoW, cơ cấu kênh, khách mới, (CM2, MER khi có) | Daasity Company Overview [S27] | `ceo_weekly_pulse` |
| R03 | Scorecard tháng | CEO, CFO | T0 (+T2) | Tháng có đạt mục tiêu không? | Doanh thu thuần, % mục tiêu, gross margin, tỉ lệ hoàn, khách quay lại | Finance Summary [S3] | `ceo_monthly_scorecard` |
| R04 | Bán hàng theo kênh × sản phẩm | CEO, LEAD | T0 | Bán gì, ở đâu? | Gross/net sales, SL, giá bán bình quân, giảm giá | Shopify Sales [S2], Nhanh Doanh thu [S39] | `sales_monthly_review` |
| R05 | Hiệu suất nhân viên và cửa hàng | LEAD, SOLO | T0 + `staff` | Ai bán tốt, hoa hồng bao nhiêu, tiền mặt khớp chưa? | Doanh thu theo nhân viên, đơn, AOV, tỉ lệ chốt, hoa hồng | Shopify POS staff [S11], Nhanh bán lẻ [S39], Pancake [S40] | `sales_ops_weekly_review` (một phần) |
| R06 | Khuyến mãi và mã giảm giá | MKT | T0 | Khuyến mãi có đáng tiền không? | Giảm giá, tỉ lệ giảm giá, doanh thu/đơn có mã, (margin sau giảm giá khi có T2) | Shopify discount codes [S2], Haravan hiệu quả KM [S32] | `sales_promotion_analysis` |
| R07 | Khách mới, quay lại và cohort | CEO, MKT | T0 | Giữ khách tốt không? | Khách mới, tỉ lệ khách quay lại, tỉ lệ mua lại theo cohort, chu kỳ mua | Shopify Customers [S4], Peel [S23], Pancake chu kỳ [S40] | `customer_retention_cohorts` |
| R08 | Tồn kho và tốc độ bán | OPS | T0 + `inventory_snapshot` | Hàng nào sắp hết, hàng nào tồn lâu? | Tồn, days of supply, sell-through, ABC, giá trị tồn (T2) | Shopify Inventory [S6], Haravan sắp hết hàng [S32] | (thiếu playbook riêng; có `mart_product_health`) |
| R09 | Vận hành đơn và giao hàng | OPS | T0 + `fulfillment_events` | Giao có nhanh không, hoàn/huỷ ở đâu? | Thời gian xử lý, tỉ lệ giao thành công, tỉ lệ hoàn/huỷ theo tỉnh và hãng VC | Haravan giao hàng [S32], Pancake vận chuyển [S40] | `logistics_operations`, `logistics_shipping` |
| R10 | Kinh tế kênh sàn | CFO, CEO | T1 | Bán trên sàn còn lại bao nhiêu? | GMV, doanh thu thuần, phí sàn theo loại, % phí, thực nhận | Haravan kênh sàn [S36], Pancake phí sàn [S41] | `shopee_channel_economics` |
| R11 | Đối soát tiền về | CFO | T1 (+COD) | Tiền đã về chưa, lệch ở đâu? | Thực nhận dự kiến và thực tế, COD đối soát, chênh lệch | Shopify net payments [S3], Pancake thực nhận ĐVVC [S41] | `finance_accounting_recon`, `finance_cashflow` |
| R12 | Lãi theo SKU, đơn, kênh | CFO, CEO | T2 (+T1) | Bán cái gì có lãi? | COGS, gross profit (CM1), CM2, % phủ giá vốn | Shopify Profit [S5], Sapo lợi nhuận [S29] | `order_profitability_all`, `finance_channel_pl` |
| R13 | P&L tháng | CFO | T2b `ledger` | Lãi ròng sau chi phí chung? | CM1 → CM2 → CM3 → lãi sau chi phí chung | Lifetimely P&L [S21], Nhanh KQHĐKD [S39] | `finance_pl`, `finance_cost_ledger` |
| R14 | Hiệu quả quảng cáo | MKT, CEO | T3 | Tiền quảng cáo có ra lãi không? | Ad spend, MER, NC-ROAS, CAC, CM3, CPA theo kênh | Triple Whale [S15][S16], Shopify Marketing [S8] | `marketing_roi`, `marketing_weekly_tracker` |
| R15 | RFM và hàng đợi chăm sóc | MKT, LEAD | T0 (RFM) + T4 (hàng đợi) | Gọi ai hôm nay? | Phân nhóm RFM, khách đến chu kỳ mua, khách có nguy cơ rời bỏ | Shopify RFM [S4], Haravan RFM [S35] | `customer_intelligence`, `customer_daily_action_queue` |

Thêm một report hạ tầng nằm ngoài 15 report trên nhưng nên đi kèm mọi bản cài: **Sức khoẻ dữ liệu** (độ tươi, `UNMAPPED`, lệch so với nguồn), theo mẫu Account Health của Daasity [S26] (`ingestion_health`).

**Trang chủ theo persona** là ghép thẻ KPI từ các report, không phải report riêng: CEO = R02 + R03 + R10/R12/R14 khi có; CFO = R11 + R12 + R13; MKT = R14 + R07 + R06; OPS = R09 + R08; SOLO = R01 + R04 + R08 (gọn); LEAD = R05 + R15.

### 6.3 Metric lõi (định nghĩa đề xuất)

Tên cột `name` theo `docs/analytics-handbook/semantic/metrics.md` khi đã có. Tên Shopify ghi trong ngoặc để đối chiếu.

| Metric | Định nghĩa đề xuất | Ghi chú / nguồn |
|---|---|---|
| `orders_count` | Số đơn hợp lệ theo quy tắc ghi nhận của tenant (mặc định: không tính đơn huỷ và đơn nháp) | Pancake "tính chốt đơn khi" [S40]; Shopify thì có tính đơn huỷ [S2] |
| `gross_revenue` (gross sales) | Σ giá niêm yết × SL, trước giảm giá, không gồm ship/thuế | [S2] |
| `discount_amount` | Giảm giá dòng hàng + giảm giá cấp đơn phân bổ theo tỉ lệ (giảm giá của shop; trợ giá sàn để riêng) | [S2][S41] |
| `return_amount` | Giá trị hàng trả/hoàn, tính vào ngày hoàn (tham số: ngày hoàn hay ngày đơn) | [S2][S40][S45] |
| `net_revenue` (net sales) | gross − discount − return; không gồm ship, thuế, phí sàn | [S3]. Pancake gọi "Doanh thu bán hàng" (cộng sàn trợ giá) [S41] |
| `gmv` | Tổng tiền đơn đặt (gồm cả đơn hoàn/huỷ về sau), chỉ dùng cho sàn | Douyin, WeChat [S45][S47] |
| `aov` | `net_revenue / orders_count` (ratio of sums) | Shopify dùng (gross − discount)/đơn [S2]; Pancake dùng doanh thu không trừ hoàn [S41]. **Cần chốt** |
| `units_per_order` | Σ SL / orders_count | [S2][S41] |
| `cancel_rate`, `return_rate` | Đơn huỷ / đơn tạo; đơn hoàn / đơn chốt | [S41] |
| `delivery_success_rate` | Đơn giao thành công / đơn đã gửi | Pancake "tỉ lệ phát" [S41] |
| `new_customers`, `returning_customer_rate` | Khách có đơn đầu tiên trong kỳ; khách cũ / khách có đơn | [S4][S41] |
| `repeat_purchase_rate_cohort` | % khách của cohort có đơn thứ 2 trong N ngày | [S4][S23] |
| `marketplace_fee_amount` | Σ phí cố định + hoa hồng + thanh toán + dịch vụ (SFP, Xtra…) | [S41][S36] |
| `net_settlement` (thực nhận) | Tiền sàn trả shop sau toàn bộ khấu trừ | [S36] |
| `cogs_amount` | SL × giá vốn tại thời điểm bán; dòng không có giá vốn tách thành "chưa có giá vốn" | [S5] |
| `gross_profit` (CM1) | net_revenue − cogs | [S5][S36] |
| `contribution_margin_2` (CM2) | CM1 − phí sàn − phí VC shop trả − phí thanh toán | [S41][S21] |
| `contribution_margin_3` (CM3) | CM2 − ad spend | [S17][S41] |
| `ad_spend` | Chi phí quảng cáo từ nền tảng + chi phí quảng cáo nhập tay | Triple Whale blended [S15] |
| `mer` | **net_revenue / ad_spend** (chiều revenue/spend; ghi rõ là nghịch đảo của MER theo Triple Whale) | [S15][S18] |
| `nc_roas`, `cac` | Doanh thu khách mới / ad_spend; ad_spend / new_customers | [S16] |
| `sell_through_rate`, `days_of_supply`, `abc_class` | Theo định nghĩa Shopify (cửa sổ 28–30 ngày) | [S6] |
| `rfm_segment` | Điểm 1–5 tương đối (quintile) theo shop, ngưỡng sửa được | [S4][S35] |

**Tham số ghi nhận doanh thu (tenant, có mặc định):** `revenue_recognized_at` ∈ {order_created, confirmed, shipped, delivered, paid}; `return_deducted_at` ∈ {return_requested, return_completed}; `time_axis` ∈ {order_date, transaction_date} cho từng report. Lấy từ cấu hình Pancake [S40] và hai trục của Haravan [S37].

### 6.4 Kiến trúc report factory (khuyến nghị xếp hạng)

**Hạng 1, nên làm: registry YAML + mart + generator + overlay tenant.**

```
catalog/                         (nằm trong repo, có version, do ta sở hữu)
  metrics/*.yml                  # name, label_vi, label_en, type: sum|count|ratio(num,den)|derived, grain, mart_column, requires
  reports/R01..R15.yml           # persona[], requires[], enhances[], question, blocks: [{metric[], dims[], viz}], engines: [metabase|evidence|rill]
tenants/<tenant>/overlay.yml     # labels, hide[], thresholds, revenue_recognition params, extra_reports[] (chỉ thêm/ẩn/đổi nhãn, không sửa định nghĩa gốc)
generator  → Metabase (deploy qua API, đã có) | trang Evidence | metrics view Rill
check      → "golden query": số của cùng metric × kỳ phải khớp giữa mart và mọi engine
```

- **Lý do:** không thêm service; khớp quyết định "theo report, không theo engine"; tận dụng `deploy_from_markdown.js` và cấu trúc `semantic/metrics.md` sẵn có; overlay chép đúng mẫu đã chứng minh của Daasity refinement [S28] và Rill derived view [S58]; capability lấy từ khai báo connector trong roadmap.
- **Đánh đổi:** phải tự bảo trì generator cho 3 engine. Giảm rủi ro bằng cách để engine chỉ hiển thị cột đã tính sẵn trong mart (tổng hợp nhẹ, không tự tính lại logic).
- **Rủi ro:** registry phình thành "semantic layer tự chế". Giữ schema gần MetricFlow/Evidence metrics (base, dimensions, measures, filter, ratio) để còn đường lui.

**Hạng 2: Rill metrics view làm đích sinh cho phân tích tự do.** Đã có trong stack và derived view hợp với overlay. Không dùng làm nguồn sự thật vì chỉ phục vụ Rill.

**Hạng 3: MetricFlow, xét lại ở Đợt 3 (semantic layer).** Đáng cân nhắc khi cần truy vấn metric động (agent/MCP hỏi metric) thay vì chỉ dashboard tĩnh. Trước khi chọn cần spike `mf query` trên dbt-duckdb của dự án, vì docs dbt không liệt kê DuckDB [S49].

**Không khuyến nghị:** Cube (thêm service, lợi thế đa tenant thừa với bản cài on-prem đơn khách); Lightdash (phải thay Metabase, DuckDB cục bộ chưa rõ); metric native của Metabase làm nguồn sự thật (không xuất được trên OSS, không dùng được trong SQL); migrate sang Evidence Core lúc này (không thấy connector DuckDB file cục bộ).

### 6.5 Ma trận đánh đổi (1 = kém, 5 = tốt)

| Tiêu chí | A. Registry + generator | F. Rill-only | B. MetricFlow | C. Cube | E. Metabase metrics |
|---|---|---|---|---|---|
| Hợp DuckDB on-prem, nhẹ | 5 | 5 | 3 | 2 | 4 |
| Một nguồn sự thật cho 3 engine | 4 | 1 | 3 | 4 | 1 |
| Overlay per-tenant | 4 | 4 | 2 | 5 | 2 |
| Độ phức tạp vận hành (thấp = tốt) | 4 | 5 | 3 | 2 | 4 |
| Rủi ro nhà cung cấp/giấy phép | 5 | 4 | 3 (đã đổi license 2 lần) | 3 | 2 (tính năng nằm sau bản Pro) |
| Công sức ban đầu | 3 | 4 | 2 | 2 | 4 |

---

## 7. Giới hạn của nghiên cứu

- **Trung Quốc:** không truy cập được help center chính thức của 生意参谋, 京东商智 và 抖音电商罗盘 (cần đăng nhập). Tên module (作战室, 品类, 物流, 竞争) chỉ có nguồn [B] cũ (2016) hoặc [C]. Phần có nguồn [A] duy nhất là API của 微信小店.
- **SaaS:** Triple Whale KB "summary page metrics library" trả "page doesn't exist" lúc truy cập. Công thức Net Profit lấy từ trích đoạn của công cụ tìm kiếm. Công thức lợi nhuận của BeProfit và P&L của Lifetimely không đọc được. Polar và Glew chỉ có trang marketing.
- **Việt Nam:** help center của Sapo (`help.sapo.vn`) không có sitemap đọc được, nên danh sách report của Sapo lấy từ blog và trang cập nhật tính năng [B]. KiotViet đọc từ một trang tổng hợp. Chưa vào thử UI thật của bất kỳ hãng nào.
- **Shopify:** không đọc nhóm Fraud và không kiểm giới hạn theo gói cho từng report.
- **Semantic layer:** chưa chạy thử MetricFlow trên dbt-duckdb của dự án; chưa kiểm license của CLI Evidence Core.
- **Không có số liệu adoption** (bao nhiêu SME Việt dùng report nào). Danh sách 15 report là suy luận từ tính năng của đối thủ, chưa phỏng vấn người dùng.

## 8. Câu hỏi còn mở

1. AOV chia theo `net_revenue` (đề xuất) hay theo doanh thu không trừ hoàn như Pancake và Sapo? Ảnh hưởng mọi report so sánh với số trên POS.
2. Chốt chiều MER: revenue/spend (đề xuất) hay spend/revenue (Triple Whale)?
3. Mặc định ghi nhận doanh thu: đơn tạo hay đơn giao thành công? Hiện mart dùng gì? Cần đối chiếu `rules.md`.
4. `net_revenue` có cộng "sàn trợ giá" (cách của Pancake) hay để thành dòng riêng?
5. Catalog đặt ở `docs/analytics-handbook/` hay thành module code (`catalog/`) có schema kiểm tra?
6. Evidence: ghim phiên bản legacy (hiện là `latest`) hay lên kế hoạch thay thế? Evidence Core self-host chưa có connector DuckDB file.
7. Persona SOLO và LEAD có nằm trong phạm vi Đợt 7 không, hay để sau 4 persona chính?

---

## Nguồn (truy cập 2026-10-14)

- [S1] [A] Shopify Help, Default reports. https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/report-types/default-reports
- [S2] [A] Shopify Help, Sales reports. …/default-reports/sales-report
- [S3] [A] Shopify Help, Finance reports. …/default-reports/finances-report
- [S4] [A] Shopify Help, Customers reports. …/default-reports/customers-reports
- [S5] [A] Shopify Help, Profit reports. …/default-reports/profit-reports
- [S6] [A] Shopify Help, Inventory reports. …/default-reports/inventory-reports
- [S7] [A] Shopify Help, Acquisition reports. …/default-reports/acquisition-reports
- [S8] [A] Shopify Help, Marketing reports. …/default-reports/marketing-reports
- [S9] [A] Shopify Help, Behavior reports. …/default-reports/behaviour-reports
- [S10] [A] Shopify Help, Order reports. …/default-reports/order-reports
- [S11] [A] Shopify Help, Retail sales reports. …/default-reports/retail-sales-reports
- [S12] [A] Shopify Help, Create a new data exploration. https://help.shopify.com/en/manual/reports-and-analytics/shopify-reports/new-analytics/explorations
- [S13] [A] Shopify.dev, ShopifyQL. https://shopify.dev/docs/api/shopifyql/latest.md
- [S14] [B] Shopify Changelog, New analytics is now the default. https://changelog.shopify.com/posts/new-analytics-is-now-the-default
- [S15] [A] Triple Whale developer docs, Blended ROAS. https://triplewhale.readme.io/docs/blended-roas
- [S16] [A] Triple Whale developer docs, NC ROAS. https://triplewhale.readme.io/docs/nc-roas
- [S17] [C] Triple Whale KB, Summary page metrics library. https://kb.triplewhale.com/en/articles/6127778-summary-page-metrics-library (trả 404 lúc truy cập; nội dung lấy từ chỉ mục tìm kiếm)
- [S18] [C] eightx, Polar vs Triple Whale vs Northbeam. https://eightx.co/blog/polar-vs-triple-whale-vs-northbeam
- [S19] [B] Polar Analytics, Pre-built dashboards. https://polaranalytics.com/business-intelligence
- [S20] [B] Polar Analytics, Template categories. https://www.polaranalytics.com/template-categories/reduce-acquisition-cost
- [S21] [A] AMP/Lifetimely Help, Lifetime Value Reports. https://help.useamp.com/category/640-lifetime-value-reports
- [S22] [A] AMP/Lifetimely Help, LTV Cohort Report Overview. https://help.useamp.com/article/1124-ltv-cohort-report-overview
- [S23] [A] Peel Help, List of Metrics. https://help.peelinsights.com/docs/list-of-metrics
- [S24] [B] Glew, Ecommerce dashboard. https://www.glew.io/features/ecommerce-dashboard
- [S25] [B] BeProfit, Shopify App Store. https://apps.shopify.com/beprofit-profit-tracker
- [S26] [A] Daasity Help, llms.txt / Report Library. https://help.daasity.com/llms.txt
- [S27] [A] Daasity Help, Company Overview. https://help.daasity.com/core-concepts/dashboards/report-library/omnichannel/company-overview.md
- [S28] [A] Daasity Help, Semantic Layer & Governance. https://help.daasity.com/core-concepts/bi-tools/looker/semantic-layer-and-governance
- [S29] [B] Sapo, Nâng cấp báo cáo lợi nhuận (10/07/2026). https://www.sapo.vn/cap-nhat-tinh-nang/bao-cao-loi-nhuan
- [S30] [B] Sapo, Dashboard Phân tích kinh doanh Sàn (24/03/2025). https://www.sapo.vn/cap-nhat-tinh-nang/phan-tich-kinh-doanh-san
- [S31] [B] Sapo Blog, Hướng dẫn làm báo cáo với phần mềm Sapo. https://www.sapo.vn/blog/huong-dan-lam-bao-cao-voi-phan-mem-quan-ly-ban-hang-sapo
- [S32] [A] Haravan Help, sitemap mục `docs/reports/*`. https://help.haravan.com/sitemap.xml
- [S33] [A] Haravan Help, Tổng quan về tính năng báo cáo. https://help.haravan.com/docs/reports/overview/tong-quan-ve-tinh-nang-bao-cao-haravan/
- [S34] [A] Haravan Help, Hướng dẫn sử dụng bảng phân tích báo cáo. https://help.haravan.com/docs/reports/custom-reports/huong-dan-su-dung-bang-phan-tich-bao-cao/
- [S35] [A] Haravan Help, Báo cáo khách hàng theo phân khúc RFM. https://help.haravan.com/docs/reports/customers/bao-cao-khach-hang-theo-phan-khuc-rfm/
- [S36] [A] Haravan Help, Báo cáo kênh bán hàng sàn TMĐT. https://help.haravan.com/docs/reports/marketplace/bao-cao-kenh-ban-hang-san-thuong-mai-dien-tu/
- [S37] [A] Haravan Help, Khác biệt giữa Báo cáo bán hàng và Báo cáo tài chính. https://help.haravan.com/docs/faqs/reports/co-gi-khac-biet-giua-bao-cao-ban-hang-va-bao-cao-tai-chinh/
- [S38] [A] KiotViet, Hướng dẫn sử dụng: Báo cáo (Retail). https://www.kiotviet.vn/huong-dan-su-dung-kiotviet/retail-bao-cao/
- [S39] [A] Nhanh.vn, Hướng dẫn sử dụng POS, mục Báo cáo (llms.txt). https://pos.manual.nhanh.vn/llms.txt
- [S40] [A] Pancake POS docs, Thống kê mặc định. https://docs.pos.pages.fm/pos/thong-ke/thong-ke-mac-dinh.md
- [S41] [A] Pancake POS docs, Khái niệm (bảng công thức). https://docs.pos.pages.fm/pos/thong-ke/khai-niem.md
- [S42] [A] Pancake POS docs, Thống kê tuỳ chỉnh. https://docs.pos.pages.fm/pos/thong-ke/thong-ke-tuy-chinh.md
- [S43] [B] 《淘宝店铺 大数据营销+SEO+爆款打造 一册通》2.1 生意参谋平台概述 (Alibaba Cloud Developer, sách ~2016). https://developer.aliyun.com/article/102469
- [S44] [C] FanRuan blog, các bài về 生意参谋/京东商智. https://www.fanruan.com/blog/article/675595/
- [S45] [C] TT123, quy ước số liệu 抖音罗盘 (trang cho người bán xuyên biên giới). https://www.tt123.com/feature/Z7mMhye3
- [S45b] [B] 新浪新闻 (2022), 罗盘经营版. https://news.sina.com.cn/sx/2022-05-31/detail-imizmscu4390925.shtml
- [S46] [B] 36氪, 商品卡 lối vào. https://www.36kr.com/p/2199384059545473
- [S47] [A] 微信小店 developer docs, 数据分析. https://developers.weixin.qq.com/doc/store/shop/guide/operation/analytics.html
- [S48] [C] App Store, 京麦 (JD merchant). https://apps.apple.com/tm/app/id904548797
- [S49] [A] dbt docs, About MetricFlow. https://docs.getdbt.com/docs/build/about-metricflow
- [S50] [B] dbt Labs blog, Open source MetricFlow. https://www.getdbt.com/blog/open-source-metricflow-governed-metrics; PyPI metricflow (lịch sử license)
- [S51] [A] GitHub dbt-labs/metricflow: `dbt-metricflow/requirements-files/requirements-dbt-duckdb.txt` = `dbt-duckdb`; release v0.213.0 ngày 2026-09-10 (kiểm bằng `gh api`)
- [S52] [A] Cube docs, Multitenancy. https://docs.cube.dev/embedding/multitenancy
- [S53] [A] Cube docs, DuckDB data source. https://docs.cube.dev/admin/connect-to-data/data-sources/duckdb
- [S54] [A] Lightdash docs, CLI reference. https://docs.lightdash.com/references/lightdash-cli
- [S55] [A] Metabase docs, Metrics (semantic layer). https://www.metabase.com/docs/latest/data-modeling/semantic-layer/metrics
- [S56] [A] Metabase docs, Serialization. https://www.metabase.com/docs/latest/installation-and-operation/serialization
- [S57] [A] Metabase docs, Remote sync. https://metabase.com/docs/latest/installation-and-operation/remote-sync
- [S58] [A] Rill docs, Derived Metrics Views. https://docs.rilldata.com/developers/build/metrics-view/derived-metrics-views
- [S59] [A] Rill docs index. https://docs.rilldata.com/llms.txt; GitHub rilldata/rill (push gần nhất 2026-10-14)
- [S60] [A] Evidence legacy docs, Templated Pages. https://legacy-docs.evidence.dev/core-concepts/templated-pages/
- [S61] [A] Evidence docs, Migration Guide (legacy → Studio/Core). https://docs.evidence.dev/migration-guide.md
- [S62] [A] Evidence docs, Metrics. https://docs.evidence.dev/core-concepts/metrics.md
- [S63] [A] Evidence docs, Self Host. https://docs.evidence.dev/self-host/index.md
- [S64] [A] Evidence docs index (danh sách direct connectors). https://docs.evidence.dev/llms.txt; GitHub evidence-dev/evidence (MIT; bản phát hành gói gần nhất 2026-02-06)
