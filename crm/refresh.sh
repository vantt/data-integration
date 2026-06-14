#!/bin/sh
# refresh.sh — Re-run reverse-ETL + syncparties without restarting the server.
# Usage (from host): docker compose exec crm /app/refresh.sh
set -e

echo "[refresh] reverse-ETL: warehouse → cache.db …"
python3 -m crm.sync.reverse_etl_warehouse_to_crm

echo "[refresh] syncparties: cache.db → crm.db …"
/app/syncparties

echo "[refresh] done."
