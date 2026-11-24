#!/usr/bin/env python3
"""TZ6v5 S05a: physical JSON Status on disposable OPNsense, not a mock."""
from __future__ import annotations

import ast
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BACKEND = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
SERVICE = BACKEND.parent / "zapret_service.sh"
SOURCE = HERE.parent / "src/opnsense/scripts/OPNsense/Zapret/backend/status_readonly.py"
INSTALLED = BACKEND / "status_readonly.py"


def existing():
    spec = importlib.util.spec_from_file_location(
        "s05a_existing_s04c", HERE / "tz6v5-s04c-opnsense-native-inventory.py")
    obj = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(obj)
    # S05a explicitly covers installed Python package __pycache__, in
    # addition to S04c's exact Config, pkgdb, runtime, journal and IPFW trees.
    obj.ROOTS = (*obj.ROOTS, BACKEND)
    return obj


s04 = existing()


def status_witness(label, expected, *, preinstall=False, setup_refused=False):
    # Also retain the S04 real physical native classification witness.
    s04.witness(label, expected, preinstall=preinstall)
    reader = SOURCE if preinstall else SERVICE
    if preinstall:
        s04.need(not INSTALLED.exists(), "S05A_PREINSTALLED_CLI_WAS_PRESENT")
        argv = ["/usr/local/bin/python3", str(reader)]
    else:
        s04.need(INSTALLED.is_file() and
                 INSTALLED.read_bytes() == SOURCE.read_bytes(),
                 "S05A_INSTALLED_JSON_READER_NOT_SOURCE_IDENTICAL")
        argv = [str(reader), "status", "--json"]
    before = s04.snapshot()
    p = s04.run(argv, timeout=90)
    after = s04.snapshot()
    if before != after:
        # Report fixed resource classes only, never Config values, file paths,
        # IPFW rules, executable argv, PID values or untrusted log bytes.
        classes = []
        for name in ("config", "engine", "process"):
            if before[name] != after[name]:
                classes.append(name)
        for name in ("rules", "tables", "ipfw_module", "ipdivert_module"):
            if before["kernel"][name] != after["kernel"][name]:
                classes.append("kernel_" + name)
        original, current = before["tree"], after["tree"]
        if original != current:
            keys = set(original) | set(current)
            for category, prefix in (
                ("pkgdb", "/var/db/pkg/"),
                ("shared", "/var/db/zapret2/"),
                ("active", "/usr/local/etc/zapret2/runtime-v2/"),
                ("setup", "/var/db/zapret2-restyle/"),
                ("backend", str(BACKEND) + "/"),
                ("pid", "/var/run/"),
            ):
                changed = [k for k in keys if k.startswith(prefix)
                           and original.get(k) != current.get(k)]
                if changed:
                    added = sum(k not in original for k in changed)
                    removed = sum(k not in current for k in changed)
                    fields = set()
                    for k in changed:
                        a, b = original.get(k), current.get(k)
                        if isinstance(a, list) and isinstance(b, list):
                            fields.update(n for i, n in ((2, "inode"), (7, "size"),
                                                          (8, "mtime"), (9, "content"))
                                          if i < len(a) and i < len(b) and a[i] != b[i])
                        else:
                            fields.add("type")
                    classes.append("tree_" + category + "_" + str(len(changed)) +
                                   "_new" + str(added) + "_del" + str(removed) +
                                   "_" + "-".join(sorted(fields)))
            if not any(s.startswith("tree_") for s in classes):
                classes.append("tree_root")
        raise s04.Refusal("S05A_JSON_STATUS_STATE_DRIFT_" + label + "__" +
                          "_".join(classes[:12]))
    try:
        row = json.loads(p.stdout)
    except ValueError:
        raise s04.Refusal("S05A_NOT_ONE_JSON_DOCUMENT_" + label) from None
    s04.need(type(row) is dict and p.stdout.strip().startswith("{") and
             p.stdout.strip().endswith("}") and
             p.stdout.count("\n") == 1,
             "S05A_JSON_OUTPUT_NOT_EXACT_ONE_LINE_" + label)
    expected_runtime = expected.get("runtime", "STOPPED")
    desired_rc = (0 if expected_runtime == "RUNNING" else
                  1 if expected_runtime == "STOPPED" else 2)
    s04.need(p.returncode == desired_rc and row.get("status_exit_code") == desired_rc
             and row.get("runtime_state") == expected_runtime
             and row.get("code") == expected.get("classification"),
             "S05A_JSON_NOT_ORIGINAL_RUNTIME_" + label)
    s04.need(row.get("authorization") == "NONE" and
             row.get("physical_transition_allowed") is False and
             row.get("schema") == 1 and type(row.get("components")) is dict,
             "S05A_JSON_GRANTED_AUTHORITY_" + label)
    for name in ("stage", "operation_id", "generation", "exit_status",
                 "stderr_excerpt", "log_ref", "requested", "effective"):
        value = "install" if setup_refused and name == "stage" else None
        s04.need(name in row and row[name] == value,
                 "S05A_JSON_INVENTED_DIAGNOSTIC_" + name)
    event = row.get("last_error")
    if setup_refused:
        s04.need(row.get("diagnostic_state") == "qualified" and
                 isinstance(event, dict) and
                 event.get("source") == "original-setup-status" and
                 event.get("code") == "SETUP_RELEASE_LIST_UNAVAILABLE" and
                 event.get("verification") == "refused" and
                 all(name in event and event[name] is None for name in
                     ("timestamp", "operation_id", "generation", "exit_status",
                      "runtime_before", "runtime_after", "stderr_excerpt", "log_ref")),
                 "S05D3_ORIGINAL_FIRST_INSTALL_STATUS_MISSING")
    elif expected.get("engine") == "absent" or label == "engine-no-config":
        s04.need(event is None, "S05D3_UNEXPECTED_FIRST_INSTALL_DIAGNOSTIC")
    s04.need(not any(secret in p.stdout for secret in
                     ("pid", "argv", "/conf/", "secret", "password", "token")),
             "S05A_JSON_LEAK")
    return {"case": label, "json_code": row["code"],
            "runtime": row["runtime_state"], "exit": desired_rc,
            "json_no_write": True}


def invalid_options():
    # Invalid combinations MUST be refused before opening original FD9.
    before = s04.snapshot()
    for args in (["status", "--force"], ["status", "--json", "--json"],
                 ["status", "--check"], ["status", "--json", "--force"]):
        p = s04.run([str(SERVICE), *args], timeout=20)
        s04.need(p.returncode == 64 and p.stdout.strip() == "",
                 "S05A_INVALID_OPTION_NOT_REFUSED")
    after = s04.snapshot()
    s04.need(before == after, "S05A_INVALID_OPTION_WROTE_STATE")


def plain_legacy(expected):
    # Kept *outside* JSON no-write windows. The original plain Status route
    # intentionally retains existing FD9 semantics and existing messages.
    p = s04.run([str(SERVICE), "status"], timeout=30)
    label = expected["runtime"]
    expected_text, rc = ({
        "RUNNING": ("zapret is running", 0),
        "STOPPED": ("zapret is not running", 1),
        "FOREIGN_OR_UNVERIFIED": ("zapret is in an incomplete runtime state", 2),
    })[label]
    s04.need(p.returncode == rc and p.stdout.strip() == expected_text,
             "S05A_PLAIN_STATUS_COMPATIBILITY_FAILED")


def setup_failure_witness(expected):
    state = Path("/var/db/zapret2-restyle")
    empty_cache = state / ".s05-no-release-cache"
    installed_setup = SERVICE.with_name("setup_transaction.sh")
    s04.need(not empty_cache.exists() and not empty_cache.is_symlink(),
             "S05D3_EXPECTED_EMPTY_PRIVATE_RELEASE_CACHE")
    before = s04.snapshot()
    result = s04.run(["/usr/bin/env", "FETCH_BIN=/usr/bin/false",
                      f"RELEASE_CACHE={empty_cache}", str(installed_setup),
                      "install", "v1.0.7"], timeout=90)
    after = s04.snapshot()
    s04.need(result.returncode == 69 and
             (state / "setup.status").read_bytes() ==
             b"failed\ncause=release-list-unavailable\n",
             "S05D3_ORIGINAL_FIRST_INSTALL_REFUSAL_NOT_RECORDED")
    s04.need(not (state / "first-install.intent").exists() and
             not Path("/usr/local/etc/zapret2.first-install").exists() and
             not (state / "runtime.release").exists() and
             not empty_cache.exists() and
             all(before[key] == after[key] for key in
                 ("config", "engine", "process", "kernel")),
             "S05D3_FIRST_INSTALL_REFUSAL_LEFT_RUNTIME_CHANGES")
    return status_witness("first-install-release-list-refused", expected,
                          setup_refused=True)


def cold():
    clean = s04.load("s05a_cold_clean", "stage2-opnsense-real-native-clean-install.py")
    clean.preflight()
    s04.need(not s04.ENGINE.exists(), "S05A_COLD_ENGINE_PRESENT")
    cases = [status_witness("nothing", {
        "plugin": "absent", "engine": "absent", "config": "absent",
        "manifest": "missing", "runtime": "STOPPED",
        "classification": "PLUGIN_NOT_INSTALLED"}, preinstall=True)]
    s04.install(clean)
    s04.need(not s04.ENGINE.exists(), "S05A_PLUGIN_ONLY_ENGINE_PRESENT")
    installed = {"plugin": "installed", "engine": "absent",
                 "config": "initialized", "manifest": "missing",
                 "runtime": "STOPPED", "classification": "ENGINE_NOT_INSTALLED"}
    plain_legacy(installed)
    invalid_options()
    cases.append(status_witness("plugin-no-engine", installed))
    cases.append(setup_failure_witness(installed))
    s04.upstream()
    s04.drop_config()
    cases.append(status_witness("engine-no-config", {
        "plugin": "installed", "engine": "valid", "config": "absent",
        "manifest": "missing", "runtime": "STOPPED",
        "classification": "CONFIG_UNINITIALIZED"}))
    return cases


def hot():
    clean = s04.load("s05a_hot_clean", "stage2-opnsense-real-native-clean-install.py")
    s04.install(clean)
    s04.upstream()
    g04 = s04.load("s05a_g04", "stage2-opnsense-g04-native-runtime.py")
    node = g04.model()
    traffic = node.findtext("strategy/trafficargs") or ""
    youtube = node.findtext("hostlist/youtubedomains") or ""
    s04.need(traffic.count("--new") == 1 and
             len(youtube.splitlines()) == 10, "S05A_G04_INITIAL_STRATEGY_CHANGED")
    g04.authenticated_first_apply(traffic, youtube)
    running = {"plugin": "installed", "engine": "valid",
               "config": "initialized", "manifest": "valid",
               "runtime": "RUNNING",
               "classification": "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION"}
    plain_legacy(running)
    invalid_options()
    rows = [status_witness("healthy-running-control", running)]
    s04.corrupt_config()
    rows.append(status_witness("running-invalid-config", {
        "plugin": "installed", "engine": "valid", "config": "invalid",
        "manifest": "valid", "runtime": "RUNNING",
        "classification": "CONFIG_INVALID"}))
    s04.foreign_rule()
    rows.append(status_witness("foreign-ipfw", {
        "plugin": "installed", "engine": "valid", "config": "invalid",
        "manifest": "valid", "runtime": "FOREIGN_OR_UNVERIFIED",
        "classification": "FOREIGN_OWNER"}))
    # Never Stop contaminated owner or delete the separate foreign rule.
    return rows


def main(argv):
    if argv == ["--self-test"]:
        # AST-based safety: do not reject string literals in this self-test.
        tree = ast.parse(Path(__file__).read_text())
        forbidden = {"kill", "rmtree", "remove", "rename", "replace", "unlink"}
        s04.need(not any(isinstance(node, ast.Call) and
                         isinstance(node.func, ast.Attribute) and
                         node.func.attr in forbidden
                         for node in ast.walk(tree)),
                 "S05A_NATIVE_TEST_MUTATING")
        print("PASS_S05A_NATIVE_SOURCE_GATE")
        return 0
    if len(argv) != 1 or argv[0] not in ("cold", "hot"):
        return 64
    try:
        s04.guest_gate(argv[0])
        s04.need(os.environ.get("ZAPRET2_S05A_DISPOSABLE_NATIVE") == "1",
                 "S05A_DISPOSABLE_NATIVE_OPTIN_REQUIRED")
        result = cold() if argv[0] == "cold" else hot()
        print("S05A_NATIVE=" + json.dumps({
            "mode": argv[0], "cases": result,
            "status_json_no_writes": True, "no_second_owner": True,
            "operator_device_touched": False,
            "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        }, sort_keys=True, separators=(",", ":")))
        return 0
    except (s04.Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("S05A_NATIVE=REFUSED:" + str(exc).split(":", 1)[0][:110],
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
