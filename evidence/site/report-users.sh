#!/usr/bin/env bash
# Accounts of the report site: one account per person and per area (Caddy basic_auth, bcrypt).
#
#   evidence/site/report-users.sh add <area> <user>      ask the password twice (not echoed), store its hash
#   evidence/site/report-users.sh remove <area> <user>   revoke the person's access to the area
#   evidence/site/report-users.sh list [<area>]          user names per area (never hashes)
#   evidence/site/report-users.sh reload                 apply the changes (caddy reload in report_site)
#
# Files: app_data/secrets/report_site/<area>.caddy, one line "<user> <bcrypt hash>" per person,
# mode 600 in a 700 directory, never in git. A person who may see two areas has a line in both.
# The password never appears on screen, in the shell history or in a process list: it is read with
# `read -s` and passed to `caddy hash-password` on stdin. Areas are those of evidence/site/Caddyfile
# (python3 -m analytics render site). Runbook: evidence/README.md ("Report site").
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
USERS_DIR="${REPORT_SITE_USERS_DIR:-$REPO/app_data/secrets/report_site}"
CADDYFILE="${REPORT_SITE_CADDYFILE:-$HERE/Caddyfile}"
HASH_CMD="${REPORT_SITE_HASH_CMD:-docker run --rm -i --network none caddy:alpine caddy hash-password}"
RELOAD_CMD="${REPORT_SITE_RELOAD_CMD:-docker exec report_site caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile}"
MIN_LENGTH=12

die() { echo "report-users: $*" >&2; exit 1; }

check_area() {
  [[ "$1" =~ ^[a-z][a-z0-9-]*$ ]] || die "invalid area '$1'"
  grep -q "import /etc/caddy/users/$1.caddy" "$CADDYFILE" \
    || die "area '$1' is not in $CADDYFILE (areas: $(areas | tr '\n' ' '))"
}

check_user() { [[ "$1" =~ ^[a-z0-9][a-z0-9._-]{1,31}$ ]] || die "user name must match [a-z0-9][a-z0-9._-]{1,31}"; }

areas() { sed -n 's#.*import /etc/caddy/users/\([a-z0-9-]*\)\.caddy.*#\1#p' "$CADDYFILE"; }

read_password() {
  local p1 p2
  if [ -t 0 ]; then
    read -rs -p "Password for $1 (min $MIN_LENGTH characters): " p1; echo >&2
    read -rs -p "Repeat: " p2; echo >&2
    [ "$p1" = "$p2" ] || die "the passwords differ"
  else
    IFS= read -r p1 || die "no password on stdin"
  fi
  [ "${#p1}" -ge "$MIN_LENGTH" ] || die "password shorter than $MIN_LENGTH characters"
  PASSWORD="$p1"
}

write_without() {  # write_without <file> <user> -> file minus the user's line (atomic, mode 600)
  local tmp
  tmp="$(mktemp "$1.XXXXXX")"
  chmod 600 "$tmp"
  if [ -f "$1" ]; then awk -v u="$2" '$1 != u' "$1" > "$tmp"; fi
  echo "$tmp"
}

cmd="${1:-}"
case "$cmd" in
  add)
    [ $# -eq 3 ] || die "usage: $0 add <area> <user>"
    check_area "$2"; check_user "$3"
    umask 077
    mkdir -p "$USERS_DIR" && chmod 700 "$USERS_DIR"
    read_password "$3"
    hash="$(printf '%s\n' "$PASSWORD" | $HASH_CMD 2>/dev/null | tail -n 1)" || true
    unset PASSWORD
    [[ "$hash" =~ ^\$2[aby]\$[0-9]{2}\$[./A-Za-z0-9]{53}$ ]] || die "hashing failed (is docker available?)"
    file="$USERS_DIR/$2.caddy"
    tmp="$(write_without "$file" "$3")"
    printf '%s %s\n' "$3" "$hash" >> "$tmp"
    unset hash
    mv -f "$tmp" "$file"
    echo "account '$3' set for area '$2'. Apply with: $0 reload"
    ;;
  remove)
    [ $# -eq 3 ] || die "usage: $0 remove <area> <user>"
    check_area "$2"; check_user "$3"
    file="$USERS_DIR/$2.caddy"
    [ -f "$file" ] && awk -v u="$3" '$1 == u {f=1} END {exit !f}' "$file" || die "no account '$3' in area '$2'"
    tmp="$(write_without "$file" "$3")"
    mv -f "$tmp" "$file"
    [ -s "$file" ] || echo "area '$2' has no account left: nobody can open it."
    echo "account '$3' removed from area '$2'. Apply with: $0 reload"
    ;;
  list)
    for area in $( [ $# -ge 2 ] && { check_area "$2"; echo "$2"; } || areas ); do
      users="$( [ -f "$USERS_DIR/$area.caddy" ] && awk '{print $1}' "$USERS_DIR/$area.caddy" | tr '\n' ' ' || true)"
      echo "$area: ${users:-(no account file: the site will not start)}"
    done
    ;;
  reload)
    $RELOAD_CMD && echo "report_site reloaded"
    ;;
  *)
    sed -n '2,15p' "$0"; exit 2 ;;
esac
