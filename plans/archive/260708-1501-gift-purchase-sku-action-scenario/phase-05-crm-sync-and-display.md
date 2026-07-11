---
phase: 5
title: "CRM Sync and Display"
status: pending
priority: P2
dependencies: [4]
---

# Phase 5: CRM Sync and Display

## Overview

Sync `supply_stream` (new from Phase 3/4) từ warehouse mart xuống CRM cache.db, wire vào read path, và đảm bảo `GIFT_TO_PURCHASE` hiển thị đúng khi enable. Tận dụng cơ chế filter chip tự động (`available_action_types()`/`available_strategic_tiers()` đã dynamic-derive từ dữ liệu) — phần lớn KHÔNG cần sửa code CRM filter.

> **Sửa sau red-team**: bản gốc phase này định denormalize `strategic_tier` vào `wh_sku_action_queue` — 2 reviewer độc lập (Assumption Destroyer, Security Adversary) chỉ ra `cache_repository.py` đã resolve `strategic_tier` qua `LEFT JOIN wh_customer_tier` sẵn (`cache_repository.py:176,213-214,418,433-437`) và bản gốc cũng recommend GIỮ JOIN đó — nghĩa là cột denormalized sẽ được ghi nhưng không bao giờ đọc (dead work), có nguy cơ lệch dữ liệu giữa 2 nguồn theo 2 chu kỳ refresh khác nhau. **Bỏ hẳn việc denormalize `strategic_tier`** — JOIN hiện có đã đủ. Chỉ sync `supply_stream` (dữ liệu THẬT SỰ mới, không có cách nào lấy qua JOIN hiện có) và wire nó vào read path.

## Requirements

- Functional: `wh_sku_action_queue` có cột `supply_stream`; reverse-ETL đọc đúng cột mới từ `mart_customer_sku_action_queue`; `cache_repository.py` đọc và trả `supply_stream` trong response.
- Functional: cache schema migration cho cột mới phải chạy trên `cache.db` HIỆN CÓ (production), không chỉ trên DB mới tạo — xem Critical fix ở step 1.
- Functional: `GIFT_TO_PURCHASE` render đúng badge màu + nhãn tiếng Việt (không phải text tiếng Anh thô) khi enable.
- Non-functional: không phá vỡ `available_action_types()`/`available_strategic_tiers()` cơ chế dynamic hiện có.
- Non-functional: KHÔNG denormalize `strategic_tier` (dead work — xem Overview).

## Architecture

```
mart_customer_sku_action_queue (supply_stream — Phase 3/4; strategic_tier đã có sẵn qua JOIN, KHÔNG denormalize thêm)
         │
         ▼
crm/sync/duckdb_reader.py  fetch_sku_action_queue()  -- thêm supply_stream vào SELECT
         │
         ▼
crm/sync/sqlite_upsert.py
  ① apply_schema() — thêm ALTER TABLE wh_sku_action_queue ADD COLUMN supply_stream
     vào _group_a (BẮT BUỘC — CREATE TABLE IF NOT EXISTS là no-op trên DB đã tồn tại)
  ② upsert_sku_action_queue() — thêm supply_stream vào INSERT/UPDATE column list
         │
         ▼
crm/sync/cache_schema.sql  wh_sku_action_queue        -- thêm cột supply_stream (CREATE TABLE
                                                            định nghĩa cho DB MỚI; DB CŨ cần ① ở trên)
         │
         ▼
crm/src/adapters/outbound/sqlite/cache_repository.py  _sku_branch()
  -- thêm supply_stream vào SELECT + domain object; GIỮ NGUYÊN JOIN wh_customer_tier
     cho strategic_tier (không đổi)
         │
         ▼
crm/src/adapters/outbound/sqlite/badge_catalog.py
  -- thêm GIFT_TO_PURCHASE vào color dict + short-label dict (nếu không, badge hiện
     màu neutral + text tiếng Anh thô)
         │
         ▼
S01 worklist filter chips (available_action_types/available_strategic_tiers)
  -- KHÔNG cần sửa code — tự động nhận GIFT_TO_PURCHASE khi enable ở Phase 4
```

## Related Code Files

- Modify: `crm/sync/cache_schema.sql` (add `supply_stream` to `wh_sku_action_queue` CREATE TABLE definition; update comment listing action_type values to include `GIFT_TO_PURCHASE`)
- Modify: `crm/sync/sqlite_upsert.py` (**Critical**: add `ALTER TABLE wh_sku_action_queue ADD COLUMN supply_stream TEXT` to the `_group_a` migration list in `apply_schema()`; add `supply_stream` to `upsert_sku_action_queue()`'s parameterized INSERT/UPDATE column list)
- Modify: `crm/sync/duckdb_reader.py` (`fetch_sku_action_queue` SELECT — add `supply_stream`)
- Modify: `crm/src/adapters/outbound/sqlite/cache_repository.py` (`_sku_branch()` — add `supply_stream` to SELECT + returned object; leave the existing `wh_customer_tier` JOIN untouched)
- Modify: `crm/src/adapters/outbound/sqlite/badge_catalog.py` (add `GIFT_TO_PURCHASE` entry to the color dict and the Vietnamese short-label dict)
- Review only (no change expected — dynamic derivation): `crm/src/application/worklist_filters.py`

## Implementation Steps

1. **`sqlite_upsert.py` — Critical fix (post red-team, Failure Mode Analyst Finding 1)**: `apply_schema()` runs `executescript` against `cache_schema.sql` (which is `CREATE TABLE IF NOT EXISTS` — a no-op against an existing table) PLUS a hardcoded `_group_a` list of explicit `ALTER TABLE ... ADD COLUMN` statements for columns added after the table's original creation (this is the established pattern — every prior `wh_sku_action_queue` column, e.g. `last_sku_discount_rate`, needed an explicit ALTER entry). Add:
   ```python
   # in _group_a (or equivalent migration list in apply_schema()):
   "ALTER TABLE wh_sku_action_queue ADD COLUMN supply_stream TEXT",
   ```
   **Without this, the very first reverse-ETL run against an existing production `cache.db` will fail** — `CREATE TABLE IF NOT EXISTS` no-ops, `upsert_sku_action_queue()` then runs an INSERT with one more placeholder than the table has columns, `_run_step` re-raises, and the ENTIRE reverse-ETL run aborts (including unrelated steps like `wh_customer_tier`, `wh_customer_base`, `wh_deadstock_target` that run after `wh_sku_action_queue` in `reverse_etl_warehouse_to_crm.py`'s step order). Verify by reading `apply_schema()`'s exact structure before writing this — confirm the `_group_a` list name and pattern match current code (may have been renamed since this plan was written).

2. `cache_schema.sql`: add to `wh_sku_action_queue`'s `CREATE TABLE IF NOT EXISTS` definition (for NEW databases — existing ones rely on step 1's ALTER):
   ```sql
   supply_stream    TEXT,   -- purchased|gift_only (see int_customer_sku_supply_tracking, Phase 3)
   ```
   Update the header comment listing action_type values: `USAGE_FOLLOWUP|PROGRESS_CHECK|REORDER_PREEMPT|REORDER_NUDGE|REORDER_OVERDUE|GIFT_TO_PURCHASE`.

3. `duckdb_reader.py` `fetch_sku_action_queue()`: add `supply_stream` to the `SELECT ... FROM main_marts.mart_customer_sku_action_queue` query. Do NOT add `strategic_tier` here — it's already resolved downstream via the `wh_customer_tier` JOIN in `cache_repository.py`.

4. `sqlite_upsert.py` `upsert_sku_action_queue()`: add `supply_stream` to the parameterized INSERT/UPDATE (follow existing pattern for how `last_sku_discount_rate` etc. were added).

5. Rebuild `crm` container (schema change, per `feedback_new_mart_crm_serving_integration.md`): `docker compose up -d --build crm`. Confirm this happens AFTER step 1's migration is in place and BEFORE the next reverse-ETL run (see `plan.md` § Deploy Sequencing for full ordering across all 5 phases).

6. `cache_repository.py`: add `supply_stream` to `_sku_branch()`'s SELECT and the returned action-queue domain object/dict. Leave the existing `wh_customer_tier` JOIN for `strategic_tier` completely untouched — do not denormalize `strategic_tier` (see Overview).

7. `badge_catalog.py` (post red-team, Assumption Destroyer Finding 4): action-type-to-badge rendering is a hardcoded dict lookup with an `_NEUTRAL` fallback that shows the raw English `action_type` string on miss. Add `GIFT_TO_PURCHASE` to both the color dict and the Vietnamese short-label dict — otherwise it renders as a neutral-colored badge with raw English text on an otherwise-Vietnamese CS worklist. Also check `reason_rail.py` (branches on action_type too) for a similar gap.

8. Verify `available_action_types()`/`available_strategic_tiers()` in `worklist_filters.py` pick up any new distinct values automatically — no code change expected, but run a manual check: with Phase 4's `GIFT_TO_PURCHASE` temporarily flipped to `enabled=true` in a test environment, confirm the filter chip appears on S01 without a CRM deploy.

9. Resume CRM reverse-ETL (per `plan.md` § Deploy Sequencing — this must be the LAST step, after Phases 3+4's regression diff is verified clean and step 1's migration is deployed) → verify `wh_sku_action_queue` row counts match `mart_customer_sku_action_queue` output, and confirm the expected gift-only-population drop (quantified in Phase 3 step 6d) matches what actually happened.

## Success Criteria

- [ ] `sqlite_upsert.py`'s `apply_schema()` migration list includes the `supply_stream` ALTER — verified by running reverse-ETL against a COPY of an existing production-shaped `cache.db` (not just a freshly-created one) without error
- [ ] `wh_sku_action_queue` has `supply_stream` column, populated for all rows, read by `cache_repository.py` and included in the API/response
- [ ] `strategic_tier` is NOT denormalized into `wh_sku_action_queue` (existing JOIN in `cache_repository.py` is untouched and still the only source)
- [ ] `badge_catalog.py` renders `GIFT_TO_PURCHASE` with a real color + Vietnamese short-label, not the neutral fallback
- [ ] Reverse-ETL run completes without error, row count matches warehouse mart output, gift-only-population drop matches Phase 3's pre-deploy quantification
- [ ] S01 worklist filter chips include `GIFT_TO_PURCHASE` when test-enabled, with zero `worklist_filters.py` code changes
- [ ] No regression in existing action-queue display (7 customer-level + 5 sku-level action types still render correctly with existing rationale copy)
- [ ] `docker compose up -d --build crm` completes, CRM app starts healthy

## Risk Assessment

- **Critical risk (addressed by step 1)**: without the `apply_schema()` ALTER-list entry, this phase breaks the ENTIRE nightly reverse-ETL on first run against production `cache.db`, not just the SKU queue sync — every step after `wh_sku_action_queue` in `reverse_etl_warehouse_to_crm.py`'s run order silently stops executing too. Test against a copy of a real (non-empty, already-migrated) cache.db, not a fresh one, or this gap will not surface in testing.
- **Low-medium risk otherwise**: additive schema column, no removal of existing columns in this phase.
- **Risk**: PII/scope check — `supply_stream` is not customer-identifying, safe to sync.
- **Risk**: forgetting the container rebuild step (schema.sql changes require rebuild, not just restart — code-only changes would only need restart, per project convention) — call out explicitly in the deploy runbook (`plan.md` § Deploy Sequencing).
- **Rollback**: `supply_stream` column can be left unpopulated (NULL) without breaking existing queries if reverse-ETL rollback is needed. No `strategic_tier` denormalization means no divergent-state rollback concern for that field.
