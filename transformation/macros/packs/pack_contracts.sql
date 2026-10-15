{#
  Column contracts between core and packs: the only place that declares which columns core reads
  from a pack model, and their DuckDB types.

    { '<pack model>': {'pack': '<pack id>', 'columns': {'<column>': '<duckdb type>', ...}}, ... }

  pack_ref() builds the empty relation of a disabled pack from it; the generic test
  `pack_contract` (tests/generic/pack_contract.sql), attached to the pack model, proves the real
  model still has these columns with these types. check_boundaries.py reads the model -> pack
  pairs from this file with a regex, so keep one entry per model in the literal form
  `'<model>': {'pack': '<pack>', 'columns': {...}}`.

  Readers (core model -> columns it uses; value when the pack is off):
    int_customer_economics  dim_customers: every column below. Finance off: all NULL, including
                            lifetime_gross_profit / lifetime_contribution_margin / is_margin_negative
                            (no COALESCE to 0 / FALSE: missing cost data is not zero profit).
    stg_crm__app_user       dim_staff: crm_user_id for active users, joined on email. CRM off:
                            crm_user_id NULL.
    int_misa_sales_lines    dim_sku_alias: MISA product codes of goods lines. Finance off: no
                            automatic VTS -> VCS alias (manual seed aliases only).
    fact_order_economics    mart_data_quality: order count and has_cogs / has_platform_fees.
                            Finance off: total_orders 0, cogs/platform-fee rates NULL.
    mart_sku_economics_monthly
                            mart_product_health: the 4 margin columns of the latest month,
                            joined on (product_key, snapshot_month) to core int_sku_sales_monthly
                            (same row set). Finance off: margin columns NULL, has_margin_data
                            false, health_class NULL.
  Types: DESCRIBE of the built relation (shadow lake), checked by the pack_contract test.
#}
{% macro pack_contracts() %}
  {{ return({
    'int_customer_economics': {'pack': 'finance', 'columns': {
        'customer_key': 'VARCHAR',
        'lifetime_gross_profit': 'BIGINT',
        'lifetime_contribution_margin': 'BIGINT',
        'avg_order_contribution_margin_pct': 'DOUBLE',
        'margin_cogs_coverage_pct': 'DOUBLE',
        'is_margin_negative': 'BOOLEAN',
        'total_cogs': 'BIGINT',
        'avg_gross_margin_pct': 'DOUBLE',
        'total_return_amount': 'BIGINT',
        'return_count': 'INTEGER',
        'cogs_order_count': 'INTEGER'}},
    'stg_crm__app_user': {'pack': 'crm', 'columns': {
        'crm_user_id': 'VARCHAR',
        'email': 'VARCHAR',
        'is_active': 'BOOLEAN'}},
    'int_misa_sales_lines': {'pack': 'finance', 'columns': {
        'product_code': 'VARCHAR',
        'is_promo_line': 'BOOLEAN',
        'is_service_line': 'BOOLEAN'}},
    'fact_order_economics': {'pack': 'finance', 'columns': {
        'has_cogs': 'BOOLEAN',
        'has_platform_fees': 'BOOLEAN'}},
    'mart_sku_economics_monthly': {'pack': 'finance', 'columns': {
        'product_key': 'VARCHAR',
        'snapshot_month': 'DATE',
        'realized_margin_pct': 'DOUBLE',
        'cogs_variance_pct': 'DOUBLE',
        'margin_outlier': 'BOOLEAN',
        'cogs_source': 'VARCHAR'}},
  }) }}
{% endmacro %}
