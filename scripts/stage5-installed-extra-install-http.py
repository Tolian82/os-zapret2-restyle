#!/usr/bin/env python3
"""Positive installed Additional Resources Install on disposable OPNsense only.

Use stock cookie+CSRF HTTPS and the genuine, package-owned native worker,
setup.lock -> inherited FD9, catalog verification, transaction and restart.
There is NO mock worker, alternate catalog fetcher, installed-file mutation
or production bypass. Test accepts only one reviewed immutable catalog SHA.
This is a QEMU/CI fixture, NOT an owner appliance or browser-button click.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
FLAG = "ZAPRET2_STAGE5_AUTHENTICATED_EXTRA_INSTALL"
STATUS = "PASS_STAGE5_INSTALLED_EXTRA_AUTHENTICATED_INSTALL_AND_NATIVE_RESTART"
SOURCE_REVISION = "39bf85d7d00af672a5870cac2f14ccff422c0d07"
EXPECTED_COUNTS = {"lua": 19, "bin": 54}
ROOT = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle/extra-resources")
SERVICE_BASE = "/api/zapret/service/"
MAX_POLLS = 300


class Refusal(RuntimeError):
    pass


def need(value, why):
    if not value:
        raise Refusal(why)


def module(filename):
    spec = importlib.util.spec_from_file_location(
        "stage5_extra_install_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def catalog_content_sha(payloads):
    need(isinstance(payloads, dict) and payloads and
         all(isinstance(k, str) and isinstance(v, bytes) and v for k, v in payloads.items()),
         "EXTRA_INSTALL_UNTRUSTED_CATALOG_PAYLOAD")
    rows = [name + " " + hashlib.sha256(payloads[name]).hexdigest()
            for name in sorted(payloads)]
    return hashlib.sha256(("\n".join(rows) + "\n").encode("utf-8")).hexdigest()


def catalog_shape(source, *, expected_revision=SOURCE_REVISION):
    need(re.fullmatch(r"[a-f0-9]{40}", str(source.get("source_commit", ""))) is not None
         and source.get("source_commit") == expected_revision and
         source.get("counts") == EXPECTED_COUNTS and source.get("total") == 73,
         "EXTRA_INSTALL_CATALOG_REVISION_OR_INVENTORY_CHANGED")
    return source


def terminal_shape(row, operation, *, source_revision=SOURCE_REVISION):
    need(isinstance(row, dict) and row.get("status") == "ok" and
         row.get("operation") == operation and
         re.fullmatch(r"[a-f0-9]{32}", operation) is not None and
         row.get("phase") == "ready" and row.get("busy") is False and
         row.get("installed") is True and
         row.get("revision") == source_revision,
         "EXTRA_INSTALL_CORRELATED_SUCCESS_NOT_ATTESTED")
    return row


def poll_terminal(web, operation):
    need(isinstance(operation, str) and
         re.fullmatch(r"[a-f0-9]{32}", operation) is not None,
         "EXTRA_INSTALL_OPERATION_ID_UNQUALIFIED")
    for _ in range(MAX_POLLS):
        row = web.api("POST", SERVICE_BASE + "resourcesStatus", {})
        need(row.get("status") == "ok", "EXTRA_INSTALL_STATUS_UNAVAILABLE")
        if row.get("operation") == operation and row.get("busy") is False:
            if row.get("phase") in ("failed", "restore_failed", "recovery_required",
                                    "restored", "unknown", "not_installed"):
                raise Refusal("EXTRA_INSTALL_TERMINAL_FAILED:" + str(row.get("phase")))
            if row.get("phase") == "ready":
                return terminal_shape(row, operation)
        time.sleep(1)
    raise Refusal("EXTRA_INSTALL_CORRELATED_TERMINAL_NOT_OBSERVED")


def self_test():
    catalog_shape({"source_commit": SOURCE_REVISION, "counts": EXPECTED_COUNTS,
                   "total": 73})
    digest = catalog_content_sha({"lua/z.lua": b"function a() end",
                                  "files/fake/a.bin": b"test"})
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    token = "a" * 32
    good = {"status": "ok", "operation": token, "phase": "ready",
            "busy": False, "installed": True, "revision": SOURCE_REVISION}
    assert terminal_shape(good, token) == good
    for name, bad in (("operation", "b" * 32), ("phase", "restored"),
                      ("busy", True), ("installed", False),
                      ("revision", "f" * 40), ("status", "failed")):
        try:
            terminal_shape({**good, name: bad}, token)
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe installed success accepted: " + name)
    for name, bad in (("source_commit", "f" * 40), ("total", 72),
                      ("counts", {"lua": 19, "bin": 53})):
        row = {"source_commit": SOURCE_REVISION, "counts": EXPECTED_COUNTS,
               "total": 73, name: bad}
        try:
            catalog_shape(row)
        except Refusal:
            pass
        else:
            raise AssertionError("unreviewed catalog accepted: " + name)
    print("PASS_STAGE5_EXTRA_INSTALLED_CATALOG_AND_CORRELATED_RECEIPT_NEGATIVES=1")
    return 0


def execute():
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI", FLAG):
        need(os.environ.get(key) == "1",
             "EXTRA_INSTALL_DISPOSABLE_OPTIN_MISSING:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true" and os.geteuid() == 0 and
         os.uname().sysname == "FreeBSD" and os.uname().machine == "amd64",
         "EXTRA_INSTALL_NOT_FREEBSD_DISPOSABLE_CI_ROOT")

    active = module("stage2-opnsense-real-native-active-service.py")
    common = module("stage2-opnsense-real-native-shared-voice.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    engine_sha = active.guest_preflight()
    owner_before = common.witness(active, engine_sha, running=True, page="strategies")
    original_config = active.CONFIG.read_bytes()
    original_rules = active.plugin_rules()
    need(ROOT.is_dir() and not ROOT.is_symlink() and
         STATE.is_dir() and not STATE.is_symlink() and
         len(original_rules) == 2 and
         not (STATE / "transaction").exists() and
         not (STATE / "transaction").is_symlink(),
         "EXTRA_INSTALL_NATIVE_BASELINE_OR_STATE_UNSAFE")

    installed_root = Path("/usr/local/opnsense/scripts/OPNsense/Zapret")
    for name in ("extra_resources_preflight.py", "extra_resources_reconcile.py",
                 "extra_resources_operation.py", "extra_resources_transaction.py",
                 "extra_resources_inventory_cache.py"):
        source = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret" / name
        installed = installed_root / name
        need(source.is_file() and installed.is_file() and
             not installed.is_symlink() and source.read_bytes() == installed.read_bytes(),
             "EXTRA_INSTALL_NATIVE_MODULE_NOT_INSTALLED:" + name)
    # Import only packaged, proven worker dependencies. Production code is
    # unchanged: it resolves main HEAD then fetches precisely that SHA.
    sys.path.insert(0, str(installed_root))
    import extra_resources_preflight as preflight
    import extra_resources_reconcile as reconcile

    upstream_before = reconcile.tracked_resources(ROOT)
    live_before = reconcile.installed_resources(ROOT)
    baseline = reconcile.make_remove_plan(ROOT, STATE / "installed.json",
                                          active.CONFIG)
    need(bool(upstream_before) and live_before == upstream_before and
         not baseline["remove"] and baseline["counts"]["total"] == 0 and
         not reconcile.previous_metadata(STATE / "installed.json"),
         "EXTRA_INSTALL_GUEST_NOT_CLEAN_AFTER_REMOVE")

    web = voice.GuestHttps()
    voice.login(web)
    general = web.request("GET", "/ui/zapret")
    need("zapretExtraInstall" in general and "resourcesInstall" in general,
         "EXTRA_INSTALL_NATIVE_GUI_ACTION_MISSING")
    refused_method = web.api("GET", SERVICE_BASE + "resourcesInstall")
    need(refused_method.get("status") == "failed",
         "EXTRA_INSTALL_GET_METHOD_NOT_REFUSED")
    baseline_status = web.api("POST", SERVICE_BASE + "resourcesStatus", {})
    need(baseline_status.get("status") == "ok" and
         baseline_status.get("busy") is False and
         baseline_status.get("installed") is False,
         "EXTRA_INSTALL_HTTP_NOT_CLEAN_BASELINE")
    need(active.CONFIG.read_bytes() == original_config and
         common.witness(active, engine_sha, running=True, page="strategies") ==
         owner_before, "EXTRA_INSTALL_NEGATIVE_CHANGED_NATIVE_STATE")

    # The pin is TEST DATA, not a production source override. Do not make
    # an extra unauthenticated GitHub API HEAD request from parallel CI VMs:
    # that redundant request exhausted the shared rate limit in native CI.
    # The REAL production worker resolves GitHub main HEAD itself and the
    # correlated installed source_commit must exactly equal this pinned SHA.
    # Independently verify source bytes via the immutable codeload URL.
    archive = preflight.obtain_archive(SOURCE_REVISION)
    files = preflight.unpack_verified_archive(archive, SOURCE_REVISION)
    payloads, described = preflight.verified_resources(files)
    inventory = json.loads(files["inventory/sources.json"].decode("utf-8"))
    catalog_shape({"source_commit": SOURCE_REVISION,
                   "counts": inventory.get("counts"),
                   "total": inventory.get("total")})
    need(len(payloads) == 73 and described == 2,
         "EXTRA_INSTALL_REVIEWED_CATALOG_PAYLOAD_OR_CAPABILITIES_CHANGED")
    planned = reconcile.make_plan(payloads, ROOT, STATE / "installed.json")
    need(not planned["removed"] and not planned["previous"] and
         0 < len(planned["incoming"]) <= 73,
         "EXTRA_INSTALL_CATALOG_COLLISION_OR_FOREIGN_RESOURCE")
    reviewed_sha = catalog_content_sha(payloads)

    # Exactly ONE production API POST. No retries after uncertain acceptance.
    started = web.api("POST", SERVICE_BASE + "resourcesInstall", {})
    need(started.get("status") == "ok" and started.get("started") is True and
         isinstance(started.get("operation"), str) and
         re.fullmatch(r"[a-f0-9]{32}", started["operation"]) is not None,
         "EXTRA_INSTALL_NATIVE_START_NOT_CONFIRMED")
    terminal = poll_terminal(web, started["operation"])
    need(terminal.get("operation") == started["operation"] and
         terminal.get("revision") == SOURCE_REVISION,
         "EXTRA_INSTALL_NATIVE_TERMINAL_DIFFERENT_OPERATION")

    metadata_path = STATE / "installed.json"
    need(metadata_path.is_file() and not metadata_path.is_symlink(),
         "EXTRA_INSTALL_COMMITTED_METADATA_ABSENT")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    need(metadata.get("schema") == 1 and
         metadata.get("source_commit") == SOURCE_REVISION and
         metadata.get("files") == planned["incoming"] and
         metadata.get("capabilities") ==
         json.loads(files["inventory/capabilities.json"].decode("utf-8")),
         "EXTRA_INSTALL_INSTALLED_METADATA_DIFFERS_FROM_VERIFIED_SOURCE")

    actual = reconcile.installed_resources(ROOT)
    expected = dict(upstream_before)
    expected.update(planned["incoming"])
    need(reconcile.tracked_resources(ROOT) == upstream_before and
         actual == expected and
         not (STATE / "transaction").exists() and
         not (STATE / "transaction").is_symlink() and
         not (ROOT / ".extra-resources-remove-quarantine").exists(),
         "EXTRA_INSTALL_FINAL_RESOURCE_SET_NOT_EXACT")
    cached = web.api("POST", SERVICE_BASE + "resourcesInventory", {})
    other = {("lua/" if kind == "lua" else "files/fake/") + x["name"]
             for kind in ("lua", "bin") for x in cached.get(kind, [])
             if isinstance(x, dict) and x.get("origin") == "other" and
             isinstance(x.get("name"), str)}
    need(cached.get("status") == "ok" and
         cached.get("installed") is True and other == set(planned["incoming"]),
         "EXTRA_INSTALL_INSTALLED_HTTP_CACHE_MISSING_RESOURCES")

    owner_after = common.witness(active, engine_sha, running=True, page="strategies")
    # Ordinary Strategy Lab Stop -> Start reboots the SAME sealed shared-Apply
    # journal owner (shared_apply_boot_service). Only the running engine PID
    # must rotate. This is intentionally different from Remove's new Apply
    # trial, which must commit a fresh logical owner ID.
    need(owner_after["id"] == owner_before["id"],
         "EXTRA_INSTALL_SEALED_SHARED_OWNER_NOT_RETAINED")
    need(owner_after["pid"] != owner_before["pid"],
         "EXTRA_INSTALL_SHARED_ENGINE_PID_DID_NOT_RESTART")
    need(owner_after["rules"] == owner_before["rules"] and
         active.plugin_rules() == original_rules,
         "EXTRA_INSTALL_OWNED_IPFW_RULES_CHANGED")
    need(active.CONFIG.read_bytes() == original_config,
         "EXTRA_INSTALL_SAVED_CONFIG_CHANGED")
    report = {
        "schema": 1, "status": STATUS,
        "source_commit": SOURCE_REVISION,
        "catalog_content_sha256": reviewed_sha,
        "reviewed_lua_count": EXPECTED_COUNTS["lua"],
        "reviewed_bin_count": EXPECTED_COUNTS["bin"],
        "installed_extra_resource_count": len(planned["incoming"]),
        "stock_authenticated_general_page_and_csrf": True,
        "get_method_refused_before_mutation": True,
        "real_github_revision_and_archive_verified": True,
        "exact_catalog_lua_bin_set_installed": True,
        "real_installed_resource_cache_verified": True,
        "correlated_ready_operation_and_revision": True,
        "real_shared_strategies_fd9_owner_restarted": True,
        "native_lo0_ipfw_rules_preserved": True,
        "native_saved_config_unchanged": True,
        "real_catalog_network_fetch_used": True,
        "physical_browser_click_tested": False,
        "owner_appliance_modified": False,
    }
    print("STAGE5_INSTALLED_EXTRA_INSTALL_HTTP=" +
          json.dumps(report, sort_keys=True))
    return report


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            execute()
            return 0
        raise Refusal("EXTRA_INSTALL_RUN_OR_SELF_TEST_REQUIRED")
    except (Refusal, OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print("STAGE5_INSTALLED_EXTRA_INSTALL_HTTP=REFUSED:" + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
