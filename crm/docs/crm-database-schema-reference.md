# CRM Database Schema Reference

## Conventions

- **Engine**: SQLite WAL mode (`crm.db`)
- **Timestamps**: `TEXT` UTC ISO-8601 `'…Z'`; display in ICT (Asia/Ho_Chi_Minh) per R6
- **UUIDs**: `TEXT` app-generated
- **Booleans**: `INTEGER` (0/1)
- **Cross-db**: `cache.db` linked read-only via `ATTACH`; no FK across files (R3)
- **Migration prefix**: column/table origin noted as `(0NNN)`

---

## crm_app_user (0001)

| Column | Type | Notes |
|--------|------|-------|
| user_id | TEXT PK | |
| username | TEXT UNIQUE | login handle |
| display_name | TEXT | |
| role | TEXT | admin\|rep\|viewer |
| password_hash | TEXT | |
| is_active | INTEGER | DEFAULT 1 |
| created_at | TEXT | |

---

## crm_party (0002 + 0007)

Core golden record. One party per real person/org.

| Column | Type | Notes |
|--------|------|-------|
| party_id | TEXT PK | |
| party_type | TEXT | person\|org |
| display_name | TEXT | |
| primary_phone | TEXT | E.164 (+84…) per R5 |
| primary_email | TEXT | |
| status | TEXT | active\|inactive\|blocked |
| is_merged | INTEGER | 1 if absorbed into another party |
| merged_into | TEXT → crm_party | |
| created_at / updated_at | TEXT | |
| **address_line** | TEXT | **(0007)** full street address |
| **ward** | TEXT | **(0007)** phường/xã |
| **district** | TEXT | **(0007)** quận/huyện |
| **province** | TEXT | **(0007)** tỉnh/thành phố |
| **address_source** | TEXT | **(0007)** `sapo_sync`\|`manual` — R13 |
| **address_note** | TEXT | **(0007)** e.g. "địa chỉ sàn bị mask" |
| **address_updated_at** | TEXT | **(0007)** |
| **address_updated_by** | TEXT → crm_app_user | **(0007)** |

---

## crm_party_identity (0002 + 0006 + 0008)

Identity → party mapping. UNIQUE(identity_type, identity_value) prevents duplicate phone/email.

| Column | Type | Notes |
|--------|------|-------|
| identity_id | TEXT PK | |
| party_id | TEXT → crm_party | |
| source_system | TEXT | sapo\|messenger\|zalo\|manual |
| identity_type | TEXT | sapo_customer\|phone\|email\|psid\|zalo_uid\|customer_code\|phone_secondary\|facebook |
| identity_value | TEXT | normalised; E.164 for phone |
| confidence | REAL | DEFAULT 1.0 |
| is_primary | INTEGER | legacy flag |
| verified_at | TEXT | |
| created_at | TEXT | |
| source_contact_quality | TEXT | **(0006)** DEFAULT 'real' |
| contact_quality | TEXT | **(0006)** DEFAULT 'real' |
| **display_label** | TEXT | **(0008)** e.g. "Số công ty" |
| **contact_status** | TEXT | **(0008)** active\|invalid\|unreachable — soft deactivate |
| **is_preferred** | INTEGER | **(0008)** 1 = preferred for outreach |

---

## crm_dedup_candidate (0002)

| Column | Type | Notes |
|--------|------|-------|
| candidate_id | TEXT PK | |
| party_a / party_b | TEXT → crm_party | |
| match_rule | TEXT | exact_phone\|exact_email\|fts_name_phone |
| match_score | REAL | |
| status | TEXT | pending\|merged\|rejected |
| reviewed_by | TEXT → crm_app_user | |
| reviewed_at / created_at | TEXT | |

---

## crm_party_merge_log (0002)

| Column | Type | Notes |
|--------|------|-------|
| merge_id | TEXT PK | |
| surviving_party_id | TEXT → crm_party | |
| merged_party_id | TEXT | soft ref (party becomes is_merged=1) |
| reason | TEXT | |
| merged_by | TEXT → crm_app_user | |
| snapshot | TEXT | JSON pre-merge state for undo (R4) |
| merged_at / undone_at | TEXT | |

---

## crm_party_external_id (0009) — NEW

Platform-independent ID registry. Decouples CRM from Sapo.

| Column | Type | Notes |
|--------|------|-------|
| ext_id | TEXT PK | |
| party_id | TEXT → crm_party | |
| source_system | TEXT | sapo\|woocommerce\|shopify\|tiki\|shopee |
| external_key | TEXT | customer_id in that platform |
| created_at | TEXT | |
| UNIQUE | (source_system, external_key) | |

---

## crm_customer_profile (0003)

1-1 enrichment per party. `custom` JSON map keyed by crm_custom_field_def.field_key.

| Column | Type | Notes |
|--------|------|-------|
| party_id | TEXT PK → crm_party | |
| owner_user_id | TEXT → crm_app_user | assigned rep |
| lifecycle_stage | TEXT | lead\|new\|active\|at_risk\|churned |
| acquisition_source | TEXT | |
| birthday | TEXT | YYYY-MM-DD |
| address | TEXT | **legacy JSON** — use crm_party address columns (0007) |
| preferences | TEXT | JSON: rep-recorded preferences |
| custom | TEXT | JSON map of custom field values |
| consent_contact | INTEGER | 1=consented, 0=opted-out (R1) |
| created_at / updated_at | TEXT | |

---

## crm_custom_field_def (0003 + 0014)

| Column | Type | Notes |
|--------|------|-------|
| field_id | TEXT PK | |
| entity_type | TEXT | party\|order |
| field_key | TEXT | slug key in custom JSON; immutable after create |
| label | TEXT | display label (VI) |
| data_type | TEXT | text\|number\|date\|bool\|select\|multiselect |
| options | TEXT | JSON array for select types |
| is_required | INTEGER | |
| is_active | INTEGER | DEFAULT 1 |
| sort_order | INTEGER | sort within section |
| **section** | TEXT | **(0014)** free-text grouping label |
| UNIQUE | (entity_type, field_key) | |

---

## crm_tag (0003)

| Column | Type | Notes |
|--------|------|-------|
| tag_id | TEXT PK | |
| name | TEXT | slug |
| category | TEXT | **enum** behavioral\|demographic\|preference\|vip_tier\|risk\|source |
| color | TEXT | hex |

---

## crm_party_tag (0003)

| Column | Type | Notes |
|--------|------|-------|
| party_id | TEXT → crm_party | PK component |
| tag_id | TEXT → crm_tag | PK component |
| tagged_by | TEXT → crm_app_user | |
| tagged_at | TEXT | |

---

## crm_note (0003 + 0010)

| Column | Type | Notes |
|--------|------|-------|
| note_id | TEXT PK | |
| party_id | TEXT → crm_party | |
| body | TEXT | |
| author_user_id | TEXT → crm_app_user | |
| created_at | TEXT | |
| **note_type** | TEXT | **(0010)** general\|preference\|contact_pref\|warning\|outcome\|internal |
| **pinned** | INTEGER | **(0010)** DEFAULT 0 |
| **pinned_until** | TEXT | **(0010)** UTC; NULL = permanent pin |
| **visibility** | TEXT | **(0010)** team\|private |
| **task_id** | TEXT → crm_task | **(0010)** retail activation chain |
| **campaign_id** | TEXT → crm_campaign | **(0010)** |
| **updated_at** | TEXT | **(0010)** |
| **updated_by_user_id** | TEXT → crm_app_user | **(0010)** |
| **deleted_at** | TEXT | **(0010)** soft delete |

---

## crm_party_insight (0011) — NEW

Rep-curated insights. Distinct from machine-generated wh_customer_insight (cache.db).

| Column | Type | Notes |
|--------|------|-------|
| insight_id | TEXT PK | |
| party_id | TEXT → crm_party | |
| insight_type | TEXT | persona\|buying_pattern\|decision_style\|life_event\|relationship\|advocate_signal |
| body | TEXT | |
| confidence | TEXT | low\|medium\|high |
| source_note_id | TEXT → crm_note | set when promoted from note via M16 |
| created_by | TEXT → crm_app_user | |
| created_at / updated_at | TEXT | |
| deleted_at | TEXT | soft delete |

---

## crm_activity (0004 + 0013)

| Column | Type | Notes |
|--------|------|-------|
| activity_id | TEXT PK | |
| party_id | TEXT → crm_party | |
| activity_type | TEXT | call\|note\|visit\|email\|chat\|other |
| direction | TEXT | in\|out |
| channel | TEXT | phone\|messenger\|zalo\|store\|… |
| subject / body / outcome | TEXT | |
| related_order_code | TEXT | soft ref to warehouse |
| staff_user_id | TEXT → crm_app_user | |
| occurred_at / created_at | TEXT | |
| **task_id** | TEXT → crm_task | **(0013)** retail activation chain |
| **channel_used** | TEXT | **(0013)** specific channel for this attempt |
| **contact_outcome** | TEXT | **(0013)** reached\|no_answer\|callback\|refused |
| **callback_at** | TEXT | **(0013)** UTC; set when contact_outcome=callback |
| **contact_duration_s** | INTEGER | **(0013)** call seconds |

---

## crm_task (0004 + 0012)

| Column | Type | Notes |
|--------|------|-------|
| task_id | TEXT PK | |
| party_id | TEXT → crm_party | |
| title / description | TEXT | |
| due_at | TEXT | UTC nullable |
| priority | INTEGER | |
| status | TEXT | open\|doing\|done\|cancelled |
| assignee_user_id | TEXT → crm_app_user | |
| source | TEXT | manual\|action_queue\|campaign |
| source_ref | TEXT | action_id / campaign_id (idempotency key R8) |
| created_by | TEXT → crm_app_user | |
| created_at / updated_at / completed_at | TEXT | |
| **outcome** | TEXT | **(0012)** converted\|follow_up\|refused\|invalid_contact |

---

## crm_conversation (0004)

| Column | Type | Notes |
|--------|------|-------|
| conversation_id | TEXT PK | |
| party_id | TEXT → crm_party | nullable until psid resolved |
| channel | TEXT | messenger\|shopee\|zalo |
| external_thread_id | TEXT | psid / shopee buyer id / zalo uid |
| page_id | TEXT | FB page / shopee shop / zalo OA |
| status | TEXT | open\|pending\|closed |
| assignee_user_id | TEXT → crm_app_user | |
| last_message_at | TEXT | |
| unread_count | INTEGER | |
| created_at / updated_at | TEXT | |

---

## crm_message (0004)

| Column | Type | Notes |
|--------|------|-------|
| message_id | TEXT PK | |
| conversation_id | TEXT → crm_conversation | |
| external_message_id | TEXT | FB mid / shopee / zalo |
| direction | TEXT | in\|out |
| sender_ref | TEXT | psid or page_id |
| body / attachments | TEXT | attachments = JSON array |
| sent_at | TEXT | |

---

## crm_segment (0005)

| Column | Type | Notes |
|--------|------|-------|
| segment_id | TEXT PK | |
| name / description | TEXT | |
| is_dynamic | INTEGER | 1=rule-based, 0=manual |
| definition | TEXT | JSON rule |
| owner_user_id | TEXT → crm_app_user | |
| created_at / updated_at | TEXT | |

## crm_segment_member (0005)

| Column | Type | Notes |
|--------|------|-------|
| segment_id | TEXT → crm_segment | PK |
| party_id | TEXT → crm_party | PK |
| source | TEXT | rule\|manual |
| added_at | TEXT | |

## crm_campaign (0005)

| Column | Type | Notes |
|--------|------|-------|
| campaign_id | TEXT PK | |
| name | TEXT | |
| objective | TEXT | reactivation\|winback\|upsell\|crosssell |
| channel | TEXT | |
| segment_id | TEXT → crm_segment | |
| status | TEXT | draft\|running\|done |
| scheduled_at | TEXT | |
| created_by | TEXT → crm_app_user | |
| created_at / updated_at | TEXT | |

## crm_campaign_target (0005)

| Column | Type | Notes |
|--------|------|-------|
| campaign_id | TEXT → crm_campaign | PK |
| party_id | TEXT → crm_party | PK |
| status | TEXT | queued\|sent\|responded\|converted\|skipped |
| assigned_user_id | TEXT → crm_app_user | |
| last_touch_at | TEXT | |
| converted_order_code / converted_revenue_vnd / converted_at | | R11 attribution |

---

## Views

### crm_party_360 (0003)

Joins `crm_party` + `crm_customer_profile` (LEFT) + aggregated `tags_json`. Used by S03.
Filters `WHERE is_merged = 0`.

---

## Cache DB (read-only via ATTACH)

No FK from crm.db to cache.db — linked by value `customer_id` (R3).

| Table | Key columns | Used by |
|-------|-------------|---------|
| `wh_customer_insight` | customer_id, rfm_segment, affinity_score, refreshed_at | P01, S03 |
| `wh_action_queue` | action_id, customer_id, action_type, priority, due_date | S01, S07 |
| `wh_product_insight` | product_id, affinity_score | P01 |
| `wh_order_hdr` | order_code, customer_id, date_key, total_vnd, … | P02, S03 |

`refreshed_at` must be displayed on every surface showing cache data (R2).
