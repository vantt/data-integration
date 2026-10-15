{{ config(materialized='view', tags=['monitoring', 'taxonomy']) }}
-- Long table of every label of the classification engine (one row per subject, domain and label):
-- UNION ALL of the lbl_<domain> models of vars.taxonomy, selftest domains excluded
-- (macros/taxonomy/taxonomy_entity_labels.sql). For monitoring and explanation only: no core or
-- pack model may read it (monitoring bucket, check_boundaries.py).
{{ taxonomy_entity_labels() }}
