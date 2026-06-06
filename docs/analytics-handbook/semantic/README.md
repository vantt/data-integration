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

---

## Blueprint Integration Standard (mandatory)

Mỗi blueprint **phải** khai báo scope ở đầu file theo 2 cách sau:

### 1. YAML Frontmatter (machine-readable)

```yaml
---
primary_scope: scope_retail          # scope_sales | scope_retail | scope_b2b | filter_has_cogs | filter_us | none
scope_indicator: "[Retail]"          # [All] | [Retail] | [B2B] | [Cross] | [US] | [Internal]
layer: L2                            # L1 | L1.5 | L2 | L3 | Internal
uses_concepts: [scope_retail, net_revenue, discount_rate, aov]
---
```

### 2. `## Segmentation Scope` Section (human-readable)

Ngay sau title, trước Collection section:

```markdown
## Segmentation Scope

> **Scope:** `scope_retail` · Layer 2 (Retail Operations) · Suffix `[Retail]`
> **Why:** Retail-specific metrics (AOV, discount, promo effectiveness). B2B discount = fixed wholesale price, not promotion.
> **Ref:** [segments.md#scope_retail](../semantic/segments.md#scope_retail)

All SQL in this blueprint: `WHERE scope_retail`. Do not re-derive as `customer_type = 'RETAIL' AND is_sales_channel = true AND status NOT IN (...)`.
```

### Scope assignment matrix

| Blueprint type | primary_scope | scope_indicator | Notes |
|---|---|---|---|
| Executive / CEO dashboards | `scope_sales` | `[All]` | Full business view |
| Finance P&L / profitability | `scope_sales` + `filter_has_cogs` | `[All]` | Add `AND has_cogs = true` for margin queries |
| Finance recon / accounting | `none` | `[All]` | MISA-based, no fact_orders scope |
| Sales / retail daily ops | `scope_retail` | `[Retail]` | AOV, promo, retention → always retail-only |
| Marketing / customer analysis | `scope_retail` | `[Retail]` | Marketing targets retail; B2B has no promo mechanics |
| B2B operations | `scope_b2b` | `[B2B]` | WHOLESALE + PARTNER |
| Cross-segment analytics | `scope_sales` | `[Cross]` | With explicit customer_type breakdown |
| US CrossBorder | `filter_us` | `[US]` | channel_name='US' ad-hoc filter |
| Infrastructure / ingestion | `none` | `[Internal]` | No order scope |

### Multi-scope dashboards (tab-level split)

Khi dashboard có nhiều tab với scope khác nhau, khai báo từng tab:

```markdown
## Segmentation Scope

> **Per-tab scope split:**
> - Tab [Retail]: `WHERE scope_retail`
> - Tab [B2B]: `WHERE scope_b2b`
>
> Do not mix scopes within a single query.
```

---

## Tham chiếu

- Domain context: `domains/`
- Report segmentation (WHY cần phân lớp): `guides/report_segmentation.md`
- Revenue terminology (WHY các tên gọi): `guides/revenue_terminology.md`
- dbt mart implementation: `transformation/models/marts/`
- Rill implementation: `rill/metrics/*.yaml`
