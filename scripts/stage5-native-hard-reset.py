#!/usr/bin/env python3
"""Disposable OPNsense guest + Linux host: abrupt QEMU reset after real torn pkg.

TEST ONLY. Does not install a guard, change plugin hooks, repair pkgdb, or
touch the owner's router. 'system_reset' is a hard VM reset, NOT power loss.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
GUARD = Path("/var/db/zapret2/pkg-update/operation.json")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
CONFIG = Path("/conf/config.xml")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
RECEIPT = Path("/root/zapret2-native-hardreset-receipt.json")
NAME = "os-zapret2-restyle"
MARKER = b"\n<!-- VM-only native package extraction witness -->\n"


def need(condition, code):
    if not condition:
        raise RuntimeError(code)


def run(argv, timeout=35):
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout,
                          check=False)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def boot_seconds(text):
    match = re.search(r"\bsec\s*=\s*(\d+)", text)
    if not match:
        raise ValueError("BOOT_TIME_NOT_PARSEABLE")
    return int(match.group(1))


def guest_boot():
    p = run(["/sbin/sysctl", "-n", "kern.boottime"])
    need(p.returncode == 0, "NATIVE_BOOT_TIME_NOT_AVAILABLE")
    return boot_seconds(p.stdout)


def guest_gate():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_HARDRESET_TEST") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64", "NOT_DISPOSABLE_FREEBSD_GUEST")
    p = run(["opnsense-version", "-a"])
    need(p.returncode == 0 and p.stdout.strip().startswith("26.7"),
         "NATIVE_26_7_REQUIRED")


def trusted_regular(path, max_size=1024 * 1024):
    try:
        s = path.lstat()
    except OSError:
        return False
    return (stat.S_ISREG(s.st_mode) and s.st_uid == 0 and s.st_nlink == 1 and
            not (s.st_mode & 0o022) and s.st_size <= max_size)


def load_witnesses():
    spec = importlib.util.spec_from_file_location(
        "native_test_only_midextract", ROOT / "scripts" /
        "stage5-native-pkg-midextract.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.WITNESS_RELATIVE


def witness_inventory():
    out = {"restored": 0, "marked": 0, "missing": 0, "foreign": 0}
    for rel in load_witnesses():
        target = Path("/usr/local/opnsense") / rel
        source = ROOT / "src" / "opnsense" / rel
        need(source.is_file() and not source.is_symlink(),
             "SOURCE_WITNESS_UNTRUSTED")
        try:
            raw = target.read_bytes()
        except FileNotFoundError:
            out["missing"] += 1
            continue
        except OSError:
            out["foreign"] += 1
            continue
        original = source.read_bytes()
        if raw == original:
            out["restored"] += 1
        elif raw == original + MARKER:
            out["marked"] += 1
        else:
            out["foreign"] += 1
    return out


def version_archive():
    version = (ROOT / "VERSION").read_text().strip()
    match = re.search(r"(?m)^PLUGIN_REVISION=\s*(\d+)$",
                      (ROOT / "Makefile").read_text())
    need(bool(match), "REVISION_MISSING")
    return version + "_" + match.group(1), (
        ROOT / "dist" / (NAME + "-" + version + "_" + match.group(1) + ".pkg"))


def trusted_service():
    src = ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
    return (trusted_regular(SERVICE, 512 * 1024) and src.is_file() and
            not SERVICE.is_symlink() and digest(SERVICE) == digest(src))


def read_guard():
    need(trusted_regular(GUARD, 16 * 1024), "PROTECTED_GUARD_MISSING_OR_UNTRUSTED")
    record = json.loads(GUARD.read_text())
    need(record.get("schema") == 1 and record.get("phase") == "prepared",
         "PROTECTED_GUARD_NOT_PREPARED")
    return record


def read_receipt():
    need(trusted_regular(RECEIPT, 16 * 1024) and
         RECEIPT.stat().st_mode & 0o777 == 0o600,
         "ROOT_PRIVATE_RESET_RECEIPT_UNTRUSTED")
    data = json.loads(RECEIPT.read_text())
    need(data.get("schema") == 1 and data.get("test_guest_only") is True,
         "INVALID_RESET_RECEIPT")
    return data


def save_private_receipt(data):
    need(not RECEIPT.exists() and not RECEIPT.is_symlink(),
         "RECEIPT_ALREADY_EXISTS")
    fd = os.open(RECEIPT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write((json.dumps(data, sort_keys=True) + "\n").encode())
        f.flush()
        os.fsync(f.fileno())
    folder = os.open(RECEIPT.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(folder)
    finally:
        os.close(folder)



def guest_setup():
    """Minimal native AUTO owner to test exactly ONE genuinely torn pkg/reset.

    LIST and repeated successful upgrades have already qualified under _87.
    Their replay is not a prerequisite for the separate reset boundary.
    """
    guest_gate()
    need(not GUARD.exists() and not GUARD.is_symlink(),
         "BASELINE_UPDATE_GUARD_PRESENT")
    version, archive = version_archive()
    need(archive.is_file(), "EXACT_NATIVE_ARCHIVE_MISSING")
    native = load_test_only("stage5-native-protected-update.py",
                            "reset_reuse_native")
    witness = load_test_only("p5b2b-native-witness.py", "reset_native_wan")
    strategies = load_test_only("test-own70-native-package-handoff.py",
                                "reset_saved_config")
    g03 = load_test_only("stage2-opnsense-g03-first-install.py",
                         "reset_real_upstream_setup")
    initial = run(["/usr/sbin/pkg", "add", "-f", str(archive)], timeout=210)
    need(initial.returncode == 0 and trusted_service() and
         run([str(SERVICE), "status"]).returncode == 1,
         "REAL_NATIVE_PACKAGE_CLEAN_INSTALL_REFUSED")
    witness.set_guest_lo0()
    strategies.set_guest_list_mode()
    native.seed_qualified_stable_tag_for_disposable_guest(g03)
    try:
        setup = g03.dispatch_and_poll()
    except (g03.Refusal, OSError, subprocess.TimeoutExpired):
        g03.bounded_disposable_failure_evidence()
        raise
    need(setup["installed"] == "1" and setup["service"] == "stopped",
         "NATIVE_UPSTREAM_NOT_READY")
    applied = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                   "strategies", strategies.request("auto")], timeout=240)
    need(applied.returncode == 0 and "applied-id=" in applied.stdout and
         trusted_regular(JOURNAL, 128 * 1024),
         "NATIVE_AUTO_CONFIGD_APPLY_FAILED")
    before = json.loads(JOURNAL.read_text())
    old_id = before.get("detail", {}).get("id", "")
    need(before.get("phase") == "committed" and
         (EPOCHS / old_id / "epoch.json").is_file() and
         run([str(SERVICE), "status"]).returncode == 0,
         "NATIVE_AUTO_OWNER_NOT_RUNNING")
    print("NATIVE_HARDRESET_AUTO_OWNER=PASS_REAL_NATIVE_RUNNING", flush=True)
    try:
        native.native_partial_payload_interruption(
            archive, version, digest(archive))
    except RuntimeError:
        # No raw service logs, Config contents or user hostlist data.
        pending = GUARD.is_file() and not GUARD.is_symlink()
        print("NATIVE_HARDRESET_PRE_RESET_REFUSAL=" + json.dumps({
            "prepared_record_present": pending,
            "auto_epoch_retired": (EPOCHS / old_id / "retired.json").is_file(),
            "service_status_rc": run([str(SERVICE), "status"]).returncode,
            "owner_appliance_modified": False,
        }, sort_keys=True), flush=True)
        raise


def load_test_only(filename, module_name):
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def guest_prepare():
    guest_gate()
    version, archive = version_archive()
    need(trusted_service(), "SERVICE_NOT_TRUSTED_BEFORE_RESET")
    need(archive.is_file() and not archive.is_symlink(),
         "EXACT_NATIVE_ARCHIVE_MISSING")
    record = read_guard()
    need(trusted_regular(CONFIG, 4 * 1024 * 1024) and
         trusted_regular(JOURNAL, 128 * 1024),
         "CONFIG_OR_JOURNAL_UNTRUSTED")
    current = json.loads(JOURNAL.read_text())
    epoch = current.get("detail", {}).get("id")
    need(current.get("phase") == "committed" and
         isinstance(epoch, str) and re.fullmatch(r"[a-f0-9]{32}", epoch) and
         (EPOCHS / epoch / "retired.json").is_file(),
         "ORIGINAL_AUTO_EPOCH_NOT_RETIRED")
    observed = witness_inventory()
    need(observed["restored"] > 0 and
         observed["marked"] + observed["missing"] > 0 and
         observed["foreign"] == 0, "NO_REAL_TORN_PAYLOAD")
    need(run([str(SERVICE), "status"]).returncode == 1,
         "SERVICE_NOT_STOPPED_BEFORE_RESET")
    data = {
        "schema": 1, "test_guest_only": True,
        "version": version, "archive_sha256": digest(archive),
        "config_sha256": digest(CONFIG), "guard_sha256": digest(GUARD),
        "original_epoch_id": epoch, "boot_seconds": guest_boot(),
        "witnesses_before": observed,
    }
    save_private_receipt(data)
    print("NATIVE_HARDRESET_PREPARED=" + json.dumps({
        "real_partial_payload": observed, "original_auto_retired": True,
        "service_stopped": True, "guard_phase": "prepared",
        "owner_appliance_modified": False}, sort_keys=True), flush=True)


def guest_verify():
    guest_gate()
    receipt = read_receipt()
    boot = guest_boot()
    need(boot > receipt["boot_seconds"], "HARD_RESET_BOOT_ID_UNCHANGED")
    need(trusted_regular(CONFIG, 4 * 1024 * 1024) and
         digest(CONFIG) == receipt["config_sha256"],
         "CONFIG_CHANGED_ACROSS_RESET")
    record = read_guard()
    need(digest(GUARD) == receipt["guard_sha256"],
         "PREPARED_GUARD_CHANGED_ACROSS_RESET")
    epoch = receipt["original_epoch_id"]
    need((EPOCHS / epoch / "retired.json").is_file(),
         "OLD_AUTO_RETIREMENT_LOST_ON_RESET")
    version, archive = version_archive()
    need(version == receipt["version"] and archive.is_file() and
         digest(archive) == receipt["archive_sha256"],
         "STAGED_ARCHIVE_CHANGED_ON_RESET")
    observed = witness_inventory()
    need(observed["foreign"] == 0 and
         observed["restored"] + observed["marked"] + observed["missing"] ==
             len(load_witnesses()),
         "UNCLASSIFIED_PAYLOAD_AFTER_RESET")
    # This checks the actual live process table after OPNsense boot. A
    # stale pidfile, pkgdb version or service status alone is not evidence.
    ps = run(["/bin/ps", "-axo", "comm="])
    need(ps.returncode == 0 and
         not any(x.strip() == "dvtws2" for x in ps.stdout.splitlines()),
         "DVTWS2_AUTO_STARTED_AFTER_RESET")
    need(trusted_service(), "INSTALLED_SERVICE_MISSING_OR_UNTRUSTED_AFTER_RESET")
    denied = {
        "status": run([str(SERVICE), "status"]).returncode,
        "start": run([str(SERVICE), "start"]).returncode,
        "apply": run([str(SERVICE), "shared-apply-run"]).returncode,
        "repeat": run([str(SERVICE), "pkg-update", str(archive)]).returncode,
        "finish": run([str(SERVICE), "pkg-update-finish",
                       receipt["archive_sha256"], receipt["version"]]).returncode,
    }
    need(denied["status"] == 1 and
         all(denied[x] == 69 for x in ("start", "apply", "repeat", "finish")),
         "MUTATING_ACTION_NOT_REFUSED_AFTER_RESET")
    need(digest(GUARD) == receipt["guard_sha256"] and
         digest(CONFIG) == receipt["config_sha256"],
         "GUARD_OR_CONFIG_CHANGED_DURING_REFUSALS")
    pkg = run(["/usr/sbin/pkg", "query", "%v", NAME], timeout=15)
    print("NATIVE_HARDRESET_POSTBOOT=" + json.dumps({
        "boot_changed": True, "config_unchanged": True,
        "guard_phase": record["phase"], "guard_digest_unchanged": True,
        "original_auto_retired": True, "dvtws2_process_count": 0,
        "service_status_rc": denied["status"], "mutating_actions_refused": True,
        "physical_payload_classification": observed,
        "pkgdb_query_rc": pkg.returncode,
        "pkgdb_version_matches_candidate":
            pkg.returncode == 0 and pkg.stdout.strip() == version,
        "service_source_trusted": True,
        "owner_appliance_modified": False,
        "power_loss_tested": False,
        "automatic_repair_attempted": False,
    }, sort_keys=True), flush=True)
    print("NATIVE_HARDRESET_POSTBOOT=PASS_GUARDED_STOPPED_AFTER_QEMU_RESET",
          flush=True)


def qemu_candidates(proc_root=Path("/proc")):
    """Require exactly one ephemeral snapshot VM with a loopback HMP monitor."""
    matches = []
    for entry in proc_root.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            argv = (entry / "cmdline").read_bytes().split(b"\0")
            argv = [a.decode("utf-8") for a in argv if a]
        except (OSError, UnicodeError):
            continue
        if not argv or Path(argv[0]).name != "qemu-system-x86_64":
            continue
        if ("-snapshot" not in argv or "-monitor" not in argv or
                not any("opnsense" in a.lower() for a in argv)):
            continue
        ix = argv.index("-monitor")
        if ix + 1 >= len(argv):
            continue
        spec = argv[ix + 1]
        found = re.fullmatch(
            r"tcp:127\.0\.0\.1:(\d+),server,nowait,nodelay", spec)
        if found:
            port = int(found.group(1))
            if 1024 <= port <= 65535:
                matches.append((int(entry.name), port))
    return matches


def ssh_boot():
    p = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
             "opnsense", "/sbin/sysctl -n kern.boottime"], timeout=12)
    if p.returncode:
        return None
    try:
        return boot_seconds(p.stdout)
    except ValueError:
        return None


def monitor_command(port, command):
    with socket.create_connection(("127.0.0.1", port), timeout=5) as conn:
        conn.settimeout(1.5)
        try:
            banner = conn.recv(4096)
        except socket.timeout:
            banner = b""
        conn.sendall((command + "\n").encode("ascii"))
        out = [banner]
        while True:
            try:
                chunk = conn.recv(4096)
                if not chunk:
                    break
                out.append(chunk)
            except socket.timeout:
                break
        return b"".join(out).decode("utf-8", errors="replace")


def host_hard_reset():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_HARDRESET_HOST") == "1" and
         os.uname().sysname == "Linux",
         "NOT_DISPOSABLE_GITHUB_VM_HOST")
    targets = qemu_candidates()
    need(len(targets) == 1, "NOT_EXACTLY_ONE_SNAPSHOT_QEMU_OPNSENSE")
    pid, port = targets[0]
    before = ssh_boot()
    need(isinstance(before, int), "GUEST_UNREACHABLE_BEFORE_RESET")
    status = monitor_command(port, "info status")
    need(bool(re.search(r"\bVM status:\s*running\b", status, flags=re.I)) and
         "Error" not in status,
         "QEMU_MONITOR_NOT_RUNNING")
    reset = monitor_command(port, "system_reset")
    need("Error" not in reset, "QEMU_SYSTEM_RESET_REFUSED")
    deadline = time.monotonic() + 240
    after = None
    while time.monotonic() < deadline:
        need(Path("/proc").joinpath(str(pid), "cmdline").is_file(),
             "QEMU_PROCESS_DISAPPEARED_AFTER_RESET")
        after = ssh_boot()
        if isinstance(after, int) and after > before:
            break
        time.sleep(3)
    need(isinstance(after, int) and after > before,
         "HARD_RESET_BOOT_NOT_OBSERVED")
    print("NATIVE_QEMU_SYSTEM_RESET=" + json.dumps({
        "same_qemu_process": True, "new_kernel_boot": True,
        "snapshot_disk_retained_in_vm": True, "graceful_guest_shutdown": False,
        "full_host_power_loss": False,
        "owner_appliance_modified": False,
    }, sort_keys=True), flush=True)


def main():
    need(len(sys.argv) == 2, "EXPECTED_SETUP_PREPARE_VERIFY_OR_HOST_RESET")
    if sys.argv[1] == "setup":
        guest_setup()
    elif sys.argv[1] == "prepare":
        guest_prepare()
    elif sys.argv[1] == "verify":
        guest_verify()
    elif sys.argv[1] == "host-reset":
        host_hard_reset()
    else:
        raise RuntimeError("UNKNOWN_NATIVE_RESET_PHASE")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError,
            subprocess.TimeoutExpired) as e:
        print("NATIVE_HARDRESET=REFUSED:" + str(e), file=sys.stderr)
        sys.exit(1)
