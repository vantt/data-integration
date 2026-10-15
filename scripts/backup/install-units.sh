#!/usr/bin/env bash
# Render the systemd user units of the backup tooling and install them.
#
# Templates live in scripts/backup/systemd/*.in and use @FG_PROJECT_ROOT@ for the checkout
# path, so no unit carries a hard-coded home directory.
#
# Usage:
#   scripts/backup/install-units.sh [--project-root DIR] [--unit-dir DIR] [--no-enable] [TIMER...]
#
#   --project-root DIR  checkout the units run from (default: the checkout holding this script)
#   --unit-dir DIR      where to write the units (default: ~/.config/systemd/user). With a
#                       directory other than the default, nothing is reloaded or enabled
#                       (render-only, used by tests and reviews)
#   --no-enable         write the units and daemon-reload, but do not enable/start timers
#   TIMER...            timers to enable --now (default: every *.timer rendered)
#
# Prints each rendered unit. Warns when lingering is off for the user (timers would only run
# while the user is logged in).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEFAULT_UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
UNIT_DIR="$DEFAULT_UNIT_DIR"
ENABLE=true
TIMERS=()

while [ "$#" -gt 0 ]; do
    case "$1" in
        --project-root) PROJECT_ROOT="$(cd "${2:?--project-root needs a directory}" && pwd)"; shift 2 ;;
        --unit-dir) UNIT_DIR="${2:?--unit-dir needs a directory}"; shift 2 ;;
        --no-enable) ENABLE=false; shift ;;
        -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
        -*) echo "install-units: unknown option $1" >&2; exit 2 ;;
        *) TIMERS+=("$1"); shift ;;
    esac
done

case "$PROJECT_ROOT" in
    *[[:space:]]*|*@*) echo "install-units: project root must not contain spaces or '@': $PROJECT_ROOT" >&2; exit 2 ;;
esac
[ -x "$PROJECT_ROOT/scripts/backup/metabase_cold_backup.sh" ] || {
    echo "install-units: $PROJECT_ROOT is not a checkout of this repo (scripts/backup/metabase_cold_backup.sh missing)" >&2
    exit 2
}

mkdir -p "$UNIT_DIR"
RENDERED=()
for tpl in "$SCRIPT_DIR"/systemd/*.in; do
    name="$(basename "$tpl" .in)"
    sed "s|@FG_PROJECT_ROOT@|${PROJECT_ROOT}|g" "$tpl" > "$UNIT_DIR/$name.tmp"
    if grep -q '@[A-Z_]*@' "$UNIT_DIR/$name.tmp"; then
        rm -f "$UNIT_DIR/$name.tmp"
        echo "install-units: unrendered placeholder left in $name" >&2
        exit 1
    fi
    mv "$UNIT_DIR/$name.tmp" "$UNIT_DIR/$name"
    RENDERED+=("$name")
    echo "rendered $UNIT_DIR/$name"
done

if [ "$UNIT_DIR" != "$DEFAULT_UNIT_DIR" ]; then
    echo "install-units: render-only ($UNIT_DIR is not the user unit directory); nothing enabled"
    exit 0
fi

systemctl --user daemon-reload
if [ "$ENABLE" = true ]; then
    if [ "${#TIMERS[@]}" -eq 0 ]; then
        for u in "${RENDERED[@]}"; do case "$u" in *.timer) TIMERS+=("$u") ;; esac; done
    fi
    for t in "${TIMERS[@]}"; do
        systemctl --user enable --now "$t"
        echo "enabled $t"
    done
    systemctl --user list-timers --no-pager "${TIMERS[@]}" || true
fi

if [ "$(loginctl show-user "$(id -un)" -p Linger --value 2>/dev/null)" != yes ]; then
    echo "WARNING: lingering is off for $(id -un): timers run only while the user is logged in" >&2
    echo "         enable it with: sudo loginctl enable-linger $(id -un)" >&2
fi
