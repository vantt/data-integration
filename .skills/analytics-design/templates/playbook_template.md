# Playbook: [Dashboard Title]

> **Tài liệu này mô tả mục đích và cách sử dụng dashboard/report từ góc nhìn người dùng nghiệp vụ.**
> Nó giải thích dashboard dành cho ai, dùng để trả lời câu hỏi nào, cần đọc theo luồng nào, dùng những metric nào từ domain documents, và khi thấy tín hiệu bất thường thì ai cần làm gì.
> Playbook không định nghĩa công thức tính metric; mọi logic nghiệp vụ phải được tham chiếu từ `domains/`.

## Overview

- **Audience:** [Ai đọc dashboard này, role gì]
- **Goal:** [Dashboard trả lời câu hỏi gì — 1 dòng]
- **Cadence:** [Frequency + timing, e.g., "Weekly, Monday morning"]
- **Archetype:** [Executive Pulse / Operational Cockpit / Exploratory Tool]
- **Tool:** [metabase | rill | evidence] ← ops/fixed layout → metabase; ad-hoc explore → rill; report/shareable/executive → evidence
- **Collection:** `[Collection Path]`
- **Blueprint:** [`name`](../blueprints/[tool]/name.md)
- **Design Spec:** [`design`](../designs/design.md)
- **Domain References:** [`domain`](../domains/domain.md)

## Key Questions

1. [Câu hỏi chính dashboard trả lời]
2. [Câu hỏi phụ #2]
3. [Câu hỏi phụ #3]

## Filters

- **Date Range:** [Default, e.g., "Last 7 days"]
- **Dimensions:** [e.g., Channel, Region — hoặc "None" cho Pulse]

## Data Lineage

- **Core Models:** [`fact_orders`](../../transformation/models/path), [`dim_channels`](path)
- **Key Dimensions:** [channel_category, order_date, ...]
- **Key Measures:** [Net Revenue](../domains/sales.md#net-revenue), [Total Orders](../domains/sales.md#total-orders)

## Visualizations

### Section 1: [Section Title — specific, descriptive]

| Chart Title | Visualization Type | Metric Reference | Notes |
|-------------|-------------------|------------------|-------|
| [e.g., Revenue Trend] | [e.g., line-chart] | [Net Revenue](../domains/sales.md#net-revenue) | [e.g., 14-day trend, WoW comparison] |

### Section 2: [Section Title]

| Chart Title | Visualization Type | Metric Reference | Notes |
|-------------|-------------------|------------------|-------|
| ... | ... | ... | ... |

## Action Triggers

> Mỗi metric chính PHẢI có ít nhất 1 threshold + owner + action.
> Bảng này biến dashboard từ "giải thích tình hình" thành "thôi thúc hành động".

| Signal | Threshold | Severity | Owner | Immediate Action | Follow-up |
|--------|-----------|----------|-------|-----------------|-----------|
| [e.g., Revenue drop WoW] | [e.g., > -10%] | [Warning / Critical] | [Role] | [Action ngay — 1 câu] | [Điều tra / escalation] |
| [e.g., Churn spike] | [e.g., > 5% monthly] | [Warning / Critical] | [Role] | [Action ngay] | [Follow-up] |

## Reading Flow

> Mô tả đường đi của người đọc từ Hero → Investigation → Escalation.
> Dùng card names cụ thể, không chung chung.

1. **Bắt đầu:** Nhìn [Hero Card Name] — trả lời "[câu hỏi chính]"
2. **Nếu** [condition, e.g., Revenue giảm > 10%] → chuyển sang [Tab/Card Name] để xem breakdown
3. **Nếu** [condition, e.g., vấn đề ở 1 kênh cụ thể] → escalate cho [Owner] với context từ [Card Name]
4. **Nếu** bình thường → scan [Supporting Cards] rồi đóng dashboard

## How to Read

> Follow the **Context → Key Finding → Evidence → Implications → Actions** flow.
> Xem `COMPOSITION_PATTERNS.md` Section 8b cho chi tiết.

1. **Context:** [Tại sao dashboard này tồn tại — 1 câu]
2. **Key Finding:** [Nhìn đâu trước — Hero metric cho biết điều gì]
3. **Evidence:** [Trend/Breakdown nào support — "scroll xuống section X để xem"]
4. **Implications:** [Nếu số liệu thế này → business impact gì]
5. **Actions:** Khi thấy [signal X] → [hành động Y]

## Key Insights

> Dùng format **"What / So What / Now What"** cho mỗi insight quan trọng.
> Xem `COMPOSITION_PATTERNS.md` Section 8a cho template.

### Insight 1: [Headline — action-oriented finding]

- **What:** [Phát hiện — 1 câu mô tả sự thật từ data]
- **So What:** [Tại sao quan trọng — impact lên business]
- **Now What:** [Hành động đề xuất — next step cụ thể]

### Insight 2: [Headline]

- **What:** [...]
- **So What:** [...]
- **Now What:** [...]

## Implementation Notes

- [e.g., Max 10 visual elements, keep glanceable]
- [e.g., Auto-subscription recommended for this audience]
