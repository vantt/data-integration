# Semantic Layer

Tầng trung gian giữa **domain** (WHY) và **implementation** (HOW).

## Vai trò trong chuỗi

```
Domain (WHY)          domains/*.md
    ↓ drives
Semantic (WHAT)       semantic/*.md        ← tầng này
    ↓ constrains
Implementation (HOW)  mart columns, Rill YAML, blueprint SQL
```

- **Domain** định nghĩa bối cảnh kinh doanh, câu hỏi phân tích, lý do đo lường.
- **Semantic** formalize domain decision thành definition chuẩn, machine-readable.
- **Implementation** dùng semantic definitions — không tự re-derive.

Domain drives semantic, không phải ngược lại. Khi semantic gặp ambiguity → đẩy ngược lên domain để clarify, không tự quyết.

---

## Cấu trúc

| File | Nội dung |
|---|---|
| `segments.md` | Scope/segment concepts: scope_retail, scope_b2b, scope_sales |
| `metrics.md` | Metric formulas: net_revenue, gross_revenue, AOV, orders_count |
| `dimensions.md` | Dimension definitions: channel_name, customer_type, platform |
| `entities.md` | Business entities: order, customer, product, channel |
| `rules.md` | Cross-cutting business rules: VAT treatment, cancellation convention |
| `freshness.md` | Data SLA per mart table |

---

## Format chuẩn cho mỗi concept

```markdown
## concept_name

> **Type:** Segment/Metric/Dimension | **Domain:** [link] | **Since:** YYYY-MM-DD

**Definition:** [one-line business definition]

**Rule / Formula:**
```sql
-- mart column nếu là pre-computed
expression hoặc filter SQL
```

**Intent:** [tại sao concept này tồn tại]

**Use in SQL:** `WHERE scope_retail` hoặc `SUM(net_revenue)` — không re-derive.
```

---

## Quy tắc governance

**Thêm concept mới:**
1. Domain team xác nhận business rule
2. Thêm definition vào file semantic tương ứng
3. Implement column trong dbt mart (nếu là pre-computed)
4. Update Rill YAML nếu cần
5. Blueprint dùng column — không viết lại rule trong SQL

**Sửa concept:**
1. Sửa definition trong semantic file
2. Sửa dbt mart → rebuild
3. Không cần sửa blueprint SQL (vì blueprint dùng column, không re-derive)

**Blueprint khai báo usage (mandatory):**
```yaml
---
uses_concepts: [scope_retail, net_revenue]
---
```

---

## Tham chiếu

- Domain context: `domains/`
- Report segmentation (WHY cần phân lớp): `guides/report_segmentation.md`
- Revenue terminology (WHY các tên gọi): `guides/revenue_terminology.md`
- dbt mart implementation: `transformation/models/marts/`
- Rill implementation: `rill/metrics/*.yaml`
