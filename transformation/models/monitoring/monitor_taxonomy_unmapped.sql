{{ config(materialized='view', tags=['monitoring', 'taxonomy']) }}
-- Raw values that no specific classification rule covers (UNMAPPED, UNKNOWN or the default rule),
-- per domain, with customers, orders and revenue: what to write rules for next.
-- macros/taxonomy/taxonomy_unmapped_survey.sql; docs/architecture/taxonomy-engine.md §4b.
{{ taxonomy_unmapped_survey(tenant_ref('taxonomy_rule_tenant')) }}
