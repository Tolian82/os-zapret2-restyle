#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ZAPRET_DIR="${ROOT_DIR}/src/opnsense/scripts/OPNsense/Zapret"
PYTHON_BIN=${STRATEGY_LAB_TEST_PYTHON:-python3.13}
VIEW="${ROOT_DIR}/src/opnsense/mvc/app/views/OPNsense/Zapret/diagnostics.volt"
ORCHESTRATOR="${ZAPRET_DIR}/strategy_lab_py/orchestrator.py"
PRESENTATION="${ZAPRET_DIR}/strategy_lab_py/protocol_presentation.py"
EXTENDED="${ZAPRET_DIR}/strategy_lab_py/extended.py"

fail(){ echo "FAIL: $*" >&2; exit 1; }
command -v "${PYTHON_BIN}" >/dev/null 2>&1 || fail 'Python 3.13 test runtime is unavailable'
"${PYTHON_BIN}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3,13) else 1)' || fail 'Python test runtime is not 3.13'
"${PYTHON_BIN}" -m py_compile "${PRESENTATION}" "${EXTENDED}" "${ORCHESTRATOR}"

PYTHONPATH="${ZAPRET_DIR}" "${PYTHON_BIN}" - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from strategy_lab_py import extended, protocol_presentation

closed = {"ipv4":"available","ipv6":"unavailable","quic_ipv4":"closed"}
opened = {"ipv4":"available","ipv6":"available","quic_ipv4":"available"}
ru30 = protocol_presentation.stage30_message("ru", "extended", True, closed)
en30 = protocol_presentation.stage30_message("en", "extended", False, opened)
assert "QUIC закрыт" in ru30
assert "подбор QUIC-стратегий включён" in ru30
assert "QUIC/IPv4" not in ru30
assert "QUIC is open" in en30
assert "QUIC strategy search is disabled" in en30

quic = {
    "status":"not_found",
    "tested":[
        {"id":"quic-fake-1"}, {"id":"quic-fake-2"},
        {"id":"quic-ipfrag-8"}, {"id":"quic-ipfrag-16"},
    ],
    "working":None,
}
udp = {
    "status":"not_found", "port":3478, "payload_bytes":140,
    "control":{
        "reply_observed":False,
        "attempts":[{"selected_ip":"203.0.113.10"}],
    },
    "tested":[{"id":"udp-ipfrag-8"},{"id":"udp-ipfrag-16"}],
    "working":None,
}
ru80 = protocol_presentation.stage80_message("ru", quic, udp)
en80 = protocol_presentation.stage80_message("en", quic, udp)
assert "QUIC: проверено стратегий 4 [quic-fake-1, quic-fake-2, quic-ipfrag-8, quic-ipfrag-16]" in ru80
assert "рабочая стратегия не найдена" in ru80
assert "UDP: порт 3478; payload 140 байт; endpoints 203.0.113.10" in ru80
assert "контрольный ответ не получен (это не означает, что порт закрыт)" in ru80
assert "проверено стратегий 2 [udp-ipfrag-8, udp-ipfrag-16]" in ru80
assert "QUIC: 4 strategies tested" in en80
assert "no control reply observed (this does not mean the port is closed)" in en80
assert "not_found" not in ru80 and "skipped" not in ru80
assert "not_found" not in en80 and "skipped" not in en80

disabled = protocol_presentation.stage80_message(
    "ru",
    {"status":"skipped","reason":"disabled","tested":[],"working":None},
    {"status":"skipped","reason":"udp_port_not_configured","tested":[],"working":None},
)
assert "QUIC: подбор стратегий отключён" in disabled
assert "UDP: проверка не настроена" in disabled
assert "skipped" not in disabled

# Direct UDP control evidence must use the exact selected IP, port and payload.
class FakeExecution:
    def __init__(self, stdout):
        self.stdout = stdout
        self.returncode = 0
        self.timed_out = False
        self.duration_ms = 7

calls = []
def fake_udp(host, port, payload_path):
    payload = payload_path.read_bytes()
    calls.append((host, port, payload))
    return FakeExecution("reply" if host == "203.0.113.10" else "")

original = extended.request.udp_response_request
extended.request.udp_response_request = fake_udp
try:
    with TemporaryDirectory() as tmp:
        payload = Path(tmp) / "payload.bin"
        payload.write_bytes(bytes(range(140)))
        epoch = SimpleNamespace(bindings=(
            {"endpoint":"udp.example","selected_ip":"203.0.113.10"},
            {"endpoint":"alt.example","selected_ip":"203.0.113.11"},
        ))
        control = extended._udp_control(epoch, 3478, payload)
finally:
    extended.request.udp_response_request = original

assert calls == [
    ("203.0.113.10", 3478, bytes(range(140))),
    ("203.0.113.11", 3478, bytes(range(140))),
]
assert control["port"] == 3478
assert control["payload_bytes"] == 140
assert control["reply_observed"] is True
assert [item["reply_observed"] for item in control["attempts"]] == [True, False]
PY

grep -Fq "udpHelp:'Файл запроса должен иметь размер 1–4096 байт." "${VIEW}" || fail 'Russian Generic UDP help text is missing'
grep -Fq "quicHelp:'Если включено, QUIC-стратегии проверяются" "${VIEW}" || fail 'Russian Enable QUIC help text is missing'
grep -Fq "quicHelp:'When enabled, QUIC candidates are tested" "${VIEW}" || fail 'English Enable QUIC help text is missing'
grep -Fq "$('#strategyLabUdpHelp').text(ui.udpHelp)" "${VIEW}" || fail 'Generic UDP help is not bound to the selected UI language'
grep -Fq "$('#strategyLabQuicHelp').text(ui.quicHelp)" "${VIEW}" || fail 'Enable QUIC help is not bound to the selected UI language'
grep -Fq 'protocol_presentation.stage30_message' "${ORCHESTRATOR}" || fail 'Stage 30 does not use localized protocol presentation'
grep -Fq 'protocol_presentation.stage80_message' "${ORCHESTRATOR}" || fail 'Stage 80 does not use localized protocol presentation'

echo 'PASS: Strategy Lab exposes localized QUIC/UDP execution evidence, exact candidate counts/IDs, and non-gating UDP control observations'
