#!/usr/bin/env bash
# Build the shadow base lake and the offline dependencies used by run-shadow.sh.
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

DEPS="$SHADOW_ROOT/deps"
rm -rf "$DEPS"; mkdir -p "$DEPS/home"
echo "[prepare] dbt_packages from prod checkout (read-only copy)"
cp -a "$PROD_ROOT/transformation/dbt_packages" "$DEPS/dbt_packages"
echo "[prepare] DuckDB extensions from prod container (read-only copy)"
docker cp data_platform:/root/.duckdb "$DEPS/home/.duckdb"

echo "[prepare] pinned pytest for shadow-only test runs (never installed into the prod image)"
# Download runs in a throwaway container with network but no code, data or secrets mounted.
# Install uses --no-deps so packages already in the image (packaging, typing_extensions,
# tomli, exceptiongroup) are not shadowed; only pytest, pluggy, iniconfig are added.
IMAGE="${SHADOW_IMAGE:-fg-dataware-house-data_platform:latest}"
mkdir -p "$DEPS/wheels"
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$DEPS/wheels:/w" "$IMAGE" \
  pip download "pytest==8.3.3" -d /w -q --disable-pip-version-check
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$DEPS/wheels:/w" \
  -v "$DEPS/home:/shadow-home" "$IMAGE" pip install --no-index --no-deps --find-links /w \
  --target /shadow-home/pylib -q --disable-pip-version-check pytest==8.3.3 pluggy==1.6.0 iniconfig==2.3.1

chmod -R go-rwx "$SHADOW_ROOT"
du -sh "$BASE" "$DEPS"
