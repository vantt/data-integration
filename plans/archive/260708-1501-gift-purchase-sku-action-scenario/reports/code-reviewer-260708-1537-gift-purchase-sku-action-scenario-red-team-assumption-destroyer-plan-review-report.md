# Red-Team Plan Review — Assumption Destroyer (Scope Auditor lens)

Plan: `plans/260708-1501-gift-purchase-sku-action-scenario`
Reviewer role: hostile skeptic — unstated dependencies, false "will work" claims, missing error paths, duplicated state, scope drift.
Verdict: **Do not implement as written.** Multiple headline claims are contradicted by the actual code. Two of the plan's own success criteria are internally impossible.

---

## Finding 1: The headline supply-tracking bug is NOT fixed for the majority (ever-purchased) case — by design, but the Overview claims otherwise

- **Severity:** High
- **Location:** plan.md "Overview" point #1 + line 27 decision; Phase 3 "Overview" / bullet `supply_stream='purchased'`
- **Flaw:** The Overview opens with the concrete bug: *"Một khách được tặng kèm 1 hộp Metabo trong đơn premium sẽ bị đẩy lùi nhịp nhắc tái mua y hệt như thể họ tự mua hộp đó."* The chosen fix routes a gift line into `supply_stream='purchased'` (gift qty still accumulates into `effective_supply_days`, unchanged) whenever the customer **ever** bought that SKU. So the exact failure described is only fixed for customers who have *never* purchased the SKU.
- **Failure scenario:** Customer bought Metabo once in Jan, is gifted a Metabo box in a premium order in Mar. `ever_purchased(customer, Metabo)=TRUE` → both lines go to `purchased`. The recursive stack still does `GREATEST(purchase_date, prev_depletion) + effective_supply_days` including the gifted box's qty, pushing the reorder reminder out by a full box's worth of days — identical to today. The bug the plan is named after persists for every repeat buyer who also receives a gift of a SKU they buy. Per the finejapan report, gifts cluster in multi-SKU premium baskets — precisely the baskets of active repeat buyers — so the unfixed population is likely the larger one.
- **Evidence:** `int_customer_sku_supply_tracking.sql:87-89` (`effective_supply_days = ROUND(total_qty * supply_days_per_unit * dose_reduction_buffer)`) and `:122` (`GREATEST(p.purchase_date, s.depletion_date) + p.effective_supply_days`) — gift qty is indistinguishable once inside `purchased`. Phase 3 line 15 explicitly keeps "MỌI quantity (mua + tặng) cộng dồn" for that stream.
- **Suggested fix:** Either (a) state plainly in the Overview that the fix scope is *never-purchased-SKU customers only*, and that gift-inflation for repeat buyers is intentionally out of scope, or (b) reconsider excluding gift qty from `effective_supply_days` for all streams (the `is_gift_line` flag makes this trivial and directly addresses the stated bug). Do not sell (a) as fixing the (b) problem.

---

## Finding 2: "Identical row counts / backward-compatible" is provably false — gift-only customers silently lose live action cards, and the regression guard is constructed to miss them

- **Severity:** High
- **Location:** Phase 3 success criteria ("Regression diff: zero changes for pairs with no gift-line history") + Phase 4 success criteria ("Existing 12 action_type values produce **identical row counts** vs baseline")
- **Flaw:** Today a customer who was only ever *gifted* SKU X still has a supply row and still receives `USAGE_FOLLOWUP` / `PROGRESS_CHECK` / `REORDER_*` cards, because the mart classifies on `last_purchase_date` (= gift date) and depletion regardless of gift status. After this change those (customer, sku) pairs become `supply_stream='gift_only'`, whose only branch is `GIFT_TO_PURCHASE`, which ships `enabled=false` and is stripped by the registry `WHERE COALESCE(reg.enabled,TRUE)=TRUE`. Net effect: those rows vanish. Row counts drop; the "identical distribution" criterion cannot hold.
- **Failure scenario:** A gift recipient who never bought Coix currently shows "Ngày 7 dùng Coix — hỏi thăm" (USAGE_FOLLOWUP) on a rep's worklist. After deploy that card disappears with no replacement (GIFT_TO_PURCHASE off). The rep's queue shrinks and nobody can explain why, because the Phase 3 regression diff (step 6) only compares pairs *"with no gift-line history"* — gift-only pairs have gift-line history by definition, so they are structurally excluded from the very check meant to prove no regression.
- **Evidence:** `mart_customer_sku_action_queue.sql:75-87` (journey + reorder CASE fires on `last_purchase_date`/depletion with no gift gate today); Phase 4 architecture lines 100-106 gate all 5 existing branches behind `supply_stream='purchased'`; Phase 3 step 6 diff predicate `new.supply_stream = 'purchased'` + "Expect 0 rows for customers with no gift-line history."
- **Suggested fix:** Drop the "identical row counts" criterion or scope it to `purchased`-stream rows only, and explicitly quantify the expected drop in gift-only cards as an intended behavior change. Add a count of current action cards attributable to gift-only pairs to the regression report so the loss is measured, not discovered in production.

---

## Finding 3: `strategic_tier` denormalization is duplicate state — the CRM already resolves tier for SKU actions via a live join; the new column would be written-but-unread and can diverge

- **Severity:** High
- **Location:** Phase 5 "Architecture" + Requirements ("`strategic_tier` denormalized trực tiếp vào `wh_sku_action_queue`/`wh_action_queue`") + step 5 (recommends keeping the existing join AND the new column)
- **Flaw:** The scope-auditor mandate is to catch duplicated state under different names. `strategic_tier` for SKU-level actions is **already** populated at read time by a `LEFT JOIN cache.wh_customer_tier` in both consuming code paths. Adding a denormalized `strategic_tier` column sourced from the mart snapshot creates a second copy of the same fact, refreshed on a different cadence (queue reverse-ETL vs tier reverse-ETL), that the read path does not even consult under the plan's recommended option (a).
- **Failure scenario:** Reverse-ETL runs `upsert_sku_action_queue` at T1 (denormalized `strategic_tier` = LIVE_CORE) and `upsert_customer_tier` at T2 after a nightly tier recompute flips the customer to DORMANT_VALUABLE. `wh_sku_action_queue.strategic_tier` now says LIVE_CORE while `wh_customer_tier` says DORMANT_VALUABLE. The worklist badge and filter (read from the join) show DORMANT_VALUABLE; the denormalized column silently disagrees. Because option (a) keeps reading the join, the new column is pure dead weight that will mislead the next engineer who greps for `strategic_tier` and finds two sources.
- **Evidence:** `cache_repository.py:176` and `:213-214` (`list_all_action_queue` sku branch: `LEFT JOIN cache.wh_customer_tier ct ... COALESCE(ct.strategic_tier,'') AS strategic_tier`); `:418` and `:433-437` (`_fetch_actions` same). `worklist_filters.py:84-86` `available_strategic_tiers()` reads `a.strategic_tier` which is already populated by that join today. The plan's own Key Constraint (plan.md:61) admits filters already derive dynamically — which is only true *because* the join already supplies the value.
- **Suggested fix:** Delete the `strategic_tier` denormalization from Phase 5 entirely. Filter chips and badges already work via the existing join. If a single source is desired, that is a separate dedup effort (drop the join in favor of a denormalized column), not "add a second copy and keep both."

---

## Finding 4: Phase 5 omits `badge_catalog.py` — a new `GIFT_TO_PURCHASE` renders as a neutral badge with the raw English code as its label

- **Severity:** Medium
- **Location:** Phase 5 "Related Code Files" (lists only cache_schema/duckdb_reader/sqlite_upsert + review-only) and plan.md Key Constraint line 61 ("new action_type ... needs no CRM filter-code change; only rationale copy + cache schema column need work")
- **Flaw:** The claim conflates *filter chips* (dynamic, genuinely zero-change) with *badge rendering* (a hardcoded per-action_type catalog). Badge color and Vietnamese short-label come from static dicts keyed on lowercased action_type. `gift_to_purchase` is absent from both.
- **Failure scenario:** When `GIFT_TO_PURCHASE` is flipped on, every worklist row for it renders with the neutral fallback color and the badge text `GIFT_TO_PURCHASE` (raw uppercase English), because `bdg_lookup` falls back to `_NEUTRAL` and `bdg_label` falls back to the raw key. On a Vietnamese CS worklist this is a visible defect that the plan asserts does not exist.
- **Evidence:** `crm/src/adapters/inbound/web/badge_catalog.py:74-88` (`action_type` color/tooltip dict, no gift entry), `:143-157` (`_ACTION_TYPE_SHORT_LABEL`, no gift entry), `:162` (`bdg_lookup` → `_NEUTRAL` on miss), `:173` (`bdg_label` returns raw `key` on miss). `reason_rail.py:36,109-111` also branches on `action_type`.
- **Suggested fix:** Add `badge_catalog.py` to Phase 5 files: one `BadgeDef` color/tooltip entry and one `_ACTION_TYPE_SHORT_LABEL` entry for `gift_to_purchase`. Audit `reason_rail.py` for any action_type-specific tiering. Correct the Key Constraint to say "rationale copy + cache schema column + badge catalog entry."

---

## Finding 5: The "3x-duplicated is_contactable" dedup claim is factually wrong for `dim_customers.sql` — removing it there breaks `mart_customer_tier`

- **Severity:** Medium
- **Location:** plan.md "Cross-plan context" line 49 ("replaces 3x-duplicated ad-hoc `is_contactable` computation in `dim_customers.sql`, `mart_customer_action_queue.sql`, `mart_customer_sku_action_queue.sql`")
- **Flaw:** `mart_customer_tier` — the very model the plan wants to make the single source of truth for `is_contactable` — itself derives `is_contactable` by selecting `dim_customers.is_contactable`. `dim_customers` is the root definition, not a redundant copy. It cannot be removed without breaking the tier mart the plan depends on.
- **Failure scenario:** An implementer follows plan.md line 49 literally, deletes `(phone IS NOT NULL AND phone <> '') AS is_contactable` from `dim_customers.sql`, and `mart_customer_tier` fails to build (references a now-missing column), cascading to both action-queue marts and the CRM tier sync.
- **Evidence:** `dim_customers.sql:298` `(phone IS NOT NULL AND phone <> '') AS is_contactable`; `mart_customer_tier.sql:28` selects `is_contactable` from `dim_customers` and passes it through at `:74`. Note also this makes the swap value-neutral (both marts use the identical predicate), so the dedup is cosmetic, not a behavior fix.
- **Suggested fix:** Correct line 49 to list only the two action-queue marts as dedup targets. Keep `dim_customers.is_contactable` as the canonical root. State that the swap is value-neutral (no `is_contactable` display change expected) so reviewers know not to expect diffs.

---

## Finding 6: Registry natural key `(action_type, mart)` has no uniqueness enforcement, and the mart-name string literal makes the filter fail *open*

- **Severity:** Medium
- **Location:** Phase 4 step 1 (seed) + step 4 (registry filter `LEFT JOIN ... AND reg.mart = '<this_mart_name>' ... AND COALESCE(reg.enabled, TRUE) = TRUE`)
- **Flaw:** Two coupled defects. (1) The seed's `(action_type, mart)` "natural key" is asserted in prose but nothing enforces it — no dbt `unique`/`dbt_utils.unique_combination_of_columns` test is specified. A duplicate row fans out the `LEFT JOIN`, duplicating every action card of that type. (2) The join predicate hardcodes the mart name as a SQL string literal; if that string is mistyped or the mart is renamed, no registry row matches, `reg.enabled` is NULL, and `COALESCE(...,TRUE)` re-enables everything — the disable mechanism fails silently open.
- **Failure scenario A:** Someone appends `GIFT_TO_PURCHASE,mart_customer_sku_action_queue,true,...` a second time while editing the CSV. Every gift card now appears twice in the worklist; the plan's idempotent `(customer_key, sku, action_type)` cache PK collapses them on upsert only if action_id matches — but the mart itself emits duplicate rows first, and any count/regression check is thrown off.
- **Failure scenario B:** A future refactor renames the mart file. The `reg.mart = 'mart_customer_sku_action_queue'` literal no longer matches any seed row, so a scenario an operator set to `enabled=false` silently turns back on in production with zero error.
- **Evidence:** No `seed_action_scenario_registry.csv` or test exists yet (Glob: not found). Existing marts show no registry pattern to copy. Phase 4 line 77 asserts the key only in a comment; line 124 shows the `COALESCE(reg.enabled, TRUE)=TRUE` fail-open default.
- **Suggested fix:** Add a `unique_combination_of_columns` test on `(action_type, mart)` for the seed. Reconsider fail-open: for a deliberately-disabled scenario, an unmatched registry row silently re-enabling it is the opposite of intent — at minimum add a dbt test that every `action_type` emitted by each mart has exactly one registry row for that mart, so a mart-name drift fails the build instead of leaking a scenario.

---

## Finding 7: Phase 3 hand-waves threading `supply_stream` through `last_order_ctx`, which has its own independent 2-branch UNION with no `ever_purchased` join

- **Severity:** Medium
- **Location:** Phase 3 step 3 ("Thread `supply_stream` through ... `last_order_ctx` (add to `ROW_NUMBER() OVER (PARTITION BY ...)` and the final join)")
- **Flaw:** `last_order_ctx` is not a passthrough of `raw_purchases`; it is a separate CTE with its own two `fact_sales`→`config` / `dim_sku_alias` UNION-ALL branches and its own `ROW_NUMBER() OVER (PARTITION BY customer_key, sku ...)`. It never computes or joins `ever_purchased`, so "add supply_stream to GROUP BY / partition" is not mechanical — the column does not exist in that subtree. The final `LEFT JOIN last_order_ctx ON s.customer_key = ... AND s.sku = ... AND loctx.rn = 1` currently joins on `(customer_key, sku)`; adding `supply_stream` to the join key requires `last_order_ctx` to also carry a matching `supply_stream`, which requires replicating the classification there.
- **Failure scenario:** If the implementer adds `s.supply_stream` only to the outer join condition without producing `supply_stream` inside `last_order_ctx`, the SQL fails to compile (unknown column). If they instead leave `last_order_ctx` keyed on `(customer_key, sku)` and join the dual-stream `supply_stack` to it, a customer with a `gift_only` row and a stale `last_order_ctx` row can mis-attach `last_order_code`/`last_net_unit_price`, or produce a fan-out if both streams ever coexist for a key.
- **Evidence:** `int_customer_sku_supply_tracking.sql:149-249` (`last_order_ctx` self-contained 2-branch UNION, partition `:156` on `customer_key, sku` only) and `:269-272` (final join on `customer_key, sku`, `loctx.rn = 1`). Phase 3 provides SQL for the `ever_purchased`/`raw_purchases` classification but only a one-line prose instruction for `last_order_ctx`.
- **Suggested fix:** Add explicit SQL for how `last_order_ctx` obtains `supply_stream` (join `ever_purchased` inside it, or derive it and add to its partition), and confirm the outer join key. Given `ever_purchased` is all-or-nothing per `(customer,sku)`, document that only one stream exists per key so the join stays 1:1 — but write it, don't assert it.

---

## Cross-cutting note (not a separate finding)

- `fact_sales.sql` uses `location="{{ get_rolling_location() }}"` with no incremental config → full rebuild each run, so Phase 1's `is_gift_line` backfills historically. That claim checks out. `mart_customer_tier` is a full-recompute `table` sourced from `dim_customers` within the same dbt run, so intra-run tier↔fact staleness (task question 5) is low *inside the warehouse*. The real staleness risk is the CRM-side denormalization in Finding 3, not the marts.

---

## Unresolved questions for the planner

1. What fraction of *current* live SKU action cards belong to gift-only pairs (Finding 2)? Without this number the "backward-compat" criterion cannot be evaluated and the reps' queue-shrinkage cannot be sized.
2. Is the ever-purchased gift-inflation (Finding 1) an accepted permanent behavior, or was the user decision made without the Overview's own example in view? The decision as recorded does not fix the named bug for repeat buyers.
3. Given the CRM already resolves `strategic_tier` via the live join (Finding 3), is there any consumer that actually needs the denormalized column? If not, Phase 5's tier work is pure scope creep.
