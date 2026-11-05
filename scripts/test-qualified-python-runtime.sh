#!/bin/sh
# Native Python policy/exec regression, fully isolated from service and pkg.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUNTIME="${ROOT}/src/opnsense/scripts/OPNsense/Zapret/python_runtime.sh"
POLICY="${ROOT}/compatibility.json"
PYTHON=${ZAPRET_TEST_PYTHON:-python3.13}
TMP=$(mktemp -d "${TMPDIR:-/tmp}/zapret-qualified-python.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
fail() { echo "FAIL: $*" >&2; exit 1; }

[ -x "${RUNTIME}" ] || fail "native launcher is not executable"
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python test interpreter is missing"
BIN=$(command -v "${PYTHON}")
sh -n "${RUNTIME}"

run()
{
    ZAPRET_PYTHON_BIN="${BIN}" ZAPRET_PYTHON_POLICY="${POLICY}" "${RUNTIME}" "$@"
}

[ -z "$(run --check)" ] || fail "policy preflight wrote to machine-readable stdout"
[ "$(run -c 'import sys; print("json-clean")')" = json-clean ] ||
    fail "policy launcher broke stdout or -c argv"
[ "$(run -c 'import sys; print(sys.argv[1])' 'argument preserved')" = 'argument preserved' ] ||
    fail "Python argv was changed"
[ "$(run -c 'import os; os.fstat(9); print("fd9-inherited")' 9>"${TMP}/fd9")" = fd9-inherited ] ||
    fail "native exec did not preserve inherited FD9"

if ZAPRET_PYTHON_BIN="${TMP}/missing" ZAPRET_PYTHON_POLICY="${POLICY}" "${RUNTIME}" --check >"${TMP}/out" 2>"${TMP}/err"; then
    fail "missing explicit Python was accepted"
fi
[ ! -s "${TMP}/out" ] || fail "runtime error contaminated stdout"
grep -Fq 'interpreter is not executable' "${TMP}/err" || fail "missing Python diagnostic"

if ZAPRET_PYTHON_BIN="${BIN}" ZAPRET_PYTHON_POLICY="${TMP}/missing-policy" "${RUNTIME}" --check >"${TMP}/out" 2>"${TMP}/err"; then
    fail "missing policy was accepted"
fi
[ ! -s "${TMP}/out" ] || fail "missing-policy error contaminated stdout"
grep -Fq 'compatibility policy is unreadable' "${TMP}/err" || fail "missing policy diagnostic"

"${BIN}" - "${POLICY}" "${TMP}/unsupported.json" <<'PY'
import json
import sys
from pathlib import Path
p = json.loads(Path(sys.argv[1]).read_text())
p["supported_platforms"][0]["python"]["supported"] = ["3.12"]
Path(sys.argv[2]).write_text(json.dumps(p))
PY
if ZAPRET_PYTHON_BIN="${BIN}" ZAPRET_PYTHON_POLICY="${TMP}/unsupported.json" "${RUNTIME}" --check >"${TMP}/out" 2>"${TMP}/err"; then
    fail "incompatible Python branch was accepted"
fi
grep -Fq 'unsupported interpreter version 3.13; qualified branches: 3.12' "${TMP}/err" ||
    fail "refusal did not use manifest supported branch"
[ ! -s "${TMP}/out" ] || fail "incompatible runtime contaminated stdout"

if run "${TMP}/missing-script.py" >"${TMP}/out" 2>"${TMP}/err"; then
    fail "unreadable Python entry point accepted"
fi
grep -Fq 'entry point is unreadable' "${TMP}/err" || fail "unreadable script diagnostic"

# A native installed package must not select arbitrary PATH Python; only
# explicit source-test overrides are permitted by this CLI contract.
grep -Fq 'PYTHON_BIN="${ZAPRET_PYTHON_BIN:-/usr/local/bin/python3}"' "${RUNTIME}" ||
    fail "native default is not the absolute generic OPNsense interpreter"
# Service Start/Apply refusal precedes template or firewall mutation.
SERVICE="${ROOT}/src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
grep -Fq '"${PYTHON_RUNTIME}" --check || return 69' "${SERVICE}" ||
    fail "native lifecycle lacks the pre-mutation Python preflight"
"${BIN}" - "${SERVICE}" <<'PY'
from pathlib import Path
import sys
s = Path(sys.argv[1]).read_text()
for name in ("start_service()", "reconfigure_service()"):
    segment = s.split(name + "\n{", 1)[1].split("\n}", 1)[0]
    assert segment.index('"${PYTHON_RUNTIME}" --check') < segment.index("refresh_generated_configuration"), name
segment = s.split("stop_service()\n{", 1)[1].split("\n}", 1)[0]
assert "PYTHON_RUNTIME" not in segment
PY
grep -Fq 'exec "${PYTHON_BIN}" "$@"' "${RUNTIME}" ||
    fail "launcher does not exec the actual Python child"

echo 'PASS: single manifest-backed Python policy, preflight/refusal, clean argv/stdout, inherited FD9, and exec'
