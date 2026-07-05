{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    pt.party_id,
    pt.tag_id,
    t.name                                       AS tag_name,
    t.category                                   AS tag_category,
    t.display_label                              AS tag_display_label,
    t.color                                      AS tag_color,
    pt.tagged_by,
    pt.tagged_at::TIMESTAMPTZ                    AS tagged_at
FROM {{ source('crm_export', 'crm_party_tag') }} pt
LEFT JOIN {{ source('crm_export', 'crm_tag') }} t USING (tag_id)
