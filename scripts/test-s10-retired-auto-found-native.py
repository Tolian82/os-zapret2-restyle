#!/usr/bin/env python3
"""S10 R3 disposable positive: real HTTPS Auto schema3 -> ONE original Stop -> archived ACK.

Never creates an epoch, changes Config or simulates the old process. The
installed native Common service is the only actuator; after it stops,
separate original-FD9/P2a inspection independently proves the same epoch
and historical archive with repair=False. Extension point: real Found.
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
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
WAL = Path("/var/db/zapret2/shared-apply/operation.json")
CONFIG = Path("/conf/config.xml")
PYTHON_RUNTIME = "/usr/local/opnsense/scripts/OPNsense/Zapret/python_runtime.sh"
LOCK = "/var/run/zapret2-lifecycle.lock"
BACKEND = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
HEX32 = re.compile(r"[a-f0-9]{32}\Z")


class Refused(RuntimeError):
    pass


def need(ok, label):
    if not ok:
        raise Refused(label)


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    need(spec is not None and spec.loader is not None, "S10_AUTO_TEST_MODULE_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def first_base_recovery_diagnosed():
    """Disposable-only observation of the actual joined recovery; no retry."""
    import tempfile

    module = BACKEND / "neutral_schema3_quiescent_preimage.py"
    original = module.read_bytes()
    with tempfile.TemporaryDirectory(prefix="s10-first-recovery-", dir="/root") as folder:
        trace = Path(folder) / "locations"
        trace.touch(mode=0o600)
        # Write only finite boundary names, numeric outcome and source locations.
        # Direct private fixture trace survives nested stdout/stderr filtering.
        # Wrappers always propagate the original result or original exception.
        addition = r'''
_S10_TEST_TRACE = __TRACE_PATH__
def _s10_test_emit(message):
    try:
        with open(_S10_TEST_TRACE, "a", encoding="ascii") as output:
            output.write("S10_RECOVERY_DIAG=" + message + "\n")
    except OSError:
        pass

def _s10_test_exception(label, error):
    modules = {
        "neutral_schema3_quiescent_preimage": "M11",
        "neutral_schema3_previous_physical": "M02",
        "auto_detect_original_lock_handoff": "M05",
        "voice_ipfw_adapter": "M06",
        "voice_firewall_transaction": "M07",
        "neutral_root_stage": "M09",
        "shared_apply_seal": "M10",
        "shared_apply_operation": "M04",
        "auto_detect_fd": "FD",
        "auto_detect_post_drop": "CUT",
    }
    seen = set()
    count = 0
    while error is not None and id(error) not in seen and len(seen) < 8:
        seen.add(id(error))
        tb = error.__traceback__
        while tb is not None and count < 32:
            code = modules.get(tb.tb_frame.f_globals.get("__name__"))
            if code is not None and 0 < tb.tb_lineno <= 99999:
                _s10_test_emit(label + ":" + code + ":" + str(tb.tb_lineno))
                count += 1
            tb = tb.tb_next
        error = error.__cause__ or error.__context__

_s10_test_original_join = _run_bound_restore_joined
def _run_bound_restore_joined(command, **kwargs):
    if "ordinary-first-recover" in command:
        label = "PHP"
    elif "shared-apply-first-running-base-physical" in command:
        label = "STOP"
    elif "zapret-first-cold" in command:
        label = "TREE"
    else:
        label = "OTHER"
    try:
        reply = _s10_test_original_join(command, **kwargs)
    except BaseException as error:
        _s10_test_exception(label, error)
        raise
    if label != "OTHER":
        import re
        out, err = reply.stdout, reply.stderr
        _s10_test_emit(label + ":RC_" + str(reply.returncode) +
            ":OUT_" + str(len(out) if isinstance(out, bytes) else 0) +
            ":ERR_" + str(len(err) if isinstance(err, bytes) else 0))
        if isinstance(err, bytes):
            for line in err[:8192].split(b"\n")[:-1][:64]:
                if re.fullmatch(rb"S10_FIRST_TRACE=D(?:0[1-9]|[12][0-9]|3[0-4])", line) or re.fullmatch(
                        rb"S10_MANAGED_TRACE=(?:M(?:0[1-9]|1[0-4])|P0[1-3]):[1-9][0-9]{0,4}", line):
                    _s10_test_emit(label + ":" + line.decode("ascii"))
    return reply

def _s10_test_wrap(original, label):
    def wrapped(*args, **kwargs):
        try:
            return original(*args, **kwargs)
        except BaseException as error:
            _s10_test_exception(label, error)
            raise
    return wrapped

finish_first_config_recovery_locked = _s10_test_wrap(
    finish_first_config_recovery_locked, "CONFIG")
native_guard_first_running_base_stopped_shell_locked = _s10_test_wrap(
    native_guard_first_running_base_stopped_shell_locked, "STOPPED")
'''
        need(addition.count("__TRACE_PATH__") == 1, "S10_RECOVERY_DIAG_PATH_REQUIRED")
        instrumented = original + b"\n" + addition.replace("__TRACE_PATH__", repr(str(trace))).encode("ascii")
        compile(instrumented, str(module), "exec")
        try:
            module.write_bytes(instrumented)
            reply = subprocess.run([str(SERVICE), "start"], capture_output=True, timeout=180)
        finally:
            module.write_bytes(original)
        need(module.read_bytes() == original, "S10_RECOVERY_DIAG_SOURCE_RESTORE_REQUIRED")
        # A complete original result is still required by the existing test.
        # Do not print arbitrary content from a fixture-owned trace.
        with trace.open("rb") as handle:
            raw = handle.read(16385)
        need(len(raw) <= 16384, "S10_RECOVERY_DIAG_LIMIT")
        for line in raw.split(b"\n")[:-1][:128]:
            if re.fullmatch(rb"S10_RECOVERY_DIAG=(?:PHP|STOP|TREE|OTHER|CONFIG|STOPPED):(?:RC_-?[0-9]{1,3}:OUT_[0-9]{1,9}:ERR_[0-9]{1,9}|(?:M(?:0[1-9]|1[0-4])|FD|CUT):[1-9][0-9]{0,4}|S10_FIRST_TRACE=D(?:0[1-9]|[12][0-9]|3[0-4])|S10_MANAGED_TRACE=(?:M(?:0[1-9]|1[0-4])|P0[1-3]):[1-9][0-9]{0,4})", line):
                print(line.decode("ascii"), flush=True)
        return reply


def inspect_first_restored():
    """Original FD9 independent physical readback, never a new lifecycle owner."""
    import hashlib
    from neutral_root_stage import verify_original_operation_pins
    from neutral_schema3_quiescent_preimage import (_zero_processes, _empty_kernel, _present,
        _reject_cold_recovery_residue, CHILD_PID, MONITOR_PID, DAEMON_PID)
    from shared_apply_operation import SharedApplyOperation, committed_owner, committed_manifest, native_lifecycle_gate
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    record = store.read()
    need(type(record) is dict and record.get("phase") == "restored" and
         record.get("manifest", {}).get("schema") == 2 and
         "first_running_sha256" in record and "first_pretraffic_sha256" in record and
         not ({"previous", "previous_manifest", "found"} & record.keys()) and
         committed_owner(record) is None and committed_manifest(record) is None,
         "S10_AUTO_FIRST_RESTORED_OWNER_REQUIRED")
    op = record["detail"]["id"]
    release = WORK / op / "release"
    verify_original_operation_pins(record=record, parent=WORK, owner_uid=0)
    _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
    need(not _present(COMMON_ACTIVE), "S10_AUTO_FIRST_RESTORED_ACTIVE_RESIDUE")
    _reject_cold_recovery_residue(COMMON_ACTIVE)
    need(_empty_kernel(release) in ("native-kernel-absent", "native-managed-kernel-empty"),
         "S10_AUTO_FIRST_RESTORED_KERNEL_RESIDUE")
    need(not native_lifecycle_gate()["safe_to_mutate"] and
         not native_lifecycle_gate("common-apply")["safe_to_mutate"] and store.read() == record,
         "S10_AUTO_FIRST_RESTORED_LEGACY_FENCE_REQUIRED")
    print("S10_FIRST_BASE_INDEPENDENT=PASS", flush=True)


def inspect_original_stopped():
    """Read only; FD9 acquired in the original lockf shell, then P2a."""
    import hashlib
    import pwd
    from auto_detect_owner import attest_learning_stopped_generation
    from auto_detect_learning_retirement import (
        retired_learning_stopped, RETIRE_DIR, READY)
    from auto_detect_epoch_receipts import EpochReceipts, _read
    from auto_detect_queue import DurableInbox
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from auto_detect_fd import _probe_original_inode
    from neutral_schema3_previous_physical import _full_prior_tree
    from neutral_schema3_quiescent_preimage import (
        _zero_processes, _empty_kernel, _verify_idle_producer,
        CHILD_PID, MONITOR_PID, DAEMON_PID)
    from shared_apply_operation import SharedApplyOperation
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE, examine_shared
    from voice_ipfw_adapter import require_lifecycle_lock

    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    rec = store.read()
    need(type(rec) is dict and rec.get("phase") == "committed" and
         rec.get("manifest", {}).get("schema") == 2 and
         "found" not in rec and "failure" not in rec,
         "S10_AUTO_STOP_TERMINAL_SCHEMA2_REQUIRED")
    old = rec["detail"]
    state = examine_shared(rec)
    need(type(state) is dict and state.get("state") == "stopped" and
         state.get("source") == "native-common" and
         state.get("config_digest") == old["candidate"],
         "S10_AUTO_STOP_NATIVE_STATUS_UNVERIFIED")
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    need(gid > 0, "S10_AUTO_STOP_ENGINE_GID_REQUIRED")
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    receipts = EpochReceipts(owner_uid=0, writer_gid=gid)

    with queue.exclusive(existing_only=True):
        def attest():
            return attest_learning_stopped_generation()

        def inspect(path, device, inode, *, owner, writer_gid):
            return _probe_original_inode(
                path, device, inode, owner=owner, writer_gid=writer_gid,
                attest_owner=lambda: attest().owner == owner)

        def snapshot():
            require_lifecycle_lock()
            need(store.read() == rec, "S10_AUTO_STOP_JOURNAL_CHANGED")
            proof = attest()
            need(proof.operation_id == old["id"] and proof.generation == old["id"] and
                 proof.owner_candidate_sha256 == old["candidate"],
                 "S10_AUTO_STOP_HISTORICAL_OWNER_CHANGED")
            ready = receipts._generation(old["id"], create=False) / RETIRE_DIR / READY
            raw = _read(ready, 0)
            need(retired_learning_stopped(
                receipts, queue, proof, WORK / old["id"],
                attest=attest, inspect=inspect, repair=False),
                "S10_AUTO_STOP_ACK_ARCHIVE_INCOMPLETE")
            _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
            complete = (_full_prior_tree(WORK / old["id"], COMMON_ACTIVE, 0),
                        _empty_kernel(WORK / old["id"] / "release"),
                        _verify_idle_producer(queue, receipts),
                        hashlib.sha256(raw).hexdigest())
            need(_read(ready, 0) == raw and store.read() == rec and
                 attest() == proof, "S10_AUTO_STOP_READY_CHANGED")
            return complete

        before = snapshot()
        need(snapshot() == before, "S10_AUTO_STOP_COMPLETED_EPOCH_RACED")
    print("S10_RETIRED_AUTO_STOP=PASS_GENUINE_HTTPS_AUTO_ORIGINAL_SERVICE_STOP_ACK_ARCHIVE",
          flush=True)


def inspect_original_found():
    """Independent historical readback AFTER the genuine GUI successor."""
    import hashlib
    import pwd
    from auto_detect_epoch_receipts import EpochReceipts, _read
    from auto_detect_learning_retirement import RETIRE_DIR, READY
    from auto_detect_queue import DurableInbox
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from neutral_root_stage import verify_original_operation_pins, _verify_original_pinned_root
    from neutral_schema3_previous_physical import _full_prior_tree
    from neutral_schema3_quiescent_preimage import (
        _verify_retired_history, _verify_idle_producer, _zero_processes, _empty_kernel,
        CHILD_PID, MONITOR_PID, DAEMON_PID)
    from shared_apply_operation import SharedApplyOperation
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE, examine_shared
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    rec = store.read()
    need(type(rec) is dict and rec.get("phase") == "committed" and
         rec.get("manifest", {}).get("schema") == 1 and
         rec.get("previous_manifest", {}).get("schema") == 2 and
         "found" not in rec and "failure" not in rec,
         "S10_AUTO_FOUND_TERMINAL_BINDINGS_REQUIRED")
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
    with queue.exclusive(existing_only=True):
        prior, detail = rec["previous"], rec["detail"]
        ready = receipts._generation(prior["id"], create=False) / RETIRE_DIR / READY
        raw = _read(ready, 0)
        def observe():
            require_lifecycle_lock()
            verify_original_operation_pins(record=rec, parent=WORK, owner_uid=0)
            _verify_retired_history(rec, queue, receipts, hashlib.sha256(raw).hexdigest())
            root = json.loads(_verify_original_pinned_root(detail=detail,
                binding=rec["manifest"], parent=WORK, owner_uid=0))
            need(root["service"]["enabled"] is False and
                 root["service"]["target_mode"] == "list",
                 "S10_AUTO_FOUND_INERT_LIST_REQUIRED")
            state = examine_shared(rec)
            need(state.get("state") == "stopped" and state.get("source") == "native-common"
                 and state.get("config_digest") == detail["candidate"],
                 "S10_AUTO_FOUND_NATIVE_STOPPED_REQUIRED")
            _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
            result = (_full_prior_tree(WORK / detail["id"], COMMON_ACTIVE, 0),
                      _empty_kernel(WORK / detail["id"] / "release"),
                      _verify_idle_producer(queue, receipts))
            need(store.read() == rec and _read(ready, 0) == raw,
                 "S10_AUTO_FOUND_OWNER_OR_HISTORY_CHANGED")
            return result
        first = observe()
        need(observe() == first, "S10_AUTO_FOUND_TERMINAL_PROOF_RACED")
    print("S10_AUTO_FOUND_HISTORY=PASS_BOTH_ROOTS_ARCHIVE_ACK_STOPPED", flush=True)


def inspect_original_restored():
    """Independent proof of the actual old terminal owner after rollback."""
    import hashlib
    import pwd
    from auto_detect_epoch_receipts import EpochReceipts, _read
    from auto_detect_learning_retirement import RETIRE_DIR, READY
    from auto_detect_queue import DurableInbox
    from auto_detect_storage import ROOT as QUEUE_ROOT, ENGINE_USER
    from neutral_root_stage import verify_original_operation_pins
    from neutral_schema3_previous_physical import _full_prior_tree
    from neutral_schema3_quiescent_preimage import (
        _verify_retired_history, _verify_idle_producer, _zero_processes, _empty_kernel,
        CHILD_PID, MONITOR_PID, DAEMON_PID)
    from shared_apply_operation import SharedApplyOperation, committed_owner, committed_manifest
    from shared_apply_seal import WORK
    from voice_live_inspect import COMMON_ACTIVE, examine_shared
    from voice_ipfw_adapter import require_lifecycle_lock
    require_lifecycle_lock()
    store = SharedApplyOperation(owner=0)
    rec = store.read()
    need(type(rec) is dict and rec.get("phase") == "restored" and
         (rec.get("manifest") is None or rec["manifest"]["schema"] == 1) and
         committed_manifest(rec) == rec.get("previous_manifest") and
         rec["previous_manifest"]["schema"] == 2 and
         committed_owner(rec) == rec["previous"] and "found" not in rec,
         "S10_AUTO_FOUND_RESTORED_OWNER_REQUIRED")
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
    with queue.exclusive(existing_only=True):
        prior = rec["previous"]
        ready = receipts._generation(prior["id"], create=False) / RETIRE_DIR / READY
        raw = _read(ready, 0)
        def observe():
            require_lifecycle_lock()
            verify_original_operation_pins(record=rec, parent=WORK, owner_uid=0)
            _verify_retired_history(rec, queue, receipts, hashlib.sha256(raw).hexdigest())
            state = examine_shared(rec)
            need(state.get("state") == "stopped" and state.get("source") == "native-common" and
                 state.get("config_digest") == prior["candidate"],
                 "S10_AUTO_FOUND_RESTORED_STOPPED_REQUIRED")
            _zero_processes((CHILD_PID, MONITOR_PID, DAEMON_PID))
            result = (_full_prior_tree(WORK / prior["id"], COMMON_ACTIVE, 0),
                      _empty_kernel(WORK / prior["id"] / "release"),
                      _verify_idle_producer(queue, receipts))
            need(store.read() == rec and _read(ready, 0) == raw,
                 "S10_AUTO_FOUND_RESTORED_HISTORY_CHANGED")
            return result
        first = observe()
        need(observe() == first, "S10_AUTO_FOUND_RESTORED_PROOF_RACED")
    print("S10_AUTO_FOUND_RESTORED_HISTORY=PASS", flush=True)


def native_found_successor(web, voice, old, command):
    import hashlib
    import secrets
    import urllib.request
    import xml.etree.ElementTree as ET
    from pathlib import Path

    work = Path("/var/db/zapret2/shared-work")
    previous_root = work / old["detail"]["id"] / "manifest.json"
    old_root = previous_root.read_bytes()
    old_root_inode = previous_root.stat().st_ino
    epoch = Path("/var/db/zapret2/auto-detect-epochs") / old["detail"]["id"]
    def history():
        result = {}
        for path in sorted(epoch.rglob("*")):
            need(not path.is_symlink(), "S10_AUTO_FOUND_EPOCH_LINK")
            if path.is_file():
                info = path.stat()
                result[str(path.relative_to(epoch))] = (info.st_dev, info.st_ino,
                    hashlib.sha256(path.read_bytes()).hexdigest())
        need(bool(result), "S10_AUTO_FOUND_EPOCH_EMPTY")
        return result
    old_history = history()
    kernel = subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=False)
    need(kernel.returncode == 0, "S10_AUTO_FOUND_KERNEL_QUERY_REQUIRED")
    initial_config = CONFIG.read_bytes()
    snapshot = web.api("POST", "/api/zapret/settings/hostlistEditorsRead")
    saved = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(snapshot.get("result") == "ok" and type(saved) is dict and
         isinstance(saved.get("hostlist", {}).get("telegramips"), str),
         "S10_AUTO_FOUND_GUI_READ_REFUSED")
    names = {"youtube": "youtube_found", "user": "user_found", "auto": "shared_found"}
    drafts = {"youtube": "zapret-retired-youtube.org\n",
              "user": "zapret-retired-user.com\n", "auto": "zapret-retired-auto.net\n"}
    sources = {}
    for short, key in names.items():
        row = snapshot["editors"][key]
        sources[short] = {"base": {name: row[name] for name in ("status", "revision", "content")},
                          "draft": drafts[short]}
    payload = {"schema_version": 1, "kind": "tz6v2-found-form-intent",
               "config_revision": snapshot["config_revision"], "sources": sources}
    boundary = "zapret-" + secrets.token_hex(16)
    parts = []
    def part(name, value, upload=False):
        headers = ['Content-Disposition: form-data; name="' + name + '"']
        if upload:
            headers[0] += '; filename="found-intent.json"'
            headers.append("Content-Type: application/json")
        parts.extend([("--" + boundary).encode(), *(h.encode() for h in headers), b"", value])
    part("zapret[sync][telegramips_baseline]", saved["hostlist"]["telegramips"].encode())
    part("zapret[general][enabled]", b"0")
    part("zapret[hostlist][mode]", b"list")
    part("found_intent_expected", b"1")
    part("found_intent", json.dumps(payload, separators=(",", ":")).encode(), upload=True)
    parts.extend([("--" + boundary + "--").encode(), b""])
    request = urllib.request.Request(voice.ORIGIN + "/api/zapret/settings/apply",
        data=b"\r\n".join(parts), headers={
            "Content-Type": "multipart/form-data; boundary=" + boundary,
            "X-CSRFToken": web.csrf_token, "Accept": "application/json",
            "Referer": voice.ORIGIN + "/ui/zapret/general"}, method="POST")
    fault = os.environ.get("ZAPRET2_S10_FOUND_FAULT", "normal")
    retry = fault == "retry"
    if retry:
        fault = "presave"
    need(fault in ("normal", "saved-gap", "presave", "prepared-unbound", "prepared-bound"), "S10_AUTO_FOUND_FAULT_MODE_INVALID")
    paths = {"youtube": Path("/var/db/zapret2/auto-detect-owned/youtube.txt"),
             "user": Path("/var/db/zapret2/auto-detect-owned/user.txt"),
             "auto": Path("/usr/local/etc/zapret2/ipset/auto-domains.txt")}
    before_files = {name: path.read_bytes() if path.exists() else None
                    for name, path in paths.items()}
    service_bytes = SERVICE.read_bytes()
    php = SERVICE.with_name("shared_apply_config.php")
    php_bytes = php.read_bytes()
    backend = SERVICE.parent / "backend"
    fault_script = backend / ("auto_detect_effective_known.py" if fault == "prepared-unbound"
                              else "auto_detect_destination_commit.py")
    fault_bytes = fault_script.read_bytes()
    before_pins = {name: (path.stat().st_dev, path.stat().st_ino, path.stat().st_mtime_ns,
                          path.stat().st_ctime_ns) if path.exists() else None
                   for name, path in paths.items()}
    if fault.startswith("prepared-"):
        # Disposable only: stop after the existing PREPARED fsync, before
        # binding or after binding, without invoking the P1 writer.
        needle = (b"    return shared_apply_bound_found_files_original_fd9(" if fault == "prepared-unbound"
                  else b"        return _with_native_found_prepared_semantic(")
        need(fault_bytes.count(needle) == 1, "S10_AUTO_FOUND_PREPARED_FAULT_BOUNDARY_CHANGED")
        indent = b"    " if fault == "prepared-unbound" else b"        "
        fault_script.write_bytes(fault_bytes.replace(needle, indent +
            b'raise RuntimeError("disposable PREPARED fault")\n' + needle))
    if fault == "presave":
        # Actual P1 writer and durable READY handshake run unchanged.
        # Interrupt ONLY the original PHP callback before Config::save.
        # On this disposable VM the exact script is restored before recovery.
        needle = b"                                $status = $saveScope();"
        need(php_bytes.count(needle) == 1, "S10_AUTO_FOUND_PRESAVE_BOUNDARY_CHANGED")
        php.write_bytes(php_bytes.replace(needle,
            b"                                throw new \\RuntimeException('S10 disposable presave fault');\n" + needle))
    if fault == "saved-gap":
        # Disposable VM ONLY. Interrupt the original real saved boundary,
        # not a fabricated Config, WAL, receipt or P1 file.
        needle = b'    case "$_bound_route" in\n        bound-stopped-schema=1)\n            _bound_terminal='
        need(service_bytes.count(needle) == 1, "S10_AUTO_FOUND_FAULT_BOUNDARY_CHANGED")
        SERVICE.write_bytes(service_bytes.replace(needle, b"    return 70\n" + needle))
    try:
        with web.client.open(request, timeout=240) as response:
            reply = json.loads(response.read(2 * 1024 * 1024))
    finally:
        if fault == "saved-gap":
            SERVICE.write_bytes(service_bytes)
        if fault == "presave":
            php.write_bytes(php_bytes)
        if fault.startswith("prepared-"):
            fault_script.write_bytes(fault_bytes)
    rec = json.loads(WAL.read_bytes())
    if fault.startswith("prepared-"):
        import base64
        pending = rec
        new_root = work / pending["detail"]["id"] / "manifest.json"
        def pins():
            return {name: (path.stat().st_dev, path.stat().st_ino, path.stat().st_mtime_ns,
                           path.stat().st_ctime_ns) if path.exists() else None
                    for name, path in paths.items()}
        def root_pin():
            return (new_root.stat().st_ino, new_root.read_bytes()) if new_root.exists() else None
        candidate_pin = root_pin()
        need(fault_script.read_bytes() == fault_bytes and reply.get("result") != "saved" and
             pending["phase"] == "prepared" and pending["previous"] == old["detail"] and
             pending["previous_manifest"] == old["manifest"] and
             ("manifest" in pending) == (fault == "prepared-bound") and
             (candidate_pin is not None) == (fault == "prepared-bound") and
             pins() == before_pins and CONFIG.read_bytes() == initial_config and
             all((path.read_bytes() if path.exists() else None) == before_files[name]
                 for name, path in paths.items()), "S10_AUTO_FOUND_PREPARED_REAL_BOUNDARY_REQUIRED")
        print("S10_AUTO_FOUND_PREPARED_FAULT=PASS_" + fault.upper().replace("-", "_"), flush=True)
        work_before = set(work.iterdir())
        envelope = {"page": "strategies", "fields": {"general": {"enabled": "0"}},
                    "sync": {"telegramips_baseline": saved["hostlist"]["telegramips"]}}
        encoded = base64.urlsafe_b64encode(json.dumps(envelope, separators=(",", ":")).encode()).decode().rstrip("=")
        recovery = subprocess.run([str(SERVICE), "shared-apply-run", "strategies", encoded],
                                  capture_output=True, text=True, timeout=180, check=False)
        rec = json.loads(WAL.read_bytes())
        if recovery.returncode != 0:
            print("S10_AUTO_FOUND_PREPARED_RECOVERY_RC=" + str(recovery.returncode), flush=True)
        need(recovery.returncode == 0 and recovery.stdout.strip() == "apply-recovered=" + pending["detail"]["id"] and
             rec == {k: v for k, v in {**pending, "phase": "restored"}.items() if k != "found"} and
             set(work.iterdir()) == work_before and root_pin() == candidate_pin and
             pins() == before_pins and CONFIG.read_bytes() == initial_config and
             all((path.read_bytes() if path.exists() else None) == before_files[name]
                 for name, path in paths.items()) and
             previous_root.read_bytes() == old_root and previous_root.stat().st_ino == old_root_inode and
             history() == old_history and
             subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout == kernel.stdout and
             subprocess.run([str(SERVICE), "status"], capture_output=True, timeout=35).returncode == 1,
             "S10_AUTO_FOUND_PREPARED_PUBLIC_RECOVERY_REFUSED")
        proof = subprocess.run(["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
            str(Path(__file__).resolve()), "--inspect-restored"], capture_output=True, text=True,
            timeout=180, check=False)
        need(proof.returncode == 0 and "S10_AUTO_FOUND_RESTORED_HISTORY=PASS" in proof.stdout.splitlines(),
             "S10_AUTO_FOUND_PREPARED_INDEPENDENT_PROOF_REFUSED")
        print("S10_AUTO_FOUND_PREPARED=PASS_NO_P1_CONFIG_RUNTIME_WRITES_" +
              fault.upper().replace("-", "_"), flush=True)
        return
    if fault == "presave":
        import base64
        need(php.read_bytes() == php_bytes and reply.get("result") != "saved" and
             rec.get("phase") == "found-config-saving" and
             rec.get("previous") == old["detail"] and rec.get("previous_manifest") == old["manifest"] and
             rec.get("manifest", {}).get("schema") == 1 and
             rec["detail"]["base"] != rec["detail"]["candidate"] and
             CONFIG.read_bytes() == initial_config and
             all(paths[name].read_bytes() == drafts[name].encode() and
                 rec["found"]["stages"][name]["state"] == "installed"
                 for name in names),
             "S10_AUTO_FOUND_PRESAVE_REAL_P1_REQUIRED")
        pending = rec
        work_before = set(work.iterdir())
        new_root = work / pending["detail"]["id"] / "manifest.json"
        new_pin = (new_root.stat().st_ino, new_root.read_bytes())
        print("S10_AUTO_FOUND_PRESAVE=PASS_REAL_P1_WRITTEN_CONFIG_BASE", flush=True)
        # Exercise the existing native Apply dispatcher, with a valid
        # Strategies envelope. It must reconcile only the pending operation
        # BEFORE staging this next request. No synthetic journal or restore.
        envelope = {"page": "strategies", "fields": {"general": {"enabled": "0"}},
                    "sync": {"telegramips_baseline": saved["hostlist"]["telegramips"]}}
        encoded = base64.urlsafe_b64encode(json.dumps(envelope, separators=(",", ":")).encode()).decode().rstrip("=")
        recovery = subprocess.run([str(SERVICE), "shared-apply-run", "strategies", encoded],
                                  capture_output=True, text=True, timeout=180, check=False)
        rec = json.loads(WAL.read_bytes())
        if recovery.returncode != 0 or rec.get("phase") != "restored":
            print("S10_AUTO_FOUND_PRESAVE_PHASE=" + rec.get("phase", "unknown")
                  if rec.get("phase") in ("found-config-saving", "found-restoring", "restored") else
                  "S10_AUTO_FOUND_PRESAVE_PHASE=other", flush=True)
        need(recovery.returncode == 0 and
             recovery.stdout.strip() == "apply-recovered=" + pending["detail"]["id"] and
             rec == {k: v for k, v in {**pending, "phase": "restored"}.items() if k != "found"} and
             CONFIG.read_bytes() == initial_config and set(work.iterdir()) == work_before and
             (new_root.stat().st_ino, new_root.read_bytes()) == new_pin,
             "S10_AUTO_FOUND_PRESAVE_PUBLIC_ROLLBACK_REFUSED")
        after = web.api("POST", "/api/zapret/settings/hostlistEditorsRead")
        need(after.get("result") == "ok" and all(
            after["editors"][key]["content"] == snapshot["editors"][key]["content"] and
            (paths[name].read_bytes() if paths[name].exists() else None) == before_files[name]
            for name, key in names.items()), "S10_AUTO_FOUND_PRESAVE_THREE_BEFORE_IMAGES_REQUIRED")
        current_kernel = subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=False)
        need(previous_root.read_bytes() == old_root and previous_root.stat().st_ino == old_root_inode and
             history() == old_history and current_kernel.returncode == 0 and
             current_kernel.stdout == kernel.stdout and
             subprocess.run([str(SERVICE), "status"], capture_output=True,
                            timeout=35).returncode == 1,
             "S10_AUTO_FOUND_PRESAVE_OLD_OWNER_CHANGED")
        proof = subprocess.run(["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
            str(Path(__file__).resolve()), "--inspect-restored"], capture_output=True, text=True,
            timeout=180, check=False)
        need(proof.returncode == 0 and "S10_AUTO_FOUND_RESTORED_HISTORY=PASS" in proof.stdout.splitlines(),
             "S10_AUTO_FOUND_PRESAVE_INDEPENDENT_PROOF_REFUSED")
        print("S10_AUTO_FOUND_ROLLBACK=PASS_PUBLIC_APPLY_THREE_BEFORE_IMAGES_BASE_CONFIG_ACK_STOPPED",
              flush=True)
        if retry:
            # Fresh actual GUI editor read and multipart submission, not
            # replay of the old request or synthetic RESTORED journal.
            os.environ["ZAPRET2_S10_FOUND_FAULT"] = "normal"
            try:
                native_found_successor(web, voice, old, command)
            finally:
                os.environ["ZAPRET2_S10_FOUND_FAULT"] = "retry"
            terminal = json.loads(WAL.read_bytes())
            need(terminal["phase"] == "committed" and
                 terminal["previous"] == old["detail"] and
                 terminal["previous_manifest"] == old["manifest"] and
                 terminal["detail"]["id"] not in (old["detail"]["id"], pending["detail"]["id"]) and
                 (new_root.stat().st_ino, new_root.read_bytes()) == new_pin and
                 set(work.iterdir()) == work_before | {work / terminal["detail"]["id"]} and
                 history() == old_history,
                 "S10_AUTO_FOUND_RETRY_WRONG_OWNER_OR_ABANDONED_ROOT_CHANGED")
            print("S10_AUTO_FOUND_RETRY=PASS_REAL_HTTPS_NEW_WAL_OLD_OWNER_ABANDONED_ROOT_INTACT",
                  flush=True)
        return
    if fault == "saved-gap":
        need(SERVICE.read_bytes() == service_bytes and
             reply.get("result") != "saved" and rec.get("phase") == "found-config-saved" and
             rec.get("previous") == old["detail"] and rec.get("previous_manifest") == old["manifest"] and
             rec.get("manifest", {}).get("schema") == 1 and CONFIG.read_bytes() != initial_config,
             "S10_AUTO_FOUND_FAULT_SAVED_BOUNDARY_REQUIRED")
        pending = rec
        saved_bytes = CONFIG.read_bytes()
        work_before = set(work.iterdir())
        # Original atomic installer; disposable shadow of mv interrupts
        # precisely after the old active tree was parked.
        active = Path("/usr/local/etc/zapret2/runtime-v2")
        backups = active.with_name("runtime-v2-backups")
        source = r"""
set -eu
. /usr/local/opnsense/scripts/OPNsense/Zapret/backend/common.sh
. /usr/local/opnsense/scripts/OPNsense/Zapret/backend/atomic.sh
count=0
mv() {
    count=$((count+1))
    /bin/mv "$@" || return $?
    if [ "$count" -eq 1 ]; then exit 73; fi
}
atomic_install_tree "$1" "$2" "$3" "$4"
"""
        op = pending["detail"]["id"]
        gap = subprocess.run(["/bin/sh", "-c", command, "s10-gap-fd9", "/bin/sh", "-c",
            source, "s10-gap", str(work / op / "release"), str(active), str(backups), op],
            capture_output=True, timeout=120, check=False)
        need(gap.returncode == 73 and not active.exists() and
             (active.parent / ("." + active.name + ".stage." + op)).is_dir() and
             (active.parent / ("." + active.name + ".old." + op)).is_dir() and
             json.loads(WAL.read_bytes()) == pending and CONFIG.read_bytes() == saved_bytes,
             "S10_AUTO_FOUND_FAULT_ATOMIC_PARK_REQUIRED")
        print("S10_AUTO_FOUND_FAULT=PASS_REAL_CONFIG_SAVED_AND_OLD_TREE_PARKED", flush=True)
        recovery = subprocess.run([str(SERVICE), "start"], capture_output=True,
                                  timeout=180, check=False)
        rec = json.loads(WAL.read_bytes())
        if recovery.returncode != 0 or rec.get("phase") != "committed":
            label = rec.get("phase")
            print("S10_AUTO_FOUND_RECOVERY_PHASE=" + (label if label in (
                "found-config-saved", "committed", "found-restoring", "restored") else "other"), flush=True)
        need(recovery.returncode == 0 and rec == {k: v for k, v in
             {**pending, "phase": "committed"}.items() if k != "found"} and
             CONFIG.read_bytes() == saved_bytes and set(work.iterdir()) == work_before,
             "S10_AUTO_FOUND_PUBLIC_RECOVERY_REFUSED")
        print("S10_AUTO_FOUND_RECOVERY=PASS_PUBLIC_START_SAME_WAL_NO_CONFIG_RESAVE", flush=True)
    if fault == "normal" and (reply.get("result") != "saved" or reply.get("applied") is not True):
        phase = rec.get("phase")
        known = {"committed", "prepared", "found-files-writing", "found-files-written",
                 "found-config-saving", "found-config-saved", "restored", "requires-review"}
        print("S10_AUTO_FOUND_REFUSAL=" + (phase if phase in known else "OTHER").upper().replace("-", "_") +
              ":CONFIG_" + ("UNCHANGED" if CONFIG.read_bytes() == initial_config else "CHANGED") +
              ":REVIEW_" + ("YES" if reply.get("requires_review") is True else "NO"), flush=True)
        raise Refused("S10_AUTO_FOUND_REAL_HTTPS_REFUSED")
    need(rec.get("phase") == "committed" and rec.get("previous") == old["detail"] and
         rec.get("previous_manifest") == old["manifest"] and
         rec.get("manifest", {}).get("schema") == 1 and
         rec["detail"]["id"] != old["detail"]["id"] and
         rec["detail"]["base"] == old["detail"]["candidate"],
         "S10_AUTO_FOUND_NEW_OWNER_REQUIRED")
    after = web.api("POST", "/api/zapret/settings/hostlistEditorsRead")
    paths = {"youtube": Path("/var/db/zapret2/auto-detect-owned/youtube.txt"),
             "user": Path("/var/db/zapret2/auto-detect-owned/user.txt"),
             "auto": Path("/usr/local/etc/zapret2/ipset/auto-domains.txt")}
    need(after.get("result") == "ok" and all(
        after["editors"][key]["content"] == drafts[short] and
        paths[short].read_bytes() == drafts[short].encode()
        for short, key in names.items()), "S10_AUTO_FOUND_THREE_SOURCE_READBACK_FAILED")
    model = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    need(model is not None and model.findtext("general/enabled") == "0" and
         model.findtext("hostlist/mode") == "list" and CONFIG.read_bytes() != initial_config,
         "S10_AUTO_FOUND_CONFIG_READBACK_FAILED")
    need(previous_root.read_bytes() == old_root and previous_root.stat().st_ino == old_root_inode and
         history() == old_history, "S10_AUTO_FOUND_PREVIOUS_ROOT_OR_ARCHIVE_CHANGED")
    new_kernel = subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=False)
    need(new_kernel.returncode == 0 and new_kernel.stdout == kernel.stdout and
         subprocess.run([str(SERVICE), "status"], capture_output=True,
                        timeout=35).returncode == 1, "S10_AUTO_FOUND_KERNEL_OR_ENGINE_CHANGED")
    proof = subprocess.run(["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
        str(Path(__file__).resolve()), "--inspect-found"], capture_output=True, text=True,
        timeout=180, check=False)
    need(proof.returncode == 0 and "S10_AUTO_FOUND_HISTORY=PASS_BOTH_ROOTS_ARCHIVE_ACK_STOPPED"
         in proof.stdout.splitlines(), "S10_AUTO_FOUND_FINAL_INDEPENDENT_PROOF_REFUSED")
    print("S10_AUTO_NATIVE_FOUND=PASS_REAL_HTTPS_THREE_P1_CONFIG_ROOTS_ACK_STOPPED", flush=True)


def native_positive():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_S10_RETIRED_AUTO_DISPOSABLE") == "1" and
         sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         HEX40.fullmatch(os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")) is not None and
         ROOT.is_dir() and SERVICE.is_file() and CONFIG.is_file() and
         not WAL.exists(), "S10_AUTO_DISPOSABLE_CLEAN_GUEST_ONLY")
    # Use the previously accepted *real* first HTTPS Strategies Apply and
    # exact official Mk package, not an edited config.xml or fake first WAL.
    h = load("test-tz6v5-s03e3h-running-lab.py", "s10_running_h")
    g04 = h.module("stage2-opnsense-g04-native-runtime.py")
    voice = h.module("stage2-opnsense-real-native-voice-http.py")
    initial = g04.model()
    traffic = initial.findtext("strategy/trafficargs") or ""
    domains = initial.findtext("hostlist/youtubedomains") or ""
    need(initial.findtext("general/enabled") == "0" and
         not initial.findtext("general/waninterface") and
         traffic.count("--new") == 1 and domains.splitlines() == g04.YOUTUBE,
         "S10_AUTO_ORIGINAL_CLEAN_SEED_UNVERIFIED")
    before = CONFIG.read_bytes()
    g04.setup_upstream()
    need(CONFIG.read_bytes() == before and not WAL.exists(),
         "S10_AUTO_UPSTREAM_SETUP_MUTATED_CONFIG")
    # The GUI must create the *first* native owner as Auto. Changing an
    # already committed schema1 List owner to Auto would require the still
    # unaccepted public bound Apply/RUNNING transition, and tests must not
    # bypass its fence merely to manufacture a running epoch.
    web = voice.GuestHttps()
    voice.login(web)
    page = web.request("GET", "/ui/zapret")
    need("frm_GeneralSettings" in page and
         "/api/zapret/settings/apply" in page,
         "S10_AUTO_ORIGINAL_HTTPS_PAGE_UNAVAILABLE")
    saved = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(type(saved) is dict and type(saved.get("hostlist", {}).get("telegramips")) is str and
         type(saved.get("strategy", {}).get("trafficargs")) is str and
         g04.same_gui_multiline(saved["strategy"]["trafficargs"], traffic) and
         g04.same_gui_multiline(saved["hostlist"].get("youtubedomains"), domains),
         "S10_AUTO_HTTPS_FRESH_MODEL_UNQUALIFIED")
    # Auto mode builds learning clones only for the exact qualified known
    # <HOSTLIST:youtube>/<HOSTLIST:user> sources. The global optional
    # <HOSTLIST:auto> is separate and has no guaranteed initial file:
    # adding it here would fail the original targets resolver, not test
    # generation ownership. Preserve exactly the seeded profile bytes.
    first_auto = [("zapret[hostlist][mode]", "auto")]
    reject = web.api("POST", "/api/zapret/settings/apply",
                     g04.g04_http_form(saved, stale=True) + first_auto)
    need(reject.get("result") == "failed" and
         reject.get("requires_review") is not True and
         CONFIG.read_bytes() == before and not WAL.exists(),
         "S10_AUTO_FRESH_STALE_CAS_MUTATED")
    first_fault = os.environ.get("ZAPRET2_S10_FOUND_FAULT", "normal")
    first_fault = first_fault if first_fault in ("first-base", "first-saved") else None
    php = SERVICE.with_name("shared_apply_config.php")
    php_bytes = php.read_bytes()
    if first_fault == "first-base":
        # After original real ACTIVATED and both pins, before native Config save.
        needle = b"""                    return self::originalLockedFileEvidence(
                        $config, $id, $firstEnabled ? 'write-first-enabled-handoff-locked'
                            : 'write-first-disabled-handoff-locked', $digest, null, null, $queueStream)
                        === ['result'=>($firstEnabled ? 'first-enabled-activated'
                            : 'first-disabled-activated'), 'id'=>$id];"""
        replacement = needle.replace(b"return self::", b"$activated = self::", 1) + (
            b"\n                    if ($firstEnabled && $activated) { "
            b"throw new \\RuntimeException('S10 disposable first base fault'); }\n"
            b"                    return $activated;")
        need(php_bytes.count(needle) == 1, "S10_FIRST_FAULT_BASE_BOUNDARY_CHANGED")
        php.write_bytes(php_bytes.replace(needle, replacement))
    if first_fault == "first-saved":
        # Actual native Config::save returned, before the original confirm/epoch.
        needle = b"                if (($firstDisabled || $firstEnabled) && $mode === 'confirm-managed-config-save-locked') {"
        need(php_bytes.count(needle) == 1, "S10_FIRST_FAULT_SAVED_BOUNDARY_CHANGED")
        php.write_bytes(php_bytes.replace(needle, needle +
            b"\n                    if ($firstEnabled) { "
            b"throw new \\RuntimeException('S10 disposable first saved fault'); }"))
    try:
        result = web.api("POST", "/api/zapret/settings/apply",
                         g04.g04_http_form(saved) + first_auto)
    finally:
        if first_fault:
            php.write_bytes(php_bytes)
    if first_fault:
        import hashlib
        pending = json.loads(WAL.read_bytes())
        need(php.read_bytes() == php_bytes and result.get("result") != "saved" and
             pending["phase"] == "activated" and pending["manifest"]["schema"] == 2 and
             "previous" not in pending and "first_running_sha256" in pending and
             "first_pretraffic_sha256" in pending and
             (CONFIG.read_bytes() == before) == (first_fault == "first-base"),
             "S10_FIRST_REAL_CONFIG_FAULT_BOUNDARY_REQUIRED")
        op = pending["detail"]["id"]
        work = Path("/var/db/zapret2/shared-work")
        root = work / op / "manifest.json"
        root_pin = (root.stat().st_dev, root.stat().st_ino, root.read_bytes())
        epoch = Path("/var/db/zapret2/auto-detect-epochs") / op
        seed = epoch / "pretraffic.json"
        seed_bytes = seed.read_bytes()
        need(hashlib.sha256(seed_bytes).hexdigest() == pending["first_pretraffic_sha256"] and
             set(path.name for path in epoch.iterdir()) == {"pretraffic.json"},
             "S10_FIRST_FAULT_SEED_REQUIRED")
        original_seed = json.loads(seed_bytes)
        producer = Path("/var/db/zapret2/auto-detect")
        # Use the existing seed as the physical inventory; never print raw data.
        def images():
            output = {}
            for row in original_seed["files"]:
                path = producer / row["name"]
                st = path.stat()
                data = path.read_bytes()
                need(not path.is_symlink() and (st.st_dev, st.st_ino, st.st_nlink) ==
                     (row["device"], row["inode"], row["nlink"]),
                     "S10_FIRST_FAULT_PRODUCER_IDENTITY_CHANGED")
                output[row["name"]] = data
            return output
        # The actual producer directory is the source-map learning parent,
        # never a guessed alternate directory.
        producer = Path(original_seed["learning"][0]["path"]).parent
        before_images = images()
        def safe_lengths(data):
            return ("INBOX_" + str(len(data["inbox.txt"])) + ":DEBUG_" +
                    str(len(data["debug.log"])) + ":LEARNING_" +
                    str(sum(len(v) for k, v in data.items() if k not in ("inbox.txt", "debug.log"))))
        print("S10_FIRST_FAULT=PASS_ACTUAL_ACTIVATED_" + first_fault.upper().replace("-", "_") +
              ":" + safe_lengths(before_images), flush=True)
        config_image = CONFIG.read_bytes()
        work_before = set(work.iterdir())
        kernel = subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout
        if first_fault == "first-base":
            # Disposable guest only: inject one controlled nonzero fixture in each
            # original producer category and verify refusal before any Stop.
            # Never truncate anything other than our exact test-only sentinel.
            need(all(not data for data in before_images.values()),
                 "S10_AUTO_FIRST_BASE_ZERO_FIXTURE_REQUIRED")
            wan = SERVICE.with_name("wan_preflight.sh")
            for mode, expected_wan in (("require", b"wan-required"), ("if-start", b"wan-not-required")):
                observed_wan = subprocess.run([str(wan), mode], capture_output=True, timeout=30)
                need(observed_wan.returncode == 0 and observed_wan.stdout.strip() == expected_wan,
                     "S10_AUTO_FIRST_BASE_SAVED_WAN_FIXTURE_REQUIRED")
            print("S10_FIRST_BASE_WAN=PASS_REQUIRED_FOR_START_NOT_FOR_DISABLED_RECOVERY", flush=True)
            pidfiles = tuple(Path(name) for name in ("/var/run/dvtws2.pid",
                "/var/run/zapret2-supervisor-monitor.pid", "/var/run/zapret2-supervisor-daemon.pid"))
            def process_pins():
                rows = []
                for path in pidfiles:
                    pid = path.read_text().strip()
                    result = subprocess.run(["/bin/ps", "-ww", "-p", pid, "-o", "lstart=", "-o", "command="],
                                            capture_output=True, check=True)
                    rows.append((path.read_bytes(), path.stat().st_ino, result.stdout))
                return tuple(rows)
            live_pins = process_pins()
            learning = original_seed["learning"][0]["path"]
            for path in (producer / "inbox.txt", producer / "debug.log", Path(learning)):
                sentinel = b"s10-disposable-zero-cut-sentinel.invalid\n"
                with path.open("ab") as handle:
                    handle.write(sentinel)
                    handle.flush()
                    os.fsync(handle.fileno())
                expected = {**before_images, path.name: sentinel}
                refusal = subprocess.run([str(SERVICE), "start"], capture_output=True, timeout=180)
                print("S10_FIRST_BASE_NONZERO_RC=" + str(refusal.returncode), flush=True)
                need(refusal.returncode == 70 and json.loads(WAL.read_bytes()) == pending and
                     CONFIG.read_bytes() == config_image and set(work.iterdir()) == work_before and
                     (root.stat().st_dev, root.stat().st_ino, root.read_bytes()) == root_pin and
                     seed.read_bytes() == seed_bytes and images() == expected and
                     process_pins() == live_pins and
                     subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout == kernel,
                     "S10_AUTO_FIRST_BASE_NONZERO_MUTATED")
                # Restore the fixture, not production recovery. If any real bytes
                # appeared, refuse the fixture and keep them; no cleanup on failure.
                with path.open("r+b") as handle:
                    need(handle.read() == sentinel, "S10_AUTO_FIRST_BASE_FIXTURE_DRIFT")
                    handle.truncate(0)
                    handle.flush()
                    os.fsync(handle.fileno())
                need(images() == before_images, "S10_AUTO_FIRST_BASE_FIXTURE_RESTORE_FAILED")
            print("S10_FIRST_BASE_NONZERO=PASS_ALL_THREE_CATEGORIES_NO_STOP_OR_MUTATION", flush=True)
        # The first recovery dispatcher deliberately returns 69 even on a
        # terminal recovery: it must never fall through to a second Start.
        recovery = (first_base_recovery_diagnosed() if first_fault == "first-base" else
                    subprocess.run([str(SERVICE), "start"], capture_output=True, timeout=180))
        rec = json.loads(WAL.read_bytes())
        need(CONFIG.read_bytes() == config_image and set(work.iterdir()) == work_before and
             (root.stat().st_dev, root.stat().st_ino, root.read_bytes()) == root_pin and
             seed.read_bytes() == seed_bytes,
             "S10_FIRST_FAULT_RECOVERY_ORIGINAL_EVIDENCE_CHANGED")
        after_images = images()
        need(all(after_images[name].startswith(data) for name, data in before_images.items()),
             "S10_FIRST_FAULT_RECOVERY_PRODUCER_DATA_LOST")
        if first_fault == "first-base":
            print("S10_FIRST_BASE_RECOVERY_RC=" + str(recovery.returncode), flush=True)
            if rec.get("phase") in ("activated", "restored"):
                print("S10_FIRST_BASE_RECOVERY_PHASE=" + rec["phase"], flush=True)
            for line in recovery.stderr.split(b"\n")[:-1][:64]:
                if (re.fullmatch(rb"ERROR: shared Apply operation cannot advance: [A-Z0-9_]{1,96}", line) or
                        re.fullmatch(rb"S10_MANAGED_TRACE=(?:M(?:0[1-9]|1[0-4])|P0[1-3]):[1-9][0-9]{0,4}", line)):
                    print(line.decode("ascii"), flush=True)
            print("S10_FIRST_BASE_AFTER=" + safe_lengths(after_images) +
                  ":PIDFILES_" + str(sum(path.exists() for path in pidfiles)), flush=True)
            need(recovery.returncode == 69 and rec == {**pending, "phase": "restored"} and
                 all(not data for data in before_images.values()) and after_images == before_images and
                 set(path.name for path in epoch.iterdir()) == {"pretraffic.json"},
                 "S10_AUTO_FIRST_BASE_ROLLBACK_REQUIRED")
            # The original reversible rollback may change ONLY managed rules.
            def foreign_rules(raw):
                return [line for line in raw.splitlines()
                        if not 19000 <= int(line.split()[0]) <= 19099]
            after_kernel = subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout
            need(foreign_rules(after_kernel) == foreign_rules(kernel),
                 "S10_AUTO_FIRST_BASE_FOREIGN_IPFW_CHANGED")
            command = ('(/usr/bin/lockf -s -t 30 9 || exit 75; exec "$@") 9>' + LOCK)
            proof = subprocess.run(["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
                str(Path(__file__).resolve()), "--inspect-first-restored"],
                capture_output=True, text=True, timeout=180, check=False)
            need(proof.returncode == 0 and "S10_FIRST_BASE_INDEPENDENT=PASS" in proof.stdout.splitlines(),
                 "S10_AUTO_FIRST_BASE_INDEPENDENT_REFUSED")
            # A subsequent Start must not use the legacy executor or erase evidence.
            # This is a temporary fail-closed successor boundary, not a retry PASS.
            repeat = subprocess.run([str(SERVICE), "start"], capture_output=True, timeout=180)
            need(repeat.returncode != 0 and json.loads(WAL.read_bytes()) == rec and
                 CONFIG.read_bytes() == config_image and set(work.iterdir()) == work_before and
                 (root.stat().st_dev, root.stat().st_ino, root.read_bytes()) == root_pin and
                 seed.read_bytes() == seed_bytes and images() == before_images and
                 subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout == after_kernel,
                 "S10_AUTO_FIRST_BASE_REPEAT_MUTATED")
            proof = subprocess.run(["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
                str(Path(__file__).resolve()), "--inspect-first-restored"],
                capture_output=True, text=True, timeout=180, check=False)
            need(proof.returncode == 0 and "S10_FIRST_BASE_INDEPENDENT=PASS" in proof.stdout.splitlines(),
                 "S10_AUTO_FIRST_BASE_REPEAT_INDEPENDENT_REFUSED")
            print("S10_FIRST_BASE=PASS_ZERO_CUT_SAME_WAL_CONFIG_ROOT_SEED_STOPPED", flush=True)
            archive = Path("/var/db/zapret2/shared-aborted-first") / op
            old_lock = (producer / "worker.lock").stat()
            old_seed = seed.stat()
            wal_image = WAL.read_bytes()
            invoke_archive = ["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
                str(SERVICE.parent / "backend/shared_apply_operation.py"), "archive-first-restored", op]
            # A late nonzero byte must refuse before any historical move.
            debug = producer / "debug.log"
            sentinel = b"s10-disposable-archive-sentinel.invalid\n"
            with debug.open("ab") as handle:
                handle.write(sentinel)
                handle.flush()
                os.fsync(handle.fileno())
            refused = subprocess.run(invoke_archive, capture_output=True, timeout=240)
            need(refused.returncode != 0 and not archive.exists() and WAL.read_bytes() == wal_image and
                 root.read_bytes() == root_pin[2] and seed.read_bytes() == seed_bytes and
                 images() == {**before_images, "debug.log": sentinel} and CONFIG.read_bytes() == config_image,
                 "S10_FIRST_ARCHIVE_NONZERO_REFUSAL_REQUIRED")
            with debug.open("r+b") as handle:
                need(handle.read() == sentinel, "S10_FIRST_ARCHIVE_SENTINEL_CHANGED")
                handle.truncate(0)
                handle.flush()
                os.fsync(handle.fileno())
            print("S10_FIRST_ARCHIVE_NONZERO=PASS", flush=True)
            # The positive retry must start from the actual unarchived RESTORED
            # record. Do not call archive-first-restored successfully beforehand:
            # the original combined HTTPS Apply itself must archive and prepare.
            need(not archive.exists() and WAL.read_bytes() == wal_image and
                 CONFIG.read_bytes() == config_image and set(work.iterdir()) == work_before and
                 (root.stat().st_dev, root.stat().st_ino, root.read_bytes()) == root_pin and
                 seed.read_bytes() == seed_bytes and images() == before_images and
                 not any(path.exists() for path in pidfiles) and
                 subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout == after_kernel,
                 "S10_FIRST_RETRY_UNARCHIVED_PREIMAGE_REQUIRED")
            fresh = web.api("GET", "/api/zapret/settings/get").get("zapret")
            need(not archive.exists() and WAL.read_bytes() == wal_image and
                 CONFIG.read_bytes() == config_image and images() == before_images,
                 "S10_FIRST_RETRY_GET_MUTATED_PREIMAGE")
            print("S10_FIRST_RETRY=PASS_DIRECT_UNARCHIVED_RESTORED_PREIMAGE", flush=True)
            # Two distinct cuts of the actual original HTTPS retry, before
            # any physical activation: durable unbound and bound PREPARED.
            source_gate = BACKEND / "neutral_shared_apply_source_gate.py"
            source_bytes = source_gate.read_bytes()
            retired_ids = set()
            for cut, boundary in (
                ("UNBOUND", b"    route, result, actual, semantic = native_coordinate_original_prepared_fd9(operation, raw_pipe)\n"),
                ("BOUND", b"    semantic = native_plan_original_prepared_fd9(source)\n"
                          b"    if (type(source) is not SourceGateReceipt or type(semantic) is not OriginalSemanticReceipt or\n"),
            ):
                need(source_bytes.count(boundary) == 1, "S10_RETRY_PREPARED_CUT_BOUNDARY_CHANGED")
                injected = (b'    if "first_retry_archive" in store.read():\n'
                    b'        raise OriginalSourceGateRefused("S10_FIRST_RETRY_PREPARE_REFUSED")\n' + boundary)
                source_gate.write_bytes(source_bytes.replace(boundary, injected))
                try:
                    fault = web.api("POST", "/api/zapret/settings/apply",
                                    g04.g04_http_form(fresh) + first_auto)
                finally:
                    source_gate.write_bytes(source_bytes)
                pending_retry = json.loads(WAL.read_bytes())
                cut_id = pending_retry["detail"]["id"]
                candidate = work / cut_id
                need(fault.get("result") != "saved" and pending_retry["phase"] == "prepared" and
                     ("manifest" in pending_retry) == (cut == "BOUND") and
                     pending_retry.get("first_retry_archive") == {"id": op,
                         "sha256": hashlib.sha256((archive / "restored.json").read_bytes()).hexdigest()} and
                     cut_id != op and cut_id not in retired_ids and
                     CONFIG.read_bytes() == config_image and candidate.is_dir() and
                     not any(path.exists() for path in pidfiles),
                     "S10_RETRY_PREPARED_CUT_REQUIRED")
                retired_ids.add(cut_id)
                names = ["candidate.xml", "plan.json", "bundle-seal.json"]
                if cut == "BOUND":
                    names.append("manifest.json")
                def pinned(folder):
                    return tuple((name, (folder / name).stat().st_dev,
                                  (folder / name).stat().st_ino,
                                  (folder / name).read_bytes()) for name in names)
                before_cut = pinned(candidate)
                recovered = subprocess.run([str(SERVICE), "start"], capture_output=True, timeout=240)
                parked = archive.parent / cut_id / "work" / cut_id
                need(recovered.returncode == 69 and WAL.read_bytes() == wal_image and
                     CONFIG.read_bytes() == config_image and not candidate.exists() and
                     parked.is_dir() and pinned(parked) == before_cut and
                     not any(path.exists() for path in pidfiles) and
                     subprocess.run(["/sbin/ipfw", "list"], capture_output=True, check=True).stdout == after_kernel,
                     "S10_RETRY_PREPARED_RECOVERY_REQUIRED")
                print("S10_RETRY_PREPARED=PASS_REAL_HTTPS_" + cut + "_RECOVERY_ORIGINAL_WAL", flush=True)
                fresh = web.api("GET", "/api/zapret/settings/get").get("zapret")
                need(WAL.read_bytes() == wal_image and CONFIG.read_bytes() == config_image,
                     "S10_RETRY_PREPARED_GET_MUTATED")
            result = web.api("POST", "/api/zapret/settings/apply",
                             g04.g04_http_form(fresh) + first_auto)
            print("S10_FIRST_RETRY_HTTP=" + ("SAVED" if result.get("result") == "saved" else "REFUSED"), flush=True)
            new_root = archive / "work" / op / "manifest.json"
            new_seed = archive / "epoch/pretraffic.json"
            old_producer = producer
            producer = archive / "producer-parent/producer"
            def old_archive_intact():
                lock = (producer / "worker.lock").stat()
                ss = new_seed.stat()
                return ((new_root.stat().st_dev, new_root.stat().st_ino, new_root.read_bytes()) == root_pin and
                        (ss.st_dev, ss.st_ino) == (old_seed.st_dev, old_seed.st_ino) and
                        new_seed.read_bytes() == seed_bytes and images() == before_images and
                        (lock.st_dev, lock.st_ino) == (old_lock.st_dev, old_lock.st_ino) and
                        json.loads((archive / "restored.json").read_bytes()) == rec)
            if result.get("result") == "saved":
                retry_record = json.loads(WAL.read_bytes())
                retry_id = retry_record["detail"]["id"]
                retry_seed = epoch.parent / retry_id / "pretraffic.json"
                retry_lock = (old_producer / "worker.lock").stat()
                need(retry_record["phase"] == "committed" and retry_record["manifest"]["schema"] == 2 and
                     retry_id != op and "previous" not in retry_record and "previous_manifest" not in retry_record and
                     retry_record.get("first_retry_archive") == {"id": op,
                         "sha256": hashlib.sha256((archive / "restored.json").read_bytes()).hexdigest()} and
                     retry_record["detail"]["base"] == rec["detail"]["base"] and
                     hashlib.sha256(retry_seed.read_bytes()).hexdigest() == retry_record["first_pretraffic_sha256"] and
                     (retry_lock.st_dev, retry_lock.st_ino) != (old_lock.st_dev, old_lock.st_ino) and
                     not root.exists() and not seed.exists() and old_archive_intact(),
                     "S10_FIRST_RETRY_NEW_OWNER_REQUIRED")
                print("S10_FIRST_RETRY=PASS_HTTPS_AFTER_PREPARED_RECOVERY_NEW_COMMITTED_ARCHIVE_INTACT", flush=True)
        else:
            need(rec == {**pending, "phase": "committed"} and
                 (epoch / "epoch.json").is_file() and
                 subprocess.run([str(SERVICE), "status"], capture_output=True, timeout=35).returncode == 0,
                 "S10_FIRST_SAVED_PUBLIC_RECOVERY_REFUSED")
            print("S10_FIRST_SAVED=PASS_PUBLIC_START_SAME_WAL_CONFIG_ROOT_PRODUCER_RUNNING",
                  flush=True)
            # Confirm the recovered owner is usable by the original normal Stop
            # and independent ACK/archive attester below, not only by WAL readback.
            os.environ["ZAPRET2_S10_FOUND_FAULT"] = "normal"
    observed = g04.model()
    checks = {
        "HTTP_RESULT": first_fault == "first-saved" or result.get("result") == "saved",
        "HTTP_STATUS": first_fault == "first-saved" or result.get("status") == "ok",
        "HTTP_REVIEW": first_fault == "first-saved" or result.get("requires_review") is not True,
        "CONFIG_AUTO": observed.findtext("hostlist/mode") == "auto",
        "CONFIG_ENABLED": observed.findtext("general/enabled") == "1",
        "CONFIG_WAN": observed.findtext("general/waninterface") == "lo0",
        "CONFIG_STRATEGY": observed.findtext("strategy/trafficargs") == traffic,
        "CONFIG_DOMAINS": observed.findtext("hostlist/youtubedomains") == domains,
    }
    failed_first = [name for name, ok in checks.items() if not ok]
    if failed_first:
        # Print only bounded ownership facts from the real guest. A GUI
        # requires-review response is NOT sufficient to locate a failed
        # first apply; no raw journal, Config, argv or log data is printed.
        phase = "ABSENT"
        schema = "NONE"
        pins = "NONE"
        if WAL.is_file() and not WAL.is_symlink() and 0 < WAL.stat().st_size <= 8192:
            try:
                state = json.loads(WAL.read_bytes())
                if type(state) is dict:
                    phase = {name: name.upper().replace("-", "_") for name in (
                        "prepared", "activating", "activated", "config-saved",
                        "epoch-finalizing", "committed", "restored", "requires-review",
                        "restore-failed")}.get(state.get("phase"), "OTHER")
                    pin = state.get("manifest")
                    if type(pin) is dict and pin.get("schema") in (1, 2):
                        schema = str(pin["schema"])
                    have = ["RUNNING" if key == "first_running_sha256" else "PRETRAFFIC"
                            for key in ("first_running_sha256", "first_pretraffic_sha256")
                            if isinstance(state.get(key), str) and
                            re.fullmatch(r"[a-f0-9]{64}", state[key])]
                    pins = "_".join(have) or "NONE"
            except (ValueError, TypeError, OSError):
                phase = "UNREADABLE"
        print("S10_AUTO_FIRST_FAILURE_WAL=" + phase + ":SCHEMA_" + schema +
              ":PINS_" + pins + ":CONFIG_" +
              ("UNCHANGED" if CONFIG.read_bytes() == before else "CHANGED"), flush=True)
        # Existing execution-status channel contains a single bounded
        # source-owned gate code, not another journal or raw stderr.
        status = Path("/var/run/zapret2-execution.status")
        if status.is_file() and not status.is_symlink():
            info = status.stat()
            if info.st_uid == 0 and 0 < info.st_size <= 512:
                fields = status.read_text(errors="replace").strip().split("|", 5)
                if (len(fields) == 6 and fields[0].isdigit() and fields[1].isdigit()
                        and fields[2] == "source-gate" and fields[3] == "failed"):
                    # Codes must have been normalized by the production gate.
                    # Still restrict what can enter this disposable CI log.
                    fixed = {
                        "S10_BOUND_ENGINE_UNQUALIFIED", "S10_BOUND_ENGINE_CHANGED",
                        "S10_EFFECTIVE_SOURCE_UNQUALIFIED", "S10_FIRST_AUTO_GUI_SCOPE_REQUIRED",
                        "S10_FIRST_RETRY_PREPARE_REFUSED", "S10_FIRST_AUTO_GUI_OUTCOME_UNCERTAIN", "S10_FIRST_ENABLED_APPLY_SCOPE_REQUIRED",
                        "S10_FIRST_ENABLED_APPLY_PREIMAGE_CHANGED", "S10_FIRST_ENABLED_APPLY_OUTCOME_UNCERTAIN",
                        "S10_FIRST_LEARNING_SOURCE_CHANGED", "S10_FIRST_LEARNING_QUEUE_OWNER_CHANGED",
                        "S10_BOUND_PROMOTION_PRECHECK_REFUSED", "S10_PREPARED_DISPATCH_BIND_CHANGED",
                        "S10_PREPARED_DISPATCH_WITNESS_CHANGED", "S10_ORIGINAL_PREPARED_REQUIRED",
                        "ORIGINAL_TYPED_SEALED_SOURCE_REQUIRED", "ORIGINAL_PREPARED_SOURCE_IDENTITY_MISMATCH",
                        "ORIGINAL_AUTO_CANDIDATE_IDENTITY_MISMATCH", "ORIGINAL_PREPARED_SOURCE_ROOT_UNQUALIFIED",
                        "ORIGINAL_SCHEMA3_PHYSICAL_UNQUALIFIED", "ORIGINAL_SEALED_REFS_UNQUALIFIED",
                        "ORIGINAL_STAGE_FILESYSTEM_REFUSED", "STAGED_ROOT_UNQUALIFIED",
                        "ORIGINAL_BOUND_ROOT_UNQUALIFIED", "ORIGINAL_CONFIG_PREIMAGE_MISMATCH",
                        "NATIVE_ORIGINAL_PROBE_REFUSED", "NATIVE_ORIGINAL_PROBE_UNAVAILABLE",
                        "ORIGINAL_QUIESCENT_PREIMAGE_REFUSED", "FIRST_LEARNING_WAN_SOURCE_CHANGED",
                        "FIRST_LEARNING_WAN_RESOLVER_REFUSED", "ORIGINAL_EFFECTIVE_REFUSAL",
                        "ORIGINAL_VALUE_REFUSAL", "ORIGINAL_TYPE_REFUSAL", "ORIGINAL_SHARED_OPERATION_REFUSAL",
                        "ORIGINAL_BUNDLE_REFUSAL", "UNCLASSIFIED_PARITY_REFUSAL",
                    }
                    print("S10_AUTO_FIRST_GATE_REFUSAL=" +
                          (fields[5] if fields[5] in fixed else "OTHER_FIXED_CODE"), flush=True)
        # S10 G05 regression: the new sealed-schema3 pre-transaction fence
        # must NOT be misreported as a partially applied/reviewed owner.
        # Prove the official clean guest still has its exact Config bytes,
        # no original WAL, and no started native service. The positive
        # Auto->Stop->ACK scenario below remains REQUIRED, not silently
        # converted into success by this safety checkpoint.
        if result.get("reason") == "native-preflight-bound-auto-required":
            inactive = subprocess.run([str(SERVICE), "status"],
                                      capture_output=True, timeout=35)
            need(result.get("requires_review") is False and
                 CONFIG.read_bytes() == before and not WAL.exists() and
                 inactive.returncode == 1,
                 "S10_AUTO_UNBOUND_FENCE_NOT_INERT")
            print("S10_AUTO_UNBOUND_FENCE=PASS_NO_CONFIG_WAL_OR_SERVICE_ACTIVATION",
                  flush=True)
        # The original HTTPS API supplies a bounded *categorical* reason.
        # No message, request fields, native args, Config, user data or raw
        # stderr is exposed in the VM log. This classifier does not change
        # the requirement that ALL physical/Config conditions must pass.
        reason = result.get("reason")
        safe = {
            "native-preflight-root-gate": "NATIVE_ROOT_GATE",
            "native-preflight-bootstrap": "NATIVE_BOOTSTRAP",
            "native-preflight-model": "NATIVE_MODEL",
            "native-preflight-decode": "NATIVE_DECODE",
            "native-preflight-candidate": "NATIVE_CANDIDATE",
            "native-preflight-candidate-plan": "NATIVE_CANDIDATE_PLAN",
            "native-preflight-candidate-validation": "NATIVE_CANDIDATE_VALIDATION",
            "native-preflight-candidate-xml": "NATIVE_CANDIDATE_XML",
            "native-preflight-runtime-build": "NATIVE_RUNTIME_BUILD",
            "native-preflight-render": "NATIVE_RENDER",
            "native-preflight-seal": "NATIVE_SEAL",
            "native-preflight-config-preflight": "NATIVE_CONFIG_PREFLIGHT",
            "strategies-preflight-lifecycle-guard": "GUI_LIFECYCLE_GUARD",
            "strategies-preflight-model": "GUI_MODEL",
            "strategies-preflight-source-manifest": "GUI_SOURCE_MANIFEST",
            "strategies-preflight-normalization": "GUI_NORMALIZATION",
            "strategies-preflight-candidate-validation": "GUI_CANDIDATE_VALIDATION",
            "strategies-preflight-candidate-xml": "GUI_CANDIDATE_XML",
            "strategies-preflight-envelope": "GUI_ENVELOPE",
        }
        label = safe.get(reason, "OTHER_OR_NO_REASON") if isinstance(reason, str) else "OTHER_OR_NO_REASON"
        validation = result.get("validations")
        keys = {
            "zapret.strategy.trafficargs": "TRAFFICARGS",
            "zapret.hostlist.mode": "HOSTLIST_MODE",
            "zapret.general.enabled": "ENABLED",
            "zapret.general.waninterface": "WAN",
        }
        declared = [keys[key] for key in sorted(validation)
                    if key in keys] if isinstance(validation, dict) else []
        if declared:
            label += "_VALID_" + "_".join(declared[:2])
        if label == "OTHER_OR_NO_REASON":
            label += "_REVIEW" if result.get("requires_review") is True else "_NO_REVIEW"
        if label == "NATIVE_RUNTIME_BUILD":
            # Existing original orchestrator status, not the untrusted
            # stage-error/log text or request bytes. Whitelist *only*
            # source-defined phase and status tokens, no freeform fields.
            status = Path("/var/run/zapret2-execution.status")
            if status.is_file() and not status.is_symlink():
                stat = status.stat()
                if stat.st_uid == 0 and 0 <= stat.st_size <= 512:
                    fields = status.read_text(errors="replace").strip().split("|", 5)
                    stages = {
                        "config": "CONFIG", "parser": "PARSER",
                        "targets": "TARGETS", "blobs": "BLOBS",
                        "ports": "PORTS", "generator": "GENERATOR",
                        "validator": "VALIDATOR", "source-gate": "SOURCE_GATE",
                        "release-modes": "RELEASE_MODES",
                    }
                    if (len(fields) == 6 and fields[0].isdigit() and
                            fields[1].isdigit() and fields[2] in stages and
                            fields[3] in ("running", "ok", "failed")):
                        label += "_STAGE_" + stages[fields[2]] + "_" + fields[3].upper()
                        # Still only fixed, code-defined error words, never
                        # Config, selector, domains or path fragments.
                        patterns = {
                            "MISSING": ("does not exist", "not found", "missing"),
                            "EMPTY": ("empty", "no content"),
                            "INVALID": ("invalid", "unsupported", "unknown"),
                            "FILE": ("file", "readable", "regular"),
                            "MAP": ("source map", "source-map"),
                            "AUTO": ("auto", "hostlist-auto"),
                        }
                        reason = fields[5].lower()
                        tags = [k for k, words in patterns.items()
                                if any(v in reason for v in words)]
                        if tags:
                            label += "_CODE_" + "_".join(tags[:2])
        need(False, "S10_AUTO_FIRST_HTTPS_REASON_" + label)
    need(not failed_first, "S10_AUTO_FIRST_HTTPS_INVARIANT_DRIFT")
    old = json.loads(WAL.read_bytes())
    native_status = subprocess.run([str(SERVICE), "status"],
                                   capture_output=True, timeout=35)
    # Safe fixed-word failure labels; never print model, journal, PID,
    # kernel, native argv, uploaded domains or HTTP details.
    failed = [
        name for name, ok in (
            ("WAL_NONCOMMITTED", old.get("phase") == "committed"),
            ("WAL_NOSCHEMA2", old.get("manifest", {}).get("schema") == 2),
            ("ENGINE_NOT_READY", native_status.returncode == 0),
        ) if not ok
    ]
    if failed:
        # A non-schema2 first owner may be the result of the existing
        # *original* immutable bound dispatch, not a reason to fabricate
        # a second generation. Inspect its source-defined mode and map
        # presence only; never print any source file or digest.
        detail = old.get("detail", {}) if isinstance(old, dict) else {}
        ident = detail.get("id") if isinstance(detail, dict) else None
        work = Path("/var/db/zapret2/shared-work") / (
            ident if isinstance(ident, str) and HEX32.fullmatch(ident) else "invalid")
        root = work / "manifest.json"
        status = "NO_ROOT"
        if root.is_file() and not root.is_symlink() and root.stat().st_size <= 8192:
            doc = json.loads(root.read_bytes())
            mode = doc.get("service", {}).get("target_mode")
            if mode in ("auto", "all", "list"):
                status = "ROOT_" + mode.upper()
        markers = []
        for name, suffix in (
            ("auto-detect-source-map.json", "SOURCEMAP"),
            ("auto-detect-generation.json", "EPOCHMAP"),
            ("dvtws.original.args", "ORIGINALARGS")):
            file = work / "release" / name
            if file.is_file() and not file.is_symlink():
                markers.append(suffix)
        failed = failed[:3]
        label = "_".join(failed + [status] + markers)
        need(False, "S10_AUTO_REAL_" + label + "_REQUIRED")
    need(not failed, "S10_AUTO_REAL_NATIVE_INVARIANT_DRIFT")
    initial_config = CONFIG.read_bytes()
    stopped = subprocess.run([str(SERVICE), "stop"], capture_output=True,
                             timeout=180, check=False)
    need(stopped.returncode == 0 and
         subprocess.run([str(SERVICE), "status"], capture_output=True,
                        timeout=35).returncode == 1 and
         CONFIG.read_bytes() == initial_config and
         json.loads(WAL.read_bytes()) == old,
         "S10_AUTO_ORIGINAL_STOP_OR_CONFIG_WAL_DRIFT")
    # The independent original lock attester does not create/recover/ACK.
    command = (
        '(/usr/bin/lockf -s -t 30 9 || exit 75; exec "$@") '
        '9>' + LOCK)
    proof = subprocess.run(
        ["/bin/sh", "-c", command, "s10-original-fd9", PYTHON_RUNTIME,
         str(Path(__file__).resolve()), "--inspect-stopped"],
        capture_output=True, text=True, timeout=180, check=False)
    need(proof.returncode == 0 and
         "S10_RETIRED_AUTO_STOP=PASS_GENUINE_HTTPS_AUTO_ORIGINAL_SERVICE_STOP_ACK_ARCHIVE"
         in proof.stdout.splitlines(),
         "S10_AUTO_REAL_STOP_ACK_HISTORY_NOT_ATTESTED")
    print("S10_AUTO_NATIVE_STOP=PASS_REAL_HTTPS_SCHEMA3_NATIVE_STOP_TERMINAL_ACK",
          flush=True)
    if first_fault == "first-base":
        need(old_archive_intact(), "S10_FIRST_RETRY_ARCHIVE_CHANGED_AFTER_STOP")
        print("S10_FIRST_RETRY=PASS_NEW_OWNER_REAL_STOP_ACK_OLD_ARCHIVE_INTACT", flush=True)
        return
    if first_fault == "first-saved":
        print("S10_FIRST_SAVED=PASS_RECOVERED_OWNER_REAL_STOP_ACK_ARCHIVE", flush=True)
        return
    native_found_successor(web, voice, old, command)


def main():
    try:
        if sys.argv[1:] == ["--inspect-first-restored"]:
            need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
                 "S10_AUTO_NATIVE_INSPECT_SCOPE")
            sys.path.insert(0, str(BACKEND))
            inspect_first_restored()
            return 0
        if sys.argv[1:] == ["--inspect-restored"]:
            need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
                 "S10_AUTO_NATIVE_INSPECT_SCOPE")
            sys.path.insert(0, str(BACKEND))
            inspect_original_restored()
            return 0
        if sys.argv[1:] == ["--inspect-found"]:
            need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
                 "S10_AUTO_NATIVE_INSPECT_SCOPE")
            sys.path.insert(0, str(BACKEND))
            inspect_original_found()
            return 0
        if sys.argv[1:] == ["--inspect-stopped"]:
            need(sys.platform.startswith("freebsd") and os.geteuid() == 0,
                 "S10_AUTO_NATIVE_INSPECT_SCOPE")
            sys.path.insert(0, str(BACKEND))
            inspect_original_stopped()
            return 0
        need(sys.argv[1:] == ["run"], "S10_AUTO_INVALID_ARGS")
        native_positive()
        return 0
    except (Refused, OSError, RuntimeError, ValueError, KeyError, TypeError,
            subprocess.TimeoutExpired) as exc:
        # No raw native Config, domain, process argv, filesystem path or
        # untrusted child stderr may enter CI output.
        reason = str(exc)
        code = (reason if re.fullmatch(r"S10_AUTO_[A-Z0-9_]{1,100}", reason)
                else "S10_AUTO_NATIVE_UNCLASSIFIED_REFUSAL")
        print("S10_AUTO_NATIVE=REFUSED:" + code, file=sys.stderr, flush=True)
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
