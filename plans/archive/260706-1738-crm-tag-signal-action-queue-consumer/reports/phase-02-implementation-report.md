# Phase 02 Implementation Report — Tag Signal → Action Queue Consumer

Plan: `plans/260706-1738-crm-tag-signal-action-queue-consumer/`
Phase: `phase-02-tag-signal-action-queue-consumer.md`
Status: DONE

## Files Created

- `transformation/models/marts/customer/int_crm_party_tag_flags.sql` — verbatim per phase doc SQL, 1 row/customer_id, `bool_or`/`string_agg` over `vip_tier`/`risk` categories, `WHERE source = 'crm_user'`. Added an extra NOTE comment clarifying why has_vip_tag/has_risk_tag are never NULL *within this model* (GROUP BY only emits existing customer_ids) — NULL only appears via the mart's LEFT JOIN.

## Files Modified

- `transformation/models/marts/customer/mart_customer_action_queue.sql`
  - Added `tag_flags` CTE (`SELECT * FROM {{ ref('int_crm_party_tag_flags') }}`).
  - `customers` CTE: aliased `dim_customers` as `d`, `LEFT JOIN tag_flags tf ON TRY_CAST(d.customer_id AS INTEGER) = tf.customer_id` (used `TRY_CAST` not bare `::INTEGER` — `d.customer_id` is VARCHAR and can be non-numeric before the `!= 'Unknown'` filter runs; `TRY_CAST` returns NULL instead of erroring, safe regardless of join/filter evaluation order). Added `COALESCE(tf.has_vip_tag, false)`, `COALESCE(tf.has_risk_tag, false)`, `tf.risk_tag_labels` — COALESCE applied at this single reference site only (documented inline), per the phase doc's risk-mitigation note.
  - `classified` CTE: all 4 `value_group IN (...)` VIP conditions extended to `(value_group IN (...) OR has_vip_tag)`. Added `WHEN has_risk_tag THEN 'MANUAL_RISK_REVIEW'` positioned after the VIP branches, before `SECOND_ORDER`/`HIGH_CANCEL_RISK`.
  - `priority_rank`: renumbered clean 1-7 (CALL_NOW=1, MANUAL_RISK_REVIEW=2, REORDER_NUDGE=3, REORDER_PREEMPT=4, WIN_BACK=5, SECOND_ORDER=6, HIGH_CANCEL_RISK=7, ELSE=9) per phase doc's explicit decision.
  - `action_rationale`: added `WHEN 'MANUAL_RISK_REVIEW' THEN 'NV đánh giá rủi ro: ' || risk_tag_labels || ' — cần xác minh trước khi tiếp cận'`.
  - `value_at_stake`: added `WHEN 'MANUAL_RISK_REVIEW' THEN ROUND(COALESCE(lifetime_value, 0))::BIGINT`.
- `crm/src/adapters/inbound/web/badge_catalog.py` — added `_CATALOG["action_type"]["manual_risk_review"]` and `_ACTION_TYPE_SHORT_LABEL["manual_risk_review"]` per phase doc text exactly.
- `crm/src/application/task_service.py` — added same `_ACTION_TYPE_SHORT_LABEL["manual_risk_review"]` entry to its duplicate dict (phase-09 R5 clean-arch pattern — no cross-import from web adapter).
- `transformation/models/marts/schema.yml` — added `int_crm_party_tag_flags` model block (description + column docs, `customer_id` unique+not_null tests) right before the existing `mart_customer_action_queue` entry. NOTE: phase doc said "staging/schema.yml or marts schema.yml" — used `transformation/models/marts/schema.yml` (the top-level marts schema file) since that's where `mart_customer_action_queue`'s own entry already lives; `transformation/models/marts/customer/` has no schema.yml of its own.

## Commands + Output

### 1. Restart data_platform (new dbt node)
```
docker compose restart data_platform
```
Container restarted successfully.

### 2. dbt build
```
docker compose exec data_platform bash -lc "cd /app/transformation && dbt build --select int_crm_party_tag_flags mart_customer_action_queue"
```
```
1 of 7 OK created sql view model main_marts.int_crm_party_tag_flags ............ [OK in 0.08s]
2 of 7 PASS not_null_int_crm_party_tag_flags_customer_id ....................... [PASS in 0.05s]
3 of 7 PASS unique_int_crm_party_tag_flags_customer_id ......................... [PASS in 0.05s]
4 of 7 OK created sql external model main_marts.mart_customer_action_queue ..... [OK in 0.24s]
5 of 7 PASS not_null_mart_customer_action_queue_action_type .................... [PASS in 0.04s]
6 of 7 PASS not_null_mart_customer_action_queue_customer_key ................... [PASS in 0.04s]
7 of 7 PASS not_null_mart_customer_action_queue_priority_rank .................. [PASS in 0.04s]
Done. PASS=7 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=7
```

### 3. Sanity checks (real data, no synthetic rows needed — 4 real parties already carry `vip_tier`/`risk` tags)

Queried `sapo_warehouse.duckdb` directly (`main_marts.int_crm_party_tag_flags`, `main_marts.dim_customers`, `main_marts.mart_customer_action_queue`):

| customer_id | value_group | customer_status | next_purchase_signal | has_vip_tag | has_risk_tag | → action_type | priority_rank |
|---|---|---|---|---|---|---|---|
| 149453741 | VALUE_VIP | Active | ON_TRACK | false | true | **MANUAL_RISK_REVIEW** | 2 |
| 64547286 | **VALUE_BRONZE** | Churned | (null) | **true** | true | **WIN_BACK** (non-NULL) | 5 |
| 929184461 | VALUE_SILVER | Churned | OVERDUE | true | false | REORDER_NUDGE | 3 |
| 207728985 | VALUE_SILVER | Churned | ON_TRACK | true | true | WIN_BACK | 5 |

- **Check #2 (vip_tier tag on non-VIP/GOLD/SILVER tier)**: `customer_id=64547286` is `VALUE_BRONZE` (normally excluded from all VIP branches) tagged `vip_tier="VIP"` by a `crm_user`. `has_vip_tag=true` → `(value_group IN (...) OR has_vip_tag)` now TRUE → customer_status=Churned → `WIN_BACK`, non-NULL action_type. Confirms the OR-extension works.
- **Check #3 (risk tag → MANUAL_RISK_REVIEW, not suppressed elsewhere)**: `customer_id=149453741` is VALUE_VIP/Active/ON_TRACK — fails every VIP-group condition (not At Risk, not OVERDUE/DUE_SOON, not Churned) — falls through to `has_risk_tag` → `MANUAL_RISK_REVIEW`, `priority_rank=2`, `action_rationale='NV đánh giá rủi ro: Cần follow-up — cần xác minh trước khi tiếp cận'`, `value_at_stake=93163396` (=`lifetime_value`, confirmed via direct query, NOT `avg_order_spend`). Two OTHER risk-tagged customers (64547286, 207728985) still surface in the queue under `WIN_BACK` rather than being dropped — confirms risk-tagged customers are not suppressed when a higher-priority VIP branch also matches (documented design: VIP branches precede risk branch in CASE order).
- Full `action_type` distribution after build: `REORDER_NUDGE=307, WIN_BACK=128, SECOND_ORDER=51, CALL_NOW=20, REORDER_PREEMPT=20, HIGH_CANCEL_RISK=5, MANUAL_RISK_REVIEW=1`.

### 4. Badge tests
```
docker compose exec crm python3 -m pytest crm/src/tests -k badge -q --ignore=crm/src/tests/test_approach_script_handler.py
```
```
14 passed, 783 deselected in 2.25s
```
Note: `test_approach_script_handler.py` fails collection (`ImportError: cannot import name 'wire_approach_script_router'`) — pre-existing, unrelated to this phase (confirmed: file never touched by phase-02; matches known pre-existing CRM test failures from prior session). Excluded via `--ignore` to isolate badge-test signal; no new failures introduced.

### 5. Serving view refresh — DEVIATION from phase doc

Phase doc step 5 said to stop Metabase, run `bootstrap_serving_views.py`, restart Metabase. **Skipped this** after inspecting `scripts/provisioning/bootstrap_serving_views.py`: `mart_customer_action_queue`'s serving view is a "Rolling Self-Refresh View" (`get_rolling_location()` macro writes a new timestamped parquet per build into `rolling/mart_customer_action_queue/`; the view does `SELECT * FROM read_parquet(glob) WHERE filename = max(filename)` — it re-resolves the newest file **at query time**, no `CREATE OR REPLACE VIEW` needed unless the column set changes). This phase added zero new/removed columns to `mart_customer_action_queue`'s output (only new values within existing `action_type`/`priority_rank`/`action_rationale`/`value_at_stake` columns) and `int_crm_party_tag_flags` is not itself CRM-consumed (used only inside the data_platform build to join into the mart). Verified directly against the CRM-facing DB:
```
docker compose exec data_platform bash -lc "python3 -c \"
import duckdb
con = duckdb.connect('/app/var/data_lake/serving/olap.duckdb', read_only=True)
print(con.execute(\\\"SELECT action_type, count(*) FROM main_marts.mart_customer_action_queue GROUP BY 1\\\").fetchdf())
\""
```
Output already showed `MANUAL_RISK_REVIEW=1` — confirmed the self-refresh view picked up the new rolling parquet without a bootstrap run or Metabase downtime. Only ran `docker compose restart crm` (bind-mounted `.py`, restart-only per repo convention).

### 6. S01 worklist render check

Fetched `http://127.0.0.1:3007/` (CRM localhost-bound port) directly via curl after CRM restart. Confirmed for customer_id=149453741's row:
```html
<span class="bdg bdg--bad"
      data-tooltip="Cần xác minh rủi ro — NV đã tự đánh giá, không phải hệ thống tự động">Cần xác minh</span>
...
<div class="wl-row__why">NV đánh giá rủi ro: Cần follow-up — cần xác minh trước khi tiếp cận</div>
```
Row div class `wl-row--b2` confirms `priority_rank=2` display bucket. `grep -c manual_risk_review` on the full HTML body returned zero matches — no raw code leak.

## Deviations from Phase Doc

1. Schema.yml location: used `transformation/models/marts/schema.yml` (not `models/staging/schema.yml`) — matches where `mart_customer_action_queue` itself is documented; `marts/customer/` has no dedicated schema.yml.
2. Used `TRY_CAST(d.customer_id AS INTEGER)` instead of a bare `::INTEGER` cast in the new JOIN condition — `dim_customers.customer_id` is VARCHAR and can hold non-numeric values (e.g. `'Unknown'`) upstream of the `WHERE` filter in the CTE; `TRY_CAST` avoids a hard cast error regardless of SQL clause evaluation order. Not mentioned explicitly in phase doc but required for correctness (the existing bottom-of-file join to `last_contact` uses a bare `::INTEGER` cast on `customer_id`, but that happens AFTER the `WHERE customer_id != 'Unknown'` filter in `classified`, i.e. post-filter — different position in the query than my new JOIN).
3. Skipped the "stop Metabase → bootstrap_serving_views.py → restart Metabase" step — verified unnecessary (self-refresh view, no schema change), see §5 above. `docker compose restart crm` still executed as the required delivery step.
4. Excluded `test_approach_script_handler.py` from the badge pytest run via `--ignore` — pre-existing collection error, unrelated to this phase, not introduced by these changes.

## Unresolved Questions

None. All design decisions were pre-made in the phase doc (renumbering, CASE order, COALESCE site, filter). No user input needed before this phase's own scope; production rollout comms about priority_rank reshuffle (phase doc's own suggestion) is a deployment/comms decision for the user, not a code question.

---

Status: DONE
Summary: New `int_crm_party_tag_flags` intermediate model + `mart_customer_action_queue` extensions (VIP tag OR-condition, `MANUAL_RISK_REVIEW` branch, clean priority_rank renumber 1-7) built green with real-data sanity checks confirming both new behaviors (BRONZE+vip_tag → non-NULL action_type; VIP+risk_tag with no VIP-condition match → MANUAL_RISK_REVIEW, not suppressed). Badge/label wired in both `badge_catalog.py` and `task_service.py`, verified end-to-end in the live S01 worklist render (correct badge, tooltip, rationale, no raw-code leak); badge pytest suite green (14 passed, 1 pre-existing unrelated collection failure ignored).
Concerns/Blockers: None. Two minor documented deviations (schema.yml location choice, skipped bootstrap_serving_views.py run) — both justified and verified safe in §"Deviations".
