#!/usr/bin/env python3
"""TZ6v4 disposable installed OPNsense schema3 canary: real FD9 service lifecycle.

NEVER run on the owner's firewall. This uses the physical official-Mk package
and actual pinned dvtws2, via the ordinary root shared-apply-run envelope and
operator Stop/Start/Restart commands. It does NOT simulate the process or
FD census, invent network discoveries, bypass Config, or write IPFW directly.

The CI-only opt-in is deliberately NOT a production feature. Refuse all other
platforms/contexts. This job does not qualify a power-loss recovery or ISP DPI.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
CONFIG = Path("/conf/config.xml")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
PID = Path("/var/run/dvtws2.pid")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
PRODUCERS = Path("/var/db/zapret2-auto-detect")
NEEDED_ENV = {
    "GITHUB_ACTIONS": "true",
    "ZAPRET2_NATIVE_BUILD_CI": "1",
    "ZAPRET2_STAGE2_SCHEMA3_DISPOSABLE_NATIVE": "1",
    "ZAPRET2_TZ6V4_SCHEMA3_NATIVE_TRIAL": "1",
}


class Refused(RuntimeError):
    pass


def require(test: bool, error: str) -> None:
    if not test:
        raise Refused(error)


def module(filename: str):
    spec = importlib.util.spec_from_file_location(
        "tz6v4_" + filename.replace(".", "_").replace("-", "_"),
        HERE / filename)
    require(spec is not None and spec.loader is not None, "CANARY_IMPORT_MISSING")
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def command(*args: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(list(args), capture_output=True, text=True,
                          timeout=timeout, check=False)


def envelope(fields: dict, baseline: str) -> str:
    require(isinstance(fields, dict) and isinstance(baseline, str),
            "CANARY_INVALID_NATIVE_REQUEST")
    raw = json.dumps({
        "page": "strategies", "fields": fields,
        "sync": {"telegramips_baseline": baseline},
    }, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    value = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    require(len(value) <= 65536 and re.fullmatch(r"[A-Za-z0-9_-]+", value),
            "CANARY_REQUEST_TOO_LARGE")
    return value


def self_test() -> None:
    encoded = envelope(
        {"general": {"waninterface": "lo0", "enabled": "1"},
         "hostlist": {"mode": "auto"}}, "")
    decoded = json.loads(base64.urlsafe_b64decode(
        encoded + "=" * (-len(encoded) % 4)))
    require(list(decoded) == ["page", "fields", "sync"] and
            decoded["page"] == "strategies" and
            decoded["fields"]["hostlist"]["mode"] == "auto" and
            decoded["sync"] == {"telegramips_baseline": ""},
            "CANARY_ENVELOPE_ROUNDTRIP_INVALID")
    print("TZ6V4_SCHEMA3_NATIVE_SOURCE=PASS")


def native_root() -> str:
    require(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
            Path("/usr/local/opnsense").is_dir() and
            all(os.environ.get(k) == v for k, v in NEEDED_ENV.items()) and
            os.environ.get("ZAPRET2_STAGE2_REAL_CLEAN_INSTALL") == "1" and
            os.environ.get("ZAPRET2_G04_DISPOSABLE_NATIVE") == "1" and
            os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1",
            "NOT_DISPOSABLE_OPNSENSE_SCHEMA3_NATIVE_TRIAL")
    sha = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None,
            "CANARY_EXACT_SOURCE_SHA_UNAVAILABLE")
    return sha


def check_process(expected_running: bool) -> int | None:
    status = command(str(SERVICE), "status", timeout=60)
    if expected_running:
        require(status.returncode == 0 and "zapret is running" in status.stdout,
                "CANARY_NATIVE_RUNNING_STATUS_REFUSED")
        require(PID.is_file() and not PID.is_symlink() and
                PID.read_text().strip().isdigit(),
                "CANARY_NATIVE_PID_MISSING")
        pid = int(PID.read_text().strip())
        require(pid > 1, "CANARY_PID_INVALID")
    else:
        require(status.returncode == 1 and
                "not running" in status.stdout and not PID.exists(),
                "CANARY_NATIVE_STOPPED_STATUS_REFUSED")
        pid = None
    ps = command("/bin/ps", "-ax", "-o", "pid=", "-o", "command=", timeout=15)
    require(ps.returncode == 0, "CANARY_GLOBAL_PROCESS_CENSUS_FAILED")
    actual = []
    for row in ps.stdout.splitlines():
        fields = row.strip().split(None, 1)
        if (len(fields) == 2 and fields[0].isdigit() and
                (fields[1] == str(ENGINE) or
                 fields[1].startswith(str(ENGINE) + " "))):
            actual.append(int(fields[0]))
    require(actual == ([pid] if expected_running else []),
            "CANARY_REAL_DVTWS2_OWNER_OR_CENSUS_CHANGED")
    return pid


def committed_id() -> str:
    require(JOURNAL.is_file() and not JOURNAL.is_symlink(),
            "CANARY_SHARED_APPLY_JOURNAL_MISSING")
    st = JOURNAL.lstat()
    require(st.st_uid == 0 and stat.S_IMODE(st.st_mode) == 0o600 and
            st.st_nlink == 1, "CANARY_UNTRUSTED_SHARED_JOURNAL")
    receipt = json.loads(JOURNAL.read_text())
    detail = receipt.get("detail")
    require(receipt.get("phase") == "committed" and
            isinstance(detail, dict) and detail.get("page") == "strategies" and
            isinstance(detail.get("id"), str) and
            re.fullmatch(r"[0-9a-f]{32}", detail["id"]),
            "CANARY_NOT_ORIGINAL_COMMITTED_SHARED_APPLY")
    return detail["id"]


def schema3_receipts(generation: str, pid: int) -> tuple[list[dict], int]:
    path = ACTIVE / "auto-detect-generation.json"
    require(path.is_file() and not path.is_symlink(),
            "CANARY_ACTIVE_NATIVE_SCHEMA3_MAP_MISSING")
    mapping = json.loads(path.read_text())
    learning = [x for x in mapping.get("profiles", [])
                if isinstance(x, dict) and x.get("role") == "learning"]
    require(mapping.get("schema") == 3 and mapping.get("generation") == generation and
            mapping.get("activation_authorized") is True and
            1 <= len(learning) <= 255 and
            all(x.get("auto_inbox") == str(
                PRODUCERS / ("learning-" + generation + "-" +
                             str(x.get("native_number")) + ".txt"))
                for x in learning),
            "CANARY_SCHEMA3_NATIVE_MAP_NOT_LEARNING")
    args = (ACTIVE / "dvtws.args").read_text()
    require(args.count("--hostlist-auto=") == len(learning) and
            "--hostlist-auto-debug=" in args and
            "--hostlist-auto=" in args and
            "--filter-tcp=" in args,
            "CANARY_NATIVE_LAUNCH_ARGV_NOT_MULTI_INBOX")
    receipt_dir = EPOCHS / generation
    pretraffic = json.loads((receipt_dir / "pretraffic.json").read_text())
    epoch = json.loads((receipt_dir / "epoch.json").read_text())
    require(pretraffic.get("schema") == 3 and
            epoch.get("schema") == 3 and epoch.get("owner_pid") == pid and
            epoch.get("generation") == generation and
            len(pretraffic.get("learning", [])) == len(learning) and
            len(pretraffic.get("files", [])) == 2 + len(learning),
            "CANARY_ORIGINAL_FD9_LIVE_SCHEMA3_EPOCH_NOT_SEALED")
    for row in learning:
        n = int(row["native_number"])
        f = PRODUCERS / ("learning-" + generation + "-" + str(n) + ".txt")
        require(f.is_file() and not f.is_symlink() and
                f.stat().st_nlink == 1, "CANARY_PRODUCER_NATIVE_N_MISSING")
    debug = PRODUCERS / "debug.log"
    require(debug.is_file() and debug.stat().st_nlink == 1,
            "CANARY_NATIVE_DEBUG_PRODUCER_MISSING")
    return learning, debug.stat().st_ino


def stopped_receipts(generation: str, learning: list[dict],
                     old_debug_inode: int) -> None:
    folder = EPOCHS / generation / "learning-retirement"
    require(folder.is_dir() and not folder.is_symlink(),
            "CANARY_TERMINAL_ARCHIVE_MISSING")
    intent = json.loads((folder / "intent.json").read_text())
    ready = json.loads((folder / "ready.json").read_text())
    require(intent.get("schema") == 3 and ready.get("schema") == 3 and
            intent.get("generation") == generation and
            ready.get("generation") == generation and
            ready.get("intent_sha256") == hashlib.sha256(
                (folder / "intent.json").read_bytes()).hexdigest(),
            "CANARY_STOPPED_TERMINAL_READY_NOT_ATTESTED")
    for row in learning:
        original = Path(row["auto_inbox"])
        archived = folder / ("old-" + original.name)
        require(not original.exists() and archived.is_file() and
                not archived.is_symlink() and archived.stat().st_nlink == 1,
                "CANARY_TERMINAL_N_INBOX_NOT_RETIRED")
    old_debug = folder / "old-debug.log"
    new_debug = PRODUCERS / "debug.log"
    require(old_debug.is_file() and new_debug.is_file() and
            old_debug.stat().st_ino == old_debug_inode and
            new_debug.stat().st_ino != old_debug_inode and
            new_debug.stat().st_size == 0,
            "CANARY_NATIVE_STOPPED_DEBUG_INODE_NOT_RETIRED")


def service_action(verb: str) -> None:
    require(verb in ("start", "stop", "restart"),
            "CANARY_UNTRUSTED_SERVICE_VERB")
    result = command(str(SERVICE), verb, timeout=180)
    require(result.returncode == 0,
            "CANARY_" + verb.upper() + "_REFUSED:rc=" +
            str(result.returncode) + ":" +
            (result.stdout + result.stderr)[-420:])


def execute() -> dict:
    head = native_root()
    g04 = module("stage2-opnsense-g04-native-config.py")
    # The SAME official-Mk physical archive, pkg installation and real
    # upstream v1.0.7 as ordinary G04/G07. No direct Config XML editing.
    g04.verify_native_pkg_and_first_config()
    require(ENGINE.is_file() and not ENGINE.is_symlink() and
            not JOURNAL.exists() and not PID.exists(),
            "CANARY_NOT_COLD_INSTALLED_NATIVE")
    before = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    require(before is not None and
            before.findtext("general/enabled") == "0" and
            (before.findtext("general/waninterface") or "") == "" and
            (before.findtext("hostlist/mode") or "all") == "all" and
            "<HOSTLIST:youtube>" in (before.findtext("strategy/trafficargs") or ""),
            "CANARY_DEFAULT_AUTO_LEARNABLE_PROFILE_MISSING")
    baseline_code = (
        "require_once('script/load_phalcon.php');"
        "$m=new \\OPNsense\\Zapret\\Zapret();"
        "$n=$m->getNodes();"
        "echo json_encode($n['hostlist']['telegramips']??null, JSON_THROW_ON_ERROR);"
    )
    baseline = command("/usr/local/bin/php", "-r", baseline_code, timeout=30)
    require(baseline.returncode == 0, "CANARY_NATIVE_PHP_MODEL_UNREADABLE")
    saved = json.loads(baseline.stdout)
    require(isinstance(saved, str), "CANARY_IPSET_GUI_BASELINE_INVALID")
    request = envelope(
        {"general": {"waninterface": "lo0", "enabled": "1"},
         "hostlist": {"mode": "auto"}}, saved)
    run = command(str(SERVICE), "shared-apply-run", "strategies", request,
                  timeout=420)
    require(run.returncode == 0 and
            re.search(r"(?m)^applied-id=[0-9a-f]{32}$", run.stdout),
            "CANARY_REAL_SHARED_APPLY_REFUSED:rc=" +
            str(run.returncode) + ":" + (run.stdout + run.stderr)[-700:])
    ident = committed_id()
    first_pid = check_process(True)
    require(first_pid is not None, "CANARY_START_PID_MISSING")
    learning, debug_inode = schema3_receipts(ident, first_pid)
    saved_root = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    require(saved_root is not None and
            saved_root.findtext("general/enabled") == "1" and
            saved_root.findtext("general/waninterface") == "lo0" and
            saved_root.findtext("hostlist/mode") == "auto",
            "CANARY_SCHEMA3_NATIVE_CONFIG_NOT_COMMITTED")

    # Operator-authorized Stop only, no SIGSTOP/SIGCONT, no second daemon.
    service_action("stop")
    check_process(False)
    stopped_receipts(ident, learning, debug_inode)
    require(committed_id() == ident, "CANARY_STOP_CHANGED_FD9_GENERATION")

    # The original Boot code deliberately creates a fresh operation/epoch
    # from the SAME persisted Config after terminal old-generation retirement.
    # Reusing a stopped PID/birth or the first generation ID would be unsafe.
    saved_model = ET.tostring(saved_root, encoding="utf-8")
    service_action("start")
    boot_pid = check_process(True)
    boot_id = committed_id()
    require(boot_pid is not None and boot_pid != first_pid and
            boot_id != ident and
            ET.tostring(ET.fromstring(CONFIG.read_bytes()).find(
                "./OPNsense/Zapret"), encoding="utf-8") == saved_model,
            "CANARY_BOOT_NEW_FD9_OWNER_DID_NOT_PRESERVE_SAVED_CONFIG")
    boot_learning, boot_debug_inode = schema3_receipts(boot_id, boot_pid)
    service_action("restart")
    restart_pid = check_process(True)
    restart_id = committed_id()
    require(restart_pid is not None and restart_pid != boot_pid and
            restart_id not in {ident, boot_id} and
            ET.tostring(ET.fromstring(CONFIG.read_bytes()).find(
                "./OPNsense/Zapret"), encoding="utf-8") == saved_model,
            "CANARY_RESTART_NEW_FD9_OWNER_DID_NOT_PRESERVE_SAVED_CONFIG")
    restart_learning, restart_debug_inode = schema3_receipts(
        restart_id, restart_pid)
    service_action("stop")
    check_process(False)
    stopped_receipts(restart_id, restart_learning, restart_debug_inode)
    require(committed_id() == restart_id,
            "CANARY_FINAL_STOP_LOST_LAST_SAVED_OWNER")
    return {
        "status": "PASS_TZ6V4_DISPOSABLE_REAL_SCHEMA3_APPLY_STOP_BOOT_RESTART",
        "source_sha": head, "initial_generation": ident,
        "boot_generation": boot_id, "restart_generation": restart_id,
        "real_engine_start_pid": first_pid,
        "real_engine_boot_pid": boot_pid,
        "real_engine_restart_pid": restart_pid,
        "native_learning_profiles": len(learning),
        "original_fd9_config_and_p2c_process": True,
        "terminal_n_debug_retirement": True,
        "new_epoch_on_boot_and_restart": True,
        "one_engine_at_each_active_checkpoint": True,
        "real_isp_positive_attribution_tested": False,
        "powerloss_recovery_tested": False,
        "owner_firewall_touched": False,
    }


def main() -> int:
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    if sys.argv[1:] != ["--native"]:
        print("TZ6V4_SCHEMA3_NATIVE=REFUSED_INVALID_COMMAND", file=sys.stderr)
        return 2
    try:
        record = execute()
    except (Refused, OSError, ValueError, KeyError, TypeError,
            ET.ParseError, subprocess.TimeoutExpired) as error:
        print("TZ6V4_SCHEMA3_NATIVE=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("TZ6V4_SCHEMA3_NATIVE=" + json.dumps(record, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
