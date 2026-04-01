# Playbook: [Dashboard Title]

## Overview

- **Audience:** [Ai đọc dashboard này, role gì]
- **Goal:** [Dashboard trả lời câu hỏi gì — 1 dòng]
- **Cadence:** [Frequency + timing, e.g., "Weekly, Monday morning"]
- **Archetype:** [Executive Pulse / Operational Cockpit / Exploratory Tool]
- **Metabase Collection:** `[Collection Path from registry]`
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

## How to Read

1. **Nhìn đâu trước:** [e.g., "Start with Hero metric at top-left"]
2. **Flow đọc:** [e.g., "Top → check status, Middle → trend direction, Bottom → breakdowns"]
3. **Actions:** Khi thấy [signal X] → [hành động Y]

## Implementation Notes

- [e.g., Max 10 visual elements, keep glanceable]
- [e.g., Auto-subscription recommended for this audience]
