{{ config(materialized='table', tags=['labels']) }}
{{ label_std_model('customer_lifecycle_stage', 'dim_customers', 'customer_key', 'lifecycle_stage', tenant_ref('taxonomy_label')) }}
