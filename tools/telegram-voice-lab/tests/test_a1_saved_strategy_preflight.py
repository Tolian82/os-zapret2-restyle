#!/usr/bin/env python3
"""Host-independent regression for the OPNsense A1 saved-GUI diagnostic.

This deliberately does not access a real OPNsense host, private config.xml,
SSH identity or TNAS; the runner's embedded read-only Python is exercised
against in-memory OPNsense XML fixtures.
"""
import contextlib
import io
import os
import shlex
from pathlib import Path
import re
import subprocess
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

RUNNER = Path(__file__).resolve().parents[1] / "run-a1-opnsense.sh"
A1 = (
    "--filter-l3=ipv4\n"
    "--filter-udp=596-599\n"
    "<IPSET:telegram>\n"
    "--payload=unknown\n"
    "--lua-desync=fake:payload=unknown:blob="
    "0x00000000000000000000000000000000:badsum:repeats=2\n"
    "--new\n"
)


def saved_diagnostic_snippet():
    source = RUNNER.read_text(encoding="utf-8")
    match = re.search(r"<<'SAVED_A1'\n(.*?)\nSAVED_A1\n", source, re.DOTALL)
    if not match:
        raise AssertionError("saved-GUI diagnostic heredoc absent")
    return match.group(1)


def execute_fixture(traffic, missing_model=False, candidate="A1"):
    if missing_model:
        xml = "<opnsense><OPNsense><Zapret/></OPNsense></opnsense>"
    else:
        xml = (
            "<opnsense><OPNsense><Zapret><strategy><trafficargs>"
            + escape(traffic)
            + "</trafficargs></strategy></Zapret></OPNsense></opnsense>"
        )
    orig_parse = ET.parse
    try:
        ET.parse = lambda path: ET.ElementTree(ET.fromstring(xml))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), patch.dict(os.environ, {"TGVOICE_CANDIDATE": candidate}):
            exec(compile(saved_diagnostic_snippet(), "saved-a1-diagnostic", "exec"), {})
        return buf.getvalue()
    finally:
        ET.parse = orig_parse


class A1SavedStrategyDiagnosticTests(unittest.TestCase):
    def test_posix_script_parses(self):
        subprocess.run(["/bin/sh", "-n", str(RUNNER)], check=True)

    def test_full_saved_a1_detected(self):
        output = execute_fixture("--filter-tcp=443\n--new\n" + A1)
        self.assertIn("saved_gui_model=READ_OK", output)
        self.assertIn("saved_gui_A1=YES", output)

    def test_missing_saved_a1(self):
        output = execute_fixture("--filter-udp=80,443,5222,8888\n--new\n")
        self.assertIn("saved_gui_A1=NO", output)
        self.assertIn("saved_gui_A1_port=NO", output)

    def test_terms_across_profiles_are_not_a_candidate(self):
        output = execute_fixture(
            A1.replace("\n--payload=unknown\n", "\n--new\n--payload=unknown\n")
        )
        self.assertIn("saved_gui_A1=NO", output)

    def test_unavailable_saved_model_is_not_reported_absent(self):
        output = execute_fixture("", missing_model=True)
        self.assertIn("saved_gui_model=NOT_FOUND", output)
        self.assertNotIn("saved_gui_A1=NO", output)

    def test_never_print_saved_xml_or_unrelated_secrets(self):
        output = execute_fixture(A1 + "PRIVATE_SECRET_MUST_NOT_APPEAR")
        self.assertNotIn("PRIVATE_SECRET_MUST_NOT_APPEAR", output)
        self.assertIn("saved_gui_A1=YES", output)

    def test_selected_a2_is_recognized_when_only_checksum_flag_changes(self):
        a2 = A1.replace(':badsum:repeats=2', ':repeats=2')
        output = execute_fixture(a2, candidate='A2')
        self.assertIn('saved_gui_A2=YES', output)
        self.assertIn('saved_gui_A1_fake=NO', output)

    def test_wrong_or_competing_candidate_is_not_accepted(self):
        a2 = A1.replace(':badsum:repeats=2', ':repeats=2')
        self.assertIn('saved_gui_A2=NO', execute_fixture(A1, candidate='A2'))
        self.assertIn('saved_gui_A1=NO', execute_fixture(a2, candidate='A1'))
        self.assertIn('saved_gui_A2=NO', execute_fixture(A1 + a2, candidate='A2'))
        self.assertIn('saved_gui_A1=NO', execute_fixture(A1 + a2, candidate='A1'))

    def test_active_profile_exact_candidate_and_competitor_guard(self):
        source = RUNNER.read_text(encoding='utf-8')
        match = re.search(r'awk -v expected="\$FAKE_LINE" -v competing="\$OTHER_FAKE" \'\n(.*?)\n\' "\$ACTIVE/traffic.conf"', source, re.DOTALL)
        self.assertIsNotNone(match, 'dynamic active-profile guard missing')
        program = match.group(1)
        a1 = '--lua-desync=fake:payload=unknown:blob=0x00000000000000000000000000000000:badsum:repeats=2'
        a2 = a1.replace(':badsum:repeats=2', ':repeats=2')
        def effective(*fake_lines):
            return ('--filter-l3=ipv4\n--filter-udp=596-599\n'
                    '--ipset=/usr/local/etc/zapret2/runtime-v2/managed/ipset-telegram.txt\n'
                    '--payload=unknown\n' + '\n'.join(fake_lines) + '\n--new\n')
        # Join the tuple's parts explicitly, not individual character iterations.
        def profile(*fake_lines):
            return ''.join(effective(*fake_lines))
        for selected, other in ((a1, a2), (a2, a1)):
            for config, succeeds in ((profile(selected), True),
                                     (profile(other), False),
                                     (profile(selected) + profile(other), False),
                                     (profile(selected, other), False),
                                     ('--new\n', False)):
                p = subprocess.run(['awk', '-v', 'expected=' + selected,
                                    '-v', 'competing=' + other, program],
                                   input=config, capture_output=True, text=True)
                self.assertEqual(p.returncode == 0, succeeds, (selected, config, p.stderr))

    def test_remote_linux_explicit_from_route_preflight(self):
        """Treat valid Linux 'from' route text as valid; independently guard NIC IP."""
        source = RUNNER.read_text(encoding="utf-8")
        remote = source.split("<<'REMOTE_PRE'\n", 1)[1].split("\nREMOTE_PRE", 1)[0]
        route_check = remote.split('[ -x "$DOCKER" ]', 1)[0]
        good = "91.108.13.10 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1 uid 0"
        second = "149.154.167.99 from 192.168.1.100 via 192.168.1.2 dev ovs_eth1 uid 0"
        for text, addr_ok, should_pass in (
            (good, True, True),
            ("91.108.13.10 via 192.168.1.2 dev ovs_eth1 src 192.168.1.100", True, True),
            ("91.108.13.10 from 192.168.1.100 via 192.168.1.140 dev ovs_eth1 uid 0", True, False),
            (good, False, False),
        ):
            shell = (
                'ip() {\n'
                '  if [ "$2" = -o ]; then\n'
                '    echo ' + shlex.quote(
                    "2: ovs_eth1 inet " + ("192.168.1.100" if addr_ok else "192.168.1.99") + "/24 brd 192.168.1.255 scope global ovs_eth1"
                ) + ';\n'
                '  elif [ "$3" = get ]; then\n'
                '    if [ "$4" = 91.108.13.10 ]; then echo ' + shlex.quote(text) + ';\n'
                '    else echo ' + shlex.quote(second) + '; fi\n'
                '  else return 1; fi\n'
                '}\n'
            )
            p = subprocess.run(["/bin/sh", "-c", shell + route_check],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode == 0, should_pass,
                             (text, addr_ok, p.stdout, p.stderr))

    def test_effective_absence_rejects_docker_without_mutation(self):
        source = RUNNER.read_text(encoding="utf-8")
        for verdict in ("_NOT_IN_SAVED_GUI", "_SAVED_BUT_NOT_EFFECTIVE",
                        "_SAVED_STATUS_UNKNOWN", "_ACTIVE_PROFILE_BUT_IPFW_RULE_MISSING"):
            self.assertIn(verdict, source)
        self.assertLess(source.index("_NOT_IN_SAVED_GUI"), source.index("Running ONE fresh"))


if __name__ == "__main__":
    unittest.main()
