---
phase: 4
title: "Scenario Registry and Tier-Aware Branching"
status: pending
priority: P1
dependencies: [3]
---

# Phase 4: Scenario Registry and Tier-Aware Branching

## Overview

Chuẩn bị cơ chế "tính toán luôn sẵn sàng, bật/tắt qua registry" (chốt với user, KHÔNG khôi phục Stage B rule-engine). Join `mart_customer_tier` vào 2 mart action-queue để tier/contactable trở thành predicate khả dụng cho scenario branching (không chỉ hiển thị). Thêm scenario `GIFT_TO_PURCHASE` cho luồng `gift_only` từ Phase 3.

## Requirements

- Functional: `seed_action_scenario_registry.csv` điều khiển bật/tắt action_type ở output layer, không cần sửa SQL branching để tắt 1 scenario.
- Functional: `GIFT_TO_PURCHASE` action_type mới, dùng `supply_stream='gift_only'` từ Phase 3.
- Functional: cả 2 mart dùng `mart_customer_tier.is_contactable`/`strategic_tier` thay vì tự tính `is_contactable` riêng.
- Functional: loại khách "US gift-fulfilment recipient" (`dim_customers.is_us_gift_recipient`) khỏi eligibility của cả 2 mart — bổ sung sau khi user phát hiện nhóm này lọt vào `customer_type='RETAIL'` do gap tagging (xem ghi chú step 2b).
- Non-functional: khi registry mặc định `enabled=true` cho toàn bộ action_type hiện có (7+5), hành vi output phải giống hệt trước khi có registry (backward-compat) — TRỪ nhóm `gift_only` (xem Deploy Sequencing ở `plan.md`, thay đổi có chủ đích).

> **Sửa sau red-team**: KHÔNG khung "join mart_customer_tier" như dedup `is_contactable` — `dim_customers.is_contactable` mới là nguồn canonical (`mart_customer_tier.is_contactable` chỉ passthrough nó), 3 nơi hiện tại đều ra cùng giá trị. Lý do thật của JOIN là lấy `strategic_tier`. Việc chuyển `is_contactable` sang dùng `mart_customer_tier` là **thay đổi ngữ nghĩa có chủ đích** (user decision): `mart_customer_tier.is_contactable` dựa trên `source_contact_quality` (loại cả SĐT relay marketplace bị `*`-che), chặt hơn biểu thức `phone IS NOT NULL AND phone <> ''` hiện tại — một số khách sẽ chuyển từ contactable=TRUE sang FALSE. Xem `mart_customer_tier.sql:11,28,74` vs `mart_customer_sku_action_queue.sql:44`.

## Architecture

```
seed_action_scenario_registry.csv
  action_type, mart, enabled, scenario_group, description_vi

mart_customer_tier (strategic_tier, is_contactable, tier_reason)
         │
         ├──► JOIN vào mart_customer_action_queue     (lấy strategic_tier mới + is_contactable
         └──► JOIN vào mart_customer_sku_action_queue  chặt hơn — thay local phone-check, có chủ đích)

int_customer_sku_supply_tracking (supply_stream, Phase 3)
         │
         ▼
mart_customer_sku_action_queue
  CASE WHEN supply_stream = 'purchased' THEN <5 action_type hiện có, KHÔNG đổi>
       WHEN supply_stream = 'gift_only' THEN <GIFT_TO_PURCHASE, logic mới>
  END AS action_type
         │
         ▼
  LEFT JOIN seed_action_scenario_registry r
    ON classified.action_type = r.action_type AND r.mart = 'mart_customer_sku_action_queue'
  WHERE classified.action_type IS NOT NULL
    AND COALESCE(r.enabled, TRUE) = TRUE   -- default TRUE if action_type missing from registry (safety)
```

## Related Code Files

- Create: `transformation/seeds/seed_action_scenario_registry.csv`
- Modify: `transformation/models/marts/customer/mart_customer_sku_action_queue.sql`
- Modify: `transformation/models/marts/customer/mart_customer_action_queue.sql`
- Modify: `transformation/models/marts/schema.yml` (registry seed doc + `unique_combination_of_columns` test, updated action_type enum tests for both marts, new `GIFT_TO_PURCHASE` value)
- Modify: `transformation/dbt_project.yml` (seed `+column_types: {enabled: boolean}` for `seed_action_scenario_registry`)
- Read only (reference, do not modify): `transformation/models/marts/core/dim_customers.sql` (`is_us_gift_recipient` already exists, lines 300-306)

## Implementation Steps

### 1. Registry seed

```csv
action_type,mart,enabled,scenario_group,description_vi
REORDER_OVERDUE,mart_customer_sku_action_queue,true,reorder_cadence,Het lieu trinh qua han
REORDER_NUDGE,mart_customer_sku_action_queue,true,reorder_cadence,Het lieu trinh hom nay
REORDER_PREEMPT,mart_customer_sku_action_queue,true,reorder_cadence,Sap het lieu trinh
PROGRESS_CHECK,mart_customer_sku_action_queue,true,journey,Hoi cam nhan D12-16
USAGE_FOLLOWUP,mart_customer_sku_action_queue,true,journey,Xac nhan bat dau dung D5-9
GIFT_TO_PURCHASE,mart_customer_sku_action_queue,false,gift_conversion,Tung duoc tang chua tung mua
CALL_NOW,mart_customer_action_queue,true,at_risk,VIP dang nguoi goi ngay
MANUAL_RISK_REVIEW,mart_customer_action_queue,true,risk,NV gan tag rui ro
REORDER_NUDGE,mart_customer_action_queue,true,reorder_cadence,Qua han nhip mua
REORDER_PREEMPT,mart_customer_action_queue,true,reorder_cadence,Sap toi han nhip mua
WIN_BACK,mart_customer_action_queue,true,winback,Da churn can offer
SECOND_ORDER,mart_customer_action_queue,true,activation,Mua 1 lan day don 2
HIGH_CANCEL_RISK,mart_customer_action_queue,true,risk,Ty le huy cao
```
Ship `GIFT_TO_PURCHASE` with `enabled=false` initially — infra ready, scenario off until timing rule (Unresolved Question #1 in plan.md) is reviewed and the rationale copy is approved. Flip to `true` via seed edit + `dbt seed && dbt run`, no code change.

Note: `(action_type, mart)` is the natural key — `mart_customer_action_queue` and `mart_customer_sku_action_queue` both have a `REORDER_NUDGE`/`REORDER_PREEMPT` value but at different grains; keep them as distinct registry rows scoped by `mart`.

**Boolean typing (post red-team, Security Adversary Finding 3 + Failure Mode Finding 5)**: DuckDB's dbt-seed type inference is a known repo footgun (`feedback_duckdb_integer_underscore.md`) — an untyped `enabled` column can load as VARCHAR, silently breaking the `COALESCE(reg.enabled, TRUE) = TRUE` boolean comparison (fails open, meaning a "disabled" scenario could ship live). Force the type explicitly in `dbt_project.yml` seed config, mirroring the existing pattern for other boolean seed columns:
```yaml
seeds:
  sapo_warehouse:
    seed_action_scenario_registry:
      +column_types:
        enabled: boolean
```

**Uniqueness test (post red-team, Assumption Destroyer Finding 6)**: no constraint currently stops a duplicate `(action_type, mart)` row from fanning out the `LEFT JOIN` (doubling cards) or a mart-name typo from silently failing the JOIN (which `COALESCE(reg.enabled, TRUE)` then fails OPEN on — a disabled scenario re-enables itself with no error). Add to `transformation/models/marts/schema.yml` under the seed's model entry:
```yaml
- name: seed_action_scenario_registry
  tests:
    - dbt_utils.unique_combination_of_columns:
        combination_of_columns: [action_type, mart]
```
Also add a build-time sanity check (dbt test or manual query before each deploy) asserting every distinct `action_type` actually emitted by each mart has exactly one matching registry row for that mart — catches mart-name drift/typos at build time instead of failing open silently.

### 2. Join `mart_customer_tier`, drop duplicated `is_contactable`

In both marts, replace:
```sql
(phone IS NOT NULL AND phone <> '') AS is_contactable
```
with a join to `mart_customer_tier`:
```sql
tier AS (
    SELECT customer_key, strategic_tier, is_contactable, tier_reason
    FROM {{ ref('mart_customer_tier') }}
)
-- ... LEFT JOIN tier t ON cu.customer_key = t.customer_key
-- SELECT t.is_contactable, t.strategic_tier
```
This makes `strategic_tier` available as a branching predicate (not just a display column) for the first time.

### 2b. Exclude US gift-fulfilment recipients (added mid-session, user-reported gap — not from red-team)

`dim_customers.customer_type = 'RETAIL'` (the eligibility filter both marts already use) is derived from **manual Sapo customer-group tagging** (`dim_customers.sql:187-211`) with an explicit `ELSE 'RETAIL'` default for untagged/legacy groups (`dim_customers.sql:210`). A VN recipient of a US-shipped gift order (CROSSBORDER segment) whose Sapo group was never (re)tagged falls through to `customer_type='RETAIL'` and is indistinguishable from a domestic retail customer to the current filter — meaning FineJapan regimen-reorder scenarios (`REORDER_*`, `USAGE_FOLLOWUP`) can fire for a shipping recipient who isn't the actual buyer/decision-maker.

A more reliable flag already exists for exactly this reason: `dim_customers.is_us_gift_recipient` (`dim_customers.sql:300-306`, added 2026-07-06 specifically because `customer_type` alone is unreliable for this segment). Add it to the customer eligibility filter in both marts, alongside `customer_type = 'RETAIL'` (not instead of — keep both as defense in depth):
```sql
WHERE customer_type = 'RETAIL'
  AND customer_id != 'Unknown'
  AND NOT is_us_gift_recipient   -- new: exclude even RETAIL-tagged US gift-fulfilment recipients
```

### 3. `GIFT_TO_PURCHASE` branch in `mart_customer_sku_action_queue.sql`

Add to the `classified` CASE WHEN cascade (after the existing 5-branch cascade, gated on `supply_stream`):
```sql
CASE
    WHEN s.supply_stream = 'gift_only'
         AND DATE_DIFF('day', s.last_purchase_date, CURRENT_DATE) BETWEEN 14 AND 45
        THEN 'GIFT_TO_PURCHASE'
    WHEN s.supply_stream = 'purchased' THEN <existing 5-branch CASE, unchanged>
    ELSE NULL
END AS action_type
```
**Timing rule placeholder (14-45 days since gift received)** — flagged as Unresolved Question #1 in plan.md; do not treat as final. Rationale draft: give the customer time to try the sample (avoid pestering day-1) but follow up before the "trial" memory fades. Needs product/CS input before enabling.

`action_rationale` for `GIFT_TO_PURCHASE`:
```sql
WHEN action_type = 'GIFT_TO_PURCHASE'
    THEN 'Được tặng ' || display_name || ' ' || days_since_order || ' ngày trước, chưa từng mua — hỏi cảm nhận, gợi ý mua chính'
```

### 4. Apply registry filter

At the end of both mart SELECTs, add:
```sql
LEFT JOIN seed_action_scenario_registry reg
    ON classified.action_type = reg.action_type
   AND reg.mart = '<this_mart_name>'
WHERE classified.action_type IS NOT NULL
  AND COALESCE(reg.enabled, TRUE) = TRUE
```

### 5. Restart `data_platform` (new seed + node) → `dbt seed --select seed_action_scenario_registry` → `dbt run --select mart_customer_tier mart_customer_sku_action_queue mart_customer_action_queue`

## Success Criteria

- [ ] `seed_action_scenario_registry.csv` loaded with `enabled` as BOOLEAN type (explicit `+column_types`), both marts join it, `enabled=false` rows disappear from output with zero SQL change
- [ ] `dbt_utils.unique_combination_of_columns` test on `(action_type, mart)` passes; every emitted action_type has exactly one matching registry row per mart
- [ ] `GIFT_TO_PURCHASE` computed but suppressed (ships `enabled=false`) — verify it WOULD appear if flipped (test query with `enabled=true` override)
- [ ] Both marts join `mart_customer_tier` for `strategic_tier` + `is_contactable`; local phone-presence `is_contactable` CTE removed from both (this is an intentional semantic tightening for masked/obfuscated phones, not a no-op dedup — see Requirements note)
- [ ] `mart_customer_sku_action_queue`/`mart_customer_action_queue` exclude `is_us_gift_recipient = TRUE` customers even when `customer_type = 'RETAIL'`
- [ ] `mart_customer_action_queue`'s 7 action_type values, and `mart_customer_sku_action_queue`'s 5 existing action_types **for `supply_stream='purchased'` rows**, produce identical output vs pre-Phase-4 baseline (registry defaults preserve current behavior). **`gift_only`-stream rows are NOT expected to match baseline** — they previously emitted `REORDER_*`/`USAGE_FOLLOWUP` under the undifferentiated old logic and now emit `GIFT_TO_PURCHASE` (suppressed while `enabled=false`) — this is the accepted gap from Phase 3, not a regression to chase.
- [ ] `strategic_tier` available as a column in both mart outputs (enrichment, ready for future tier-gated branches — not required to add new tier-gated CASE branches in this phase beyond what's specified)

## Risk Assessment

- **Medium risk**: touching the WHERE/JOIN of 2 live marts feeding CRM. Registry default (`COALESCE(reg.enabled, TRUE)`) is a safety net — a missing registry row never silently drops an existing action_type. This same fail-open default is also the risk for accidental re-enablement on a typo/type-mismatch — mitigated by the boolean typing + uniqueness test above.
- **Risk**: seed-based enable/disable is per-`(action_type, mart)`, not per-customer-segment — if a future need arises to enable a scenario ONLY for e.g. LIVE_CORE tier, that's a CASE WHEN change, not a registry change (registry only controls on/off, per explicit user decision — document this boundary clearly to avoid scope creep later).
- **Rollback**: registry can be reverted to all-`true` (current behavior) via seed edit; mart SQL changes are additive (new columns/joins), existing action_type logic for `supply_stream='purchased'` and the 7 customer-level types is untouched. Note: rollback does NOT undo CRM-side action-state mutations already applied by reverse-ETL — see `plan.md` § Deploy Sequencing.
