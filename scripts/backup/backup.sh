#!/usr/bin/env bash
# =============================================================================
# Data Integration Platform - nightly local backup (Linux/Docker)
# =============================================================================
# Runs inside the data_platform container (Dagster job maintain_backup_platform_job, op that
# holds duckdb_lock, so dbt and serving are not writing DuckDB). Does NOT stop containers.
#
# Docker layout (DATA_ROOT=/app/var), one directory per run under BACKUP_ROOT:
#   app_data/data_lake/      hot copy of the lake (raw = source of truth; sapo_warehouse.duckdb
#                            and serving/ = "accelerator": used only if they open, dbt rebuilds
#                            them). The monitoring/ volume is NOT copied file by file.
#   app_data/monitoring/     ingestion_health.db via the SQLite backup API (sqlite_snapshot.py)
#   app_data/dagster_home/   schedules/schedules.db via the SQLite backup API + dagster.yaml.
#                            history/ (runs, event log) and storage/ (IO manager output, compute
#                            logs) are not kept: regenerated, and run history is purged daily.
#   app_data/input_source/   hot copy (files dropped by hand)
#   exports/warehouse/       tables that cannot be rebuilt from raw, exported to parquet
#                            (duckdb_snapshot.py; BACKUP_EXPORT_TABLES)
#   config/                  docker-compose.yml, Dockerfiles (never .env*: secrets stay off
#                            local backups, ADR-019 D6)
#   metabase_export/         Metabase content as JSON through its API (metabase_export.py)
#   manifest.json            every component: role, size, sha256, row counts (backup_manifest.py)
# Status of the last run: BACKUP_ROOT/status/local.json (state ok | partial | failed), written
# even when the script aborts. "partial" = the data copy succeeded but a consistent snapshot
# (monitoring, schedules, exports) failed; the job stays green and the status file says which.
# The Metabase H2 file is copied cold on the host by metabase_cold_backup.sh.
#
# Usage:
#   ./backup.sh                                   # Use env var defaults
#   BACKUP_ROOT=/backups ./backup.sh              # Override backup location
#   BACKUP_KEEP_COUNT=14 ./backup.sh              # Keep 14 backups
# Env: BACKUP_EXPORT_TABLES (default main.monitor_taxonomy_parity_log), BACKUP_GIT_SHA
# (recorded in the manifest when set).
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${BACKUP_PROJECT_ROOT:-/app}"
BACKUP_ROOT="${BACKUP_ROOT:?BACKUP_ROOT env var is required}"
KEEP_COUNT="${BACKUP_KEEP_COUNT:-7}"
EXPORT_TABLES="${BACKUP_EXPORT_TABLES:-main.monitor_taxonomy_parity_log}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
LOG_FILE="${BACKUP_ROOT}/backup-${TIMESTAMP}.log"
STATUS_FILE="${BACKUP_ROOT}/status/local.json"
EXIT_CODE=0
BACKUP_DATA_OK=false
PARTIAL_ERRORS=()
START_SECONDS=$SECONDS
# Commit of the code that took the backup, when the checkout is visible (not in the container,
# which mounts only subdirectories: the off-site wrapper records it on the host instead).
if [ -z "${BACKUP_GIT_SHA:-}" ] && [ -e "${PROJECT_ROOT}/.git" ] && command -v git >/dev/null 2>&1; then
    BACKUP_GIT_SHA="$(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || true)"
fi
export BACKUP_GIT_SHA="${BACKUP_GIT_SHA:-}"

# --- Helpers ---
log() { local msg="$(date +%H:%M:%S) $*"; echo "$msg"; echo "$msg" >> "$LOG_FILE" 2>/dev/null || true; }
py() { python3 "${SCRIPT_DIR}/$1" "${@:2}"; }

# Run a snapshot step; its failure makes the run "partial", never aborts the data backup.
snapshot_step() {
    local label="$1"; shift
    local out rc=0
    out="$("$@" 2>&1)" || rc=$?
    while IFS= read -r line; do [ -n "$line" ] && log "$line"; done <<< "$out"
    if [ "$rc" -ne 0 ]; then
        PARTIAL_ERRORS+=("${label} failed (rc=${rc})")
        log "WARNING: ${label} failed (rc=${rc}); continuing"
    fi
}

# Record a copied tree/file in the manifest (size and file count, no hashing of the bulk).
dir_entry() {  # <component> <path relative to BACKUP_DIR> <role>
    py backup_manifest.py dir-entry "$BACKUP_DIR" "$1" "$2" "$3" >/dev/null \
        || PARTIAL_ERRORS+=("manifest entry for $1 failed")
}

# Drop dagster_home/history/ from a copied dagster_home (native layout only).
prune_dagster_history() {
    local dh_dir="$1"
    if [ -d "${dh_dir}/history" ]; then
        rm -rf "${dh_dir}/history"
        log "Pruned ${dh_dir}/history (run records excluded from backup)"
    fi
}

# Role of a top-level entry of the data lake in the manifest.
lake_role() {
    case "$1" in
        sapo_warehouse.duckdb|sapo_warehouse.duckdb.wal|serving) echo accelerator ;;
        export|crm_export|sapo_raw_staging|test_raw|desktop.ini) echo copy ;;
        *) echo source_of_truth ;;
    esac
}

# Always-run cleanup, registered as EXIT trap: status file first, then rotation. Runs even
# when the script aborts mid-copy (set -e + cp failure on disk-full, etc.) — without this,
# rotation only fired on success, so failing backups piled up and made the next run fail too.
on_exit() {
    local rc=$?
    set +e  # never let cleanup itself bubble up an error

    local state=ok dir_arg=()
    if [ "$rc" -ne 0 ] || [ "${BACKUP_DATA_OK:-false}" = false ]; then
        state=failed
    elif [ "${#PARTIAL_ERRORS[@]}" -gt 0 ]; then
        state=partial
    fi
    [ "$state" != failed ] && [ -d "${BACKUP_DIR:-}" ] && dir_arg=("$BACKUP_DIR")
    local err_args=()
    for e in "${PARTIAL_ERRORS[@]}"; do err_args+=(--error "$e"); done
    [ "$state" = failed ] && err_args+=(--error "backup failed (rc=${rc})")
    mkdir -p "${BACKUP_ROOT}/status" 2>/dev/null
    # The host-side Metabase script (user vantt) writes into the same directory.
    chown --reference="$BACKUP_ROOT" "${BACKUP_ROOT}/status" 2>/dev/null
    py backup_manifest.py status "$STATUS_FILE" "$state" "$((SECONDS - START_SECONDS))" \
        "${dir_arg[@]}" "${err_args[@]}" || echo "WARNING: could not write $STATUS_FILE" >&2
    log "Status: ${state} (${STATUS_FILE})"

    # Drop incomplete backup if data step never finished
    if [ "${BACKUP_DATA_OK:-false}" = false ] && [ -n "${BACKUP_DIR:-}" ] && [ -d "$BACKUP_DIR" ]; then
        rm -rf "$BACKUP_DIR" 2>/dev/null && log "Removed failed backup dir: $(basename "$BACKUP_DIR")"
    fi

    # Rotate timestamped backup dirs (newest $KEEP_COUNT kept)
    if [ -d "${BACKUP_ROOT:-}" ]; then
        local keep="${KEEP_COUNT:-7}"
        cd "$BACKUP_ROOT" 2>/dev/null || return $rc
        ls -1d [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9] 2>/dev/null \
            | sort -r \
            | tail -n +$((keep + 1)) \
            | while read -r old; do
                rm -rf "${BACKUP_ROOT}/${old}" && log "Rotated old backup: ${old}"
            done
        # Rotate log files alongside backup dirs
        for pattern in "backup-*.log" "restore-*.log"; do
            ls -1 ${pattern} 2>/dev/null | sort -r | tail -n +$((keep + 1)) | while read -r old_log; do
                rm -f "${BACKUP_ROOT}/${old_log}" 2>/dev/null
            done
        done
    fi

    return $rc
}

# --- Pre-flight ---
if [ "$KEEP_COUNT" -lt 1 ]; then
    echo "ERROR: BACKUP_KEEP_COUNT must be >= 1 (got $KEEP_COUNT)" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# Register cleanup AFTER vars are set (so trap can read BACKUP_DIR/BACKUP_ROOT/KEEP_COUNT).
trap on_exit EXIT

DATA_ROOT="${DATA_ROOT:-/app/var}"

# Disk space pre-flight: estimate need vs free, fail fast if insufficient.
# Need = size of what is copied + 1 GB safety margin. Measure only the sources, NOT the parent
# DATA_ROOT — that would include BACKUP_ROOT itself (circular). dagster_home counts only
# schedules.db (history/ and storage/ are not copied).
# Trap still runs on early exit → old backups get rotated → space freed for next attempt.
_precheck_need_kb() {
    local total=0 sz
    if [ -d "${PROJECT_ROOT}/app_data" ]; then
        total=$(du -sk "${PROJECT_ROOT}/app_data" 2>/dev/null | awk '{print $1}')
    else
        for p in "${DATA_ROOT}/data_lake" "${DATA_ROOT}/input_source" "${DATA_ROOT}/dagster_home/schedules/schedules.db"; do
            if [ -e "$p" ]; then
                sz=$(du -sk "$p" 2>/dev/null | awk '{print $1}')
                total=$((total + ${sz:-0}))
            fi
        done
    fi
    echo "$total"
}
NEED_KB=$(_precheck_need_kb)
if [ -n "$NEED_KB" ] && [ "$NEED_KB" -gt 0 ]; then
    FREE_KB=$(df -Pk "$BACKUP_ROOT" | awk 'NR==2 {print $4}')
    SAFETY_KB=$((1024 * 1024))  # 1 GB
    if [ -n "$FREE_KB" ] && [ "$FREE_KB" -lt "$((NEED_KB + SAFETY_KB))" ]; then
        log "=== Backup ABORTED: insufficient disk space ==="
        log "Source size:  $((NEED_KB / 1024)) MB"
        log "Free space:   $((FREE_KB / 1024)) MB"
        log "Required:     $((NEED_KB / 1024 + 1024)) MB (source + 1 GB margin)"
        log "Trap will still rotate old backups to free space for next attempt."
        EXIT_CODE=1
        exit 1
    fi
fi

log "=== Backup started: $TIMESTAMP ==="
log "Source: $PROJECT_ROOT"
log "Destination: $BACKUP_DIR"
log "Mode: hot backup (no container stop — running inside Docker)"

# --- Step 1: Backup app_data ---
if [ -d "${PROJECT_ROOT}/app_data" ]; then
    # Native layout (outside Docker): one copy of app_data.
    APP_DATA_SRC="${PROJECT_ROOT}/app_data"
    APP_DATA_DST="${BACKUP_DIR}/app_data"
    log "Backing up app_data from ${APP_DATA_SRC}..."
    if cp -a "$APP_DATA_SRC" "$APP_DATA_DST" 2>&1; then
        BACKUP_DATA_OK=true
        # Exclude GCP service-account key — backup archives live outside app_data's
        # access controls, don't propagate the credential there.
        rm -rf "${APP_DATA_DST}/secrets"
        prune_dagster_history "${APP_DATA_DST}/dagster_home"
        dir_entry app_data app_data source_of_truth
        log "app_data backed up: $(du -sh "$APP_DATA_DST" 2>/dev/null | cut -f1 || echo unknown)"
    else
        log "ERROR: cp failed for app_data"
        EXIT_CODE=1
    fi
else
    # Docker layout: data dirs under DATA_ROOT (/app/var/). crm_data is backed up by
    # crm/ops/backup_crm.py (consistent SQLite snapshot, not a raw WAL copy).
    mkdir -p "${BACKUP_DIR}/app_data"

    # 1a. data lake, without the monitoring/ volume (a live SQLite file, snapshotted in 1b).
    LAKE_SRC="${DATA_ROOT}/data_lake"
    LAKE_DST="${BACKUP_DIR}/app_data/data_lake"
    if [ -d "$LAKE_SRC" ]; then
        log "Backing up data_lake from ${LAKE_SRC} (without monitoring/)..."
        mkdir -p "$LAKE_DST"
        shopt -s dotglob nullglob
        for entry in "$LAKE_SRC"/*; do
            name="$(basename "$entry")"
            [ "$name" = monitoring ] && continue
            # cp -a may return non-zero when a DuckDB WAL is checkpointed (deleted/recreated)
            # mid-copy. Treat as success if the destination was populated.
            cp -a "$entry" "$LAKE_DST/" 2>/dev/null || true
            [ -e "$LAKE_DST/$name" ] && dir_entry "data_lake/${name}" "app_data/data_lake/${name}" "$(lake_role "$name")"
        done
        shopt -u dotglob nullglob
        if [ "$(ls -A "$LAKE_DST" 2>/dev/null)" ]; then
            BACKUP_DATA_OK=true
            log "data_lake backed up: $(du -sh "$LAKE_DST" 2>/dev/null | cut -f1 || echo unknown)"
        else
            log "WARNING: failed to copy ${LAKE_SRC} (destination empty)"
        fi
    fi

    # 1b. monitoring: ingestion_health.db (SQLite, WAL) through the backup API.
    log "Snapshotting monitoring/ingestion_health.db..."
    snapshot_step "monitoring snapshot" py sqlite_snapshot.py \
        "${LAKE_SRC}/monitoring/ingestion_health.db" "${BACKUP_DIR}/app_data/monitoring/ingestion_health.db" \
        --backup-dir "$BACKUP_DIR" --component monitoring

    # 1c. dagster_home: schedule/sensor state and cursors only.
    DH_SRC="${DATA_ROOT}/dagster_home"
    DH_DST="${BACKUP_DIR}/app_data/dagster_home"
    if [ -d "$DH_SRC" ]; then
        log "Snapshotting dagster_home/schedules/schedules.db..."
        mkdir -p "$DH_DST"
        snapshot_step "dagster schedules snapshot" py sqlite_snapshot.py \
            "${DH_SRC}/schedules/schedules.db" "${DH_DST}/schedules/schedules.db" \
            --backup-dir "$BACKUP_DIR" --component dagster_home
        if [ -f "${DH_SRC}/dagster.yaml" ]; then
            cp -a "${DH_SRC}/dagster.yaml" "${DH_DST}/" && dir_entry dagster_yaml app_data/dagster_home/dagster.yaml copy
        fi
    fi

    # 1d. input_source: files dropped by hand.
    if [ -d "${DATA_ROOT}/input_source" ]; then
        log "Backing up input_source from ${DATA_ROOT}/input_source..."
        cp -a "${DATA_ROOT}/input_source" "${BACKUP_DIR}/app_data/input_source" 2>/dev/null || true
        if [ -d "${BACKUP_DIR}/app_data/input_source" ]; then
            dir_entry input_source app_data/input_source source_of_truth
            log "input_source backed up: $(du -sh "${BACKUP_DIR}/app_data/input_source" 2>/dev/null | cut -f1 || echo unknown)"
        else
            PARTIAL_ERRORS+=("input_source copy failed")
        fi
    fi

    # 1e. tables that cannot be rebuilt from raw (append-only history in the warehouse).
    log "Exporting warehouse tables: ${EXPORT_TABLES}..."
    snapshot_step "warehouse export" py duckdb_snapshot.py \
        "${LAKE_SRC}/sapo_warehouse.duckdb" "${BACKUP_DIR}/exports/warehouse" \
        --tables "$EXPORT_TABLES" --backup-dir "$BACKUP_DIR" --component exports_warehouse

    if [ "$BACKUP_DATA_OK" = false ]; then
        log "ERROR: no data directories found to back up"
        EXIT_CODE=1
    fi
fi

# --- Step 2: Backup config files ---
log "Backing up config files..."
CONFIG_DST="${BACKUP_DIR}/config"
mkdir -p "$CONFIG_DST"
COPIED=0
# Config files are mounted read-only at PROJECT_ROOT in Docker (same relative path as host)
for f in docker-compose.yml Dockerfile.dataplatform Dockerfile.metabase; do
    src="${PROJECT_ROOT}/${f}"
    if [ -f "$src" ]; then
        cp "$src" "$CONFIG_DST/" && COPIED=$((COPIED + 1))
    fi
done
[ "$COPIED" -gt 0 ] && dir_entry config config copy
log "Config files backed up (${COPIED} found)."

# --- Step 2b: Export Metabase content through its API ---
# metabase_data is not mounted in this container; the H2 file itself is copied cold on the
# host (metabase_cold_backup.sh). This export is a readable JSON record of collections, cards
# and dashboards. A failure is a warning only: it never fails the data backup.
log "Exporting Metabase content (API)..."
MB_RC=0
MB_OUT="$(python3 "${SCRIPT_DIR}/metabase_export.py" "${BACKUP_DIR}/metabase_export" 2>&1)" || MB_RC=$?
while IFS= read -r line; do [ -n "$line" ] && log "$line"; done <<< "$MB_OUT"
if [ "$MB_RC" -ne 0 ]; then
    log "WARNING: Metabase export failed (rc=${MB_RC}); data backup is unaffected"
else
    dir_entry metabase_export metabase_export copy
fi

# --- Step 2c: secrets never land in a local backup (ADR-019 D6) ---
LEAKED="$(find "$BACKUP_DIR" -name '.env*' -type f 2>/dev/null)"
if [ -n "$LEAKED" ]; then
    while IFS= read -r f; do rm -f "$f"; log "ERROR: removed secret file from backup: ${f#"$BACKUP_DIR"/}"; done <<< "$LEAKED"
    PARTIAL_ERRORS+=("secret files found in the backup and removed")
fi

# --- Step 3: Finalize ---
if [ "$BACKUP_DATA_OK" = true ]; then
    MANIFEST_OUT="$(py backup_manifest.py assemble "$BACKUP_DIR" 2>&1)" || PARTIAL_ERRORS+=("manifest assembly failed")
    log "$MANIFEST_OUT"
fi
# Cleanup (status, rotation, failed-dir removal) is handled by the EXIT trap so it runs even
# when the script aborts mid-copy.
ELAPSED=$(( SECONDS - START_SECONDS ))
if [ "$EXIT_CODE" -eq 0 ] && [ "${#PARTIAL_ERRORS[@]}" -eq 0 ]; then
    log "=== Backup completed successfully in ${ELAPSED}s ==="
    log "Backup location: $BACKUP_DIR"
elif [ "$EXIT_CODE" -eq 0 ]; then
    log "=== Backup completed with ${#PARTIAL_ERRORS[@]} snapshot problem(s) in ${ELAPSED}s (status: partial) ==="
    for e in "${PARTIAL_ERRORS[@]}"; do log "  - $e"; done
    log "Backup location: $BACKUP_DIR"
else
    log "=== Backup completed WITH ERRORS in ${ELAPSED}s ==="
fi

exit $EXIT_CODE
