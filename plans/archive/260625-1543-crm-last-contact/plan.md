# Plan: CRM Last Contact Entity + Warehouse Write-Back

**Status:** ✅ ALL DONE (shipped 2026-06-25)

## Context

CS contacts a customer → CRM records outcome → warehouse still shows the same
action next day. Two-part fix:

1. **Phase 1** — Per-customer `crm_last_contact` entity in `crm.db`; worklist
   badge + `hide_contacted` real-time filter at the CRM app layer. *(DONE)*

2. **Phase 2** — Generic CRM-to-warehouse write-back pipeline: Dagster reads
   from `crm.db` (already RO-mounted at `/app/var/crm_data`), writes parquet,
   dbt enriches `mart_customer_action_queue` with contact metadata. *(DONE)*

## Phases

| # | Phase | Status | File |
|---|-------|--------|------|
| 1 | CRM entity, migration, worklist badge + filter | ✅ DONE | [phase-01](phase-01-crm-entity-and-worklist.md) |
| 1b | Rename `crm_activity` → `crm_activity_log` (migration + code) | ✅ DONE | [phase-01b](phase-01b-rename-crm-activity-to-activity-log.md) |
| 2 | Warehouse write-back — 4 tables, Dagster→parquet→dbt | ✅ DONE | [phase-02](phase-02-warehouse-writeback.md) |

## Phase 2 scope

**This batch (implement now):**

| Table | Mode | Value |
|-------|------|-------|
| `crm_last_contact` | snapshot | action queue enrichment |
| `crm_activity_log` | incremental_append | contact outcome funnel |
| `crm_hug_voucher` | snapshot | HUG campaign attribution / ROI |
| `crm_campaign_target` | snapshot | campaign conversion rate + revenue attribution |

**Deferred (no immediate analytics need):**

| Table | Mode | When |
|-------|------|------|
| `crm_task` | snapshot | When CS productivity dashboard needed |
| `crm_action_state` | snapshot | When dismiss/snooze feedback loop needed |

## Key Files (Phase 1, already shipped)

```
crm/migrations/0027_last_contact.up.sql
crm/src/domain/entities/last_contact.py
crm/src/adapters/outbound/sqlite/last_contact_repository.py
crm/src/application/activity_service.py           (upsert on activity save)
crm/src/adapters/inbound/web/screen_worklist.py   (lc_map fetch + hide_contacted)
crm/src/adapters/inbound/web/templates/fragments/_wl_row.html  (badge UI)
crm/src/application/worklist_filters.py           (hide_contacted filter + product)
```

## Dependencies

- Phase 2 depends on Phase 1 (crm_last_contact table must exist)
- Phase 2 output is prerequisite for any warehouse-level action suppression
