{#- Error-level check that every label a lbl_<domain> model produces is declared: rows whose label is
    not a reserved code (UNMAPPED, UNKNOWN) and is either a tenant-layer label missing from `label_set`
    in the tenant's taxonomy_label, or a product-layer label (source_layer = 'product') that is not a
    canonical code of `label_set` in taxonomy_canonical (product rules assign canonical codes). A rule
    with an undeclared label is first stopped by scripts/checks/check_taxonomy_rules.py; this catches
    what reaches the warehouse anyway. -#}
{% test taxonomy_label_declared(model, column_name, label_set) %}
SELECT m.*
FROM {{ model }} m
WHERE m.{{ column_name }} IS NULL
   OR (m.{{ column_name }} NOT IN ('UNMAPPED', 'UNKNOWN')
       AND (
           (m.source_layer = 'product' AND m.{{ column_name }} NOT IN (
                SELECT code FROM {{ ref('taxonomy_canonical') }}
                WHERE domain = '{{ label_set }}' AND code IS NOT NULL))
           OR (m.source_layer IS DISTINCT FROM 'product' AND m.{{ column_name }} NOT IN (
                SELECT label FROM {{ tenant_ref('taxonomy_label') }}
                WHERE domain = '{{ label_set }}' AND label IS NOT NULL))))
{% endtest %}
