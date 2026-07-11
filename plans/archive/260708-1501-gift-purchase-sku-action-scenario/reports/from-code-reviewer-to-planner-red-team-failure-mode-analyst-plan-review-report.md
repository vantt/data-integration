# Red-Team Plan Review — Failure Mode Analyst (Flow Tracer)

Plan: `plans/260708-1501-gift-purchase-sku-action-scenario`
Reviewer role: hostile failure-mode analyst; verification lens = flow tracer (entry → guards → branching → target).
Verdict: **Not ship-ready.** Two Critical state-corruption/deploy-failure gaps and three High-severity data-loss / rollback holes. The plan's regression guard is scoped to the one metric that will NOT change and blind to the ones that will.

---

## Finding 1: Phase 5 adds cache columns to CREATE TABLE but not to the `apply_schema` ALTER migration list — nightly reverse-ETL aborts on every existing cache.db

- **Severity:** Critical
- **Location:** Phase 5, "Implementation Steps" step 1 + "Related Code Files"
- **Flaw:** Phase 5 adds `supply_stream` / `strategic_tier` only to the `CREATE TABLE IF NOT EXISTS wh_sku_action_queue` block in `cache_schema.sql` and to the `upsert_sku_action_queue` column list. On a database that already exists (production cache.db), `CREATE TABLE IF NOT EXISTS` is a no-op — it never adds columns. New columns reach an existing DB ONLY via the hardcoded `_group_a` ALTER list inside `apply_schema()`. The plan never edits that list.
- **Failure scenario:** After deploy, `apply_schema()` runs `executescript(_SCHEMA_SQL)` (no-op on the existing table), skips `_group_a` (no supply_stream entry), then `upsert_sku_action_queue` issues an `INSERT ... (17 columns) VALUES (17 ?)` against a 15-column table → `sqlite3.OperationalError: table wh_sku_action_queue has 15 columns but 17 values were supplied`. `_run_step` logs status=failed and **re-raises** (`reverse_etl_warehouse_to_crm.py:82`), aborting the entire ETL. Every step ordered after `wh_sku_action_queue` — `wh_customer_tier`, `wh_customer_base`, `wh_product`, `wh_order_hdr`, `wh_deadstock_target`, `wh_party_seed` — never runs. The whole CRM cache goes stale nightly, not just the SKU queue. "Rebuild the crm container" does NOT fix it: cache.db is persisted data, not baked into the image, so a rebuild re-runs the same `CREATE IF NOT EXISTS` no-op.
- **Evidence:** `crm/sync/sqlite_upsert.py:47-113` (`apply_schema` = `executescript` + hardcoded `_group_a` ALTER list); precedent at `sqlite_upsert.py:83-86` — every prior `wh_sku_action_queue` column (`last_purchase_date`, `last_order_code`, `last_sku_discount_rate`, `last_net_unit_price`) required an explicit `ALTER TABLE ... ADD COLUMN` entry. Abort-on-failure at `reverse_etl_warehouse_to_crm.py:71-82`. Ordering at `reverse_etl_warehouse_to_crm.py:183-206`.
- **Suggested fix:** Phase 5 must add two `ALTER TABLE wh_sku_action_queue ADD COLUMN supply_stream TEXT` / `ADD COLUMN strategic_tier TEXT` entries to `_group_a` in `sqlite_upsert.py`, matching the 2026-06-29 precedent. Editing `cache_schema.sql` alone is insufficient and is the exact mistake the existing migration list was built to prevent.

---

## Finding 2: On ship day, every "gift-only" customer's live action is silently DELETED from the queue, orphaning any claimed CRM task — no state migration is defined

- **Severity:** Critical
- **Location:** Phase 3 (grain split) + Phase 4 step 1 (ships `GIFT_TO_PURCHASE` with `enabled=false`)
- **Flaw:** Today, `int_customer_sku_supply_tracking` sums ALL quantity — including gift lines — into `effective_supply_days`, so a customer who was only ever *gifted* SKU X still gets an `estimated_depletion_date` and currently produces live `REORDER_*` actions. After Phase 3 those (customer, sku) pairs route to `supply_stream='gift_only'`, and Phase 4 maps them exclusively to `GIFT_TO_PURCHASE`, which ships `enabled=false`. The registry `WHERE COALESCE(reg.enabled, TRUE)=TRUE` then filters every such row out of the mart. The reverse-ETL treats a vanished mart row as "signal gone" and DELETEs it from cache.
- **Failure scenario:** The night Phase 3+4 land, `upsert_sku_action_queue` computes today's batch (gift-only rows absent), then executes `DELETE FROM wh_sku_action_queue WHERE (customer_key, sku, action_type) NOT IN (<batch>)` — hard-deleting every gift-only customer's previously-live `REORDER_*` row. A sales rep who had **claimed** one of those actions holds an open `crm_task` whose `source_ref = action_id` now points at a deleted cache row; the action disappears from S01/S14 mid-workflow, the task is orphaned (no worklist row to resolve against), and completion counters desync. This is a real population: the plan's own motivation (`plan.md:23`, finejapan report) says Metabo/Gaba/Coix are gifted 67–78% of the time. The plan never enumerates how many live actions disappear, never migrates or reopens the orphaned tasks, and never warns reps.
- **Evidence:** current all-quantity summation at `int_customer_sku_supply_tracking.sql:36-95` (no `is_gift_line` filter anywhere); signal-based DELETE at `crm/sync/sqlite_upsert.py:308-318`; ship-disabled at Phase 4 step 1 line 66 (`GIFT_TO_PURCHASE,...,false,...`); task keyed on action_id via `source_ref` at `crm/src/application/task_service.py:341-367,434-455`.
- **Suggested fix:** Before ship, quantify the gift-only population that currently produces live actions and the subset with open/claimed `crm_task`s. Either (a) keep those customers' current `REORDER_*` behavior until `GIFT_TO_PURCHASE` is enabled (i.e. don't strip the signal while its replacement is disabled), or (b) add an explicit task-reconciliation step that reopens/annotates orphaned tasks. Add an acceptance criterion asserting zero live actions silently deleted for customers with an open task.

---

## Finding 3: `ever_purchased` is an all-history fact — one new purchase flips `supply_stream`, resetting `action_type`/`action_id`/`pending_since` and re-triggering the exact B5 "dismissed action reappeared" bug

- **Severity:** High
- **Location:** Phase 3 step 1-2 (`ever_purchased` CTE, `supply_stream` classification)
- **Flaw:** `supply_stream` is derived from `ever_purchased`, a static per-(customer, sku) boolean over ALL history. A customer who is gift-only today becomes `purchased` the instant they place any real order for that SKU. Because `action_id = md5(customer_key|sku|action_type|pending_since)` and `action_type` flips `GIFT_TO_PURCHASE → REORDER_*` on that transition, the action_id changes and `pending_since` resets to the new episode date.
- **Failure scenario:** Rep dismisses or snoozes a `GIFT_TO_PURCHASE` action. The B5 cross-episode memory (`crm_action_dismissal`) is keyed on `(party_id, action_type)` — but `action_type` itself changed, so the dismissal does not match the new `REORDER_*` row. The customer reappears at the top of the worklist the next night with a fresh `pending_since`, which UX doc B5 explicitly flags as the trust-eroding "NV thấy việc đã bỏ quay lại" bug. The plan modifies the very grain that feeds action_id and does not analyze the impact on either the action_id-keyed `crm_action_state` (snooze) or the action_type-keyed `crm_action_dismissal` (B5) memory.
- **Evidence:** action_id formula at `crm/sync/sqlite_upsert.py:281-282` and `cache_schema.sql:224`; B5 dismissal keyed on `(party_id, action_type)` at `crm/src/adapters/outbound/sqlite/action_state_repository.py:67-79`; B5 bug already documented at `crm/docs/ui-spec/notes/ux-action-queue-task-cockpit-data-loop-design.md:119` ("warehouse sinh action_id mới cùng nội dung, dismiss cũ gắn action_id cũ").
- **Suggested fix:** Document the stream-transition state-transfer explicitly. Decide whether a gift→purchase transition should preserve dismissal/snooze memory (map old `GIFT_TO_PURCHASE` dismissal onto the successor `REORDER_*`) or intentionally reset it, and add a test asserting the chosen behavior. At minimum, add a Phase 3 risk entry acknowledging the pending_since/action_id churn this introduces.

---

## Finding 4: No production rollback path — Phase 3 says "same deploy window" as Phase 4 but also "don't proceed until diff clean"; the parquet is overwritten in place and nightly reverse-ETL mutates action-state before anyone can validate

- **Severity:** High
- **Location:** Phase 3 "Risk Assessment" (bullets: "land Phase 3 and Phase 4 in the same deploy window" vs "Do not proceed to Phase 4 until the regression diff is clean")
- **Flaw:** These two mitigations contradict each other. If 3 and 4 must ship together (because Phase-3-alone breaks the downstream mart's grain), then the regression diff cannot be a gate *between* them in production — by the time you can diff the live mart, Phase 4 has already shipped. The plan's rollback story ("registry revert to all-true", "additive columns") does not cover the recursive-CTE grain change: `int_customer_sku_supply_tracking` is `materialized='table'` and the two action marts are external parquet at `get_rolling_location()` — each `dbt run` overwrites them in place. There is no snapshot-restore path; step 6's snapshot is used only for *diffing*, never for *restoring*.
- **Failure scenario:** Phase 3/4 dbt run completes; the nightly reverse-ETL cron fires before anyone inspects the diff; it recomputes action_ids, resets `pending_since` for shifted rows, and DELETEs disappeared signals (Finding 2). A dirty diff is discovered the next morning. Reverting the SQL and re-running dbt regenerates the mart — but the cache's `crm_action_state` / `crm_action_dismissal` / `crm_task` rows have already been mutated against the now-reverted action_ids. The warehouse rolls back; the CRM operational state does not. The damage is one-way.
- **Evidence:** table materialization at `int_customer_sku_supply_tracking.sql:1-4`; parquet-external marts at `mart_customer_sku_action_queue.sql:1-5` and `mart_customer_action_queue.sql:1-5`; unconditional nightly upsert+DELETE at `crm/sync/sqlite_upsert.py:305-318`; no reverse-ETL gate/dry-run flag in `reverse_etl_warehouse_to_crm.py`.
- **Suggested fix:** Define an explicit rollback runbook: (a) gate/pause the reverse-ETL cron during the Phase 3/4 deploy window so the mart can be diffed before any cache mutation; (b) resolve the contradiction — either ship behind a feature branch with the regression diff run against a non-serving schema, or accept that "same deploy window" means the diff gate happens pre-merge, not in production. State how cache action-state is restored if the mart is rolled back after a reverse-ETL run.

---

## Finding 5: Registry `COALESCE(reg.enabled, TRUE)` fails OPEN, and the new seed has no `+column_types` boolean coercion — `GIFT_TO_PURCHASE` can ship accidentally LIVE

- **Severity:** High
- **Location:** Phase 4 step 4 (`AND COALESCE(reg.enabled, TRUE) = TRUE`) + step 1 (new `seed_action_scenario_registry.csv`)
- **Flaw:** The plan bills `COALESCE(reg.enabled, TRUE)` as a "safety net" so a missing registry row never drops an existing action. But for the one scenario deliberately shipped OFF (`GIFT_TO_PURCHASE`, `enabled=false`), fail-open is the *dangerous* direction: any condition that makes `reg.enabled` read as NULL or non-FALSE flips the unreviewed scenario ON in front of real reps. Two concrete ways that happens: (1) if the `dbt seed` isn't re-loaded but `dbt run` executes (the plan's own toggle instruction is "seed edit + `dbt seed && dbt run`" — if the seed step is skipped or fails, the join finds no row → NULL → COALESCE→TRUE); (2) the new seed is not registered in `dbt_project.yml`'s `+column_types`, so DuckDB's CSV sniffer infers the `enabled` column's type. Existing seeds that carry booleans (`ref_order_sources.status`, `is_generic_source`) are forced to `boolean` explicitly precisely because the team hit this — if `enabled` loads as VARCHAR `'false'`, then `COALESCE(reg.enabled, TRUE) = TRUE` compares a string to a boolean (coercion/always-open behavior, not the intended `'false'→suppressed`).
- **Failure scenario:** `GIFT_TO_PURCHASE` — which the plan states has no finalized timing rule (Unresolved Q#1) and no approved rationale copy — surfaces on the live S01 worklist with placeholder "14–45 days" logic and draft copy, because the disable mechanism silently failed open. Reps start calling customers on an unreviewed play.
- **Evidence:** fail-open predicate at Phase 4 step 4 line 124 and Architecture line 45; boolean seeds requiring explicit `+column_types` at `transformation/dbt_project.yml:17-23` (`status: boolean`, `is_generic_source: boolean`); new seed absent from that config; prior repo seed type-inference footgun in memory (`feedback_duckdb_integer_underscore.md`).
- **Suggested fix:** For a not-yet-approved scenario, fail CLOSED, not open — e.g. maintain an explicit enabled-allowlist or default unknown action_types to suppressed until the row is present. Register `seed_action_scenario_registry` in `dbt_project.yml` with `enabled: boolean` (and text columns as varchar). Add a test asserting `GIFT_TO_PURCHASE` produces zero output rows while `enabled=false`.

---

## Finding 6: The Phase 3 regression guard checks only `estimated_depletion_date` for zero-gift customers — i.e. the population and metric guaranteed NOT to change — and is blind to the rows that will

- **Severity:** Medium
- **Location:** Phase 3 step 6 ("Regression test — before/after comparison") + Success Criteria
- **Flaw:** The guard joins old vs new on `supply_stream='purchased'` and asserts zero `estimated_depletion_date` diffs "for customers with no gift-line history." By construction those customers have no gift lines, so nothing about their computation changed — the test is guaranteed to pass and proves nothing about the risky paths. It does not assert: (a) purchased-stream customers who *do* have gift lines (ever_purchased=TRUE, gifts still summed) keep identical output; (b) the total set of emitted `action_type`s and row counts is unchanged; (c) no (customer, sku) that previously emitted a live action now emits none. The genuinely at-risk rows (gift-bearing, and gift-only-now-suppressed) are outside the test's WHERE clause.
- **Failure scenario:** A subtle error in the `ever_purchased` join (e.g. the pack/alias UNION branch flagged as an optional TODO in step 1's comment is omitted) reclassifies real purchasers as gift-only. The regression test still shows "0 rows" because it only inspects the untouched zero-gift population, and the corruption ships undetected.
- **Evidence:** test WHERE scope at Phase 3 step 6 lines 104-108; the pack/alias branch left as an unresolved "add a second UNION here … (recommended: yes)" comment at Phase 3 step 1 lines 65-71 — an unclosed decision inside the highest-risk model; downstream action derivation depends entirely on this grain at `mart_customer_sku_action_queue.sql:75-91`.
- **Suggested fix:** Broaden the regression assertion to full action-level parity: compare pre/post `action_type` and row count per (customer, sku) across the *entire* population with `enabled` defaults matching current behavior, and explicitly assert the count of newly-actionless customers. Resolve the pack/alias UNION decision before implementation, not in a code comment.

---

## Finding 7: Replacing the marts' `is_contactable` with `mart_customer_tier.is_contactable` is a silent behavior change for obfuscated-phone customers — not covered by the registry and asserted (not proven) equivalent

- **Severity:** Medium
- **Location:** Phase 4 step 2 ("Join `mart_customer_tier`, drop duplicated `is_contactable`") + plan.md:49
- **Flaw:** Both action marts currently compute `is_contactable = (phone IS NOT NULL AND phone <> '')`. `mart_customer_tier` derives contactability from `source_contact_quality`, where `'masked' = NULL/empty/obfuscated(*) phone (marketplace relay)`. These are NOT equivalent: a marketplace-relay customer with an obfuscated `*…` phone is `is_contactable=TRUE` under the current mart expression (non-null, non-empty) but `masked → not-contactable` under the tier definition. The plan asserts the tier version merely "replaces 3x-duplicated ad-hoc computation" (plan.md:49) and that behavior is "identical when registry defaults all enabled" (Phase 4 non-functional req) — but the registry only gates action_type on/off, not the contactability predicate, and no parity test is specified.
- **Failure scenario:** Every customer whose phone is obfuscated flips `is_contactable` TRUE→FALSE on the swap. Downstream CRM display/filter chips (`available_strategic_tiers`, contactability-based filtering) silently change which customers reps see, with no registry toggle and no line item in the acceptance criteria flagging it.
- **Evidence:** current mart expression at `mart_customer_sku_action_queue.sql:44`; tier contactability semantics at `mart_customer_tier.sql:11` and pass-through at `mart_customer_tier.sql:28,74`; plan's equivalence assertion at `plan.md:49` and Phase 4 line 20.
- **Suggested fix:** Before the swap, run a diff of `is_contactable` old-vs-tier across all customers and quantify the flips. If the semantic change is intended, call it out as a behavior change in the acceptance criteria; if not, keep the phone-presence expression. Do not present a semantic change as a pure dedup.

---

## Cross-cutting deploy-ordering note (not a standalone finding)

The five phases touch three runtimes that must be sequenced: `dbt seed`/`dbt run` (with `data_platform` restart for the new node + seed, per `feedback_dbt_node_needs_manifest_reload.md`), `bootstrap_serving_views.py` with Metabase stopped (parquet grain change, per `feedback_duckdb_view_rebuild.md`), and the CRM cache migration + container rebuild + reverse-ETL. The plan lists these constraints individually across phases but never as one ordered deploy runbook with the reverse-ETL pause from Finding 4. Given Findings 1–4 all live at phase boundaries, a single ordered cutover checklist is required before execution.

## Unresolved Questions

1. How many gift-only (customer, sku) pairs currently emit live actions, and how many have an open/claimed `crm_task`? This number determines whether Finding 2 is a minor blip or a mass task-orphaning event — the plan must measure it before ship.
2. Is `mart_customer_tier.is_contactable` intended to change contactability for obfuscated-phone customers (Finding 7), or is byte-identical parity required?
3. On a gift→purchase stream transition (Finding 3), should dismissal/snooze memory transfer to the successor action_type or intentionally reset?
