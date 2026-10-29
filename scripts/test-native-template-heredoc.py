#!/usr/bin/env python3
"""Parse generated POSIX shell from the REAL checked-in OPNsense Jinja template.

Regression: _10's inline {% endif %} consumed the newline before the
Exclude IPSet heredoc terminator. This test fails against that template.
"""
from pathlib import Path
import subprocess
import unittest

from jinja2 import Environment, StrictUndefined

TEMPLATE = (Path(__file__).resolve().parents[1] /
            "src/opnsense/service/templates/OPNsense/Zapret/zapret.conf")
MARKER = "__ZAPRET_EXCLUDE_IPSET__"


class Helpers:
    def __init__(self, present: bool):
        self.present = present

    def exists(self, dotted: str) -> bool:
        if dotted == "OPNsense.Zapret.hostlist.excludeipset":
            return self.present
        return True


def render(excluded: str, *, exists: bool = True, domains: str = "") -> str:
    # Reproduce the native Jinja trim_blocks behavior against the production
    # template file, not a fabricated shell fixture.
    env = Environment(trim_blocks=True, lstrip_blocks=False,
                      keep_trailing_newline=True, undefined=StrictUndefined)
    hostlist = dict(mode="ipset", youtubedomains=domains,
                    telegramips="91.108.0.0/16", discordips="", xips="",
                    sipips="", customips="", userdomains="example.org",
                    excludedomains="")
    if exists:
        hostlist["excludeipset"] = excluded
    config = {"Zapret": {
        "general": {"enabled": "1", "waninterface": "WAN", "divertport": "989"},
        "strategy": {"trafficargs": "--filter-tcp=443", "extraargs": ""},
        "hostlist": hostlist,
        "voice": {service: {"enabled": "0"} for service in
                  ("telegram", "discord", "x", "sip", "custom")},
    }}
    return env.from_string(TEMPLATE.read_text(encoding="utf-8")).render(
        OPNsense=config, helpers=Helpers(exists))


class NativeTemplateShellTests(unittest.TestCase):
    def test_real_rendered_shell_has_standalone_terminator(self):
        # Comparable to the owner's 1.78 MB rendered config.
        large_domains = "\n".join(f"host{i:05d}.example.org"
                                  for i in range(85000))
        values = (
            ("missing-node", "", False, ""),
            ("empty-node", "", True, ""),
            ("ipv4-cidr", "192.168.3.0/24", True, ""),
            ("ipv6-cidr", "2001:db8:1234::/48", True, ""),
            ("dual-stack", "192.0.2.0/24\n2001:db8::/32", True, ""),
            ("large-saved-domains", "192.168.3.0/24", True, large_domains),
        )
        for label, ipset, present, domains in values:
            with self.subTest(label=label):
                shell = render(ipset, exists=present, domains=domains)
                block = (f"EXCLUDE_IPSET=$(cat <<'{MARKER}'\n"
                         f"{ipset if present else ''}\n{MARKER}\n)")
                self.assertTrue(block in shell,
                                f"heredoc terminator missing for {label}")
                if ipset:
                    self.assertNotIn(ipset.splitlines()[-1] + MARKER, shell,
                                     f"joined terminator in {label}")
                syntax = subprocess.run(["/bin/sh", "-n"], input=shell,
                                        text=True, capture_output=True, timeout=20)
                self.assertEqual(0, syntax.returncode,
                                 f"{label}: shell rejected: {syntax.stderr[-500:]}")
                if domains:
                    self.assertTrue(domains in shell,
                                    "large unchanged domains mutated by render")


if __name__ == "__main__":
    unittest.main(verbosity=2)
