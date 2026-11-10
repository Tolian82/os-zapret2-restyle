#!/usr/bin/env python3
"""G01 destructive test ONLY inside the GitHub disposable OPNsense 26.7 VM.

Install from exactly this source first via stage2-opnsense-real-native-clean-install.py.
Do NOT run this on the owner router; guard actual VM, root, exact source, and opt-in.
"""
import copy
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

NAME = "os-zapret2-restyle"
CONFIG = Path("/conf/config.xml")
PURGER = Path(__file__).with_name("purge-os-zapret2-restyle.sh")
PACKAGED_PURGER = Path(
    "/usr/local/opnsense/scripts/OPNsense/Zapret/purge-os-zapret2-restyle.sh"
)


def attest_installed_purger():
    """Require the actual root-owned package executable, not the checkout tool."""
    need(PACKAGED_PURGER.is_file() and not PACKAGED_PURGER.is_symlink(),
         "G10A_INSTALLED_PACKAGE_PURGER_MISSING_OR_SYMLINK")
    details = PACKAGED_PURGER.lstat()
    need(stat.S_ISREG(details.st_mode) and details.st_uid == 0 and
         stat.S_IMODE(details.st_mode) == 0o755,
         "G10A_PACKAGE_PURGER_MODE_OR_OWNER_CHANGED")
    need(PACKAGED_PURGER.read_bytes() == PURGER.read_bytes(),
         "G10A_PACKAGE_PURGER_BYTES_DIFFER_FROM_G01")


def attest_package_purger_removed():
    """The invoked file must vanish with native pkg delete before script exit."""
    need(not os.path.lexists(PACKAGED_PURGER),
         "G10A_INSTALLED_PACKAGE_PURGER_SURVIVED_PURGE")
BACKUP_ROOT = Path("/root/zapret2-restyle-purge-backups")
REPO = Path("/usr/local/etc/pkg/repos/zapret2-restyle.conf")
RUNTIME = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle")
LOGS = Path("/var/log/zapret2")
LAB = Path("/var/run/zapret2-restyle/strategy-lab")


class Refusal(Exception):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def run(argv, *, env=None, timeout=200):
    try:
        r = subprocess.run(argv, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           env=env, timeout=timeout, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise Refusal("NATIVE_COMMAND_FAILURE:" + argv[0]) from exc
    return r


def require_run(argv, marker=None, *, env=None, timeout=200):
    result = run(argv, env=env, timeout=timeout)
    need(result.returncode == 0, "NONZERO:" + argv[0] + ":" +
         str(result.returncode) + ":" + result.stderr[-400:])
    if marker is not None:
        need(marker in result.stdout, "EXPECTED_MARKER_MISSING:" + marker)
    return result.stdout


def sha(data):
    return hashlib.sha256(data).hexdigest()


def xml(data):
    root = ET.fromstring(data)
    need(root.tag == "opnsense", "NOT_AN_OPNSENSE_CONFIG")
    return root


def normalized(root):
    other = copy.deepcopy(root)
    for revision in other.findall("revision"):
        other.remove(revision)
    def strip(node):
        if not (node.text or "").strip():
            node.text = None
        node.tail = None
        for child in node:
            strip(child)
    strip(other)
    return ET.tostring(other, encoding="utf-8")


def preflight():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_PURGE_DISPOSABLE_GUEST") == "1" and
         os.environ.get("ZAPRET2_G01_DISPOSABLE_NATIVE") == "1",
         "CI_DISPOSABLE_OPT_IN_REQUIRED")
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "REQUIRES_FREEBSD_AMD64_ROOT")
    version = require_run(["/usr/local/sbin/opnsense-version", "-a"]).strip()
    need(version == "26.7", "WRONG_OPNSENSE_VERSION")
    need(require_run(["/usr/sbin/pkg", "config", "ABI"]).strip() ==
         "FreeBSD:15:amd64", "WRONG_PKG_ABI")
    guest = require_run(["/sbin/sysctl", "-n", "kern.vm_guest"]).strip().lower()
    need(guest not in ("none", "unknown", ""), "NOT_A_DISPOSABLE_GUEST")
    need(PURGER.is_file() and not PURGER.is_symlink(), "MISSING_STANDALONE_PURGER")
    attest_installed_purger()
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 0,
         "PLUGIN_MUST_ALREADY_BE_INSTALLED")
    # GitHub Actions tar sync leaves the checkout owned by the host UID.
    # Trust ONLY the exact current checkout for this read-only revision query;
    # never write global safe.directory or weaken the system Git policy.
    git = require_run(["/usr/local/bin/git", "-c",
                       "safe.directory=" + str(Path.cwd().resolve()),
                       "rev-parse", "HEAD"]).strip()
    need(os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA") == git,
         "SOURCE_SHA_MISMATCH")
    config = CONFIG.read_bytes()
    root = xml(config)
    # LC-05 now persists default Zapret Config during the real package
    # POST_INSTALL. The fixture must verify it, never require it absent.
    z = root.find("OPNsense/Zapret")
    defaults = (z.findtext("hostlist/youtubedomains") or "").strip().splitlines() if z is not None else []
    strategy = (z.findtext("strategy/trafficargs") or "") if z is not None else ""
    need(z is not None and z.find("purgeSentinel") is None and
         (z.findtext("general/enabled") or "0") == "0" and
         (z.findtext("general/waninterface") or "") == "" and
         defaults == ["youtube.com", "googlevideo.com", "yt.be", "youtu.be",
                      "ytimg.com", "youtubei.googleapis.com", "youtube.googleapis.com",
                      "youtube-nocookie.com", "ggpht.com", "ssl.gstatic.com"] and
         "--filter-tcp=80,443" in strategy and "--filter-udp=443" in strategy,
         "G01_REAL_CLEAN_INSTALL_DEFAULT_CONFIG_MISMATCH")
    need(BACKUP_ROOT.exists() is False, "BACKUP_ROOT_NOT_FRESH")
    need(not REPO.exists(), "REPO_ALREADY_EXISTS")
    return config


def seed_config():
    # Fixture-only saved Config, via actual OPNsense Config API; never directly
    # rewrite /conf/config.xml or disable its locking semantics.
    php = r'''
require_once("config.inc");
require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
    $root = $c->object();
    if (!isset($root->OPNsense)) $root->addChild("OPNsense");
    // A real first install ALREADY has LC-05 defaults. Uninstalled-remnant
    // scenario starts without a Zapret node. Never replace existing values.
    $entry = isset($root->OPNsense->Zapret)
        ? $root->OPNsense->Zapret
        : $root->OPNsense->addChild("Zapret");
    if (isset($entry->purgeSentinel)) exit(73);
    $entry->addChild("purgeSentinel", "g01-disposable-owned");
    $c->save();
} finally { $c->unlock(); }
'''
    require_run(["/usr/local/bin/php", "-r", php])
    need(xml(CONFIG.read_bytes()).findtext("OPNsense/Zapret/purgeSentinel") ==
         "g01-disposable-owned", "CONFIG_SEED_NOT_SAVED")
def seed():
    seed_config()

    # Install the ACTUAL original upstream v1.0.7, not an empty directory
    # masquerading as an engine. This verifies the full checkout/binary tree
    # can be purged without touching the installed OPNsense system.
    setup = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh")
    need(setup.is_file() and not setup.is_symlink(), "NATIVE_SETUP_SCRIPT_MISSING")
    upstream = run(["/bin/sh", str(setup), "install", "v1.0.7"], timeout=300)
    need(upstream.returncode == 0, "NATIVE_UPSTREAM_1_0_7_INSTALL_FAILED:" +
         str(upstream.returncode) + ":" + upstream.stderr[-450:])
    engine = RUNTIME / "binaries/my/dvtws2"
    need(engine.is_file() and os.access(engine, os.X_OK),
         "REAL_UPSTREAM_DVTWS2_NOT_CREATED")
    exact_tag = require_run(["/usr/local/bin/git", "-c",
                             "safe.directory=" + str(RUNTIME),
                             "-C", str(RUNTIME), "describe", "--tags", "--exact-match"]).strip()
    need(exact_tag == "v1.0.7", "UNQUALIFIED_UPSTREAM_CHECKOUT_TAG")
    for d in (RUNTIME / "files/fake", RUNTIME / "lua",
              STATE / "extra-resources", LOGS / "strategy-lab", LAB):
        d.mkdir(parents=True, exist_ok=True)
    for p in (RUNTIME / "lua/g01-owned-custom.lua",
              RUNTIME / "files/fake/g01-owned-extra.bin",
              STATE / "extra-resources/g01-owned.json",
              LOGS / "strategy-lab/g01-owned.log",
              LAB / "g01-owned-job"):
        p.write_text("g01-disposable-owned\n", encoding="utf-8")
        os.chmod(p, 0o600)
    REPO.parent.mkdir(parents=True, exist_ok=True)
    REPO.write_text(
        'Zapret2Restyle: {\n'
        '  url: "https://tolian82.github.io/os-zapret2-restyle/FreeBSD:15:amd64",\n'
        '  enabled: yes,\n  signature_type: "none"\n}\n',
        encoding="utf-8",
    )
    need(REPO.exists(), "REPO_SEED_FAILED")


def verify_isolation(before, after):
    before_root = xml(before)
    after_root = xml(after)
    saved = before_root.find("OPNsense/Zapret")
    need(saved is not None, "NO_SEEDED_OLD_ZAPRET")
    before_root.find("OPNsense").remove(saved)
    plugins = before_root.find("system/firmware/plugins")
    need(plugins is not None and plugins.text is not None,
         "NO_FIRMWARE_REGISTRATION")
    entries = plugins.text.split(",")
    need(NAME in entries, "NO_OLD_REGISTRATION")
    plugins.text = ",".join(sorted(i for i in entries if i != NAME))
    need(normalized(before_root) == normalized(after_root),
         "UNRELATED_CONFIG_WAS_MODIFIED")


def seed_after_normal_uninstall():
    """Simulate a prior GUI/pkg removal that left saved data and custom files."""
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 1,
         "NOT_UNINSTALLED_FOR_REMNANT_SCENARIO")
    need(not Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh").exists(),
         "STILL_INSTALLED_SERVICE_FOR_REMNANT_SCENARIO")
    seed_config()
    for base in (RUNTIME / "lua", STATE / "extra-resources", LAB, LOGS):
        base.mkdir(parents=True, exist_ok=True)
    for item in (RUNTIME / "lua/g01-leftover.lua",
                 STATE / "extra-resources/g01-leftover.json",
                 LAB / "g01-leftover-job", LOGS / "g01-leftover.log"):
        item.write_text("g01-uninstalled-remaining-owned\n", encoding="utf-8")
        os.chmod(item, 0o600)


def verify_uninstalled_remnant_isolation(before, after):
    original = xml(before)
    saved = original.find("OPNsense/Zapret")
    need(saved is not None, "REMNANT_SCENARIO_MISSING_SAVED_CONFIG")
    original.find("OPNsense").remove(saved)
    need(normalized(original) == normalized(xml(after)),
         "REMNANT_PURGE_CHANGED_NONZAPRET_CONFIG")


def verify_running_purge_after_reinstall():
    """Third native scenario: same authentic archive, real lo0 engine RUNNING."""
    root = Path(__file__).resolve().parents[1]
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*([0-9]+)\s*$",
                         (root / "Makefile").read_text(encoding="utf-8"))
    need(revision is not None, "RUNNING_SOURCE_REVISION_MISSING")
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    archive = root / "dist" / (NAME + "-" + version + "_" + revision.group(1) + ".pkg")
    need(archive.is_file() and not archive.is_symlink(),
         "RUNNING_SAME_NATIVE_PACKAGE_ARCHIVE_UNAVAILABLE")
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 1,
         "RUNNING_CANNOT_REINSTALL_OVER_OLD_PACKAGE")
    require_run(["/usr/sbin/pkg", "add", "-f", str(archive)], timeout=180)
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 0,
         "RUNNING_NATIVE_REINSTALL_NOT_INSTALLED")
    attest_installed_purger()

    # Use the source-qualified Stage 0 loopback-only native profile:
    # one harmless TCP 65431/lo0 rule (port 989), no WAN interception.
    php = r'''
require_once("config.inc");
require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
    $root = $c->object();
    if (!isset($root->OPNsense) || !isset($root->OPNsense->Zapret)) exit(73);
    // Preserve original POST_INSTALL defaults; only set loopback-only values
    // through the stock Config API for the disposable RUNNING purge witness.
    $z = $root->OPNsense->Zapret;
    if (!isset($z->general) || !isset($z->strategy) || !isset($z->hostlist)
        || isset($z->purgeSentinel)) exit(73);
    $g = $z->general;
    $g->enabled = "1";
    $g->waninterface = "lo0";
    $g->divertport = "989";
    $g->ports = "65431";
    $s = $z->strategy;
    $s->trafficargs = "--filter-tcp=65431\n--filter-l7=tls\n--lua-desync=pktmod:ip_ttl=23";
    $s->extraargs = "";
    $h = $z->hostlist;
    $h->mode = "all";
    $c->save();
} finally { $c->unlock(); }
'''
    require_run(["/usr/local/bin/php", "-r", php])
    check = xml(CONFIG.read_bytes())
    need(check.findtext("OPNsense/Zapret/general/waninterface") == "lo0" and
         check.findtext("OPNsense/Zapret/general/ports") == "65431",
         "RUNNING_PROFILE_NOT_BOUND_TO_LOOPBACK")

    setup = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh")
    installed = run(["/bin/sh", str(setup), "install", "v1.0.7"], timeout=300)
    need(installed.returncode == 0, "RUNNING_RUNTIME_INSTALL_FAILED:" +
         str(installed.returncode) + ":" + installed.stderr[-450:])
    engine = RUNTIME / "binaries/my/dvtws2"
    need(engine.is_file() and os.access(engine, os.X_OK),
         "RUNNING_NATIVE_UPSTREAM_ENGINE_MISSING")
    service = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
    need(service.is_file() and not service.is_symlink(), "RUNNING_NATIVE_SERVICE_MISSING")
    before = CONFIG.read_bytes()
    service_start = run([str(service), "start"], timeout=150)
    need(service_start.returncode == 0, "LOOPBACK_ONLY_NATIVE_START_FAILED:" +
         str(service_start.returncode) + ":" +
         (service_start.stdout + service_start.stderr)[-650:])
    status = run([str(service), "status"], timeout=30)
    need(status.returncode == 0 and "zapret is running" in status.stdout,
         "LOOPBACK_ONLY_NATIVE_ENGINE_NOT_RUNNING")
    pidfile = Path("/var/run/dvtws2.pid")
    need(pidfile.is_file() and not pidfile.is_symlink(),
         "LOOPBACK_ONLY_ENGINE_PID_MISSING")
    pid_raw = pidfile.read_text(encoding="ascii").strip()
    need(pid_raw.isdecimal() and int(pid_raw) > 1, "LOOPBACK_ONLY_ENGINE_PID_INVALID")
    owned = require_run(["/bin/ps", "-p", pid_raw, "-o", "command="]).strip()
    need(str(engine) in owned, "LOOPBACK_ONLY_ENGINE_PROCESS_NOT_ATTESTED")
    ipfw = require_run(["/sbin/ipfw", "-q", "list"])
    exact = [line for line in ipfw.splitlines()
             if re.match(r"^\s*0*19000\s+", line)]
    need(len(exact) == 1 and "divert 989" in exact[0] and
         "65431" in exact[0] and "lo0" in exact[0],
         "LOOPBACK_ONLY_OWNED_IPFW_NOT_ATTESTED")

    print("G01_PHASE3_RUNNING_PACKAGED_PURGE=BEGIN", flush=True)
    try:
        purge = require_run(["/bin/sh", str(PACKAGED_PURGER), "--purge", "--yes-disposable"],
                            "POSTCHECK:", timeout=200)
    except Refusal:
        report_native_process_attestation_mismatch()
        raise
    need("PURGE COMPLETE" in purge, "RUNNING_NATIVE_FULL_PURGE_NOT_ACKNOWLEDGED")
    attest_package_purger_removed()
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 1,
         "RUNNING_NATIVE_PACKAGE_SURVIVED_PURGE")
    need(not RUNTIME.exists() and not pidfile.exists(),
         "RUNNING_NATIVE_ENGINE_OR_PIDFILE_SURVIVED_PURGE")
    after_rules = require_run(["/sbin/ipfw", "-q", "list"])
    need(not any(re.match(r"^\s*0*19000\s+", row)
                 for row in after_rules.splitlines()),
         "RUNNING_OWNED_IPFW_RULE_SURVIVED_PURGE")
    unrelated_before = [row for row in ipfw.splitlines()
                        if not re.match(r"^\s*0*19000\s+", row)]
    unrelated_after = [row for row in after_rules.splitlines()
                       if not re.match(r"^\s*0*19000\s+", row)]
    need(unrelated_after == unrelated_before,
         "RUNNING_NATIVE_PURGE_MODIFIED_UNRELATED_IPFW")
    copies = list(BACKUP_ROOT.glob("config-*.xml"))
    need(len(copies) == 3 and
         any(sha(item.read_bytes()) == sha(before) for item in copies),
         "RUNNING_NATIVE_PREDELETION_CONFIG_BACKUP_MISSING")
    verify_isolation(before, CONFIG.read_bytes())
    return {
        "running_to_purged": True,
        "installed_package_purger_self_removed": True,
        "lo0_only_65431": True,
        "real_dvtws2_pid": True,
        "real_owned_ipfw_removed": True,
        "native_pkg_stop_and_delete": True,
    }


def report_native_process_attestation_mismatch():
    """Disposable-VM-only, redacted PID/PPID/source diagnostics; no secrets."""
    pidfiles = {}
    for name in ("dvtws2.pid", "zapret2-supervisor-daemon.pid",
                 "zapret2-supervisor-monitor.pid"):
        location = Path("/var/run") / name
        if location.is_file() and not location.is_symlink():
            value = location.read_text(encoding="ascii", errors="replace").strip()
            pidfiles[name] = int(value) if value.isdecimal() else "invalid"
        else:
            pidfiles[name] = None
    census = run(["/bin/ps", "-A", "-ww", "-o", "pid=",
                  "-o", "ppid=", "-o", "command="], timeout=20)
    matched = []
    if census.returncode == 0:
        for line in census.stdout.splitlines():
            row = re.match(r"^\s*(\d+)\s+(\d+)\s+(.*)$", line)
            if row is None:
                continue
            pid, ppid, cmd = int(row[1]), int(row[2]), row[3]
            kind = ("engine" if "dvtws2" in cmd else
                    "script" if "/usr/local/opnsense/scripts/OPNsense/Zapret/" in cmd
                    else "lab" if "/var/run/zapret2-restyle/strategy-lab/" in cmd
                    else "")
            if not kind:
                continue
            command_name = Path(cmd.split()[0]).name if cmd.split() else "empty"
            matched.append({"pid": pid, "ppid": ppid,
                            "kind": kind, "first_executable": command_name})
    print("G01_NATIVE_REDACTED_OWNER_CENSUS=" + json.dumps({
        "owner_pidfiles": pidfiles,
        "candidate_count": len(matched),
        "candidates": matched[:30],
        "ps_returncode": census.returncode,
    }, sort_keys=True), flush=True)


def execute():
    preflight()
    seed()
    seeded_config = CONFIG.read_bytes()
    need(xml(seeded_config).find("OPNsense/Zapret") is not None, "SAVED_CONFIG_MISSING")
    metadata = CONFIG.lstat()
    print("G01_NATIVE_CONFIG_METADATA=" + json.dumps({
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "mode": oct(stat.S_IMODE(metadata.st_mode)),
        "file_type": "regular" if stat.S_ISREG(metadata.st_mode) else "not_regular",
    }, sort_keys=True))
    conf_parent = Path("/conf").lstat()
    native_owner = require_run(["/usr/local/sbin/opnsense-version", "-R",
                                "CORE_GROUP=CORE_GID:CORE_USER=CORE_UID"]).strip()
    print("G01_NATIVE_CONF_OWNER=" + json.dumps({
        "conf_uid": conf_parent.st_uid,
        "conf_gid": conf_parent.st_gid,
        "conf_mode": oct(stat.S_IMODE(conf_parent.st_mode)),
        "system_owner": native_owner,
    }, sort_keys=True))
    dry_before = CONFIG.read_bytes()
    fd9 = Path("/var/run/zapret2-lifecycle.lock")
    before_fd9 = fd9.lstat() if fd9.exists() else None
    output = require_run(["/bin/sh", str(PACKAGED_PURGER), "--dry-run"], "DRY RUN:")
    after_fd9 = fd9.lstat() if fd9.exists() else None
    need((before_fd9 is None and after_fd9 is None) or
         (before_fd9 is not None and after_fd9 is not None and
          (before_fd9.st_ino, before_fd9.st_size,
           before_fd9.st_mtime_ns, before_fd9.st_ctime_ns) ==
          (after_fd9.st_ino, after_fd9.st_size,
           after_fd9.st_mtime_ns, after_fd9.st_ctime_ns)),
         "G01_DRY_RUN_CREATED_OR_MUTATED_NATIVE_FD9")
    need("Package: installed" in output and "Firmware registration: present" in output,
         "DRY_RUN_DID_NOT_DETECT_PACKAGE_OR_SAVED_CONFIG")
    need(CONFIG.read_bytes() == dry_before and REPO.exists(),
         "DRY_RUN_MUTATED_CONFIG_OR_REPO")
    os.environ["ZAPRET2_PURGE_DISPOSABLE_GUEST"] = "1"
    try:
        purge = require_run(["/bin/sh", str(PACKAGED_PURGER), "--purge", "--yes-disposable"],
                            "POSTCHECK:", timeout=200)
    except Refusal:
        report_native_process_attestation_mismatch()
        raise
    need("PURGE COMPLETE" in purge, "PURGE_DID_NOT_ACKNOWLEDGE")
    attest_package_purger_removed()
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 1,
         "PACKAGE_STILL_INSTALLED")
    need(not REPO.exists() and not RUNTIME.exists() and
         not STATE.exists() and not LOGS.exists() and not LAB.exists(),
         "OWNED_RUNTIME_OR_REPO_REMAINS")
    need(xml(CONFIG.read_bytes()).find("OPNsense/Zapret") is None,
         "ZAPRET_SAVED_CONFIG_REMAINS")
    verify_isolation(seeded_config, CONFIG.read_bytes())
    copies = sorted(BACKUP_ROOT.glob("config-*.xml"))
    need(len(copies) == 1, "NOT_EXACTLY_ONE_CONFIG_BACKUP")
    backup = copies[0]
    need(stat.S_IMODE(BACKUP_ROOT.stat().st_mode) == 0o700,
         "BACKUP_DIRECTORY_NOT_PRIVATE")
    need(stat.S_IMODE(backup.stat().st_mode) == 0o600,
         "BACKUP_FILE_NOT_PRIVATE")
    need(sha(backup.read_bytes()) == sha(seeded_config),
         "CONFIG_BACKUP_NOT_ORIGINAL_SEEDED_BYTES")
    post_config = CONFIG.read_bytes()
    clean = require_run(["/bin/sh", str(PURGER), "--dry-run"], "DRY RUN:")
    need("Package: absent" in clean and
         "Saved OPNsense.Zapret settings: absent" in clean,
         "POSTPURGE_DRY_RUN_REPORTS_LEFTOVER")
    need(CONFIG.read_bytes() == post_config, "REPEAT_DRY_RUN_CHANGED_CONFIG")
    print("G10A_INSTALLED_PACKAGE_PURGER_SELF_DELETE=PASS", flush=True)
    print("G01_PHASE1_INSTALLED_PURGE=PASS", flush=True)
    # Second destructive case: actual reinstall followed by stock Firmware
    # removal. The locally deployed purge must still exist without a pkg.
    root = Path(__file__).resolve().parents[1]
    revision = re.search(r"(?m)^PLUGIN_REVISION=\s*([0-9]+)\s*$",
                         (root / "Makefile").read_text())
    need(revision is not None, "REMNANT_PACKAGE_REVISION_MISSING")
    pkgpath = root / "dist" / (
        NAME + "-" + (root / "VERSION").read_text().strip()
        + "_" + revision.group(1) + ".pkg")
    need(pkgpath.is_file() and not pkgpath.is_symlink(),
         "REMNANT_REAL_PACKAGE_ARCHIVE_MISSING")
    require_run(["/usr/sbin/pkg", "add", "-f", str(pkgpath)], timeout=180)
    attest_installed_purger()
    require_run(["/bin/sh", "/usr/local/opnsense/scripts/firmware/remove.sh",
                 NAME], timeout=220)
    need(run(["/usr/sbin/pkg", "info", "-e", NAME]).returncode == 1,
         "REMNANT_PACKAGE_UNINSTALL_FAILED")
    attest_installed_purger()
    seed_after_normal_uninstall()
    second_saved = CONFIG.read_bytes()
    dry_uninstalled = require_run(["/bin/sh", str(PACKAGED_PURGER), "--dry-run"], "DRY RUN:")
    need("Package: absent" in dry_uninstalled and
         "Saved OPNsense.Zapret settings: present" in dry_uninstalled,
         "POSTUNINSTALL_LEFTOVER_INVENTORY_WRONG")
    need(second_saved == CONFIG.read_bytes(), "POSTUNINSTALL_DRY_RUN_CHANGED_CONFIG")
    require_run(["/bin/sh", str(PACKAGED_PURGER), "--purge", "--yes-disposable"],
                "POSTCHECK:", timeout=200)
    need(not RUNTIME.exists() and not STATE.exists() and
         not LOGS.exists() and not LAB.exists() and
         xml(CONFIG.read_bytes()).find("OPNsense/Zapret") is None,
         "POSTUNINSTALL_RESIDUALS_SURVIVED")
    verify_uninstalled_remnant_isolation(second_saved, CONFIG.read_bytes())
    all_backups = sorted(BACKUP_ROOT.glob("config-*.xml"))
    need(len(all_backups) == 2, "MISSING_SECOND_PRIVATE_CONFIG_BACKUP")
    need(any(sha(p.read_bytes()) == sha(second_saved) for p in all_backups),
         "SECOND_CONFIG_BACKUP_CHANGED_BYTES")
    need(not os.path.lexists(PACKAGED_PURGER), "POSTUNINSTALL_PURGE_SCRIPT_SURVIVED")
    print("G01_PHASE2_REAL_FIRMWARE_UNINSTALL_PERSISTENT_PURGE=PASS", flush=True)
    running_case = verify_running_purge_after_reinstall()


    return {
        "status": "PASS_DISPOSABLE_NATIVE_G01_INSTALLED_AND_UNINSTALLED_REMNANTS",
        "exact_source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        "real_pkg_delete": True,
        "installed_package_purger_used_and_self_removed": True,
        "running_package_purger_used_and_self_removed": running_case["installed_package_purger_self_removed"],
        "firmware_registration_removed": True,
        "root_config_backup_sha256": sha(backup.read_bytes()),
        "nonzapret_config_semantically_unchanged": True,
        "custom_lua_bin_job_logs_removed": True,
        "repo_removed": True,
        "second_dry_run_idempotent": True,
        "postuninstall_real_firmware_retained_cli_purge_tested": True,
        "exact_upstream_v1_0_7_tree_purged": True,
        "runtime_ipfw_rules_tested": running_case["real_owned_ipfw_removed"],
        "real_running_process_tested": running_case["real_dvtws2_pid"],
        "running_case": running_case,
        "owner_machine_modified": False,
    }


if __name__ == "__main__":
    try:
        result = execute()
    except (Refusal, OSError, ValueError, ET.ParseError) as error:
        print("STAGE2_G01_PURGE=REFUSED:" + str(error), file=sys.stderr)
        sys.exit(2)
    print("STAGE2_G01_PURGE=" + json.dumps(result, sort_keys=True))
