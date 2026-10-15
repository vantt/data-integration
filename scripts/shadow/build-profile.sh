#!/usr/bin/env bash
# Build a shadow lake with a non-default dbt profile (e.g. packs turned off) and show how it
# differs from the baseline lake-A. Informational: the golden compare never decides the exit code.
#
# Usage: scripts/shadow/build-profile.sh <code_dir> '<dbt vars yaml>' [lake_name]
#   e.g. scripts/shadow/build-profile.sh /home/vantt/app/fg-dw-pack '{enabled_packs: []}'
#   lake_name  default lake-P (created under $SHADOW_ROOT from lake-base with the rolling tree
#              deleted, so every rolling model of the profile is rebuilt from scratch)
# Env: KEEP=1 keeps the lake afterwards (it holds customer PII: delete it with cleanup.sh).
#
# Steps: clone-lake.sh --empty-rolling, build-lake.sh <code_dir> <lake> --vars '<vars>', a
# summary of run_results.json (status counts and every non-success node with the first line of
# its message; when dbt stopped at parse/compile time, the error from build.log instead), then
# golden_snapshot.py capture + compare against lake-A (printed only, skipped when dbt built nothing).
# Exit code: the dbt build exit code.
set -uo pipefail

SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ "$#" -ge 2 ] || { echo "usage: $0 <code_dir> '<dbt vars yaml>' [lake_name]" >&2; exit 2; }
CODE_DIR="$(realpath "$1")"; VARS="$2"; LAKE_NAME="${3:-lake-P}"
case "$LAKE_NAME" in lake-A|lake-A2|lake-AF|lake-base|*/*|"") echo "refusing lake name $LAKE_NAME" >&2; exit 2 ;; esac
M=/app/var/data_lake
MODELS=scripts/checks/public_models.yaml

"$SCRIPT_DIR/clone-lake.sh" "$LAKE_NAME" --empty-rolling >/dev/null || exit 1
echo "=== build $CODE_DIR on $LAKE_NAME with --vars '$VARS'"
"$SCRIPT_DIR/build-lake.sh" "$CODE_DIR" "$LAKE_NAME" --vars "$VARS" | tail -2
RC=${PIPESTATUS[0]}

echo "=== run_results"
# build-lake.sh copies the artifacts left in transformation/target; when dbt stops at parse or
# compile time they belong to an earlier run, so they are used only if written by this build.
META="$SHADOW_ROOT/$LAKE_NAME/_shadow_meta"
FRESH=0
python3 - "$META/run_results.json" "$META/build_start" <<'PY' && FRESH=1
import collections, datetime, json, os, sys
path, start_file = sys.argv[1], sys.argv[2]
start = datetime.datetime.fromisoformat(open(start_file).read().strip().replace("Z", "+00:00"))
doc = json.load(open(path)) if os.path.exists(path) else None
generated = doc and datetime.datetime.fromisoformat(doc["metadata"]["generated_at"].replace("Z", "+00:00"))
if not doc or generated < start:
    print("no run_results from this build: dbt stopped before running any node (errors below)")
    sys.exit(1)
results = doc["results"]
print("status:", dict(collections.Counter(r["status"] for r in results)))
for r in sorted(results, key=lambda r: r["unique_id"]):
    if r["status"] not in ("success", "pass"):
        msg = (r.get("message") or "").strip().splitlines()
        print(f"  {r['status']:6} {r['unique_id']}: {msg[0][:160] if msg else ''}")
PY
if [ "$FRESH" -eq 0 ]; then
  sed 's/\x1b\[[0-9;]*m//g' "$META/build.log" | grep -A3 -E "Compilation Error|Parsing Error|Encountered an error" | head -12
fi

if [ "$FRESH" -eq 1 ] && [ -f "$SHADOW_ROOT/lake-A/_shadow_meta/golden.json" ]; then
  echo "=== golden lake-A vs $LAKE_NAME (informational)"
  "$SCRIPT_DIR/run-shadow.sh" "$CODE_DIR" "$SHADOW_ROOT" sh -c "
    python scripts/checks/golden_snapshot.py capture --lake $M/$LAKE_NAME --models $MODELS --out $M/$LAKE_NAME/_shadow_meta/golden.json | tail -1
    python scripts/checks/golden_snapshot.py compare $M/lake-A/_shadow_meta/golden.json $M/$LAKE_NAME/_shadow_meta/golden.json" \
    || true
fi

if [ "${KEEP:-0}" = "1" ]; then
  echo "kept $SHADOW_ROOT/$LAKE_NAME (PII: scripts/shadow/cleanup.sh $LAKE_NAME)"
else
  "$SCRIPT_DIR/cleanup.sh" "$LAKE_NAME" >/dev/null && echo "removed $SHADOW_ROOT/$LAKE_NAME"
fi
echo "build-profile: dbt build rc=$RC"
exit "$RC"
