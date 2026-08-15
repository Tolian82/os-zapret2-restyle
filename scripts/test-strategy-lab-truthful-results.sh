#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
MODULE="${ZAPRET_DIR}/strategy_lab_py/truthful_result_support.py"
ENTRY="${ZAPRET_DIR}/strategy_lab_python.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON}" >/dev/null 2>&1 || fail "Python 3.13 is unavailable: ${PYTHON}"
"${PYTHON}" -m py_compile "${MODULE}" "${ENTRY}" || fail 'truthful result support does not compile under Python 3.13'

TMP=$(mktemp -d "${TMPDIR:-/tmp}/strategy-lab-truthful-results.XXXXXX")
trap 'rm -rf "${TMP}"' EXIT HUP INT TERM
mkdir -p "${TMP}/jobs/job.truth"
export STRATEGY_LAB_JOBS_DIR="${TMP}/jobs"
export PYTHONPATH="${ZAPRET_DIR}"
export TEST_TMP="${TMP}"

cat > "${TMP}/test.py" <<'PY'
import json
import os
from pathlib import Path

from strategy_lab_py import adaptive_validation, endpoint_epoch, extended
from strategy_lab_py import protocol_presentation
from strategy_lab_py import truthful_result_support as truthful

root = Path(os.environ["TEST_TMP"])
job = Path(os.environ["STRATEGY_LAB_JOBS_DIR"]) / "job.truth"

truthful.install()

# A real intercepted HTTP application response proves that the selected DPI path reached
# the service.  4xx/5xx must remain visible evidence, not erase a Stage-70-stable finalist.
def replay(code=502, *, intercepted=True, status="PASS"):
    return {
        "all_pass": True,
        "profile_exact": True,
        "endpoints": [{
            "status": status,
            "firewall": {"intercepted": intercepted},
            "execution": {
                "stdout": f"exit=0 remote_ip=172.67.136.246 http=2 code={code} bytes=16\n"
            },
        }],
    }

cloudflare = adaptive_validation.classify_deep_replay(replay(502), "tls13", 16384)
assert cloudflare["classification"] == "reachable_application_error", cloudflare
assert cloudflare["accepted"] is True
assert cloudflare["http_statuses"] == [502]
assert cloudflare["reason"] == "http_application_response"

# The corrective rule must not weaken interception/profile proof.
not_intercepted = adaptive_validation.classify_deep_replay(
    replay(502, intercepted=False), "tls13", 16384
)
assert not_intercepted["classification"] == "fail"
assert not_intercepted["accepted"] is False

# Bare IPv4 + curl exit 60 is missing TLS service identity, not proof that no bypass exists.
baseline = {
    "target": "37.48.102.131",
    "target_type": "ip",
    "endpoints": [{
        "endpoint": "37.48.102.131",
        "status": "FAIL",
        "exit_code": 60,
        "transport": "tls13-ipv4",
    }],
}
assert truthful.mark_bare_ip_tls_identity_requirement(job, "ip", baseline) is True
assert truthful.terminal_outcome_for(job, "NO_CANDIDATE") == "PARTIAL"
assert truthful.terminal_outcome_for(job, "SUCCESS") == "SUCCESS"

# Supplying Host/SNI clears the missing-identity marker.
(job / "service-host").write_text("files.dune-hd.com\n", encoding="utf-8")
assert truthful.mark_bare_ip_tls_identity_requirement(job, "ip", baseline) is False
assert truthful.terminal_outcome_for(job, "NO_CANDIDATE") == "NO_CANDIDATE"
(job / "service-host").unlink()

# QUIC on bare IPv4 must be skipped before any candidate runner/catalog work starts.
endpoints = job / "endpoints.txt"
endpoints.write_text("91.105.192.1\n", encoding="utf-8")
epoch = endpoint_epoch.create(
    job,
    "91.105.192.1",
    "ip",
    ["91.105.192.1"],
    [{"endpoint": "91.105.192.1"}],
)
quic_path = job / "quic.json"
status = extended.quic(
    "job.truth",
    str(endpoints),
    str(job / "network.json"),
    str(quic_path),
)
assert status == 0
quic = json.loads(quic_path.read_text(encoding="utf-8"))
assert quic["search_epoch_id"] == epoch.epoch_id
assert quic["status"] == "skipped"
assert quic["reason"] == "host_sni_required"
assert quic["tested"] == []
assert quic["working"] is None
ru = protocol_presentation._quic_summary("ru", quic)
en = protocol_presentation._quic_summary("en", quic)
assert "ПРОПУЩЕНО" in ru and "Host / SNI" in ru
assert "SKIPPED" in en and "Host / SNI" in en
PY

"${PYTHON}" "${TMP}/test.py" || fail 'truthful Strategy Lab result regression failed'

grep -Fq 'truthful_result_support.install()' "${ENTRY}" || fail 'packaged Strategy Lab entry point does not install truthful result support'
grep -Eq '^PLUGIN_REVISION=[[:space:]]+23$' "${ROOT_DIR}/Makefile" || fail 'package revision is not v0.4.1_23'
sh -n "$0"

echo 'PASS: Strategy Lab accepts intercepted HTTP application responses, skips bare-IP QUIC truthfully, and requests Host/SNI after bare-IP TLS identity failure'
