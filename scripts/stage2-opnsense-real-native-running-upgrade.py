#!/usr/bin/env python3
"""Real historical RUNNING -> official native pkg replacement, disposable OPNsense only.

Uses the pinned genuine old dvtws2 on lo0 TCP 65431; no WAN interception.
A successful test is evidence of this specific pkg schedule, NOT atomic
root-pkg admission, owner-live upgrade, rollback or configd PID-reuse safety.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

import importlib.util

HERE = Path(__file__).resolve().parent
REVISION = "77"
OPTIN = "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE"


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace("-", "_").replace(".", "_"), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stopped = load("stage2-opnsense-real-native-stopped-upgrade.py")
clean = stopped.clean
native = stopped.native
old = stopped.old
genuine = load("stage0-opnsense-genuine-running.py")


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def require_disposable():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true",
         "RUNNING_UPGRADE_DISPOSABLE_KVM_OPTIN_REQUIRED")
    native.gate()
    genuine.qualify_guest()
    need(native.REVISION == REVISION and clean.REVISION == REVISION and
         stopped.REVISION == REVISION, "NATIVE_SOURCE_REVISION_NOT_CURRENT")


def owned_process_ids():
    # Bind preexisting old engine/supervisor owners to native observed PIDs;
    # old processes cannot be silently reused as the new runtime.
    result = genuine.command("/bin/ps", "-ax", "-o", "pid=", "-o", "command=")
    need(result.returncode == 0, "NATIVE_PROCESS_CENSUS_UNAVAILABLE")
    identities = {}
    for line in result.stdout.splitlines():
        bits = line.strip().split(None, 1)
        if len(bits) != 2 or not bits[0].isdigit():
            continue
        command = bits[1]
        if command.startswith(str(genuine.ENGINE)) or (
            "supervisor_loop.sh" in command and
            "/usr/local/opnsense/scripts/OPNsense/Zapret/" in command
        ):
            identities[int(bits[0])] = command
    return identities


def assert_old_processes_replaced(old_ids, new_engine_pid):
    need(old_ids and new_engine_pid not in old_ids,
         "OLD_RUNNING_PIDS_REUSED_OR_MISSING")
    pending = {}
    # Historical daemon supervisor parent can drain after Stop. Never kill,
    # release ownership, or treat an immediate transient as a permanent leak.
    for _ in range(4):
        current = owned_process_ids()
        pending = {pid: name for pid, name in current.items() if pid in old_ids}
        if not pending:
            return {"old_processes_drained": True,
                    "prior_owned_process_count": len(old_ids)}
        time.sleep(1)
    raise Refusal("OLD_OWNED_PROCESS_SURVIVED_REPLACEMENT:" +
                  ",".join(str(i) for i in sorted(pending)))


def fw_rules():
    result = genuine.command("/sbin/ipfw", "-q", "list")
    need(result.returncode == 0, "IPFW_RUNTIME_UNAVAILABLE")
    return result.stdout.splitlines()


def unrelated_rules(lines):
    # The single authorized test-owned rule is number 19000 on lo0 only.
    return [line for line in lines
            if not re.match(r"^19000\s", line)]


def verify_running_successor(engine_sha, prior_processes, prior_rules):
    service = old.SERVICE
    rc, stdout, stderr = genuine.status(service, "status")
    need(rc == 0 and "zapret is running" in stdout,
         "NEW_INSTALLED_SERVICE_NOT_RUNNING:" + str(rc) + ":" +
         (stdout + stderr)[-260:])
    p = genuine.PID
    need(p.is_file() and not p.is_symlink(), "NEW_ENGINE_PIDFILE_MISSING")
    value = p.read_text().strip()
    need(value.isdecimal() and int(value) > 1, "NEW_ENGINE_PID_INVALID")
    new_pid = int(value)
    need(hashlib.sha256(genuine.ENGINE.read_bytes()).hexdigest() == engine_sha,
         "PINNED_RUNTIME_ENGINE_CHANGED_DURING_REPLACEMENT")
    process = genuine.command("/bin/ps", "-p", str(new_pid), "-o", "command=")
    need(process.returncode == 0 and
         process.stdout.strip().split(" ")[0] == str(genuine.ENGINE),
         "NEW_ENGINE_NOT_ACTUAL_OWNED_PROCESS")
    live_rules = fw_rules()
    need(unrelated_rules(live_rules) == unrelated_rules(prior_rules),
         "UNRELATED_IPFW_RULES_CHANGED")
    matched = [line for line in live_rules if line.startswith("19000 ")]
    need(len(matched) == 1 and
         "divert 989" in matched[0] and "65431" in matched[0] and
         "lo0" in matched[0],
         "NEW_RUNNING_LOOPBACK_ONLY_RULE_NOT_OWNED")
    for path in (Path("/var/run/zapret2-restyle/pkg-upgrade.restart"),
                 Path("/var/run/zapret2-restyle/pkg-replacement.restart")):
        need(not path.exists() and not path.is_symlink(),
             "RESTART_MARKER_UNCONSUMED:" + str(path))
    drained = assert_old_processes_replaced(prior_processes, new_pid)
    return {"real_new_service_running": True,
            "new_engine_pid": new_pid,
            "new_engine_identity_verified": True,
            "one_owned_loopback_rule": True,
            "restart_markers_consumed": True, **drained}


def execute(archive):
    require_disposable()
    clean.plugin_absent()
    stopped.check_old_archive(archive)
    native_build = native.build()  # official native Mk source-built before old install
    need(native_build["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY" and
         native_build["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "CURRENT_OFFICIAL_NATIVE_BUILD_UNQUALIFIED")
    successor = native.ROOT / native_build["output"]
    sha = native_build["real_native_pkg"]["sha256"]
    need(successor.is_file() and not successor.is_symlink() and
         clean.digest(successor) == sha, "NATIVE_SUCCESSOR_ARCHIVE_CHANGED")
    installer = stopped.load("stage0-opnsense-installed-predecessor.py")
    previous = installer.install_and_verify(archive)
    need(previous["status"] ==
         "PASS_OPNSENSE_26_7_REAL_PREDECESSOR_INSTALLED_PROVENANCE",
         "HISTORICAL_PKGDB_OWNERSHIP_NOT_VERIFIED")
    inspector = stopped.load("stage0-opnsense-prepkg-readonly.py")
    cold = inspector.snapshot(archive)
    need(cold["status"] == "PASS_COLD_READ_ONLY_SNAPSHOT_ONLY" and
         cold["safe_pkg_transaction_authorized"] is False,
         "ORIGINAL_COLD_OWNER_NOT_VERIFIED")
    genuine.fresh_owned_paths()
    saved, mode, uid, gid, xml = genuine.original_config()
    genuine.original_generated()
    genuine.original_template_hostlists()
    runtime = genuine.RUNTIME.lstat()
    need(stat.S_ISDIR(runtime.st_mode) and not genuine.RUNTIME.is_symlink(),
         "HISTORICAL_RUNTIME_ROOT_UNQUALIFIED")
    with tempfile.TemporaryDirectory(prefix="stage2-real-running-old-") as temp:
        upstream = stopped.load("stage0-opnsense-upstream-engine-build.py")
        upstream.build(Path(temp))
        engine_sha = genuine.stage_engine(Path(temp) / "upstream")
        genuine.RUNTIME.chmod(0o755)
        generated = ET.tostring(genuine.insert_test_model(xml), encoding="utf-8")
        genuine.write_config(generated, mode, owner=(uid, gid))
        render = genuine.command("/usr/local/sbin/configctl", "template", "reload",
                                 "OPNsense/Zapret")
        need(render.returncode == 0 and render.stdout.strip() == "OK",
             "GENUINE_OLD_TEMPLATE_RELOAD_FAILED")
        config_before = genuine.CONFIG.read_bytes()
        old_pid = genuine.bounded_running(old.SERVICE, engine_sha)
        pre_processes = owned_process_ids()
        need(int(old_pid) in pre_processes, "OLD_ENGINE_NOT_IN_PROCESS_CENSUS")
        before_rules = fw_rules()
        old_owned = [line for line in before_rules if line.startswith("19000 ")]
        need(len(old_owned) == 1 and "lo0" in old_owned[0],
             "OLD_LOOPBACK_RULE_NOT_UNAMBIGUOUS")
        # No explicit Stop before pkg: incoming pre-install must actually stop
        # historical RUNNING owner and POST_INSTALL must restore new RUNNING.
        pkg = stopped.replace_with_actual_pkg(successor)
        need(clean.digest(successor) == sha,
             "SUCCESSOR_ARCHIVE_SHA_CHANGED_DURING_PKG_REPLACEMENT")
        manifest, installed = clean.installed_pkg_manifest(successor)
        payload = clean.verify_installed_files(successor, manifest)
        live = verify_running_successor(engine_sha, pre_processes, before_rules)
        registry = stopped.prove_preserved_config(
            config_before, genuine.CONFIG.read_bytes())
        need(genuine.CONFIG.is_file() and not genuine.CONFIG.is_symlink(),
             "NEW_CONFIG_NOT_REGULAR")
        # Full test-owned model must survive unchanged apart from official
        # firmware registration/revision; registry function checks all others.
        need(genuine.CONFIG.read_bytes() != b"",
             "OPNSENSE_CONFIG_MISSING_AFTER_UPGRADE")
    return {"schema": 1, "status": "PASS_REAL_RUNNING_NATIVE_VERSION_REPLACEMENT",
            "tested_exact_project_sha": native_build["project_sha"],
            "old_archive_sha256": old.ARCHIVE_SHA,
            "new_temporary_pkg_sha256": sha,
            "old_running_pid": int(old_pid), "actual_pkg_replacement": pkg,
            "new_package": native.NAME + "-" + native.VERSION + "_" + REVISION,
            "installed_files": payload,
            "installed_original_four_hooks_equal": True,
            "native_dependencies": installed["deps"],
            "old_engine_sha256": engine_sha, "restored_runtime": live,
            "config_verification": registry,
            "actual_old_hook_scheduler_traced": False,
            "fd9_held_across_pkg": False,
            "root_pkg_bypass_protected": False,
            "failure_compensation_tested": False,
            "forced_reinstall_tested": False,
            "configctl_worker_pid_reuse_negative_tested": False,
            "owner_appliance_modified": False,
            "stage0_closed": False, "publication_approved": False}


def main():
    if len(sys.argv) != 2:
        print("STAGE2_REAL_RUNNING=REFUSED:EXACT_OLD_ARCHIVE_PATH_REQUIRED",
              file=sys.stderr)
        return 2
    try:
        result = execute(Path(sys.argv[1]))
    except (Refusal, stopped.Refusal, clean.Refusal, native.Refusal,
            genuine.Refusal, old.Refusal,
            OSError, ValueError, KeyError, TypeError, ET.ParseError) as exc:
        print("STAGE2_REAL_RUNNING=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_REAL_RUNNING=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
