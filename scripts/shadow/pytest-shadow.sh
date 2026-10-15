#!/usr/bin/env bash
# Run pytest inside the shadow container. pytest lives in $SHADOW_DEPS/home/pylib (see
# prepare-deps.sh) and is put on PYTHONPATH only for this command.
#
# Usage: scripts/shadow/pytest-shadow.sh <code_dir> <lake_name> [pytest args...]
#   e.g. scripts/shadow/pytest-shadow.sh /home/vantt/app/fg-dw-pack lake-B ingestion/tests orchestration scripts/tests -q
set -euo pipefail
SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "$#" -ge 2 ] || { echo "usage: $0 <code_dir> <lake_name> [pytest args...]" >&2; exit 2; }
CODE_DIR="$1"; LAKE="$SHADOW_ROOT/$2"; shift 2
exec "$SCRIPT_DIR/run-shadow.sh" "$CODE_DIR" "$LAKE" \
  sh -c 'PYTHONPATH=/app:/shadow-home/pylib exec python -m pytest -p no:cacheprovider "$@"' sh "$@"
