# Dashboard Design Patterns

## 🎨 Design Philosophy

- **Standardization**: All dashboards should follow a consistent layout grid.
- **Top-Down Flow**: Scalar KPIs (Headlines) -> Trend Analysis (Context) -> Actionable Details (Drill-down).
- **Less is More**: Avoid cluttering. Max 6-8 main visual elements per dashboard.

## 🏢 Executive Dashboard Layout

**Purpose**: High-level strategic overview for C-Suite and Directors. Focus on "Traffic light" indicators and YoY trends.

```
┌─────────────────────────────────────────────────────────────┐
│                    EXECUTIVE DASHBOARD                       │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Revenue      │ Orders       │ AOV          │ Customers     │
│ $1.2M (+15%) │ 15,234 (+8%) │ $79 (+6%)    │ 8,901 (+12%)  │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Revenue Trend (Last 30 Days)                    │    │
│  │     [Line Chart: Daily Revenue]                     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ Top Products        │  │ Channel Performance        │   │
│  │ [Table]             │  │ [Pie Chart]                │   │
│  └─────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Customer Segments (RFM)                              │   │
│  │ [Scatter Plot]                                       │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## ⚙️ Operations Dashboard Layout

**Purpose**: Real-time monitoring for Managers and Staff. Focus on queues, bottlenecks, and today's status.

```
┌─────────────────────────────────────────────────────────────┐
│                   OPERATIONS DASHBOARD                       │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ Pending      │ Processing   │ Shipped      │ Avg Delivery  │
│ 234 orders   │ 156 orders   │ 89 today     │ 2.3 days      │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Order Status Funnel                             │    │
│  │     [Funnel Chart]                                  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ Fulfillment Queue   │  │ Shipping Performance       │   │
│  │ [Table: Priority]   │  │ [Bar Chart: Carriers]      │   │
│  └─────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Inventory Alerts                                     │   │
│  │ [Table: Low Stock, Out of Stock]                     │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

## 📢 Marketing Dashboard Layout

**Purpose**: Campaign effectiveness and customer acquisition tracking.

```
┌─────────────────────────────────────────────────────────────┐
│                   MARKETING DASHBOARD                        │
├──────────────┬──────────────┬──────────────┬───────────────┤
│ CAC          │ CLV          │ ROAS         │ Conv Rate     │
│ $45          │ $450         │ 3.2x         │ 2.3%          │
├──────────────┴──────────────┴──────────────┴───────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Customer Acquisition Trend                      │    │
│  │     [Stacked Bar: New vs Returning]                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────┐  ┌───────────────────────────┐   │
│  │ Campaign ROI        │  │ Channel Attribution        │   │
│  │ [Table]             │  │ [Sankey Diagram]           │   │
│  └─────────────────────┘  └───────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Cohort Retention                                     │   │
│  │ [Heatmap]                                            │   │
│  └─────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```
