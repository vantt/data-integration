#!/usr/bin/env bash
# Build the offline tools used by run-shadow.sh: dbt_packages, DuckDB extensions and a pinned
# pytest. They hold no data, so they live outside the shadow root and survive its deletion
# (cleanup.sh --all): scripts/checks/run-all.sh keeps working between refactor waves.
#
# Usage: scripts/shadow/prepare-deps.sh
# Env:   SHADOW_DEPS  destination (default ${XDG_CACHE_HOME:-$HOME/.cache}/fg-dw-tools/deps)
# Re-run after the prod image or dbt_packages change (versions must match prod).
set -euo pipefail

PROD_ROOT=/home/vantt/app/fg-dataware-house
DEPS="${SHADOW_DEPS:-${XDG_CACHE_HOME:-$HOME/.cache}/fg-dw-tools/deps}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/../checks/guard_not_prod.py" "$DEPS"
umask 077

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
  pip download "pytest==8.3.3" "pluggy==1.6.0" "iniconfig==2.3.1" -d /w -q --disable-pip-version-check
docker run --rm --network none --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$DEPS/wheels:/w" \
  -v "$DEPS/home:/shadow-home" "$IMAGE" pip install --no-index --no-deps --find-links /w \
  --target /shadow-home/pylib -q --disable-pip-version-check pytest==8.3.3 pluggy==1.6.0 iniconfig==2.3.1

chmod -R go-rwx "$DEPS"
du -sh "$DEPS"
