{{ config(materialized='table', tags=['labels']) }}
{{ label_std_model('value_group', 'dim_customers', 'customer_key', 'value_group', tenant_ref('taxonomy_label')) }}
