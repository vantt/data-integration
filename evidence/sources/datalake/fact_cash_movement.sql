SELECT
    posting_date,
    period_month,
    cash_account,
    offset_account,
    cashflow_line,
    direction,
    is_internal_transfer,
    amount,
    signed_amount,
    voucher_no,
    description
FROM main_marts.fact_cash_movement
