#!/usr/bin/env python3
"""Exact source/native-helper regression for owner-approved IPFW rule numbers.

Numeric range only, NOT a foreign-rule occupancy/identity scan.
FreeBSD engine auto-reread behavior is outside this test (manual.en.md canon).
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"
ENGINE = BACKEND.parent / "zapret_service.sh"
PREVIEW = BACKEND / "strategy_preview_build.py"
ORCHESTRATOR = BACKEND / "orchestrator.sh"
FIREWALL = BACKEND / "firewall.sh"
LAB = BACKEND.parent / "strategy_lab/firewall.sh"
PURGE = ROOT / "scripts/purge-os-zapret2-restyle.sh"
PACKAGED_PURGE = ROOT / "src/opnsense/share/zapret2-restyle/purge-os-zapret2-restyle.sh"


def shell_function(file: Path, func: str, *arguments: str, env: dict | None = None) -> int:
    shell = '. "$1"; shift; ' + func + ' "$@"'
    result = subprocess.run(
        ["/bin/sh", "-c", shell, "scope", str(file), *arguments],
        env={**os.environ, **(env or {})}, capture_output=True, text=True,
        timeout=6, check=False,
    )
    return result.returncode


class IPFWAllocation(unittest.TestCase):
    def test_entrypoints_and_preview_share_ordinary_range(self):
        engine = ENGINE.read_text()
        self.assertRegex(engine, r"(?m)^RULE_BASE=19000$")
        self.assertRegex(engine, r"(?m)^RULE_MAX=19099$")
        self.assertNotIn("RULE_MAX=19010", engine)

        preview = PREVIEW.read_text()
        self.assertRegex(preview, r"(?m)^RULE_BASE=19000$")
        self.assertRegex(preview, r"(?m)^RULE_MAX=19099$")
        generator = ORCHESTRATOR.read_text()
        self.assertIn(r'${RULE_BASE:-19000}', generator)
        self.assertIn(r'${RULE_MAX:-19099}', generator)
        self.assertNotIn(r'${RULE_MAX:-19010}', generator)

    def test_numeric_scope_for_actual_ordinary_firewall_mutations(self):
        for first, last, expected in [
            (19000, 19099, True), (19000, 19000, True),
            (19099, 19099, True), (19000, 19010, True),
            (18999, 19099, False), (19000, 19100, False),
            (19100, 19131, False), (19140, 19200, False),
            (19132, 19139, False), (65534, 65534, False),
            (19099, 19000, False),
        ]:
            with self.subTest(first=first, last=last):
                rc = shell_function(FIREWALL, "firewall_normal_rule_range_valid",
                                    str(first), str(last))
                self.assertEqual(rc == 0, expected)
        # The helper guards dangerous operations BEFORE any external IPFW call.
        firewall_text = FIREWALL.read_text()
        for function in (
            "firewall_remove_rules", "firewall_install_port_rules",
            "firewall_install_rules", "firewall_snapshot_rules",
            "firewall_restore_rules",
        ):
            start = firewall_text.index("\n" + function + "()")
            end = firewall_text.find("\n}\n", start)
            block = firewall_text[start:end]
            self.assertIn("firewall_normal_rule_range_valid", block,
                          function)

    def test_voice_adapter_mutation_guard_but_no_new_rule_ownership_scan(self):
        sys.path.insert(0, str(BACKEND))
        from voice_ipfw_adapter import FreeBSDIPFWAdapter, IPFWAdapterError

        for first, last in [(19000, 19099), (19000, 19010), (19099, 19099)]:
            with self.subTest(first=first, last=last):
                FreeBSDIPFWAdapter(first, last, allow_mutations=True)
        for first, last in [
            (18999, 19000), (19000, 19100), (19100, 19131),
            (19140, 19200), (65534, 65534),
        ]:
            with self.subTest(first=first, last=last):
                with self.assertRaises(IPFWAdapterError):
                    FreeBSDIPFWAdapter(first, last, allow_mutations=True)

    def test_lab_current_range_is_separate_from_future_reserve(self):
        for first, last, ok in [
            (19100, 19131, True), (19100, 19100, True),
            (19131, 19131, True),
            (19099, 19131, False), (19100, 19132, False),
            (19132, 19139, False), (19140, 19200, False),
        ]:
            with self.subTest(first=first, last=last):
                rc = shell_function(LAB, "strategy_lab_firewall_contract_valid",
                                    env={"STRATEGY_LAB_RULE_BASE": str(first),
                                         "STRATEGY_LAB_RULE_MAX": str(last)})
                self.assertEqual(rc == 0, ok)

    def test_both_purges_agree_and_reserve_is_untouched(self):
        a, b = PURGE.read_text(), PACKAGED_PURGE.read_text()
        self.assertEqual(a, b, "standalone/installed purge must agree")
        self.assertIn("19000 <= number <= 19099 or 19100 <= number <= 19131", a)
        self.assertNotIn("19000 <= number <= 19010", a)
        self.assertNotRegex(a, r"if 19140 <= number <= 19200")
        self.assertNotRegex(a, r"if 19000 <= number <= 19200")

    def test_invalid_restore_snapshot_cannot_touch_ipfw(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / "snapshot"
            # Untrusted/stale rollback must be rejected BEFORE deleting
            # any currently installed 19000..19099 rules.
            snapshot.write_text("65534 allow ip from any to any\\n")
            log = root / "ipfw.log"
            stub = root / "ipfw"
            stub.write_text('#!/bin/sh\\nprintf "%s\\\\n" "$*" >> "$IPFW_TEST_LOG"\\n')
            stub.chmod(0o755)
            command = '''
. "$1"
common_require_file() { [ -f "$1" ]; }
firewall_restore_rules "$2" 19000 19099
'''
            rc = subprocess.run(
                ["/bin/sh", "-c", command, "scope", str(FIREWALL), str(snapshot)],
                env={**os.environ, "IPFW_BIN": str(stub), "IPFW_TEST_LOG": str(log)},
                capture_output=True, text=True, timeout=6, check=False,
            )
            self.assertNotEqual(0, rc.returncode)
            self.assertFalse(log.exists(), "invalid snapshot attempted IPFW mutation")

    def test_preinstall_ipfw_policy_is_read_only_and_precedes_stop(self):
        # Old 65534 allow cannot be attributed to Zapret2 just by its text.
        # Reject an incompatible successor BEFORE calling the old Stop.
        import tempfile
        hook = (ROOT / "pkg/+PRE_INSTALL").read_text()
        declaration = "preinstall_ipfw_policy_compatible()\n{"
        begin = hook.index(declaration)
        end = hook.index("\n}\n", begin) + len("\n}\n")
        helper = hook[begin:end]
        status = hook.index("\nread_service_status\nservice_status")
        gate = hook.index("preinstall_ipfw_policy_compatible || exit 1")
        marker = hook.index(': > "${REPLACEMENT_RESTART_MARKER}"')
        stop = hook.index('if "${SERVICE_SCRIPT}" stop')
        self.assertLess(status, gate)
        self.assertLess(gate, marker)
        self.assertLess(gate, stop)
        self.assertIn('case "${service_status}" in\n    0)', hook[:gate])
        # A prior legacy updater may have stopped a RUNNING owner already:
        # STOPPED + any restart marker / protected journal is NOT safe to
        # upgrade under default-deny without the same policy preflight.
        stopped = hook.index("\n    1)\n", hook.index('case "${service_status}" in'))
        failed = hook.index("\n    2)\n", stopped)
        branch = hook[stopped:failed]
        for required in (
            "REPLACEMENT_RESTART_MARKER", "UPGRADE_RESTART_MARKER",
            "PROTECTED_UPDATE_RECORD", "preinstall_ipfw_policy_compatible || exit 1",
        ):
            self.assertIn(required, branch)
        self.assertIn('[ -L "${PROTECTED_UPDATE_RECORD}" ]', branch)
        self.assertLess(branch.index("PROTECTED_UPDATE_RECORD"),
                        branch.index("preinstall_ipfw_policy_compatible || exit 1"))
        executable = "\n".join(line for line in helper.splitlines()\n                               if not line.lstrip().startswith("#"))\n        self.assertNotRegex(executable, r"\b(delete|flush|add)\b")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            trace = root / "calls"
            for name, source in {
                "sysctl": (
                    '#!/bin/sh\necho sysctl >> "$IPFW_TEST_LOG"\n'
                    '[ "$MOCK_POLICY" = missing ] && exit 1\n'
                    'printf "%s\\n" "$MOCK_POLICY"\n'
                ),
                "kldstat": (
                    '#!/bin/sh\necho kldstat >> "$IPFW_TEST_LOG"\n'
                    '[ "$MOCK_MODULE" = unloaded ] && exit 1\n'
                    '[ "$MOCK_MODULE" = loaded ] && exit 0\nexit 70\n'
                ),
                "ipfw": (
                    '#!/bin/sh\necho ipfw >> "$IPFW_TEST_LOG"\n'
                    'if [ "$MOCK_COLD" = 1 ]; then\n'
                    'echo "ipfw: retrieving config failed: Protocol not available" >&2\n'
                    'exit 71\nfi\n'
                    'echo "65534 allow ip from any to any"\n'
                    'echo "65535 deny ip from any to any"\n'
                ),
            }.items():
                file = root / name
                file.write_text(source)
                file.chmod(0o755)
            for policy, module, cold, expected, calls in [
                ("1", "loaded", "0", True, ["sysctl"]),
                ("0", "loaded", "0", False, ["sysctl"]),
                ("missing", "unloaded", "1", True, ["sysctl", "kldstat", "ipfw"]),
                ("missing", "loaded", "1", False, ["sysctl", "kldstat"]),
                ("missing", "unloaded", "0", False, ["sysctl", "kldstat", "ipfw"]),
            ]:
                with self.subTest(policy=policy, module=module, cold=cold):
                    trace.write_text("")
                    r = subprocess.run(
                        ["/bin/sh", "-c", helper + "\npreinstall_ipfw_policy_compatible\n"],
                        env={**os.environ, "IPFW_SYSCTL_BIN": str(root / "sysctl"),
                             "KLDSTAT_BIN": str(root / "kldstat"),
                             "IPFW_BIN": str(root / "ipfw"),
                             "IPFW_TEST_LOG": str(trace),
                             "MOCK_POLICY": policy, "MOCK_MODULE": module,
                             "MOCK_COLD": cold},
                        capture_output=True, text=True, timeout=6, check=False,
                    )
                    self.assertEqual(r.returncode == 0, expected, r.stderr)
                    self.assertEqual(trace.read_text().splitlines(), calls)

    def test_protected_pkg_preflights_before_record_or_stop(self):
        service = ENGINE.read_text()
        begin = service.index("pkg_update_prepare_service()\n{")
        end = service.index("\n}\n", begin)
        prepare = service[begin:end]
        self.assertIn("net.inet.ip.fw.default_to_accept", prepare)
        self.assertIn('if [ "${_pkg_prev_running}" = running ]; then', prepare)
        self.assertLess(prepare.index('if [ "${_pkg_prev_running}" = running ]; then'),
                        prepare.index("_pkg_ipfw_policy=$("))
        self.assertIn("shared_apply_ipfw_kernel_absent_service", prepare)
        self.assertIn('if [ "${_pkg_ipfw_policy}" != "1" ]; then', prepare)
        self.assertLess(prepare.index("_pkg_ipfw_policy=$("),
                        prepare.index('"${PYTHON_RUNTIME}" "${SCRIPT_DIR}/protected_pkg_update.py" record'))
        self.assertLess(prepare.index("_pkg_ipfw_policy=$("),
                        prepare.index('shared_apply_stop_service "${_pkg_current_owner}"'))
        self.assertNotRegex(prepare, r"(?m)^\s*[^#\n]*\b(ipfw\s+.*\b(?:add|delete|flush)\b)")

    def test_system_rule_65534_is_not_created(self):
        text = FIREWALL.read_text()
        self.assertNotRegex(text, r'(?m)^\s*[^#\n]*\badd\s+65534\b')
        self.assertIn('net.inet.ip.fw.default_to_accept', text)
        self.assertIn('refusing to create system rule 65534', text)


if __name__ == "__main__":
    unittest.main()
