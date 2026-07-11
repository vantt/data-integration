---
title: "Channel-Based CROSSBORDER Customer Detection (US Order Signal)"
description: "Bổ sung tín hiệu channel_name='US' (tự động từ Sapo ingestion) vào phân loại customer_type=CROSSBORDER và is_us_gift_recipient, thay vì chỉ dựa vào manual group-tag hiện đang có gap (untagged → mặc định RETAIL)."
status: completed
priority: P2
branch: "main"
tags: ["dbt", "dim_customers", "crossborder", "customer-segmentation"]
blockedBy: []
blocks: []
created: "2026-07-08T09:28:38.976Z"
createdBy: "ck:plan"
source: skill
---

# Channel-Based CROSSBORDER Customer Detection (US Order Signal)

## Overview

`dim_customers.customer_type = 'CROSSBORDER'` và `is_us_gift_recipient` hiện CHỈ dựa vào manual Sapo customer-group tag (`customer_group_code`/`customer_group_name` LIKE `%TYPE_CROSSBORDER%`/`%CTN00014%` — `dim_customers.sql:197-211`, `:300-306`). Comment trong code đã tự cảnh báo: "Legacy groups whose code was not yet re-tagged... so the migration backlog doesn't silently default to RETAIL" — nhưng `ELSE 'RETAIL'` (line 210) VẪN default untagged customers về RETAIL. Khách "đơn Mỹ" (US gift-fulfilment recipient) chưa được tag đúng trong Sapo sẽ lọt vào RETAIL, không phân biệt được với khách lẻ trong nước.

**Phát hiện trong phiên trước** (khi làm plan `260708-1501-gift-purchase-sku-action-scenario`): pipeline đã có sẵn tín hiệu đáng tin cậy hơn — `int_us_shipment_line_prices.sql:16-26` xác định "đơn Mỹ" qua `dim_channels.channel_name = 'US'`, một kênh bán hàng Sapo riêng được gán TỰ ĐỘNG lúc ingest đơn hàng, KHÔNG qua tag thủ công của nhân viên. Tín hiệu này không có gap "chưa tag thì rơi về RETAIL" như group-tag.

**Nguyên tắc fix**: KHÔNG hardcode danh sách customer_id cụ thể (vi phạm nguyên tắc "no one-off hardcode fixes" — data gap tái diễn cần logic idempotent trong pipeline, không phải patch thủ công). Thay vào đó: thêm `OR EXISTS (đơn có channel_name='US')` vào CẢ 2 biểu thức hiện có — một rule xác định (deterministic), tự động healing khi có đơn mới, không phụ thuộc nhân viên tag kịp hay không.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Channel-Based Detection Logic](./phase-01-channel-based-detection-logic.md) | Done |
| 2 | [Blast-Radius Validation](./phase-02-blast-radius-validation.md) | Done |
| 3 | [Downstream Refresh and Serving Sync](./phase-03-downstream-refresh-and-serving-sync.md) | Done |

## Dependency order

`1 (detection logic) → 2 (validate blast radius before shipping) → 3 (refresh downstream serving)`

## Cross-plan context

- **Related to, but NOT blocking/blocked by** `plans/260708-1501-gift-purchase-sku-action-scenario` (action-queue gift/purchase classification plan) — that plan's Phase 4 already excludes `is_us_gift_recipient=TRUE` customers from action-queue eligibility using the CURRENT (leaky) group-tag-only definition; this plan strengthens that same flag's underlying accuracy. No ordering dependency: that plan works correctly today with the current flag (just less complete coverage); this plan improves coverage independently. If both ship, the action-queue plan's exclusion gets MORE effective automatically (no code change needed there — `is_us_gift_recipient` is a boolean it already reads).
- **User-supplied reference data**: `plans/reports/us-customers-260606.csv` (818 rows: customer_id, customer_code, full_name, phone, us_order_count, first_us_order, last_us_order) — appears to be a prior manual/semi-manual extraction of US-order customers. Use as a cross-check/validation reference in Phase 2 (does the new `channel_name='US'` derivation roughly match this list's population?), NOT as an input to the pipeline logic itself (the fix must be self-deriving from `fact_orders`/`dim_channels`, not this static file).

## Key Constraints

- `dim_customers` is **incremental** — this change requires `--full-refresh` (per `feedback_dim_customers_incremental_full_refresh.md`), run via dbt CLI directly in container with lock-retry pattern.
- `customer_type = 'RETAIL'`/`'CROSSBORDER'` is consumed by 8+ downstream models (confirmed via grep): `mart_customer_action_queue.sql`, `mart_customer_sku_action_queue.sql`, `int_customer_benchmarks.sql`, `int_customer_entry_attributes.sql`, `mart_retention_waterfall_monthly.sql`, `mart_cohort_retention.sql`, `mart_customer_status_snapshot_monthly.sql` — reclassifying previously-mistagged customers WILL shift numbers in retention/cohort/benchmark marts. This is the CORRECT behavior (fixing bad data), but must be quantified before shipping (Phase 2) so downstream dashboard consumers aren't surprised.
- `customer_type` is synced to CRM cache (**correction, verified 2026-07-08**: actual column is `wh_customer_tier.customer_type`, NOT `wh_customer_base` as originally stated here — `wh_customer_base` has no `customer_type` column) — no schema change needed (existing column), but reverse-ETL must re-run after the warehouse refresh to pick up reclassified customers.
- `is_us_gift_recipient` is NOT currently synced to CRM cache — no CRM-side change needed for this plan (it's consumed only inside dbt mart WHERE clauses, per the other plan's Phase 4).
- After `dim_customers` full-refresh → stop Metabase → `bootstrap_serving_views.py` → restart (per `feedback_duckdb_view_rebuild.md`).
- Open DuckDB files `read_only=True` always (per `feedback_duckdb_always_readonly.md`).

## Acceptance Criteria

- [x] `dim_customers.sql` adds a `us_channel_customers` CTE (or equivalent) deriving "customer has ≥1 order on `dim_channels.channel_name='US'`" and ORs it into both `customer_type`'s CROSSBORDER branch and `is_us_gift_recipient`.
- [x] No customer_id hardcoding anywhere in the fix — purely derived from `fact_orders`/`dim_channels` join.
- [x] Blast radius quantified: count of customers flipping RETAIL→CROSSBORDER, cross-checked against `us-customers-260606.csv` for plausibility.
- [x] Full-refresh completes without lock errors; downstream marts (retention/cohort/benchmark) re-run successfully with new customer_type values.
- [x] CRM `customer_type` reflects reclassified customers after reverse-ETL re-run. **Correction**: actual column lives in `wh_customer_tier` (not `wh_customer_base` as originally stated in Key Constraints below — `wh_customer_base` has no `customer_type` column; verified via `PRAGMA table_info` against live `cache.db`). Reverse-ETL already syncs both tables correctly regardless.
- [x] Existing manual-tag-based CROSSBORDER detection is NOT removed — the channel signal is additive (`OR`), preserving any customers already correctly tagged but who (for whatever reason) have no US-channel order on record.

## Completion Summary (2026-07-08)

All 3 phases implemented, validated, and deployed to production. Real measured results:

- **Blast radius**: 773 customers reclassified RETAIL→CROSSBORDER (754→1527 CROSSBORDER; WHOLESALE=161/PARTNER=11 unchanged — precedence preserved, only transition type observed was RETAIL→CROSSBORDER).
- **CSV cross-check** (`us-customers-260606.csv`, 817 rows): 813 now CROSSBORDER; remaining 4 are WHOLESALE by design (higher-precedence branch) with `is_us_gift_recipient=TRUE` set independently, exactly per confirmed Unresolved Question #1/#2 answers.
- **Hard gate**: PASSED (773 vs 817 CSV rows — same order of magnitude, not >10x, not near-zero).
- **Downstream**: all 7 marts rebuilt successfully (non-zero row counts); reclassified customers confirmed absent from `mart_customer_action_queue`/`mart_customer_sku_action_queue` (both filter `customer_type='RETAIL'`).
- **Wiring verification**: in addition to direct `dbt run --full-refresh`, materialized `marts/dim_customers` via a real Dagster asset run (`dagster asset materialize`) — 14/14 dbt tests/checks passed (accepted_values, relationships, uniqueness), confirming no regression through the actual orchestrated path.
- **Serving/CRM sync**: Metabase serving views (`bootstrap_serving_views.py`) and CRM `cache.db` (`crm/refresh.sh`) both confirmed reflecting the new distribution (RETAIL=5902, CROSSBORDER=1527, WHOLESALE=161, PARTNER=11).
- **One real bug caught and fixed during implementation**: initial `EXISTS` subquery used an unqualified `customer_key` reference that self-correlated to `us_channel_customers` instead of the outer row, flipping customer_type=CROSSBORDER for 7429/7601 customers (RETAIL→0). Caught immediately after the first full-refresh by inspecting the distribution (this is exactly the failure mode the Phase 2 hard gate was designed to catch), fixed by qualifying as `joined_data.customer_key`, re-verified. `code-reviewer` subagent also caught the same unqualified-reference bug reproduced in the staff-guide doc's illustrative SQL snippet — fixed.
- **Code review**: `code-reviewer` subagent found no blocking issues in the final SQL; optional/non-blocking suggestions (hoist duplicated EXISTS into `joined_data`, add `is_us_gift_recipient` schema.yml test) left as-is per YAGNI/scope.

## Unresolved Questions

1. Should `WHOLESALE`/`PARTNER`/`STAFF`/`KOL` branches (which come BEFORE the CROSSBORDER check in the CASE cascade, `dim_customers.sql:198-206`) take precedence over the new channel-based CROSSBORDER signal for a customer who happens to be tagged WHOLESALE but also has a US-channel order? Current design: yes, CASE WHEN order is unchanged, so higher-precedence branches still win — confirm this is desired (a wholesale account that occasionally ships via the US channel should probably stay WHOLESALE, not flip to CROSSBORDER).
2. `is_us_gift_recipient` combines with `customer_type` at the boolean level but is a SEPARATE column — should a customer who is channel-derived CROSSBORDER but was previously a different `customer_type` branch (e.g. WHOLESALE) also get `is_us_gift_recipient=TRUE`? Current design: yes (the two expressions are independently OR'd, not mutually coupled) — confirm this is fine, since `is_us_gift_recipient` is meant to flag "this shipment relationship" independent of overall account classification.

## Validation Log

### Session 1 — 2026-07-08
**Trigger:** `/ck:plan validate` (no red-team run — plan is smaller scope, additive-only logic)
**Questions asked:** 2

#### Verification Results
- **Tier:** Standard (3 phases → Fact Checker + Contract Verifier)
- **Claims checked:** all key claims verified directly during plan authoring via Read/Grep this session — `fact_orders.customer_key` (`fact_orders.sql:109,125`), `dim_channels.channel_name` (`dim_channels.sql:45,111`), `dim_customers.sql` CTE structure and exact line numbers for `customer_type`/`is_us_gift_recipient` (`dim_customers.sql:6-24,197-211,300-306`), all 7 downstream consumer files (grep-confirmed), `cache_schema.sql:136` (`customer_type` column), `int_us_shipment_line_prices.sql:16-26` reference pattern.
- **Verified:** all sampled | **Failed:** 0 | **Unverified:** 0

#### Questions & Answers

1. **[Architecture]** Unresolved Question #1 — khi khách vừa tag WHOLESALE vừa có đơn US-channel, WHOLESALE có nên thắng (giữ nguyên CASE order) không?
   - Options: Đúng — giữ nguyên precedence (Recommended) | Channel signal nên thắng, đổi thứ tự CASE
   - **Answer:** Đúng — giữ nguyên precedence
   - **Rationale:** Tài khoản có quan hệ thương mại chính (đại lý/sỉ) mà thỉnh thoảng ship qua US vẫn nên coi là WHOLESALE trước — channel chỉ là tín hiệu bổ sung cho nhóm chưa có tag rõ ràng khác.

2. **[Risk]** Phase 2 blast-radius: nếu số reclassify quá khác biệt so với CSV 818 dòng, có nên hard-gate chặn Phase 3?
   - Options: Có — dừng điều tra nếu bất thường (Recommended) | Không — chỉ report
   - **Answer:** Có — hard gate
   - **Rationale:** Số lệch quá lớn có thể báo hiệu join sai (vd trùng lặp trong dim_channels) — an toàn hơn khi phát hiện trước khi refresh serving layer.

#### Confirmed Decisions
- CASE branch order unchanged (WHOLESALE/PARTNER/STAFF/KOL still precede CROSSBORDER) — closes Unresolved Question #1, no Phase 1 change needed.
- Phase 2's blast-radius check promoted to a hard gate — Phase 3 blocked until an implausible reclassification count is investigated and explained.

#### Action Items
- [x] Update Phase 2 to make the blast-radius plausibility check an explicit hard gate blocking Phase 3
- [x] Close Unresolved Question #1 (no code change needed)

#### Impact on Phases
- Phase 2: blast-radius check becomes a hard gate (see Phase 2 file)
- Phase 1: no change — Unresolved Question #1 confirmed as designed

### Whole-Plan Consistency Sweep
- Files reread: plan.md, phase-01, phase-02, phase-03
- Decision deltas checked: 2
- Reconciled stale references: Phase 2 blast-radius check wording (informational → hard gate)
- Unresolved contradictions: 0
