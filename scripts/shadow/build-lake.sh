#!/usr/bin/env bash
# Build one shadow lake the way production does: container-start directory prep, then the
# sapo_dbt_assets sequence (`dbt parse` + `dbt build`), then refresh_rolling.py.
#
# Usage: scripts/shadow/build-lake.sh <code_dir> <lake_name> [extra dbt build args...]
#   e.g. scripts/shadow/build-lake.sh /home/vantt/app/fg-dw-baseline lake-A
#        scripts/shadow/build-lake.sh /home/vantt/app/fg-dw-pack lake-B --full-refresh --select <models>+
#
# Run clone-lake.sh first. dbt artifacts (manifest.json, run_results.json) and the build
# start time are copied into <lake>/_shadow_meta/ for golden_snapshot.py and dbt_inventory.py.
set -uo pipefail

SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "$#" -ge 2 ] || { echo "usage: $0 <code_dir> <lake_name> [dbt args...]" >&2; exit 2; }
CODE_DIR="$(realpath "$1")"; LAKE="$SHADOW_ROOT/$2"; shift 2
[ -d "$LAKE" ] || { echo "missing $LAKE (run clone-lake.sh)" >&2; exit 1; }

META="$LAKE/_shadow_meta"; mkdir -p "$META"
BUILD_START="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "$BUILD_START" > "$META/build_start"
echo "$CODE_DIR @ $(git -C "$CODE_DIR" rev-parse HEAD)" > "$META/code_ref"

"$SCRIPT_DIR/run-shadow.sh" "$CODE_DIR" "$LAKE" sh -c '
  set -u
  python scripts/ensure_dbt_directories.py || exit 10
  cd transformation
  dbt parse --profiles-dir . >/dev/null || exit 11
  dbt build --profiles-dir . "$@"; rc=$?
  cd .. && python scripts/provisioning/refresh_rolling.py >/dev/null 2>&1 || echo "refresh_rolling failed" >&2
  exit $rc' sh "$@" 2>&1 | tee "$META/build.log" | tail -25
RC=${PIPESTATUS[0]}

cp "$CODE_DIR/transformation/target/manifest.json" "$CODE_DIR/transformation/target/run_results.json" "$META/" 2>/dev/null
echo "$RC" > "$META/build_rc"
echo "build-lake: $LAKE rc=$RC (start $BUILD_START)"
exit "$RC"
