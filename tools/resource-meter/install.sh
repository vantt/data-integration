#!/usr/bin/env bash
# Install, upgrade or remove the resource-meter systemd unit on this host.
#
# Build first, as your normal user (root has no Rust toolchain):
#   cd tools/resource-meter && cargo build --release
# Then, with sudo:
#   sudo tools/resource-meter/install.sh                       install or upgrade, start
#   sudo tools/resource-meter/install.sh --uninstall           stop, disable, remove binary and unit
#   sudo tools/resource-meter/install.sh --uninstall --purge   ... and delete /var/lib/resource-meter
#
# Installing touches no container and restarts nothing but this unit. It refuses to run
# during the nightly window (02:30-04:00) unless --force is given.
set -euo pipefail

UNIT=resource-meter.service
BIN_DST=/usr/local/bin/resource-meter
UNIT_DST=/etc/systemd/system/$UNIT
DATA=/var/lib/resource-meter

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
BIN_SRC=$HERE/target/release/resource-meter
UNIT_SRC=$HERE/$UNIT

usage() {
    sed -n '2,12p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
}

die() {
    echo "install.sh: $*" >&2
    exit 1
}

uninstall=no
purge=no
force=no
for arg in "$@"; do
    case "$arg" in
        --uninstall) uninstall=yes ;;
        --purge) purge=yes ;;
        --force) force=yes ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done
[[ $purge == yes && $uninstall == no ]] && die "--purge only goes with --uninstall"
[[ $EUID -eq 0 ]] || die "run with sudo"

hhmm=$(TZ=Asia/Ho_Chi_Minh date +%H%M)
if [[ $force == no && 10#$hhmm -ge 230 && 10#$hhmm -lt 400 ]]; then
    die "it is $(TZ=Asia/Ho_Chi_Minh date +%H:%M) Asia/Saigon, inside the nightly window 02:30-04:00; retry later or pass --force"
fi

if [[ $uninstall == yes ]]; then
    if systemctl list-unit-files "$UNIT" --no-legend 2>/dev/null | grep -q "^$UNIT"; then
        systemctl disable --now "$UNIT"
    fi
    rm -f "$UNIT_DST" "$BIN_DST"
    systemctl daemon-reload
    if [[ $purge == yes ]]; then
        rm -rf "$DATA"
        echo "removed $UNIT, $BIN_DST and $DATA"
    else
        echo "removed $UNIT and $BIN_DST (data kept in $DATA; --uninstall --purge deletes it)"
    fi
    exit 0
fi

[[ -f $UNIT_SRC ]] || die "missing $UNIT_SRC"
[[ -x $BIN_SRC ]] || die "missing $BIN_SRC; build it first as your user: cd $HERE && cargo build --release"
"$BIN_SRC" --help >/dev/null || die "$BIN_SRC does not run on this host"

install -m 0755 -o root -g root "$BIN_SRC" "$BIN_DST"
install -m 0644 -o root -g root "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
systemctl enable "$UNIT"
# restart (not start) so an upgrade picks up the new binary.
systemctl restart "$UNIT"
sleep 3
systemctl --no-pager --lines=5 status "$UNIT" || die "$UNIT did not start; see: journalctl -u $UNIT"
echo
echo "installed. In a minute: resource-meter status ; in 15 minutes: resource-meter report"
