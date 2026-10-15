#!/usr/bin/env bash
# =============================================================================
# Cold copy of the Metabase H2 database (the full Metabase restore point).
# =============================================================================
# Runs on the HOST (needs docker and app_data/metabase_data; the data_platform container has
# neither). Stops the `metabase` container, copies metabase.db.mv.db while no process holds it,
# starts Metabase again and waits for /api/health. Metabase is unreachable for ~20 seconds.
# Once healthy, exports collections/cards/dashboards through the API next to the copy
# (metabase_export.py): its manifest.json holds the counts at the time of the copy, which a
# restore drill compares against the restored H2 file.
#
# Usage:
#   scripts/backup/metabase_cold_backup.sh nightly      # systemd timer (every night 00:30)
#   scripts/backup/metabase_cold_backup.sh pre-deploy   # by hand, before a deploy that writes to Metabase
#   scripts/backup/metabase_cold_backup.sh weekly       # previous timer kind, still accepted
#
# Copies: app_data/backups/metabase/metabase-<kind>-<YYYYmmdd-HHMMSS>.mv.db and its
# <copy>.export/ directory, newest METABASE_COLD_KEEP (default 7) kept per kind.
# Log: app_data/backups/metabase/cold-backup.log. Status: app_data/backups/status/metabase_cold.json.
# The API key is read from .env.docker (METABASE_API_KEY only, never printed); an export failure
# is a warning and does not fail the copy.
# Exit code 0 only when the copy is complete and Metabase is healthy again.
# Restore: docs/operations/deployment.md, section "Metabase".
set -uo pipefail

KIND="${1:-}"
case "$KIND" in nightly|weekly|pre-deploy) ;; *) echo "usage: $0 nightly|pre-deploy" >&2; exit 2 ;; esac

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONTAINER="${METABASE_CONTAINER:-metabase}"
SRC="${PROJECT_ROOT}/app_data/metabase_data/metabase.db.mv.db"
DEST_DIR="${PROJECT_ROOT}/app_data/backups/metabase"
KEEP="${METABASE_COLD_KEEP:-7}"
HEALTH_URL="${METABASE_HEALTH_URL:-http://127.0.0.1:3001/api/health}"
API_URL="${METABASE_API_URL:-http://127.0.0.1:3001}"
ENV_FILE="${METABASE_ENV_FILE:-${PROJECT_ROOT}/.env.docker}"
STATUS_FILE="${PROJECT_ROOT}/app_data/backups/status/metabase_cold.json"
HEALTH_WAIT_SEC=300
DEST="${DEST_DIR}/metabase-${KIND}-$(date +%Y%m%d-%H%M%S).mv.db"
LOG_FILE="${DEST_DIR}/cold-backup.log"

mkdir -p "$DEST_DIR"
log() { local msg; msg="$(date '+%F %T') [${KIND}] $*"; echo "$msg"; echo "$msg" >> "$LOG_FILE"; }

# Status file for the backup age check, written on every exit (also on early errors).
COPY_OK=false; HEALTHY=false; EXPORT_STATE=skipped
write_status() {
    local rc=$1
    mkdir -p "$(dirname "$STATUS_FILE")" 2>/dev/null
    python3 - "$STATUS_FILE" "$rc" "$KIND" "$((SECONDS - ${START:-$SECONDS}))" "$COPY_OK" "$HEALTHY" \
        "$EXPORT_STATE" "${DEST}" <<'PY' || log "WARNING: could not write status file"
import json, os, sys, tempfile, datetime
path, rc, kind, dur, copy_ok, healthy, export_state, dest = sys.argv[1:]
counts = None
try:
    with open(dest + ".export/manifest.json") as f:
        counts = json.load(f).get("counts")
except (OSError, ValueError):
    pass
status = {
    "ok": rc == "0", "state": "ok" if rc == "0" else "failed", "kind": kind,
    "ts": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    "duration_s": int(dur), "copy_ok": copy_ok == "true", "healthy": healthy == "true",
    "export": export_state, "copy": os.path.basename(dest) if copy_ok == "true" else None,
    "counts": counts,
}
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".metabase_cold.")
with os.fdopen(fd, "w") as f:
    json.dump(status, f, indent=2, sort_keys=True)
os.chmod(tmp, 0o644)
os.replace(tmp, path)
PY
}

[ -f "$SRC" ] || { log "ERROR: $SRC not found"; write_status 1; exit 1; }
WAS_RUNNING="$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" || WAS_RUNNING=missing
[ "$WAS_RUNNING" = missing ] && { log "ERROR: container $CONTAINER not found"; write_status 1; exit 1; }

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
    docker stop -t 60 "$CONTAINER" >/dev/null || { log "ERROR: docker stop failed"; write_status 1; exit 1; }
    log "stopped $CONTAINER"
fi

if cp -a "$SRC" "${DEST}.part" && [ "$(stat -c %s "$SRC")" = "$(stat -c %s "${DEST}.part")" ]; then
    mv "${DEST}.part" "$DEST"
    COPY_OK=true
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
        HEALTHY=true
        log "Metabase healthy again ($((SECONDS - START))s since stop)"
    else
        log "ERROR: Metabase not healthy ${HEALTH_WAIT_SEC}s after start"
        RC=1
    fi
fi

# Content counts at the time of the copy, through the API of the Metabase that just started.
# Only METABASE_API_KEY is taken from the env file (sourcing it would expand other values); the
# key goes to the exporter through its environment, never on a command line or in the log.
if [ "$COPY_OK" = true ] && [ "$HEALTHY" = true ]; then
    API_KEY="$(sed -n 's/^[[:space:]]*METABASE_API_KEY[[:space:]]*=[[:space:]]*//p' "$ENV_FILE" 2>/dev/null \
        | tail -1 | sed -e 's/[[:space:]]*$//' -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/")"
    if [ -z "$API_KEY" ]; then
        EXPORT_STATE=failed
        log "WARNING: METABASE_API_KEY not found in ${ENV_FILE}; no content export"
    elif EXPORT_OUT="$(METABASE_URL="$API_URL" METABASE_API_KEY="$API_KEY" \
            python3 "${PROJECT_ROOT}/scripts/backup/metabase_export.py" "${DEST}.export" 2>&1)"; then
        EXPORT_STATE=ok
        log "$(echo "$EXPORT_OUT" | grep 'metabase export:' | tail -1)"
    else
        EXPORT_STATE=failed
        rm -rf "${DEST}.export"
        log "WARNING: content export failed (copy is unaffected): $(echo "$EXPORT_OUT" | tail -1)"
    fi
    unset API_KEY
fi

# Rotation: newest $KEEP copies of this kind, with their export directories.
ls -1 "$DEST_DIR"/metabase-"${KIND}"-*.mv.db 2>/dev/null | sort -r | tail -n +$((KEEP + 1)) | while read -r old; do
    rm -rf "$old" "${old}.export" && log "rotated $(basename "$old")"
done

[ "$RC" -eq 0 ] && log "done" || log "FAILED"
write_status "$RC"
exit "$RC"
