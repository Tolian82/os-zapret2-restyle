#!/usr/bin/env python3
"""S05b2a genuine delayed engine exit on a *disposable* OPNsense VM.

Run only under stage0+S04C+S05B2 isolated CI gates. Intentional SIGTERM is
an isolated fault injection, NEVER traffic maintenance or owner device action.
"""
from __future__ import annotations
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
PID = Path("/var/run/dvtws2.pid")
ORIGINAL = Path("/var/db/zapret2/shared-apply/operation.json")


def load_s05a():
    spec = importlib.util.spec_from_file_location(
        "s05b2a_original_native", HERE / "tz6v5-s05a-status-json-native.py")
    obj = importlib.util.module_from_spec(spec)
    sys.dont_write_bytecode = True
    spec.loader.exec_module(obj)
    return obj


s05a = load_s05a()
s04 = s05a.s04


def original_record():
    raw = ORIGINAL.read_bytes()
    s04.need(0 < len(raw) <= 8192, "S05B2_UNQUALIFIED_ORIGINAL_JOURNAL_SIZE")
    row = json.loads(raw)
    s04.need(type(row) is dict and row.get("phase") == "committed" and
             re.fullmatch(r"[a-f0-9]{32}", row.get("detail", {}).get("id", "")) is not None,
             "S05B2_UNQUALIFIED_ORIGINAL_COMMITTED_OWNER")
    return row


def status_json(label, runtime, code, *, error=False):
    before = s04.snapshot()
    p = s04.run([str(SERVICE), "status", "--json"], timeout=40)
    after = s04.snapshot()
    if before != after:
        # Fail hard, but label only resource classes and metadata categories.
        # Do NOT put private file paths, PID values, kernel rule lines, argv,
        # user Config or any raw log bytes into a CI diagnostic marker.
        drift = []
        for name in ("config", "engine", "process"):
            if before[name] != after[name]:
                drift.append(name)
        for name in ("rules", "tables", "ipfw_module", "ipdivert_module"):
            if before["kernel"][name] != after["kernel"][name]:
                drift.append("kernel_" + name)
        old, new = before["tree"], after["tree"]
        for category, prefix in (
            ("pkgdb", "/var/db/pkg/"),
            ("original", "/var/db/zapret2/"),
            ("active", "/usr/local/etc/zapret2/runtime-v2/"),
            ("setup", "/var/db/zapret2-restyle/"),
            ("backend", "/usr/local/opnsense/scripts/OPNsense/Zapret/backend/"),
            ("pid", "/var/run/"),
        ):
            changed = [k for k in set(old) | set(new)
                       if k.startswith(prefix) and old.get(k) != new.get(k)]
            if changed:
                added = sum(k not in old for k in changed)
                removed = sum(k not in new for k in changed)
                fields = set()
                for k in changed:
                    a, b = old.get(k), new.get(k)
                    if isinstance(a, list) and isinstance(b, list):
                        fields.update(field for i, field in (
                            (2, "inode"), (7, "size"), (8, "mtime"),
                            (9, "content")) if i < len(a) and i < len(b)
                            and a[i] != b[i])
                    else:
                        fields.add("type")
                drift.append("tree_" + category + "_" + str(len(changed)) +
                             "_new" + str(added) + "_del" + str(removed) +
                             "_" + "-".join(sorted(fields)))
        if not drift:
            drift.append("unclassified")
        raise s04.Refusal("S05B2_JSON_STATUS_STATE_DRIFT_" + label +
                         "__" + "_".join(drift[:14]))
    s04.need(p.stdout.count("\n") == 1 and p.returncode == (
        0 if runtime == "RUNNING" else 1 if runtime == "STOPPED" else 2
    ), "S05B2_STATUS_RC_UNVERIFIED_" + label)
    try:
        row = json.loads(p.stdout)
    except ValueError:
        raise s04.Refusal("S05B2_STATUS_NOT_JSON_" + label) from None
    s04.need(row.get("runtime_state") == runtime and row.get("code") == code
             and row.get("authorization") == "NONE" and
             row.get("physical_transition_allowed") is False,
             "S05B2_STATUS_OWNER_UNQUALIFIED_" + label)
    event = row.get("last_error")
    if error:
        s04.need(row.get("diagnostic_state") == "qualified" and
                 type(event) is dict and event.get("code") == "ENGINE_EXIT_AFTER_READY"
                 and event.get("action") == "runtime-failure" and
                 event.get("stage") == "engine-stop" and
                 event.get("exit_status") is None and
                 event.get("stderr_excerpt") is None and
                 event.get("runtime_before") == "RUNNING" and
                 event.get("runtime_after") == "STOPPED",
                 "S05B2_ORIGINAL_LATE_ERROR_MISSING_OR_FABRICATED")
    else:
        s04.need(event is None, "S05B2_STALE_DIAGNOSTIC_" + label)
    s04.need(not any(x in p.stdout for x in
                    ("argv", "/conf/", "password", "token=", "127.0.0.1")),
             "S05B2_STATUS_SECRET_LEAK_" + label)
    return {"case": label, "runtime": runtime, "status_rc": p.returncode,
            "no_write": True, "code": event["code"] if error else None}


def real_fault():
    s04.guest_gate("hot")
    s04.need(os.environ.get("ZAPRET2_S05B2_DISPOSABLE_NATIVE") == "1",
             "S05B2_NO_DISPOSABLE_OPTIN")
    clean = s04.load("s05b2_hot_clean", "stage2-opnsense-real-native-clean-install.py")
    s04.install(clean)
    s04.upstream()
    g04 = s04.load("s05b2_g04", "stage2-opnsense-g04-native-runtime.py")
    node = g04.model()
    traffic = node.findtext("strategy/trafficargs") or ""
    domains = node.findtext("hostlist/youtubedomains") or ""
    s04.need(traffic.count("--new") == 1 and len(domains.splitlines()) == 10,
             "S05B2_BASELINE_RELEASE_CHANGED")
    g04.authenticated_first_apply(traffic, domains)
    # Prewarm original plain FD9 *outside* the no-write snapshot.
    s05a.plain_legacy({"runtime": "RUNNING"})
    original = original_record()
    owner_id = original["detail"]["id"]
    s04.need("failure" not in original, "S05B2_INITIAL_FAILURE_ALREADY_PRESENT")
    rows = [status_json("original-running", "RUNNING",
                        "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION")]
    source_pid = PID.read_text("ascii").strip()
    s04.need(re.fullmatch(r"[1-9][0-9]{1,9}", source_pid) is not None,
             "S05B2_ORIGINAL_PID_UNQUALIFIED")
    # Validate physical monitor OS argv PINNED at the original engine start.
    monitor_pid = Path("/var/run/zapret2-supervisor-monitor.pid").read_text("ascii").strip()
    s04.need(re.fullmatch(r"[1-9][0-9]{1,9}", monitor_pid) is not None,
             "S05B2_MONITOR_PID_UNQUALIFIED")
    monitor_cmd = s04.run(["/bin/ps", "-p", monitor_pid, "-o", "command="])
    expected_monitor = ("/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh "
                        "/var/run/dvtws2.pid "
                        "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh "
                        "/usr/local/etc/zapret2/binaries/my/dvtws2 " + source_pid)
    s04.need(monitor_cmd.returncode == 0 and
             monitor_cmd.stdout.strip() in
             (expected_monitor, "/bin/sh " + expected_monitor),
             "S05B2_UNPINNED_ORIGINAL_SUPERVISOR_ARGV")
    wrong = str(int(source_pid) + 1)
    # Test a stale callback while real Common RUNNING: no cleanup, no journal
    # mutation, no IPFW modification or change of PID/protected Config.
    before = s04.snapshot()
    stale = s04.run([str(SERVICE), "runtime-failure",
                     "dvtws2 exited after ready", wrong], timeout=35)
    after = s04.snapshot()
    s04.need(stale.returncode == 69,
             "S05B2_STALE_CALLBACK_NOT_REFUSED_RC_" + str(stale.returncode))
    s04.need(original_record() == original,
             "S05B2_STALE_CALLBACK_CHANGED_ORIGINAL_JOURNAL")
    # The legacy mutating callback still enters original FD9, whose sole
    # fixed lockfile can be touched by lockf. That is NOT a JSON Status call.
    # Everything else (original journal, Config, PID, kernel, package, runtime)
    # must remain byte/metadata identical on this refused callback.
    for key in ("config", "engine", "process"):
        s04.need(before[key] == after[key],
                 "S05B2_STALE_CALLBACK_MUTATED_" + key)
    s04.need(before["kernel"] == after["kernel"],
             "S05B2_STALE_CALLBACK_MUTATED_KERNEL")
    changed = {k for k in set(before["tree"]) | set(after["tree"])
               if before["tree"].get(k) != after["tree"].get(k)}
    s04.need(changed <= {"/var/run/zapret2-lifecycle.lock"},
             "S05B2_STALE_CALLBACK_CHANGED_NONFD9_RESOURCE")
    rows.append(status_json("stale-callback-no-effect", "RUNNING",
                            "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION"))
    # Only now intentionally terminate the genuine installed native child.
    # The already-running ORIGINAL supervisor must detect the disappearance
    # and request original FD9 runtime-failure with the pinned old PID.
    termination = s04.run(["/bin/kill", "-TERM", source_pid], timeout=15)
    s04.need(termination.returncode == 0, "S05B2_NATIVE_FAULT_NOT_DELIVERED")
    final = None
    for _ in range(45):
        time.sleep(2)
        row = original_record()
        if "failure" in row:
            final = row
            break
    if final is None:
        # Actual supervisor delivery must pass WITHOUT manual intervention.
        # This is a diagnostic-only original FD9 callback AFTER the failed
        # native acceptance; success here does NOT turn the native gate green.
        before_direct = original_record()
        live = s04.run([str(SERVICE), "status", "--json"], timeout=40)
        try:
            observed = json.loads(live.stdout)
            runtime = observed.get("runtime_state", "unknown")
            if runtime not in ("RUNNING", "STOPPED", "INCOMPLETE",
                               "FOREIGN_OR_UNVERIFIED", "UNKNOWN"):
                runtime = "unknown"
        except ValueError:
            runtime = "invalid"
        monitor = Path("/var/run/zapret2-supervisor-monitor.pid").exists()
        child = PID.exists()
        stagefile = Path("/var/run/zapret2-execution.status")
        stage = "absent"
        if stagefile.exists() and stagefile.is_file():
            # Only expose a bounded enumerated stage state; never the
            # original stage message, argv, Config or IPFW.
            items = stagefile.read_text(errors="replace")[:2048].split("|")
            if len(items) >= 4 and items[3] in ("running", "ok", "failed", "stopped"):
                stage = items[3]
            else:
                stage = "unqualified"
        direct = s04.run([str(SERVICE), "runtime-failure",
                          "dvtws2 exited after the service reached ready state",
                          source_pid], timeout=125)
        now = original_record()
        result = "recorded" if "failure" in now else "absent"
        s04.need(False, "S05B2_SUPERVISOR_CALLBACK_UNCONFIRMED_" +
                 runtime + "_status" + str(live.returncode) +
                 "_monitor" + str(int(monitor)) +
                 "_pidfile" + str(int(child)) +
                 "_stage" + stage +
                 "_direct" + str(direct.returncode) + "_" + result)
    s04.need(final["detail"]["id"] == owner_id and
             final["failure"].get("operation_id") == owner_id and
             final["failure"].get("code") == "ENGINE_EXIT_AFTER_READY" and
             final["failure"].get("exit_status") is None,
             "S05B2_ORIGINAL_SUPERVISOR_RECEIPT_INVALID")
    rows.append(status_json("real-post-ready-exit", "STOPPED",
                            "COMPONENTS_PRESENT_REQUIRES_PREFLIGHT", error=True))
    # Native common Start is allowed to clear only after full sealed owner,
    # process/supervisor and IPFW evidence becomes RUNNING again.
    restarted = s04.run([str(SERVICE), "start"], timeout=150)
    s04.need(restarted.returncode == 0, "S05B2_ORIGINAL_VERIFIED_RESTART_FAILED")
    s04.need("failure" not in original_record(),
             "S05B2_OLD_FAILURE_SURVIVED_VERIFIED_RESTART")
    rows.append(status_json("verified-running-clears-error", "RUNNING",
                            "RUNNING_REQUIRES_ORIGINAL_OWNER_ATTESTATION"))
    return rows


def main(argv):
    if argv == ["--self-test"]:
        src = Path(__file__).read_text()
        tree = ast.parse(src)
        s04.need("s04.guest_gate(\"hot\")" in src and
                 "ZAPRET2_S05B2_DISPOSABLE_NATIVE" in src and
                 not any(isinstance(node, ast.Call) and
                         isinstance(node.func, ast.Attribute) and
                         node.func.attr == "kill" and
                         len(node.args) > 1 and
                         isinstance(node.args[1], ast.Attribute) and
                         node.args[1].attr in ("SIGSTOP", "SIGCONT")
                         for node in ast.walk(tree)),
                 "S05B2_MISSING_ISOLATED_FAULT_GATE")
        print("S05B2_SOURCE_GATE=PASS")
        return 0
    if argv != ["hot"]:
        return 64
    try:
        result = real_fault()
        print("S05B2_NATIVE=" + json.dumps({
            "status": "PASS", "cases": result, "original_fd9_owner": True,
            "physical_engine_fault_disposable": True,
            "operator_device_touched": False,
            "raw_stderr_exposed": False,
            "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        }, sort_keys=True, separators=(",", ":")))
        return 0
    except (s04.Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        # Never print original error data or sensitive file contents.
        print("S05B2_NATIVE=REFUSED:" +
              str(exc).split(":", 1)[0][:120], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
