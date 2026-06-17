#!/bin/sh
# refresh.sh — Re-run reverse-ETL + sync_parties without restarting the server.
# Usage (from host): docker compose exec crm /app/refresh.sh
set -e

echo "[refresh] reverse-ETL: warehouse → cache.db …"
PYTHONPATH=/app python3 -m crm.sync.reverse_etl_warehouse_to_crm

echo "[refresh] sync_parties: cache.db → crm.db …"
PYTHONPATH=/app python3 -m crm.src.sync_parties

echo "[refresh] done."
