# Plan: Cash Flow and Liquidity

> Created: 2026-06-09
> Status: In progress
> Origin: `analytics_improvement_opportunities.md` § Cash Flow and Liquidity
> (updated 2026-06-24: payment pipeline unblocked — $.prepayments fix commit 8624772, fact_payments now 9272 rows with payment_behavior COD populated; dashboard + AR/DSO work still not started)

## Objective

Move from sales/payment reporting to treasury visibility — cash balance, daily movement, DSO, short-term liquidity.

## What this unlocks

- Cash balance by account
- Daily cash inflow / outflow
- DSO (days sales outstanding)
- Short-term liquidity monitoring
- Cash forecast

## Data needed

- Payment inflow/outflow classification (receipt vs disbursement)
- Bank/account balance snapshots (daily)
- Accounts receivable and payable aging
- Payment due dates
- Bank transaction data or accounting cash ledger (from GL — see `plans/260609-1107-gl-accounting-entries/`)

## Current state

- `fact_payments` now has **9,272 rows** with payment_behavior COD populated (commit 8624772: extract from `$.prepayments` not `$.payments`)
- Ingestion pipeline is live; payment method field corrected (commit 2b97835)
- `fact_orders` has `total_collected` and payment status fields — still the primary cash proxy
- **Remaining:** bank balance snapshots, AR/DSO analytics, and Cash Flow dashboard still not built

## Implementation steps

- [ ] Identify payment data source (Sapo payment records, bank export, or MISA cash accounts)
- [ ] Build ingestion for payment transactions (inflow/outflow, method, account, date)
- [ ] Classify transactions: cash_in (completed order payment) vs cash_out (refund, supplier)
- [ ] Populate `fact_payments` with real data
- [ ] Add account balance snapshot table (daily bank balance)
- [ ] Build Cash Flow dashboard: daily movement, running balance, DSO
- [ ] Link to B2B outstanding: `fact_orders` unpaid B2B orders as AR proxy

## Dependency

Partial dependency on `plans/260609-1107-gl-accounting-entries/` for full cash ledger.
First useful version (order payment tracking) possible from Sapo data alone.
