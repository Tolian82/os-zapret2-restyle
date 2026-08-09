#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON="${STRATEGY_LAB_TEST_PYTHON:-python3.13}"
LAUNCHER="${SCRIPT_DIR}/strategy_lab_python_launcher.sh"
JQ=$(command -v jq || true)

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python 3.13 test interpreter is unavailable: ${PYTHON}"
[ -x "${JQ}" ] || fail 'jq is unavailable'

"${PYTHON}" -m py_compile \
    "${SCRIPT_DIR}/strategy_lab_py/resources.py" \
    "${SCRIPT_DIR}/strategy_lab_py/candidate_spec.py" \
    "${SCRIPT_DIR}/strategy_lab_py/candidate.py" \
    "${SCRIPT_DIR}/strategy_lab_py/family.py" \
    "${SCRIPT_DIR}/strategy_lab_py/compat.py"

grep -Fq 'candidate run' "${SCRIPT_DIR}/strategy_lab_candidate_runner.sh" || fail 'candidate runner is not a Python launcher'
grep -Fq 'family screen' "${SCRIPT_DIR}/strategy_lab_family_runner.sh" || fail 'family runner is not a Python launcher'
if grep -Fq 'strategy_lab_family_screen()' "${SCRIPT_DIR}/strategy_lab/family.sh"; then
    fail 'retired shell Stage-50 family owner is still present'
fi

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-python-candidate.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
JOBS="${TMP}/jobs"
JOB="job.test"
JOB_DIR="${JOBS}/${JOB}"
RUNTIME="${JOB_DIR}/candidate-runtime"
ENDPOINTS="${TMP}/endpoints.txt"
STRATEGY="${TMP}/candidate.args"
RESULT="${TMP}/candidate.json"
ADAPTER="${TMP}/adapter.sh"
DRILL="${TMP}/drill"
CURL="${TMP}/curl"
COUNTER_STATE="${TMP}/counter"
ACTIONS="${TMP}/actions"
LUA_DIR="${TMP}/lua"
FAKE_DIR="${TMP}/fake"
mkdir -p "${JOB_DIR}" "${LUA_DIR}" "${FAKE_DIR}"
for lua in zapret-lib.lua zapret-antidpi.lua zapret-auto.lua unrelated.lua
do
  printf '%s\n' '-- fixture' > "${LUA_DIR}/${lua}"
done
printf '%s\n' fake > "${FAKE_DIR}/unused.bin"
printf '%s\n' example.test > "${ENDPOINTS}"
printf '%s\n' '--lua-desync=multisplit:pos=1' > "${STRATEGY}"
printf '%s\n' 0 > "${COUNTER_STATE}"
: > "${ACTIONS}"

cat > "${DRILL}" <<'EOF'
#!/bin/sh
cat <<'OUT'
;; QUESTION SECTION:
;example.test. IN A
;; ANSWER SECTION:
example.test. 60 IN A 203.0.113.10
;; AUTHORITY SECTION:
ns.example.test. 60 IN A 198.51.100.99
OUT
EOF
chmod 0755 "${DRILL}"

cat > "${CURL}" <<'EOF'
#!/bin/sh
printf '%s\n' 'exit=0 remote_ip=203.0.113.10 http=1.1 code=206 bytes=1'
EOF
chmod 0755 "${CURL}"

cat > "${ADAPTER}" <<'EOF'
#!/bin/sh
set -eu
action="$1"; shift
printf '%s\n' "${action}" >> "${MOCK_ACTIONS}"
case "${action}" in
  cleanup|firewall-install-protocol|allow-access) exit 0 ;;
  wan) printf '%s\n' vtnet1 ;;
  launch)
    mkdir -p "${MOCK_RUNTIME}"
    if [ "${MOCK_FATAL:-0}" = 1 ]; then
      printf '%s\n' 'fatal: bind failed' > "${MOCK_RUNTIME}/dvtws2.log"
    else
      : > "${MOCK_RUNTIME}/dvtws2.log"
    fi
    ;;
  snapshot)
    printf '%s\n' '{"pid":4242,"executable":"/mock/dvtws2","command":"/mock/dvtws2 --port=9989","divert_port":9989,"process_identity":true,"socket_ready":true}'
    ;;
  counter)
    value=$(cat "${MOCK_COUNTER}")
    if [ "${value}" -eq 0 ]; then
      printf '%s\n' 1 > "${MOCK_COUNTER}"
      printf '%s\n' '0 0'
    else
      printf '%s\n' "$((value + 1))" > "${MOCK_COUNTER}"
      printf '%s\n' "$((value + 1)) $(((value + 1) * 64))"
    fi
    ;;
  *) exit 64 ;;
esac
EOF
chmod 0755 "${ADAPTER}"

run_candidate()
{
  MOCK_ACTIONS="${ACTIONS}" MOCK_RUNTIME="${RUNTIME}" MOCK_COUNTER="${COUNTER_STATE}" MOCK_FATAL="${1:-0}" \
  STRATEGY_LAB_JOBS_DIR="${JOBS}" \
  STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER="${ADAPTER}" \
  STRATEGY_LAB_LUA_DIR="${LUA_DIR}" \
  STRATEGY_LAB_FAKE_DIR="${FAKE_DIR}" \
  STRATEGY_LAB_DRILL_BIN="${DRILL}" \
  STRATEGY_LAB_CURL_BIN="${CURL}" \
  STRATEGY_LAB_RUNTIME_START_TIMEOUT=3 \
  STRATEGY_LAB_RUNTIME_READY_POLL=0.01 \
  STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
  sh "${LAUNCHER}" candidate run "${JOB}" "${ENDPOINTS}" "${RESULT}" c1 multisplit "${STRATEGY}" 1
}

run_candidate 0
"${JQ}" -e '
  .id=="c1" and .family=="multisplit" and .all_pass==true and
  (.candidate_spec.spec_id|startswith("cs1-")) and
  .candidate_spec.lua_instances[0].function=="multisplit" and
  .candidate_spec.ranges.out=="-d10" and
  (.resource_inventory_id|startswith("ri1-")) and
  ([.runtime_arguments[]|select(startswith("--lua-init="))]|length)==2 and
  ([.runtime_arguments[]|select(contains("zapret-auto.lua"))]|length)==0 and
  ([.runtime_arguments[]|select(contains("unrelated.lua"))]|length)==0 and
  .runtime.ready==true and .runtime.stable_checks==2 and
  (.endpoints|length)==1 and
  .endpoints[0].selected_ip=="203.0.113.10" and
  .endpoints[0].remote_ip=="203.0.113.10" and
  .endpoints[0].endpoint_match==true and
  .endpoints[0].firewall.intercepted==true and
  .endpoints[0].execution.returncode==0 and
  .endpoints[0].execution.timed_out==false
' "${RESULT}" >/dev/null || { cat "${RESULT}" >&2; fail 'Python candidate success evidence contract failed'; }
grep -Fq cleanup "${ACTIONS}" || fail 'candidate cleanup was not requested'
grep -Fq launch "${ACTIONS}" || fail 'candidate runtime launch was not requested'

printf '%s\n' 0 > "${COUNTER_STATE}"
: > "${ACTIONS}"
run_candidate 1
"${JQ}" -e '
  .all_pass==false and .error==true and
  .runtime.ready==false and
  (.runtime.fatal_reason|test("fatal: bind failed"))
' "${RESULT}" >/dev/null || { cat "${RESULT}" >&2; fail 'fatal runtime log was not rejected by Python readiness'; }

CATALOG="${TMP}/families.tsv"
ARGS_DIR="${TMP}/args"
FAMILY_RESULT="${TMP}/family.json"
FAKE_CANDIDATE="${TMP}/fake-candidate.sh"
mkdir -p "${ARGS_DIR}"
: > "${CATALOG}"
for id in f1 f2 f3 f4 f5 f6 f7
do
  printf '%s\t%s\t%s\t%s\n' "${id}" "family-${id}" 1 "${id}.args" >> "${CATALOG}"
  printf '%s\n' '--lua-desync=multisplit:pos=1' > "${ARGS_DIR}/${id}.args"
done
cat > "${FAKE_CANDIDATE}" <<'EOF'
#!/bin/sh
set -eu
output="$3"; id="$4"; family="$5"
if [ "${MOCK_TIMEOUT_ID:-}" = "${id}" ]; then sleep 2; fi
all=false
[ "${id}" != f2 ] || all=true
printf '{"id":"%s","family":"%s","strategy":"","endpoints":[],"all_pass":%s}\n' "${id}" "${family}" "${all}" > "${output}"
EOF
chmod 0755 "${FAKE_CANDIDATE}"

STRATEGY_LAB_JOBS_DIR="${JOBS}" \
STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}" \
STRATEGY_LAB_FAMILY_ARGS_DIR="${ARGS_DIR}" \
STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${FAKE_CANDIDATE}" \
STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT=1 \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
sh "${LAUNCHER}" family screen "${JOB}" "${ENDPOINTS}" "${FAMILY_RESULT}"
"${JQ}" -e '
  .total==7 and .completed==7 and (.families|length)==7 and
  [.families[].id]==["f1","f2","f3","f4","f5","f6","f7"] and
  .accepted==["family-f2"] and (.rejected|length)==6 and .all_pass==true
' "${FAMILY_RESULT}" >/dev/null || { cat "${FAMILY_RESULT}" >&2; fail 'Python family ordering/aggregation contract failed'; }

MOCK_TIMEOUT_ID=f1 \
STRATEGY_LAB_JOBS_DIR="${JOBS}" \
STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}" \
STRATEGY_LAB_FAMILY_ARGS_DIR="${ARGS_DIR}" \
STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${FAKE_CANDIDATE}" \
STRATEGY_LAB_SINGLE_CANDIDATE_TIMEOUT=0.2 \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
sh "${LAUNCHER}" family screen "${JOB}" "${ENDPOINTS}" "${FAMILY_RESULT}"
"${JQ}" -e '.families[0].id=="f1" and .families[0].timeout==true and .completed==7' "${FAMILY_RESULT}" >/dev/null ||
  fail 'Python family candidate timeout contract failed'

CANCEL="${JOB_DIR}/cancel.request"
: > "${CANCEL}"
set +e
STRATEGY_LAB_JOBS_DIR="${JOBS}" \
STRATEGY_LAB_FAMILY_CATALOG="${CATALOG}" \
STRATEGY_LAB_FAMILY_ARGS_DIR="${ARGS_DIR}" \
STRATEGY_LAB_SINGLE_CANDIDATE_RUNNER="${FAKE_CANDIDATE}" \
STRATEGY_LAB_PYTHON_BIN="${PYTHON}" \
sh "${LAUNCHER}" family screen "${JOB}" "${ENDPOINTS}" "${FAMILY_RESULT}"
rc=$?
set -e
[ "${rc}" -eq 125 ] || fail "pre-existing family cancellation returned ${rc}, expected 125"
rm -f "${CANCEL}"

echo 'PASS: Python 3.13 owns Strategy Lab candidate runtime/readiness/interception and ordered Stage-50 family screening'
