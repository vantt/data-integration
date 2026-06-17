#!/bin/sh
# entrypoint.sh — CRM container startup sequence (Python-only).
# All pre-server steps are best-effort: a failure logs a warning but does NOT
# crash the container so the UI is always reachable (graceful-empty mode).
set -e

echo "[entrypoint] CRM starting — data dir: ${CRM_DATA_DIR}"

# ── Step 1: Apply crm.db schema migrations ────────────────────────────────────
echo "[entrypoint] running migrations …"
if python3 -c "import sys,os; sys.path.insert(0,'/app'); from crm.src.adapters.outbound.sqlite.migrations import apply_migrations; apply_migrations(os.environ.get('CRM_DATA_DIR','/data'))"; then
    echo "[entrypoint] migrations OK"
else
    echo "[entrypoint] WARN: migrations failed" >&2
fi

# ── Step 2: Reverse-ETL (warehouse → cache.db) ────────────────────────────────
# Reads olap.duckdb read-only; writes cache.db.
# Graceful on missing/empty olap.duckdb — logs warning, UI still serves.
echo "[entrypoint] running reverse-ETL …"
if PYTHONPATH=/app python3 -m crm.sync.reverse_etl_warehouse_to_crm; then
    echo "[entrypoint] reverse-ETL OK"
else
    echo "[entrypoint] WARN: reverse-ETL failed — cache.db may be empty (UI will still serve)" >&2
fi

# ── Step 3: Sync warehouse party seeds → crm_party rows ──────────────────────
# Reads cache.db (wh_party_seed); writes crm.db (crm_party + identities).
echo "[entrypoint] running sync_parties …"
if PYTHONPATH=/app python3 -m crm.src.sync_parties; then
    echo "[entrypoint] sync_parties OK"
else
    echo "[entrypoint] WARN: sync_parties failed — crm_party table may be empty" >&2
fi

# ── Step 4: Start CRM server (foreground) ────────────────────────────────────
echo "[entrypoint] starting CRM server on :${CRM_PORT} …"
if [ "${CRM_DEV_RELOAD:-0}" = "1" ]; then
    echo "[entrypoint] DEV mode — uvicorn --reload enabled"
    exec python3 -m uvicorn crm.src.main:app --host 0.0.0.0 --port "${CRM_PORT:-8090}" --reload --reload-dir /app/crm/src
else
    exec python3 -m uvicorn crm.src.main:app --host 0.0.0.0 --port "${CRM_PORT:-8090}"
fi
