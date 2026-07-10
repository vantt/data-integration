{{ config(materialized='view', tags=['staging', 'crm']) }}

SELECT
    pt.party_id,
    pt.customer_id::INTEGER                      AS customer_id,
    pt.tag_id,
    t.name                                       AS tag_name,
    t.category                                   AS tag_category,
    t.display_label                              AS tag_display_label,
    t.color                                      AS tag_color,
    COALESCE(t.is_archived::BOOLEAN, false)      AS tag_is_archived,
    pt.tagged_by,
    pt.tagged_at::TIMESTAMPTZ                    AS tagged_at,
    pt.source                                    AS source,
    -- FK -> stg_crm__activity_log.activity_id (nullable, migration 0044) — links a
    -- tag attach back to the call/activity it was captured during.
    pt.source_activity_id::VARCHAR               AS source_activity_id
FROM {{ source('crm_export', 'crm_party_tag') }} pt
LEFT JOIN {{ source('crm_export', 'crm_tag') }} t USING (tag_id)
