{{ config(tags=['intermediate', 'crm'], materialized='view') }}

-- Gộp tag risk/vip_tier theo customer_id (1 dòng/customer, aggregate qua bool_or).
-- Party chưa link Sapo (customer_id NULL) bị loại — vô hình với action queue by design.
-- source='crm_user': chỉ tag người gán được tính là signal. Tag sync từ Sapo
-- (source='sapo_v2_sync', plan 260619) là dữ liệu phân loại, không phải phán đoán NV —
-- MANUAL_RISK_REVIEW hứa với người dùng đây là đánh giá con người, và wholesale sync
-- tags không được boost khách B2B vào queue outreach.
-- tag_is_archived: admin archive tag (260706-0833 Governance Admin) phải cắt tag đó
-- khỏi action queue ngay — nếu không, tag đã "retired" khỏi picker vẫn âm thầm tiếp
-- tục boost/flag khách, mâu thuẫn với kỳ vọng của admin.
-- NOTE: bool_or/string_agg return NULL for customer_ids with zero qualifying rows —
-- but such customer_ids never appear here at all (GROUP BY only emits rows that exist
-- in the source), so has_vip_tag/has_risk_tag are never NULL for a party present in
-- this model. NULL only shows up via the LEFT JOIN in mart_customer_action_queue for
-- customers absent from this model entirely — handled there with COALESCE.
SELECT
    customer_id,
    bool_or(tag_category = 'vip_tier')                                   AS has_vip_tag,
    string_agg(DISTINCT CASE WHEN tag_category = 'vip_tier'
               THEN tag_display_label END, ', ')                          AS vip_tag_labels,
    bool_or(tag_category = 'risk')                                        AS has_risk_tag,
    string_agg(DISTINCT CASE WHEN tag_category = 'risk'
               THEN tag_display_label END, ', ')                          AS risk_tag_labels,
    max(tagged_at)                                                        AS tags_updated_at
FROM {{ ref('stg_crm__party_tag') }}
WHERE customer_id IS NOT NULL
  AND tag_category IN ('risk', 'vip_tier')
  AND source = 'crm_user'
  AND NOT tag_is_archived
GROUP BY customer_id
