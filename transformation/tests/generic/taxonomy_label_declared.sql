{#- Error-level check that every label a lbl_<domain> model produces is declared: rows whose label is
    neither a reserved code (UNMAPPED, UNKNOWN) nor a label of `label_set` in the tenant's
    taxonomy_label. A rule with an undeclared label is first stopped by
    scripts/checks/check_taxonomy_rules.py; this catches what reaches the warehouse anyway. -#}
{% test taxonomy_label_declared(model, column_name, label_set) %}
SELECT m.*
FROM {{ model }} m
WHERE m.{{ column_name }} IS NULL
   OR (m.{{ column_name }} NOT IN ('UNMAPPED', 'UNKNOWN')
       AND m.{{ column_name }} NOT IN (
           SELECT label FROM {{ tenant_ref('taxonomy_label') }}
           WHERE domain = '{{ label_set }}' AND label IS NOT NULL))
{% endtest %}
