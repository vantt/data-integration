#!/bin/sh
# entrypoint.sh — CRM container startup sequence.
# All pre-server steps are best-effort: a failure logs a warning but does NOT
# crash the container so the UI is always reachable (graceful-empty mode).
set -e

echo "[entrypoint] CRM starting — data dir: ${CRM_DATA_DIR}"

# ── Step 1: Apply crm.db schema migrations ────────────────────────────────────
# crm-server also self-migrates on startup; running crm-migrate first is a
# belt-and-suspenders guard so syncparties (step 3) can safely write crm.db.
echo "[entrypoint] running migrations …"
if /app/crm-migrate up; then
    echo "[entrypoint] migrations OK"
else
    echo "[entrypoint] WARN: migrations failed (server will retry on startup)" >&2
fi

# ── Step 2: Reverse-ETL (warehouse → cache.db) ────────────────────────────────
# Reads olap.duckdb read-only; writes cache.db.
# Graceful on missing/empty olap.duckdb — logs warning, UI still serves.
echo "[entrypoint] running reverse-ETL …"
if python3 -m crm.sync.reverse_etl_warehouse_to_crm; then
    echo "[entrypoint] reverse-ETL OK"
else
    echo "[entrypoint] WARN: reverse-ETL failed — cache.db may be empty (UI will still serve)" >&2
fi

# ── Step 3: Sync warehouse party seeds → crm_party rows ──────────────────────
# Reads cache.db (wh_party_seed); writes crm.db (crm_party + identities).
echo "[entrypoint] running syncparties …"
if /app/syncparties; then
    echo "[entrypoint] syncparties OK"
else
    echo "[entrypoint] WARN: syncparties failed — crm_party table may be empty" >&2
fi

# ── Step 4: Start CRM server (foreground) ────────────────────────────────────
echo "[entrypoint] starting crm-server on :${CRM_PORT} …"
exec /app/crm-server
