---
title: "Gift vs Purchase Line-Item Classification + Action-Queue Scenario Mechanism"
description: "Phân loại line-item hàng bán vs hàng tặng (chiết khấu 100%) tại warehouse, sửa bug supply-tracking lẫn hàng tặng vào nhịp tái mua, và chuẩn bị cơ chế bật/tắt kịch bản action-queue theo tier/contactable/gift-stream."
status: done
priority: P2
branch: "main"
tags: ["dbt", "action-queue", "gift-classification", "customer-tier", "crm-sync"]
blockedBy: []
blocks: []
created: "2026-07-08T08:23:04.604Z"
createdBy: "ck:plan"
source: skill
---

# Gift vs Purchase Line-Item Classification + Action-Queue Scenario Mechanism

## Overview

Hiện tại pipeline không phân biệt line-item "hàng bán" vs "hàng tặng" (chiết khấu 100%, `line_amount = 0`). Hệ quả cụ thể đã xác nhận:

1. **Bug supply-tracking**: `int_customer_sku_supply_tracking` (nguồn của SKU action-queue) cộng dồn TẤT CẢ quantity — kể cả hàng tặng — vào `effective_supply_days`. Một khách được tặng kèm 1 hộp Metabo trong đơn premium sẽ bị đẩy lùi nhịp nhắc tái mua y hệt như thể họ tự mua hộp đó.
2. **Cơ chế kịch bản đơn giản, chưa "specific hơn"**: 2 mart action-queue (`mart_customer_action_queue` 7 action_type, `mart_customer_sku_action_queue` 5 action_type) branch hoàn toàn dựa trên recency/frequency/depletion-day; `mart_customer_tier` (7-tier `strategic_tier` + `is_contactable`, đã deploy) **không** được join vào logic sinh action — tier/contactable hiện chỉ ảnh hưởng filter hiển thị phía CRM, không ảnh hưởng việc mart có sinh ra action hay không.
3. Không có kịch bản nào cho khách "chỉ từng được tặng SKU X, chưa từng chủ động mua" — theo `finejapan-gift-entry-sku-zero-rev-260622-1720-report.md`, đây là nhóm cơ hội chuyển đổi rõ ràng (Metabo/Gaba/Coix bị tặng kèm 67-78% trong đơn multi-SKU, nhưng khi mua solo thì 89-90% là doanh thu thật).

**Nguyên tắc gift = `line_amount = 0` (STRICT)** — tái dùng chính xác định nghĩa đã validate ở finance layer (`int_order_promo_goods_cost.is_gift_no_invoice`), KHÔNG dùng ngưỡng `discount_rate` (vì `unit_price=0` không tạo ra `discount_rate` — field này NULL khi `discount_amount=0`). Không gộp trường hợp `distributed_discount_amount` (voucher/campaign order-level phủ hết 1 line) vào định nghĩa gift — đó là "khách dùng voucher 100%", khác bản chất với "rep tặng tay không thu tiền".

**Quyết định luồng đã chốt với user** (xem chi tiết Phase 3): 1 line hàng tặng thuộc **luồng mua** (`supply_stream='purchased'`, cộng dồn supply_days như hiện tại) nếu khách đã TỪNG mua SKU đó (bất kỳ đơn nào, không cần cùng đơn); nếu khách CHƯA TỪNG mua SKU đó — chỉ toàn được tặng — thì thuộc **luồng tặng riêng** (`supply_stream='gift_only'`), track supply_days độc lập, feed scenario mới `GIFT_TO_PURCHASE`.

> **Phạm vi thực tế của "fix" (làm rõ sau red-team — 3/3 reviewer độc lập chỉ ra Overview đoạn trên dễ đọc nhầm)**: bug "gift đẩy lùi nhịp tái mua" chỉ được sửa cho khách **CHƯA TỪNG mua SKU đó** (chuyển sang `gift_only`, tách khỏi nhịp tái mua). Khách **đã từng mua** SKU đó thì gift qty **vẫn cộng dồn vào `effective_supply_days` y như hiện tại** — đây là quyết định có chủ đích của user (case a), không phải phần còn sót lại của bug. Ví dụ "khách được tặng kèm Metabo trong đơn premium" ở trên chỉ được fix triệt để nếu khách đó chưa từng tự mua Metabo; nếu đã từng mua, gift box vẫn đẩy lùi nhịp nhắc — hành vi này giữ nguyên theo thiết kế.

**Cơ chế mở rộng kịch bản đã chốt**: KHÔNG khôi phục Stage B rule-engine đã hoãn (`plans/260619-1030-crm-nba-resell-engine/phase-03-rule-engine-and-ladders.md`, hoãn 2026-06-19 vì active base còn nhỏ ~83 LIVE_CORE — lý do đó vẫn đúng, không đảo ngược). Thay vào đó: mở rộng CASE WHEN hiện có trong 2 mart + thêm **registry bật/tắt kịch bản** (`seed_action_scenario_registry.csv`) — mọi logic tính toán luôn sẵn sàng chạy, nhưng scenario chỉ xuất hiện ở output khi `enabled=true` trong registry. Đổi bật/tắt = sửa seed + `dbt seed && dbt run`, không cần sửa SQL branching.

## Phases

| Phase | Name | Status |
|-------|------|--------|
| 1 | [Gift Line Classification](./phase-01-gift-line-classification.md) | Done |
| 2 | [SKU Gift-Rate Profile](./phase-02-sku-gift-rate-profile.md) | Done |
| 3 | [Dual-Stream Supply Tracking](./phase-03-dual-stream-supply-tracking.md) | Done |
| 4 | [Scenario Registry and Tier-Aware Branching](./phase-04-scenario-registry-and-tier-aware-branching.md) | Done |
| 5 | [CRM Sync and Display](./phase-05-crm-sync-and-display.md) | Done |

## Dependency order

`1 (is_gift flag) → 2 (SKU gift-rate, parallel to 3) → 3 (dual-stream supply, needs is_gift) → 4 (registry + branching, needs supply_stream + tier join) → 5 (CRM sync, needs final mart columns)`

## Cross-plan context

- **Does NOT reopen** `plans/260619-1030-crm-nba-resell-engine` Stage B (rule engine, phases B1-B5, all ⛔ deferred per that plan's `plan.md:38`) — explicit user decision this session: keep tactical, revisit Stage B only when active base grows (per that plan's own deferral reasoning).
  > **Registry ≠ NBA Engine (clarified this session)**: Phase 4's scenario registry is a feature-flag layer on top of the EXISTING static CASE WHEN branching — one candidate per customer, no scoring, no state. Stage B's NBA Engine is a different architecture: B1 warehouse scoring (percentile/rank, multiple scored candidate objectives per customer) → B2 CRM fusion scoring (`final_score` = base score adjusted by live state: recent contact, open task, rep insight, consent gate) → B3 rule engine with an objective ladder (hard priority order) AND a contactability ladder (stateful phone→email→zalo fallback, tracks what's been tried) → B4 CS surface → B5 feedback loop. Registry only toggles an action_type's visibility on/off; it cannot rank multiple candidates or remember contact-channel state. Stage B stays blocked on unresolved design gates (`discussion.md` §14.1 weighting formula, §14.2 objective ladder, §14.3 contactability state schema, §14.5 rules representation) plus the business call that ~83 LIVE_CORE customers don't yet justify that investment — this plan does not change either blocker.
- **Builds on** `plans/archive/260629-1215-customer-discount-tracking` (done 2026-07-08) — reuses `std_order_items.discount_rate`/`line_amount` plumbing, does not modify its 8 dim_customers discount fields.
- **Reuses** `mart_customer_tier` (`plans/260619-1030-crm-nba-resell-engine/phase-a1-customer-tiering-mart.md`, deployed) as the source for `strategic_tier` (new to both action-queue marts) and `is_contactable`.
  > **Correction (red-team)**: `dim_customers.is_contactable` is the CANONICAL source (`mart_customer_tier.is_contactable` is itself a passthrough of it) — it is not a duplicate to remove. The 2 action-queue marts currently re-derive the identical `(phone IS NOT NULL AND phone <> '')` expression locally; only those 2 copies are being replaced with the tier JOIN, and the JOIN's real purpose is to obtain `strategic_tier` (not to "dedup" `is_contactable`, which was never actually duplicated in a meaningful sense — all 3 expressions agree today). **User decision**: switch to `mart_customer_tier.is_contactable` anyway (stricter — correctly excludes obfuscated `*`-masked marketplace-relay phones that the phone-presence check would wrongly treat as contactable) — this is an intentional behavior change, not a no-op swap. See Phase 4.
- **Informed by** `plans/reports/finejapan-gift-entry-sku-zero-rev-260622-1720-report.md` (SKU gift-rate pattern) and `docs/architecture/order-pl/discount-classification.md` (order-level discount taxonomy — stays independent from line-item `is_gift`).

## Deploy Sequencing (added post red-team — see Red Team Review)

Phase 3+4 must ship in the same dbt deploy window (Phase 3 alone breaks the grain Phase 4 consumes), but reverse-ETL must NOT run against that window until the regression diff is verified — otherwise CRM action-state (dismissals, open tasks, `action_id`s) mutates irreversibly before the diff can gate it. Ordered runbook:

1. **Pause** the CRM reverse-ETL Dagster schedule before starting (confirmed pausable via Dagster UI/CLI — validation session 2026-07-08). Exact schedule/job name not pinned in this plan; grep `orchestration/` for the reverse-ETL asset/schedule definition at the start of Phase 5 implementation and record it in the actual runbook used for deploy.
2. `dbt seed --select seed_action_scenario_registry` (Phase 4) — verify `enabled` loads as BOOLEAN (see Phase 4 fix), not VARCHAR.
3. `dbt run --select int_customer_sku_supply_tracking mart_customer_tier mart_customer_sku_action_queue mart_customer_action_queue` (Phase 3+4 combined).
4. Run Phase 3's regression diff (broadened scope — see Phase 3 fix) BEFORE resuming reverse-ETL. If not clean: fix and re-run steps 2-4; do not resume reverse-ETL on a dirty diff.
5. Only after a clean diff: apply Phase 5's `cache_schema.sql` + `sqlite_upsert.py` ALTER-list changes (see Critical fix in Phase 5), rebuild the `crm` container.
6. Resume reverse-ETL cron. First run will diff-delete any gift-only customers' now-vanished action rows (accepted per user decision — notify CS team before this step, not after).
7. `bootstrap_serving_views.py` (Metabase stopped) to pick up new mart columns for Metabase-side consumers.

**Known accepted gap (user decision)**: step 6 will cause gift-only customers' currently-live `REORDER_*`/`USAGE_FOLLOWUP` cards to disappear from CRM worklist until `GIFT_TO_PURCHASE` is reviewed and flipped `enabled=true` (Phase 4). This is intentional — CS team must be notified before step 1, not discovered after.

## Key Constraints

- `is_gift` = STRICT `line_amount = 0` only (per `int_order_promo_goods_cost.sql` precedent) — do not use `distributed_discount_amount` or a discount-rate threshold.
- `int_customer_sku_supply_tracking` is `materialized='table'`, no incremental flag — full rebuild each `dbt run`, no `--full-refresh` needed for this model itself.
- `dim_customers` is incremental — any column removal/rename there needs `--full-refresh` (per `feedback_dim_customers_incremental_full_refresh.md`). This plan does not touch `dim_customers` at all — `dim_customers.is_contactable` stays canonical; only the 2 action-queue marts' local `is_contactable` expressions are replaced (those are `table`/parquet marts, not incremental).
- After any new dbt node or seed → restart `data_platform` (manifest reload, per `feedback_dbt_node_needs_manifest_reload.md`).
- After mart column changes → stop Metabase → `bootstrap_serving_views.py` → restart (per `feedback_duckdb_view_rebuild.md`).
- CRM cache schema change → rebuild `crm` container (per `feedback_new_mart_crm_serving_integration.md`); code/template edits alone only need `docker compose restart crm`.
- Open DuckDB files `read_only=True` always (per `feedback_duckdb_always_readonly.md`).
- `available_action_types()`/`available_strategic_tiers()` in `crm/src/application/worklist_filters.py` already derive filter chips dynamically from distinct mart output values — new `action_type` (e.g. `GIFT_TO_PURCHASE`) needs **no CRM filter-code change** to appear as a filter chip; only rationale copy + cache schema column need work.

## Acceptance Criteria

- [ ] `std_order_items`/`fact_sales` carry `is_gift_line` (or equivalent), NULL-safe, `line_amount = 0` test — cross-checked against `int_order_promo_goods_cost`'s `line_revenue = 0` predicate (NOT the narrower `is_gift_no_invoice` flag — see Phase 1 fix), zero disagreements expected on the shared `line_revenue=0` scope.
- [ ] SKU gift-rate metric exists per core SKU, exposes at least `gift_rate` (continuous) — matches finejapan report's known bimodal pattern (Metabo/Gaba/Coix high, Shark/Natto/Cordyceps/Fucoidan low) as a sanity check.
- [ ] `int_customer_sku_supply_tracking` output grain becomes `(customer_key, sku, supply_stream)`; `supply_stream='purchased'` rows for customers with zero gift-line history produce **identical** `estimated_depletion_date`/`effective_supply_days` to pre-change baseline. **This does NOT mean overall action-queue row counts are unchanged** — gift-only customers' output changes by design (their rows move from implicit `purchased`-stream REORDER_* to `gift_only`-stream `GIFT_TO_PURCHASE`, which ships `enabled=false` — see Deploy Sequencing's accepted gap). Broadened regression test (Phase 3 fix) must also assert zero *unintended* reclassification (e.g. a real purchaser wrongly landing in `gift_only`).
- [ ] New `supply_stream='gift_only'` rows appear only for (customer, sku) pairs with zero non-gift purchase history.
- [ ] `seed_action_scenario_registry.csv` exists with `enabled` typed as BOOLEAN (explicit `column_types`, not inferred) and a uniqueness test on `(action_type, mart)`; toggling `enabled=false` for an existing action_type removes it from mart output without any SQL change, verified by a test run.
- [ ] `mart_customer_sku_action_queue`/`mart_customer_action_queue` join `mart_customer_tier` for `strategic_tier` + `is_contactable` (see corrected framing under Cross-plan context — this is a deliberate `is_contactable` semantic tightening for masked/obfuscated phones, not a no-op dedup); existing 5+7 action_types unchanged in behavior when registry defaults all `enabled=true`.
- [ ] New `GIFT_TO_PURCHASE` action_type implemented, gated by registry (ships `enabled=false`), appears in CRM worklist filter chips automatically once enabled (no `worklist_filters.py` change needed) AND renders with a real Vietnamese badge label (not raw English) via `badge_catalog.py` update.
- [ ] `wh_sku_action_queue` cache schema carries `supply_stream`, wired into the CRM read path (`cache_repository.py` `_sku_branch`) and denormalized/upserted via an explicit `ALTER TABLE` entry in `sqlite_upsert.py`'s migration list (not just `CREATE TABLE IF NOT EXISTS`, which no-ops against an existing prod `cache.db`). `strategic_tier` is NOT separately denormalized (existing `wh_customer_tier` JOIN in `cache_repository.py` already serves it — avoid dead/diverging state). No PII leak beyond existing pattern.

## Unresolved Questions

1. `GIFT_TO_PURCHASE` timing rule (khi nào nhắc: X ngày sau khi nhận tặng? theo `supply_days_per_unit` của SKU đó như luồng mua?) — chưa chốt, đề xuất cụ thể ở Phase 4, cần review trước khi implement.
2. Ngưỡng `gift_rate` để gán nhãn `sku_role` (ANCHOR/PREMIUM vs ENTRY_GIFT_PRONE) — đề xuất >40% dựa trên báo cáo finejapan nhưng chưa validate trên toàn bộ 8 core SKU hiện tại (báo cáo chỉ cover Metabo/Gaba/Coix).
3. Approach-script (S14 talk-track) cho `GIFT_TO_PURCHASE` chưa có template — out of scope plan này, cần plan riêng hoặc bổ sung vào approach-script backend feed.
4. `wh_deadstock_target`/`mart_product_action_queue` (2 action-queue engine khác, không thuộc scope plan này) có nên cũng tham chiếu `is_gift_line`/`sku_role` không? Chưa đánh giá — để riêng nếu có nhu cầu.
5. `is_us_gift_recipient` (`dim_customers.sql:300-306`, dùng trong Phase 4 để loại khách US khỏi eligibility) vẫn dựa 100% vào manual Sapo group-tag — có cùng lỗ hổng "chưa tag thì rơi về RETAIL" mà plan này đang né bằng cách dùng flag đó. Fix triệt để (thêm `EXISTS (đơn channel_name='US')` — signal tự động từ `dim_channels`, không qua tag thủ công, xem `int_us_shipment_line_prices.sql:16-26`) — **đã quyết định tách thành plan riêng** (không mở rộng scope plan này), vì đây là thay đổi nền tảng `dim_customers` ảnh hưởng nhiều mart khác ngoài action-queue.

## Validation Log

### Session 1 — 2026-07-08
**Trigger:** `/ck:plan validate` sau red-team pass
**Questions asked:** 6

#### Questions & Answers

1. **[Risk]** `GIFT_TO_PURCHASE` ships với timing rule placeholder (14-45 ngày) vì chưa có căn cứ dữ liệu — ổn không hay cần data-grounded rule ngay trong plan này?
   - Options: Placeholder ổn, tune sau khi enable (Recommended) | Cần data-grounded rule ngay
   - **Answer:** Placeholder ổn, tune sau khi enable
   - **Rationale:** Scenario ships `enabled=false` — không có rủi ro production; timing rule review là gate bắt buộc trước khi flip `enabled=true` (đã có trong Phase 4), không cần chặn plan này lại để nghiên cứu thêm ngay.

2. **[Risk]** Deploy Sequencing yêu cầu "pause CRM reverse-ETL cron" — cơ chế này có sẵn thực tế không?
   - Options: Có — Dagster schedule pause qua UI/CLI (Recommended) | Chưa rõ, cần scout trước khi cook
   - **Answer:** Có — Dagster schedule pause qua UI/CLI
   - **Rationale:** Xác nhận cơ chế tồn tại; tên schedule/job cụ thể chưa pin trong plan — grep `orchestration/` lúc bắt đầu Phase 5 implementation.

3. **[Risk]** Phase 3 regression check (d) — nếu số khách gift_only bị ảnh hưởng LỚN, có nên hard-gate chặn deploy không?
   - Options: Có — hard gate nếu > ngưỡng (Recommended) | Không — chỉ inform CS
   - **Answer:** Có — hard gate
   - **Rationale:** An toàn vận hành hơn quyết định gốc "chấp nhận gap, báo CS sau" — nhưng chỉ áp dụng cho case gây hại thật (task đang claim), không chặn toàn bộ deploy vì con số informational.

4. **[Scope]** Phase 2 chỉ expose `gift_rate` liên tục, không gán nhãn `sku_role` categorical — giữ nguyên hay thêm nhãn threshold-based ngay?
   - Options: Giữ nguyên — chỉ expose gift_rate (Recommended) | Thêm nhãn sku_role ngay
   - **Answer:** Giữ nguyên
   - **Rationale:** Ngưỡng >40% chưa validate trên toàn bộ 8 core SKU (báo cáo finejapan chỉ cover 3/8) — tránh đóng băng ngưỡng business chưa chắc.

5. **[Risk]** Ngưỡng hard-gate cụ thể cho check (d) là bao nhiêu?
   - Options: >0 open crm_task đang claim (Recommended) | >50 tổng action bị ảnh hưởng
   - **Answer:** >0 open crm_task đang claim
   - **Rationale:** Chỉ gate trường hợp gây hại thật (NV đang xử lý dở, orphan giữa chừng) — action chưa claim thì không gate, chỉ cần báo CS.

6. **[Risk]** Runbook cần tên cụ thể Dagster schedule/job — biết tên hay để grep lúc cook?
   - Options: Grep tìm lúc cook (Recommended) | Biết tên, nhập ngay
   - **Answer:** Grep tìm lúc cook
   - **Rationale:** Không chặn plan lại để tra cứu tên chính xác; việc này rẻ, làm lúc bắt đầu implement Phase 5.

#### Confirmed Decisions
- `GIFT_TO_PURCHASE` timing: placeholder 14-45 ngày OK để ship (disabled), tune trước khi enable — không đổi Phase 4.
- Deploy Sequencing pause mechanism: Dagster schedule pause confirmed available; exact name deferred to cook-time grep.
- Phase 3 regression check (d): promoted to HARD GATE, scoped narrowly to `>0` open/claimed `crm_task` overlap (not total population).
- Phase 2 `sku_role`: stays out of scope, `gift_rate` only.
- **New scope decision (mid-session, outside the 6 formal questions)**: `is_us_gift_recipient`'s underlying tagging-gap weakness (still relies on manual Sapo group tag, same hole as `customer_type`) — real fix (`EXISTS` on `channel_name='US'` order evidence) explicitly deferred to a SEPARATE plan, not folded into this one. Added as Unresolved Question #5.

#### Action Items
- [x] Update `plan.md` § Deploy Sequencing step 1 wording (Dagster schedule, grep exact name at cook time)
- [x] Update Phase 3 regression check (d) + Success Criteria to hard-gate on open-task overlap
- [x] Add Unresolved Question #5 documenting the `is_us_gift_recipient` follow-on plan

#### Impact on Phases
- Phase 3: regression check (d) is now a hard deploy gate, not just informational (see Phase 3 file)
- Phase 5: Deploy Sequencing step 1 needs the actual Dagster schedule name resolved at implementation start (grep `orchestration/`)

### Whole-Plan Consistency Sweep
- Files reread: plan.md, phase-01, phase-02, phase-03, phase-04, phase-05
- Decision deltas checked: 6 validation answers + 1 mid-session scope decision
- Reconciled stale references: Deploy Sequencing step 1 (cron → Dagster schedule), Phase 3 check (d) (informational → hard gate) and its Success Criteria line
- Unresolved contradictions: 0

## Red Team Review

### Session — 2026-07-08
**Findings:** 21 raw → 15 deduplicated (2 Critical, 6 High, 7 Medium)
**Severity breakdown:** 2 Critical, 6 High, 7 Medium
**Reviewers:** Security Adversary (Fact Checker), Assumption Destroyer (Scope Auditor), Failure Mode Analyst (Flow Tracer)
**Reports:** `reports/from-code-reviewer-to-planner-red-team-security-adversary-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-assumption-destroyer-plan-review-report.md`, `reports/from-code-reviewer-to-planner-red-team-failure-mode-analyst-plan-review-report.md`

| # | Finding | Severity | Disposition | Applied To |
|---|---------|----------|-------------|------------|
| 1 | Phase 5 cache columns missing from `sqlite_upsert.py` ALTER migration list → nightly reverse-ETL aborts on existing cache.db | Critical | Accept | Phase 5 |
| 2 | Ship-day: gift-only customers' live actions silently deleted, orphaning claimed CRM tasks; "identical row counts" criteria provably false | Critical | Accept (user decision: accept temporary gap, notify CS first) | plan.md (Deploy Sequencing, Acceptance Criteria), Phase 3, Phase 4 |
| 3 | Overview implies bug fully fixed; actually only fixed for never-purchased customers (3/3 reviewers flagged independently) | High | Accept | plan.md Overview |
| 4 | Phase 1 verification query references nonexistent `fact_sales.sku`/`fact_sales.order_code` | High | Accept | Phase 1 |
| 5 | "Mirrors `is_gift_no_invoice`" claim inaccurate — different grain/prefilters, disagreement expected not a bug | High | Accept | Phase 1, plan.md Acceptance Criteria |
| 6 | Registry `enabled` seed column has no boolean type coercion — DuckDB inference footgun + fail-open combination | High | Accept | Phase 4 |
| 7 | `ever_purchased` static reclassification churns `action_id`/`pending_since` on stream transition, retriggers documented B5 dismiss-reappear bug | High | Accept (user decision: reset dismiss/snooze state is intentional, not a bug) | Phase 3, Phase 4 |
| 8 | No production rollback path; Phase 3's own mitigations contradict (gate on diff vs. same-window ship) | High | Accept | plan.md (Deploy Sequencing) |
| 9 | `strategic_tier` denormalization in Phase 5 is dead work — CRM already resolves it via live JOIN | Medium | Accept (drop denormalization, keep existing JOIN; `supply_stream` IS wired into read path since it's genuinely new) | Phase 5 |
| 10 | Phase 5 omits `badge_catalog.py` — `GIFT_TO_PURCHASE` renders as neutral badge with raw English label | Medium | Accept | Phase 5 |
| 11 | "3x-duplicated is_contactable" claim inaccurate — `dim_customers` is canonical, not a duplicate | Medium | Accept (wording fix; user also decided to adopt tier's stricter semantics — see Finding 15) | plan.md (Cross-plan context, Key Constraints) |
| 12 | Registry `(action_type, mart)` has no uniqueness test; mart-name string typo fails open | Medium | Accept | Phase 4 |
| 13 | Phase 3 under-specifies threading `supply_stream` through the independent `last_order_ctx` CTE | Medium | Accept | Phase 3 |
| 14 | Phase 3 regression test scoped to population that structurally cannot change — blind to real defects | Medium | Accept | Phase 3 |
| 15 | `mart_customer_tier.is_contactable` differs from marts' phone-presence check for obfuscated marketplace-relay phones | Medium | Accept (user decision: switch to tier's stricter semantics, document as intentional) | Phase 4 |

### Whole-Plan Consistency Sweep
- Files reread: plan.md, phase-01, phase-02, phase-03, phase-04, phase-05 (after applying all 15 accepted findings)
- Decision deltas checked: 15 (2 Critical + 6 High + 7 Medium)
- Reconciled stale references: Overview honesty framing, "identical row counts" claim, "mirrors is_gift_no_invoice" claim, "3x-duplicated is_contactable" claim, `strategic_tier` denormalization scope, Phase 1 verification query, Phase 3 regression test scope, Phase 3 `last_order_ctx` threading, Phase 4 registry typing/uniqueness, Phase 5 ALTER-list gap + badge_catalog.py
- Unresolved contradictions: 0

## Deploy Execution Log — 2026-07-08

All 5 phases implemented and shipped same-session (`/ck:cook --auto --parallel`). Deviation from the planned Deploy Sequencing, discovered and remediated live:

- **Step 1 (pause reverse-ETL) was NOT executed before Phase 3 started** — `crm_sync.crm_cache_refresh` isn't a standalone schedule; it's an asset embedded in `pipeline_sapo_v2_realtime_job` (cron `*/3 * * * *`), `pipeline_sapo_v2_incremental_job` (`*/10 * * * *`), and `pipeline_batch_nightly_job` (`0 3 * * *`). All 3 kept ticking through Phases 3-5, so every phase's dbt changes synced to production `cache.db` live and automatically, without the CS team being notified first as planned.
- Discovered when re-checking Phase 5's completion (a fullstack-developer subagent flagged that `mart_customer_sku_action_queue`'s final SELECT never re-exposed `classified.supply_stream` as an output column, despite Phase 4 computing it for branching — fixed with a 1-line addition, `transformation/models/marts/customer/mart_customer_sku_action_queue.sql`).
- Remediation: paused all 3 schedules (`dagster schedule stop ...`), re-verified the Phase 3 hard-gate (open/claimed `crm_task` overlap with `gift_only`-reclassified customers) against current production state — still 0, consistent with Phase 3's original check (both found the same 18 total open/doing tasks, none created during this session, none overlapping). No new orphaning occurred. User reviewed the finding and explicitly chose to resume all 3 schedules immediately (CS notification treated as moot since the gap already happened with no confirmed harm, not worth blocking further on).
- **Follow-up still owed**: CS team has not yet been notified that gift-only customers' `REORDER_*`/`USAGE_FOLLOWUP` cards silently dropped off their worklist (per the plan's accepted gap) — this is a communication step outside tooling, owned by the user.
- Net: all Success Criteria across 5 phases verified; `GIFT_TO_PURCHASE` ships `enabled=false` pending timing-rule/copy review (Unresolved Question #1); schedules back to normal operation.
