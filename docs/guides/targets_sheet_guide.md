# Targets Sheet Guide

> Purpose: explain how the target sheet should be read and filled as a rule table, not as a simple input form.

## Mental Model

Each row in the sheet defines **one target rule**.

A target rule has 3 parts:

1. **Cycle**
   - When the target starts and what period it covers
2. **Metric**
   - What is being targeted
3. **Scope**
   - Who or what the target applies to

In practice, a row answers this question:

> Starting from `cycle_start_date`, for a `cycle_type` period, the expected value for `metric_code` is `target_value`, applied to the entities matched by the scope fields on that row.

---

## Core Fields

| Field | Meaning | Required | Example | Notes |
|---|---|---:|---|---|
| `cycle_start_date` | First day of the cycle where the target becomes effective | Yes | `2026-03-01` | This is the **start of the cycle**, not the data entry date |
| `cycle_type` | Duration of the target cycle | Yes | `monthly` | Valid values: `daily`, `weekly`, `monthly`, `quarterly`, `yearly` |
| `metric_code` | What the target is measuring | Yes | `gmv`, `orders`, `profit` | Should use an agreed code list |
| `target_value` | Expected value for the metric | Yes | `300000000` | Unit depends on `metric_code`. Currency formatting (e.g. `$100,000`) is accepted — the system strips it automatically |
| `description` | Human-readable explanation | No | `March GMV target for ST01` | For readability only, not for matching logic |

---

## Scope Fields

Scope fields are used only to decide **where the target applies**.

| Field | Meaning | Example | Notes |
|---|---|---|---|
| `branch_code` | Limit target to a branch or store | `ST01` | Leave blank if branch is not part of the scope |
| `team_code` | Limit target to a team | `TEAM_A` | Leave blank if team is not part of the scope |
| `staff_email` | Limit target to a specific staff member | `name@company.com` | Must be the staff member's email address (matches `dim_staff.email`) |
| `sales_channel` | Limit target to a sales channel | `facebook`, `retail`, `shopee` | Leave blank if target applies across channels |
| `product_sku` | Limit target to a product | `SKU123` | Leave blank if target is not product-specific |

---

## Matching Semantics

The sheet should be read with these rules:

- Each non-empty scope field is a **constraint**
- Each empty scope field means **not constrained by that dimension**
- If multiple scope fields are filled on the same row, they are combined with **AND**

Examples:

| Filled Scope | Meaning |
|---|---|
| `branch_code = ST01` | Target applies to everything in branch `ST01` |
| `staff_email = a@fgorg.vn` | Target applies to that staff member only |
| `branch_code = ST01`, `staff_email = a@fgorg.vn` | Target applies only to that staff member inside branch `ST01` |
| `branch_code = ST01`, `sales_channel = facebook` | Target applies only to Facebook sales in branch `ST01` |
| `branch_code = ST01`, `staff_email = a@fgorg.vn`, `product_sku = SKU123` | Target applies only to SKU `SKU123` sold by that staff in branch `ST01` |

---

## How Cycles Work

`cycle_start_date` is the first day of the cycle. `cycle_type` determines how long the cycle lasts.

The system automatically derives `cycle_end_date`:

| `cycle_type` | `cycle_start_date` | Derived `cycle_end_date` | Meaning |
|---|---|---|---|
| `daily` | `2026-03-15` | `2026-03-15` | Single day target |
| `weekly` | `2026-03-23` | `2026-03-29` | 7-day target starting that date |
| `monthly` | `2026-03-01` | `2026-03-31` | Full calendar month |
| `quarterly` | `2026-04-01` | `2026-06-30` | Full calendar quarter |
| `yearly` | `2026-01-01` | `2026-12-31` | Full calendar year |

If downstream dashboards need smaller periods than the original cycle (e.g. showing daily progress for a monthly target), those smaller periods are derived by system logic (pro-rating). The sheet itself is only responsible for declaring the target at its intended cycle.

---

## Example Rows

### 1. Branch-wide monthly GMV target

| cycle_start_date | cycle_type | metric_code | target_value | branch_code | team_code | staff_email | sales_channel | product_sku | description |
|---|---|---|---:|---|---|---|---|---|---|
| `2026-03-01` | `monthly` | `gmv` | `300000000` | `ST01` |  |  |  |  | `March GMV target for ST01` |

Meaning: Starting March 2026, for the full month, expected GMV is 300,000,000 for branch ST01.

### 2. Personal GMV target inside a branch

| cycle_start_date | cycle_type | metric_code | target_value | branch_code | team_code | staff_email | sales_channel | product_sku | description |
|---|---|---|---:|---|---|---|---|---|---|
| `2026-03-01` | `monthly` | `gmv` | `20000000` | `ST01` |  | `a@fgorg.vn` |  |  | `March personal target for staff A in ST01` |

Meaning: Starting March 2026, expected GMV is 20,000,000 for staff A within branch ST01.

### 3. Product-specific weekly target on a channel

| cycle_start_date | cycle_type | metric_code | target_value | branch_code | team_code | staff_email | sales_channel | product_sku | description |
|---|---|---|---:|---|---|---|---|---|---|
| `2026-03-23` | `weekly` | `orders` | `120` |  |  |  | `facebook` | `SKU123` | `Week 12 Facebook orders target for SKU123` |

Meaning: For the week starting 2026-03-23, expected order count is 120 for SKU123 on the Facebook channel.

### 4. Daily target for a special sale event

| cycle_start_date | cycle_type | metric_code | target_value | branch_code | team_code | staff_email | sales_channel | product_sku | description |
|---|---|---|---:|---|---|---|---|---|---|
| `2026-06-06` | `daily` | `gmv` | `500000000` |  |  |  |  |  | `6/6 sale day target` |

Meaning: On 2026-06-06 specifically, expected total GMV is 500,000,000 across all dimensions.

---

## Practical Guidance For Users

- Think of the sheet as a **target rule table**
- Fill only the scope fields that are relevant to the target
- If a dimension should not limit the target, leave it blank
- Use `description` to make the business intent obvious
- Keep `metric_code` consistent across rows (lowercase recommended)
- Always fill `cycle_type` — the system defaults to `monthly` if missing, but explicit is better

---

## Open Design Decisions

These decisions should be documented separately once finalized:

1. **Conflict resolution**
   - If multiple target rules match the same entity, does the system use:
     - the most specific rule,
     - fallback logic,
     - or an error?
2. **Target distribution**
   - If a larger cycle target is displayed at a smaller period, how it is derived downstream (uniform pro-rating vs weighted)

---

## Short Summary

Use this sheet to declare:

- **when** a target starts and how long it lasts (`cycle_start_date` + `cycle_type`)
- **what** is being targeted (`metric_code`)
- **how much** is expected (`target_value`)
- **where / to whom** the target applies (scope fields)

The sheet is not just a data-entry form. It is a compact business rules table for target assignment.
