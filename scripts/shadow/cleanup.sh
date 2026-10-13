#!/usr/bin/env bash
# Remove shadow lakes. Shadow lakes contain customer PII copied from backups, so they are
# deleted as soon as they are no longer needed.
#
# Usage:
#   scripts/shadow/cleanup.sh <lake-name> [...]   delete specific lakes (e.g. lake-B after a compare)
#   scripts/shadow/cleanup.sh --all               delete the whole shadow root (when the plan closes)
set -euo pipefail

SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/../checks/guard_not_prod.py" "$SHADOW_ROOT"
[ "$#" -ge 1 ] || { echo "usage: $0 <lake-name>... | --all" >&2; exit 2; }

if [ "$1" = "--all" ]; then
  rm -rf "$SHADOW_ROOT"
  echo "removed $SHADOW_ROOT"
  exit 0
fi
for name in "$@"; do
  case "$name" in */*|.|..|"") echo "invalid lake name: $name" >&2; exit 1 ;; esac
  rm -rf "${SHADOW_ROOT:?}/$name"
  echo "removed $SHADOW_ROOT/$name"
done
