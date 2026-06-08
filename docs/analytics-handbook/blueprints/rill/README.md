# Rill Blueprints

Deployable YAML specifications for Rill explores, following the 3-layer architecture.

## Directory Structure

```
blueprints/rill/
├── README.md                    # This file
├── orders_executive.yaml        # Layer 1 Executive [All]
├── orders_retail_ops.yaml       # Layer 2 Retail [Retail]
├── orders_b2b_ops.yaml          # Layer 2 B2B [B2B]
└── sales_items_product.yaml     # Product performance [Retail]
```

## Blueprint Format

Rill blueprints use the standard Rill YAML format for `explore` resources:

```yaml
type: explore
display_name: "Dashboard Name [Scope]"
metrics_view: metrics_view_name
description: "Brief description with layer and audience"

dimensions: "*"  # or explicit list
measures: "*"    # or explicit list

default_preset:
  time_range: "P7D"  # ISO 8601 duration
  where: "scope_xxx = true"
  dimensions:
    - dimension_name
  measures:
    - measure_name
```

## Deployment

Blueprints are deployed by copying to `rill/dashboards/`:

```bash
# Deploy a single blueprint
cp docs/analytics-handbook/blueprints/rill/orders_executive.yaml rill/dashboards/

# Deploy all blueprints
cp docs/analytics-handbook/blueprints/rill/*.yaml rill/dashboards/
```

Rill auto-reloads on file changes (dev mode).

## Naming Convention

| Blueprint | Display Name | Scope |
|-----------|--------------|-------|
| `orders_executive.yaml` | Orders Executive [All] | scope_sales |
| `orders_retail_ops.yaml` | Orders Retail Ops [Retail] | scope_retail |
| `orders_b2b_ops.yaml` | Orders B2B Ops [B2B] | scope_b2b |

## Cross-Reference

| Rill Blueprint | Playbook | Metabase Blueprint |
|----------------|----------|-------------------|
| orders_executive | [playbook](../playbooks/rill/orders_executive.md) | ceo_weekly_pulse.md |
| orders_retail_ops | [playbook](../playbooks/rill/orders_retail_ops.md) | sales_today_operation.md |
| orders_b2b_ops | [playbook](../playbooks/rill/orders_b2b_ops.md) | b2b_orders_tracking.md |

