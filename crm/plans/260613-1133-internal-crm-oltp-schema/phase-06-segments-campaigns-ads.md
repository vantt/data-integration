# Phase 06 — Segments + Reactivation Campaigns + Ads Tracking

**Context:** [plan.md](plan.md) · Reports: orders-sales-products, engagement-chat-ads-channel

## Overview
- **Priority:** P1
- **Status:** ⬜ (cần Phase 02 party + Phase 04 insight)
- Biến insight thành hành động bán lại: tạo **tệp khách** (segment), chạy **chiến dịch reactivation/winback/upsell**, đo kết quả; và **theo dõi ads** + attribution mà warehouse không có.

## Key Insights
- Segment nên build trên signal `wh_cache` (value_group, customer_status, next_purchase_signal, affinity) — không re-derive.
- Warehouse `fact_marketing_spend` LIVE (spend theo date+channel) nhưng **không ad→order**. CRM tự sở hữu lead-capture (click ad messenger) → party → order_code để đo ROI thật.
- Đo reactivation = nối campaign_target → order_code phát sinh sau touch (lấy order từ warehouse/wh_cache).

## Requirements
- **FR:** segment tĩnh (member thủ công) + động (rule jsonb trên party/insight); campaign gắn segment + objective + kênh; theo dõi từng target (queued→sent→responded→converted) + gán NV; ghi nhận ad campaign/spend/lead + attribution → party/order.
- **NFR:** materialize segment member để query nhanh; attribution idempotent.

## Architecture
> DDL Postgres-style — map **SQLite** theo Quy ước [plan.md](plan.md): `crm_*` prefix, `uuid`→`TEXT`, `timestamptz`→`TEXT` UTC, `definition jsonb`→`TEXT`+JSON1, `numeric`(VND)→`INTEGER`, ở `crm.db`.

### Core DDL — Segments & Campaigns
```sql
CREATE TABLE crm.segment (
  segment_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL, description text,
  is_dynamic boolean DEFAULT true,
  definition jsonb,                 -- rule: vd {value_group:['VIP'], customer_status:'at_risk'}
  owner_user_id uuid REFERENCES crm.app_user(user_id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE crm.segment_member (
  segment_id uuid REFERENCES crm.segment(segment_id),
  party_id uuid REFERENCES crm.party(party_id),
  source text DEFAULT 'rule',       -- rule|manual
  added_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (segment_id, party_id)
);
CREATE TABLE crm.campaign (
  campaign_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  objective text NOT NULL,          -- reactivation|winback|upsell|crosssell
  channel text,                     -- call|messenger|zalo|sms|email
  segment_id uuid REFERENCES crm.segment(segment_id),
  status text DEFAULT 'draft',      -- draft|running|done
  scheduled_at timestamptz, created_by uuid REFERENCES crm.app_user(user_id),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE crm.campaign_target (
  campaign_id uuid REFERENCES crm.campaign(campaign_id),
  party_id uuid REFERENCES crm.party(party_id),
  status text DEFAULT 'queued',     -- queued|sent|responded|converted|skipped
  assigned_user_id uuid REFERENCES crm.app_user(user_id),
  last_touch_at timestamptz,
  converted_order_code text, converted_revenue_vnd numeric, converted_at timestamptz,
  PRIMARY KEY (campaign_id, party_id)
);
```
### Core DDL — Ads tracking (CRM-owned)
```sql
CREATE TABLE crm.ad_campaign (
  ad_campaign_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  platform text NOT NULL,           -- facebook|google|tiktok
  external_campaign_id text, name text, objective text,
  UNIQUE (platform, external_campaign_id)
);
CREATE TABLE crm.ad_spend (
  spend_date date, ad_campaign_id uuid REFERENCES crm.ad_campaign(ad_campaign_id),
  spend_vnd numeric, impressions bigint, clicks bigint, leads int,
  PRIMARY KEY (spend_date, ad_campaign_id)
);
CREATE TABLE crm.ad_lead (
  lead_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  ad_campaign_id uuid REFERENCES crm.ad_campaign(ad_campaign_id),
  party_id uuid REFERENCES crm.party(party_id),   -- nullable cho tới resolve
  psid text, captured_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE crm.ad_attribution (
  attribution_id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  party_id uuid REFERENCES crm.party(party_id),
  ad_campaign_id uuid REFERENCES crm.ad_campaign(ad_campaign_id),
  order_code text,                  -- đơn quy cho ad
  touch_type text,                  -- click|lead|message_ref
  model text DEFAULT 'last_touch',
  attributed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON crm.segment_member (party_id);
CREATE INDEX ON crm.campaign_target (assigned_user_id, status);
```

## Related Code Files
- **Tạo:** `crm/migrations/0008_segments_campaigns.up.sql`, `0009_ads_tracking.up.sql`, Go segment-rule evaluator + campaign handler, `crm/sync/ingest_fb_ads.py` (spend/lead từ FB Ads API + messenger ad-referral).
- **Đọc:** `fact_marketing_spend.sql`, `dim_fb_ads.sql` (field tham khảo), `dim_channels` (mapping kênh).

## Implementation Steps
1. Migration 0008 (segment/campaign) + 0009 (ads).
2. Segment-rule evaluator: dịch `definition` jsonb → query trên party+wh_cache → upsert `segment_member` (refresh động).
3. Campaign builder: từ segment → sinh `campaign_target` + (tuỳ chọn) task cho NV.
4. Conversion tracker: match `campaign_target.party` ↔ order_code mới (sau scheduled_at) từ wh_cache/warehouse → set converted_*.
5. Ads ingest: FB Ads spend + lead; messenger ad-referral → `ad_lead` → resolve party.
6. Báo cáo ROI campaign + ad (revenue vs spend).

## Todo
- [ ] Migration 0008 + 0009
- [ ] Segment rule evaluator
- [ ] Campaign → targets (+tasks)
- [ ] Conversion tracker (order_code match)
- [ ] FB Ads spend/lead ingest
- [ ] Ad attribution + ROI report

## Success Criteria
- Segment "VIP at-risk" auto cập nhật member theo wh_cache; campaign sinh target + giao NV; khách trong campaign đặt đơn → `converted_order_code` set, ROI tính được; ad lead resolve về party, đơn quy về ad.

## Risk Assessment
- **Attribution không chuẩn** (no warehouse precedent) → v1 last-touch đơn giản, ghi rõ `model`; không cố đa-touch.
- **consent_contact=false** (Phase 03) → loại khỏi campaign target (compliance).
- **Conversion match sai** → cửa sổ thời gian + chỉ tính đơn sau touch.

## Security
- Danh sách campaign = PII hàng loạt → export role-gated, log truy cập.

## Next Steps
→ Conversion/winback outcome có thể là field ghi ngược Sapo (Phase 07). → ROI feed lại warehouse (câu hỏi mở #4).
