#!/usr/bin/env python3
"""Positive REPEAT Install + confirmed complete Remove on disposable OPNsense.

Uses only the installed stock HTTPS cookie/CSRF/configd native worker and real
installed file tree. The independently verified first Install must already
have completed. Never retry an uncertain mutation or fabricate a catalog.
All safety flags are CI/disposable-only; owner appliances are never targeted.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
from urllib.request import getproxies

HERE = Path(__file__).resolve().parent
ROOT = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle/extra-resources")
BASE = "/api/zapret/service/"
FLAG = "ZAPRET2_STAGE5_AUTHENTICATED_EXTRA_ROUNDTRIP"
STATUS = "PASS_STAGE5_REAL_REPEAT_INSTALL_AND_ALL_73_REMOVE"
LUA = 19
BIN = 54
TOTAL = LUA + BIN


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def module(path):
    spec = importlib.util.spec_from_file_location(
        "stage5_roundtrip_" + path.replace("-", "_").replace(".", "_"),
        HERE / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def content_sha(installed):
    """Same name + digest formula as the original independent source proof."""
    need(isinstance(installed, dict) and len(installed) == TOTAL and
         all(isinstance(name, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
             for name, digest in installed.items()),
         "EXTRA_ROUNDTRIP_CATALOG_MANIFEST_UNQUALIFIED")
    lines = [name + " " + installed[name] for name in sorted(installed)]
    return hashlib.sha256(("\n".join(lines) + "\n").encode("utf-8")).hexdigest()


def names_from_cache(row):
    need(isinstance(row, dict) and row.get("status") == "ok" and
         isinstance(row.get("lua"), list) and isinstance(row.get("bin"), list),
         "EXTRA_ROUNDTRIP_NATIVE_INVENTORY_CACHE_NOT_VERIFIED")
    names = set()
    for kind, root in (("lua", "lua/"), ("bin", "files/fake/")):
        for entry in row[kind]:
            need(isinstance(entry, dict) and entry.get("origin") in ("upstream", "other") and
                 isinstance(entry.get("name"), str) and
                 re.fullmatch(r"[A-Za-z0-9_.+\-]+\." + ("lua" if kind == "lua" else "bin"),
                              entry["name"]) is not None,
                 "EXTRA_ROUNDTRIP_UNSAFE_NATIVE_CACHE_ENTRY")
            if entry["origin"] == "other":
                names.add(root + entry["name"])
    return names


def failed_fetch_network_diagnostics():
    """Read-only CI evidence AFTER failed repeat; never retry a mutation."""
    result = {}
    try:
        proc = subprocess.run(["/sbin/ipfw", "-a", "list"], capture_output=True,
                              text=True, timeout=8, check=False)
        lines = [line.strip() for line in proc.stdout.splitlines()
                 if any(word in line.lower() for word in
                        ("divert", "deny", "reject", "unreach"))]
        result["ipfw_rc"] = proc.returncode
        result["ipfw_relevant"] = lines[:24]
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["ipfw_error"] = type(exc).__name__ + ":" + str(exc)[:120]
    # These are diagnostic keys ONLY. Never print proxy URLs, credentials,
    # headers, or environment values into a public CI artifact.
    result["urllib_proxy_schemes"] = sorted(str(k) for k in getproxies())[:12]
    result["proxy_env_variable_names"] = sorted(
        k for k in os.environ if k.lower().endswith("_proxy"))[:12]
    for label, args in (
        ("pf_info", ["/sbin/pfctl", "-s", "info"]),
        ("pf_rules", ["/sbin/pfctl", "-sr"]),
        ("ipv4_routes", ["/usr/bin/netstat", "-rn", "-f", "inet"]),
    ):
        try:
            p = subprocess.run(args, capture_output=True, text=True,
                               timeout=5, check=False)
            result[label] = {"rc": p.returncode,
                             "lines": p.stdout.splitlines()[:16]}
        except (OSError, subprocess.TimeoutExpired) as exc:
            result[label] = type(exc).__name__ + ":" + str(exc)[:120]
    for host in ("api.github.com", "codeload.github.com"):
        try:
            # TCP handshake only: no catalog GET, no test fetch, no service mutation.
            with socket.create_connection((host, 443), timeout=4):
                result[host] = "tcp_443_connected"
        except OSError as exc:
            result[host] = type(exc).__name__ + ":" + str(exc)[:120]
    print("STAGE5_EXTRA_REPEAT_FAILED_FETCH_NETWORK_DIAGNOSTICS=" +
          json.dumps(result, sort_keys=True), file=sys.stderr, flush=True)


def self_test():
    entries = {"lua/z%02d.lua" % i: "a" * 64 for i in range(LUA)}
    entries.update({"files/fake/x%02d.bin" % i: "b" * 64 for i in range(BIN)})
    digest = content_sha(entries)
    need(re.fullmatch(r"[0-9a-f]{64}", digest) is not None,
         "EXTRA_ROUNDTRIP_BAD_CATALOG_SHA")
    for changed in ({}, {"bad": "x" * 64}, {**entries, "strange": "x" * 64}):
        try:
            content_sha(changed)
        except Refusal:
            pass
        else:
            raise AssertionError("invalid catalog accepted")
    try:
        names_from_cache({"status": "ok", "lua": [{"origin": "other", "name": "../bad.lua"}],
                          "bin": []})
    except Refusal:
        pass
    else:
        raise AssertionError("unsafe cache basename accepted")
    fake = {"status": "ok", "lua": [{"origin": "other", "name": "s.lua"}],
            "bin": [{"origin": "upstream", "name": "u.bin"}]}
    need(names_from_cache(fake) == {"lua/s.lua"}, "EXTRA_ROUNDTRIP_CACHE_SELFTEST")
    print("PASS_STAGE5_EXTRA_REPEAT_INSTALL_REMOVE_SHAPE_NEGATIVES=1")
    return 0


def execute(initial_install):
    for key in ("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_NATIVE_BUILD_CI",
                "ZAPRET2_STAGE5_AUTHENTICATED_EXTRA_INSTALL", FLAG):
        need(os.environ.get(key) == "1",
             "EXTRA_ROUNDTRIP_DISPOSABLE_OPTIN_MISSING:" + key)
    need(os.environ.get("GITHUB_ACTIONS") == "true" and os.geteuid() == 0 and
         os.uname().sysname == "FreeBSD" and os.uname().machine == "amd64",
         "EXTRA_ROUNDTRIP_NOT_DISPOSABLE_NATIVE_CI_ROOT")
    original = module("stage5-installed-extra-install-http.py")
    remove = module("stage5-installed-extra-remove-http.py")
    active = module("stage2-opnsense-real-native-active-service.py")
    common = module("stage2-opnsense-real-native-shared-voice.py")
    voice = module("stage2-opnsense-real-native-voice-http.py")
    need(isinstance(initial_install, dict) and
         initial_install.get("status") == original.STATUS and
         initial_install.get("source_commit") == original.SOURCE_REVISION and
         initial_install.get("installed_extra_resource_count") == TOTAL and
         isinstance(initial_install.get("catalog_content_sha256"), str) and
         re.fullmatch(r"[a-f0-9]{64}", initial_install["catalog_content_sha256"]),
         "EXTRA_ROUNDTRIP_FIRST_REAL_INSTALL_RECEIPT_REQUIRED")

    engine_sha = active.guest_preflight()
    owner_start = common.witness(active, engine_sha, running=True, page="strategies")
    original_config = active.CONFIG.read_bytes()
    rules = active.plugin_rules()
    need(len(rules) == 2 and ROOT.is_dir() and not ROOT.is_symlink() and
         STATE.is_dir() and not STATE.is_symlink() and
         not (STATE / "transaction").exists() and
         not (STATE / "transaction").is_symlink(),
         "EXTRA_ROUNDTRIP_NATIVE_STARTING_STATE_UNSAFE")

    installed_root = Path("/usr/local/opnsense/scripts/OPNsense/Zapret")
    for name in ("extra_resources_operation.py", "extra_resources_transaction.py",
                 "extra_resources_reconcile.py", "extra_resources_inventory_cache.py"):
        actual = installed_root / name
        known = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret" / name
        need(actual.is_file() and not actual.is_symlink() and
             known.is_file() and actual.read_bytes() == known.read_bytes(),
             "EXTRA_ROUNDTRIP_PACKAGE_OWNED_WORKER_NOT_VERIFIED:" + name)
    sys.path.insert(0, str(installed_root))
    import extra_resources_reconcile as reconcile

    upstream = reconcile.tracked_resources(ROOT)
    manifest_path = STATE / "installed.json"
    need(manifest_path.is_file() and not manifest_path.is_symlink(),
         "EXTRA_ROUNDTRIP_INITIAL_MANIFEST_MISSING")
    metadata = json.loads(manifest_path.read_text(encoding="utf-8"))
    owned = reconcile.previous_metadata(manifest_path)
    need(metadata.get("source_commit") == original.SOURCE_REVISION and
         len(owned) == TOTAL and
         sum(x.startswith("lua/") for x in owned) == LUA and
         sum(x.startswith("files/fake/") for x in owned) == BIN and
         not set(owned).intersection(upstream) and
         content_sha(owned) == initial_install["catalog_content_sha256"],
         "EXTRA_ROUNDTRIP_PREVIOUSLY_VERIFIED_CATALOG_DIFFERS")
    installed = dict(upstream)
    installed.update(owned)
    need(reconcile.installed_resources(ROOT) == installed,
         "EXTRA_ROUNDTRIP_INITIAL_INSTALLED_FILES_NOT_EXACT")

    web = voice.GuestHttps()
    voice.login(web)
    initial_status = web.api("POST", BASE + "resourcesStatus", {})
    need(initial_status.get("status") == "ok" and
         initial_status.get("phase") == "ready" and
         initial_status.get("installed") is True and
         initial_status.get("busy") is False and
         initial_status.get("revision") == original.SOURCE_REVISION,
         "EXTRA_ROUNDTRIP_INSTALLED_READY_NOT_OBSERVED")
    prior_operation = initial_status.get("operation")
    initial_inventory = web.api("POST", BASE + "resourcesInventory", {})
    need(initial_inventory.get("installed") is True and
         names_from_cache(initial_inventory) == set(owned),
         "EXTRA_ROUNDTRIP_INITIAL_REAL_CACHE_NOT_EXACT")

    # Exactly one stock POST for the repeated, UNCHANGED content. A new
    # operation must run even though the disk content will not change.
    repeated = web.api("POST", BASE + "resourcesInstall", {})
    need(repeated.get("status") == "ok" and repeated.get("started") is True and
         re.fullmatch(r"[a-f0-9]{32}", str(repeated.get("operation", ""))) and
         repeated.get("operation") != prior_operation,
         "EXTRA_ROUNDTRIP_REPEAT_INSTALL_NOT_STARTED")
    try:
        completed = original.poll_terminal(web, repeated["operation"])
    except original.Refusal as exc:
        # Diagnostic ONLY. The native worker's failure remains terminal:
        # do not retry an uncertain resource mutation or reclassify as PASS.
        row = web.api("POST", BASE + "resourcesStatus", {})
        detail = str(row.get("detail", ""))[:240].replace("\n", " ").replace("\r", " ")
        failed_fetch_network_diagnostics()
        raise Refusal("EXTRA_ROUNDTRIP_REPEAT_INSTALL_TERMINAL_FAILED:" +
                      str(row.get("phase", "unknown")) + ":" + detail) from exc
    need(completed.get("operation") == repeated["operation"] and
         completed.get("revision") == original.SOURCE_REVISION,
         "EXTRA_ROUNDTRIP_REPEAT_INSTALL_NOT_CORRELATED")
    need(manifest_path.is_file() and not manifest_path.is_symlink() and
         json.loads(manifest_path.read_text(encoding="utf-8")) == metadata and
         reconcile.installed_resources(ROOT) == installed and
         names_from_cache(web.api("POST", BASE + "resourcesInventory", {})) == set(owned) and
         not (STATE / "transaction").exists(),
         "EXTRA_ROUNDTRIP_NO_CHANGE_CATALOG_NOT_PRESERVED")
    owner_repeat = common.witness(active, engine_sha, running=True, page="strategies")
    need(owner_repeat["id"] == owner_start["id"] and
         owner_repeat["pid"] != owner_start["pid"] and
         owner_repeat["rules"] == owner_start["rules"] and
         active.plugin_rules() == rules and
         active.CONFIG.read_bytes() == original_config,
         "EXTRA_ROUNDTRIP_REPEAT_STOP_START_NOT_PROVEN")

    # The plan SHA is installation-local and must be recomputed AFTER the
    # repeat. It is NOT the plugin archive or external-catalog SHA.
    native = reconcile.make_remove_plan(ROOT, manifest_path, active.CONFIG)
    local_sha = native["witness"]["inventory_sha256"]
    need(native["counts"] == {"lua": LUA, "bin": BIN, "total": TOTAL} and
         {r["path"] for r in native["remove"]} == set(owned) and
         reconcile.previous_metadata(manifest_path) == owned and
         native["installed"] == installed and native["upstream"] == upstream and
         re.fullmatch(r"[a-f0-9]{64}", local_sha) is not None,
         "EXTRA_ROUNDTRIP_LOCAL_POSITIVE_REMOVE_PLAN_NOT_EXACT")
    api_plan = web.api("POST", BASE + "resourcesRemovePlan", {})
    need(remove.plan_shape(api_plan, total=TOTAL, lua=LUA, bin_count=BIN) == local_sha,
         "EXTRA_ROUNDTRIP_HTTP_AND_LOCAL_REMOVE_PLAN_DIFFER")

    bad_count = web.api("POST", BASE + "resourcesRemove",
                        {"inventory_sha256": local_sha,
                         "confirmation": "REMOVE 72"})
    stale = "f" * 64 if local_sha != "f" * 64 else "e" * 64
    bad_witness = web.api("POST", BASE + "resourcesRemove",
                          {"inventory_sha256": stale,
                           "confirmation": "REMOVE 73"})
    need(all(row.get("status") == "rejected" and
             row.get("reason") == "plan_changed" and
             row.get("started") is False for row in (bad_count, bad_witness)),
         "EXTRA_ROUNDTRIP_BAD_CONFIRMATION_OR_STALE_SHA_NOT_REFUSED")
    need(common.witness(active, engine_sha, running=True, page="strategies") ==
         owner_repeat and
         reconcile.installed_resources(ROOT) == installed and
         reconcile.make_remove_plan(ROOT, manifest_path, active.CONFIG)
         ["witness"]["inventory_sha256"] == local_sha and
         active.CONFIG.read_bytes() == original_config and
         active.plugin_rules() == rules,
         "EXTRA_ROUNDTRIP_REJECTED_REMOVE_MUTATED_NATIVE_STATE")

    # ONE confirmed destructive operation, no automatic retry on uncertain
    # acknowledgement. Its native Apply creates a new committed shared owner.
    started = web.api("POST", BASE + "resourcesRemove",
                      {"inventory_sha256": local_sha,
                       "confirmation": "REMOVE 73"})
    need(started.get("status") == "ok" and started.get("started") is True and
         re.fullmatch(r"[a-f0-9]{32}", str(started.get("operation", ""))) and
         started["operation"] != repeated["operation"],
         "EXTRA_ROUNDTRIP_REAL_REMOVE_NOT_ACCEPTED")
    terminal = remove.poll_terminal(web, started["operation"])
    need(terminal.get("status") == "ok" and
         terminal.get("operation") == started["operation"] and
         terminal.get("phase") == "not_installed" and
         terminal.get("installed") is False and
         terminal.get("busy") is False,
         "EXTRA_ROUNDTRIP_REAL_REMOVE_NOT_COMPLETED")

    final_owner = common.witness(active, engine_sha, running=True, page="strategies")
    need(final_owner["id"] != owner_repeat["id"] and
         final_owner["pid"] != owner_repeat["pid"] and
         final_owner["rules"] == owner_start["rules"] and
         active.plugin_rules() == rules and
         active.CONFIG.read_bytes() == original_config,
         "EXTRA_ROUNDTRIP_NEW_SHARED_OWNER_OR_CONFIG_IPFW_NOT_PROVEN")
    final_plan = reconcile.make_remove_plan(ROOT, manifest_path, active.CONFIG)
    final_inventory = web.api("POST", BASE + "resourcesInventory", {})
    final_api_plan = web.api("POST", BASE + "resourcesRemovePlan", {})
    need(not manifest_path.exists() and not manifest_path.is_symlink() and
         reconcile.installed_resources(ROOT) == upstream and
         reconcile.tracked_resources(ROOT) == upstream and
         not reconcile.previous_metadata(manifest_path) and
         not final_plan["remove"] and
         final_plan["counts"] == {"lua": 0, "bin": 0, "total": 0} and
         remove.plan_shape(final_api_plan, total=0, lua=0, bin_count=0) ==
         final_plan["witness"]["inventory_sha256"] and
         final_inventory.get("installed") is False and
         not names_from_cache(final_inventory) and
         not (STATE / "transaction").exists() and
         not (STATE / "transaction").is_symlink() and
         not (ROOT / ".extra-resources-remove-quarantine").exists(),
         "EXTRA_ROUNDTRIP_REMOVAL_DID_NOT_RESTORE_EXACT_UPSTREAM")

    report = {
        "schema": 1, "status": STATUS,
        "source_commit": original.SOURCE_REVISION,
        "catalog_content_sha256": initial_install["catalog_content_sha256"],
        "resource_count": TOTAL, "lua_count": LUA, "bin_count": BIN,
        "repeat_real_https_install_completed": True,
        "repeat_no_change_catalog_bytes_preserved": True,
        "repeat_native_stop_start_rotated_pid_same_fd9": True,
        "fresh_local_remove_plan_matched_native_https": True,
        "bad_confirmation_and_stale_local_sha_refused": True,
        "real_positive_remove_73_correlated_terminal": True,
        "real_remove_committed_new_shared_owner": True,
        "native_config_and_ipfw_preserved": True,
        "all_extra_files_removed_upstream_intact": True,
        "installed_metadata_and_inventory_cache_cleared": True,
        "extra_local_plan_sha256": local_sha,
        "physical_browser_click_tested": False,
        "owner_appliance_modified": False,
    }
    print("STAGE5_EXTRA_ROUNDTRIP_HTTP=" + json.dumps(report, sort_keys=True))
    return report


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        raise Refusal("EXTRA_ROUNDTRIP_REQUIRES_INSTALLED_STAGE5_CALLER")
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE5_EXTRA_ROUNDTRIP_HTTP=REFUSED:" + str(exc),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
