# Targets Sheet Guide

> Purpose: explain how the target sheet should be read and filled as a rule table, not as a simple input form.

## Mental Model

Each row in the sheet defines **one target rule**.

A target rule has 3 parts:

1. **Cycle**
   - When the target starts, what period it covers, and optionally how long it repeats
2. **Metric**
   - What is being targeted
3. **Scope**
   - Who or what the target applies to

In practice, a row answers this question:

> Starting from `cycle_start_date`, repeating every `cycle_type` until `repeat_until`, the expected value for `metric_code` is `target_value`, applied to the entities matched by the scope fields on that row.

---

## Core Fields

| Field | Meaning | Required | Example | Notes |
|---|---|---:|---|---|
| `cycle_start_date` | First day of the cycle where the target becomes effective | Yes | `2026-03-01` | This is the **start of the cycle**, not the data entry date. Can be any date — does not have to be day 1 of a month |
| `cycle_type` | Duration of each cycle | Yes | `monthly` | Valid values: `daily`, `weekly`, `monthly`, `quarterly`, `yearly` |
| `repeat_until` | Last date the target remains active | No | `2026-12-31` | If blank, target applies for one cycle only. If filled, system auto-generates one target per cycle from `cycle_start_date` to `repeat_until` |
| `metric_code` | What the target is measuring | Yes | `gmv`, `orders`, `profit` | Should use an agreed code list |
| `target_value` | Expected value for the metric per cycle | Yes | `300000000` | Unit depends on `metric_code`. Currency formatting (e.g. `$100,000`) is accepted — the system strips it automatically |
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

---

## How Cycles Work

### Cycle end date derivation

`cycle_start_date` can be any date. The system derives `cycle_end_date` using the formula: `cycle_start_date + cycle_type interval - 1 day`.

| `cycle_type` | `cycle_start_date` | Derived `cycle_end_date` | Formula |
|---|---|---|---|
| `daily` | `2026-03-15` | `2026-03-15` | Same day |
| `weekly` | `2026-03-23` | `2026-03-29` | +7 days - 1 |
| `monthly` | `2026-03-01` | `2026-03-31` | +1 month - 1 day |
| `monthly` | `2026-03-15` | `2026-04-14` | +1 month - 1 day |
| `quarterly` | `2026-04-01` | `2026-06-30` | +3 months - 1 day |
| `yearly` | `2026-01-01` | `2026-12-31` | +1 year - 1 day |

Note: the cycle length adapts to the calendar. A monthly cycle starting on March 1 ends on March 31 (31 days), while one starting on February 1 ends on February 28 (28 days). This is handled automatically.

### Flexible start dates

`cycle_start_date` does not have to be the first day of a month or quarter. Use cases for non-standard start dates:

- **Campaign cycle**: weekly target starting on Wednesday
- **Payroll cycle**: monthly target from the 15th to the 14th of the next month
- **Fiscal quarter**: quarterly target starting on a non-calendar boundary

If you want standard calendar months, simply use day 1 (e.g. `2026-03-01`).

### Repeating targets with `repeat_until`

If `repeat_until` is filled, the system generates multiple cycles from a single row.

**Rule**: a new cycle is generated if its `cycle_start_date <= repeat_until`.

Example: `cycle_start_date = 2026-01-01`, `cycle_type = monthly`, `repeat_until = 2026-06-25`

| Generated cycle | cycle_start_date | cycle_end_date | Why |
|---|---|---|---|
| 1 | 2026-01-01 | 2026-01-31 | 01-01 ≤ 06-25 |
| 2 | 2026-02-01 | 2026-02-28 | 02-01 ≤ 06-25 |
| 3 | 2026-03-01 | 2026-03-31 | 03-01 ≤ 06-25 |
| 4 | 2026-04-01 | 2026-04-30 | 04-01 ≤ 06-25 |
| 5 | 2026-05-01 | 2026-05-31 | 05-01 ≤ 06-25 |
| 6 | 2026-06-01 | 2026-06-30 | 06-01 ≤ 06-25 |
| ~~7~~ | ~~2026-07-01~~ | — | 07-01 > 06-25, **not generated** |

`repeat_until` does not need to be an exact cycle boundary. Any date works — the system checks whether the next cycle's start date falls within range.

If `repeat_until` is blank, only one cycle is generated (the original row).

### Pro-rating for dashboards

If downstream dashboards need smaller periods than the original cycle (e.g. showing daily progress for a monthly target), those smaller periods are derived by system logic (pro-rating). The sheet itself is only responsible for declaring the target at its intended cycle.

---

## Example Rows

### 1. Branch-wide monthly GMV target for the full year (1 row → 12 cycles)

| cycle_start_date | cycle_type | repeat_until | metric_code | target_value | branch_code | description |
|---|---|---|---|---:|---|---|
| `2026-01-01` | `monthly` | `2026-12-31` | `gmv` | `300000000` | `ST01` | `2026 monthly GMV target for ST01` |

The system generates 12 monthly targets (Jan–Dec), each with target_value = 300,000,000.

### 2. Personal target for one month only (no repeat)

| cycle_start_date | cycle_type | repeat_until | metric_code | target_value | branch_code | staff_email | description |
|---|---|---|---|---:|---|---|---|
| `2026-03-01` | `monthly` | | `gmv` | `20000000` | `ST01` | `a@fgorg.vn` | `March personal target` |

No `repeat_until` → one cycle only (March 2026).

### 3. Weekly target for a quarter

| cycle_start_date | cycle_type | repeat_until | metric_code | target_value | sales_channel | product_sku | description |
|---|---|---|---|---:|---|---|---|
| `2026-04-07` | `weekly` | `2026-06-30` | `orders` | `120` | `facebook` | `SKU123` | `Q2 weekly Facebook orders for SKU123` |

Generates ~13 weekly targets from April 7 to end of June.

### 4. Daily target for a special sale event (no repeat)

| cycle_start_date | cycle_type | repeat_until | metric_code | target_value | description |
|---|---|---|---|---:|---|
| `2026-06-06` | `daily` | | `gmv` | `500000000` | `6/6 sale day target` |

Single day, no repeat.

---

## Practical Guidance For Users

- Think of the sheet as a **target rule table**
- Use `repeat_until` to avoid entering the same target row for every month — one row can cover a full year
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
- **how long** it repeats (`repeat_until`, optional)
- **what** is being targeted (`metric_code`)
- **how much** is expected per cycle (`target_value`)
- **where / to whom** the target applies (scope fields)

The sheet is not just a data-entry form. It is a compact business rules table for target assignment.
