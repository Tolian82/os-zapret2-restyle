#!/usr/bin/env python3
"""Disposable Stage 5 guest C: A's *unchanged* Mk archive across a real kernel boot.

No alternate builder, pkg hook, lifecycle service, PF/IPFW manager or release.
The original reboot observer and historical RUNNING pkg path remain authoritative.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPORT = ROOT / "dist" / "stage5-native-same-archive-reboot.json"
STATUS = "PASS_STAGE5_ONE_ARCHIVE_REAL_KERNEL_SHARED_VOICE"
KEY = "ZAPRET2_STAGE5_SAME_ARCHIVE_REBOOT"


class Refusal(RuntimeError):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_same_archive_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guard(env):
    required = (
        "ZAPRET2_STAGE5_CROSS_VM", "ZAPRET2_STAGE5_RUNNING_VOICE_ARTIFACT",
        "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK", "ZAPRET2_NATIVE_BUILD_CI",
        "ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST",
        "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
        "ZAPRET2_STAGE2_REAL_ACTIVE_SERVICE",
        "ZAPRET2_STAGE2_REAL_BOOT_SYSHOOK",
        "ZAPRET2_STAGE2_REAL_COMMON_VOICE",
        "ZAPRET2_STAGE5_REAL_SHARED_VOICE_REBOOT", KEY,
    )
    need(env.get("GITHUB_ACTIONS") == "true" and
         all(env.get(x) == "1" for x in required) and
         re.fullmatch(r"[a-f0-9]{40}", env.get("ZAPRET2_NATIVE_PROJECT_SHA", "")) is not None and
         env.get("ZAPRET2_STAGE0_PROJECT_SHA") == env.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "STAGE5_THIRD_GUEST_EXPLICIT_DISPOSABLE_SOURCE_OPTIN_REQUIRED")
    return env["ZAPRET2_NATIVE_PROJECT_SHA"]


def read_json(path):
    need(path.is_file() and not path.is_symlink(),
         "STAGE5_THIRD_GUEST_READONLY_RECEIPT_MISSING")
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise Refusal("STAGE5_THIRD_GUEST_INVALID_JSON_RECEIPT") from None
    need(isinstance(result, dict),
         "STAGE5_THIRD_GUEST_NONOBJECT_RECEIPT")
    return result


def clean_archive(source):
    standard = load("stage5-native-single-artifact.py")
    clean = read_json(standard.RECEIPT)
    digest = standard.check_record(clean, standard.ARCHIVE, source)
    return standard, clean, digest


def validate_c(c, source, sha):
    required = (
        "genuine_new_kernel", "original_shared_fd9_restored",
        "two_scoped_ipfw_rules_and_voice_table_restored",
        "pkgdb_and_original_four_hooks_unchanged",
        "same_archive_before_after_kernel",
    )
    need(c.get("schema") == 1 and c.get("status") == STATUS and
         c.get("source_sha") == source and
         c.get("archive_sha256") == sha and
         re.fullmatch(r"[a-f0-9]{64}", sha) is not None and
         c.get("owner_appliance_modified") is False and
         c.get("physical_browser_click_tested") is False and
         c.get("real_wan_dpi_bypass_proven") is False and
         all(c.get(key) is True for key in required),
         "STAGE5_THIRD_GUEST_KERNEL_OR_ARCHIVE_RECEIPT_UNQUALIFIED")
    return sha


def prepare(old_archive):
    source = guard(os.environ)
    standard, clean, sha = clean_archive(source)
    need(not REPORT.exists() and not REPORT.is_symlink() and
         old_archive.is_file() and not old_archive.is_symlink(),
         "STAGE5_THIRD_GUEST_FOREIGN_RECEIPT_OR_MISSING_PREDECESSOR")
    running = load("stage2-opnsense-real-native-running-upgrade.py")
    built = {
        "status": "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY",
        "project_sha": source,
        "output": "dist/" + standard.ARCHIVE.name,
        "real_native_pkg": {"sha256": sha},
    }
    # The existing Stage 2 native pkg path is used with the qualified
    # prebuilt artifact. It MUST NOT call native.build() in guest C.
    installed = running.execute(old_archive, prebuilt_native_report=built)
    need(installed.get("status") == "PASS_REAL_RUNNING_NATIVE_VERSION_REPLACEMENT" and
         installed.get("new_temporary_pkg_sha256") == sha and
         installed.get("tested_exact_project_sha") == source and
         installed.get("installed_original_four_hooks_equal") is True and
         installed.get("restored_runtime", {}).get("real_new_service_running") is True and
         installed.get("owner_appliance_modified") is False,
         "STAGE5_THIRD_GUEST_PREBUILT_RUNNING_UPGRADE_UNQUALIFIED")
    reboot = load("stage5-native-real-shared-voice-reboot.py")
    prepared = reboot.prepare()
    need(prepared.get("status") == "PREPARED_REAL_KERNEL_SHARED_STRATEGIES_VOICE" and
         prepared.get("physical_native_archive_sha256") == sha and
         prepared.get("passive_native_stop_start_observers") is True and
         prepared.get("real_kernel_reboot_not_yet_observed") is True,
         "STAGE5_THIRD_GUEST_REBOOT_PREPARATION_UNQUALIFIED")
    record = read_json(reboot.RECORD)
    need(record.get("source_sha") == source and
         record.get("physical_native_package_sha256") == sha,
         "STAGE5_THIRD_GUEST_PREBOOT_ARCHIVE_DRIFT")
    print("STAGE5_THIRD_GUEST_PREPARED_ARCHIVE_SHA=" + sha, flush=True)


def verify():
    source = guard(os.environ)
    _, clean, sha = clean_archive(source)
    need(not REPORT.exists() and not REPORT.is_symlink(),
         "STAGE5_THIRD_GUEST_RECEIPT_ALREADY_PRESENT")
    reboot = load("stage5-native-real-shared-voice-reboot.py")
    result = reboot.verify()
    need(result.get("status") == "PASS_REAL_KERNEL_SHARED_STRATEGIES_VOICE_REBOOT" and
         result.get("physical_native_archive_sha256") == sha and
         result.get("same_physical_archive_before_and_after_kernel") is True and
         result.get("genuine_different_kernel_boot") is True and
         result.get("one_original_shared_fd9_committed_journal_restored") is True and
         result.get("two_scoped_voice_and_tcp_ipfw_rules_restored") is True and
         result.get("exact_voice_table_restored") is True and
         result.get("original_four_hooks_and_pkgdb_verified") is True and
         result.get("owner_appliance_modified") is False,
         "STAGE5_THIRD_GUEST_REAL_KERNEL_REBOOT_NOT_PROVEN")
    row = {
        "schema": 1, "status": STATUS, "source_sha": source,
        "archive_sha256": sha,
        "genuine_new_kernel": True,
        "original_shared_fd9_restored": True,
        "two_scoped_ipfw_rules_and_voice_table_restored": True,
        "pkgdb_and_original_four_hooks_unchanged": True,
        "same_archive_before_after_kernel": True,
        "owner_appliance_modified": False,
        "physical_browser_click_tested": False,
        "real_wan_dpi_bypass_proven": False,
    }
    validate_c(row, source, sha)
    with REPORT.open("x", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    print("PASS_STAGE5_THIRD_GUEST_REAL_KERNEL_REBOOT_SHA=" + sha, flush=True)


def verify_c(source):
    standard, _, sha = clean_archive(source)
    result = read_json(REPORT)
    validate_c(result, source, sha)
    need(standard.ARCHIVE.is_file(),
         "STAGE5_THIRD_GUEST_COPIED_ARCHIVE_MISSING")
    print("PASS_STAGE5_THIRD_GUEST_COPYBACK_SHA=" + sha)


def verify_three(source):
    verify_c(source)
    running = load("stage5-native-running-voice-artifact.py")
    standard = load("stage5-native-single-artifact.py")
    clean = read_json(standard.RECEIPT)
    live = read_json(running.RECEIPT)
    running.receipt_check(live, standard.ARCHIVE, source)
    combined_sha = running.cross_receipt_binding(clean, live)
    validate_c(read_json(REPORT), source, combined_sha)
    print("PASS_STAGE5_ONE_ARCHIVE_THREE_DISPOSABLE_GUESTS_SHA=" + combined_sha)


def self_test():
    good = {
        "schema": 1, "status": STATUS, "source_sha": "a" * 40,
        "archive_sha256": "b" * 64,
        "genuine_new_kernel": True, "original_shared_fd9_restored": True,
        "two_scoped_ipfw_rules_and_voice_table_restored": True,
        "pkgdb_and_original_four_hooks_unchanged": True,
        "same_archive_before_after_kernel": True,
        "owner_appliance_modified": False,
        "physical_browser_click_tested": False,
        "real_wan_dpi_bypass_proven": False,
    }
    assert validate_c(good, "a" * 40, "b" * 64)
    for key, value in (
        ("source_sha", "c" * 40), ("archive_sha256", "d" * 64),
        ("genuine_new_kernel", False), ("original_shared_fd9_restored", False),
        ("same_archive_before_after_kernel", False),
        ("owner_appliance_modified", True), ("status", "NOT_TESTED"),
    ):
        bad = {**good, key: value}
        try:
            validate_c(bad, "a" * 40, "b" * 64)
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe third-guest receipt accepted: " + key)
    try:
        guard({})
    except Refusal:
        pass
    else:
        raise AssertionError("missing disposable opt-ins accepted")
    print("PASS_STAGE5_THIRD_GUEST_REBOOT_ARCHIVE_NEGATIVE_CONTRACTS")


def main():
    args = sys.argv[1:]
    if args == ["--self-test"]:
        self_test()
    elif len(args) == 2 and args[0] == "prepare":
        prepare(Path(args[1]))
    elif args == ["verify"]:
        verify()
    elif len(args) == 2 and args[0] in ("verify-c", "verify-three"):
        if args[0] == "verify-c":
            verify_c(args[1])
        else:
            verify_three(args[1])
    else:
        raise Refusal("STAGE5_THIRD_GUEST_INVALID_OPERATION")


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE5_THIRD_GUEST=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
