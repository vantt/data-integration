#!/usr/bin/env bash
# Create a working shadow lake from lake-base and clear rolling parquet files so a build
# must regenerate every rolling model (stale inherited files would make a golden compare
# pass for models that were never rebuilt).
#
# Usage: scripts/shadow/clone-lake.sh <name> [--empty-rolling]
#   <name>            lake-A, lake-A2, lake-B, ... (created under $SHADOW_ROOT)
#   --empty-rolling   also delete the rolling/<model>/ directories themselves, to prove the
#                     build recreates them (the "empty lake" check)
set -euo pipefail

SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "$#" -ge 1 ] || { echo "usage: $0 <name> [--empty-rolling]" >&2; exit 2; }
DST="$SHADOW_ROOT/$1"
python3 "$SCRIPT_DIR/../checks/guard_not_prod.py" "$DST"
[ -d "$SHADOW_ROOT/lake-base" ] || { echo "missing lake-base; run prepare-shadow.sh" >&2; exit 1; }

umask 077
rm -rf "$DST"
cp -a --reflink=auto "$SHADOW_ROOT/lake-base" "$DST"
ROLL="$DST/export/marts/rolling"
if [ "${2:-}" = "--empty-rolling" ]; then
  rm -rf "$ROLL"; mkdir -p "$ROLL"
else
  find "$ROLL" -type f -name '*.parquet' -delete
fi
echo "$DST"
