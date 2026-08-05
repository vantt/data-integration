---
title: "CRM — Suggestion Settings panel (per-party × action_type × mart suppression)"
description: "Dedicated Customer 360 tab where staff explicitly toggle opportunity types off per customer with a chosen end date, backed by a mart-aware crm_action_dismissal."
status: pending
priority: P2
effort: 13h
branch: feat/crm-suggestion-settings-panel
tags: [crm, worklist, suppression, action-queue, htmx, migration, dbt]
created: 2026-08-05
---

# Suggestion Settings panel — Customer 360

## Problem

Staff confuse "bỏ qua việc này" (dismiss one card) with "tắt gợi ý loại này" (stop future suggestions).
4 suppression mechanisms exist, none is a discoverable settings surface. Suppression only happens as a
side-effect of dismissing an already-active card, lives a hardcoded 30 days, and cannot distinguish
customer-level from SKU-level `REORDER_NUDGE`/`REORDER_PREEMPT`.

## Solution

New C360 tab **P07 "Cài đặt gợi ý"**: lists the full action_type catalog (from the dbt seed
`seed_action_scenario_registry`, grouped by `scenario_group`), shows current state per row
(bật / tắt tới ngày X / bởi ai), and lets staff toggle any type off with a staff-chosen end date —
without needing an active action to exist. Same table as the existing quick-dismiss, extended with a
`source_mart` discriminator.

## Locked decisions

| # | Decision |
|---|---|
| D1 | `source_mart` values = exact registry mart names (`mart_customer_action_queue`, `mart_customer_sku_action_queue`). No new taxonomy. |
| D2 | Migration backfill **expands** each legacy row into 2 rows (one per mart) — no `'ANY'` sentinel. Preserves legacy "suppress everywhere" semantics; keeps read predicate plain equality. |
| D3 | Registry reaches CRM via dbt marts passthrough → parquet → `olap.duckdb` → reverse-ETL → `cache.wh_action_scenario_registry`. Never a CRM-side copy of the taxonomy. |
| D4 | Quick-dismiss now records the **precise** mart it resolved from — behavior change, see Risk R3. |
| D5 | `_fetch_actions()` (C360 reason rail) is NOT filtered — deliberate, verified `cache_repository.py:9-15`. |
| D6 | `_DISMISSAL_TTL_DAYS = 30` stays as the quick-dismiss default; only the panel supplies explicit dates. |
| D7 | No `sku` column. Per-SKU suppression stays with per-`action_id` dismiss. |
| D8 | `do_not_contact` (mechanism #3) is **NOT touched** by this feature. |

## Phases

| # | Phase | Effort | Blocked by | Owns |
|---|-------|--------|-----------|------|
| 01 | [Expose registry to serving layer](phase-01-warehouse-registry-serving-exposure.md) | 1.5h | — | `transformation/**` |
| 02 | [Sync registry into cache.db](phase-02-sync-registry-to-cache-db.md) | 2h | 01 | `crm/sync/**` |
| 03 | [Migration 0046 — source_mart](phase-03-migration-source-mart-discriminator.md) | 1.5h | — | `crm/migrations/0046_*` |
| 04 | [Suppression repository + ports](phase-04-suppression-repository-and-ports.md) | 2h | 03 | `action_state_repository.py`, `domain/ports/`, `domain/entities/action_dismissal.py` |
| 05 | [Worklist read path per mart](phase-05-worklist-read-path-per-mart.md) | 1h | 03 | `cache_repository.py` |
| 06 | [C360 panel P07](phase-06-c360-suggestion-settings-panel.md) | 3h | 02, 04 | new screen module + fragment, `customer_360.html`, `composition.py` |
| 07 | [Integration tests + docs](phase-07-integration-tests-and-docs.md) | 2h | 05, 06 | `crm/src/tests/**`, `crm/docs/ui-spec/**` |

Parallel: 01→02 runs alongside 03→(04 ∥ 05). 06 joins after 02+04. 07 last.

## Success criteria

- Staff can turn off `REORDER_NUDGE` (customer-level) for a party while the SKU-level `REORDER_NUDGE`
  keeps firing — proven by an integration test over `list_all_action_queue()`.
- Suppression can be created with no active `action_id` for that party.
- End date is staff-chosen; panel shows it and who set it; editing a row created by the old
  quick-dismiss works.
- Globally-disabled types (`GIFT_TO_PURCHASE`) render greyed, non-togglable.
- `do_not_contact` behaviour unchanged; `test_worklist_suppression_do_not_contact.py` still green.

## Key references

- Research verified in-line in each phase file (all claims carry `file:line`).
- Registry seed: `transformation/seeds/seed_action_scenario_registry.csv` (13 rows).
- Existing suppression: `crm/migrations/0038_action_dismissal_ttl.up.sql`,
  `crm/src/adapters/outbound/sqlite/action_state_repository.py`,
  `crm/src/adapters/outbound/sqlite/cache_repository.py:179,227`.
