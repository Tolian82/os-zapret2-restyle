#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
RESULT="${SCRIPT_DIR}/strategy_lab_py/result.py"
CANDIDATE_SPEC="${SCRIPT_DIR}/strategy_lab_py/candidate_spec.py"
WORKER="${SCRIPT_DIR}/strategy_lab_worker.sh"
PY_STAGE_ADAPTER="${SCRIPT_DIR}/strategy_lab_python_stage_adapter.sh"
RESULT_RUNNER="${SCRIPT_DIR}/strategy_lab_result_runner.sh"
PROFILE_ADAPTER="${SCRIPT_DIR}/strategy_lab_profile_candidate_adapter.sh"
LEGACY_REPLAY="${SCRIPT_DIR}/strategy_lab_profile_replay_runner.sh"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail 'Python 3.13 runtime is unavailable'

PYTHONPATH="${SCRIPT_DIR}" "${PYTHON}" - <<'PY'
from strategy_lab_py import result

fragment = "--out-range=-d8\n--lua-desync=multisplit:pos=1\n--lua-desync=syndata:blob=0x1603\n"
profile = result.build_profile("telegram.org", "domain", "tls13", 443, "", fragment)
assert "--filter-tcp=443\n" in profile
assert "--filter-l7=tls\n" in profile
assert "--hostlist-domains=telegram.org\n" in profile
assert "--out-range=-d8\n" in profile
assert "--out-range=-d10\n" not in profile
assert "--lua-desync=multisplit:pos=1\n" in profile
assert "--port=" not in profile and "--lua-init=" not in profile
result.validate_profile("telegram.org", "domain", "tls13", 443, "", profile)

ip_profile = result.build_profile("203.0.113.10", "ip", "tls13", 443, "", "--lua-desync=multisplit:pos=2\n")
assert "--ipset-ip=203.0.113.10\n" in ip_profile
assert "--hostlist-domains=" not in ip_profile
assert "--out-range=" not in ip_profile

udp_profile = result.build_profile(
    "udp.example", "domain", "udp", 5353, "203.0.113.53",
    "--lua-desync=ipfrag:udp=8\n",
)
assert "--filter-udp=5353\n" in udp_profile
assert "--ipset-ip=203.0.113.53\n" in udp_profile
assert "--filter-l7=" not in udp_profile

for bad in (
    "--port=9989\n--lua-desync=multisplit:pos=1\n",
    "--filter-tcp=443\n--lua-desync=multisplit:pos=1\n",
    "--new\n--lua-desync=multisplit:pos=1\n",
    "--hostlist-domains=evil.example\n--lua-desync=multisplit:pos=1\n",
    "--out-range=-d8\n--out-range=-d10\n--lua-desync=multisplit:pos=1\n",
):
    try:
        result.build_profile("telegram.org", "domain", "tls13", 443, "", bad)
    except result.ResultError:
        pass
    else:
        raise AssertionError(f"forbidden fragment was accepted: {bad!r}")
PY

grep -Fq 'strategy_lab_python_stage_adapter.sh' "${WORKER}" ||
    fail 'production worker does not route Stage 85 through the Python final-stage adapter'
grep -Fq '85)' "${PY_STAGE_ADAPTER}" ||
    fail 'Python final-stage adapter does not own Stage 85'
grep -Fq 'result "$@"' "${RESULT_RUNNER}" ||
    fail 'final result runner is not a thin Python launcher'
grep -Fq 'STRATEGY_LAB_CANDIDATE_SYSTEM_ADAPTER="${PROFILE_ADAPTER}"' "${RESULT_RUNNER}" ||
    fail 'exact profile replay does not use the narrow profile system adapter'
grep -Fq 'body.append(f"--hostlist={hostlist_path}")' "${CANDIDATE_SPEC}" ||
    fail 'Python CandidateSpec does not replace the validated static selector for exact replay'
grep -Fq 'STRATEGY_LAB_PROFILE_REPLAY_SELECTOR' "${PROFILE_ADAPTER}" &&
    fail 'profile system adapter still owns exact-selector replacement policy'
grep -Fq 'exec /bin/sh "${BASE_ADAPTER}" "$@"' "${PROFILE_ADAPTER}" ||
    fail 'profile system adapter does not delegate remaining candidate system actions'
[ ! -e "${LEGACY_REPLAY}" ] ||
    fail 'retired shell profile replay owner is still packaged'

"${PYTHON}" -m py_compile "${RESULT}" "${CANDIDATE_SPEC}"
sh -n "${PY_STAGE_ADAPTER}"
sh -n "${RESULT_RUNNER}"
sh -n "${PROFILE_ADAPTER}"

echo 'PASS: Python owns complete user-ready profile construction/validation and exact replay uses only the narrow system adapter'
