#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
PY_ORCHESTRATOR="${SCRIPT_DIR}/strategy_lab_py/orchestrator.py"
PY_RESULT="${SCRIPT_DIR}/strategy_lab_py/result.py"
PY_STAGE_ADAPTER="${SCRIPT_DIR}/strategy_lab_python_stage_adapter.sh"
RESULT_RUNNER="${SCRIPT_DIR}/strategy_lab_result_runner.sh"
PROFILE_ADAPTER="${SCRIPT_DIR}/strategy_lab_profile_candidate_adapter.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-module-namespace.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

base_modules='common state firewall runtime candidate lifecycle target request result probe family expansion stability profile extended quic udp udp_input preflight'
worker_modules='worker_messages worker_expansion_messages worker_stability_messages worker_extended_messages worker_quic_messages worker_udp_messages worker_budget worker_control worker_watchdog worker_flow'

[ -s "${WORKER}" ] || fail 'main Strategy Lab worker is missing'
[ -s "${PY_ORCHESTRATOR}" ] || fail 'Python automated orchestrator is missing'
[ -s "${PY_RESULT}" ] || fail 'Python final-result owner is missing'
[ -s "${PY_STAGE_ADAPTER}" ] || fail 'Python final-stage adapter is missing'
[ -s "${RESULT_RUNNER}" ] || fail 'Python final-result runner is missing'
[ -s "${PROFILE_ADAPTER}" ] || fail 'exact-profile system adapter is missing'

[ ! -e "${MODULE_DIR}/worker_state_serialization.sh" ] || fail 'obsolete worker_state_serialization override module still exists'
[ ! -e "${MODULE_DIR}/worker_stage_machine.sh" ] || fail 'retired shell automated stage-machine owner still exists'
[ ! -e "${MODULE_DIR}/worker_result.sh" ] || fail 'retired shell automated result owner still exists'
[ ! -e "${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh" ] || fail 'retired shell final replay owner still exists'

if grep -Fq 'worker_state_serialization' "${WORKER}"; then
    fail 'main worker still sources the obsolete serialization override module'
fi
if grep -Eq 'worker_(stage_machine|result)' "${WORKER}"; then
    fail 'main worker still references a retired automated shell owner'
fi

grep -Fq 'exec "${PYTHON_LAUNCHER}" orchestrate "${JOB_ID}"' "${WORKER}" ||
    fail 'main worker does not enter the Python automated orchestrator'
grep -Fq 'strategy_lab_python_stage_adapter.sh' "${WORKER}" ||
    fail 'main worker does not select the Python final-stage adapter'
grep -Fq 'def build_shortlist(' "${PY_RESULT}" ||
    fail 'Python final-result module does not own shortlist construction'
grep -Fq 'def circular_eligibility(' "${PY_RESULT}" ||
    fail 'Python final-result module does not own automated circular eligibility'

: > "${TMP}/definitions.tsv"
for module in ${base_modules} ${worker_modules}
do
    file="${MODULE_DIR}/${module}.sh"
    [ -s "${file}" ] || fail "remaining shell compatibility/system module is missing: ${module}.sh"
    awk -v file="${module}.sh" '
        /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\(\)[[:space:]]*\{/ {
            line=$0
            sub(/^[[:space:]]*/, "", line)
            sub(/[[:space:]]*\(\).*/, "", line)
            print line "\t" file
            next
        }
        /^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*\(\)[[:space:]]*$/ {
            line=$0
            gsub(/[[:space:]]/, "", line)
            sub(/\(\)$/, "", line)
            print line "\t" file
        }
    ' "${file}" >> "${TMP}/definitions.tsv"
done

cut -f1 "${TMP}/definitions.tsv" | sort | uniq -d > "${TMP}/duplicates"
if [ -s "${TMP}/duplicates" ]; then
    echo 'FAIL: remaining shell compatibility/system modules define duplicate function names:' >&2
    while IFS= read -r name
    do
        awk -F '\t' -v name="${name}" '$1==name {print "  " $1 " -> " $2}' "${TMP}/definitions.tsv" >&2
    done < "${TMP}/duplicates"
    exit 1
fi

for file in expansion.sh stability.sh extended.sh quic.sh udp.sh
do
    if grep -Eq '^[[:space:]]*strategy_lab_skip_(unfinished|remaining)[[:space:]]*\(\)' "${MODULE_DIR}/${file}"; then
        fail "obsolete skip hook remains in ${file}"
    fi
done

# profile.sh may retain one compatibility helper for private/system consumers, but it is no
# longer the automated Stage-85 owner and no second shell definition may appear.
shortlist_defs=$(grep -R -E -l '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}"/*.sh | wc -l | tr -d ' ')
[ "${shortlist_defs}" -le 1 ] || fail "multiple shell shortlist compatibility definitions remain: ${shortlist_defs}"
if [ "${shortlist_defs}" -eq 1 ]; then
    grep -Eq '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}/profile.sh" ||
        fail 'unexpected shell shortlist compatibility definition outside profile.sh'
fi

eligibility_defs=$(grep -R -E -l '^[[:space:]]*worker_result_set_circular_eligibility[[:space:]]*\(\)' "${MODULE_DIR}"/*.sh | wc -l | tr -d ' ')
[ "${eligibility_defs}" -eq 0 ] || fail "retired shell automated circular-eligibility definition remains"

grep -Fq '85)' "${PY_STAGE_ADAPTER}" || fail 'Python final-stage adapter does not intercept Stage 85'
grep -Fq 'eligibility)' "${PY_STAGE_ADAPTER}" || fail 'Python final-stage adapter does not intercept automated eligibility'
grep -Fq 'result "$@"' "${RESULT_RUNNER}" || fail 'result runner is not a thin Python launcher'
grep -Fq 'exec /bin/sh "${BASE_ADAPTER}" "$@"' "${PROFILE_ADAPTER}" ||
    fail 'exact-profile adapter does not delegate remaining system actions to the canonical candidate adapter'

sh -n "${WORKER}"
sh -n "${PY_STAGE_ADAPTER}"
sh -n "${RESULT_RUNNER}"
sh -n "${PROFILE_ADAPTER}"

echo 'PASS: remaining shell compatibility/system modules have a unique namespace while Python exclusively owns automated stage/result policy'
