# Domain Modeling

> Cách định nghĩa business domains, metrics, và formulas cho analytics handbook.

## Domain Organization

Mỗi business domain là **một file Markdown** trong `docs/analytics-handbook/domains/`. Mỗi file chứa toàn bộ metrics của domain đó, được nhóm thành các **Contexts** (logical groupings).

Mỗi domain file mới phải đặt định nghĩa tài liệu này ngay sau H1 title:

```markdown
> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.
```

| Domain file | Phạm vi |
|---|---|
| `sales.md` | Revenue, orders, targets, promotions, channels |
| `customer.md` | Acquisition, retention, lifetime value, segmentation |
| `logistics.md` | Fulfillment, shipping, delivery performance |
| `finance.md` | Cash flow, P&L, payment reconciliation |
| `product.md` | Inventory, product performance, category analysis |
| `customer_support.md` | Tickets, response time, social commerce ops |

**Naming convention:** `lowercase_with_underscores.md`. Một domain = một file. Không tạo thư mục con.

## Context Structure

Mỗi Context nhóm một lát cắt nghiệp vụ trong domain. Cấu trúc chuẩn của mỗi context:

1. **Context Overview** — bảng tổng quan category → câu hỏi phân tích nền tảng → metric liên quan → data đã sẵn sàng → phần cần bổ sung.
2. **Analytical Questions** — đi qua từng câu hỏi, định nghĩa câu hỏi, trình bày bản chất nghiệp vụ, giải thích lý do cần hỏi, nêu lợi hại/giới hạn, và insight/action có thể kích hoạt.
3. **Metrics** — sau khi câu hỏi đã rõ, định nghĩa từng metric dùng để trả lời các câu hỏi đó.

Format bắt buộc:

```markdown
## Context: <Context Name>

> **Description:** Mô tả ngắn scope của context này và khi nào dùng.
> **dbt Source:** `<schema.table>` hoặc `<model_name>`
> **Grain:** Per Order | Per Customer | Per Day | ...

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| Revenue Quality | Doanh thu đang tăng vì volume hay value? | Net Revenue, Order Count, AOV | `fact_orders.net_revenue`, `fact_orders.order_id` | Target table |

### Analytical Questions

#### Q1. <Question Name>

- **Question:** <Câu hỏi phân tích nền tảng>
- **Definition:** <Câu hỏi này quan sát điều gì trong nghiệp vụ>
- **Nature:** <Bản chất: leading/lagging, volume/value/quality, operational/strategic, etc.>
- **Why It Matters:** <Vì sao câu hỏi này quan trọng>
- **Tradeoffs / Caveats:** <Lợi hại, giới hạn, khi nào dễ đọc sai>
- **Insight / Action Enabled:** <Insight/action có thể kích hoạt>
- **Related Metrics:** <Metric A>, <Metric B>

### Metrics

#### 1. <Metric Name>

> **dbt Source:** `<schema.table>`

- **Business Definition:** <Định nghĩa sâu về nghiệp vụ, phạm vi tính, điều kiện loại trừ, và cách metric đại diện cho thực tế business>
- **Business Logic:** <Logic tính toán bằng ngôn ngữ nghiệp vụ: grain, numerator/denominator, filters, dedup, time basis>
- **Formula:** <Công thức business/math ngắn gọn, ví dụ Net Revenue = Gross Revenue - Discounts>
- **Logic (SQL):**
  ```sql
  <SQL expression>
  ```
- **Unit:** <VND | % | count | ...>
- **Common Misunderstandings:** <Những hiểu lầm/sai lầm thường gặp>
- **Pitfalls / Edge Cases:** <Trường hợp dễ query/report sai>
```

- **Description**: 1 dòng, giải thích scope.
- **dbt Source**: dbt model chính cung cấp dữ liệu cho context này.
- **Grain**: Granularity — mỗi row trong source table đại diện cho gì.
- **Context Overview**: bảng scan nhanh, giúp reader biết context này trả lời nhóm câu hỏi nào và data đã đủ đến đâu.
- **Analytical Questions**: phần giải thích business meaning trước khi đi vào metric; câu hỏi phải đủ rõ để người đọc hiểu vì sao metric tồn tại.
- **Metrics**: phần định nghĩa đo lường, đặt sau khi câu hỏi phân tích đã được trình bày.

Một domain có thể có nhiều Contexts. Ví dụ `sales.md` có: Order Performance, Operational Trends, Product Performance, Payment Operations, Promotions & Discounts, Sales Targets.

## Metric Definition Standard

Mỗi metric phải có đầy đủ các trường sau. `Business Definition` cần giải thích sâu ý nghĩa nghiệp vụ và ranh giới đo lường, không chỉ tóm tắt bằng một câu ngắn.

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| **Name** | Yes | Tiếng Việt + English. Ví dụ: "Doanh thu thuần (Net Revenue)" |
| **Business Definition** | Yes | Định nghĩa sâu bằng ngôn ngữ business: metric đại diện cho điều gì, scope tính, điều kiện loại trừ, và vì sao cách đo này đúng với nghiệp vụ. |
| **Business Logic** | Yes | Logic tính toán trước khi viết SQL: grain, numerator/denominator, filters, dedup rule, time basis, source-of-truth timestamp nếu có. |
| **Formula** | Yes | Công thức business/math ngắn gọn, giúp người đọc hiểu quan hệ tính toán trước khi xem SQL. |
| **Logic (SQL)** | Yes | SQL expression — aggregation hoặc calculation. SQL phải phản ánh đúng Formula và Business Logic. |
| **Unit** | Yes | VND, %, count, days, score, ratio, etc. |
| **Source** | Yes | dbt model hoặc table reference |
| **Common Misunderstandings** | Yes | Các hiểu lầm/sai lầm thường gặp khi dùng metric. |
| **Pitfalls / Edge Cases** | Recommended | Các trường hợp dễ query/report sai, ví dụ duplicate grain, canceled orders, missing timestamps, null handling. |

### Format mẫu

```markdown
### 1. Doanh thu thuần (Net Revenue)

> **dbt Source:** `marts.sales.fact_orders`

- **Business Definition:** Số tiền ghi nhận từ đơn bán hợp lệ sau khi trừ chiết khấu, dùng để phản ánh sức bán thực tế của hàng hóa trong phạm vi sales. Metric này không đại diện cho tiền mặt đã thu nếu còn COD/chưa đối soát, và không bao gồm đơn hủy/voided.
- **Business Logic:** Tính trên grain đơn hàng hoặc dòng đơn hàng đã dedup. Chỉ lấy order hợp lệ, loại trạng thái hủy/voided, dùng `modified_on` hoặc order timestamp chuẩn theo model. Tổng hợp `net_revenue` sau discount theo kỳ phân tích.
- **Formula:** Net Revenue = Gross Revenue - Discounts
- **Logic (SQL):**
  ```sql
  SUM(net_revenue)
  ```
- **Unit:** VND
- **Status:** `active`
- **Common Misunderstandings:** Nhầm Net Revenue với GMV/Gross Revenue; tính cả đơn hủy; dùng payment collected thay cho sales revenue.
- **Pitfalls / Edge Cases:** Sai grain khi join order items làm nhân đôi doanh thu; dùng ngày ingest thay vì ngày đơn hàng; không `COALESCE` discount/tax nullable.
```

### dbt Model Reference Pattern

Dùng blockquote style thống nhất trong toàn bộ handbook:

```markdown
> **dbt Source:** `marts.sales.fact_orders`
```

Khi cần link tới file SQL thực tế:

```markdown
> **dbt Model:** [`fact_orders`](../../../transformation/models/marts/sales/fact_orders.sql)
```

## Metric Status Lifecycle

Mỗi metric có một trong ba trạng thái:

| Status | Ý nghĩa | Khi nào dùng |
|---|---|---|
| `active` | Metric có dbt model/table, sẵn sàng query | **Default** — không cần ghi nếu active |
| `planned` | Metric đã định nghĩa nhưng data source chưa tồn tại | dbt model chưa được build |
| `deprecated` | Metric không còn dùng, giữ lại cho reference | Khi business logic thay đổi |

**Transition rules:**

```
planned ──→ active       Khi dbt model đã deploy và có data.
                         Engineer cập nhật status.

active ──→ deprecated    Khi metric bị thay thế hoặc business không dùng nữa.
                         Ghi note lý do và metric thay thế (nếu có).
```

**Convention:** Nếu metric là `active` (default), KHÔNG cần ghi `Status` field. Chỉ ghi khi `planned` hoặc `deprecated`.

## No-Duplicate Rule

**KHÔNG copy metric definition sang domain khác.** Nếu metric đã tồn tại trong một domain, các domain khác phải **tham chiếu** (reference) thay vì sao chép.

Pattern tham chiếu:

```markdown
### AOV (Average Order Value)

> Xem định nghĩa tại [Sales Domain — AOV](sales.md#5-aov-average-order-value)
```

Ngoại lệ duy nhất: Khi metric cần **business definition khác** cho domain khác (ví dụ: "Revenue" trong Sales domain vs "Revenue" trong Finance domain có thể khác nhau về scope). Trong trường hợp này, ghi rõ sự khác biệt.

## Metric Relationships

Ghi rõ mối quan hệ giữa các metrics để giúp analyst hiểu data flow.

### Leading vs Lagging

| Loại | Ý nghĩa | Ví dụ |
|---|---|---|
| **Leading** (Chỉ báo sớm) | Dự đoán kết quả tương lai | Order Count, New Customers, Traffic |
| **Lagging** (Chỉ báo trễ) | Đo kết quả đã xảy ra | Net Revenue, CLV, Churn Rate |

### Absolute vs Relative

| Loại | Ý nghĩa | Ví dụ |
|---|---|---|
| **Absolute** | Giá trị thô, đo lường trực tiếp | Net Revenue (VND), Order Count |
| **Relative** | Tỷ lệ, so sánh, normalized | AOV, Return Rate (%), YoY Growth |

### Metric Chain (Chuỗi metric)

Khi các metrics có quan hệ tính toán, ghi rõ chuỗi:

```
Gross Revenue (GMV)
  └─ minus Discounts
      └─ = Net Revenue
          └─ plus Tax (VAT)
              └─ = Total Collected
```

```
Net Revenue ÷ Total Orders = AOV
```

Document chuỗi này trong domain file, tại Context chứa metric gốc.

## When to Split Domains vs Add Contexts

### Thêm Context mới vào domain hiện tại khi:

- Metrics cùng **business owner** (cùng team chịu trách nhiệm)
- Metrics dùng chung **data source chính** (cùng fact table)
- Metrics phục vụ cùng **business process** (sales pipeline, customer journey)

### Tạo domain mới khi:

- **Business owner khác hẳn** (Marketing vs Finance vs Ops)
- **Data source hoàn toàn khác** (fact table riêng, schema riêng)
- File domain hiện tại **>300 dòng** — cân nhắc tách sub-domain
- **Terminology conflict** — cùng tên metric nhưng ý nghĩa khác (ví dụ: "Revenue" trong Sales vs Finance)

### Ví dụ quyết định

| Tình huống | Quyết định | Lý do |
|---|---|---|
| Thêm "Shipping Cost" metrics | Context mới trong `logistics.md` | Cùng owner (Ops), cùng fulfillment data |
| Thêm "Social Commerce" metrics | Domain mới `customer_support.md` | Owner khác (CS team), data source riêng |
| Thêm "Product Return" metrics | Context mới trong `sales.md` | Dùng chung `fact_orders`, cùng sales process |

## Domain File Template

Khi tạo domain mới, dùng template: `templates/domain_template.md`

Cấu trúc tối thiểu:

```markdown
# <Domain Name> Domain

> **Domain Document định nghĩa cách một nhóm nghiệp vụ được hiểu và đo lường trong hệ thống analytics.**
> Tài liệu này xác định phạm vi domain, các câu hỏi phân tích nền tảng, các metric liên quan, cùng định nghĩa nghiệp vụ và logic tính toán chuẩn cho từng metric.
> Đây là nguồn tham chiếu chính thức cho business logic; dashboard, playbook, design spec và blueprint phải tham chiếu lại tài liệu này thay vì tự định nghĩa lại metric.

> **Owner:** <Team / Role>
> **Update Frequency:** <Real-time / Daily / Weekly / Monthly>

## Context: <Context Name>

> **Description:** <Mô tả scope>
> **dbt Source:** `<model_name>`
> **Grain:** <Per X>

### Context Overview

| Category | Foundational Analytical Questions | Related Metrics | Data Ready | Needs Added |
|----------|-----------------------------------|-----------------|------------|-------------|
| <Category> | <Question 1; Question 2> | <Metric A>, <Metric B> | <Model/field/table available> | <Missing model/field/business input> |

### Analytical Questions

#### Q1. <Question Name>

- **Question:** <Câu hỏi phân tích nền tảng>
- **Definition:** <Câu hỏi này quan sát điều gì trong nghiệp vụ>
- **Nature:** <Bản chất vấn đề: leading/lagging, volume/value/quality, operational/strategic>
- **Why It Matters:** <Vì sao quan trọng>
- **Tradeoffs / Caveats:** <Lợi hại, giới hạn, khi nào dễ đọc sai>
- **Insight / Action Enabled:** <Insight/action có thể có từ câu hỏi>
- **Related Metrics:** <Metric A>, <Metric B>

### Metrics

#### 1. <Metric Name (Vietnamese + English)>

> **dbt Source:** `<schema.table>`

- **Business Definition:** <Định nghĩa sâu về nghiệp vụ, phạm vi tính, điều kiện loại trừ, và ý nghĩa business>
- **Business Logic:** <Logic tính toán bằng ngôn ngữ nghiệp vụ trước khi viết SQL>
- **Formula:** <Công thức business/math ngắn gọn>
- **Logic (SQL):**
  ```sql
  <SQL expression>
  ```
- **Unit:** <VND | % | count | ...>
- **Common Misunderstandings:** <Hiểu lầm/sai lầm thường gặp>
- **Pitfalls / Edge Cases:** <Trường hợp dễ query/report sai>
```

## Checklist khi thêm/sửa metric

1. Context đã có bảng `Context Overview` với category, foundational analytical questions, related metrics, data ready, needs added?
2. Mỗi câu hỏi nền tảng đã có Definition, Nature, Why It Matters, Tradeoffs / Caveats, Insight / Action Enabled?
3. Metric đã tồn tại trong domain khác chưa? → Nếu có, reference thay vì copy.
4. Business Definition đủ sâu cho non-technical stakeholder, không chỉ là 1 câu ngắn?
5. Business Logic đã nêu rõ grain, filters, numerator/denominator, dedup/time basis nếu có?
6. Formula thể hiện đúng quan hệ tính toán ở mức business/math?
7. Logic (SQL) đúng SQL syntax, dùng tên column từ dbt model, và phản ánh đúng Formula + Business Logic?
8. Unit được ghi rõ?
9. dbt Source reference đúng model đang active?
10. Status = `planned` nếu dbt model chưa deploy?
11. Common Misunderstandings và Pitfalls / Edge Cases đã document?
12. Metric relationships (chain, leading/lagging) đã document?
