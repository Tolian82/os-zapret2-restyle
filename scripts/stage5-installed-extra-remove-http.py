#!/usr/bin/env python3
"""Real installed, authenticated Additional Resources Remove on disposable OPNsense.

Test one deliberately untracked harmless Lua file against the existing local
Git HEAD and native saved Strategies/Voice owner. Use the stock General GUI's
cookie+CSRF API, setup.lock -> original FD9, and native Remove/rollback path.

NEVER run on an owner appliance, WAN fixture or a non-CI machine. This is not
a physical GUI click, catalog Install, WAN/IPv6 test or production publication.
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
import time

HERE = Path(__file__).resolve().parent
FLAG = "ZAPRET2_STAGE5_AUTHENTICATED_EXTRA_REMOVE"
STATUS = "PASS_STAGE5_INSTALLED_EXTRA_AUTHENTICATED_REMOVE_AND_NATIVE_TRIAL"
ROOT = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle/extra-resources")
RESOURCE = "lua/stage5_disposable_remove_acceptance.lua"
FIXTURE = b"-- isolated Stage 5 Remove acceptance fixture; not loaded by Strategies\n"
SERVICE_BASE = "/api/zapret/service/"
MAX_POLLS = 180


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def module(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_extra_remove_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def plan_shape(value, *, total, lua, bin_count):
    need(isinstance(value, dict) and value.get("status") == "ok" and
         value.get("ready") is False and
         type(value.get("lua")) is int and value["lua"] == lua and
         type(value.get("bin")) is int and value["bin"] == bin_count and
         type(value.get("total")) is int and value["total"] == total and
         re.fullmatch(r"[a-f0-9]{64}", str(value.get("inventory_sha256", ""))) is not None,
         "EXTRA_REMOVE_UNEXPECTED_INSTALLED_PLAN_OR_COUNTS")
    return value["inventory_sha256"]


def poll_terminal(web, operation):
    need(re.fullmatch(r"[a-f0-9]{32}", operation) is not None,
         "EXTRA_REMOVE_OPERATION_ID_UNQUALIFIED")
    for _ in range(MAX_POLLS):
        row = web.api("POST", SERVICE_BASE + "resourcesStatus", {})
        need(row.get("status") == "ok", "EXTRA_REMOVE_STATUS_UNAVAILABLE")
        if row.get("operation") == operation and row.get("busy") is False:
            if row.get("phase") == "not_installed" and row.get("installed") is False:
                return row
            if row.get("phase") in ("failed", "restore_failed", "recovery_required",
                                    "restored", "ready", "unknown"):
                raise Refusal("EXTRA_REMOVE_NATIVE_TERMINAL_UNQUALIFIED:" +
                              str(row.get("phase")))
        # Never infer success from a missing PID; require the correlated,
        # persisted, successful terminal receipt and exact operation ID.
        time.sleep(1)
    raise Refusal("EXTRA_REMOVE_CORRELATED_TERMINAL_NOT_OBSERVED")


def self_test():
    good = {"status": "ok", "ready": False, "lua": 1, "bin": 0,
            "total": 1, "inventory_sha256": "a" * 64}
    assert plan_shape(good, total=1, lua=1, bin_count=0) == "a" * 64
    assert plan_shape({**good, "lua": 0, "total": 0}, total=0,
                      lua=0, bin_count=0) == "a" * 64
    for patch in ({"status": "failed"}, {"ready": True}, {"total": 2},
                  {"lua": True}, {"inventory_sha256": "z" * 64},
                  {"bin": 1}, {"inventory_sha256": ""}):
        try:
            plan_shape({**good, **patch}, total=1, lua=1, bin_count=0)
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe Remove plan accepted " + repr(patch))
    need(RESOURCE.startswith("lua/") and RESOURCE.endswith(".lua") and
         RESOURCE.count("/") == 1 and len(FIXTURE) > 10,
         "EXTRA_REMOVE_FIXTURE_NOT_SINGLE_LUA_FILE")
    print("PASS_STAGE5_EXTRA_REMOVE_NATIVE_PLAN_AND_SCOPE_NEGATIVES=1")
    return 0


def execute():
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI", FLAG):
        need(os.environ.get(key) == "1",
             "EXTRA_REMOVE_DISPOSABLE_OPTIN_MISSING:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true" and os.geteuid() == 0 and
         os.uname().sysname == "FreeBSD" and os.uname().machine == "amd64",
         "EXTRA_REMOVE_NOT_FREEBSD_DISPOSABLE_CI_ROOT")

    active = module("stage2-opnsense-real-native-active-service.py")
    common = module("stage2-opnsense-real-native-shared-voice.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    engine_sha = active.guest_preflight()
    original_owner = common.witness(active, engine_sha, running=True, page="strategies")
    original_config = active.CONFIG.read_bytes()
    original_rules = active.plugin_rules()
    need(len(original_rules) == 2 and ROOT.is_dir() and
         not ROOT.is_symlink() and not (ROOT / "lua").is_symlink() and
         (ROOT / "lua").is_dir() and not STATE.is_symlink(),
         "EXTRA_REMOVE_NOT_EXACT_DISPOSABLE_RESOURCE_TREE")

    installed_root = Path("/usr/local/opnsense/scripts/OPNsense/Zapret")
    for name in ("extra_resources_preflight.py", "extra_resources_reconcile.py",
                 "extra_resources_operation.py", "extra_resources_transaction.py"):
        source = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret" / name
        installed = installed_root / name
        need(source.is_file() and installed.is_file() and
             not installed.is_symlink() and source.read_bytes() == installed.read_bytes(),
             "EXTRA_REMOVE_NATIVE_INSTALLED_MODULE_NOT_SOURCE:" + name)

    # Import the actual package-owned native planner, not a copy of its rules.
    sys.path.insert(0, str(installed_root))
    import extra_resources_reconcile as reconcile

    baseline_plan = reconcile.make_remove_plan(ROOT, STATE / "installed.json",
                                               active.CONFIG)
    need(not baseline_plan["remove"] and baseline_plan["counts"]["total"] == 0,
         "EXTRA_REMOVE_PREEXISTING_FOREIGN_USER_RESOURCES_PRESENT")
    upstream_before = baseline_plan["upstream"]
    live_before = reconcile.installed_resources(ROOT)
    need(live_before == upstream_before and bool(upstream_before),
         "EXTRA_REMOVE_NOT_CLEAN_UPSTREAM_BASELINE")

    web = voice.GuestHttps()
    voice.login(web)
    general = web.request("GET", "/ui/zapret")
    need("resourcesRemovePlan" in general and "resourcesRemove" in general and
         "zapretExtraRemove" in general, "EXTRA_REMOVE_INSTALLED_GUI_ACTIONS_ABSENT")
    no_op = web.api("POST", SERVICE_BASE + "resourcesRemovePlan", {})
    no_op_digest = plan_shape(no_op, total=0, lua=0, bin_count=0)
    need(no_op_digest == baseline_plan["witness"]["inventory_sha256"],
         "EXTRA_REMOVE_NATIVE_NOOP_DIGEST_DIFFERS")
    rejected_empty = web.api("POST", SERVICE_BASE + "resourcesRemove",
                             {"inventory_sha256": no_op_digest,
                              "confirmation": "REMOVE 0"})
    need(rejected_empty.get("status") == "rejected" and
         rejected_empty.get("reason") == "nothing_to_remove" and
         rejected_empty.get("started") is False,
         "EXTRA_REMOVE_NATIVE_NOOP_REQUEST_NOT_REJECTED")
    need(common.witness(active, engine_sha, running=True, page="strategies") ==
         original_owner and active.CONFIG.read_bytes() == original_config,
         "EXTRA_REMOVE_NOOP_CHANGED_NATIVE_OWNER")

    path = ROOT / RESOURCE
    need(not path.exists() and not path.is_symlink() and
         RESOURCE not in upstream_before,
         "EXTRA_REMOVE_TEST_FILE_COLLIDES_WITH_REAL_UPSTREAM")
    # Creation is strictly confined to ONE disposable scratch resource on
    # a guest already attested as OPNsense CI, and is untracked by Git HEAD.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(FIXTURE)
        stream.flush()
        os.fsync(stream.fileno())
    need(stat.S_ISREG(path.lstat().st_mode) and
         path.lstat().st_nlink == 1 and path.read_bytes() == FIXTURE,
         "EXTRA_REMOVE_TEST_ONLY_RESOURCE_CHANGED_BEFORE_PLAN")

    planned = reconcile.make_remove_plan(ROOT, STATE / "installed.json",
                                         active.CONFIG)
    need([entry["path"] for entry in planned["remove"]] == [RESOURCE] and
         planned["counts"] == {"lua": 1, "bin": 0, "total": 1} and
         planned["upstream"] == upstream_before,
         "EXTRA_REMOVE_NATIVE_LOCAL_PLAN_INCLUDES_NON_TEST_RESOURCE")
    digest = planned["witness"]["inventory_sha256"]
    http_plan = web.api("POST", SERVICE_BASE + "resourcesRemovePlan", {})
    need(plan_shape(http_plan, total=1, lua=1, bin_count=0) == digest,
         "EXTRA_REMOVE_INSTALLED_HTTP_PLAN_DIFFERS_FROM_NATIVE")
    before_resource = hashlib.sha256(path.read_bytes()).hexdigest()

    # A real typed-confirmation refusal must leave the running owner,
    # Config, service and test file untouched.
    negative = web.api("POST", SERVICE_BASE + "resourcesRemove",
                       {"inventory_sha256": digest,
                        "confirmation": "REMOVE 2"})
    need(negative.get("status") == "rejected" and
         negative.get("reason") == "plan_changed" and
         negative.get("started") is False,
         "EXTRA_REMOVE_BAD_CONFIRMATION_NOT_REFUSED")
    stale = "f" * 64 if digest != "f" * 64 else "e" * 64
    bad_digest = web.api("POST", SERVICE_BASE + "resourcesRemove",
                         {"inventory_sha256": stale,
                          "confirmation": "REMOVE 1"})
    need(bad_digest.get("status") == "rejected" and
         bad_digest.get("reason") == "plan_changed" and
         bad_digest.get("started") is False,
         "EXTRA_REMOVE_STALE_DIGEST_NOT_REFUSED")
    need(active.CONFIG.read_bytes() == original_config and
         common.witness(active, engine_sha, running=True, page="strategies") ==
         original_owner and
         path.is_file() and
         hashlib.sha256(path.read_bytes()).hexdigest() == before_resource,
         "EXTRA_REMOVE_REJECTED_REQUEST_MUTATED_REAL_SERVICE_OR_FILE")

    # Exactly ONE destructive API request. If it times out or the response
    # is ambiguous, never automatically retry; VM is discarded.
    started = web.api("POST", SERVICE_BASE + "resourcesRemove",
                      {"inventory_sha256": digest,
                       "confirmation": "REMOVE 1"})
    need(started.get("status") == "ok" and
         started.get("started") is True and
         re.fullmatch(r"[a-f0-9]{32}", str(started.get("operation", ""))) is not None,
         "EXTRA_REMOVE_AUTHENTICATED_START_NOT_CONFIRMED")
    terminal = poll_terminal(web, started["operation"])
    need(terminal.get("operation") == started["operation"] and
         terminal.get("phase") == "not_installed" and
         terminal.get("installed") is False and
         terminal.get("busy") is False,
         "EXTRA_REMOVE_CORRELATED_TERMINAL_INCONSISTENT")

    need(not path.exists() and not path.is_symlink() and
         reconcile.installed_resources(ROOT) == upstream_before and
         active.CONFIG.read_bytes() == original_config,
         "EXTRA_REMOVE_DID_NOT_RETAIN_EXACT_UPSTREAM_AND_CONFIG")
    final_plan = reconcile.make_remove_plan(ROOT, STATE / "installed.json",
                                            active.CONFIG)
    need(not final_plan["remove"] and final_plan["counts"]["total"] == 0,
         "EXTRA_REMOVE_POST_REMOVAL_PLAN_NOT_EMPTY")
    final_owner = common.witness(active, engine_sha, running=True, page="strategies")
    need(final_owner["id"] != original_owner["id"] and
         final_owner["pid"] != original_owner["pid"] and
         final_owner["rules"] == original_owner["rules"] and
         active.plugin_rules() == original_rules,
         "EXTRA_REMOVE_NATIVE_TRIAL_DID_NOT_RESTART_OR_PRESERVE_IPFW")

    report = {
        "schema": 1, "status": STATUS,
        "stock_authenticated_general_page_and_csrf": True,
        "read_only_noop_plan_and_refusal": True,
        "exact_local_git_head_and_single_test_file": True,
        "typed_confirmation_and_stale_digest_refused": True,
        "native_confirmed_remove_worker_completed": True,
        "correlated_operation_status_not_installed": True,
        "removed_only_test_file_upstream_bytes_intact": True,
        "native_saved_config_unchanged": True,
        "real_shared_strategies_fd9_owner_restarted": True,
        "native_lo0_ipfw_rules_preserved": True,
        "outside_network_access_used": False,
        "additional_resources_install_tested": False,
        "real_extra_catalog_install_tested": False,
        "physical_browser_click_tested": False,
        "owner_appliance_modified": False,
    }
    print("STAGE5_INSTALLED_EXTRA_REMOVE_HTTP=" +
          json.dumps(report, sort_keys=True))
    return report


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("EXTRA_REMOVE_RUN_OR_SELF_TEST_REQUIRED")
    except (Refusal, OSError, KeyError, ValueError, TypeError, RuntimeError) as exc:
        print("STAGE5_INSTALLED_EXTRA_REMOVE_HTTP=REFUSED:" + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
