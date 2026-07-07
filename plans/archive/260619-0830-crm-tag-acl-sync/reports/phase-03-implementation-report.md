# Phase 03 — Inbound Sync — Implementation Report

**Plan:** `plans/260619-0830-crm-tag-acl-sync/` · **Phase:** 03 (final, v1 scope) · **Status:** DONE

## Files Modified / Created

Created:
- `crm/src/sync_party_tags.py` — CLI entry (mirrors `sync_parties.py`)
- `crm/src/application/tag_acl_sync_service.py` — `TagAclSyncService.reconcile()`
- `crm/src/tests/test_tag_acl_sync.py` — 7 tests (5 required + idempotency + guard)

Modified:
- `crm/src/adapters/outbound/sqlite/tag_note_repository.py` — `attach_tag` upsert (source-upgrade); added `list_party_tags_by_source`, `bulk_attach_synced`, `bulk_detach_synced`
- `crm/src/domain/ports/tag_repository.py` — protocol additions for the 3 new methods
- `crm/entrypoint.sh` — added Step 4: `sync_party_tags` after `sync_parties`
- `crm/refresh.sh` — added `sync_party_tags` after `sync_parties`

## Deviation from phase doc (verified, not a design change)

Phase doc specified party resolution via `crm_party_external_id` (migration 0009).
Verified empirically this table has **zero writers** in the actual codebase (grep:
only my new code referenced it) — `sync_parties.py` → `PartyService.upsert_from_sapo_identity()`
writes `crm_party_identity` (identity_type='sapo_customer'), not `crm_party_external_id`.
A live end-to-end run against `crm_party_external_id` skipped 100% of rows
(`skipped_no_party=7592`). Switched resolution to `crm_party_identity`
(`source_system='sapo_v2' AND identity_type='sapo_customer'`) — confirmed correct
by the subsequent live run (`skipped_no_party=0`, `inserted=939` matching the
seeded mapping exactly). Documented inline in `tag_acl_sync_service.py` module
docstring + `_load_party_lookup`.

## Tests Status

- `pytest crm/src/tests/test_tag_acl_sync.py -v` → **7/7 passed**
  1. `TestReconcileInsertsNewTag` — WHOLESALE party gets tag, source='sapo_v2_sync', ext_ref='1812239'
  2. `TestReconcileGroupChange` — group change deletes old sync tag, inserts new
  3. `TestReconcileDoesNotOverwriteCrmUserRow` — crm_user row on same pair survives 2 reconcile runs
  4. `TestAttachTagUpgradesSyncOwnedRow` — `attach_tag` upgrades sync→crm_user; next reconcile doesn't delete it
  5. `TestReconcileSkipsUnresolvedRows` — unseeded party + unmapped group (RETAIL) skipped, counted, no exception
  6. `TestReconcileIsIdempotent` — second run with no input change: 0 inserted, 0 deleted
  7. `TestReconcileEmptyFeedGuard` — empty feed + >5 current sync rows aborts delete, 0 removed

- Full suite: `pytest crm/src/tests -q --ignore=test_approach_script_handler.py` → **824 passed, 1 failed**
  (pre-existing, unrelated: `test_approach_script_file_repository.py::test_list_customer_ids_reflects_new_file_without_reinit`,
  a caching-behavior assertion in the approach-script area — flagged in-scope as a known
  pre-existing issue this session, not touched by this phase). A second pre-existing
  failure (`test_approach_script_handler.py` — ImportError, `wire_approach_script_router`
  missing) blocks bare collection of that one file; excluded via `--ignore` per the same
  known-issue note.

## Real End-to-End Verification

`docker compose up -d --build crm` (rebuild required: `entrypoint.sh`/`refresh.sh` are
baked into the image, not bind-mounted — `crm/src/*.py` changes only need `restart`).

Entrypoint log — full sequence, no errors:
```
[entrypoint] running migrations …            → OK
[entrypoint] running reverse-ETL …            → OK (7593 wh_customer_base rows)
[entrypoint] running sync_parties …           → OK (7592 parties upserted)
[entrypoint] running sync_party_tags …        → OK
  tag_acl_sync: inserted=939 deleted=0 skipped_no_party=0 skipped_no_mapping=6653 aborted=False
[entrypoint] starting CRM server on :8090 …
```

`crm.db` verification — counts match the 5 active seeded mappings exactly (939 = 161+662+104+11+1):
```
KH US giao hộ   ext_ref=2421894  n=662
KH Sỉ           ext_ref=1812239  n=161
Selly           ext_ref=2308212  n=104
Ký Gửi          ext_ref=2281219  n=11
VIP             ext_ref=1812240  n=1
Total source='sapo_v2_sync': 939
```

Spot-check WHOLESALE customer: `Huỳnh Thị Tuyết Trinh` → tag "KH Sỉ", `source='sapo_v2_sync'`, `ext_ref='1812239'`.

Idempotency — 2 consecutive `python3 -m crm.src.sync_party_tags` runs, no data change:
```
Run 1: inserted=0 deleted=0 skipped_no_party=0 skipped_no_mapping=6653 aborted=False
Run 2: inserted=0 deleted=0 skipped_no_party=0 skipped_no_mapping=6653 aborted=False
```

## Notes on design choices

- `attach_tag` SQL upgraded to upsert exactly per phase doc: `ON CONFLICT(party_id, tag_id) DO UPDATE SET source='crm_user', tagged_by=excluded.tagged_by`. Verified safe for the Phase-02 health-tag-collect endpoint: every existing caller of `attach_tag`/`TagService.attach_tag` already passes `source="crm_user"` (grep-checked across `screen_modal_tags.py`, `screen_modal_shared.py`, `composition.py`) — the upgrade is a no-op there.
- `bulk_detach_synced` filters `source=?` inside the SQL itself (not just in the Python-built pair list) — satisfies the "safety invariant" requirement so a caller bug can never delete a `crm_user` row.
- Guard threshold (`ABORT_GUARD_MIN_CURRENT = 5`) implemented exactly as phase doc's example; abort only blocks the delete phase and is surfaced via `stats["aborted"]` + CLI non-zero exit — `entrypoint.sh`/`refresh.sh` treat step 4 failure as a WARN (matches existing `sync_parties` graceful-degradation pattern), so a transient warehouse hiccup does not block CRM from serving.
- Reconcile runs in one transaction (single `db.commit()` after both bulk operations) per phase doc's atomicity requirement.

## Unresolved Questions

None — the `crm_party_external_id` vs `crm_party_identity` discrepancy was resolved via direct verification (grep + live run), not left open.
