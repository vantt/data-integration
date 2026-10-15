#!/usr/bin/env bash
# One-command refactor gate. Compares a branch worktree against the baseline (lake-A,
# built from the untouched `main` worktree) on a fresh shadow lake.
#
# Usage: scripts/shadow/gate.sh <M|S> [--allow-new] [--allow-code-change]
#   M  move-only phases: golden + dbt inventory + compiled SQL + module boundaries + taxonomy inventory (warn only) + dagster inventory
#      + dagster-run dbt subset + pytest + empty-lake build + bare-core profile build (every pack off)
#   S  SQL-changing phases: M + a second golden pass after --full-refresh of every
#      incremental model and everything downstream (the incremental branch is exercised
#      only when rows are reprocessed)
#   --allow-new          accept added nodes/assets/checks and grown job selections (reported as INFO)
#   --allow-code-change  accept SQL checksum changes in the dbt inventory (data equality is
#                        still enforced by the golden snapshot)
#
# Env: BRANCH_DIR (default /home/vantt/app/fg-dw-modular), BASELINE_DIR (default
# /home/vantt/app/fg-dw-baseline). Exit code 0 only when every step passes.
set -uo pipefail

SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRANCH_DIR="${BRANCH_DIR:-/home/vantt/app/fg-dw-modular}"
BASELINE_DIR="${BASELINE_DIR:-/home/vantt/app/fg-dw-baseline}"
M=/app/var/data_lake
[ "$#" -ge 1 ] || { echo "usage: $0 <M|S> [--allow-new] [--allow-code-change]" >&2; exit 2; }
LEVEL="$1"; shift
INV_FLAGS=(); DAG_FLAGS=()
for a in "$@"; do
  case "$a" in
    --allow-new) INV_FLAGS+=(--allow-new); DAG_FLAGS+=(--allow-new) ;;
    --allow-code-change) INV_FLAGS+=(--allow-code-change) ;;
    *) echo "unknown flag $a" >&2; exit 2 ;;
  esac
done

RUN="$SCRIPT_DIR/run-shadow.sh"
MODELS=scripts/checks/public_models.yaml
FAIL=0
step() { echo; echo "=== $1"; }
check() { if [ "$1" -ne 0 ]; then echo "FAILED: $2"; FAIL=1; else echo "ok: $2"; fi; }

golden_pair() {  # <baseline lake> <branch lake>
  "$RUN" "$BRANCH_DIR" "$SHADOW_ROOT" sh -c "
    python scripts/checks/golden_snapshot.py capture --lake $M/$2 --models $MODELS --out $M/$2/_shadow_meta/golden.json | tail -3 && \
    python scripts/checks/golden_snapshot.py compare $M/$1/_shadow_meta/golden.json $M/$2/_shadow_meta/golden.json"
}

[ -f "$SHADOW_ROOT/lake-A/_shadow_meta/golden.json" ] || { echo "missing baseline lake-A (see scripts/shadow/README.md)" >&2; exit 1; }

# Models compute date-relative values (recency_days, snapshot_date, action queues), so the
# baseline and the branch must be built on the same calendar day (ICT). A baseline from an
# earlier day is rebuilt here, together with the cached full-refresh baseline.
TODAY="$(TZ=Asia/Ho_Chi_Minh date +%F)"
BASE_DAY="$(TZ=Asia/Ho_Chi_Minh date -d "$(cat "$SHADOW_ROOT/lake-A/_shadow_meta/build_start")" +%F)"
if [ "$BASE_DAY" != "$TODAY" ]; then
  step "0. baseline built on $BASE_DAY, today is $TODAY: rebuilding lake-A from $BASELINE_DIR"
  "$SCRIPT_DIR/clone-lake.sh" lake-A >/dev/null
  "$SCRIPT_DIR/build-lake.sh" "$BASELINE_DIR" lake-A | tail -1
  "$RUN" "$BRANCH_DIR" "$SHADOW_ROOT" python scripts/checks/golden_snapshot.py capture --lake $M/lake-A --models $MODELS --out $M/lake-A/_shadow_meta/golden.json | tail -1
  "$SCRIPT_DIR/cleanup.sh" lake-AF >/dev/null 2>&1 || true
  # inventories describe the baseline code, so export them from the baseline worktree
  "$RUN" "$BASELINE_DIR" "$SHADOW_ROOT" sh -c "
    python scripts/checks/dbt_inventory.py export --manifest $M/lake-A/_shadow_meta/manifest.json --out $M/inventory/dbt-main.json && \
    python scripts/checks/dagster_inventory.py export --manifest $M/lake-A/_shadow_meta/manifest.json --out $M/inventory/dagster-main.json 2>/dev/null" | tail -2
fi
echo "baseline: $(cat "$SHADOW_ROOT/lake-A/_shadow_meta/code_ref")"

step "1. build branch on fresh lake-B"
"$SCRIPT_DIR/clone-lake.sh" lake-B >/dev/null
"$SCRIPT_DIR/build-lake.sh" "$BRANCH_DIR" lake-B | tail -2; check "${PIPESTATUS[0]}" "dbt build (branch)"

step "2. golden snapshot lake-A vs lake-B"
golden_pair lake-A lake-B; check $? "golden"

step "3. dbt inventory"
"$RUN" "$BRANCH_DIR" "$SHADOW_ROOT" sh -c "
  python scripts/checks/dbt_inventory.py export --manifest $M/lake-B/_shadow_meta/manifest.json --out $M/inventory/dbt-branch.json >/dev/null && \
  python scripts/checks/dbt_inventory.py diff $M/inventory/dbt-main.json $M/inventory/dbt-branch.json ${INV_FLAGS[*]:-}"
check $? "dbt inventory"
CODE_FLAG=""; case " ${INV_FLAGS[*]:-} " in *--allow-code-change*) CODE_FLAG=--allow-code-change ;; esac
"$RUN" "$BRANCH_DIR" "$SHADOW_ROOT" python scripts/checks/dbt_inventory.py compiled-diff \
  $M/lake-A/_shadow_meta/manifest.json $M/lake-B/_shadow_meta/manifest.json $CODE_FLAG | tail -5
check "${PIPESTATUS[0]}" "compiled SQL"

step "3b. module boundaries (host python: needs crm/ and detailView/)"
python3 "$BRANCH_DIR/scripts/checks/check_boundaries.py" --manifest "$SHADOW_ROOT/lake-B/_shadow_meta/manifest.json" | tail -5
check "${PIPESTATUS[0]}" "module boundaries"

step "3c. taxonomy inventory (warn only: a changed or new classification block is printed, never fails the gate)"
python3 "$BRANCH_DIR/scripts/checks/check_taxonomy_inventory.py" --repo "$BRANCH_DIR" | tail -20

step "4. dagster inventory (assets, checks, job selections, schedules, sensors, SLA)"
"$RUN" "$BRANCH_DIR" "$SHADOW_ROOT" sh -c "
  python scripts/checks/dagster_inventory.py export --manifest $M/lake-B/_shadow_meta/manifest.json --out $M/inventory/dagster-branch.json 2>/dev/null | tail -1 && \
  python scripts/checks/dagster_inventory.py diff $M/inventory/dagster-main.json $M/inventory/dagster-branch.json ${DAG_FLAGS[*]:-}"
check $? "dagster inventory"

step "4b. dbt subset through Dagster (selection is passed to dbt as fqn from the manifest)"
rm -rf "$SHADOW_ROOT/lake-D"; cp -a --reflink=auto "$SHADOW_ROOT/lake-B" "$SHADOW_ROOT/lake-D"
"$RUN" "$BRANCH_DIR" "$SHADOW_ROOT/lake-D" sh -c 'cd transformation && dbt parse --profiles-dir . >/dev/null && cd .. && \
  timeout 600 dagster asset materialize -f orchestration/definitions.py --select "marts/fact_order_returns" 2>&1' \
  | grep -E "Running dbt command: .dbt build|Done. PASS|RUN_SUCCESS|RUN_FAILURE" | sed 's/^.* - //' | tail -3 | tee /tmp/gate-dagster-subset.log
grep -q "Finished execution of run" /tmp/gate-dagster-subset.log && grep -q "ERROR=0" /tmp/gate-dagster-subset.log; check $? "dagster dbt subset run"

step "5. pytest"
"$SCRIPT_DIR/pytest-shadow.sh" "$BRANCH_DIR" lake-B ingestion/tests orchestration scripts/tests -q 2>&1 | tail -3
PYTEST_RC=${PIPESTATUS[0]}
if [ "$PYTEST_RC" -ne 0 ]; then
  # test_concurrent_writes_no_lock_error (SQLite timing) fails ~1 in 4 runs on baseline too.
  # Re-run once; a real failure fails twice. The re-run is reported, never hidden.
  echo "pytest failed; re-running once to separate flaky timing tests from real failures"
  "$SCRIPT_DIR/pytest-shadow.sh" "$BRANCH_DIR" lake-B ingestion/tests orchestration scripts/tests -q 2>&1 | tail -3
  PYTEST_RC=${PIPESTATUS[0]}
  [ "$PYTEST_RC" -eq 0 ] && echo "FLAKY: first pytest run failed, re-run passed"
fi
check "$PYTEST_RC" "pytest"

step "6. empty-lake build (rolling directories deleted)"
"$SCRIPT_DIR/clone-lake.sh" lake-E --empty-rolling >/dev/null
"$SCRIPT_DIR/build-lake.sh" "$BRANCH_DIR" lake-E | tail -1; check "${PIPESTATUS[0]}" "dbt build on empty rolling"
golden_pair lake-A lake-E | tail -1; check "${PIPESTATUS[0]}" "golden on empty-rolling lake"

step "6b. bare-core profile (no pack, no tenant): the build must pass; differences with lake-A are printed for review"
# Expected differences: scripts/shadow/README.md "Bare-core profile". Only the build result decides.
"$SCRIPT_DIR/build-profile.sh" "$BRANCH_DIR" '{enabled_packs: [], tenant: ""}' lake-P 2>&1 \
  | grep -vE "^DIFF \[B capture error\]|only in A$" | sed -n '/=== run_results/,$p'
check "${PIPESTATUS[0]}" "bare-core profile build"

if [ "$LEVEL" = "S" ]; then
  step "7. full-refresh pass for incremental models and downstream"
  if [ ! -f "$SHADOW_ROOT/lake-AF/_shadow_meta/golden.json" ]; then
    "$SCRIPT_DIR/clone-lake.sh" lake-AF >/dev/null
    "$SCRIPT_DIR/build-lake.sh" "$BASELINE_DIR" lake-AF --full-refresh | tail -1
    "$RUN" "$BRANCH_DIR" "$SHADOW_ROOT" python scripts/checks/golden_snapshot.py capture --lake $M/lake-AF --models $MODELS --out $M/lake-AF/_shadow_meta/golden.json | tail -1
  fi
  "$SCRIPT_DIR/clone-lake.sh" lake-BF >/dev/null
  "$SCRIPT_DIR/build-lake.sh" "$BRANCH_DIR" lake-BF --full-refresh | tail -1; check "${PIPESTATUS[0]}" "dbt build --full-refresh (branch)"
  golden_pair lake-AF lake-BF; check $? "golden after full refresh"
fi

step "cleanup branch lakes (PII copies)"
"$SCRIPT_DIR/cleanup.sh" lake-B lake-D lake-E $( [ "$LEVEL" = "S" ] && echo lake-BF )

echo
if [ "$FAIL" -eq 0 ]; then echo "GATE $LEVEL: PASS"; else echo "GATE $LEVEL: FAIL"; fi
exit "$FAIL"
