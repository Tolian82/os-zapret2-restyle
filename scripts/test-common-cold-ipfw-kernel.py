#!/usr/bin/env python3
"""No-network regression for cold FreeBSD IPFW kernel read-only classification.

The only positive case is BOTH ipfw/ipdivert absent and ipfw(8) exit 71
with the exact ENOPROTOOPT message. No foreign rules are deleted.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
service = (root / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").read_text()
start = service.find("shared_apply_ipfw_kernel_absent_service()\n{\n")
end = service.find("\nshared_apply_boot_service()\n{\n", start)
assert start >= 0 and end > start, "missing cold-kernel proof"
function = service[start:end]
boot = service[end:service.index("\n# Seal/attest",end)]
assert "apply_runtime_attest_engine_inventory || return 69" in boot
assert boot.index("apply_runtime_attest_engine_inventory || return 69") < boot.index(
    "prepare_firewall_prerequisites || return 70"
) < boot.index("apply_runtime_activate")
assert "if shared_apply_ipfw_kernel_absent_service; then" in boot
assert "preflight_shared_apply_journal common-apply" in boot
assert "shared_apply_bundle_service verify" in boot
assert "kldload" not in function
with tempfile.TemporaryDirectory() as tmp:
    directory = Path(tmp)
    kld = directory / "kldstat"
    ipfw = directory / "ipfw"
    kld.write_text('#!/bin/sh\n[ "$3" = "$MOCK_LOADED_MODULE" ] && exit 0\n[ "${MOCK_KLD_ERROR:-0}" = 1 ] && exit 70\nexit 1\n')
    ipfw.write_text('#!/bin/sh\nprintf "%s\\n" "$MOCK_IPFW_MESSAGE" >&2\nexit "$MOCK_IPFW_RC"\n')
    kld.chmod(0o755)
    ipfw.chmod(0o755)
    for loaded, rc, message, expected in (
        ("none", 71, "ipfw: retrieving config failed: Protocol not available", True),
        ("ipfw", 71, "ipfw: retrieving config failed: Protocol not available", False),
        ("ipdivert", 71, "ipfw: retrieving config failed: Protocol not available", False),
        ("none", 0, "", False),
        ("none", 71, "permission denied", False),
        ("none", 70, "Protocol not available", False),
    ):
        env = dict(os.environ, SHARED_APPLY_KLDSTAT_BIN=str(kld),
                   SHARED_APPLY_IPFW_BIN=str(ipfw), MOCK_LOADED_MODULE=loaded,
                   MOCK_IPFW_RC=str(rc), MOCK_IPFW_MESSAGE=message)
        result = subprocess.run(
            ["sh", "-c", function + "\nshared_apply_ipfw_kernel_absent_service\n"],
            capture_output=True, text=True, env=env,
        )
        assert (result.returncode == 0) == expected, (
            f"cold kernel proof drift: loaded={loaded} rc={rc}: {result.stderr}"
        )
    # Query failures are not "module absent" even if ipfw itself returns 71.
    denied = subprocess.run(
        ["sh", "-c", function + "\nshared_apply_ipfw_kernel_absent_service\n"],
        capture_output=True, text=True,
        env={**os.environ,
             "SHARED_APPLY_KLDSTAT_BIN":str(kld),
             "SHARED_APPLY_IPFW_BIN":str(ipfw),
             "MOCK_LOADED_MODULE":"none", "MOCK_KLD_ERROR":"1",
             "MOCK_IPFW_RC":"71",
             "MOCK_IPFW_MESSAGE":"ipfw: retrieving config failed: Protocol not available"},
    )
    assert denied.returncode != 0, "kldstat failure was treated as absence"
print("PASS: cold IPFW ENOPROTOOPT recognized without foreign-rule bypass")

# Verify the PRODUCTION firewall_prepare cold path, with inert FreeBSD command
# mocks. No host module or rule operation is performed by this test.
firewall = (root / "src/opnsense/scripts/OPNsense/Zapret/backend/firewall.sh").read_text()
begin = firewall.index("firewall_cold_load_ipfw()\n{\n")
finish = firewall.index("\nfirewall_install_port_rules()\n{\n", begin)
cold_functions = firewall[begin:finish]
with tempfile.TemporaryDirectory() as td:
    base = Path(td)
    state = base / "state"
    state.mkdir()
    trace = base / "trace"
    mocks = {
        "kldstat": """#!/bin/sh
[ "$TEST_KLDSTAT_ERROR" = 1 ] && exit 70
[ -e "$TEST_STATE/$3" ] && exit 0
exit 1
""",
        "ipfw": """#!/bin/sh
if [ ! -e "$TEST_STATE/ipfw" ]; then
    [ "$TEST_IPFW_RC" = 70 ] && exit 70
    echo 'ipfw: retrieving config failed: Protocol not available' >&2
    exit 71
fi
if [ "$TEST_FOREIGN_RULES" = 1 ]; then
    echo '19000 deny ip from any to any'
fi
echo '65535 count ip from any to any not // orphaned dynamic states counter'
echo '65535 allow ip from any to any'
""",
        "kldload": """#!/bin/sh
echo "load:$1" >> "$TEST_TRACE"
touch "$TEST_STATE/$1"
""",
        "kenv": """#!/bin/sh
if [ "$1" = 'net.inet.ip.fw.default_to_accept=1' ]; then
    echo 'kenv:set' >> "$TEST_TRACE"
    [ "$TEST_KENV_ERROR" = 1 ] && exit 1
    echo 1 > "$TEST_STATE/default"
    exit 0
fi
if [ "$1" = -qv ]; then
    [ -f "$TEST_STATE/default" ] || exit 255
    echo 'net.inet.ip.fw.default_to_accept="1"'
    exit 0
fi
exit 64
""",
        "sysctl": """#!/bin/sh
if [ "$TEST_SYSCTL_ERROR" = 1 ]; then
    echo 0
else
    cat "$TEST_STATE/default"
fi
""",
    }
    for name, content in mocks.items():
        path = base / name
        path.write_text(content)
        path.chmod(0o755)
    probe = cold_functions + """
firewall_ensure_default_accept() { echo ensure >> "$TEST_TRACE"; }
firewall_configure_reinject() { echo reinject >> "$TEST_TRACE"; }
firewall_prepare
"""
    def run_case(*, loaded=(), kld_error=0, ipfw_rc=71, kenv_error=0,
                 sysctl_error=0, foreign=0):
        for child in state.iterdir():
            child.unlink()
        for module in loaded:
            (state / module).touch()
        trace.write_text("")
        env = {**os.environ,
               "TEST_STATE":str(state), "TEST_TRACE":str(trace),
               "TEST_KLDSTAT_ERROR":str(kld_error),
               "TEST_IPFW_RC":str(ipfw_rc),
               "TEST_KENV_ERROR":str(kenv_error),
               "TEST_SYSCTL_ERROR":str(sysctl_error),
               "TEST_FOREIGN_RULES":str(foreign),
               "FIREWALL_KLDSTAT_BIN":str(base / "kldstat"),
               "FIREWALL_KLDLOAD_BIN":str(base / "kldload"),
               "FIREWALL_KENV_BIN":str(base / "kenv"),
               "FIREWALL_SYSCTL_BIN":str(base / "sysctl"),
               "IPFW_BIN":str(base / "ipfw")}
        response = subprocess.run(["sh", "-c", probe], env=env,
                                  capture_output=True, text=True)
        return response, trace.read_text().splitlines()
    success, actions = run_case()
    assert success.returncode == 0, success.stderr
    assert actions == ["kenv:set", "load:ipfw", "load:ipdivert",
                       "ensure", "reinject"], actions
    warm, actions = run_case(loaded=("ipfw", "ipdivert"))
    assert warm.returncode == 0 and actions == ["ensure", "reinject"], actions
    partial, actions = run_case(loaded=("ipdivert",))
    assert partial.returncode != 0 and not actions, actions
    for label, args, prefix in (
        ("untrusted-module-query", {"kld_error":1}, []),
        ("invalid-ipfw-probe", {"ipfw_rc":70}, []),
        ("no-kenv-authorization", {"kenv_error":1}, ["kenv:set"]),
        ("wrong-loaded-policy", {"sysctl_error":1}, ["kenv:set","load:ipfw"]),
        ("unexpected-ipfw-rule", {"foreign":1}, ["kenv:set","load:ipfw"]),
    ):
        response, actions = run_case(**args)
        assert response.returncode != 0, label
        assert actions == prefix, (label, actions)
print("PASS: cold IPFW loader stages default allow before kldload and refuses ambiguity")

