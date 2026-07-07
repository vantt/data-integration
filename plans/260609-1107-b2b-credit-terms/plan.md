# Plan: B2B Credit Terms

> Created: 2026-06-09
> Status: ⚠️ Partially ready — Not started
> Origin: `analytics_improvement_opportunities.md` § B2B Credit Terms
> (updated 2026-06-24: untouched by 260623 audit work; data layer prerequisites not yet built)

## Objective

Turn unpaid-order tracking into credit-risk management — overdue amounts, credit exposure, DSO by customer, collection priority queue.

## What this unlocks

- Overdue amount by customer
- Credit exposure (outstanding vs credit limit)
- DSO by customer
- Collection priority queue
- Hold/release recommendation for new B2B orders

## Current state

- Payment status and outstanding amount available via `fact_orders` (Sapo)
- B2B blueprints (`b2b_orders_tracking`, `b2b_sales_daily`) cover aging and unpaid orders
- **Missing:** formal credit terms per customer (credit limit, payment terms, due date per invoice)
- **Missing:** partial payment allocation (how much of a payment applies to which invoice)

## Data needed

- Customer credit limit (per `dim_customers` or separate credit master)
- Payment terms (net-30, net-60, etc.) per customer
- Due date per invoice/order
- Payment schedule for installment B2B orders
- Partial payment allocation: which payment → which order
- Customer owner / sales rep assignment

## Implementation steps

- [ ] Add `credit_limit`, `payment_terms_days` to `dim_customers` or new `dim_b2b_credit` table
- [ ] Add `due_date` to `fact_orders` for B2B orders (= order_date + payment_terms_days)
- [ ] Create `int_b2b_aging` with aging buckets: current / 1-30 / 31-60 / 61-90 / 90+
- [ ] Create `int_b2b_credit_exposure`: outstanding_amount vs credit_limit per customer
- [ ] Add Collections Priority Queue card to B2B Orders Tracking dashboard
- [ ] Add Credit Exposure card: customers near or over credit limit
- [ ] Add Hold/Release signal: flag customers with overdue > threshold for new order review

## Dependency

Requires credit terms data from sales/finance team (not available in Sapo by default).
`fact_payments` (partial payment allocation) already populated — see `plans/archive/260609-1107-cash-flow-payments/` (superseded/closed 2026-07-06; that plan's remaining DSO/AR scope now lives here).
