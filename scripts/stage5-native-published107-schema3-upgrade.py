#!/usr/bin/env python3
"""Published 0.6.5_107 RUNNING schema2 Auto -> current exact native pkg schema3.

Only a fresh disposable OPNsense 26.7 VM. Uses the genuine published _107
archive and its installed protected pkg-update service, not a replacement
installer or a synthetic observer. Never an owner appliance. The installed
user Config, original FD9, IPFW and dvtws2 are never fabricated.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OLD_VERSION = "0.6.5_107"
OLD_URL = ("https://github.com/Tolian82/os-zapret2-restyle/releases/"
           "download/v0.6.5_107/os-zapret2-restyle-0.6.5_107.pkg")
OLD_SHA256 = "85d8e6a1d00cc81d22e13aec6d3b8d1a59e65de6d223c5e4947c0e62e93ad8d7"
NAME = "os-zapret2-restyle"


class Refused(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refused(reason)


def load(file, module):
    spec = importlib.util.spec_from_file_location(module, HERE / file)
    need(spec is not None and spec.loader is not None,
         "NATIVE_SOURCE_LIBRARY_MISSING")
    instance = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(instance)
    return instance


def run(argv, timeout=180):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=timeout, check=False)


def manifest(pkg):
    item = run(["/usr/bin/tar", "-xOf", str(pkg), "+MANIFEST"], timeout=45)
    need(item.returncode == 0 and len(item.stdout) < 512 * 1024,
         "PUBLISHED_OR_NEW_MANIFEST_UNAVAILABLE")
    return json.loads(item.stdout)


def gate():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_PUBLISHED107_SCHEMA3_DISPOSABLE") == "1" and
         os.environ.get("ZAPRET2_PROTECTED_PKG_NATIVE_TEST") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "NOT_DISPOSABLE_PUBLISHED107_GUEST")
    v = run(["opnsense-version", "-a"])
    abi = run(["pkg", "config", "ABI"])
    need(v.returncode == 0 and v.stdout.strip().startswith("26.7") and
         abi.returncode == 0 and abi.stdout.strip() == "FreeBSD:15:amd64",
         "NATIVE_OPNSENSE_VERSION_OR_ABI_MISMATCH")
    need(run(["pkg", "info", "-e", NAME]).returncode == 1,
         "DISPOSABLE_107_GUEST_NOT_CLEAN")


def qualified_postboot_generation(protected, boot_id):
    """Record a genuine mismatched native owner without masking Boot evidence.

    The original protected fixture raises RuntimeError from need(), not a
    custom Refused type. A mismatch still makes mandatory acceptance fail.
    No user data or raw exception string is logged.
    """
    try:
        schema, learning = protected.original_auto_generation(boot_id, True)
    except RuntimeError:
        return 0, [], False
    return schema, learning, True


def main():
    gate()
    protected = load("stage5-native-protected-update.py",
                     "published107_protected_helpers")
    bridge = load("test-own70-native-package-handoff.py",
                  "published107_strategy_bridge")
    wan = load("p5b2b-native-witness.py", "published107_wan_model")
    g03 = load("stage2-opnsense-g03-first-install.py",
               "published107_native_g03")
    service = protected.SERVICE
    journal = protected.JOURNAL
    epoch = protected.EPOCHS
    config = protected.CONFIG
    candidate_version = ROOT.joinpath("VERSION").read_text().strip() + "_" + (
        re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$",
                  ROOT.joinpath("Makefile").read_text()).group(1))
    candidate = ROOT / "dist" / f"{NAME}-{candidate_version}.pkg"
    need(candidate.is_file() and not candidate.is_symlink() and
         manifest(candidate).get("name") == NAME and
         manifest(candidate).get("version") == candidate_version and
         manifest(candidate).get("abi") == "FreeBSD:15:amd64" and
         not protected.ACTIVE.exists() and
         not protected.MARKER.exists(),
         "EXACT_HEAD_CANDIDATE_OR_DISPOSABLE_GUARD_UNQUALIFIED")
    candidate_sha = protected.sha(candidate)

    # The predecessor is the immutable public release asset, never tag
    # source checked out and repackaged as a fake old plugin.
    old = Path("/root/os-zapret2-restyle-0.6.5_107.pkg")
    need(not old.exists() and not old.is_symlink(),
         "PREEXISTING_107_PACKAGE_FILE")
    downloaded = run(["/usr/bin/fetch", "-o", str(old), OLD_URL], timeout=120)
    need(downloaded.returncode == 0 and protected.sha(old) == OLD_SHA256 and
         manifest(old).get("name") == NAME and
         manifest(old).get("version") == OLD_VERSION and
         manifest(old).get("abi") == "FreeBSD:15:amd64",
         "PUBLISHED_107_ARCHIVE_SHA_OR_ABI_UNQUALIFIED")
    installed = run(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                     "add", "-f", str(old)], timeout=210)
    need(installed.returncode == 0 and
         protected.installed_version() == OLD_VERSION and
         run([str(service), "status"]).returncode == 1,
         "PUBLISHED_107_NATIVE_INSTALL_NOT_STOPPED")
    need(service.is_file() and service.lstat().st_nlink == 1 and
         (service.parent / "protected_pkg_update.py").is_file(),
         "PUBLISHED_107_PROTECTED_OWNER_NOT_INSTALLED")

    # GUI-Model and original configctl only, never manual XML construction.
    wan.set_guest_lo0()
    bridge.set_guest_list_mode()
    protected.seed_qualified_stable_tag_for_disposable_guest(g03)
    try:
        setup = g03.dispatch_and_poll()
    except (g03.Refusal, OSError, subprocess.TimeoutExpired):
        g03.bounded_disposable_failure_evidence()
        raise
    need(setup.get("installed") == "1" and setup.get("service") == "stopped",
         "PUBLISHED_107_UPSTREAM_V1_0_7_NOT_READY")
    for mode in ("list", "auto"):
        result = run(["/usr/local/sbin/configctl", "zapret",
                      "shared_apply", "strategies", bridge.request(mode)],
                     timeout=300)
        state = json.loads(journal.read_bytes())
        need(result.returncode == 0 and
             "applied-id=" in result.stdout and
             state.get("phase") == "committed" and
             run([str(service), "status"]).returncode == 0,
             "PUBLISHED_107_NATIVE_" + mode.upper() + "_APPLY_FAILED")

    predecessor = json.loads(journal.read_bytes())["detail"]["id"]
    old_schema, _ = protected.original_auto_generation(predecessor, True)
    pidfile = Path("/var/run/dvtws2.pid")
    previous_pid = pidfile.read_text().strip().split()[0]
    need(old_schema == 2 and previous_pid.isdecimal() and
         (epoch / predecessor / "epoch.json").is_file(),
         "PUBLISHED_107_NOT_RUNNING_ORIGINAL_SCHEMA2_AUTO")
    saved_config = protected.sha(config)
    engine = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
    need(engine.is_file() and not engine.is_symlink(),
         "PUBLISHED_107_ENGINE_MISSING")
    engine_sha = protected.sha(engine)

    # Run the genuine INSTALLED _107 service's protected pkg updater. It
    # performs original FD9 Stop -> native pkg -> successor FD9 Boot.
    updated = run([str(service), "pkg-update", str(candidate)], timeout=450)
    after_status = run([str(service), "status"]).returncode
    new_state = json.loads(journal.read_bytes())
    new_id = new_state.get("detail", {}).get("id", "")
    successor_schema = 0
    successor_learning = []
    if after_status == 0:
        successor_schema, successor_learning = protected.original_auto_generation(
            new_id, True)
    old_retired = protected.verified_old_auto_retirement(predecessor, 2, [])
    successor_pid = (pidfile.read_text().strip().split()[0]
                     if pidfile.is_file() and not pidfile.is_symlink()
                     else "missing")
    production = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
    result = {
        "schema": 1,
        "status": "PUBLISHED_107_TO_109_ORIGINAL_PROTECTED_AUTO",
        "published_old_version": OLD_VERSION,
        "candidate_version": candidate_version,
        "published_old_archive_sha256": OLD_SHA256,
        "candidate_sha256": candidate_sha,
        "old_schema2_generation": True,
        "protected_update_rc": updated.returncode,
        "verified_pkg_receipt":
            "pkg-update=verified-installed-and-restored" in updated.stdout,
        "new_pkgdb_version": protected.installed_version(),
        "new_source_exact": protected.sha(service) == protected.sha(production),
        "after_status_rc": after_status,
        "old_schema2_retired": old_retired,
        "old_schema2_observer_not_restarted": new_id != predecessor,
        "new_schema3_active": successor_schema == 3,
        "new_native_learning_profiles": len(successor_learning),
        "new_engine_pid_distinct":
            successor_pid.isdecimal() and successor_pid != previous_pid,
        "original_config_unchanged": protected.sha(config) == saved_config,
        "upstream_engine_sha_unchanged": protected.sha(engine) == engine_sha,
        "no_pkg_guard": not protected.ACTIVE.exists() and
            not protected.ACTIVE.is_symlink(),
        "no_restart_marker": not protected.MARKER.exists(),
        "owner_appliance_modified": False,
        "positive_real_isp_discovery_tested": False,
        "physical_powercut_tested": False,
    }
    print("NATIVE_PUBLISHED107_SCHEMA3_UPGRADE=" +
          json.dumps(result, sort_keys=True), flush=True)
    need(updated.returncode == 0 and result["verified_pkg_receipt"] and
         result["new_pkgdb_version"] == candidate_version and
         result["new_source_exact"] and after_status == 0 and
         old_retired and result["old_schema2_observer_not_restarted"] and
         successor_schema == 3 and len(successor_learning) >= 1 and
         result["new_engine_pid_distinct"] and
         result["original_config_unchanged"] and
         result["upstream_engine_sha_unchanged"] and
         result["no_pkg_guard"] and result["no_restart_marker"],
         "PUBLISHED_107_TO_109_SCHEMA3_NATIVE_UPGRADE_NOT_ACCEPTED")

    # Make real new schema3 Stop/Boot operate AFTER cross-version migration,
    # not merely rely on the replacement install's self-report.
    stopped = run([str(service), "stop"], timeout=240)
    physical = protected.verified_old_auto_retirement(
        new_id, successor_schema, successor_learning)
    booted = run([str(service), "start"], timeout=260)
    bootstate = json.loads(journal.read_bytes())
    boot_id = bootstate.get("detail", {}).get("id", "")
    boot_status = run([str(service), "status"]).returncode
    boot_schema, boot_learning, map_consistent = qualified_postboot_generation(
        protected, boot_id)
    guard = re.search(
        r"(?m)^native-common-boot-guard="
        r"(saved-candidate|candidate-identity|build-command|build-preflight|"
        r"execute|receipt|ordinary-activate|ordinary-commit)$",
        booted.stderr)
    print("NATIVE_PUBLISHED107_SCHEMA3_POSTBOOT=" + json.dumps({
        "stop_rc": stopped.returncode,
        "retired_source_verified": physical,
        "boot_rc": booted.returncode,
        "boot_guard": guard.group(1) if guard else "unknown",
        "boot_status_rc": boot_status,
        "journal_phase": bootstate.get("phase") if bootstate.get("phase") in (
            "committed", "prepared", "activating", "activated",
            "config-saved", "epoch-finalizing", "requires-review",
            "restored") else "other",
        "generation_changed": boot_id not in (predecessor, new_id),
        "generation_map_consistent": map_consistent,
        "boot_native_schema3": boot_schema == 3,
        "learning_count": len(boot_learning),
        "config_unchanged": protected.sha(config) == saved_config,
        "engine_unchanged": protected.sha(engine) == engine_sha,
    }, sort_keys=True), flush=True)
    need(stopped.returncode == 0 and physical and
         booted.returncode == 0 and boot_status == 0 and map_consistent and
         boot_id not in (predecessor, new_id) and boot_schema == 3 and
         len(boot_learning) >= 1 and
         protected.sha(config) == saved_config and
         protected.sha(engine) == engine_sha and
         not protected.ACTIVE.exists(),
         "PUBLISHED_107_MIGRATED_SCHEMA3_STOP_BOOT_NOT_VERIFIED")
    print("NATIVE_PUBLISHED107_SCHEMA3=PASS_PUBLISHED_107_PROTECTED_UPGRADE"
          "_NEW_NATIVE_N_STOP_BOOT", flush=True)


if __name__ == "__main__":
    try:
        if sys.argv[1:] != []:
            raise Refused("INVALID_NATIVE_TEST_ARGUMENTS")
        main()
    except (Refused, RuntimeError, OSError, ValueError, TypeError, KeyError,
            subprocess.TimeoutExpired) as exc:
        print("NATIVE_PUBLISHED107_SCHEMA3=REFUSED:" + str(exc)[:180],
              file=sys.stderr)
        sys.exit(2)
