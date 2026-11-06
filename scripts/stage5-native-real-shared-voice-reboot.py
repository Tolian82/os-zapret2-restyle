#!/usr/bin/env python3
"""One real OPNsense kernel reboot of the existing shared Strategies/Voice owner.

This is a disposable CI-only extension of the already accepted Stage2 passive
20-zapret syshook observation, NOT an alternate product hook or a simulated boot.
Stop/start observers never start or stop the service themselves.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

HERE = Path(__file__).resolve().parent
ROOT = Path("/root/stage5-zapret-voice-real-kernel-boot")
RECORD = ROOT / "prepared.json"
OPTIN = "ZAPRET2_STAGE5_REAL_SHARED_VOICE_REBOOT"
HOOKS = {
    phase: Path("/usr/local/etc/rc.syshook.d") / phase /
           "21-zapret2-stage5-voice-boot-observer"
    for phase in ("start", "stop")
}


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_voice_boot_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


boot = load("stage2-opnsense-real-native-boot-syshook.py")
common = load("stage2-opnsense-real-native-shared-voice.py")
active = boot.active
need = active.need
Refusal = active.Refusal


def sha(data):
    return hashlib.sha256(data).hexdigest()


def gate():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("ZAPRET2_STAGE2_REAL_COMMON_VOICE") == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true",
         "VOICE_REBOOT_EXPLICIT_DISPOSABLE_NATIVE_CI_OPTIN_REQUIRED")
    # Existing boot gate checks real FreeBSD guest, exact source SHA,
    # installed official package and unmodified pkg-owned product hooks.
    return boot.gate()


def hook_bytes(phase):
    """The accepted passive witness, plus a read-only Voice-table snapshot."""
    need(phase in HOOKS, "VOICE_REBOOT_INVALID_OBSERVER_PHASE")
    original = boot.observe_bytes(phase).decode("ascii")
    old_name = str(boot.ROOT / phase)
    anchor = 'printf "COMPLETE\\n" > "' + old_name + '.done"\n'
    need(original.count(anchor) == 1, "VOICE_REBOOT_BOOT_WITNESS_DRIFT")
    extra = (
        '/sbin/ipfw table zapret2_voice_telegram list > "' +
        old_name + '.table" 2> "' + old_name + '.table.err"\n'
        'printf "%s\\n" "$?" > "' + old_name + '.table.rc"\n'
    )
    return original.replace(anchor, extra + anchor).replace(
        str(boot.ROOT), str(ROOT)).encode("ascii")


def observe(phase):
    need(boot.regular_bytes(HOOKS[phase], 0o755) == hook_bytes(phase),
         "VOICE_REBOOT_PASSIVE_OBSERVER_CONTENT_CHANGED")
    fields = {}
    for suffix in ("bootid", "status", "status.rc", "ipfw", "ipfw.rc",
                   "pid", "table", "table.rc"):
        value = boot.regular_bytes(ROOT / (phase + "." + suffix), 0o600)
        fields[suffix] = value.decode("utf-8").strip()
    need(boot.regular_bytes(ROOT / (phase + ".done"), 0o600).strip() ==
         b"COMPLETE" and fields["status.rc"] == "0" and
         fields["ipfw.rc"] == "0",
         "VOICE_REBOOT_PASSIVE_OBSERVER_INCOMPLETE")
    return fields


def foreign_rules(lines):
    return [line for line in lines if not re.match(r"^190(?:0\d|10)\s", line)]


def all_rules():
    response = active.cmd(["/sbin/ipfw", "-q", "list"], timeout=20)
    need(response.returncode == 0, "VOICE_REBOOT_CANNOT_READ_IPFW")
    return response.stdout.splitlines()


def qualify_reboot(record, stop, start, after, current_boot):
    need(current_boot != record["initial_boot"] and
         stop["bootid"] == record["initial_boot"] and
         start["bootid"] == current_boot,
         "VOICE_REBOOT_DISTINCT_NATIVE_KERNELS_NOT_PROVEN")
    need(stop["status"] == "zapret is not running" and
         stop["pid"] == "ABSENT" and not boot.rule_lines(stop["ipfw"]) and
         common.TARGET not in stop["table"],
         "VOICE_REBOOT_SHUTDOWN_LEFT_OWNED_RUNTIME")
    # The genuine stock configctl status is exactly "zapret is running".
    # The passive syshook separately records the pidfile; a forged text
    # suffix must not stand in for the independently verified real process.
    need(start["status"].strip() == "zapret is running" and
         start["pid"].isdecimal() and int(start["pid"]) > 1 and
         int(start["pid"]) != record["old_pid"] and
         int(start["pid"]) == after["pid"],
         "VOICE_REBOOT_NATIVE_SYSHOOK_DID_NOT_START_NEW_ENGINE")
    start_rules = common.checked_rules(boot.rule_lines(start["ipfw"]))
    need(start_rules == after["rules"] == record["old_rules"] and
         foreign_rules(start["ipfw"].splitlines()) == record["foreign_rules"],
         "VOICE_REBOOT_NATIVE_IPFW_OR_FOREIGN_RULE_DRIFT")
    need(start["table.rc"] == "0" and common.TARGET in start["table"],
         "VOICE_REBOOT_PASSIVE_VOICE_IPFW_TABLE_NOT_RESTORED")
    need(after["id"] == record["original_journal_owner_id"],
         "VOICE_REBOOT_ORIGINAL_FD9_OWNER_JOURNAL_LOST")
    return True


def physical_archive():
    archive = active.ROOT / "dist" / (
        active.PACKAGE + "-" + active.qualified_revision() + ".pkg")
    need(archive.is_file() and not archive.is_symlink() and
         archive.stat().st_size > 0,
         "VOICE_REBOOT_EXACT_MK_ARCHIVE_NOT_PRESERVED")
    return archive


def pkgdb_manifest_sha():
    # pkg's own RAW installed manifest includes the retained native package
    # script metadata; it must remain byte-identical through real kernel boot.
    result = active.cmd(["/usr/local/sbin/pkg", "info", "-R",
                         active.PACKAGE], timeout=30)
    need(result.returncode == 0 and result.stdout.strip(),
         "VOICE_REBOOT_INSTALLED_PKGDB_RAW_MANIFEST_UNAVAILABLE")
    return sha(result.stdout.encode("utf-8"))


def package_integrity():
    # Stock pkgdb checks installed file SHA, without edits or relinks.
    response = active.cmd(["/usr/local/sbin/pkg", "check", "-s",
                           active.PACKAGE], timeout=180)
    need(response.returncode == 0, "VOICE_REBOOT_PKG_OWNED_BYTES_CHANGED")


def prepare():
    engine_sha = gate()
    need(not ROOT.exists() and not ROOT.is_symlink() and
         all(not h.exists() and not h.is_symlink() for h in HOOKS.values()),
         "VOICE_REBOOT_FOREIGN_OR_STALE_TEST_OBSERVER_PRESENT")
    ordinary = active.live_state(engine_sha)
    # Stock native Config normalization and exact Voice OFF fixture,
    # then real configd Apply. No private boot/start implementation.
    _, foreign, strategies = common.prepare_fixture(active, boot)
    need(active.live_state(engine_sha) == ordinary,
         "VOICE_REBOOT_DRAFT_MODIFIED_LIVE_OWNER")
    common.invoke(active, "/usr/local/sbin/configctl",
                  "zapret", "telegram_voice_enable", timeout=600)
    current = common.witness(active, engine_sha, running=True, page="voice")
    saved = active.CONFIG.read_bytes()
    need(boot.config_except_model(saved) == foreign and
         boot.protected_model_values(saved) == strategies and
         current["pid"] != ordinary["pid"],
         "VOICE_REBOOT_COMMON_APPLY_CHANGED_FOREIGN_CONFIG_OR_OWNER")
    package_integrity()
    package_db_sha = pkgdb_manifest_sha()
    archive_sha = sha(physical_archive().read_bytes())
    for phase, path in boot.PRODUCT.items():
        need(path.read_bytes() ==
             (active.ROOT / "src/etc/rc.syshook.d" / phase / "20-zapret").read_bytes(),
             "VOICE_REBOOT_PRODUCTION_HOOK_CHANGED")
    now = boot.boot_id()
    record = {
        "schema": 1, "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        "pkg_version": active.qualified_revision(),
        "engine_sha": engine_sha,
        "physical_native_package_sha256": archive_sha,
        "native_pkgdb_raw_manifest_sha256": package_db_sha,
        "initial_boot": now,
        "old_pid": current["pid"],
        "old_rules": current["rules"],
        "original_journal_owner_id": current["id"],
        "foreign_rules": foreign_rules(all_rules()),
        "config_sha": sha(saved),
        "hook_sha": {phase: sha(path.read_bytes())
                     for phase, path in boot.PRODUCT.items()},
    }
    ROOT.mkdir(mode=0o700)
    need(ROOT.stat().st_uid == 0 and
         stat.S_IMODE(ROOT.stat().st_mode) == 0o700,
         "VOICE_REBOOT_TEST_RECORD_DIRECTORY_UNSAFE")
    boot.write_owned(ROOT / "preboot-config.xml", saved, 0o600)
    boot.write_owned(RECORD, (json.dumps(record, sort_keys=True) + "\n").encode(),
                     0o600)
    for phase, hook in HOOKS.items():
        boot.write_owned(hook, hook_bytes(phase), 0o755)
        need(boot.regular_bytes(hook, 0o755) == hook_bytes(phase),
             "VOICE_REBOOT_TEST_OBSERVER_NOT_BYTE_IDENTICAL")
    return {
        "schema": 1, "status": "PREPARED_REAL_KERNEL_SHARED_STRATEGIES_VOICE",
        "before_boot": now, "one_real_owner": True,
        "two_scoped_rules_and_one_table": True,
        "physical_native_archive_sha256": archive_sha,
        "passive_native_stop_start_observers": True,
        "real_kernel_reboot_not_yet_observed": True,
        "owner_appliance_modified": False,
    }


def verify():
    engine_sha = gate()
    need(ROOT.is_dir() and not ROOT.is_symlink() and
         ROOT.stat().st_uid == 0 and
         stat.S_IMODE(ROOT.stat().st_mode) == 0o700,
         "VOICE_REBOOT_TEST_EVIDENCE_SCOPE_UNTRUSTED")
    record = json.loads(boot.regular_bytes(RECORD, 0o600))
    need(record.get("schema") == 1 and
         record.get("source_sha") == os.environ["ZAPRET2_NATIVE_PROJECT_SHA"] and
         record.get("pkg_version") == active.qualified_revision() and
         record.get("engine_sha") == engine_sha and
         record.get("physical_native_package_sha256") ==
         sha(physical_archive().read_bytes()),
         "VOICE_REBOOT_SOURCE_ABI_AND_PACKAGE_CHANGED")
    for phase, source in boot.PRODUCT.items():
        need(sha(source.read_bytes()) == record["hook_sha"][phase],
             "VOICE_REBOOT_PRODUCTION_SYSHOOK_CHANGED_AFTER_BOOT")
    stop, start = observe("stop"), observe("start")
    current = common.witness(active, engine_sha, running=True, page="voice")
    qualify_reboot(record, stop, start, current, boot.boot_id())
    previous = boot.regular_bytes(ROOT / "preboot-config.xml", 0o600)
    need(sha(previous) == record["config_sha"], "VOICE_REBOOT_PREBOOT_CONFIG_CHANGED")
    after = active.CONFIG.read_bytes()
    # Native boot may update Config revision metadata/serialization only.
    policy = load("stage2-opnsense-real-native-stopped-upgrade.py")
    need(policy.normalized_config(previous) == policy.normalized_config(after),
         "VOICE_REBOOT_SAVED_CONFIG_CHANGED_ACROSS_ACTUAL_KERNEL")
    need(foreign_rules(all_rules()) == record["foreign_rules"],
         "VOICE_REBOOT_UNRELATED_IPFW_RULE_CHANGED")
    package_integrity()
    need(pkgdb_manifest_sha() == record["native_pkgdb_raw_manifest_sha256"],
         "VOICE_REBOOT_PKGDB_SCRIPT_METADATA_CHANGED")
    for phase, hook in HOOKS.items():
        need(boot.regular_bytes(hook, 0o755) == hook_bytes(phase),
             "VOICE_REBOOT_OBSERVER_REPLACED_BY_FOREIGN_CONTENT")
        hook.unlink()
    need(all(not h.exists() and not h.is_symlink()
             for h in HOOKS.values()), "VOICE_REBOOT_TEST_HOOKS_NOT_REMOVED")
    return {
        "schema": 1, "status": "PASS_REAL_KERNEL_SHARED_STRATEGIES_VOICE_REBOOT",
        "genuine_different_kernel_boot": True,
        "passive_shutdown_and_start_product_syshooks": True,
        "old_runtime_dropped_on_shutdown": True,
        "one_new_real_dvtws2_process": True,
        "one_original_shared_fd9_committed_journal_restored": True,
        "two_scoped_voice_and_tcp_ipfw_rules_restored": True,
        "exact_voice_table_restored": True,
        "saved_config_semantics_preserved": True,
        "foreign_ipfw_rules_preserved": True,
        "original_four_hooks_and_pkgdb_verified": True,
        "physical_native_archive_sha256": record["physical_native_package_sha256"],
        "same_physical_archive_before_and_after_kernel": True,
        "same_native_pkgdb_script_manifest_before_and_after_kernel": True,
        "test_observers_removed": True,
        "voice_media_tested": False, "browser_click_tested": False,
        "unexpected_power_loss_tested": False, "owner_appliance_modified": False,
    }


def self_test():
    rules = [
        "19000 divert 989 udp from any to table(zapret2_voice_telegram) "
        "out not diverted not sockarg xmit lo0",
        "19001 divert 989 tcp from any to any 65431 "
        "out not diverted not sockarg xmit lo0",
    ]
    record = {"initial_boot": "boot1", "old_pid": 100, "old_rules": rules,
              "original_journal_owner_id": "a" * 32,
              "foreign_rules": ["65535 allow ip from any to any"]}
    stop = {"bootid": "boot1", "status": "zapret is not running",
            "pid": "ABSENT", "ipfw": "65535 allow ip from any to any",
            "table": "", "table.rc": "1"}
    start = {"bootid": "boot2", "status": "zapret is running",
             "pid": "200", "ipfw": "\n".join(rules + record["foreign_rules"]),
             "table": "192.0.2.42/32 0", "table.rc": "0"}
    current = {"pid": 200, "id": "a" * 32, "rules": rules}
    assert qualify_reboot(record, stop, start, current, "boot2")
    for changed in (
        {"record": {**record, "old_pid": 200}},
        {"start": {**start, "status": "zapret is running as pid 200"}},
        {"start": {**start, "status": "zapret is not running"}},
        {"start": {**start, "pid": "201"}},
        {"start": {**start, "ipfw": start["ipfw"].replace("lo0", "vtnet0")}},
        {"start": {**start, "ipfw": start["ipfw"].replace("19001 ", "19002 ")}},
        {"start": {**start, "table": ""}},
        {"current": {**current, "id": "b" * 32}},
        {"stop": {**stop, "pid": "100"}},
        {"kernel": "boot1"},
    ):
        try:
            qualify_reboot(changed.get("record", record),
                           changed.get("stop", stop),
                           changed.get("start", start),
                           changed.get("current", current),
                           changed.get("kernel", "boot2"))
            raise AssertionError("Unsafe voice reboot evidence accepted")
        except (Refusal, common.Refusal):
            pass
    assert b"configctl zapret start" not in hook_bytes("start")
    assert b"configctl zapret stop" not in hook_bytes("stop")
    assert b"ipfw table zapret2_voice_telegram list" in hook_bytes("start")
    assert HOOKS["start"].name.startswith("21-")
    print("PASS_STAGE5_REAL_KERNEL_SHARED_VOICE_BOOT_NEGATIVE_CONTRACTS")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["prepare"]:
            print("STAGE5_REAL_VOICE_REBOOT=" + json.dumps(prepare(), sort_keys=True))
        elif sys.argv[1:] == ["verify"]:
            print("STAGE5_REAL_VOICE_REBOOT=" + json.dumps(verify(), sort_keys=True))
        else:
            raise Refusal("VOICE_REBOOT_RUN_PREPARE_VERIFY_OR_SELF_TEST")
    except (Refusal, common.Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE5_REAL_VOICE_REBOOT=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(2)
