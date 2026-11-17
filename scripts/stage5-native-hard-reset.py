#!/usr/bin/env python3
"""Disposable OPNsense guest + Linux host: abrupt QEMU reset after real torn pkg.

TEST ONLY. Does not install a guard, change plugin hooks, repair pkgdb, or
touch the owner's router. 'system_reset' is a hard VM reset, NOT power loss.
"""
import fcntl
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
import xml.etree.ElementTree as ET

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


def opnsense_config_readable():
    """Read-only Config input; OPNsense itself owns its inode/ACL lifecycle.

    The original installed Model/Config and shared FD9 have already validated
    and committed this exact Config. No new independent Config ownership rule.
    """
    try:
        st = CONFIG.lstat()
    except OSError:
        return False
    return stat.S_ISREG(st.st_mode) and st.st_size <= 32 * 1024 * 1024


def stable_xml_value(node):
    """Compare saved XML values, ignoring XML formatting-only indentation.

    Leaf text (including any whitespace in user profiles) is preserved exactly.
    Only whitespace between child elements is ignored; child order, attributes,
    tags, and all actual leaf values are significant.
    """
    children = list(node)
    text = node.text or ""
    if children and not text.strip():
        text = ""
    return [node.tag, sorted(node.attrib.items()), text,
            [[stable_xml_value(child),
              child.tail if child.tail and child.tail.strip() else ""]
             for child in children]]


def config_snapshot():
    """Read only original OPNsense Config and hash saved plugin/WAN semantics."""
    need(opnsense_config_readable(), "CONFIG_NOT_READABLE")
    root = ET.fromstring(CONFIG.read_bytes())
    need(root.tag == "opnsense", "NATIVE_CONFIG_ROOT_UNKNOWN")
    plugin = root.find("./OPNsense/Zapret")
    interfaces = root.find("./interfaces")
    need(plugin is not None and interfaces is not None,
         "SAVED_PLUGIN_OR_INTERFACES_MISSING")
    def fingerprint(node):
        encoded = json.dumps(stable_xml_value(node), ensure_ascii=True,
                             separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
    return {
        "full": digest(CONFIG),
        "plugin": fingerprint(plugin),
        "interfaces": fingerprint(interfaces),
        "plugin_diagnostic_paths": plugin_diagnostic_paths(plugin),
    }




def plugin_diagnostic_paths(plugin):
    """VM-only, value-free fingerprints of bounded named plugin paths.

    Safety remains the complete semantic fingerprint; this diagnostic cannot
    authorize any field change. Only structural names, never values, print.
    """
    result = {}
    def descend(node, path, depth):
        need(len(result) < 300, "PLUGIN_DIAGNOSTIC_TOO_MANY_FIELDS")
        encoded = json.dumps(stable_xml_value(node), ensure_ascii=True,
                             separators=(",", ":")).encode("utf-8")
        result[path] = hashlib.sha256(encoded).hexdigest()[:24]
        if depth >= 4:
            return
        counters = {}
        for child in list(node):
            number = counters.get(child.tag, 0)
            counters[child.tag] = number + 1
            descend(child, path + "/" + child.tag + "[" + str(number) + "]",
                    depth + 1)
    descend(plugin, "Zapret", 0)
    return result


def diagnostic_changed_paths(before, after):
    """Return only deepest changed XML path labels; never return node data."""
    changed = {key for key in before.keys() | after.keys()
               if before.get(key) != after.get(key)}
    deepest = [key for key in changed
               if not any(other.startswith(key + "/") for other in changed)]
    return sorted(deepest)


def config_structure():
    """Read-only persisted native XML classification; never print values."""
    evidence = {
        "config_regular": opnsense_config_readable(),
        "valid_xml": False,
        "opnsense_container_present": False,
        "zapret_section_present": False,
        "interfaces_section_present": False,
    }
    if not evidence["config_regular"]:
        return evidence
    try:
        root = ET.fromstring(CONFIG.read_bytes())
    except (OSError, ET.ParseError):
        return evidence
    evidence["valid_xml"] = root.tag == "opnsense"
    if not evidence["valid_xml"]:
        return evidence
    evidence["opnsense_container_present"] = (
        root.find("./OPNsense") is not None)
    evidence["zapret_section_present"] = (
        root.find("./OPNsense/Zapret") is not None)
    evidence["interfaces_section_present"] = (
        root.find("./interfaces") is not None)
    return evidence


def postboot_readonly_classification(receipt):
    """Independent physical evidence before any lifecycle command."""
    config = config_structure()
    config["raw_bytes_preserved"] = (
        config["config_regular"] and
        digest(CONFIG) == receipt["config_sha256"])
    try:
        record = read_guard()
        valid_record = True
    except (RuntimeError, OSError, ValueError, json.JSONDecodeError):
        record = None
        valid_record = False
    guard_equal = valid_record and digest(GUARD) == receipt["guard_sha256"]
    staged_guarded = False
    if valid_record and guard_equal:
        staged_path = Path(record.get("stage", ""))
        staged_guarded = (
            staged_path.parent == GUARD.parent and
            staged_path.name.startswith("incoming-") and
            staged_path.suffix == ".pkg" and
            trusted_regular(staged_path, 256 * 1024 * 1024) and
            digest(staged_path) == receipt["archive_sha256"] and
            record.get("sha256") == receipt["archive_sha256"])
    epoch = receipt["original_epoch_id"]
    retired = (EPOCHS / epoch / "retired.json").is_file()
    process = run(["/bin/ps", "-axo", "comm="])
    process_readable = process.returncode == 0
    dvtws2_absent = process_readable and not any(
        line.strip() == "dvtws2" for line in process.stdout.splitlines())
    version, archive = version_archive()
    staged = (version == receipt["version"] and archive.is_file() and
              not archive.is_symlink() and
              digest(archive) == receipt["archive_sha256"])
    pkg = run(["/usr/sbin/pkg", "query", "%v", NAME], timeout=15)
    report = {
        **config,
        "prepared_guard_present_unchanged": guard_equal,
        "guard_private_staged_package_unchanged": staged_guarded,
        "old_auto_retired": retired,
        "process_table_available": process_readable,
        "dvtws2_absent": dvtws2_absent,
        "installed_service_source_trusted": trusted_service(),
        "candidate_archive_unchanged": staged,
        "pkgdb_query_rc": pkg.returncode,
        "pkgdb_version_matches_candidate":
            pkg.returncode == 0 and pkg.stdout.strip() == version,
        "owner_appliance_modified": False,
        "postboot_mutation_attempted": False,
    }
    print("NATIVE_HARDRESET_POSTBOOT_READONLY=" +
          json.dumps(report, sort_keys=True), flush=True)
    return report



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



def postboot_witness_named_states():
    """Only allowlisted static package filenames and finite state labels.

    Do not log package file contents, Config, runtime arguments or hostlists.
    Unknown bytes remain FAIL, not a replacement eligibility verdict.
    """
    result = []
    for rel in load_witnesses():
        target = Path("/usr/local/opnsense") / rel
        source = ROOT / "src" / "opnsense" / rel
        need(source.is_file() and not source.is_symlink(),
             "POSTBOOT_SOURCE_WITNESS_UNTRUSTED")
        expected = source.read_bytes()
        try:
            actual = target.read_bytes()
        except FileNotFoundError:
            status = "missing"
        except OSError:
            status = "foreign"
        else:
            if actual == expected:
                status = "restored"
            elif actual == expected + MARKER:
                status = "marked"
            else:
                status = "foreign"
        if status != "restored":
            result.append({"path": rel, "state": status})
    return result



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
    need(trusted_regular(RECEIPT, 64 * 1024) and
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
        body = (json.dumps(data, sort_keys=True) + "\n").encode()
        need(len(body) <= 64 * 1024, "TEST_RECEIPT_TOO_LARGE")
        f.write(body)
        f.flush()
        os.fsync(f.fileno())
    folder = os.open(RECEIPT.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(folder)
    finally:
        os.close(folder)




def flush_native_saved_config_in_disposable_setup():
    """Test-only controlled saved-Config durability baseline, not a writer.

    OPNsense's original Config::save() has already returned from configd.
    Its documented path calls fflush but not fsync. This one-shot fsync of
    unchanged saved Config isolates the protected pkg interruption from
    an unrelated fresh-Apply guest-cache crash window.
    """
    need(opnsense_config_readable(), "NATIVE_SAVED_CONFIG_UNTRUSTED")
    before = CONFIG.lstat()
    fd = os.open(CONFIG, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
        pinned = os.fstat(fd)
        need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
             (pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns),
             "CONFIG_CHANGED_BEFORE_FSYNC")
        os.fsync(fd)
        after = os.fstat(fd)
        named = CONFIG.lstat()
        need((pinned.st_dev, pinned.st_ino, pinned.st_size, pinned.st_mtime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
             (named.st_dev, named.st_ino, named.st_size, named.st_mtime_ns),
             "CONFIG_CHANGED_DURING_FSYNC")
    finally:
        os.close(fd)
    print("NATIVE_HARDRESET_TEST_ONLY_NATIVE_CONFIG_FSYNC=PASS",
          flush=True)


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
    # This fixture alone establishes a durable pre-existing saved Config.
    # Never silently treat this as a production plugin fix or a powercut test.
    flush_native_saved_config_in_disposable_setup()
    config_before_partial = digest(CONFIG)
    call_rc = {}
    original_native_run = native.run
    def observing_run(argv, **kwargs):
        result = original_native_run(argv, **kwargs)
        if (len(argv) >= 2 and argv[0] == str(SERVICE) and
                argv[1] in ("status", "start", "shared-apply-run",
                            "pkg-update", "pkg-update-finish")):
            # Same native call, same arguments and result; no extra command.
            call_rc[argv[1]] = result.returncode
        return result
    native.run = observing_run
    native_reviewed = load_test_only(
        "stage5-native-reviewed-recovery.py", "reviewed_physical_guest")
    try:
        native_reviewed.interrupt_for_reset(
            native, archive, version, digest(archive))
    except RuntimeError:
        # No raw service logs, Config contents, domains or user hostlists.
        pending = GUARD.is_file() and not GUARD.is_symlink()
        phase = "absent"
        if pending:
            try:
                phase = str(json.loads(GUARD.read_text()).get("phase", "unknown"))
            except (OSError, ValueError):
                phase = "unknown"
        print("NATIVE_HARDRESET_PRE_RESET_REFUSAL=" + json.dumps({
            "guard_phase": phase,
            "prepared_record_present": pending,
            "auto_epoch_retired": (EPOCHS / old_id / "retired.json").is_file(),
            "config_unchanged": digest(CONFIG) == config_before_partial,
            "native_service_rcs": call_rc,
            "service_status_rc": original_native_run(
                [str(SERVICE), "status"]).returncode,
            "owner_appliance_modified": False,
        }, sort_keys=True), flush=True)
        raise
    finally:
        native.run = original_native_run


def load_test_only(filename, module_name):
    spec = importlib.util.spec_from_file_location(
        module_name, ROOT / "scripts" / filename)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def guest_prepare():
    guest_gate()
    version, archive = version_archive()
    # A partial native package may remove a service script or its runtime
    # dependencies. Do not EXECUTE it after the SIGKILL. The old original
    # FD9 Stop and retired epoch were proven before extraction began.
    need(archive.is_file() and not archive.is_symlink(),
         "EXACT_NATIVE_ARCHIVE_MISSING")
    record = read_guard()
    # Metadata only; never log Config content, domain lists or credentials.
    print("NATIVE_HARDRESET_PRECHECK_METADATA=" + json.dumps({
        "config": {"mode": oct(CONFIG.lstat().st_mode & 0o777),
                   "links": CONFIG.lstat().st_nlink,
                   "bytes": CONFIG.lstat().st_size},
        "journal": {"mode": oct(JOURNAL.lstat().st_mode & 0o777),
                    "links": JOURNAL.lstat().st_nlink,
                    "bytes": JOURNAL.lstat().st_size},
    }, sort_keys=True), flush=True)
    need(opnsense_config_readable() and
         trusted_regular(JOURNAL, 128 * 1024),
         "CONFIG_OR_JOURNAL_UNAVAILABLE")
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
    # Read the actual native process table, never run an untrusted or
    # partially installed service after a real package extraction tear.
    ps = run(["/bin/ps", "-axo", "comm="])
    need(ps.returncode == 0 and not any(
         name.strip() == "dvtws2" for name in ps.stdout.splitlines()),
         "NATIVE_ENGINE_NOT_PHYSICALLY_STOPPED_BEFORE_RESET")
    config_before = config_snapshot()
    data = {
        "schema": 1, "test_guest_only": True,
        "version": version, "archive_sha256": digest(archive),
        "config_sha256": config_before["full"],
        "config_snapshot": config_before,
        "guard_sha256": digest(GUARD),
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
    postboot = postboot_readonly_classification(receipt)
    need(postboot["prepared_guard_present_unchanged"],
         "POSTBOOT_PREPARED_GUARD_NOT_DURABLE")
    need(postboot["old_auto_retired"],
         "POSTBOOT_AUTO_RETIREMENT_LOST")
    need(postboot["process_table_available"] and postboot["dvtws2_absent"],
         "POSTBOOT_ENGINE_AUTO_STARTED_OR_UNKNOWN")
    need(postboot["zapret_section_present"] and
         postboot["interfaces_section_present"],
         "POSTBOOT_SAVED_PLUGIN_OR_INTERFACES_MISSING")
    after_config = config_snapshot()
    before_config = receipt["config_snapshot"]
    need(before_config["full"] == receipt["config_sha256"],
         "PRE_RESET_CONFIG_RECEIPT_INCONSISTENT")
    config_bytes_preserved = (
        after_config["full"] == before_config["full"])
    plugin_preserved = after_config["plugin"] == before_config["plugin"]
    interfaces_preserved = (
        after_config["interfaces"] == before_config["interfaces"])
    print("NATIVE_HARDRESET_CONFIG_CLASSIFICATION=" + json.dumps({
        "raw_config_bytes_equal": config_bytes_preserved,
        "saved_plugin_settings_equal": plugin_preserved,
        "saved_wan_interfaces_equal": interfaces_preserved,
        "changed_plugin_paths_count": len(diagnostic_changed_paths(
            before_config["plugin_diagnostic_paths"],
            after_config["plugin_diagnostic_paths"])),
        "changed_plugin_paths": diagnostic_changed_paths(
            before_config["plugin_diagnostic_paths"],
            after_config["plugin_diagnostic_paths"])[:24],
        "opnsense_other_boot_writes_possible": not config_bytes_preserved,
    }, sort_keys=True), flush=True)
    need(plugin_preserved and interfaces_preserved,
         "SAVED_PLUGIN_OR_INTERFACES_CHANGED_ACROSS_RESET")
    record = read_guard()
    need(digest(GUARD) == receipt["guard_sha256"],
         "PREPARED_GUARD_CHANGED_ACROSS_RESET")
    epoch = receipt["original_epoch_id"]
    need((EPOCHS / epoch / "retired.json").is_file(),
         "OLD_AUTO_RETIREMENT_LOST_ON_RESET")
    version, _ = version_archive()
    need(version == receipt["version"] and
         postboot["guard_private_staged_package_unchanged"],
         "PRIVATE_STAGED_ARCHIVE_CHANGED_ON_RESET")
    observed = witness_inventory()
    print("NATIVE_HARDRESET_POSTBOOT_PAYLOAD_WITNESSES=" + json.dumps({
        "counts": observed,
        "non_restored_package_file_states": postboot_witness_named_states(),
        "read_only": True,
    }, sort_keys=True), flush=True)
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
    if not postboot["installed_service_source_trusted"]:
        # A genuinely torn package can leave its service script absent or
        # untrusted. DO NOT execute a service, pkg or unreviewed repair.
        # Prior guards, Config and physical no-engine were checked above.
        print("NATIVE_HARDRESET_POSTBOOT=" + json.dumps({
            "result": "PASS_FAIL_CLOSED_UNTRUSTED_SERVICE_REVIEW_REQUIRED",
            "guard_phase": "prepared",
            "no_engine_process": True,
            "saved_plugin_and_wan_preserved": True,
            "original_auto_retired": True,
            "protected_archive_durable": True,
            "installed_service_trusted": False,
            "pkgdb_current_version": postboot["pkgdb_version_matches_candidate"],
            "mutation_attempted": False, "automatic_repair_attempted": False,
            "recovery_tested": False, "power_loss_tested": False,
            "owner_appliance_modified": False,
        }, sort_keys=True), flush=True)
        print("NATIVE_HARDRESET_POSTBOOT=PASS_FAIL_CLOSED_NO_SERVICE",
              flush=True)
        return
    record = read_guard()
    stage = Path(record["stage"])
    denied = {
        "status": run([str(SERVICE), "status"]).returncode,
        "start": run([str(SERVICE), "start"]).returncode,
        "apply": run([str(SERVICE), "shared-apply-run"]).returncode,
        "repeat": run([str(SERVICE), "pkg-update", str(stage)]).returncode,
        "finish": run([str(SERVICE), "pkg-update-finish",
                       receipt["archive_sha256"], receipt["version"]]).returncode,
    }
    need(denied["status"] == 1 and
         all(denied[x] == 69 for x in ("start", "apply", "repeat", "finish")),
         "MUTATING_ACTION_NOT_REFUSED_AFTER_RESET")
    stable_after_refusals = config_snapshot()
    need(digest(GUARD) == receipt["guard_sha256"] and
         stable_after_refusals["plugin"] == after_config["plugin"] and
         stable_after_refusals["interfaces"] == after_config["interfaces"],
         "GUARD_OR_SAVED_SETTINGS_CHANGED_DURING_REFUSALS")
    pkg = run(["/usr/sbin/pkg", "query", "%v", NAME], timeout=15)
    print("NATIVE_HARDRESET_POSTBOOT=" + json.dumps({
        "boot_changed": True,
        "full_config_bytes_equal": config_bytes_preserved,
        "saved_plugin_settings_equal": True,
        "saved_wan_interfaces_equal": True,
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
    observer = load_test_only("stage5-native-reset-observer.py",
                              "reset_linux_host_readonly_observer")
    # Native AnyVM already maintains a host serial log and SSH forwarding.
    # Read only; neither QEMU's guest disk nor FreeBSD Config is modified.
    serial_path = observer.serial_log_path(observer.qemu_argv(pid))
    serial_before = observer.safe_serial_size(serial_path)
    before = ssh_boot()
    need(isinstance(before, int), "GUEST_UNREACHABLE_BEFORE_RESET")
    status = monitor_command(port, "info status")
    need(bool(re.search(r"\bVM status:\s*running\b", status, flags=re.I)) and
         "Error" not in status,
         "QEMU_MONITOR_NOT_RUNNING")
    reset = monitor_command(port, "system_reset")
    need("Error" not in reset, "QEMU_SYSTEM_RESET_REFUSED")
    deadline = time.monotonic() + 240
    next_observation = time.monotonic() + 60
    after = None
    while time.monotonic() < deadline:
        need(Path("/proc").joinpath(str(pid), "cmdline").is_file(),
             "QEMU_PROCESS_DISAPPEARED_AFTER_RESET")
        after = ssh_boot()
        if isinstance(after, int) and after > before:
            break
        if time.monotonic() >= next_observation:
            print("NATIVE_HARDRESET_HOST_READONLY_OBSERVATION=" + json.dumps(
                observer.observe(pid, port, monitor_command,
                                 serial_before, serial_path), sort_keys=True),
                  flush=True)
            next_observation += 60
        time.sleep(3)
    new_kernel_via_ssh = isinstance(after, int) and after > before
    final_observation = observer.observe(pid, port, monitor_command,
                                         serial_before, serial_path)
    final_observation["strict_new_kernel_via_ssh"] = new_kernel_via_ssh
    print("NATIVE_HARDRESET_HOST_READONLY_FINAL=" +
          json.dumps(final_observation, sort_keys=True), flush=True)
    # Console signal, a running HMP or an SSH banner alone is NOT proof of
    # the required strictly later guest kern.boottime.
    need(new_kernel_via_ssh, "HARD_RESET_BOOT_NOT_OBSERVED")
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
