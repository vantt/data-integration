# Red-Team Plan Review — Gift vs Purchase SKU Action Scenario

**Reviewer role:** Fact Checker / Security Adversary (mis-targeting, data integrity, unsafe rollout of rep-facing derived logic)
**Plan:** `plans/260708-1501-gift-purchase-sku-action-scenario/`
**Verdict:** Multiple factual claims in the plan do not match the codebase. Two verification steps reference columns that do not exist and will fail on first run; the central "reuse the validated finance definition" justification is a misread; and the CRM-sync phase does dead work that contradicts its own recommendation. Fix before implementation.

---

## Finding 1: Phase 1 verification query references `fact_sales.sku` and `fact_sales.order_code` — neither column exists

- **Severity:** High
- **Location:** Phase 1, "Implementation Steps" step 5 (cross-check query) + Acceptance Criteria in `plan.md`
- **Flaw:** `fact_sales` has no `sku` and no `order_code` column. Every consumer that needs SKU joins `dim_products` on `product_key`, and every consumer that needs the order code joins `fact_orders` on `order_id`. The plan's verification query joins `int_order_promo_goods_cost p ON fs.order_code = p.order_code AND fs.sku = p.sku`.
- **Failure scenario:** The implementer runs the step-5 "should return 0 rows" gate; DuckDB raises a Binder error on `fs.order_code` / `fs.sku`. The verification never executes, so the Phase-1 correctness gate is silently skipped and later phases build on an unverified `is_gift_line`.
- **Evidence:** `transformation/models/marts/sales/fact_sales.sql:32-99` — SELECT list exposes `product_key`, `i.order_id`, `i.order_line_id`, `net_revenue`, `discount_amount`, `distributed_discount_amount`, `discount_rate`, `ordered_at`; no `sku`, no `order_code`. Compare `int_customer_sku_supply_tracking.sql:52-55` (joins `dim_products` for sku, `fact_orders` for order context) and `int_order_promo_goods_cost.sql:29-31` (bridges `order_id`→`order_code` via `fact_orders`).
- **Suggested fix:** Rewrite the check to join `dim_products dp ON fs.product_key = dp.product_key` and `fact_orders fo ON fs.order_id = fo.order_id`, comparing `dp.sku`/`fo.order_code` — or run the check at `std_order_items` grain where `sku` and `order_id` do exist.

---

## Finding 2: "Mirrors `int_order_promo_goods_cost.is_gift_no_invoice`" is a misread — the two flags will NOT agree, so the acceptance gate is wrong

- **Severity:** High
- **Location:** `plan.md` lines 25, 54, 65 (Acceptance Criteria) + Phase 1 overview/step 3/step 5
- **Flaw:** The plan repeatedly claims `is_gift_line = (line_amount = 0)` reuses the validated `is_gift_no_invoice` definition, and the acceptance criterion says the two "should agree wherever both apply." They are not the same predicate. `is_gift_no_invoice` is `cogs_source = 'sapo_mac' AND misa_642_amount IS NULL`, evaluated only on rows already filtered to `line_revenue = 0 AND cogs_goods_primary IS NOT NULL AND sku NOT LIKE 'DV%'/'CPBH%'`. It is a strict subset of zero-revenue lines. A gift line that HAS a MISA-642 entry, or lacks a MAC cost, or is a service SKU has `is_gift_no_invoice = FALSE` while `is_gift_line = TRUE`.
- **Failure scenario:** Implementer follows the acceptance criterion literally, diffs `is_gift_line` against `is_gift_no_invoice`, sees many "disagreements," and either wastes time chasing a non-bug or wrongly narrows `is_gift_line` to match, corrupting the gift signal that Phase 3's `ever_purchased` depends on. Additionally, the real precedent — `line_revenue = 0` — is computed at `(order_code, sku)` aggregate grain (`SUM(line_amount)`), while `is_gift_line` is per line-item; a SKU split across a paid line and a gift line in one order sums to `line_revenue > 0`, so even the "correct" predicate diverges from line-grain `is_gift_line`.
- **Evidence:** `int_order_promo_goods_cost.sql:22-31` (`line_rev` = `SUM(i.line_amount)` grouped by `order_code, sku`), `:45-61` (promo CTE prefilter), `:71-74` (`is_gift_no_invoice = cogs_source='sapo_mac' AND misa_642_amount IS NULL`). The only line-level equivalence is the `line_revenue = 0` prefilter at `:57`, not the output flag.
- **Suggested fix:** Reword the plan to say `is_gift_line` reuses the `line_revenue = 0` STRICT predicate (line 57), not `is_gift_no_invoice`. Drop the "agree with is_gift_no_invoice" acceptance criterion or replace with "agree with `line_revenue = 0` after aggregating `is_gift_line` to `(order_code, sku)` grain."

---

## Finding 3: Registry `enabled` boolean typing is unspecified — dbt-seed may load `true/false` as VARCHAR and break the on/off filter

- **Severity:** High
- **Location:** Phase 4, step 1 (seed CSV) + step 4 (`COALESCE(reg.enabled, TRUE) = TRUE`)
- **Flaw:** `seed_action_scenario_registry.csv` stores `enabled` as literal `true`/`false` text. The plan provides no `column_types`/`seeds:` config forcing a BOOLEAN cast. dbt-seed column typing is inference-based and this repo already has a documented seed-typing footgun. If `enabled` loads as VARCHAR, `COALESCE(reg.enabled, TRUE) = TRUE` compares a string to a boolean — DuckDB will either error or coerce so that a `'false'` row does not evaluate to disabled.
- **Failure scenario:** The whole registry mechanism silently fails: flipping `GIFT_TO_PURCHASE` to `false` (or disabling any scenario) has no effect, or the mart run errors on a type mismatch. The plan's headline promise — "toggle enable/disable = seed edit + dbt seed && dbt run, no SQL change" — does not work as written.
- **Evidence:** Repo memory `feedback_duckdb_integer_underscore.md` documents seed columns silently mistyped by DuckDB; no `column_types` block appears anywhere in Phase 4's seed definition (`phase-04-...md:59-74`). Existing marts never rely on a seed boolean, so there is no precedent to copy.
- **Suggested fix:** Add an explicit `seeds:` `column_types: {enabled: boolean}` (or store `1/0` and compare numerically), and add a test that a `false` row is actually dropped from mart output.

---

## Finding 4: Phase 5 `strategic_tier` denormalization is dead work — cache_repository already sources it via JOIN and Phase 5 recommends keeping that JOIN

- **Severity:** Medium
- **Location:** Phase 5, "Requirements" + step 5 (option a/b), Architecture diagram
- **Flaw:** Phase 5 states the point of denormalizing `strategic_tier` into `wh_sku_action_queue` is to replace the separate JOIN in `cache_repository.py` ("thay vì JOIN riêng ở cache_repository.py — giờ mart đã tính sẵn"). But step 5 then recommends option (a): keep the `wh_customer_tier` JOIN. `_sku_branch` enumerates columns explicitly (`COALESCE(ct.strategic_tier, '') AS strategic_tier`) — it does not use `sa.*` — so a new `wh_sku_action_queue.strategic_tier` column is never read unless the SELECT is changed to `sa.strategic_tier`. With option (a), the denormalized column is added, synced, and stored but never consumed. Likewise the new `supply_stream` column is added to `wh_sku_action_queue` but is not added to the `_sku_branch`/`_customer_branch` SELECT, so it never reaches the domain object or UI.
- **Failure scenario:** Reverse-ETL and schema changes ship; extra columns sit unused in the cache; the stated dedup benefit never materializes; a later reader assumes `sa.strategic_tier` is authoritative while the UI still reads `ct.strategic_tier`, creating two sources that can drift.
- **Evidence:** `crm/src/adapters/outbound/sqlite/cache_repository.py:201-222` — `_sku_branch` SELECT enumerates columns and derives `strategic_tier` from `LEFT JOIN cache.wh_customer_tier ct` (`:213`, `:222`); no `sa.*`; no `supply_stream`. Same pattern in `_customer_branch` (`:402-418`).
- **Suggested fix:** Pick one path. Either denormalize AND rewrite `_sku_branch` to read `sa.strategic_tier` and drop the `ct` JOIN, or do not denormalize `strategic_tier` at all (keep the existing JOIN) and drop that column from Phase 5 scope. If `supply_stream` is meant to be visible/filterable, add it to the branch SELECT and the domain model; otherwise drop it from the cache schema.

---

## Finding 5: The headline bug (gifts inflating reorder cadence) is NOT fixed for customers who ever purchased the SKU

- **Severity:** Medium
- **Location:** `plan.md` Overview item 1 + Phase 3 "purchased" stream definition
- **Flaw:** The Overview motivates the whole plan with: a customer gifted one Metabo box in a premium order gets their reorder reminder pushed back as if they bought it. But Phase 3 routes ALL lines (gift + purchased) into `supply_stream='purchased'` whenever the customer has ever purchased that SKU, keeping the existing accumulate-everything behavior. Only customers who NEVER bought the SKU (gift_only) are carved out. The motivating example — someone buying a premium order and receiving a gift box — is precisely an ever-purchased/active buyer, whose gift box will still inflate `effective_supply_days`.
- **Failure scenario:** After shipping, the exact scenario in the Overview still mis-times reorder reminders for the majority of real (active, purchasing) customers. Stakeholders read the acceptance criteria as "gift inflation fixed" and are surprised the cadence bug persists for their core buyers.
- **Evidence:** Phase 3 lines 15 and 35-38 ("nếu ever_purchased=TRUE, TẤT CẢ dòng (kể cả is_gift_line=TRUE) đi vào stream 'purchased' — giữ hành vi cộng dồn hiện tại"); current accumulation in `int_customer_sku_supply_tracking.sql:84-95` (`total_qty * supply_days_per_unit` sums all `raw_purchases` including gift lines).
- **Suggested fix:** Either scope the Overview honestly (state that ever-purchased customers intentionally retain gift inflation, per user decision) or reconsider excluding gift quantity from `effective_supply_days` within the purchased stream too (the data to do so — `is_gift_line` — is now available at the line grain).

---

## Finding 6: "3x-duplicated is_contactable" is not a real duplication; the tier JOIN adds a build-order dependency for no dedup gain

- **Severity:** Medium
- **Location:** `plan.md` line 49 (Cross-plan context) + Phase 4 step 2
- **Flaw:** The plan claims `mart_customer_tier` will "replace 3x-duplicated ad-hoc `is_contactable` computation in `dim_customers.sql`, `mart_customer_action_queue.sql`, `mart_customer_sku_action_queue.sql`." All three use the identical rule `(phone IS NOT NULL AND phone <> '')` — they are consistent, not divergent. And `mart_customer_tier` does not compute `is_contactable`; it passes through `dim_customers.is_contactable`. So swapping the marts' local expression for a `mart_customer_tier` JOIN yields the same values while adding a new hard build dependency (tier must materialize before both action marts) and pulling from an all-customer-type mart into RETAIL-filtered marts.
- **Failure scenario:** The "dedup" is presented as risk-reducing cleanup but actually increases coupling; a future change to the tier mart's row set or a build-order regression can now affect `is_contactable` in the action queues. The genuine reason for the JOIN — obtaining `strategic_tier` — is real, but the `is_contactable` framing is inaccurate and invites unnecessary edits to `dim_customers.sql`.
- **Evidence:** `dim_customers.sql:298`, `mart_customer_action_queue.sql:46`, `mart_customer_sku_action_queue.sql:44` — identical `(phone IS NOT NULL AND phone <> '')`; `mart_customer_tier.sql:28-31` selects `is_contactable` straight from `dim_customers`.
- **Suggested fix:** Justify the tier JOIN by `strategic_tier` only; keep `is_contactable` computed locally (or read from `dim_customers`), and drop the "3x duplication removal" claim and any implied edit to `dim_customers.sql`.

---

## Finding 7: `GIFT_TO_PURCHASE` can be enabled by a one-line seed edit with no code-review gate, while its timing rule and S14 talk-track are admittedly unfinished

- **Severity:** Medium (rollout-safety / mis-targeting)
- **Location:** Phase 4 step 1 ("Flip to `true` via seed edit + dbt seed && dbt run, no code change") + Unresolved Questions #1 and #3 + Phase 5 S01/S14 wiring
- **Flaw:** The plan's selling point — enabling a scenario is "just a seed edit, no SQL/code change" — deliberately removes the code-review gate for turning on rep-facing outreach. Yet the `GIFT_TO_PURCHASE` timing rule (14-45 days) is flagged as an unvalidated placeholder (Unresolved Q1) and there is no S14 approach-script/talk-track for it (Unresolved Q3). The rationale copy also asserts an absolute "chưa từng mua" (never purchased), which is only as trustworthy as line-grain `is_gift_line` and the `ever_purchased` join.
- **Failure scenario:** Someone flips `enabled=true` in the seed to "test in prod," `dbt seed && dbt run` runs, and reps immediately see `GIFT_TO_PURCHASE` cards in the S01 worklist and S14 call cockpit (filter chips auto-derive per the plan) with an unvalidated cadence and no script — reps cold-call real customers about a gift with no guidance and a possibly-wrong "you've never bought this" claim. No PR review would have caught it because the change was data-only.
- **Evidence:** `phase-04-...md:66,75` (`GIFT_TO_PURCHASE ... enabled=false`; "Flip to true via seed edit ... no code change"); `phase-04-...md:108` (timing "placeholder ... do not treat as final"); `plan.md:76,78` (Unresolved Q1 timing, Q3 no talk-track); `phase-05-...md:73` (chip appears on S01 "without a CRM deploy"); rationale text `phase-04-...md:112-114`.
- **Suggested fix:** Gate `enabled=true` for any new/rep-facing scenario behind a checklist that requires the timing rule and approach-script to be signed off (document this as a hard precondition in the registry doc), and soften the rationale copy to reflect the windowed/derived nature of "never purchased" (e.g. "chưa ghi nhận đơn mua" rather than an absolute claim).

---

## Verified-OK (checked, no issue)

- `mart_customer_tier` is 7 tiers (NONBUYER, LIVE_CORE, SECOND_ORDER, MASKED_REPEAT, DORMANT_VALUABLE, LAPSED_VALUABLE, GRAVEYARD) — matches plan (`mart_customer_tier.sql:37-56`).
- Customer-mart 7 action_types and SKU-mart 5 action_types match the registry CSV (`mart_customer_action_queue.sql:71-91`; `mart_customer_sku_action_queue.sql:75-87`).
- `available_action_types()` / `available_strategic_tiers()` exist and derive dynamically — new `action_type` needs no filter-code change (`crm/src/application/worklist_filters.py:74,84`).
- `fetch_sku_action_queue` / `upsert_sku_action_queue` / `cache_schema.sql` / `dim_sku_alias` (`sapo_pack_sku`/`sapo_base_sku`/`units_per_pack`) / `seed_sku_regimen_config.csv` all exist as cited.
- `_check_columns` is a subset check (`duckdb_reader.py:239-243`), so adding columns to the reader SELECT will not break it (contrary to a first-glance worry) — but see Finding 4: the added columns are not surfaced downstream.
- No time-window WHERE filter found in `fact_orders`/`std_orders`, so `ever_purchased` sees full history — the "never purchased" claim is not truncated by a rolling window (the `get_rolling_location` macro only controls the parquet output path, `macros/get_rolling_location.sql:1`).

## Unresolved Questions for the planner

1. Does the Phase-1 grain question (line-item `is_gift_line` vs `(order_code, sku)` aggregate) affect Phase 3's `ever_purchased`? `ever_purchased` uses line-grain `is_gift_line = FALSE`, which is the correct grain there — but the plan should state this explicitly so it is not "fixed" to match the finance aggregate.
2. Is `supply_stream` intended to be visible in the CRM UI, or is it purely an internal warehouse discriminator? If internal-only, it should not be added to the cache schema at all.
