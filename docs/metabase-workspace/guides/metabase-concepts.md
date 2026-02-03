# Metabase Concepts Guide

## Overview

This guide explains key Metabase concepts to help you build effective analytics.

## Core Concepts

### 1. Collections
- **What**: Folders to organize your analytics content
- **Why**: Keep dashboards, questions, and models organized by domain or team
- **Best Practice**: Create one collection per business domain (Sales, Finance, etc.)

### 2. Models
- **What**: Curated datasets that serve as the foundation for questions
- **Why**: Provide a clean, business-friendly view of your data
- **Best Practice**: Create models for commonly used datasets with meaningful column names

```sql
-- Example: Orders Model
SELECT
    order_id,
    customer_id,
    order_date,
    total_amount as revenue,
    status
FROM fact_orders
WHERE status != 'cancelled'
```

### 3. Metrics
- **What**: Reusable business calculations defined on models
- **Why**: Ensure consistency across all analytics
- **Best Practice**: Define metrics for all KPIs in your playbooks

### 4. Questions
- **What**: Individual queries that answer specific business questions
- **Why**: Building blocks for dashboards
- **Types**:
  - **Native SQL**: Full control with SQL queries
  - **Query Builder**: Visual interface for non-technical users
  - **Metrics-based**: Using pre-defined metrics

### 5. Dashboards
- **What**: Collections of questions arranged in a layout
- **Why**: Provide comprehensive view of a business area
- **Best Practice**:
  - Keep dashboards focused (5-8 questions max)
  - Use filters to make them interactive
  - Design for your audience (executive vs operational)

## Visualization Types

### Scalar/Number
- **Use for**: Single KPI values (Revenue Today, Order Count)
- **Best Practice**: Include comparison (vs yesterday, vs target)

### Line Chart
- **Use for**: Trends over time
- **Best Practice**: Limit to 3-5 lines for readability

### Bar Chart
- **Use for**: Comparing categories
- **Best Practice**: Sort by value, limit to top 10-15

### Pie/Donut Chart
- **Use for**: Part-to-whole relationships
- **Best Practice**: Maximum 5-7 slices, group small values as "Other"

### Table
- **Use for**: Detailed data, multiple dimensions
- **Best Practice**: Enable sorting, use conditional formatting

### Heatmap
- **Use for**: Patterns across two dimensions (hour × day)
- **Best Practice**: Use for operational insights

## Filters and Variables

### Dashboard Filters
- Allow users to interact with dashboards
- Common types: Date range, Location, Product category

### SQL Variables
- Make questions reusable with different parameters
- Syntax: `{{variable_name}}`

```sql
SELECT * FROM orders
WHERE created_date >= {{start_date}}
AND created_date <= {{end_date}}
```

## Performance Tips

1. **Use Models**: Pre-aggregate data in models instead of complex dashboard queries
2. **Limit Date Ranges**: Default to last 30 days, allow users to expand
3. **Index Key Columns**: Ensure database indexes on filter columns
4. **Cache Results**: Enable caching for executive dashboards
5. **Progressive Loading**: Start with summary, drill down to details

## Access Control

### Collection Permissions
- **View**: Can see content
- **Curate**: Can create/edit questions and dashboards
- **Admin**: Full control including permissions

### Data Permissions
- Control access at database/schema/table level
- Use data sandboxing for row-level security

## Best Practices Summary

1. **Organize by Domain**: One collection per business area
2. **Build on Models**: Create clean, reusable datasets
3. **Define Metrics**: Standardize calculations
4. **Design for Users**: Consider audience and use cases
5. **Document Everything**: Use descriptions for models, metrics, questions
6. **Test Performance**: Verify queries run efficiently
7. **Enable Self-Service**: Provide filters and drill-downs