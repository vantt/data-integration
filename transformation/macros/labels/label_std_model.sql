{#
  label_std_model(domain, subject_model, key, label_column, labels): body of a lbl_<domain> model.

  One row per row of `subject_model` (grain `key`) with its label and `<label_column>_std`, the
  canonical code the label is anchored to in the tenant's taxonomy_label for `domain`:
    - label found        -> its label_std (a code of taxonomy_canonical for the domain)
    - label NULL         -> 'UNKNOWN'
    - label not in table -> 'UNMAPPED' (test labels_mapped warns)
  Exact, case-sensitive match on the label, like the SQL that produces it.

  `labels` is the relation tenant_ref('taxonomy_label'), passed by the model so that the model's
  own SQL calls tenant_ref literally (check_boundaries.py rules dbt-seed, tenant-seed-contract).
  Preview layer: the taxonomy engine (docs/architecture/taxonomy-engine.md) will later produce
  these models under the same names from rules; readers do not change.
#}
{% macro label_std_model(domain, subject_model, key, label_column, labels) %}
SELECT
    s.{{ key }},
    s.{{ label_column }},
    COALESCE(l.label_std, IF(s.{{ label_column }} IS NULL, 'UNKNOWN', 'UNMAPPED')) AS {{ label_column }}_std
FROM {{ ref(subject_model) }} s
LEFT JOIN (
    SELECT label, label_std
    FROM {{ labels }}
    WHERE domain = '{{ domain }}'
) l ON l.label = s.{{ label_column }}
{% endmacro %}
