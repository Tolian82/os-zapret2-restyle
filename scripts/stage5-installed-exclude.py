#!/usr/bin/env python3
"""Bounded installed Exclude backend regression on a disposable OPNsense 26.7 VM.

Reuses existing policy suites against their installed package-owned Python
modules. All test data lives in private scratch; no native Apply or live traffic.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

HERE = Path(__file__).resolve().parent
BACKEND = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
OPTIN = "ZAPRET2_STAGE5_INSTALLED_EXCLUDE"
STATUS = "PASS_STAGE5_INSTALLED_EXCLUDE_OFFLINE_BACKEND"
SUITES = ("test-global-exclusions.py", "test-ipset-policy.py")


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "exclude_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backend_files():
    for name in ("global_exclusions.py", "ipset_policy.py"):
        path = BACKEND / name
        info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
             not path.is_symlink() and info.st_size > 1000,
             "EXCLUDE_INSTALLED_BACKEND_NOT_PKG_FILE:" + name)


def suites(*, installed):
    env = os.environ.copy()
    if installed:
        env[OPTIN] = "1"
        env["GITHUB_ACTIONS"] = "true"
    else:
        env.pop(OPTIN, None)
    completed = {}
    for filename in SUITES:
        result = subprocess.run(
            [sys.executable, str(HERE / filename)],
            text=True, capture_output=True, env=env, timeout=160, check=False)
        match = re.search(r"Ran (\d+) tests? in", result.stderr)
        if result.returncode or match is None or int(match.group(1)) < 8 or \
                re.search(r"(?m)^OK$", result.stderr) is None:
            # These two suites use synthetic public fixture data only.
            print("EXCLUDE_SUITE_REFUSED:" + filename + ":" +
                  result.stderr[-1200:], file=sys.stderr)
            raise Refusal("EXCLUDE_INSTALLED_TEST_SUITE_FAILED:" + filename)
        completed[filename] = int(match.group(1))
    return completed


def self_test():
    result = suites(installed=False)
    need(all(count >= 8 for count in result.values()),
         "EXCLUDE_OFFTARGET_SOURCE_SUITE_INCOMPLETE")
    print("PASS: source Exclude/IPSET production-policy suites and CLI negatives")
    return 0


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get(OPTIN) == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.environ.get("ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE") == "1",
         "EXCLUDE_INSTALLED_DISPOSABLE_OPTIN_REQUIRED")
    active = load("stage2-opnsense-real-native-active-service.py")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    engine_sha = active.guest_preflight()
    test_backend_files()
    before = common.witness(active, engine_sha, running=True)
    saved = active.CONFIG.read_bytes()
    journal = common.JOURNAL.read_bytes()
    ipfw = active.plugin_rules()
    completed = suites(installed=True)
    after = common.witness(active, engine_sha, running=True)
    need(before == after and active.CONFIG.read_bytes() == saved and
         common.JOURNAL.read_bytes() == journal and
         active.plugin_rules() == ipfw,
         "EXCLUDE_INSTALLED_TEST_CHANGED_CONFIG_FD9_ENGINE_OR_IPFW")
    report = {
        "schema": 1, "status": STATUS,
        "installed_policy_suites": completed,
        "installed_global_exclusions_cli": True,
        "installed_dualstack_ipset_policy": True,
        "invalid_apply_argv_and_witness_unchanged": True,
        "native_config_fd9_and_ipfw_unchanged": True,
        "isolated_scratch_only": True,
        "real_wan_or_ipv6_packets_tested": False,
        "browser_gui_click_tested": False,
    }
    print("STAGE5_INSTALLED_EXCLUDE=" + json.dumps(report, sort_keys=True))
    return report


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("EXCLUDE_INSTALLED_USAGE_SELF_TEST_OR_RUN")
    except (Refusal, OSError, ValueError, TypeError, subprocess.TimeoutExpired) as error:
        print("STAGE5_INSTALLED_EXCLUDE=REFUSED:" + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
