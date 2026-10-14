#!/usr/bin/env bash
# =============================================================================
# Cold copy of the Metabase H2 database (the full Metabase restore point).
# =============================================================================
# Runs on the HOST (needs docker and app_data/metabase_data; the data_platform container has
# neither). Stops the `metabase` container, copies metabase.db.mv.db while no process holds it,
# starts Metabase again and waits for /api/health. Metabase is unreachable for 1-2 minutes.
#
# Usage:
#   scripts/backup/metabase_cold_backup.sh weekly       # systemd timer (Sunday 00:30)
#   scripts/backup/metabase_cold_backup.sh pre-deploy   # by hand, before a deploy that writes to Metabase
#
# Copies: app_data/backups/metabase/metabase-<kind>-<YYYYmmdd-HHMMSS>.mv.db, newest
# METABASE_COLD_KEEP (default 7) kept per kind. Log: app_data/backups/metabase/cold-backup.log.
# Exit code 0 only when the copy is complete and Metabase is healthy again.
# Restore: docs/operations/deployment.md, section "Metabase".
set -uo pipefail

KIND="${1:-}"
case "$KIND" in weekly|pre-deploy) ;; *) echo "usage: $0 weekly|pre-deploy" >&2; exit 2 ;; esac

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTAINER="${METABASE_CONTAINER:-metabase}"
SRC="${PROJECT_ROOT}/app_data/metabase_data/metabase.db.mv.db"
DEST_DIR="${PROJECT_ROOT}/app_data/backups/metabase"
KEEP="${METABASE_COLD_KEEP:-7}"
HEALTH_URL="${METABASE_HEALTH_URL:-http://127.0.0.1:3001/api/health}"
HEALTH_WAIT_SEC=300
DEST="${DEST_DIR}/metabase-${KIND}-$(date +%Y%m%d-%H%M%S).mv.db"
LOG_FILE="${DEST_DIR}/cold-backup.log"

mkdir -p "$DEST_DIR"
log() { local msg; msg="$(date '+%F %T') [${KIND}] $*"; echo "$msg"; echo "$msg" >> "$LOG_FILE"; }

[ -f "$SRC" ] || { log "ERROR: $SRC not found"; exit 1; }
WAS_RUNNING="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null || echo missing)"
[ "$WAS_RUNNING" = missing ] && { log "ERROR: container $CONTAINER not found"; exit 1; }

# Whatever happens after the stop, start Metabase again if it was running.
restart_metabase() {
    if [ "$WAS_RUNNING" = true ] && [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" != true ]; then
        docker start "$CONTAINER" >/dev/null && log "started $CONTAINER"
    fi
}
trap restart_metabase EXIT

RC=0
START=$SECONDS
if [ "$WAS_RUNNING" = true ]; then
    docker stop -t 60 "$CONTAINER" >/dev/null || { log "ERROR: docker stop failed"; exit 1; }
    log "stopped $CONTAINER"
fi

if cp -a "$SRC" "${DEST}.part" && [ "$(stat -c %s "$SRC")" = "$(stat -c %s "${DEST}.part")" ]; then
    mv "${DEST}.part" "$DEST"
    log "copied $(du -h "$DEST" | cut -f1) -> $(basename "$DEST")"
else
    rm -f "${DEST}.part"
    log "ERROR: copy failed or incomplete"
    RC=1
fi

restart_metabase
trap - EXIT

if [ "$WAS_RUNNING" = true ]; then
    healthy=false
    for _ in $(seq 1 $((HEALTH_WAIT_SEC / 5))); do
        if curl -sf -o /dev/null "$HEALTH_URL"; then healthy=true; break; fi
        sleep 5
    done
    if [ "$healthy" = true ]; then
        log "Metabase healthy again ($((SECONDS - START))s since stop)"
    else
        log "ERROR: Metabase not healthy ${HEALTH_WAIT_SEC}s after start"
        RC=1
    fi
fi

# Rotation: newest $KEEP copies of this kind.
ls -1 "$DEST_DIR"/metabase-"${KIND}"-*.mv.db 2>/dev/null | sort -r | tail -n +$((KEEP + 1)) | while read -r old; do
    rm -f "$old" && log "rotated $(basename "$old")"
done

[ "$RC" -eq 0 ] && log "done" || log "FAILED"
exit "$RC"
