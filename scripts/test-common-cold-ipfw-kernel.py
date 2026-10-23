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
    kld.write_text('#!/bin/sh\n[ "$3" = "$MOCK_LOADED_MODULE" ] && exit 0\nexit 1\n')
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
print("PASS: cold IPFW ENOPROTOOPT recognized without foreign-rule bypass")
