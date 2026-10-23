#!/bin/sh
# Standalone, operator-invoked inspection for the *installed* 0.5.7_10.
# This file is intentionally NOT a package lifecycle hook or an auto-repair.
# It does not load modules, change IPFW, start/stop services, or run pkg add.

set -u
umask 077

ID_BIN=${ID_BIN:-/usr/bin/id}
PKG_BIN=${PKG_BIN:-/usr/sbin/pkg}
LOCKF_BIN=${LOCKF_BIN:-/usr/bin/lockf}
KLDSTAT_BIN=${KLDSTAT_BIN:-/sbin/kldstat}
IPFW_BIN=${IPFW_BIN:-/sbin/ipfw}
PYTHON_BIN=${PYTHON_BIN:-/usr/local/bin/python3.13}
PS_BIN=${PS_BIN:-/bin/ps}
SERVICE_SCRIPT=${SERVICE_SCRIPT:-/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh}
COLD_INSPECT_BIN=${COLD_INSPECT_BIN:-/usr/local/opnsense/scripts/OPNsense/Zapret/backend/voice_live_inspect.py}
SHARED_APPLY_JOURNAL=${SHARED_APPLY_JOURNAL:-/var/db/zapret2/shared-apply/operation.json}
LIFECYCLE_LOCK_FILE=${LIFECYCLE_LOCK_FILE:-/var/run/zapret2-lifecycle.lock}
DVTWS_BIN=${DVTWS_BIN:-/usr/local/etc/zapret2/binaries/my/dvtws2}
SUPERVISOR_LOOP=${SUPERVISOR_LOOP:-/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh}

refuse()
{
    printf 'REFUSED: %s\nUPGRADE_AUTHORIZED=no\n' "$1" >&2
    exit 69
}

[ "$#" -eq 0 ] || refuse 'no arguments accepted'
for bin in "$ID_BIN" "$PKG_BIN" "$LOCKF_BIN" "$KLDSTAT_BIN" "$IPFW_BIN" "$PYTHON_BIN" "$PS_BIN" "$SERVICE_SCRIPT"; do
    [ -x "$bin" ] && [ ! -L "$bin" ] || refuse 'required executable unavailable or linked'
done
[ -r "$COLD_INSPECT_BIN" ] && [ ! -L "$COLD_INSPECT_BIN" ] || refuse 'old native inspector unavailable or linked'
[ -f "$SHARED_APPLY_JOURNAL" ] && [ -r "$SHARED_APPLY_JOURNAL" ] &&
[ ! -L "$SHARED_APPLY_JOURNAL" ] || refuse 'committed journal evidence unavailable or linked'
[ "$($ID_BIN -u 2>/dev/null)" = 0 ] || refuse 'run as root on the OPNsense appliance'

installed=$($PKG_BIN query '%v' os-zapret2-restyle 2>/dev/null) || refuse 'installed package identity unavailable'
[ "$installed" = 0.5.7_10 ] || refuse 'this probe is only for the installed 0.5.7_10'

(
    # Lock against the OLD native FD9 owner. The lock file is the only
    # possible on-disk side effect; no persistent runtime/journal mutations.
    "$LOCKF_BIN" -s -t 5 9 || exit 75

    cold_signature()
    {
        "$KLDSTAT_BIN" -q -m ipfw >/dev/null 2>&1
        [ "$?" -eq 1 ] || return 1
        "$KLDSTAT_BIN" -q -m ipdivert >/dev/null 2>&1
        [ "$?" -eq 1 ] || return 1
        ipfw_message=$(LC_ALL=C "$IPFW_BIN" -q list 2>&1)
        ipfw_rc=$?
        [ "$ipfw_rc" -eq 71 ] || return 1
        case "$ipfw_message" in
            *'retrieving config failed: Protocol not available'*) return 0 ;;
            *) return 1 ;;
        esac
    }

    cold_signature || exit 69
    "$SERVICE_SCRIPT" status >/dev/null 2>&1
    [ "$?" -eq 2 ] || exit 69

    inspection=$("$PYTHON_BIN" "$COLD_INSPECT_BIN" 2>/dev/null)
    [ "$?" -eq 2 ] || exit 69
    printf '%s\n' "$inspection" | "$PYTHON_BIN" -c '
import json,sys
try:
    x=json.load(sys.stdin)
    assert isinstance(x,dict)
    assert x.get("source")=="native-common"
    assert x.get("state")=="foreign-or-modified-rules"
    assert x.get("condition")=="common-stopped-with-kernel-objects"
    assert x.get("can_activate") is False
    assert isinstance(x.get("runtime"),dict)
    assert x["runtime"].get("state")=="stopped"
except (ValueError,TypeError,KeyError,AssertionError):
    sys.exit(1)
' || exit 69

    # Additional independent exact-executable census. A missing PID file
    # alone is not evidence that an orphan dvtws2 engine is absent.
    processes=$("$PS_BIN" ax -o pid= -o command= 2>/dev/null) || exit 69
    printf '%s\n' "$processes" | awk -v expected="$DVTWS_BIN" -v monitor="$SUPERVISOR_LOOP" '
        $1 ~ /^[0-9]+$/ && $2 == expected { found=1 }
        $1 ~ /^[0-9]+$/ { for (i=2; i<=NF; i++) if ($i == monitor) found=1 }
        END { exit (found ? 1 : 0) }
    ' || exit 69

    # A fresh read prevents one changed kernel/service state being mistaken
    # for two independent compatible observations within original FD9.
    cold_signature || exit 69
    "$SERVICE_SCRIPT" status >/dev/null 2>&1
    [ "$?" -eq 2 ] || exit 69

    printf 'PACKAGE=0.5.7_10\nDIAGNOSIS=cold-ipfw-committed-stopped\nUPGRADE_AUTHORIZED=no\nNEXT=owner-reviewed-recovery-required\n'
    exit 0
) 9>"$LIFECYCLE_LOCK_FILE"
rc=$?
case "$rc" in
    0) exit 0 ;;
    75) refuse 'the native lifecycle is busy; no diagnosis established' ;;
    *) refuse 'native ownership or exact cold-IPFW state could not be verified' ;;
esac
