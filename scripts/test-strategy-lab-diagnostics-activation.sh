#!/bin/sh
set -eu
ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
DIAGNOSTICS="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/DiagnosticsController.php"
LAB="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"
CIRCULAR="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/CircularController.php"
ACTIONS="${ROOT_DIR}/src/opnsense/service/conf/actions.d/actions_zapret.conf"
LEGACY="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/blockcheck.sh"
SHELL_VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/strategy_lab_shell.volt"
MAKEFILE="${ROOT_DIR}/Makefile"

fail(){ echo "FAIL: $*" >&2; exit 1; }

[ ! -e "${LEGACY}" ] || fail 'legacy blockcheck wrapper remains packaged'
[ ! -e "${SHELL_VIEW}" ] || fail 'dormant Strategy Lab shell remains packaged'
! grep -Fq 'blockcheckAction' "${DIAGNOSTICS}" || fail 'synchronous blockcheck API remains'
! grep -Fq '[blockcheck]' "${ACTIONS}" || fail 'synchronous blockcheck configd action remains'
! grep -Fq '/api/zapret/diagnostics/blockcheck' "${VIEW}" || fail 'GUI still calls synchronous blockcheck API'
! grep -Fq 'timeout: 600000' "${VIEW}" || fail 'legacy ten-minute AJAX timeout remains'

grep -Fq '/api/zapret/strategy_lab/start' "${VIEW}" || fail 'Strategy Lab start call missing'
grep -Fq '/api/zapret/strategy_lab/status' "${VIEW}" || fail 'Strategy Lab status call missing'
grep -Fq '/api/zapret/strategy_lab/cancel' "${VIEW}" || fail 'Strategy Lab cancel call missing'
grep -Fq '/api/zapret/strategy_lab/result' "${VIEW}" || fail 'Strategy Lab result call missing'
grep -Fq 'setTimeout(pollStatus, 1000)' "${VIEW}" || fail 'one-second asynchronous polling missing'
grep -Fq 'renderStages(data)' "${VIEW}" || fail 'live stage rendering missing'
grep -Fq 'renderShortlist(data)' "${VIEW}" || fail 'shortlist rendering missing'
grep -Fq '/api/zapret/circular/start' "${VIEW}" || fail 'circular start control missing'
grep -Fq '/api/zapret/circular/status' "${VIEW}" || fail 'circular status control missing'
grep -Fq '/api/zapret/circular/stop' "${VIEW}" || fail 'circular stop control missing'

grep -Fq "'strategy_lab_start'" "${LAB}" || fail 'Strategy Lab backend start action missing'
grep -Fq "'strategy_lab_result'" "${LAB}" || fail 'Strategy Lab backend result action missing'
grep -Fq "'strategy_lab_circular_start'" "${CIRCULAR}" || fail 'circular backend start action missing'
grep -Fq "'strategy_lab_circular_stop'" "${CIRCULAR}" || fail 'circular backend stop action missing'

plugin_revision=$(awk -F= '
    /^PLUGIN_REVISION=/ {
        gsub(/[[:space:]]/, "", $2)
        print $2
        exit
    }
' "${MAKEFILE}")
case "${plugin_revision}" in
    ''|*[!0-9]*) fail 'package revision is not a positive integer' ;;
esac
[ "${plugin_revision}" -ge 15 ] || fail 'package revision predates Strategy Lab activation'

echo 'PASS: Diagnostics uses asynchronous Strategy Lab and the synchronous Blockcheck path is retired'
