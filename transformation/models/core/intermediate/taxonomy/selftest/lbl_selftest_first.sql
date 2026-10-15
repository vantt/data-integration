{{ config(enabled=var('taxonomy_selftest'), materialized='table', tags=['taxonomy_selftest']) }}
{{ taxonomy_label_model('selftest_first', tenant_ref('taxonomy_rule_tenant'), tenant_ref('taxonomy_label')) }}
