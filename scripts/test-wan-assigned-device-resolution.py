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

    # Stage50 must retrieve the selected WAN from the same native Config
    # preflight, even if the generated zapret.conf has not been created, or
    # still contains an obsolete WAN_IF.
    lab_dir = root / "lab"
    (lab_dir / "backend").mkdir(parents=True)
    (lab_dir / "bin").mkdir()
    (lab_dir / "backend" / "config.sh").write_text(mock_config.read_text())
    (lab_dir / "backend" / "common.sh").write_text(
        'common_error() { echo "REFUSED: $*" >&2; }\n'
    )
    fake_ifconfig = lab_dir / "bin" / "ifconfig"
    fake_ifconfig.write_text(
        '#!/bin/sh\n'
        'case " $MOCK_DEVICES " in *" $1 "*) exit 0 ;; esac\n'
        'exit 1\n'
    )
    fake_ifconfig.chmod(0o700)
    mock_php = lab_dir / "bin" / "php"
    mock_php.write_text(
        '#!/bin/sh\n'
        '[ "$2" = require ] || exit 64\n'
        'printf "%s\\n" "$MOCK_PHP_REPLY"\n'
    )
    mock_php.chmod(0o700)
    canonical = (
        ROOT / "src/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh"
    ).read_text()
    assert canonical.count("/usr/local/bin/php") == 2
    lab_preflight = lab_dir / "wan_preflight.sh"
    lab_preflight.write_text(
        canonical.replace("/usr/local/bin/php", str(mock_php))
    )
    lab_preflight.chmod(0o700)
    lab_config = lab_dir / "zapret.conf"
    lab_source = ROOT / "src/opnsense/scripts/OPNsense/Zapret/strategy_lab/runtime.sh"
    lab_shell = '. "$1"\nstrategy_lab_candidate_resolve_wan\n'
    scenarios = (
        ("saved OPT without generated runtime", "wan-selected=opt0", "tun42", "tun42", False),
        ("saved OPT with stale WAN_IF", "wan-selected=opt0", "tun42", "tun42", True),
        ("saved direct tunnel despite stale generation", "wan-selected=tun42", "", "tun42", True),
        ("no saved WAN", "wan-required", "tun42", None, False),
        ("invalid native WAN", "wan-invalid", "tun42", None, True),
        ("unassigned OPT", "wan-selected=opt0", "", None, False),
        ("unsafe interface mapping", "wan-selected=opt0", "tun42;bad", None, False),
        ("inactive selected WAN", "wan-not-required", "tun42", None, False),
    )
    for name, reply, assigned, expected, stale in scenarios:
        if stale:
            lab_config.write_text('WAN_IF="obsolete_if"\n')
        else:
            lab_config.unlink(missing_ok=True)
        env = os.environ.copy()
        env.pop("STRATEGY_LAB_WAN_DEVICE", None)
        env.pop("STRATEGY_LAB_TEST_WAN_OVERRIDE", None)
        env.update(
            SCRIPT_DIR=str(lab_dir),
            STRATEGY_LAB_CONFIG_FILE=str(lab_config),
            MOCK_TRACE=str(trace), MOCK_IPV4="", MOCK_ASSIGNED=assigned,
            MOCK_DEVICES="tun42", MOCK_PHP_REPLY=reply,
            PATH=str(lab_dir / "bin") + os.pathsep + os.environ.get("PATH", ""),
        )
        actual = subprocess.run(
            ["sh", "-c", lab_shell, "lab-wan", str(lab_source)], env=env,
            capture_output=True, text=True,
        )
        if expected is None:
            assert actual.returncode != 0 and actual.stdout.strip() == "", (
                name, actual.returncode, actual.stdout, actual.stderr)
        else:
            assert actual.returncode == 0 and actual.stdout.strip() == expected, (
                name, actual.returncode, actual.stdout, actual.stderr)
        # A failed device request must NOT be accepted as a kernel name.
        if reply in {"wan-required", "wan-invalid", "wan-not-required"}:
            assert reply in actual.stderr, (name, actual.stderr)

    # Bypass is allowed only with explicit isolated test fixture opt-in.
    env["STRATEGY_LAB_WAN_DEVICE"] = "tun42"
    env.pop("STRATEGY_LAB_TEST_WAN_OVERRIDE", None)
    bad = subprocess.run(
        ["sh", "-c", lab_shell, "lab-wan", str(lab_source)], env=env,
        capture_output=True, text=True,
    )
    assert bad.returncode != 0 and bad.stdout.strip() == "" and (
        "wan-device-override-refused" in bad.stderr)
    env["STRATEGY_LAB_TEST_WAN_OVERRIDE"] = "1"
    accepted = subprocess.run(
        ["sh", "-c", lab_shell, "lab-wan", str(lab_source)], env=env,
        capture_output=True, text=True,
    )
    assert accepted.returncode == 0 and accepted.stdout.strip() == "tun42"

print("PASS: saved native WAN authoritative with missing/stale generated runtime, OPT/TUN and strict refusal")
