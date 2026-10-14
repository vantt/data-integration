#!/usr/bin/env bash
# Build the shadow base lake, then the offline tools (prepare-deps.sh, kept outside the
# shadow root) used by run-shadow.sh.
#
# Usage: scripts/shadow/prepare-shadow.sh <backup_new> <backup_prev>
#   backup_new / backup_prev: directory names under app_data/backups/ (e.g. 20261013-010341)
#
# lake-base = DuckDB warehouse, exports, serving and health DB from <backup_prev>
#           + raw landing folders (*_raw, crm_export) from <backup_new>,
# so the first shadow build processes exactly one day of new loads and the incremental
# branches of the 17 incremental models really run. Backups are taken by
# maintain_backup_platform_job under duckdb_lock; a live prod lake is never copied.
set -euo pipefail

PROD_ROOT=/home/vantt/app/fg-dataware-house
SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

[ "$#" -eq 2 ] || { echo "usage: $0 <backup_new> <backup_prev>" >&2; exit 2; }
NEW="$PROD_ROOT/app_data/backups/$1/app_data/data_lake"
PREV="$PROD_ROOT/app_data/backups/$2/app_data/data_lake"
[ -d "$NEW" ] && [ -d "$PREV" ] || { echo "backup not found: $NEW or $PREV" >&2; exit 1; }

python3 "$SCRIPT_DIR/../checks/guard_not_prod.py" "$SHADOW_ROOT"
umask 077
mkdir -p "$SHADOW_ROOT" && chmod 700 "$SHADOW_ROOT"

BASE="$SHADOW_ROOT/lake-base"
rm -rf "$BASE"; mkdir -p "$BASE"
echo "[prepare] warehouse/export/serving/monitoring from $2"
for item in sapo_warehouse.duckdb export serving monitoring; do
  [ -e "$PREV/$item" ] && cp -a --reflink=auto "$PREV/$item" "$BASE/"
done
echo "[prepare] raw landing folders from $1"
for d in "$NEW"/*_raw "$NEW/crm_export"; do
  [ -d "$d" ] && cp -a --reflink=auto "$d" "$BASE/"
done
printf 'base_prev=%s\nraw_new=%s\nprepared_at=%s\n' "$2" "$1" "$(date -Is)" > "$BASE/SHADOW_SOURCE"

"$SCRIPT_DIR/prepare-deps.sh"

chmod -R go-rwx "$SHADOW_ROOT"
du -sh "$BASE"
