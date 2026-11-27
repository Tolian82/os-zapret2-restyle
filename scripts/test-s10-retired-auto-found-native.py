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
    g04.authenticated_first_apply(traffic, domains)
    web = voice.GuestHttps()
    voice.login(web)
    saved = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(type(saved) is dict and type(saved.get("hostlist", {}).get("telegramips")) is str,
         "S10_AUTO_HTTPS_SAVED_MODEL_UNQUALIFIED")
    result = web.api("POST", "/api/zapret/settings/apply", [
        ("zapret[sync][telegramips_baseline]", saved["hostlist"]["telegramips"]),
        ("zapret[hostlist][mode]", "auto")])
    need(result.get("result") == "saved" and result.get("status") == "ok" and
         result.get("requires_review") is not True and
         g04.model().findtext("hostlist/mode") == "auto",
         "S10_AUTO_REAL_HTTPS_STRATEGIES_MODE_NOT_COMMITTED")
    old = json.loads(WAL.read_bytes())
    need(old.get("phase") == "committed" and
         old.get("manifest", {}).get("schema") == 2 and
         subprocess.run([str(SERVICE), "status"], capture_output=True,
                        timeout=35).returncode == 0,
         "S10_AUTO_REAL_SCHEMA2_RUNNING_REQUIRED")
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


def main():
    try:
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
