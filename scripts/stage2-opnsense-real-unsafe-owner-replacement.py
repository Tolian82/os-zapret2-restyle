#!/usr/bin/env python3
"""Observe real pkg add -f while the old installed service has foreign IPFW.

Disposable OPNsense 26.7 only. This is a hazard witness, not a safe updater.
"""
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REVISION = "79"
OPTIN = "ZAPRET2_STAGE2_REAL_UNSAFE_OWNER_PKG"


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


stopped = load("stage2-opnsense-real-native-stopped-upgrade.py")
clean, native, old = stopped.clean, stopped.native, stopped.old
foreign = load("stage0-opnsense-foreign-ipfw-admission.py")


class Refusal(Exception):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def qualify():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.geteuid() == 0,
         "DISPOSABLE_OPNSENSE_UNSAFE_OWNER_OPTIN_REQUIRED")
    native.gate()
    need(all(m.REVISION == REVISION for m in (native, stopped, clean)),
         "SOURCE_REVISION_INCONSISTENT")
    need(foreign.RULE == 63037 and
         foreign.only_default(foreign.DEFAULT),
         "FOREIGN_KERNEL_BASELINE_HELPER_CHANGED")


# The native old service classifies orphaned managed-range divert rules as
# incomplete ownership; unrelated count rules are intentionally ignored.
ORPHAN_RULE = 19000
ORPHAN_PORT = 65431


def only_orphan_loopback_divert():
    result = foreign.command("/sbin/ipfw", "-q", "list")
    if result.returncode != 0:
        return False
    rows = foreign.kernel_rules(result.stdout)
    return (len(rows) == 2 and rows[1] == foreign.DEFAULT and
            rows[0].startswith("19000 divert 989 tcp ") and
            "65431" in rows[0] and "out via lo0" in rows[0])


def add_test_orphan():
    need(foreign.command("/sbin/kldstat", "-q", "-m", "ipdivert").returncode == 1,
         "IPDIVERT_ALREADY_LOADED")
    need(foreign.command("/sbin/kldload", "ipdivert").returncode == 0,
         "ISOLATED_IPDIVERT_LOAD_FAILED")
    need(foreign.command(
         "/sbin/ipfw", "-q", "add", str(ORPHAN_RULE), "divert", "989",
         "tcp", "from", "any", "to", "any", str(ORPHAN_PORT),
         "out", "via", "lo0").returncode == 0,
         "TEST_ORPHAN_DIVERT_INSTALL_FAILED")
    need(only_orphan_loopback_divert(), "ORPHAN_DIVERT_NOT_EXACT_LOOPBACK")


def remove_test_orphan():
    need(only_orphan_loopback_divert(),
         "ORPHAN_RULE_CHANGED_REFUSE_DELETE")
    need(foreign.command("/sbin/ipfw", "-q", "delete", str(ORPHAN_RULE)).returncode == 0,
         "TEST_ORPHAN_RULE_DELETE_FAILED")
    current = foreign.command("/sbin/ipfw", "-q", "list")
    need(current.returncode == 0 and foreign.only_default(current.stdout),
         "TEST_ORPHAN_CLEANUP_NOT_DEFAULT_ONLY")


def installed_identity():
    p = clean.run(["pkg", "-o", "REPO_AUTOUPDATE=false",
                   "query", "%n|%v", native.NAME], timeout=30)
    need(p.returncode == 0, "PKGDB_NOT_READABLE")
    return p.stdout.strip()


def classify(original, successor, observed, hook_refused):
    need(hook_refused, "PRODUCTION_PREINSTALL_REFUSAL_NOT_OBSERVED")
    if observed == original:
        return "OBSERVED_PKG_PRESERVED_OLD_AFTER_HOOK_REFUSAL"
    if observed == successor:
        return "OBSERVED_PKG_REPLACED_DESPITE_HOOK_REFUSAL"
    raise Refusal("UNKNOWN_PACKAGE_STATE_AFTER_HOOK_REFUSAL")


def execute(archive):
    qualify()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    built = native.build()
    need(built["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY" and
         built["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "OFFICIAL_NATIVE_SUCCESSOR_NOT_BUILT")
    successor = native.ROOT / built["output"]
    pkg_sha = built["real_native_pkg"]["sha256"]
    need(successor.is_file() and not successor.is_symlink() and
         clean.digest(successor) == pkg_sha,
         "NATIVE_PACKAGE_DIGEST_UNQUALIFIED")
    installer = stopped.load("stage0-opnsense-installed-predecessor.py")
    prior = installer.install_and_verify(archive)
    need(prior["status"] == "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
         "ORIGINAL_PREDECESSOR_NOT_QUALIFIED")
    inspector = stopped.load("stage0-opnsense-prepkg-readonly.py")
    initial = inspector.snapshot(archive)
    need(initial["status"] == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
         initial["real_old_status"] == "STOPPED",
         "OLD_OWNER_NOT_PROVEN_COLD")
    old_id = native.NAME + "|0.6.2_1"
    new_id = native.NAME + "|" + native.VERSION + "_" + REVISION
    need(installed_identity() == old_id, "ORIGINAL_PKGDB_IDENTITY_CHANGED")
    config_before = Path("/conf/config.xml").read_bytes()
    service_sha = clean.digest(Path(old.SERVICE))
    foreign.activate_kernel(inspector)
    injected = False
    pkg_result = None
    after_id = None
    observed_status = None
    refused = False
    config_unchanged = None
    try:
        add_test_orphan()
        injected = True
        status = foreign.command(str(old.SERVICE), "status")
        observed_status = status.returncode
        need(observed_status == 2,
             "AUTHENTIC_OLD_STATUS_NOT_UNSAFE:" + str(observed_status))
        need(only_orphan_loopback_divert(),
             "TEST_ORPHAN_IPFW_IDENTITY_NOT_PROVEN")
        pkg_result = clean.run(["pkg", "-o", "REPO_AUTOUPDATE=false",
                                "add", "-f", str(successor)], timeout=230)
        after_id = installed_identity()
        output = pkg_result.stdout + "\n" + pkg_result.stderr
        refused = ("incomplete zapret lifecycle" in output or
                   "cannot determine zapret service state" in output or
                   "controlled recovery before package replacement" in output)
        need(clean.digest(successor) == pkg_sha,
             "SUCCESSOR_ARCHIVE_CHANGED")
        need(only_orphan_loopback_divert(),
             "ORPHANED_MANAGED_IPFW_CHANGED_BY_PACKAGE")
        # Evidence, not a post-hoc gate: root pkg may mutate firmware Config.
        config_unchanged = Path("/conf/config.xml").read_bytes() == config_before
        # Emit the actual native pkgdb result before even cleanup diagnostics.
        print("STAGE2_UNSAFE_OWNER_PRE_CLEANUP=" + json.dumps({
            "installed_pkg_after": after_id, "real_pkg_exit": pkg_result.returncode,
            "authentic_hook_refusal_text": refused,
            "config_unchanged": config_unchanged
        }, sort_keys=True), flush=True)
    finally:
        if injected:
            remove_test_orphan()
        current = foreign.command("/sbin/ipfw", "-q", "list")
        need(current.returncode == 0 and
             foreign.only_default(current.stdout),
             "TEST_RULE_CLEANUP_NOT_DEFAULT_ONLY")
        # ipfw/ipdivert module unloading is deliberately NOT a product
        # operation. The single-use KVM guest is destroyed after this job.
    need(pkg_result is not None and after_id is not None,
         "REAL_PKG_COMMAND_NOT_OBSERVED")
    verdict = classify(old_id, new_id, after_id, refused)
    if after_id == old_id:
        need(config_unchanged is True,
             "OLD_PKG_PRESERVED_BUT_CONFIG_MUTATED")
        final_status = foreign.command(str(old.SERVICE), "status")
        need(clean.digest(Path(old.SERVICE)) == service_sha and
             final_status.returncode == 1,
             "OLD_PKGDB_PRESERVED_BUT_PAYLOAD_OR_OWNER_CHANGED")
    return {"schema": 1, "status": "OBSERVED_NATIVE_UNSAFE_OWNER_PKG",
            "orphaned_test_divert": "lo0 TCP/65431 / ipfw 19000",
            "verdict": verdict, "real_pkg_exit": pkg_result.returncode,
            "authentic_old_status_exit_with_foreign_ipfw": observed_status,
            "authentic_preinstall_refusal_observed": refused,
            "installed_pkg_after": after_id,
            "original_old_archive_sha256": old.ARCHIVE_SHA,
            "native_successor_pkg_sha256": pkg_sha,
            "config_unchanged": config_unchanged,
            "orphaned_managed_divert_preserved": True,
            "test_rule_safely_cleaned": True,
            "ipfw_ipdivert_modules_left_loaded_in_disposable_guest": True,
            "root_pkg_atomic_refusal_proved": False,
            "owner_appliance_modified": False,
            "new_package_published": False}


def main():
    if len(sys.argv) != 2:
        print("STAGE2_UNSAFE_OWNER=REFUSED:OLD_ARCHIVE_REQUIRED", file=sys.stderr)
        return 2
    try:
        print("STAGE2_UNSAFE_OWNER=" +
              json.dumps(execute(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, stopped.Refusal, clean.Refusal, native.Refusal,
            foreign.Refusal, old.Refusal, OSError, KeyError, ValueError,
            TypeError) as exc:
        print("STAGE2_UNSAFE_OWNER=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
