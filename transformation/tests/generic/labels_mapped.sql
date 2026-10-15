{#- Warn-level check that every label of a lbl_<domain> model is anchored to a canonical code:
    returns the rows whose <label>_std is 'UNMAPPED' (label missing from the tenant's
    taxonomy_label). Warn, not error, so a new label (e.g. after ref_order_sources changes) does not
    red the nightly; the shadow gate requires `pass`. Fix by adding the label to
    seeds/tenants/<tenant>/taxonomy_label.csv. -#}
{% test labels_mapped(model, column_name) %}
{{ config(severity='warn') }}
SELECT *
FROM {{ model }}
WHERE {{ column_name }} = 'UNMAPPED'
{% endtest %}
