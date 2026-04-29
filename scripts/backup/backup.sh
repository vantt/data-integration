#!/usr/bin/env bash
# =============================================================================
# Data Integration Platform - Automated Backup Script (Linux/Docker version)
# =============================================================================
# Hot backup variant for running inside Docker containers.
# Does NOT stop containers (Dagster would kill itself). Metabase H2 DB may
# have minor inconsistency — acceptable trade-off for automated scheduling.
#
# Usage:
#   ./backup.sh                                   # Use env var defaults
#   BACKUP_ROOT=/backups ./backup.sh              # Override backup location
#   BACKUP_KEEP_COUNT=14 ./backup.sh              # Keep 14 backups
# =============================================================================

set -euo pipefail

PROJECT_ROOT="${BACKUP_PROJECT_ROOT:-/app}"
BACKUP_ROOT="${BACKUP_ROOT:?BACKUP_ROOT env var is required}"
KEEP_COUNT="${BACKUP_KEEP_COUNT:-7}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${BACKUP_ROOT}/${TIMESTAMP}"
LOG_FILE="${BACKUP_ROOT}/backup-${TIMESTAMP}.log"
EXIT_CODE=0
BACKUP_DATA_OK=false

# --- Helpers ---
log() { local msg="$(date +%H:%M:%S) $*"; echo "$msg"; echo "$msg" >> "$LOG_FILE" 2>/dev/null || true; }

# Drop dagster_home/history/ from a copied dagster_home — Dagster run records
# are regenerable and large (often the bulk of dagster_home). Restoring runs
# from an old backup is undesirable; we only need dagster.yaml, schedules/,
# storage/ (assets), logs/ etc. to recover orchestration state.
prune_dagster_history() {
    local dh_dir="$1"
    if [ -d "${dh_dir}/history" ]; then
        rm -rf "${dh_dir}/history"
        log "Pruned ${dh_dir}/history (run records excluded from backup)"
    fi
}

# Always-run cleanup, registered as EXIT trap. Runs even when the script
# aborts mid-copy (set -e + cp failure on disk-full, etc.) — without this,
# rotation only fired on success, so failing backups piled up and made the
# next run fail too. Idempotent: safe to run when there's nothing to clean.
rotate_old_backups() {
    local rc=$?
    set +e  # never let cleanup itself bubble up an error

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
trap rotate_old_backups EXIT

# Disk space pre-flight: estimate need vs free, fail fast if insufficient.
# Need = size of directories being backed up + 1 GB safety margin.
# IMPORTANT: measure only the source dirs (data_lake, dagster_home, input_source),
# NOT the parent DATA_ROOT — that would include BACKUP_ROOT itself (circular).
# Trap still runs on early exit → old backups get rotated → space freed for next attempt.
_precheck_need_kb() {
    local total=0
    if [ -d "${PROJECT_ROOT}/app_data" ]; then
        total=$(du -sk "${PROJECT_ROOT}/app_data" 2>/dev/null | awk '{print $1}')
    else
        local dr="${DATA_ROOT:-/app/var}"
        for vol in data_lake dagster_home input_source; do
            local d="${dr}/${vol}"
            if [ -d "$d" ]; then
                local sz
                sz=$(du -sk "$d" 2>/dev/null | awk '{print $1}')
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

START_SECONDS=$SECONDS

# --- Step 1: Backup app_data ---
# Docker layout: data directories grouped under /app/var/.
# Local layout: grouped under ${PROJECT_ROOT}/app_data/.
DATA_ROOT="${DATA_ROOT:-/app/var}"

# Try the native-style app_data first (if running outside Docker or custom mount)
if [ -d "${PROJECT_ROOT}/app_data" ]; then
    APP_DATA_SRC="${PROJECT_ROOT}/app_data"
    APP_DATA_DST="${BACKUP_DIR}/app_data"
    log "Backing up app_data from ${APP_DATA_SRC}..."
    if cp -a "$APP_DATA_SRC" "$APP_DATA_DST" 2>&1; then
        BACKUP_DATA_OK=true
        prune_dagster_history "${APP_DATA_DST}/dagster_home"
        SIZE=$(du -sh "$APP_DATA_DST" 2>/dev/null | cut -f1 || echo "unknown")
        log "app_data backed up: ${SIZE}"
    else
        log "ERROR: cp failed for app_data"
        EXIT_CODE=1
    fi
else
    # Docker volume layout: all data dirs under DATA_ROOT (/app/var/)
    mkdir -p "${BACKUP_DIR}/app_data"
    for vol_name in data_lake dagster_home input_source; do
        candidate="${DATA_ROOT}/${vol_name}"
        if [ -d "$candidate" ]; then
            log "Backing up ${vol_name} from ${candidate}..."
            if cp -a "$candidate" "${BACKUP_DIR}/app_data/${vol_name}" 2>&1; then
                BACKUP_DATA_OK=true
                if [ "$vol_name" = "dagster_home" ]; then
                    prune_dagster_history "${BACKUP_DIR}/app_data/dagster_home"
                fi
                log "${vol_name} backed up."
            else
                log "WARNING: failed to copy ${candidate}"
            fi
        fi
    done
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
CONFIG_SRC="${PROJECT_ROOT}"
for f in .env.docker docker-compose.yml Dockerfile.dataplatform Dockerfile.metabase; do
    src="${CONFIG_SRC}/${f}"
    if [ -f "$src" ]; then
        cp "$src" "$CONFIG_DST/" && COPIED=$((COPIED + 1))
    fi
done
log "Config files backed up (${COPIED} found)."

# --- Step 3: Finalize ---
# Cleanup (rotation + failed-dir removal) is handled by the EXIT trap so it
# runs even when the script aborts mid-copy.
ELAPSED=$(( SECONDS - START_SECONDS ))
if [ "$EXIT_CODE" -eq 0 ]; then
    log "=== Backup completed successfully in ${ELAPSED}s ==="
    log "Backup location: $BACKUP_DIR"
else
    log "=== Backup completed WITH ERRORS in ${ELAPSED}s ==="
fi

exit $EXIT_CODE
