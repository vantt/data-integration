# Phase 01 Implementation Report — CRM Export customer_id Resolution

**Plan:** `plans/260706-1738-crm-tag-signal-action-queue-consumer/`
**Phase:** `phase-01-crm-export-customer-id-resolution.md`
**Date:** 2026-07-06
**Status:** DONE (with one out-of-scope environment concern — see below)

## Files Modified

1. `orchestration/assets/crm_writeback_assets.py` — 4 export queries in `CRM_WRITEBACK_TABLES` (`crm_note`, `crm_party_tag`, `crm_party_insight`, `crm_customer_profile_custom`) now `LEFT JOIN crm_party_identity pi ON pi.party_id = X.party_id AND pi.identity_type = 'sapo_customer'` + `pi.identity_value AS customer_id`. `crm_party_tag` export also adds `'crm_user' AS source` (literal fallback, `260619-0830` not landed yet) with a `TODO(260619 phase-01)` comment.
2. `transformation/models/staging/stg_crm__party_tag.sql`, `stg_crm__note.sql`, `stg_crm__party_insight.sql`, `stg_crm__customer_profile_custom.sql` — added `customer_id::INTEGER AS customer_id` pass-through after `party_id`. `stg_crm__party_tag.sql` also adds `pt.source AS source` with matching `TODO(260619 phase-01)` comment.
3. `scripts/ensure_crm_export_placeholder.py` — **not in the original file list, added because required.** This safety-placeholder generator (own header comment: "keep in sync with export_query columns... a column added there but not here reproduces the exact bug this script exists to prevent") was missing `customer_id`/`source` for the 4 tables. Without this fix, `stg_crm__party_insight` fails to compile whenever the underlying CRM table has zero rows (its only source file is this placeholder) — hit this exact failure during verification (see below).

`schema.yml` — no change needed; it already has no `not_null` test on `customer_id` (nothing to remove, per requirement).

## Deviation from phase doc

- `crm_party_tag` export/staging use literal `'crm_user' AS source` (not `pt.source`) — confirmed via `crm/migrations/*.up.sql` grep that no migration adds a `source` column to `crm_party_tag` yet (260619-0830 phase-01 not landed). Matches the phase doc's documented fallback exactly.
- Extra fix not in the phase doc's file list: `scripts/ensure_crm_export_placeholder.py` (see above) — required for `stg_crm__party_insight` to compile since that table has 0 real rows today.

## Data Operations

1. `docker compose restart data_platform` — restarted before running exports.
2. `crm_note` cursor: `/app/var/data_lake/crm_export/crm_note/crm_note_cursor.json` — confirmed volume small (34 rows, 1 batch) before deleting. Deleted.
3. `crm_party_insight` cursor: none existed (table has 0 rows in `crm.db` — feature unused so far, confirmed via direct query). Nothing to delete.
4. Triggered the 4 export assets. **Deviation:** `dagster asset materialize` CLI is broken in this container (pre-existing, unrelated — see Concern below), so I invoked the underlying `_snapshot_export`/`_incremental_export` functions directly via a one-off Python script (`orchestration.assets.crm_writeback_assets`), which is exactly what the asset wrappers call — same code path, same result. Output:
   ```
   crm_note (incremental_append): 34 new rows
   crm_party_tag (snapshot): 13 rows -> /app/var/data_lake/crm_export/crm_party_tag.parquet
   crm_party_insight (incremental_append): 0 new rows
   crm_customer_profile_custom (snapshot): 2748 rows -> /app/var/data_lake/crm_export/crm_customer_profile_custom.parquet
   ```
5. **Found + fixed a duplicate-row issue:** resetting `crm_note`'s cursor and re-exporting from epoch created a *new* batch (`date=20260706/batch_153306.parquet`, 34 rows, all with `customer_id`) alongside the *old* pre-fix batch (`date=20260705/batch_200155.parquet`, same 34 rows, no `customer_id`) — this is incremental_append, additive by design, so both existed simultaneously and produced duplicate `note_id`s (caught by `unique_stg_crm__note_note_id` test — 34 failures). Verified the new batch was a strict superset (same 34 rows, `customer_id` populated) before deleting the old batch directory `date=20260705/`. Re-ran `dbt build` clean afterward. This is a one-time cleanup implied but not spelled out by the phase doc's "delete cursor" instruction — flagging for anyone repeating this pattern for other incremental tables in the future.
6. `crm_party_tag` (snapshot) and `crm_customer_profile_custom` (snapshot) — re-run overwrote the single parquet file automatically, as expected, no manual step needed.

## dbt build — verification step 4

```
docker compose exec data_platform bash -lc "cd /app/transformation && dbt build --select stg_crm__party_tag stg_crm__note stg_crm__party_insight stg_crm__customer_profile_custom"
```
Result: `Done. PASS=14 WARN=0 ERROR=0 SKIP=0 NO-OP=0 TOTAL=14` — all 4 models + 10 existing schema tests green.

## Sanity query — verification step 5

Read-only DuckDB query against `main_staging.<model>`:

| Model | total rows | rows with customer_id | NULL % |
|---|---|---|---|
| `stg_crm__party_tag` | 13 | 13 | 0% |
| `stg_crm__note` | 34 | 34 | 0% |
| `stg_crm__party_insight` | 0 | 0 | n/a (no data yet) |
| `stg_crm__customer_profile_custom` | 2748 | 2748 | 0% |

**Note on 0% NULL (deviation from phase doc expectation):** the phase doc's risk section anticipated some NULL rate ("party chưa link Sapo"). Checked directly: `crm_party_identity` currently has 7590 distinct `party_id`, and **all 7590** are linked to `identity_type='sapo_customer'` — this CRM instance has no party today that exists independently of a Sapo customer record (no CRM-native-only leads yet). So 0% NULL is correct for the current data, not a resolution bug — confirmed by checking the join key population directly rather than assuming. Will show non-zero NULL once CRM gains parties without a Sapo link (e.g. Lark-only signups).

## Cast-error check — verification step 6

No cast errors during any of the above (`customer_id::INTEGER` succeeded on all 2795 populated rows across the 3 non-empty tables) — `identity_value` values are numeric strings as expected, no data-quality investigation needed.

## `_qualify_for_attach()` check

Verified empirically (not just by inspection): the 4 direct export calls above executed the qualifier against the new alias-bearing queries (`FROM crm_note n`, `FROM crm_party_tag pt`, `FROM crm_party_insight i`, `FROM crm_customer_profile cp`) without error, and the joins resolved `customer_id` correctly. No collision risk: none of the table names in `_CRM_TABLE_NAMES` is a substring of another in a way that would double-qualify (e.g. `crm_tag` is not a contiguous substring of `crm_party_tag`).

## Concern — unrelated environment issue found (out of Phase 01 scope)

`data_platform`'s own Dagster process (`dagster dev`, PID 1 of the container) is in a continuous crash-loop (~12s cycle, `RestartCount` climbing steadily), unrelated to this phase's changes:

```
google.protobuf.runtime_version.VersionError: Detected incompatible Protobuf Gencode/Runtime
versions when loading grpc_health/v1/health.proto: gencode 7.35.0 runtime 6.33.6.
```

This also breaks `dagster asset materialize`/`dagster job execute` CLI entirely (same import chain). Root-caused this to the *already-applied* (uncommitted) `Dockerfile.dataplatform` diff for the codex-CLI work (`plans/260706-0837-approach-script-codex-autogen/`, not this plan) — confirmed the running image (built 2026-07-06 13:37) already has `node`/`npm`/`codex` baked in, and that diff also *removed* the `webhook_consumer/cloudflared1_consumer/requirements.txt` install, likely changing the pip dependency resolution for `protobuf`/`grpcio-health-checking` used by `dagster`/`dagster-dbt`. I did not touch `Dockerfile.dataplatform` or any requirements file (out of my file ownership for this phase) — worked around it for verification by using a one-off `docker compose run --rm` container plus direct Python invocation of the export functions and read-only DuckDB queries, bypassing the broken CLI/webserver path entirely. Left `data_platform` back in its normal (crash-looping) `docker compose up -d` state, matching how I found the rest of the stack — did not attempt a fix since it's owned by different, currently in-progress work.

**This needs separate attention** — right now no Dagster-scheduled or UI-triggered run of *any* asset can succeed in this container (not specific to CRM), until whoever owns the codex-CLI Dockerfile change re-pins `protobuf`/`grpcio-health-checking` or rebuilds cleanly.

## Constraints respected

- Did not touch `mart_customer_action_queue.sql`, `int_crm_party_tag_flags.sql`, `badge_catalog.py` (Phase 02 scope).
- Did not commit.
- `schema.yml` untouched (no `not_null` test existed on `customer_id`, nothing to add/remove).

Status: DONE_WITH_CONCERNS
Summary: All 4 export queries + staging models done exactly per phase doc (with the documented `source` literal fallback), plus a necessary fix to `ensure_crm_export_placeholder.py` (not in original file list but required for `stg_crm__party_insight` to compile with 0 rows) and cleanup of a duplicate `crm_note` batch created by the cursor-reset step. dbt build green, sanity counts confirmed correct (0% NULL is genuine — all current CRM parties are already Sapo-linked, verified directly, not assumed).
Concerns/Blockers: `data_platform`'s Dagster process is crash-looping from an unrelated, already-applied Dockerfile change (codex CLI plan) — breaks all Dagster CLI/scheduled runs repo-wide, not just CRM. Flagging for the owner of `plans/260706-0837-approach-script-codex-autogen/` to fix (protobuf/grpc_health version pin). Did not fix myself (out of file ownership + out of this phase's scope).
