#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-module-namespace.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

base_modules='common state firewall runtime candidate lifecycle target request result probe family expansion stability profile extended quic udp udp_input preflight'
worker_modules='worker_messages worker_expansion_messages worker_stability_messages worker_extended_messages worker_quic_messages worker_udp_messages worker_budget worker_stage_machine worker_result worker_control worker_watchdog worker_flow'

[ -s "${WORKER}" ] || fail 'main Strategy Lab worker is missing'
[ ! -e "${MODULE_DIR}/worker_state_serialization.sh" ] || fail 'obsolete worker_state_serialization override module still exists'
if grep -Fq 'worker_state_serialization' "${WORKER}"; then
    fail 'main worker still sources the obsolete serialization override module'
fi

: > "${TMP}/definitions.tsv"
for module in ${base_modules} ${worker_modules}
do
    file="${MODULE_DIR}/${module}.sh"
    [ -s "${file}" ] || fail "main-worker module is missing: ${module}.sh"
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
    echo 'FAIL: jointly loaded Strategy Lab modules define duplicate function names:' >&2
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

shortlist_defs=$(grep -R -E -l '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}"/*.sh | wc -l | tr -d ' ')
[ "${shortlist_defs}" -eq 1 ] || fail "expected one strategy_lab_shortlist_build definition, found ${shortlist_defs}"
grep -Eq '^[[:space:]]*strategy_lab_shortlist_build[[:space:]]*\(\)' "${MODULE_DIR}/profile.sh" || fail 'profile.sh is not the sole shortlist owner'

eligibility_defs=$(grep -R -E -l '^[[:space:]]*worker_result_set_circular_eligibility[[:space:]]*\(\)' "${MODULE_DIR}"/*.sh | wc -l | tr -d ' ')
[ "${eligibility_defs}" -eq 1 ] || fail "expected one circular eligibility definition, found ${eligibility_defs}"
grep -Eq '^[[:space:]]*worker_result_set_circular_eligibility[[:space:]]*\(\)' "${MODULE_DIR}/worker_result.sh" || fail 'worker_result.sh is not the sole circular eligibility owner'

sh -n "${WORKER}"
echo 'PASS: jointly loaded Strategy Lab modules have a unique function namespace and no load-order control-flow overrides'
