#!/usr/bin/env python3
"""Stage 5: installed Strategy Lab mock-probe job and resource transaction suites.

Real package-owned Python and shell entrypoints, PRIVATE mock-driven fixture
data and lifecycle, no network probe, no real extra-resource mutation, no GUI.
Runs only on a disposable OPNsense 26.7 GitHub Actions guest.
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
INSTALLED = Path("/usr/local/opnsense/scripts/OPNsense/Zapret")
FLAG = "ZAPRET2_STAGE5_INSTALLED_FUNCTIONS"
STATUS = "PASS_STAGE5_INSTALLED_LAB_MOCKED_JOB_RESOURCE_TRANSACTION"


class Refusal(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_functional_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def entrypoint_files():
    names = (
        "strategy_lab_launcher.sh", "strategy_lab_worker.sh",
        "strategy_lab_circular_launcher.sh", "strategy_lab_probe_runner.sh",
        "strategy_lab_python_launcher.sh", "strategy_lab_python_stage_adapter.sh",
        "strategy_lab/common.sh", "strategy_lab/query.sh", "strategy_lab/launch.sh",
        "extra_resources_transaction.py", "extra_resources_operation.py",
    )
    for name in names:
        path = INSTALLED / name
        info = path.lstat()
        need(stat.S_ISREG(info.st_mode) and not path.is_symlink() and
             info.st_nlink == 1 and info.st_size >= 100,
             "INSTALLED_FUNCTIONAL_ENTRYPOINT_INVALID:" + name)
    return len(names)


def offline_transaction(*, installed):
    env = os.environ.copy()
    if installed:
        env[FLAG] = "1"
        env["GITHUB_ACTIONS"] = "true"
    else:
        env.pop(FLAG, None)
    result = subprocess.run(
        [sys.executable, str(HERE / "test-extra-resources-transaction.py")],
        capture_output=True, text=True, env=env, check=False, timeout=280)
    match = re.search(r"Ran (\d+) tests? in", result.stderr)
    count = int(match.group(1)) if match else 0
    if (result.returncode != 0 or count < 35 or
            re.search(r"(?m)^OK$", result.stderr) is None):
        print("STAGE5_FUNCTIONAL_TX_REFUSED:" + result.stderr[-1600:],
              file=sys.stderr)
        raise Refusal("INSTALLED_RESOURCE_TRANSACTION_SUITE_FAILED")
    return count


def lab_mocked_jobs():
    # This existing test harness installs its service, lock and network mocks
    # under mktemp. Its root remains the checkout for fixture-only delegated
    # tests, while launcher/worker/probe orchestration are pkg-owned binaries.
    env = os.environ.copy()
    env[FLAG] = "1"
    env["GITHUB_ACTIONS"] = "true"
    result = subprocess.run(
        ["/bin/sh", str(HERE / "test-strategy-lab-e2e.sh")],
        capture_output=True, text=True, env=env, check=False, timeout=420)
    scenarios = re.findall(r"(?m)^E2E scenario=", result.stdout)
    ok = ("PASS: installed Strategy Lab mock-backed job lifecycle, "
          "errors, restoration and private circular flow")
    if (result.returncode != 0 or len(scenarios) < 8 or
            ok not in result.stdout or
            "E2E phase=circular-start" not in result.stdout):
        print("STAGE5_FUNCTIONAL_LAB_REFUSED:" +
              result.stdout[-1300:] + "\n" + result.stderr[-1300:],
              file=sys.stderr)
        raise Refusal("INSTALLED_LAB_MOCKED_JOB_E2E_FAILED")
    return len(scenarios)


def self_test():
    count = offline_transaction(installed=False)
    sh = subprocess.run(
        ["/bin/sh", "-n", str(HERE / "test-strategy-lab-e2e.sh")],
        capture_output=True, text=True, check=False, timeout=15)
    need(sh.returncode == 0, "LAB_FUNCTIONAL_SHELL_SYNTAX_FAILED")
    print("PASS_STAGE5_FUNCTIONAL_SOURCE_TX_CASES=" + str(count))
    print("PASS_STAGE5_FUNCTIONAL_SOURCE_LAB_SHELL_SYNTAX=1")
    return 0


def execute():
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI", FLAG):
        need(os.environ.get(key) == "1",
             "INSTALLED_FUNCTIONAL_DISPOSABLE_OPTIN_MISSING:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true",
         "INSTALLED_FUNCTIONAL_REQUIRES_GITHUB_DISPOSABLE_GUEST")
    active = load("stage2-opnsense-real-native-active-service.py")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    engine_sha = active.guest_preflight()
    files = entrypoint_files()
    before = common.witness(active, engine_sha, running=True)
    config = active.CONFIG.read_bytes()
    journal = common.JOURNAL.read_bytes()
    rules = active.plugin_rules()

    transaction_count = offline_transaction(installed=True)
    lab_job_count = lab_mocked_jobs()

    after = common.witness(active, engine_sha, running=True)
    need(before == after and active.CONFIG.read_bytes() == config and
         common.JOURNAL.read_bytes() == journal and
         active.plugin_rules() == rules,
         "INSTALLED_FUNCTIONAL_CHANGED_REAL_SERVICE_CONFIG_FD9_IPFW")
    receipt = {
        "schema": 1,
        "status": STATUS,
        "installed_entrypoints": files,
        "installed_resource_transaction_cases": transaction_count,
        "installed_lab_mocked_job_scenarios": lab_job_count,
        "real_config_shared_fd9_engine_ipfw_unchanged": True,
        "service_and_probes_mocked_in_private_job_harness": True,
        "actual_lab_network_probe_tested": False,
        "actual_extra_install_remove_tested": False,
        "physical_browser_click_tested": False,
        "wan_ipv6_media_tested": False,
        "owner_appliance_modified": False,
    }
    print("STAGE5_INSTALLED_FUNCTIONAL=" + json.dumps(receipt, sort_keys=True))
    return receipt


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("INSTALLED_FUNCTIONAL_USAGE_SELF_TEST_OR_RUN")
    except (Refusal, OSError, TypeError, ValueError, subprocess.TimeoutExpired) as exc:
        print("STAGE5_INSTALLED_FUNCTIONAL=REFUSED:" + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
