#!/bin/sh
# entrypoint.sh — CRM container startup sequence (Python-only).
# Schema migrations (Step 1) are HARD-FAIL: a partial schema is unsafe to serve.
# Data steps (Steps 2-3) are graceful-empty: missing warehouse → UI still serves.
set -e

echo "[entrypoint] CRM starting — data dir: ${CRM_DATA_DIR}"

# ── Step 1: Apply crm.db schema migrations ────────────────────────────────────
# HARD-FAIL: a migration failure leaves crm.db in an unknown state; serving on a
# half-migrated DB causes silent data corruption or wrong query results.
# Let the failure propagate (set -e will exit non-zero) — orchestrator will restart
# the container and ops will see the error in container logs.
echo "[entrypoint] running migrations …"
python3 -c "import sys,os; sys.path.insert(0,'/app'); from crm.src.adapters.outbound.sqlite.migrations import apply_migrations; apply_migrations(os.environ.get('CRM_DATA_DIR','/data'))"
echo "[entrypoint] migrations OK"

# CRM_VERIFY_MODE=1 → restore-verify drill: serve the RESTORED data exactly as-is.
# Skip Steps 2-3 because they mutate the DBs from the warehouse (reverse-ETL rewrites
# cache.db; sync_parties writes crm.db) — which would corrupt the integrity comparison
# against the backup manifest. Migrations (Step 1) still run (validates the schema head).
if [ "${CRM_VERIFY_MODE:-0}" = "1" ]; then
    echo "[entrypoint] CRM_VERIFY_MODE=1 — skipping reverse-ETL + sync_parties (serving restored data as-is)"
else
    # ── Step 2: Reverse-ETL (warehouse → cache.db) ────────────────────────────
    # Reads olap.duckdb read-only; writes cache.db. Graceful on missing/empty.
    echo "[entrypoint] running reverse-ETL …"
    if PYTHONPATH=/app python3 -m crm.sync.reverse_etl_warehouse_to_crm; then
        echo "[entrypoint] reverse-ETL OK"
    else
        echo "[entrypoint] WARN: reverse-ETL failed — cache.db may be empty (UI will still serve)" >&2
    fi

    # ── Step 3: Sync warehouse party seeds → crm_party rows ──────────────────
    # Reads cache.db (wh_party_seed); writes crm.db (crm_party + identities).
    echo "[entrypoint] running sync_parties …"
    if PYTHONPATH=/app python3 -m crm.src.sync_parties; then
        echo "[entrypoint] sync_parties OK"
    else
        echo "[entrypoint] WARN: sync_parties failed — crm_party table may be empty" >&2
    fi

    # ── Step 4: Mirror-reconcile crm_party_tag from wh_customer_base.customer_group_id ──
    # Must run AFTER sync_parties (needs crm_party_external_id seeded to resolve party_id).
    # Reads cache.db; writes crm.db (crm_party_tag rows with source='sapo_v2_sync').
    echo "[entrypoint] running sync_party_tags …"
    if PYTHONPATH=/app python3 -m crm.src.sync_party_tags; then
        echo "[entrypoint] sync_party_tags OK"
    else
        echo "[entrypoint] WARN: sync_party_tags failed — synced tags may be stale" >&2
    fi

fi

# ── Step 4: Start CRM server (foreground) ────────────────────────────────────
echo "[entrypoint] starting CRM server on :${CRM_PORT} …"
if [ "${CRM_DEV_RELOAD:-0}" = "1" ]; then
    echo "[entrypoint] DEV mode — uvicorn --reload enabled"
    exec python3 -m uvicorn crm.src.main:app --host 0.0.0.0 --port "${CRM_PORT:-8090}" --reload --reload-dir /app/crm/src
else
    exec python3 -m uvicorn crm.src.main:app --host 0.0.0.0 --port "${CRM_PORT:-8090}"
fi
