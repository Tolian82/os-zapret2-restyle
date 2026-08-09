#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
MODULE_DIR="${SCRIPT_DIR}/strategy_lab"
RUNNER="${SCRIPT_DIR}/strategy_lab_family_runner.sh"
STRATEGY_LAB_JQ=$(command -v jq || true)

[ -x "${RUNNER}" ] || { echo 'FAIL: Strategy Lab family runner is unavailable' >&2; exit 1; }
[ -x "${STRATEGY_LAB_JQ}" ] || { echo 'FAIL: jq is unavailable' >&2; exit 1; }
[ -x /usr/bin/timeout ] || { echo 'FAIL: default timeout binary is unavailable' >&2; exit 1; }

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-family-timeout.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM

JOBS="${TMP}/jobs"
JOB="job.test"
JOB_DIR="${JOBS}/${JOB}"
ARGS_DIR="${TMP}/args"
CATALOG="${TMP}/families.tsv"
ENDPOINTS="${TMP}/endpoints.txt"
RESULT="${TMP}/result.json"
FAKE_RUNNER="${TMP}/candidate.sh"

mkdir -p "${JOB_DIR}" "${ARGS_DIR}" "${TMP}/lua"
for lua in zapret-lib.lua zapret-antidpi.lua
do
    printf '%s\n' '-- fixture' > "${TMP}/lua/${lua}"
done
printf '%s\n' 'rutracker.org' > "${ENDPOINTS}"
: > "${CATALOG}"

for id in f1 f2 f3 f4 f5 f6 f7
do
    printf '%s\t%s\t%s\t%s\n' "${id}" "family-${id}" '-' "${id}.args" >> "${CATALOG}"
    printf '%s\n' '--filter-tcp=443' > "${ARGS_DIR}/${id}.args"
done

cat > "${FAKE_RUNNER}" <<'EOF'
#!/bin/sh
set -eu
output="$3"
id="$4"
family="$5"
printf '{"id":"%s","family":"%s","strategy":"","endpoints":[],"all_pass":false}\n' \
    "${id}" "${family}" > "${output}"
EOF
chmod +x "${FAKE_RUNNER}"

# The production runner enables set -u and does not source request.sh. The family module
# therefore must own a safe default for STRATEGY_LAB_TIMEOUT_BIN rather than relying on
# an unrelated module or caller environment.
env -u STRATEGY_LAB_TIMEOUT_BIN \
    SCRIPT_DIR="${SCRIPT_DIR}" \
    MODULE_DIR="${MODULE_DIR}" \
    STRATEGY_LAB_JQ="${STRATEGY_LAB_JQ}" \
    STRATEGY_LAB_JOBS_DIR="${JOBS}" \
    STRATEGY_LAB_LUA_DIR="${TMP}/lua" \
    STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}" \
    STRATEGY_LAB_FAMILY_ARGS_DIR="${ARGS_DIR}" \
    STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${FAKE_RUNNER}" \
    STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT=2 \
    STRATEGY_LAB_PYTHON_BIN="${STRATEGY_LAB_TEST_PYTHON:-python3.13}" \
    sh "${RUNNER}" "${JOB}" "${ENDPOINTS}" "${RESULT}"

"${STRATEGY_LAB_JQ}" -e '
    .total == 7 and
    .completed == 7 and
    (.families | length) == 7 and
    (.rejected | length) == 7 and
    .all_pass == false
' "${RESULT}" >/dev/null || {
    echo 'FAIL: family runner did not complete all seven families under set -u' >&2
    cat "${RESULT}" >&2
    exit 1
}

echo 'PASS: native-graph Strategy Lab family runner owns its timeout default under set -u'
