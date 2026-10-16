#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TMP=$(mktemp -d /tmp/zapret-php-fd9.XXXXXXXX)
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
LOCK="$TMP/native.lock"
FOREIGN="$TMP/foreign.lock"
TEST="$ROOT/scripts/test-shared-apply-lock.php"
touch "$LOCK" "$FOREIGN"
chmod 600 "$LOCK" "$FOREIGN"
command -v flock >/dev/null || exit 1
sh -c 'exec 9>"$1"; flock -x 9; php "$2" held "$1"' sh "$LOCK" "$TEST"
sh -c 'exec 9>"$1"; php "$2" refuse "$1"' sh "$LOCK" "$TEST"
sh -c 'exec 9>"$1"; flock -x 9; php "$2" refuse "$3"' sh "$FOREIGN" "$TEST" "$LOCK"
ln -s "$LOCK" "$TMP/link"
sh -c 'exec 9>"$1"; flock -x 9; php "$2" refuse "$3"' sh "$LOCK" "$TEST" "$TMP/link"
php "$TEST" refuse "$LOCK"
echo 'PASS: native PHP Config requires original FD9, not a root-only caller'
