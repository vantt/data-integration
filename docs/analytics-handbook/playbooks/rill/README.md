# Rill Playbooks

Playbooks for Rill explores and dashboards, following the 3-layer architecture.

## Structure

| File | Layer | Scope | Audience |
|------|-------|-------|----------|
| `orders_executive.md` | 1 - Executive | scope_sales [All] | CEO, Directors |
| `orders_retail_ops.md` | 2 - Operational | scope_retail [Retail] | Sales Ops, Store Managers |
| `orders_b2b_ops.md` | 2 - Operational | scope_b2b [B2B] | B2B Sales, Partners |
| `sales_items_product.md` | 2 - Operational | scope_retail [Retail] | Product Team |

## 3-Layer Architecture

```
Layer 1: Executive [All]
├── Filter: scope_sales = true
├── View: Business overview
└── Audience: C-level, Directors

Layer 2: Operational
├── Retail [Retail]
│   ├── Filter: scope_retail = true
│   └── Audience: Sales, Marketing, CS
└── B2B [B2B]
    ├── Filter: scope_b2b = true
    └── Audience: B2B Sales, Partners

Layer 3: Analytics [Cross]
├── Filter: Explicit per-analysis
└── Audience: Data Team, Analysts
```

## Playbook Template

```markdown
# Playbook: [Explore Title]

## Overview
- **Metrics View:** `[metrics_view_name]`
- **Layer:** [1-Executive / 2-Retail / 2-B2B / 3-Analytics]
- **Scope Filter:** `scope_[sales/retail/b2b] = true`
- **Audience:** [Who uses this]
- **Goal:** [What questions does it answer]

## Default Configuration

### Time Range
- Default: [Last 7 days / Last 30 days / etc.]

### Pre-applied Filters
- `scope_xxx = true` (required for this layer)
- [Other default filters]

### Recommended Dimensions
| Priority | Dimension | Use Case |
|----------|-----------|----------|
| Primary | ... | ... |
| Secondary | ... | ... |

### Key Measures
| Measure | Domain Reference |
|---------|------------------|
| ... | domains/sales.md#... |

## Use Cases

### [Use Case 1]
1. Filter by...
2. Group by...
3. Look for...

## Related
- **Domain:** [Link to domain file]
- **Metabase Playbook:** [Link if exists]
- **Blueprint:** [Link to Rill blueprint]
```

## Cross-Reference

| Rill Explore | Metabase Equivalent |
|--------------|---------------------|
| Orders Executive | CEO Weekly Pulse, Order Profitability |
| Orders Retail Ops | Daily Sales [Retail], Sales Ops Weekly |
| Orders B2B Ops | B2B Daily Sales, B2B Orders Tracking |
| Sales Items Product | Product Performance |

