# Domain Modeling

> Cách định nghĩa business domains, metrics, và formulas cho analytics handbook.

## Domain Organization

Mỗi business domain là **một file Markdown** trong `docs/analytics-handbook/domains/`. Mỗi file chứa toàn bộ metrics của domain đó, được nhóm thành các **Contexts** (logical groupings).

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

Mỗi Context nhóm các metrics liên quan trong cùng một domain. Format bắt buộc:

```markdown
## Context: <Tên Context>

> **Description:** Mô tả ngắn scope của context này.
> **dbt Source:** `<schema.table>` hoặc `<model_name>`
> **Grain:** Per Order | Per Customer | Per Day | ...
```

- **Description**: 1 dòng, giải thích scope.
- **dbt Source**: dbt model chính cung cấp dữ liệu cho context này.
- **Grain**: Granularity — mỗi row trong source table đại diện cho gì.

Một domain có thể có nhiều Contexts. Ví dụ `sales.md` có: Order Performance, Operational Trends, Product Performance, Payment Operations, Promotions & Discounts, Sales Targets.

## Metric Definition Standard

Mỗi metric phải có đầy đủ các trường sau:

| Trường | Bắt buộc | Mô tả |
|---|---|---|
| **Name** | Yes | Tiếng Việt + English. Ví dụ: "Doanh thu thuần (Net Revenue)" |
| **Business Definition** | Yes | 1 dòng, ngôn ngữ business, không dùng thuật ngữ kỹ thuật. Tiếng Việt ưu tiên. |
| **Formula** | Yes | SQL expression — aggregation hoặc calculation |
| **Unit** | Yes | VND, %, count, days, score, ratio, etc. |
| **Source** | Yes | dbt model hoặc table reference |

### Format mẫu

```markdown
### 1. Doanh thu thuần (Net Revenue)

> **dbt Source:** `marts.sales.fact_orders`

- **Business Definition:** Số tiền khách trả cho hàng hóa sau chiết khấu, trước thuế. Con số quan trọng nhất cho phân tích kinh doanh.
- **Formula:**
  ```sql
  SUM(net_revenue)
  ```
- **Unit:** VND
- **Status:** `active`
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

> **Owner:** <Team / Role>
> **Update Frequency:** <Real-time / Daily / Weekly / Monthly>

## Context: <Context Name>

> **Description:** <Mô tả scope>
> **dbt Source:** `<model_name>`
> **Grain:** <Per X>

### 1. <Metric Name (Vietnamese + English)>

> **dbt Source:** `<schema.table>`

- **Business Definition:** <1 dòng, plain language>
- **Formula:**
  ```sql
  <SQL expression>
  ```
- **Unit:** <VND | % | count | ...>
```

## Checklist khi thêm/sửa metric

1. Metric đã tồn tại trong domain khác chưa? → Nếu có, reference thay vì copy.
2. Business Definition rõ ràng cho non-technical stakeholder?
3. Formula đúng SQL syntax, dùng tên column từ dbt model?
4. Unit được ghi rõ?
5. dbt Source reference đúng model đang active?
6. Status = `planned` nếu dbt model chưa deploy?
7. Metric relationships (chain, leading/lagging) đã document?
