#!/bin/sh
set -eu
SOURCE=${DEV065_SOURCE:-"$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"}
ROOT=$(mktemp -d /tmp/dev065.XXXXXXXX) || exit 1
trap 'rm -rf "$ROOT"' EXIT HUP INT TERM
fail() { echo "FAIL_DEV065: $*" >&2; exit 1; }
sed -n '/^original_fd9_lifecycle_transition()$/,/^}$/p' "$SOURCE" > "$ROOT/helper.sh"
[ -s "$ROOT/helper.sh" ] || fail 'helper absent'
[ "$(grep -Ec '^original_fd9_lifecycle_transition\(\)$' "$SOURCE")" -eq 1 ] || fail 'duplicate helper'
sh -n "$ROOT/helper.sh" || fail 'shell syntax'
for spec in 'strategy_lab_internal_dispatch stop lab' 'strategy_lab_internal_dispatch start lab' 'pkg_update_prepare_service stop pkg-update' 'pkg_update_finish_service start pkg-update'; do
    set -- $spec
    sed -n "/^$1()$/,/^}$/p" "$SOURCE" > "$ROOT/caller.sh"
    grep -Fq "original_fd9_lifecycle_transition $2 $3" "$ROOT/caller.sh" || fail "independent owner selector in $1"
    if grep -Eq '^[[:space:]]*(shared_apply_boot_service|shared_apply_stop_service|start_service|stop_service)([[:space:]]|$)' "$ROOT/caller.sh"; then
        fail "duplicated physical transition in $1"
    fi
done
. "$ROOT/helper.sh"
LOG="$ROOT/log"
: > "$LOG"
OWNER='committed aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa strategies'
HAS_RECORD=1
WAN_OK=1
GUARD_OK=1
STRATEGY_LAB_LIFECYCLE_OWNER=1
strategy_lab_lock_owner_valid() { [ "$STRATEGY_LAB_LIFECYCLE_OWNER" = 1 ]; }
wan_first_service() { [ "$WAN_OK" = 1 ] || return 69; echo "wan:$1" >> "$LOG"; }
shared_apply_has_record_service() { [ "$HAS_RECORD" = 1 ]; }
shared_apply_inspect_service() { printf '%s\n' "$OWNER"; }
preflight_shared_apply_journal() { [ "$GUARD_OK" = 1 ] || return 69; echo "guard:${1:-legacy}" >> "$LOG"; }
shared_apply_boot_service() { echo "native-start:$1" >> "$LOG"; }
shared_apply_stop_service() { echo "native-stop:$1" >> "$LOG"; }
start_service() { echo 'legacy-start' >> "$LOG"; }
stop_service() { echo 'legacy-stop' >> "$LOG"; }
exec 9>"$ROOT/lock"
original_fd9_lifecycle_transition start lab
original_fd9_lifecycle_transition stop lab
original_fd9_lifecycle_transition start pkg-update
original_fd9_lifecycle_transition stop pkg-update
[ "$(grep -c 'native-start:' "$LOG")" -eq 2 ] || fail 'common start'
[ "$(grep -c 'native-stop:' "$LOG")" -eq 2 ] || fail 'common stop'
OWNER='prepared aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa strategies'
if original_fd9_lifecycle_transition stop lab; then fail 'pending Lab owner'; fi
if original_fd9_lifecycle_transition start pkg-update; then fail 'pending pkg owner'; fi
HAS_RECORD=0
original_fd9_lifecycle_transition start lab
original_fd9_lifecycle_transition stop lab
original_fd9_lifecycle_transition start pkg-update
original_fd9_lifecycle_transition stop pkg-update
[ "$(grep -c 'legacy-start' "$LOG")" -eq 2 ] || fail 'legacy start'
[ "$(grep -c 'legacy-stop' "$LOG")" -eq 2 ] || fail 'legacy stop'
WAN_OK=0
if original_fd9_lifecycle_transition start lab; then fail 'WAN bypass'; fi
WAN_OK=1
GUARD_OK=0
if original_fd9_lifecycle_transition stop lab; then fail 'journal bypass'; fi
GUARD_OK=1
STRATEGY_LAB_LIFECYCLE_OWNER=0
if original_fd9_lifecycle_transition stop lab; then fail 'Lab owner bypass'; fi
if original_fd9_lifecycle_transition restart pkg-update; then fail 'unknown action'; fi
printf '%s\n' 'PASS_DEV065_ORIGINAL_FD9_LAB_PKG_SINGLE_TRANSITION'
