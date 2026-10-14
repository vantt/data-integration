# Taxonomy: chuẩn và pattern liên ngành để kiểm chứng thiết kế FEATURES → RULES → LABELS

> Ngày nghiên cứu: 2026-10-14. Phạm vi: đối chiếu thiết kế phân loại Đợt 4 (xem [taxonomy-engine.md](../../architecture/taxonomy-engine.md)) với chuẩn phân loại sản phẩm, kế toán, decision table, CDP/CRM, semantic layer, channel grouping và data governance.
> Quy ước: **[đã kiểm]** là thông tin lấy từ tài liệu chính thức hoặc nhiều nguồn khớp nhau; **[chưa chắc]** là thông tin từ nguồn thứ cấp hoặc từ hiểu biết sẵn có, cần đối chiếu trước khi dựa vào. Số trong ngoặc vuông `[S#]` trỏ tới mục Nguồn ở cuối file.

---

## TL;DR

1. **Hướng đi đúng và khớp với cách các hệ thống lớn đang làm.** Ba lớp "feature tính bằng SQL → rule là dữ liệu → label có tầng canonical" là cùng khuôn với GA4 channel groups (rule có thứ tự, kênh mặc định không sửa được, nhóm tuỳ chỉnh sửa được, rơi về `Unassigned`) [S1], Bloomreach segmentation (first-hit theo thứ tự tab, mỗi segmentation thành một thuộc tính) [S12], DMN decision table (hit policy, DRG các quyết định phụ thuộc nhau) [S5][S6], và ESEF anchoring (mỗi phần tử mở rộng của doanh nghiệp phải neo vào khái niệm chuẩn gần nhất có nghĩa rộng hơn) [S9]. Không có chuẩn nào bác bỏ thiết kế; các chuẩn chỉ ra những chỗ còn thiếu.
2. **Năm chỗ thiếu quan trọng nhất (P0):**
   - **Hit policy phải khai báo theo từng domain**, không ngầm định "first-hit" cho mọi thứ. Cần ít nhất `FIRST`, `UNIQUE` (cấm chồng lấn, có test) và `COLLECT` (domain đa nhãn như tag đơn, loại giảm giá). Thiết kế hiện tại chỉ có một nhãn mỗi (entity, domain), nên không biểu diễn được `primary_discount_type` đang chọn bằng `MAX_BY` trên 10 loại.
   - **Tách `UNMAPPED` khỏi `UNKNOWN` (thiếu dữ liệu đầu vào) và `NOT_APPLICABLE`.** Nếu gộp chung, chỉ số coverage sẽ báo sai và cảnh báo sẽ nhiễu.
   - **Version theo cả ruleset, không chỉ theo từng rule.** Với first-hit, kết quả của một rule phụ thuộc mọi rule đứng trước nó, nên `rule_version` không đủ để tái lập kết quả. Cần thêm `ruleset_version` (hoặc hash) cho mỗi domain trong mỗi lần chạy.
   - **Có hai trục thời gian khác nhau:** "trạng thái entity tại thời điểm nào" (as-of-event so với current/SCD2, thiết kế đã có) và "áp bộ luật phiên bản nào" (chưa có). Mặc định nên là **restate**: áp luật hiện hành cho toàn bộ lịch sử, giống GA4 custom channel group [S2]. Chỉ **freeze** cho domain cần khoá kỳ, ví dụ GL sau khi khoá sổ.
   - **Canonical set phải có ID bất biến, có phiên bản, và có giá trị `OTHER`.** Đây là bài học từ Google Product Taxonomy (khuyên gửi ID thay vì path vì path đổi tên) [S15] và Shopify taxonomy (CalVer, có mapping giữa các taxonomy) [S17]. Ràng buộc "tenant label → đúng một canonical" nên theo quy tắc anchoring của ESEF.
3. **Không nên áp chuẩn phân loại sản phẩm quốc tế (GS1 GPC, UNSPSC, Amazon BTG) làm canonical.** Các chuẩn này phục vụ trao đổi dữ liệu thương mại, mua sắm B2B và listing marketplace, không phục vụ báo cáo quản trị của SME. Canonical sản phẩm nên là tập nhỏ do sản phẩm định nghĩa. Nếu sau này cần benchmark liên khách hàng thì để một crosswalk tuỳ chọn sang Google/Shopify taxonomy (YAGNI cho tới khi có nhu cầu).
4. **Semantic layer (MetricFlow, Cube, LookML) không thay được rule engine.** Cả ba định nghĩa nhóm phân loại bằng biểu thức `CASE` viết trong code [S19][S20][S21], không theo tenant và không có lịch sử luật. Kết luận này củng cố quyết định materialize label trong warehouse rồi pivot ra cột mart cho Metabase/Evidence.
5. **Xếp hạng cách triển khai engine:** (1) mỗi domain một model dbt, sinh từ một macro chung, `entity_labels` là view `UNION ALL`; (2) một model "long table" duy nhất cho mọi domain; (3) rule engine ngoài (DMN/Drools/Python). Phương án (1) giữ được lineage, incremental, test theo domain và DAG giữa các domain do chính dbt quản lý.

---

## 1. Chuẩn phân loại sản phẩm

### 1.1 Cấu trúc và versioning

| Chuẩn | Cấu trúc | Versioning / quản trị | Dùng cho | Độ tin cậy nguồn |
|---|---|---|---|---|
| **GS1 GPC** | 4 tầng Segment → Family → Class → **Brick**. Brick là khái niệm trung tâm; ba tầng trên chỉ để tìm brick và không truyền trong message GS1. Brick có thêm attribute type/value [S13] | Phát hành 2 lần/năm (GS1 Benelux ghi tháng 5 và 11; release notes cũ ghi tháng 6 và 12) [S13] **[đã kiểm, lịch có đổi theo thời gian]** | Đồng bộ dữ liệu sản phẩm giữa nhà sản xuất và nhà bán lẻ (GDSN) | GS1 member org: cao |
| **UNSPSC** | 4 tầng × 2 chữ số = mã 8 số (Segment/Family/Class/Commodity), `00` cho tầng cao hơn; có thể thêm 2 số business function [S14] | Version dạng `vNN.YYMM`; thay đổi qua quy trình yêu cầu add/change/delete/reclassify và bỏ phiếu [S14] **[đã kiểm qua nhiều nguồn thứ cấp]** | Mua sắm B2B, spend analysis | Wikipedia + tài liệu ERP: trung bình |
| **Google Product Taxonomy** | Cây khoảng 5.500–6.000 node, mỗi node có ID số và path đầy đủ [S15] | Google mô tả taxonomy "liên tục phát triển"; merchant gửi **ID hoặc path, không gửi cả hai**; Google tự gán category và merchant có thể override [S15]. Nhịp cập nhật (nhiều nguồn nói theo quý) **[chưa chắc]** | Merchant Center, Shopping ads | Google Help: cao |
| **Shopify Standard Product Taxonomy** | Hơn 10K category, hơn 1K attribute, hơn 26 ngành; mã nguồn mở MIT trên GitHub [S16][S17] | **CalVer** theo lịch API (vd. `2024-07`, mới nhất thấy là `2026-08`); tối đa một release mỗi quý; thư mục `data/integrations` chứa mapping sang taxonomy khác; Shopify cam kết thay đổi tương thích ngược [S16][S17] | Catalog của merchant Shopify | GitHub chính chủ: cao |
| **Amazon browse nodes / BTG** | Cây browse node theo từng marketplace; `item_type_keyword` đặt ASIN vào graph; SP-API trả node gợi ý theo product type [S18] | Browse Tree Guide tải theo marketplace; cây đổi thường xuyên **[chưa chắc, nguồn thứ cấp]** | Listing và tìm kiếm trên Amazon | SP-API docs: cao |
| **ARTS ODM (NRF, OMG lưu trữ)** | Item là đơn vị nhỏ nhất; **cho phép nhiều merchandise hierarchy song song**, số tầng tuỳ ý (thường đủ 7), tên tầng cấu hình được (Item–Group–Class–Department) [S22] | ODM 7.x; trạng thái chuẩn OMG chính thức **[chưa chắc]** | Mô hình dữ liệu vận hành bán lẻ | OMG-hosted: cao |

### 1.2 Pattern mapping local → chuẩn rút ra được

- **Mã ổn định tách khỏi nhãn hiển thị.** Google khuyên dùng ID vì path đổi chữ giữa các phiên bản [S15]. GS1 chỉ truyền brick code, không truyền tên [S13]. Áp vào thiết kế: `label_std` phải là **code** (vd. `B2B_DEALER`), tên tiếng Việt/Anh là thuộc tính của code.
- **Gán ở tầng lá, cuộn lên theo cây.** Cả GPC (brick), UNSPSC (commodity) và Google (node sâu nhất) đều gán ở tầng chi tiết nhất rồi suy ra tầng cha bằng cấu trúc cây, không gán lại bằng luật. Thiết kế đã có "luật phân cấp" (cây kênh 4 tầng); nên coi đó là **thuộc tính của canonical set** (bảng parent-child), không phải một dạng rule.
- **Nhiều hierarchy song song là bình thường** (ARTS ODM [S22]). Điều này khớp với ý "domain là DAG": một sản phẩm có thể đồng thời thuộc `product_matrix`, `product_lifecycle` và nhóm hàng của tenant.
- **Tự động gợi ý rồi để người override** (Google tự gán category và merchant override [S15]; Amazon SP-API gợi ý browse node [S18]). Đây chính là precedence `override > rules`.
- **Taxonomy có changelog và crosswalk giữa các phiên bản** (Shopify `CHANGELOG.md`, `data/integrations` [S16]). Canonical set của mình cũng cần changelog và bảng `deprecated_code → replacement_code`.

### 1.3 Đánh giá áp dụng

| Lựa chọn canonical cho domain sản phẩm | Phù hợp SME VN | Chi phí | Rủi ro | Xếp hạng |
|---|---|---|---|---|
| Tập nhỏ do sản phẩm định nghĩa (vd. 10–20 nhóm ngành hàng + `OTHER`) | Cao | Thấp | Benchmark liên khách hàng bị hạn chế | **1** |
| Shopify taxonomy (cắt ở tầng 1–2) làm canonical | Trung bình; nhiều shop VN bán qua Shopee/TikTok chứ không qua Shopify | Trung bình (mapping 10K node) | Mapping thủ công rất tốn công | 2 (chỉ khi cần benchmark) |
| Google Product Taxonomy | Trung bình | Trung bình | Cây đổi; mang tính quảng cáo | 3 |
| GS1 GPC / UNSPSC | Thấp (cho GDSN và mua sắm, không cho báo cáo bán lẻ) | Cao | Quá chi tiết, không ai trong SME điền được | 4 |

---

## 2. Mapping local → canonical trong kế toán và báo cáo tài chính

### 2.1 Hệ thống tài khoản Việt Nam

- **TT 200/2014/TT-BTC**: danh mục tài khoản cấp 1 và cấp 2 ở Phụ lục 1. Doanh nghiệp được mở chi tiết cấp 2, cấp 3 cho tài khoản chưa quy định chi tiết mà không cần xin phép; muốn thêm hoặc sửa tài khoản cấp 1, cấp 2 thì phải có chấp thuận bằng văn bản của Bộ Tài chính [S23] **[đã kiểm]**.
- **TT 99/2025/TT-BTC** ban hành 27/10/2025, **thay thế TT 200** cho năm tài chính bắt đầu từ 01/01/2026 (trừ nội dung cổ phần hoá DNNN). Thông tư này cho doanh nghiệp tự thiết kế hệ thống tài khoản, chứng từ, sổ sách để phù hợp đặc thù hoạt động, và đổi tên "Bảng cân đối kế toán" thành "Báo cáo tình hình tài chính" [S24] **[đã kiểm qua KPMG và nhiều nguồn; nên đọc văn bản gốc trước khi khoá danh mục]**. LuatVietnam nhắc 17 quy định của TT 200 vẫn áp dụng từ 2026 **[chưa chắc về nội dung]**.
- **TT 133/2016/TT-BTC** (chế độ kế toán doanh nghiệp nhỏ và vừa): còn hiệu lực hay đã có văn bản thay thế tại 10/2026 thì **[chưa kiểm]**. Phần lớn khách hàng SME có thể đang dùng TT 133 nên cần kiểm.

**Hệ quả cho thiết kế:** với domain `GL account`, "canonical" tự nhiên là **tài khoản cấp 1/cấp 2 theo chế độ kế toán** mà doanh nghiệp áp dụng (TT 99, hoặc TT 133). Tài khoản chi tiết của doanh nghiệp (cấp 3 trở xuống, hoặc hệ thống tự thiết kế theo TT 99) là "tenant label". Hai điểm cần lưu ý:

1. Mapping theo **tiền tố mã tài khoản** là dạng rule tự nhiên nhất, và hit policy đúng cho nó là **longest-prefix-wins** (`5111` thắng `511`), không phải thứ tự ưu tiên do người nhập. Cách này tự đúng khi thêm tài khoản con, giống cách Tally gán ledger theo group: gán group thì mọi ledger con thừa hưởng [S25].
2. TT 99 cho tự thiết kế hệ thống tài khoản, nên khoảng cách giữa tài khoản của doanh nghiệp và danh mục chuẩn có thể lớn hơn trước; khi đó mapping trực tiếp (bảng) phải thay cho mapping theo tiền tố. Canonical set của domain GL cũng phải có **phiên bản theo chế độ kế toán** (`VAS_TT200`, `VAS_TT99`, `VAS_TT133`), vì một tenant có thể có dữ liệu trước và sau 2026.

### 2.2 XBRL / IFRS Taxonomy: mô hình quản trị đáng mượn nhất

- IFRS Taxonomy **không phải** chart of accounts. Việc mapping cần xét nghĩa kế toán, không chỉ khớp tên, và nên giữ chuỗi truy vết từ nguồn tới chính sách kế toán, tới phần tử được chọn, tới fact được tag [S26] **[nguồn vendor, mức trung bình]**.
- Taxonomy quốc gia hoặc ngành được **thêm** extension nhưng **không được bỏ** tag chuẩn [S26] **[chưa chắc, nguồn thứ cấp]**.
- **ESEF anchoring** [S9][S10] **[đã kiểm, XBRL International]**:
  - Mỗi extension phải neo vào khái niệm chuẩn **gần nhất có nghĩa rộng hơn** (wider).
  - Nếu một dòng gộp hai khái niệm chuẩn trở lên thì phải neo thêm vào từng khái niệm **hẹp hơn** (narrower).
  - Subtotal không cần neo.
  - Không neo extension vào một extension khác.

**Ánh xạ sang thiết kế (đây là pattern nên dùng cho quan hệ tenant label → `label_std`):**

| ESEF | Thiết kế của mình |
|---|---|
| Extension element | Tenant label (vd. `ĐẠI LÝ CẤP 1`) |
| Neo wider bắt buộc | Mỗi tenant label **bắt buộc** có đúng một `label_std` có nghĩa bao trùm nó (vd. `B2B_DEALER`) |
| Không có wider phù hợp | Dùng `OTHER` của domain, đồng thời ghi lại thành ứng viên để mở rộng canonical set ở phiên bản sau |
| Dòng gộp nhiều khái niệm chuẩn (cần narrower) | **Không cho phép.** Nếu tenant label `ĐẠI LÝ & CTV` trải trên hai canonical thì phải tách luật thành hai label; một label không được ánh xạ một-nhiều |
| Không neo vào extension | Tenant label không neo vào tenant label khác; phân cấp giữa label đi qua canonical hoặc qua domain khác |

### 2.3 Quản trị bảng mapping

Từ các công cụ RDM như Informatica Reference 360, erwin và CluedIn [S27][S28][S29] **[nguồn vendor, nhưng thống nhất với nhau]**, một crosswalk được quản trị thường có:

- danh sách code canonical có `effective_from` / `effective_to` / `status`;
- dòng mapping có `approved_by`, `approved_at` và (tuỳ chọn) `match_confidence`;
- vòng đời `draft → approved → published`;
- **version cho cả codeset lẫn crosswalk**, publish theo môi trường.

Theo thiết kế, Đợt 4 đã có bước "④ Xem trước tác động → ⑤ Áp dụng (duyệt)". Phần còn thiếu là `status` và người duyệt trên từng dòng luật (xem mục 8).

---

## 3. Decision table và rule engine nhẹ đi cùng SQL/dbt

### 3.1 OMG DMN

**Hit policy** [S5][S6][S7] **[đã kiểm qua Camunda docs và Trisotech/Bruce Silver; chưa đọc trực tiếp spec OMG]**:

| Policy | Ý nghĩa | Khi dùng |
|---|---|---|
| `U` Unique | Các rule không được chồng lấn; chồng lấn là lỗi | Domain có điều kiện rời nhau tự nhiên (ngưỡng, mapping trực tiếp) |
| `A` Any | Được chồng lấn nếu output giống nhau | Ít dùng |
| `P` Priority | Được chồng lấn; output có **thứ tự ưu tiên khai báo trên danh sách giá trị output**, không phụ thuộc thứ tự dòng | Domain mà thứ tự ưu tiên là thuộc tính của nhãn (vd. `STAFF` > `KOL` > `WHOLESALE` > `RETAIL`) |
| `F` First | Lấy rule khớp đầu tiên theo thứ tự dòng | Pattern matching trên chuỗi |
| `C` Collect (+ `SUM/MIN/MAX/COUNT`) | Trả mọi output khớp, có thể gộp | Domain đa nhãn (tag) |
| `R` / `O` | Collect theo thứ tự rule hoặc thứ tự output | Hiếm dùng [S7] |

- Bruce Silver (Trisotech) gọi `F` là "semi-deprecated" vì trái nguyên tắc logic khai báo độc lập với thứ tự dòng, và khuyên dùng `P` [S7]. Spec không bắt buộc bảng phải đầy đủ (completeness), nhưng thực hành tốt là đầy đủ; "gap" (tổ hợp input không khớp rule nào) được coi là lỗi. Công cụ phân tích decision table kiểm tra gap, subsumption (rule bị rule khác bao trùm) và hit policy sai [S7].
- **DRG (Decision Requirements Graph):** quyết định này dùng output của quyết định khác làm input. Đây đúng là "decision table over other labels" và "domains form a DAG" trong thiết kế.
- **FEEL:** ngôn ngữ biểu thức của DMN. Unary test kiểu `[10..50)`, `"A","B"`, `not("X")` là tập toán tử đủ cho ô điều kiện. Thiết kế không cần FEEL đầy đủ, nhưng nên giới hạn toán tử ở mức tương đương (xem mục 8, R7).

**Bài học cho thiết kế:** "first-hit theo priority" mà thiết kế đang dùng chính là `F`. Nó thực dụng cho pattern matching (GA4, Bloomreach cũng dùng). Tuy vậy, cần cho phép khai báo `U` và `P` theo domain và cần **phát hiện rule chết/bị che** (subsumption): rule không bao giờ thắng vì rule đứng trước luôn bắt hết.

### 3.2 Pattern trong dbt và warehouse

- **Seeds làm mapping table** là pattern phổ biến và đã có sẵn trong dự án (`ref_order_sources`, `ref_tag_categories` có `pattern/match_type/priority`). Hạn chế đã biết: seed nạp lại toàn bộ, không có lịch sử, không có duyệt. Nếu luật đến từ Google Sheet thì sheet là giao diện, còn bảng trong warehouse phải có snapshot (dbt snapshot hoặc bảng append-only) để có lịch sử luật **[thực hành chung, không có nguồn chuẩn duy nhất]**.
- **Data Vault 2.0:** business rule áp ở business vault, có reference hub/satellite/reference table, và effectivity satellite cho quan hệ có hiệu lực theo thời gian [S30][S31]. Đáng mượn là tách `load_date` (khi nào biết) khỏi `effective_from` (khi nào đúng về nghiệp vụ). Đây chính là hai trục thời gian nêu ở TL;DR.
- **Rule engine ngoài** (Drools/Camunda DMN, Python rule libraries): mạnh về phân tích bảng, nhưng phải chạy ngoài DuckDB, mất lineage dbt, thêm runtime cần vận hành. Với quy mô SME (hàng chục nghìn tới vài triệu dòng), SQL sinh từ dữ liệu luật đủ dùng **[đánh giá]**.

---

## 4. Phân khúc khách hàng trong CDP/CRM: cách giữ canonical cố định mà vẫn cho tuỳ biến

| Hệ thống | Canonical cố định | Phần tuỳ biến | Cách gán | Nguồn |
|---|---|---|---|---|
| **HubSpot lifecycle stage** | Có bộ stage mặc định (Subscriber → Lead → MQL → SQL → Opportunity → Customer → Evangelist → Other **[danh sách theo hiểu biết, chưa kiểm lại]**) | Đổi tên stage mặc định, thêm stage tuỳ chỉnh | Tự động chỉ được **đi tiến**; import/form/API/workflow cũng chỉ set tiến; muốn lùi phải xoá giá trị trước; property history ghi nguồn của từng lần đổi | [S3] **[đã kiểm]** |
| **Salesforce picklist** | **Global value set** luôn là restricted picklist; chỉ admin sửa; giá trị ngoài danh sách bị từ chối kể cả qua API; phân biệt hoa thường | **Record type** chọn tập con giá trị dùng cho từng loại bản ghi | Người dùng chọn hoặc tự động hoá | [S4] **[đã kiểm, Trailhead + nhiều nguồn]** |
| **Segment (Twilio) Engage/Unify** | Không có canonical set; computed trait là chỉ số theo profile (B2C) hoặc account (B2B) | Audience là điều kiện trên trait/event; tạo audience thì sinh ra trait cùng tên | Mỗi trait/audience có lookback window tính theo timestamp của event | [S11] **[đã kiểm]** |
| **RudderStack Profiles** | Không có canonical | Feature/trait định nghĩa bằng YAML có version control; tool sinh SQL chạy trong warehouse; output là bảng "entity traits 360" | Warehouse-native | [S32] **[đã kiểm, docs nhiều phiên bản]** |
| **Klaviyo RFM** | **Bộ nhóm cố định**: Champions, Loyal, Recent, Needs attention, At risk, Inactive | Không đổi tên nhóm; người dùng tạo segment trên property `$current_month_rfm_group` | Tính lại hằng ngày; có nhóm tháng trước để bắt chuyển dịch ("Became At risk"). Thang điểm (1–3 theo Klaviyo Academy, hay quintile) **[chưa chắc]** | [S33] |
| **Bloomreach Engagement** | Không có | Segmentation gồm nhiều segment | **Loại trừ lẫn nhau, first-hit theo thứ tự tab trái → phải**; đổi thứ tự tab thì đổi kết quả; lưu thành một thuộc tính khách | [S12] **[đã kiểm, docs chính thức]** |

**Pattern rút ra:**

1. **"Canonical cố định + tên/giá trị tuỳ biến"** có hai biến thể. HubSpot cho đổi tên ngay trên giá trị chuẩn; Salesforce khoá cứng danh sách rồi cho chọn tập con theo record type. Thiết kế "tenant label + `label_std` bắt buộc" nằm giữa hai cách và mạnh hơn cả hai, vì tenant có nhãn riêng mà report chuẩn vẫn chạy được.
2. **Kiểm soát chiều chuyển trạng thái** (HubSpot forward-only) là một ràng buộc mà thiết kế chưa có. Với domain kiểu lifecycle (`LIFECYCLE_*`), cần quyết định rõ nhãn được phép lùi hay không; nếu tính lại từ feature thì nhãn tự lùi.
3. **Lưu lịch sử nhãn để bắt chuyển dịch** (Klaviyo previous/current month group): báo cáo "khách chuyển từ VIP sang At risk" cần snapshot nhãn theo kỳ, không tự có từ bảng current.
4. **Chặt về giá trị:** Salesforce từ chối giá trị lạ và phân biệt hoa thường. Đây đúng là lỗi `'Active'` vs `'ACTIVE'` mà dự án đang có, và test `accepted_values` trên `label_std` sẽ chặn được nó.
5. **Feature định nghĩa bằng cấu hình, sinh SQL, chạy trong warehouse** (RudderStack) giống hướng "features tính bằng SQL". Khác biệt là ở thiết kế này feature do sản phẩm viết, không do tenant viết. Đây là lựa chọn đúng cho SME.

---

## 5. Semantic layer: định nghĩa nhóm phân loại khai báo

| Công cụ | Cách định nghĩa nhóm | Giới hạn liên quan |
|---|---|---|
| **dbt Semantic Layer / MetricFlow** | Dimension `type: categorical`, `expr` là SQL tuỳ ý (vd. `case when quantity > 10 ...`). Hỗ trợ SCD2 qua `validity_params` (`is_start`/`is_end`, entity `natural`); khi một kỳ thô có nhiều giá trị thì lấy giá trị hợp lệ ở đầu kỳ [S19] **[đã kiểm]** | Logic nằm trong YAML của code, không theo tenant; semantic model có SCD2 không chứa simple metric được [S19] |
| **Cube** | Dimension có `case` gồm danh sách `when {sql, label}` và `else`; label có thể động [S20] **[đã kiểm]** | Vẫn là `CASE` sinh lúc query; luật nằm trong model file |
| **LookML** | `type: tier` (ngưỡng số, `style` classic/integer/interval/relational), tham số `case` (`when`/`else`), hoặc `CASE WHEN` trong `sql` [S21] **[đã kiểm]** | Như trên; có thể dùng parameter cho người dùng tự chọn ngưỡng tier |

**Kết luận:**

- Cả ba công cụ chỉ đưa `CASE` từ SQL lên YAML. Không công cụ nào hỗ trợ luật theo tenant, override theo entity, lịch sử luật hay coverage. Như vậy chúng **không thay** được engine trong thiết kế.
- Tính nhãn lúc query (semantic layer) làm mất khả năng giải thích theo `rule_id` và khó dùng nhãn làm input cho nhãn khác (DAG). Materialize nhãn (thiết kế) là đúng.
- Có hai thứ đáng mượn. (a) **Ngưỡng là tham số** (LookML tier với parameter) giống dạng rule threshold. (b) **Ngữ nghĩa join SCD2 của MetricFlow** (`valid_from <= t < valid_to`, lấy giá trị đầu kỳ khi gom thô) dùng làm đặc tả cho chế độ "as-of-event" khi gắn nhãn khách vào đơn.
- Dự án hiện dùng Metabase và Evidence, không dùng semantic layer, nên pivot ra cột mart là đúng tầng.

---

## 6. Channel taxonomy cho bán lẻ và thương mại điện tử

### 6.1 GA4 channel groups: mẫu gần nhất với thiết kế

- **Default channel group:** 19 kênh (Affiliates, AI Assistant, Audio, Cross-network, Direct, Display, Email, Mobile Push, Organic Search/Shopping/Social/Video, Paid Other/Search/Shopping/Social/Video, Referral, SMS). Khi không có luật nào khớp thì gán **`Unassigned`**. Default group **không sửa được** vì Google giữ nó làm chuẩn chung [S1] **[đã kiểm, Google Help]**. Đáng chú ý là danh sách kênh vẫn được Google thêm theo thời gian (vd. "AI Assistant"), tức canonical set cũng tiến hoá.
- **Luật** khớp trên source/medium/campaign, cộng với **danh sách source theo category do Google duy trì** (bảng tải về được, nhận yêu cầu bổ sung, rà ít nhất mỗi năm một lần) [S1]. Đây chính là pattern "feature = `source_category` lấy từ danh sách tham chiếu, rule chỉ tham chiếu feature".
- **Thứ tự đánh giá:** luật được xét theo thứ tự và luật khớp đầu tiên quyết định [S34] **[nguồn thứ cấp; trang Google không ghi rõ thứ tự]**.
- **Custom channel group:** bản standard có 2 nhóm, bản 360 có 5; mỗi nhóm có 25 hay 50 kênh thì các nguồn mâu thuẫn **[chưa chắc]**. Custom group **áp hồi tố** lên dữ liệu cũ khi chọn trong report; "primary channel group" tạo ra một bản sao default có thể sửa [S2][S34].

### 6.2 Danh sách kênh omnichannel và ARTS

- Không tìm được một "danh sách kênh omnichannel chuẩn" có tổ chức chuẩn hoá đứng sau. ARTS ODM mô hình hoá giao dịch, item và customer, nhưng không công bố một bộ giá trị kênh bán chuẩn **[không tìm thấy, chưa chắc]**.
- Thực tế của SME Việt Nam (POS, website, Shopee, Lazada, TikTok Shop, Facebook/Zalo chat, đại lý, B2B, CTV/KOL, cross-border) không trùng với GA4 (GA4 là kênh **thu hút traffic**, còn đây là kênh **bán/fulfil**). Vì vậy canonical channel nên do sản phẩm tự định nghĩa theo hai trục: **`channel_category`** (Online marketplace / Own online / Offline store / B2B / Social commerce / Other) và **`channel_format`**, giữ cây 4 tầng mà dự án đã có.

**Bài học cho thiết kế:** mô hình "default không sửa được + primary group là bản sao sửa được + custom group" của GA4 tương ứng đúng với layered packs "product default → tenant". GA4 cho thấy hai điều nên làm. Thứ nhất, **report luôn chạy được trên default** khi tenant chưa cấu hình. Thứ hai, **tenant không sửa default mà tạo lớp riêng** đè lên.

---

## 7. Chất lượng dữ liệu và quản trị phân loại

Các kiểm tra nên có (tổng hợp từ DMN analysis [S7], RDM [S27]–[S29], GA4 `Unassigned` [S1], và dbt testing chung):

| Kiểm tra | Định nghĩa | Ngưỡng / hành động |
|---|---|---|
| **Coverage** | % entity (và % doanh thu) theo từng domain có nhãn khác `UNMAPPED` | Cảnh báo khi coverage theo doanh thu < ngưỡng (vd. 98%); đo theo **doanh thu**, không chỉ theo số dòng |
| **Unknown rate** | % `UNKNOWN` (feature null) | Tách khỏi coverage; đây là lỗi dữ liệu hoặc ingestion, không phải lỗi luật |
| **Uniqueness** | Domain single-valued: đúng một dòng mỗi (entity, domain[, as_of]) | Test `unique` |
| **Accepted values** | `label_std` thuộc canonical set của phiên bản hiện hành; tenant label thuộc danh sách label đã khai báo | Test `accepted_values` sinh từ seed canonical |
| **Overlap (cho `U`)** | Số entity khớp nhiều hơn một rule | Fail với `U`; với `F`/`P` chỉ báo cáo |
| **Dead / shadowed rule** | Rule có hit = 0 trong N lần chạy, hoặc luôn bị rule trước che | Báo cáo trong bước ④ xem trước |
| **Rule hit distribution** | Số entity và doanh thu theo `rule_id` | Phục vụ explainability và review |
| **Orphan override** | Override trỏ tới entity không còn tồn tại (bị merge hoặc xoá) | Cảnh báo |
| **Label drift** | Thay đổi phân bố nhãn giữa hai lần chạy liên tiếp không đi kèm thay đổi luật | Cảnh báo; thường do ngưỡng percentile hoặc dữ liệu nguồn đổi |
| **Impact preview** | Chạy ruleset đề xuất ở shadow, diff với hiện hành theo (domain, label_std, label): số entity chuyển nhãn và doanh thu chuyển | Dùng lại safety harness của phase 0 |
| **Explainability** | Mọi nhãn truy được về `rule_id`, `ruleset_version`, `source_layer` (product/connector/industry/tenant/override) | Cột bắt buộc trong `entity_labels` |

---

## 8. Đánh giá thiết kế đề xuất

### 8.1 Những gì thiết kế đã làm đúng (có chuẩn đỡ lưng)

| Điểm thiết kế | Chuẩn/pattern tương ứng | Nhận xét |
|---|---|---|
| Rule chỉ tham chiếu feature, không tham chiếu cột thô | GA4: rule dùng `source_category` từ danh sách tham chiếu [S1]; RudderStack: feature khai báo [S32] | Giữ. Đây là ranh giới quan trọng nhất để luật đổi được mà không đụng code |
| Precedence override > rules > default > UNMAPPED | Google auto-category + merchant override [S15]; GA4 `Unassigned` [S1] | Giữ, nhưng sửa lại tầng cuối (R2) |
| Hai tầng label: tenant + `label_std` bắt buộc | ESEF anchoring [S9]; HubSpot rename default [S3] | Giữ; bổ sung quy tắc anchoring (R4) |
| Domain là DAG, decision table trên label khác | DMN DRG [S6] | Giữ; cần ràng buộc kỹ thuật (R8) |
| Layered packs | GA4 default/primary/custom [S1][S2]; IFRS base + extension [S26] | Giữ; cần cơ chế tắt rule kế thừa (R6) |
| Một output dạng long table có `rule_id` | DMN "selected rule explains outcome" [S7] | Giữ ở dạng view; xem phương án triển khai ở 8.3 |
| Thời gian theo từng domain | MetricFlow SCD2 [S19]; Data Vault effectivity [S30] | Đúng, nhưng mới có một trong hai trục (R3) |

### 8.2 Khuyến nghị (xếp theo ưu tiên)

**P0: phải có trước khi chốt schema rule/label**

- **R1. Khai báo `hit_policy` và `cardinality` theo domain.**
  - `hit_policy ∈ {FIRST, UNIQUE, PRIORITY, LONGEST_PREFIX}`; `cardinality ∈ {single, multi}`.
  - Domain `multi` (tag đơn, loại giảm giá áp dụng) dùng `COLLECT`: `entity_labels` có nhiều dòng mỗi (entity, domain), và domain cần thêm một **rule chọn nhãn chính** (đúng như `MAX_BY` trong `primary_discount_type` hiện tại) khi pivot ra cột mart.
  - Nếu thiếu R1, engine sẽ ép mọi domain vào first-hit single-valued và mất thông tin ở các domain đa nhãn.
  - `LONGEST_PREFIX` dành cho mã tài khoản GL (mục 2.1).
  - `PRIORITY` theo nghĩa DMN (thứ tự đặt trên **giá trị output**, không đặt trên dòng) phù hợp `customer_type`: thứ tự `STAFF > KOL > CROSSBORDER > WHOLESALE > RETAIL` là thuộc tính nghiệp vụ của nhãn, và không bị phá khi ai đó chèn dòng luật mới vào giữa sheet.
- **R2. Mở rộng tầng cuối thành bốn trạng thái có code canonical dành riêng:**
  - `UNMAPPED`: có input nhưng không luật nào khớp. Đây là việc của nghiệp vụ.
  - `UNKNOWN`: feature bắt buộc bị null. Đây là việc của data/ingestion.
  - `NOT_APPLICABLE`: domain không áp dụng cho entity này, vd. `lifecycle_stage` cho khách chưa từng mua.
  - `OTHER`: tenant chủ động gom vào nhóm khác. Đây là một nhãn hợp lệ, không phải lỗi.

  Chỉ `UNMAPPED` mới kích hoạt vòng ⑥ → ③. Coverage tính trên mẫu số trừ `NOT_APPLICABLE`.
- **R3. Thêm trục "phiên bản luật".**
  - Mỗi lần chạy ghi `ruleset_version` theo domain (hash của toàn bộ dòng luật hiệu lực, kể cả các lớp pack), cạnh `rule_id`, `rule_version`.
  - Mặc định **restate**: nhãn của mọi kỳ tính bằng luật hiện hành. Cách này giống GA4 custom group [S2] và giữ số liệu các kỳ so sánh được với nhau.
  - Domain đánh dấu `freeze_after_close` (GL account, có thể cả team attribution sau khi chốt thưởng) thì giữ nhãn của kỳ đã khoá: lưu snapshot `entity_labels` theo kỳ và không tính lại.
  - Luật nên có `effective_from` để biết ngày có hiệu lực, nhưng **không** nên tự động áp "luật có hiệu lực tại thời điểm event" cho dữ liệu cũ. Cách đó làm hai kỳ không so sánh được và nhân đôi độ phức tạp. Chỉ bật khi nghiệp vụ yêu cầu rõ.
- **R4. Quy tắc anchoring cho tenant label** (theo ESEF):
  - Mỗi tenant label có **đúng một** `label_std`, được khai báo **một lần trong bảng label của tenant**, không lặp trên từng dòng luật. Lý do là DRY và để tránh hai luật gán cùng label vào hai canonical khác nhau.
  - Ràng buộc kiểm bằng test: `(domain, label) → label_std` là hàm, tức không có label nào ánh xạ tới hai canonical.
  - Label không tìm được canonical rộng hơn thì neo vào `OTHER`.
- **R5. Canonical set dùng code bất biến và có phiên bản.**
  - Bảng `taxonomy_canonical(domain, code, parent_code, sort_order, name_vi, name_en, introduced_in, deprecated_in, replaced_by)`.
  - Không đổi nghĩa một code đã phát hành; đổi nghĩa thì tạo code mới và đánh dấu code cũ `replaced_by`.
  - Thêm code canonical là thay đổi của **sản phẩm**, có changelog, giống nhịp release CalVer của Shopify [S16]. Tenant không thêm được code canonical (tương đương Salesforce global value set restricted [S4]).
  - Cây canonical (`parent_code`) thay cho "luật phân cấp" (mục 1.2).

**P1: cần trước khi giao cho tenant thứ hai**

- **R6. Layered packs cần thao tác "tắt" và có quy tắc xung đột.**
  - Thứ tự: `tenant > industry > connector > product default`.
  - Lớp trên phải **tắt được** một rule kế thừa (`rule_id` + `enabled=false`), không chỉ chèn rule ưu tiên cao hơn. Nếu không, rule mặc định "bắt rộng" sẽ vẫn hút entity ở cuối danh sách first-hit.
  - Priority nên được chuẩn hoá theo dải số cho từng lớp (vd. tenant 1000–1999, industry 2000–2999...) để thứ tự trộn giữa các lớp xác định được.
  - Bước ④ phải hiển thị rule nào bị lớp nào che.
- **R7. Giới hạn ngôn ngữ điều kiện của rule.**
  - Toán tử cho phép: `eq`, `in`, `not_in`, `between` (nửa mở `[a,b)` như FEEL), `starts_with`, `contains`, `regex`, `is_null`, cùng `AND` trong một dòng (decision table nhiều cột điều kiện).
  - **Không** cho SQL tự do trong rule. Luật đặc thù (chéo bảng) phải được viết thành **feature mới** do mình viết. Điều này giữ đúng nguyên tắc "rule chỉ tham chiếu feature", tránh SQL injection từ Google Sheet, và giữ rule dịch được sang bất kỳ engine nào.
  - **Chuẩn hoá chuỗi tiếng Việt ở tầng feature**, không ở tầng rule: `lower`, `trim`, gộp khoảng trắng, và cung cấp thêm phiên bản bỏ dấu (`strip_accents` của DuckDB, cần kiểm khi triển khai). Nếu không, `"Đại Lý"`, `"đại lý"` và `"Dai ly"` sẽ thành ba luật.
- **R8. DAG giữa domain phải do dbt quản lý, không do engine tự lặp.**
  - Mỗi domain một model `lbl_<domain>`; domain phụ thuộc label khác thì `ref()` model đó.
  - Có test chặn chu trình. dbt tự báo lỗi khi có cycle, nên nếu mỗi domain là một model thì chặn chu trình là miễn phí.
  - Decision table trên label chỉ được tham chiếu **`label_std`** của domain khác, không tham chiếu tenant label. Nếu tham chiếu tenant label, luật dẫn xuất (vd. `scope_*`, `order_nature`) sẽ không tái dùng được qua tenant, và pack mặc định sẽ gãy khi tenant đổi tên nhãn.
- **R9. Ngưỡng percentile phải ổn định.**
  - Percentile tính lại mỗi lần chạy làm nhãn trôi khi hành vi khách không đổi (khách "VIP" mất VIP vì người khác mua nhiều hơn). Phải chọn một trong hai:
    - (a) chốt điểm cắt theo kỳ (tháng/quý), lưu thành tham số có version;
    - (b) dùng cửa sổ tham chiếu cố định.
  - Ghi rõ cách xử lý giá trị nằm đúng biên (nửa mở `[a,b)`).
  - Klaviyo tính lại RFM hằng ngày nhưng giữ nhóm tháng trước để so sánh [S33]. Nếu chọn tính lại hằng ngày thì vẫn cần snapshot kỳ.
- **R10. Override theo entity phải có metadata.**
  - Các trường: `reason`, `created_by`, `created_at`, `expires_at` (tuỳ chọn).
  - Có test orphan (entity bị merge hoặc xoá ở Sapo).
  - Override đi vào `entity_labels` với `source_layer='override'` để báo cáo được tỉ lệ nhãn đến từ override. Tỉ lệ cao chứng tỏ luật kém.

**P2: nên có, làm sau**

- **R11. Thêm trạng thái duyệt trên dòng luật** (`draft/approved`). Chỉ `approved` vào ruleset hiệu lực; `draft` chạy trong impact preview. Đây là mức tối thiểu của vòng đời RDM [S27][S29].
- **R12. Ràng buộc chiều chuyển nhãn** cho domain kiểu lifecycle (HubSpot forward-only [S3]). Chỉ làm nếu nghiệp vụ cần; mặc định để nhãn tính lại tự do.
- **R13. Crosswalk sang taxonomy ngoài** (Google/Shopify cho sản phẩm; chế độ kế toán cho GL) là thuộc tính của canonical code, không phải tenant rule. Chỉ làm khi có nhu cầu benchmark hoặc xuất dữ liệu.
- **R14. Canonical set cần một chính sách tiến hoá.** GA4 vẫn thêm kênh mới (AI Assistant) [S1], Shopify phát hành theo quý [S16]. Khi thêm code canonical mới, cần quy trình rà lại các tenant label đang neo `OTHER` để chuyển sang code mới.

### 8.3 Phương án triển khai engine (xếp hạng)

| Tiêu chí | **A. Mỗi domain một model dbt sinh từ macro chung; `entity_labels` là view UNION ALL** | B. Một model long table cho mọi domain | C. Rule engine ngoài (DMN/Python) |
|---|---|---|---|
| DAG giữa domain | dbt `ref()` lo; cycle bị dbt chặn | Phải tự chia tầng topo (nhiều pass hoặc giới hạn độ sâu) | Engine lo |
| Lineage / docs dbt | Rõ theo domain | Một nút to, mờ | Mất |
| Incremental, freeze theo domain | Cấu hình được theo từng model | Một cấu hình chung cho mọi domain | Tự làm |
| Test theo domain (unique, accepted_values theo hit policy) | Tự nhiên | Phải lọc theo domain trong test | Tự làm |
| DRY | Macro chung theo dạng rule + `hit_policy` | Cao nhất | Cao |
| Hiệu năng DuckDB ở quy mô SME | Tốt | Tốt | Thêm I/O ra vào warehouse |
| Rủi ro vận hành | Thấp | Trung bình (một lỗi luật làm hỏng mọi domain) | Cao (thêm runtime) |
| **Xếp hạng** | **1** | 2 | 3 |

Ghi chú cho phương án A: macro nhận `domain` và đọc định nghĩa domain (hit policy, cardinality, time semantics, feature model) từ một seed hoặc YAML lúc compile. Như vậy model là thứ được sinh ra, còn logic chung chỉ viết một lần. Việc đọc **dữ liệu luật** phải đi qua `ref()` tới bảng luật (join trong SQL), không qua `run_query` lúc compile, để tránh phụ thuộc ẩn. Đây cũng là nguyên tắc phase 4 đã ghi.

### 8.4 Schema tối thiểu đề xuất (chỉ hình dạng, không phải DDL)

- `taxonomy_domain(domain, subject, hit_policy, cardinality, time_semantics{as_of_event|current|scd2}, versioning{restate|freeze_after_close}, depends_on[])`
- `taxonomy_canonical(domain, code, parent_code, sort_order, name_vi, name_en, introduced_in, deprecated_in, replaced_by)`. Code dành riêng cho mọi domain: `UNMAPPED`, `UNKNOWN`, `NOT_APPLICABLE`, `OTHER`.
- `taxonomy_label(domain, label, label_std, display_name)` là lớp tenant. Ràng buộc: `label → label_std` là hàm (R4).
- `taxonomy_rule(rule_id, layer, domain, priority, conditions(feature, op, value)[], label, enabled, status, effective_from, author, note)`
- `taxonomy_override(subject, entity_id, domain, label, reason, created_by, created_at, expires_at)`
- `taxonomy_param(domain, name, value, period, ruleset_version)` cho điểm cắt percentile đã chốt (R9).
- Output `entity_labels(subject, entity_id, domain, label, label_std, rule_id, rule_version, ruleset_version, source_layer, as_of)`.

### 8.5 Rủi ro chính của chính thiết kế

1. **Phức tạp vượt nhu cầu.** Năm dạng rule × bốn lớp pack × hai trục thời gian × DAG là một rule engine thực thụ. Rủi ro lớn nhất là xây đủ engine trước khi có tenant thứ hai. Đề xuất giảm rủi ro: Đợt 4 chỉ triển khai `FIRST` + `UNIQUE` + `COLLECT`, hai lớp (product default + tenant), một chế độ versioning (restate). Industry pack, connector pack, `PRIORITY` và freeze chỉ bật khi có domain cần thật (GL là ứng viên đầu tiên cho freeze). Phần này là gợi ý; cắt scope là quyết định của user.
2. **Google Sheet làm nơi nhập luật** dễ có lỗi gõ, trùng `rule_id`, sai kiểu ngưỡng. Phải có bước validate schema (kiểu, toán tử hợp lệ, label đã khai báo, feature tồn tại) trước khi nạp. Nếu không, lỗi luật sẽ thành lỗi build dbt.
3. **Ngữ nghĩa nhãn trôi giữa các tenant.** Nếu `label_std` quá thô (vd. chỉ `B2B`/`B2C`) thì report chuẩn vô nghĩa; nếu quá mịn thì tenant không neo được. Cần chốt canonical set của từng domain bằng dữ liệu thật của ít nhất hai doanh nghiệp, không chỉ Fine Japan.
4. **Known divergences hiện tại** (CROSSBORDER ba định nghĩa, `'Active'`/`'ACTIVE'`, `lifecycle_stage` hai nghĩa) cho thấy chỉ "chuyển sang data" thì chưa đủ. Engine phải buộc mỗi khái niệm có **một domain, một định nghĩa**; các biến thể hiện có phải được thống nhất (có đổi số) hoặc tách thành domain khác tên.

---

## Hạn chế của nghiên cứu

- **Chưa đọc trực tiếp spec OMG DMN 1.5.** Mô tả hit policy lấy từ Camunda docs và Trisotech (Bruce Silver, thành viên nhóm soạn DMN), nên độ tin cậy cao nhưng là nguồn thứ cấp.
- **Chưa đối chiếu văn bản gốc TT 99/2025/TT-BTC** và tình trạng TT 133/2016. Đây là các chỗ ảnh hưởng trực tiếp tới canonical set của domain GL.
- **Giới hạn của GA4 custom channel group** (25 hay 50 kênh) và **thứ tự đánh giá rule chính thức** chưa kiểm được từ trang của Google.
- **Không truy cập được** tài liệu NRF/ARTS về danh sách kênh chuẩn (có thể không tồn tại) và DAMA-DMBOK (sách trả phí). Phần RDM dựa trên tài liệu vendor.
- **Không đánh giá hiệu năng thực tế** của macro sinh SQL trên DuckDB với dữ liệu Fine Japan. Cần một spike nhỏ khi triển khai.
- **HubSpot:** danh sách stage mặc định và **Klaviyo:** thang điểm RFM dựa trên hiểu biết sẵn có hoặc nguồn thứ cấp.

## Câu hỏi chưa giải quyết (cần user quyết)

1. Mặc định **restate** (áp luật hiện hành cho toàn bộ lịch sử) có chấp nhận được cho mọi domain ngoài GL không?
2. Domain nào là **multi-valued** (tag, discount type, có thể cả `product_affinity`)? Quy tắc chọn nhãn chính khi pivot ra cột mart là gì?
3. Ngưỡng percentile chốt theo **tháng** hay **quý**?
4. Canonical set của từng domain do ai chốt, và dựa trên dữ liệu của những doanh nghiệp nào ngoài Fine Japan?
5. Khách hàng SME đang dùng **TT 133** hay **TT 99**? Điều này quyết định canonical cho GL.

---

## Nguồn (truy cập 2026-10-14)

- [S1] Google Analytics Help: Default channel group. https://support.google.com/analytics/answer/9756891
- [S2] Tatvic: Custom channel grouping in GA4. https://www.tatvic.com/blog/custom-channel-grouping-in-ga4/ ; MeasureU: https://measureu.com/custom-channel-grouping-ga4 (thứ cấp)
- [S3] HubSpot Knowledge Base: Use lifecycle stages (cập nhật 06/01/2026). https://knowledge.hubspot.com/records/use-lifecycle-stages
- [S4] Salesforce Trailhead: Global picklists. https://trailhead.salesforce.com/content/learn/modules/picklist_admin/picklist_admin_global ; Salesforce Ben: https://www.salesforceben.com/bad-value-for-restricted-picklist-field/
- [S5] Camunda 7.22 docs: DMN Hit Policy. https://docs.camunda.org/manual/7.22/reference/dmn/decision-table/hit-policy
- [S6] Camunda 8 docs: Decision table hit policy. https://docs.camunda.io/docs/components/modeler/dmn/decision-table-hit-policy/
- [S7] Trisotech (Bruce Silver): DMN Hit Policy Explained. https://www.trisotech.com/dmn-hit-policy-explained/
- [S8] Jmix docs: Using DMN 1.3. https://docs.jmix.io/jmix/bpm/dmn-1-3.html
- [S9] XBRL International: ESEF rules, anchoring extensions. https://www.xbrl.org/guidance/esef-rules-anchoring-extensions/
- [S10] XBRL International: Wider/narrower anchoring in ESEF. https://www.xbrl.org/news/wider-narrower-anchoring-in-esef/ ; ESMA deck (FSMA): https://www.fsma.be/sites/default/files/public/content/ESEF/2018-10-10_esma.pdf
- [S11] Twilio Segment: Unify. https://www.twilio.com/docs/segment/unify ; Using Engage data: https://static0.twilio.com/docs/segment/engage/using-engage-data
- [S12] Bloomreach Engagement docs: Segmentations. https://documentation.bloomreach.com/engagement/docs/segmentations-1
- [S13] GS1 Netherlands: GPC in a nutshell (06/2024). https://www.gs1.nl/media/sfpiaxye/gpc-in-a-nutshell_jun24-def.pdf ; GS1 release notes 2020-06: https://www.gs1.org/sites/default/files/docs/release_notes_2020_06_publication_0.pdf
- [S14] Wikipedia: UNSPSC. https://en.wikipedia.org/wiki/UNSPSC ; GS1 Australia UNSPSC attribute: https://www.gs1au.org/services/data-and-content/national-product-catalogue/npc-data-dictionary/data-attribute/unspsc-code
- [S15] Google Merchant Center Help: Google product category. https://support.google.com/merchants/answer/6324436
- [S16] GitHub Shopify/product-taxonomy. https://github.com/Shopify/product-taxonomy
- [S17] Shopify dev changelog: Updates to Standard Product Taxonomy (10/2024). https://shopify.dev/changelog/updates-to-shopify-s-standard-product-taxonomy-october-2024
- [S18] Amazon SP-API: Get recommended browse nodes or item type keywords. https://developer-docs.amazon.com/sp-api/docs/get-recommended-browse-nodes-or-item-type-keywords
- [S19] dbt docs: Dimensions (MetricFlow). https://docs.getdbt.com/docs/build/dimensions
- [S20] Cube docs: Dimensions reference. https://docs.cube.dev/reference/data-modeling/dimensions
- [S21] Looker docs: Bucketing in Looker. https://docs.cloud.google.com/looker/docs/best-practices/how-to-bucket-data-in-looker
- [S22] OMG Retail: ARTS Operational Data Model. https://www.omg.org/retail/operational-data-model.htm ; ODM 7.3: https://www.omg.org/retail-depository/arts-odm-73/introduction_and_overview.htm
- [S23] Thông tư 200/2014/TT-BTC (vbpl.vn). https://vbpl.vn/FileData/TW/Lists/vbpq/Attachments/66801/VanBanGoc_200.2014.TT-BTC-1.pdf ; MISA AMIS: https://amis.misa.vn/24791/tai-khoan-ke-toan/
- [S24] KPMG Việt Nam: Thông tư 99/2025/TT-BTC. https://assets.kpmg.com/content/dam/kpmg/vn/pdf/2025/11/circular-99-vi.pdf ; LuatVietnam: https://luatvietnam.vn/bai-viet-lien-quan/thong-tu-200-92289.html
- [S25] Tally Help: Reconfigure the XBRL mapping. https://help.tallysolutions.com/article/te9rel49/XBRL/Reconfigure_the_XBRL_Mapping.htm
- [S26] Hyperbots glossary: XBRL IFRS reporting / IFRS taxonomy (vendor). https://www.hyperbots.com/glossary/xbrl-ifrs-reporting ; AccountingWEB: https://www.accountingweb.co.uk/business/financial-reporting/electronic-taxonomy-updated-for-ifrs
- [S27] Informatica Reference 360: Create a crosswalk. https://docs.informatica.com/master-data-management-cloud/reference-360-saas/current-version/reference-360/manage-crosswalks/step-1--create-a-crosswalk.html
- [S28] erwin DI Reference Data Management Guide. https://bookshelf.erwin.com/bookshelf/15.0DIBookshelf/Content/PDFs/erwin%20DI%20Reference%20Data%20Management%20Guide.pdf
- [S29] CluedIn: Reference Data Management. https://documentation.cluedin.net/reference-data-management
- [S30] AutomateDV: Effectivity satellites. https://automate-dv.readthedocs.io/en/v0.9.0/tutorial/tut_eff_satellites/
- [S31] datavault4dbt documentation. https://www.datavault4dbt.com/
- [S32] RudderStack Profiles: Data modeling. https://rudderstack.com/docs/profiles/data-modeling/ ; Overview: https://www.rudderstack.com/docs/profiles/overview
- [S33] Klaviyo Academy: Build retention strategies using RFM analysis. https://academy.klaviyo.com/en-us/quick-guides/build-impactful-retention-strategies-using-rfm-analysis
- [S34] Trackingplan: GA4 channel groups explained (thứ cấp). https://trackingplan.com/guides/ga4-channel-groups-explained ; Cardinal Path: https://cardinalpath.com/blog/understanding-channel-groupings-in-ga4
