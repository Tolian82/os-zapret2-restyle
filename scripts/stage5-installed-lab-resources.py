#!/usr/bin/env python3
"""Installed Strategy Lab/Extra Resources offline Stage 5 evidence on OPNsense.

Uses the actual pkg-owned launcher and Extra Resources modules. The Strategy
Lab launcher receives a private empty run/log tree, never a live job. The
resource suites use synthetic archives, scratch Git repositories and no fetch.
No Strategy Lab search, real install/remove, WAN or appliance Config mutation.
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
import tempfile

HERE = Path(__file__).resolve().parent
SCRIPT_DIR = Path("/usr/local/opnsense/scripts/OPNsense/Zapret")
OPTIN = "ZAPRET2_STAGE5_INSTALLED_LAB_RESOURCES"
STATUS = "PASS_STAGE5_INSTALLED_LAB_STATUS_EXTRA_OFFLINE"
SUITES = ("test-extra-resources-preflight.py",
          "test-extra-resources-inventory-cache.py")


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_lab_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def installed_entrypoints():
    paths = (
        "strategy_lab_launcher.sh",
        "strategy_lab/common.sh", "strategy_lab/state.sh",
        "strategy_lab/launch.sh", "strategy_lab/query.sh",
        "extra_resources_preflight.py",
        "extra_resources_inventory_cache.py",
    )
    for name in paths:
        source = SCRIPT_DIR / name
        info = source.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
             not source.is_symlink() and info.st_size >= 500,
             "LAB_EXTRA_INSTALLED_ENTRYPOINT_MISSING:" + name)
    return len(paths)


def extra_suites(*, installed):
    env = os.environ.copy()
    if installed:
        env[OPTIN] = "1"
        env["GITHUB_ACTIONS"] = "true"
    else:
        env.pop(OPTIN, None)
    results = {}
    for name in SUITES:
        run = subprocess.run(
            [sys.executable, str(HERE / name)], capture_output=True,
            text=True, timeout=180, env=env, check=False)
        count = re.search(r"Ran (\d+) tests? in", run.stderr)
        if (run.returncode != 0 or count is None or int(count.group(1)) < 8 or
                re.search(r"(?m)^OK$", run.stderr) is None):
            print("LAB_EXTRA_SUITE_REFUSED:" + name + ":" +
                  run.stderr[-900:], file=sys.stderr)
            raise Refusal("LAB_EXTRA_INSTALLED_SUITE_FAILED:" + name)
        results[name] = int(count.group(1))
    return results


def installed_lab_status():
    # All launcher state, locks, pointers, jobs, and logs are private. The
    # installed modules/launcher are never copied or replaced with test mocks.
    with tempfile.TemporaryDirectory(prefix="stage5-lab-installed-") as tmp:
        root = Path(tmp)
        env = os.environ.copy()
        env.update({
            "SCRIPT_DIR": str(SCRIPT_DIR),
            "STRATEGY_LAB_RUN_DIR": str(root / "run"),
            "STRATEGY_LAB_LOG_DIR": str(root / "log"),
        })
        launcher = SCRIPT_DIR / "strategy_lab_launcher.sh"

        def check(args, code):
            run = subprocess.run(
                ["/bin/sh", str(launcher), *args],
                capture_output=True, text=True, env=env,
                timeout=60, check=False)
            need(run.returncode == code,
                 "LAB_INSTALLED_LAUNCHER_RETURN_CODE:" + args[0])
            return run

        for args in (("status", "@active"), ("status", "-")):
            output = check(args, 0)
            try:
                value = json.loads(output.stdout)
            except ValueError:
                raise Refusal("LAB_INSTALLED_IDLE_OUTPUT_NOT_JSON") from None
            need(value == {"status": "idle"},
                 "LAB_INSTALLED_EXPECTED_PRIVATE_IDLE_STATUS")

        invalid_job = check(("status", "../untrusted"), 64)
        need("invalid job id" in invalid_job.stderr,
             "LAB_INSTALLED_INVALID_JOB_NOT_REFUSED")
        invalid_target = check(("start", "../untrusted", "standard", "en"), 64)
        need("invalid target" in invalid_target.stderr,
             "LAB_INSTALLED_INVALID_TARGET_NOT_REFUSED")
        missing_job = check(("status", "job.Missing"), 1)
        try:
            missing = json.loads(missing_job.stdout)
        except ValueError:
            raise Refusal("LAB_INSTALLED_MISSING_JOB_OUTPUT_NOT_JSON") from None
        need(missing.get("status") == "error" and
             "not found" in missing.get("message", "").lower(),
             "LAB_INSTALLED_MISSING_JOB_ACCEPTED")
        jobs = root / "run" / "jobs"
        need(jobs.is_dir() and not list(jobs.iterdir()) and
             not (root / "run" / "active.job").exists() and
             not (root / "run" / "latest.job").exists(),
             "LAB_INSTALLED_INVALID_REQUEST_STARTED_JOB")
    return {
        "idle_status_queries": 2,
        "invalid_job_refused": True,
        "invalid_target_refused": True,
        "missing_job_refused": True,
        "no_lab_job_launched": True,
    }


def self_test():
    results = extra_suites(installed=False)
    need(len(results) == 2 and all(value >= 8 for value in results.values()),
         "LAB_EXTRA_SOURCE_OFFLINE_PREFLIGHT_NOT_PROVEN")
    print("PASS: existing source Extra Resources preflight and inventory suites")
    return 0


def execute():
    for key in ("ZAPRET2_NATIVE_BUILD_CI",
                "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE", OPTIN):
        need(os.environ.get(key) == "1",
             "LAB_EXTRA_DISPOSABLE_OPTIN_MISSING:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true",
         "LAB_EXTRA_NOT_IN_DISPOSABLE_GITHUB_CI")
    active = load("stage2-opnsense-real-native-active-service.py")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    engine_sha = active.guest_preflight()
    files = installed_entrypoints()
    before = common.witness(active, engine_sha, running=True)
    config = active.CONFIG.read_bytes()
    journal = common.JOURNAL.read_bytes()
    ipfw = active.plugin_rules()
    lab = installed_lab_status()
    extra = extra_suites(installed=True)
    after = common.witness(active, engine_sha, running=True)
    need(before == after and active.CONFIG.read_bytes() == config and
         common.JOURNAL.read_bytes() == journal and
         active.plugin_rules() == ipfw,
         "LAB_EXTRA_CHANGED_CONFIG_FD9_ENGINE_OR_IPFW")
    result = {
        "schema": 1, "status": STATUS,
        "installed_file_entrypoints": files,
        "installed_strategy_lab": lab,
        "installed_extra_suites": extra,
        "native_config_fd9_and_ipfw_unchanged": True,
        "strategy_lab_real_search_tested": False,
        "extra_resources_real_install_or_remove_tested": False,
        "wan_ipv6_media_tested": False,
        "isolated_private_fixtures": True,
    }
    print("STAGE5_INSTALLED_LAB_EXTRA=" + json.dumps(result, sort_keys=True))
    return result


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("LAB_EXTRA_USAGE_SELF_TEST_OR_RUN")
    except (Refusal, OSError, ValueError, TypeError,
            subprocess.TimeoutExpired) as err:
        print("STAGE5_INSTALLED_LAB_EXTRA=REFUSED:" + str(err),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
