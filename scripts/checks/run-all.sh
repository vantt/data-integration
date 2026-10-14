#!/usr/bin/env bash
# Pre-commit checks in one command: dbt parse, module boundaries, Dagster definitions, pytest.
#
# Usage: scripts/checks/run-all.sh [code_dir]
#   code_dir  the worktree to check (default: the checkout containing this script). The prod
#             checkout is refused (run-shadow.sh guard): commit from a worktree.
#
# dbt, Dagster and pytest run in the shadow container (scripts/shadow/run-shadow.sh: prod
# image, --network none, no secrets) on an EMPTY scratch lake created under $SHADOW_ROOT and
# deleted on exit; no lake with data is read, so it works after the shadow data is deleted.
# Only the offline tools are required: $SHADOW_DEPS (default ~/.cache/fg-dw-tools/deps;
# dbt_packages, DuckDB extensions, pinned pytest; scripts/shadow/prepare-deps.sh).
# check_boundaries.py runs with host python3 because crm/ and detailView/ are not mounted in
# the container.
#
# Steps (all run, exit 1 if any failed):
#   1. dbt parse            writes <code_dir>/transformation/target/manifest.json
#   2. check_boundaries.py  on that manifest (scripts/checks/README.md)
#   3. dagster definitions validate -f orchestration/definitions.py
#   4. pytest ingestion/tests orchestration scripts/tests (one re-run after a failure, reported
#      as FLAKY when it passes: see scripts/shadow/README.md for the known SQLite timing test)
#
# This does not prove data equality; refactors that move models or SQL still need
# scripts/shadow/gate.sh M|S before deploy.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODE_DIR="$(realpath "${1:-$SCRIPT_DIR/../..}")"
SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
RUN="$SCRIPT_DIR/../shadow/run-shadow.sh"
MANIFEST="$CODE_DIR/transformation/target/manifest.json"

[ -d "$CODE_DIR/transformation" ] && [ -d "$CODE_DIR/orchestration" ] || {
  echo "run-all: $CODE_DIR is not a checkout of this repo" >&2; exit 2; }
DEPS="${SHADOW_DEPS:-${XDG_CACHE_HOME:-$HOME/.cache}/fg-dw-tools/deps}"
[ -d "$DEPS/dbt_packages" ] && [ -d "$DEPS/home/pylib" ] || {
  echo "run-all: missing $DEPS (run scripts/shadow/prepare-deps.sh, or set SHADOW_DEPS)" >&2; exit 2; }

# The scratch lake must live under $SHADOW_ROOT (run-shadow.sh), which may not exist between
# refactor waves; create it private.
mkdir -p "$SHADOW_ROOT" && chmod 700 "$SHADOW_ROOT"

LAKE="$(mktemp -d "$SHADOW_ROOT/checks-XXXXXX")" || exit 2
chmod 700 "$LAKE"
trap 'rm -rf "$LAKE"' EXIT

FAIL=0
step() { echo; echo "=== $1"; }
check() { if [ "$1" -ne 0 ]; then echo "FAILED: $2"; FAIL=1; else echo "ok: $2"; fi; }
in_shadow() { SHADOW_ROOT="$SHADOW_ROOT" "$RUN" "$CODE_DIR" "$LAKE" "$@"; }

step "1. dbt parse"
in_shadow sh -c 'cd transformation && dbt parse --profiles-dir . --no-partial-parse' 2>&1 | tail -3
check "${PIPESTATUS[0]}" "dbt parse"

step "2. module boundaries (host python3)"
if [ -f "$MANIFEST" ]; then
  python3 "$CODE_DIR/scripts/checks/check_boundaries.py" --manifest "$MANIFEST" | tail -8
  check "${PIPESTATUS[0]}" "module boundaries"
else
  check 1 "module boundaries (no manifest: dbt parse failed)"
fi

step "3. dagster definitions validate"
in_shadow dagster definitions validate -f orchestration/definitions.py 2>&1 | grep -E "Validation|validation|Error|error" | tail -5
check "${PIPESTATUS[0]}" "dagster definitions"

step "4. pytest"
run_pytest() {
  in_shadow sh -c 'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/shadow-home/pylib \
    exec python -m pytest -p no:cacheprovider -q ingestion/tests orchestration scripts/tests' 2>&1 | tail -3
  return "${PIPESTATUS[0]}"
}
run_pytest; RC=$?
if [ "$RC" -ne 0 ]; then
  echo "pytest failed; re-running once to separate flaky timing tests from real failures"
  run_pytest; RC=$?
  [ "$RC" -eq 0 ] && echo "FLAKY: first pytest run failed, re-run passed"
fi
check "$RC" "pytest"

echo
if [ "$FAIL" -eq 0 ]; then echo "RUN-ALL: PASS"; else echo "RUN-ALL: FAIL"; fi
exit "$FAIL"
