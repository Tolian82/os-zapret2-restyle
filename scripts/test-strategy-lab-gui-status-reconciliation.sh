#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
LAUNCH="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret/strategy_lab/launch.sh"
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
CONTROLLER="${ROOT_DIR}/src/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/StrategyLabController.php"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

for file in "${LAUNCH}" "${VIEW}" "${CONTROLLER}"
do
    [ -s "${file}" ] || fail "missing Patch-8 surface: ${file}"
done

# The background worker must not inherit the launcher serialization lock. Circular
# already used the same isolation rule; the automated launcher now does too.
grep -Fq '"${TRANSACTION_SCRIPT}" strategy-lab "${_strategy_lab_job}" 9>&-' "${LAUNCH}" ||
    fail 'automated Strategy Lab daemon still inherits launcher lock FD 9'

# Empty/invalid configd output is a transport/read failure, not persisted job state.
[ "$(grep -Fc "'transient' => true" "${CONTROLLER}")" -ge 2 ] ||
    fail 'controller does not classify empty/invalid backend output as transient'
grep -Fq "'message' => 'Strategy Lab returned no output.'" "${CONTROLLER}" ||
    fail 'empty-output diagnostic contract changed unexpectedly'
grep -Fq "'message' => 'Strategy Lab returned invalid output.'" "${CONTROLLER}" ||
    fail 'invalid-output diagnostic contract changed unexpectedly'

# AJAX/network failures use the same transient channel. GUI state is rendered only from
# a validated persisted job snapshot and never falls back from state to transport status.
grep -Fq "done({status:'error', transient:true, message:ui.requestFailed + status})" "${VIEW}" ||
    fail 'AJAX errors are not marked transient'
grep -Fq 'function jobSnapshot(data)' "${VIEW}" || fail 'job snapshot validator is missing'
grep -Fq 'function transientReply(data)' "${VIEW}" || fail 'transient reply classifier is missing'
grep -Fq 'if (!jobSnapshot(data)) return false;' "${VIEW}" ||
    fail 'renderJob accepts non-persisted transport replies'
grep -Fq "String(data.state).toUpperCase()" "${VIEW}" ||
    fail 'visible Strategy Lab state is not derived from persisted state'
if grep -Fq "data.state || data.status || 'idle'" "${VIEW}"; then
    fail 'transport status can still masquerade as visible job state'
fi

# Active polling preserves the last valid view across transient reads and retries instead
# of rendering ERROR/0% from an empty reply. Reload discovery retries transient reads but
# accepts explicit idle without resurrecting retained terminal history.
grep -Fq 'function renderTransientStatus()' "${VIEW}" || fail 'transient status renderer is missing'
grep -Fq 'if (transientReply(data)) { renderTransientStatus(); setBusy(true); schedulePoll(pollStatus); return; }' "${VIEW}" ||
    fail 'active polling does not retry transient status reads'
grep -Fq 'function discoverActive(attempt)' "${VIEW}" || fail 'active reload discovery is missing'
grep -Fq "if (data.status === 'idle') { activeJobId=''; setBusy(false); return; }" "${VIEW}" ||
    fail 'reload discovery no longer distinguishes explicit idle'
grep -Fq 'discoverActive(0);' "${VIEW}" || fail 'Diagnostics does not use reconciled active discovery on load'

# Start presents an accepted job as queued immediately, then switches to authoritative
# persisted snapshots. Progress continues to prefer the persisted Python progress object.
grep -Fq "state:'queued'" "${VIEW}" || fail 'accepted job is not rendered optimistically as queued'
grep -Fq 'var progress = data.progress || {}, percent = Number(progress.percent);' "${VIEW}" ||
    fail 'GUI no longer prefers persisted progress percent'
grep -Fq "statusRetry:'Статус Strategy Lab временно недоступен. Повторная попытка…'" "${VIEW}" ||
    fail 'Russian transient status message is missing'
grep -Fq "statusRetry:'Strategy Lab status is temporarily unavailable. Retrying…'" "${VIEW}" ||
    fail 'English transient status message is missing'

sh -n "${LAUNCH}"
printf '%s\n' 'PASS: Strategy Lab GUI/status reconciliation keeps transport failures separate from persisted job state and preserves live progress/reload polling'
