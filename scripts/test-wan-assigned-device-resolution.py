#!/usr/bin/env python3
"""Single narrow off-target execution test for native WAN assignment resolver.

Uses the production shell function with only absolute pluginctl/jq tool paths
replaced by disposable fixtures. Never touches firewall, Config or services.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/config.sh"

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    mock_plugin = root / "pluginctl"
    mock_jq = root / "jq"
    mock_config = root / "config.sh"
    trace = root / "trace"
    mock_plugin.write_text(
        '#!/bin/sh\n'
        'printf "%s %s\\n" "$1" "$2" >> "$MOCK_TRACE"\n'
        'case "$1" in\n'
        '  -4) printf \'{"opt0":[{"device":null}]}\\n\' ;;\n'
        '  -g) [ "$2" = "interfaces.opt0.if" ] || exit 2;\n'
        '      printf "%s\\n" "$MOCK_ASSIGNED" ;;\n'
        '  *) exit 2 ;;\n'
        'esac\n'
    )
    mock_jq.write_text(
        '#!/bin/sh\n'
        'cat >/dev/null\n'
        'printf "%s\\n" "$MOCK_IPV4"\n'
    )
    for executable in (mock_plugin, mock_jq):
        executable.chmod(0o700)
    source = SOURCE.read_text()
    assert source.count("/usr/local/sbin/pluginctl") >= 2
    assert source.count("/usr/local/bin/jq") >= 2
    mock_config.write_text(
        source.replace("/usr/local/sbin/pluginctl", str(mock_plugin))
              .replace("/usr/local/bin/jq", str(mock_jq))
    )
    shell = (
        'common_error() { printf "REFUSED: %s\\n" "$*" >&2; }\n'
        'ifconfig() {\n'
        '  case " $MOCK_DEVICES " in *" $1 "*) return 0 ;; esac\n'
        '  return 1\n'
        '}\n'
        '. "$1"\n'
        'config_resolve_interface "$2"\n'
    )

    def check(name, logical, ipv4, assigned, devices, expected, use_fallback):
        trace.write_text("")
        env = os.environ.copy()
        env.update(MOCK_TRACE=str(trace), MOCK_IPV4=ipv4,
                   MOCK_ASSIGNED=assigned, MOCK_DEVICES=devices)
        run = subprocess.run(["sh", "-c", shell, "resolver-test",
                              str(mock_config), logical], env=env,
                             capture_output=True, text=True)
        actual = run.stdout.strip()
        log = trace.read_text()
        if expected is None:
            assert run.returncode != 0 and actual == "", (
                name, run.returncode, run.stdout, run.stderr)
        else:
            assert run.returncode == 0 and actual == expected, (
                name, run.returncode, run.stdout, run.stderr)
        assert ("-g interfaces.opt0.if" in log) == use_fallback, (
            name, log, use_fallback)

    # Existing IPv4 interface and direct-kernel-device paths are unchanged.
    check("normal WAN IPv4", "wan", "vtnet1", "", "vtnet1 tun42 lo0",
          "vtnet1", False)
    check("direct tunnel device", "tun42", "", "", "tun42", "tun42", False)

    # User-reproduced opt0 -> NO_DEVICE: device assignment has no primary IPv4.
    check("IPv4-less assigned TUN", "opt0", "", "tun42", "tun42",
          "tun42", True)
    check("disconnected TUN", "opt0", "", "tun42", "vtnet1",
          None, True)
    check("unassigned opt0", "opt0", "", "", "tun42",
          None, True)
    check("unsafe assigned device", "opt0", "", "tun42;danger", "tun42",
          None, True)
    check("unsafe logical assignment", "opt0foo", "", "tun42", "tun42",
          None, False)

    # Lab Stage 50 must use the same native resolver; -4-only would refuse TUN.
    lab_dir = root / "lab"
    (lab_dir / "backend").mkdir(parents=True)
    (lab_dir / "backend" / "config.sh").write_text(mock_config.read_text())
    (lab_dir / "backend" / "common.sh").write_text(
        'common_error() { echo "REFUSED: $*" >&2; }\n'
    )
    lab_config = lab_dir / "zapret.conf"
    lab_source = ROOT / "src/opnsense/scripts/OPNsense/Zapret/strategy_lab/runtime.sh"
    lab_shell = (
        'ifconfig() { case " $MOCK_DEVICES " in *" $1 "*) return 0 ;; esac; return 1; }\n'
        '. "$1"\n'
        'strategy_lab_candidate_resolve_wan\n'
    )
    for name, logical, assigned, expected in (
        ("IPv4-less assigned OPT/TUN", "opt0", "tun42", "tun42"),
        ("unassigned OPT/TUN", "opt0", "", None),
        ("unsafe device", "opt0", "tun42;bad", None),
        ("direct device", "tun42", "", "tun42"),
        ("missing WAN", "", "tun42", None),
    ):
        lab_config.write_text(f'WAN_IF="{logical}"\n')
        env = os.environ.copy()
        env.pop("STRATEGY_LAB_WAN_DEVICE", None)
        env.update(SCRIPT_DIR=str(lab_dir), STRATEGY_LAB_CONFIG_FILE=str(lab_config),
                   MOCK_TRACE=str(trace), MOCK_IPV4="", MOCK_ASSIGNED=assigned,
                   MOCK_DEVICES="tun42")
        actual = subprocess.run(["sh", "-c", lab_shell, "lab-wan",
                                 str(lab_source)], env=env, capture_output=True, text=True)
        if expected is None:
            assert actual.returncode != 0 and actual.stdout.strip() == "", (
                name, actual.stdout, actual.stderr)
        else:
            assert actual.returncode == 0 and actual.stdout.strip() == expected, (
                name, actual.stdout, actual.stderr)

print("PASS: native TUN without IPv4, unchanged WAN, fail-closed invalid/unavailable device")
