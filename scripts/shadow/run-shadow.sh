#!/usr/bin/env bash
# Run a command inside a one-off container built from the prod image, fully isolated
# from production: no network, no secrets, code and data from shadow paths only.
#
# Usage: scripts/shadow/run-shadow.sh <code_dir> <lake_dir> <cmd...>
#   code_dir  a git worktree (never the prod checkout)
#   lake_dir  a shadow lake under $SHADOW_ROOT (never app_data/ of prod)
#
# Mount layout mirrors docker-compose.yml `data_platform` (per-subdirectory code mounts,
# data lake at /app/var/data_lake) so paths inside the container match prod exactly.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHADOW_ROOT="${SHADOW_ROOT:-/home/vantt/app/fg-dw-shadow}"
IMAGE="${SHADOW_IMAGE:-fg-dataware-house-data_platform:latest}"

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <code_dir> <lake_dir> <cmd...>" >&2
  exit 2
fi
CODE_DIR="$(realpath "$1")"; LAKE_DIR="$(realpath "$2")"; shift 2

python3 "$SCRIPT_DIR/../checks/guard_not_prod.py" "$CODE_DIR" "$LAKE_DIR" "$SHADOW_ROOT"
case "$LAKE_DIR" in
  "$(realpath "$SHADOW_ROOT")"|"$(realpath "$SHADOW_ROOT")"/*) ;;
  *) echo "run-shadow: lake_dir must live under $SHADOW_ROOT" >&2; exit 1 ;;
esac
for forbidden in --env-file app_data/secrets agent_codex_config; do
  case " $* " in *"$forbidden"*) echo "run-shadow: refused argument containing $forbidden" >&2; exit 1 ;; esac
done

DEPS="$SHADOW_ROOT/deps"
[ -d "$DEPS/dbt_packages" ] && [ -d "$DEPS/home/.duckdb" ] || {
  echo "run-shadow: missing $DEPS (run scripts/shadow/prepare-shadow.sh first)" >&2; exit 1; }

code_mounts=()
for d in transformation ingestion orchestration scripts webhook_consumer; do
  [ -d "$CODE_DIR/$d" ] && code_mounts+=(-v "$CODE_DIR/$d:/app/$d")
done

# Explicit env allowlist. Values are the non-secret path settings from
# .env.docker.example and the compose `environment:` block; .env.docker is never read.
exec docker run --rm --network none \
  --user "$(id -u):$(id -g)" --cpus="${SHADOW_CPUS:-2}" --memory="${SHADOW_MEMORY:-6g}" \
  "${code_mounts[@]}" \
  -v "$DEPS/dbt_packages:/app/transformation/dbt_packages:ro" \
  -v "$LAKE_DIR:/app/var/data_lake" \
  -v "$DEPS/home:/shadow-home" \
  --tmpfs /app/var/dagster_home:uid="$(id -u)" \
  -w /app \
  -e HOME=/shadow-home \
  -e TZ=Asia/Ho_Chi_Minh \
  -e PYTHONPATH=/app \
  -e DAGSTER_HOME=/app/var/dagster_home \
  -e DBT_DATA_LAKE_PATH=/app/var/data_lake \
  -e DBT_EXPORT_PATH=/app/var/data_lake/export/marts \
  -e DESTINATION__FILESYSTEM__BUCKET_URL=file:///app/var/data_lake \
  -e OLAP_DB_PATH=/app/var/data_lake/serving/olap.duckdb \
  -e DLT_TELEMETRY_DISABLED=true \
  -e DBT_SEND_ANONYMOUS_USAGE_STATS=false \
  -e SHADOW=1 \
  "$IMAGE" \
  sh -c 'python -c "import socket,sys
try:
    socket.getaddrinfo(\"github.com\", 443)
except OSError:
    sys.exit(0)
print(\"run-shadow: network is reachable, refusing to run\", file=sys.stderr); sys.exit(1)" && exec "$@"' sh "$@"
