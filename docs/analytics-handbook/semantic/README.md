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

Mỗi blueprint **phải** có 2 thành phần:

### 1. YAML Frontmatter (machine-readable, dòng 1 của file)

```yaml
---
primary_scope: scope_retail          # scope_sales | scope_retail | scope_b2b | filter_has_cogs | filter_us | none
scope_indicator: "[Retail]"          # [All] | [Retail] | [B2B] | [Cross] | [US] | [Internal]
layer: L2                            # L1 | L1.5 | L2 | L3 | Internal
uses_concepts: [scope_retail, net_revenue, discount_rate, aov]
issues:                              # optional — known issues / todos discovered during build or review
  - "[warn] Card: <card_name> — <description>"
  - "[todo] Card: <card_name> — <description>"
---
```

`primary_scope`, `scope_indicator`, `layer`, `uses_concepts` được parse bởi `deploy_from_markdown.js`. Trường `issues` là metadata thuần — không ảnh hưởng deploy, chỉ dùng cho LLM và người review.

**`issues` severity tags:**

| Tag | Ý nghĩa |
|---|---|
| `[error]` | Logic sai, sinh ra số sai — phải fix trước khi dùng data |
| `[warn]` | Semantic ambiguity — cần xác nhận intent với business |
| `[info]` | Known limitation, chấp nhận được — ghi nhận để người đọc biết |
| `[todo]` | Cải tiến đã lên kế hoạch — không urgent, không blocking |

**Format mỗi issue:** `"[severity] Card: <tên card hoặc 'Dashboard-level'> — <mô tả ngắn gọn>"`

### 2. `## Semantic Contract` Section (LLM + human readable)

Ngay sau title, trước Collection section. Mục đích: **context đầy đủ cho LLM khi đọc/viết SQL trong blueprint này** — không cần đọc thêm file nào khác để biết dùng concept gì.

```markdown
## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md) — segments, metrics, dimensions, rules, freshness.
> **Scope:** `scope_retail` · Layer 2 `[Retail]` · [`segments.md#scope_retail`](../semantic/segments.md#scope_retail)
> **Why:** Retail-specific metrics (AOV, discount, promo). B2B discount = fixed wholesale price — mixing distorts all KPIs.
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`net_revenue`](../semantic/metrics.md#net_revenue) · [`aov`](../semantic/metrics.md#aov) · [`discount_rate`](../semantic/metrics.md#discount_rate)

All SQL: `WHERE scope_retail`. Do not re-derive as `customer_type = 'RETAIL' AND is_sales_channel = true AND status NOT IN (...)`.
```

#### Concept → file mapping (cho LLM tự resolve link)

| Concept prefix / name | File |
|---|---|
| `scope_*`, `filter_*` | [`segments.md`](segments.md) |
| `net_revenue`, `gross_revenue`, `total_collected`, `gross_profit`, `aov`, `discount_rate`, `orders_count`, `cogs_amount`, `return_rate`, `channel_net_profit`, và các metric khác | [`metrics.md`](metrics.md) |
| `channel_name`, `channel_category`, `channel_format`, `customer_type`, `platform`, `order_status`, `fulfillment_status`, và các dimension khác | [`dimensions.md`](dimensions.md) |
| `Order`, `Customer`, `Channel`, `Product`, `OrderEconomics`, và các entity khác | [`entities.md`](entities.md) |
| VAT, COGS sourcing, promo goods, Shopee fee, overhead alloc | [`rules.md`](rules.md) |
| Freshness SLA per mart | [`freshness.md`](freshness.md) |

### Multi-scope dashboards (tab-level split)

```markdown
## Semantic Contract

> **Semantic layer:** [`semantic/README.md`](../semantic/README.md)
> **Scope:** Per-tab split · Layer 2
>
> | Tab | Scope | SQL |
> |---|---|---|
> | [Retail] | `scope_retail` | `WHERE scope_retail` |
> | [B2B] | `scope_b2b` | `WHERE scope_b2b` |
>
> **Concepts used:**
> [`scope_retail`](../semantic/segments.md#scope_retail) · [`scope_b2b`](../semantic/segments.md#scope_b2b) · [`net_revenue`](../semantic/metrics.md#net_revenue)

Do not mix scopes within a single query.
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

---

## Tham chiếu

- Domain context: `domains/`
- Report segmentation (WHY cần phân lớp): `guides/report_segmentation.md`
- Revenue terminology (WHY các tên gọi): `guides/revenue_terminology.md`
- dbt mart implementation: `transformation/models/marts/`
- Rill implementation: `rill/metrics/*.yaml`
