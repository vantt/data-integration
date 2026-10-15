{{ config(materialized='table', tags=['labels']) }}
{{ taxonomy_label_model('customer_type__group_blob', tenant_ref('taxonomy_rule_tenant'), tenant_ref('taxonomy_label')) }}
