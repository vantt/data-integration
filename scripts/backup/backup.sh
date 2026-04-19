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

# --- Pre-flight ---
if [ "$KEEP_COUNT" -lt 1 ]; then
    echo "ERROR: BACKUP_KEEP_COUNT must be >= 1 (got $KEEP_COUNT)" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

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

# --- Step 3: Remove failed backup directory ---
if [ "$BACKUP_DATA_OK" = false ]; then
    rm -rf "$BACKUP_DIR" 2>/dev/null && log "Removed failed backup dir." || log "WARNING: could not remove failed backup dir."
fi

# --- Step 4: Rotate old backups ---
log "Rotating backups (keeping last ${KEEP_COUNT})..."
# List timestamp-named dirs, newest first, skip $KEEP_COUNT, delete rest
cd "$BACKUP_ROOT"
ls -1d [0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9] 2>/dev/null \
    | sort -r \
    | tail -n +$((KEEP_COUNT + 1)) \
    | while read -r old; do
        rm -rf "${BACKUP_ROOT}/${old}" && log "Deleted old backup: ${old}" || log "WARNING: could not delete ${old}"
    done || true

# Rotate logs
for pattern in "backup-*.log" "restore-*.log"; do
    ls -1 ${pattern} 2>/dev/null | sort -r | tail -n +$((KEEP_COUNT + 1)) | while read -r old_log; do
        rm -f "${BACKUP_ROOT}/${old_log}" 2>/dev/null || true
    done || true
done

ELAPSED=$(( SECONDS - START_SECONDS ))
if [ "$EXIT_CODE" -eq 0 ]; then
    log "=== Backup completed successfully in ${ELAPSED}s ==="
    log "Backup location: $BACKUP_DIR"
else
    log "=== Backup completed WITH ERRORS in ${ELAPSED}s ==="
fi

exit $EXIT_CODE
