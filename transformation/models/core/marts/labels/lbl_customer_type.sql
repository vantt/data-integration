{{ config(materialized='table', tags=['labels']) }}
{{ label_std_model('customer_type', 'dim_customers', 'customer_key', 'customer_type', tenant_ref('taxonomy_label')) }}
