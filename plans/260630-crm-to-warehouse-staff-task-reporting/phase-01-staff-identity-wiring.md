# Phase 1: Staff Identity Wiring (CRM side)

**Status:** DONE

## What was done

- `crm_app_user.staff_id` already existed (migration 0001) but was never wired
- Migration `0030_app_user_staff_id_unique` adds partial UNIQUE index (WHERE staff_id IS NOT NULL)
- `AppUser` entity: added `staff_id: Optional[int]`
- `SQLiteAppUserRepository`: SELECT, INSERT, UPDATE all include `staff_id`
- `StaffIdResolver` (new): `crm/src/adapters/outbound/duckdb/staff_id_resolver.py`
  - Queries `main_marts.dim_staff WHERE lower(trim(email)) = ?`
  - Returns `Optional[int]`; silent on failure (olap.duckdb may be absent)
- `AppUserService`: takes `staff_resolver=None`; calls `_try_sync_staff_id` on new user + backfills on login when `staff_id IS NULL`
- `composition.py`: wires `StaffIdResolver(olap_path())` into `AppUserService`

## Files modified

- `crm/migrations/0030_app_user_staff_id_unique.up.sql` (new)
- `crm/migrations/0030_app_user_staff_id_unique.down.sql` (new)
- `crm/src/domain/entities/app_user.py`
- `crm/src/adapters/outbound/sqlite/app_user_repository.py`
- `crm/src/adapters/outbound/duckdb/staff_id_resolver.py` (new)
- `crm/src/application/app_user_service.py`
- `crm/src/composition.py`
