#!/bin/sh
# Standalone, explicitly destructive OPNsense Zapret2 Restyle purge.
# Uses system Python3; does not depend on the installed plugin package.
exec /usr/bin/env python3 - "$@" <<'PY'
import argparse
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

PACKAGE = "os-zapret2-restyle"
CONFIG = Path("/conf/config.xml")
REGISTRAR = Path("/usr/local/opnsense/scripts/firmware/register.php")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
LOCK = Path("/var/run/zapret2-lifecycle.lock")
REPO = Path("/usr/local/etc/pkg/repos/zapret2-restyle.conf")
IPFW = "/sbin/ipfw"
KLDSTAT = "/sbin/kldstat"

# Explicit Zapret-owned namespaces, not a filesystem wildcard.
OWNED_TREES = (
    "/usr/local/etc/zapret2", "/var/db/zapret2-restyle",
    "/var/db/zapret2", "/var/log/zapret2",
    "/var/run/zapret2-restyle", "/usr/local/share/zapret2-restyle",
    "/usr/local/libexec/zapret2-restyle",
    "/usr/local/opnsense/service/templates/OPNsense/Zapret",
    "/usr/local/opnsense/scripts/OPNsense/Zapret",
    "/usr/local/opnsense/mvc/app/models/OPNsense/Zapret",
    "/usr/local/opnsense/mvc/app/controllers/OPNsense/Zapret",
    "/usr/local/opnsense/mvc/app/views/OPNsense/Zapret",
)
OWNED_FILES = (
    "/var/run/zapret2-lifecycle.lock", "/var/run/zapret2-execution.status",
    "/var/run/zapret2-supervisor-daemon.pid",
    "/var/run/zapret2-supervisor-monitor.pid", "/var/run/dvtws2.pid",
    "/usr/local/opnsense/service/conf/actions.d/actions_zapret.conf",
    "/usr/local/etc/inc/plugins.inc.d/zapret.inc",
    "/usr/local/etc/rc.syshook.d/start/20-zapret",
    "/usr/local/etc/rc.syshook.d/stop/20-zapret",
    "/usr/local/etc/rc.d/zapret",
    "/usr/local/opnsense/version/zapret2-restyle",
)
VOICE_TABLES = tuple("zapret2_voice_" + service + suffix
                     for service in ("telegram", "discord", "x", "sip", "custom")
                     for suffix in ("", "_stage"))


class Refusal(Exception):
    pass


def run(argv, *, accepted=(0,), timeout=30):
    try:
        result = subprocess.run(argv, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Refusal("command could not execute: " + argv[0]) from error
    if result.returncode not in accepted:
        raise Refusal("command failed: " + argv[0] +
                      " (exit " + str(result.returncode) + ")")
    return result


def node(path):
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None


def safe_tree(path):
    """Refuse foreign-owned objects and every symlink; never follow redirects."""
    path = Path(path)
    for part in (path, *path.parents):
        metadata = node(part)
        if metadata is not None and stat.S_ISLNK(metadata.st_mode):
            raise Refusal("symlink in deletion path: " + str(part))
    metadata = node(path)
    if metadata is None:
        return False
    if metadata.st_uid != 0 or not (
        stat.S_ISREG(metadata.st_mode) or stat.S_ISDIR(metadata.st_mode)
    ):
        raise Refusal("unverified owner or file kind: " + str(path))
    if stat.S_ISDIR(metadata.st_mode):
        for parent, dirs, files in os.walk(path, followlinks=False):
            for name in dirs + files:
                item = Path(parent, name)
                nested = node(item)
                if nested is None or nested.st_uid != 0 or not (
                    stat.S_ISDIR(nested.st_mode) or stat.S_ISREG(nested.st_mode)
                    or stat.S_ISLNK(nested.st_mode)
                ):
                    raise Refusal("foreign or unsupported object in owned tree: " + str(item))
                # Upstream v1.0.7 Makefile creates binary aliases with ln -fs.
                # Links INSIDE an already attested Zapret-only tree are safe
                # to unlink as links: never traverse their targets. Neither
                # an owned root nor any path ancestor may be a symlink.

    return True


def opnsense_core_uid():
    """Read OPNsense's system-owned CORE_UID, not a guessed file owner.

    The stock /usr/local/etc/rc.subr.d/php obtains these same values via
    opnsense-version -R and chowns /conf and /conf/config.xml to CORE_USER:wheel.
    """
    output = run(["/usr/local/sbin/opnsense-version", "-R",
                  "CORE_GROUP=CORE_GID:CORE_USER=CORE_UID"], timeout=12).stdout.strip()
    match = re.fullmatch(r"[^:=\s]+=\d+:[^:=\s]+=([1-9]\d*)", output)
    if match is None:
        raise Refusal("cannot verify native OPNsense CORE_USER ownership")
    return int(match.group(1))


def safe_config():
    """Trust native CORE_USER:wheel Config, while refusing unrelated owners.

    OPNsense 26.7 explicitly chowns /conf and config.xml to CORE_USER:wheel;
    assuming UID 0 incorrectly rejects an authentic clean OPNsense guest.
    Never follow symlinks or allow any world-write / foreign Config ancestor.
    """
    native_uid = opnsense_core_uid()
    native_dir = CONFIG.parent
    for parent in CONFIG.parents:
        metadata = node(parent)
        if metadata is None or not stat.S_ISDIR(metadata.st_mode):
            raise Refusal("missing or redirected OPNsense Config ancestor: " + str(parent))
        if parent == native_dir:
            if (metadata.st_uid not in (0, native_uid) or metadata.st_gid != 0 or
                    metadata.st_mode & stat.S_IWOTH):
                raise Refusal("untrusted native OPNsense Config directory: " + str(parent))
        elif metadata.st_uid != 0 or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise Refusal("untrusted OPNsense Config ancestor: " + str(parent))
    metadata = node(CONFIG)
    if (metadata is None or not stat.S_ISREG(metadata.st_mode) or
            metadata.st_uid not in (0, native_uid) or metadata.st_gid != 0 or
            metadata.st_mode & stat.S_IWOTH):
        raise Refusal("missing, redirected or foreign-owned OPNsense config.xml")
    return True

def safe_repo():
    if not safe_tree(REPO):
        return False
    data = REPO.read_text(encoding="utf-8", errors="replace").lower()
    if (not re.search(r"(?m)^\s*zapret2restyle\s*:\s*\{", data) or
            not re.search(r'(?m)^\s*url:\s*"https://tolian82[.]github[.]io/os-zapret2-restyle/[^"]+"', data)):
        raise Refusal("repository file does not prove project ownership")
    return True


def config_state():
    """Presence-only inventory; never dump secret Config data."""
    safe_config()
    try:
        root = ET.parse(CONFIG).getroot()
    except ET.ParseError as error:
        raise Refusal("OPNsense config.xml is malformed") from error
    if root.tag != "opnsense":
        raise Refusal("unexpected OPNsense config root")
    plugins = root.find("system/firmware/plugins")
    registered = PACKAGE in (plugins.text or "").split(",") if plugins is not None else False
    return root.find("OPNsense/Zapret") is not None, registered


def pkg_installed():
    result = run(["/usr/sbin/pkg", "info", "-e", PACKAGE], accepted=(0, 1))
    return result.returncode == 0


def firmware_marker():
    marker = Path("/usr/local/opnsense/version/zapret2-restyle")
    if not safe_tree(marker):
        return False
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise Refusal("firmware marker is not valid OPNsense metadata") from error
    if not isinstance(data, dict) or data.get("product_id") != PACKAGE:
        raise Refusal("firmware marker is not proven to be ours")
    return True


def service_status(installed):
    if not SERVICE.exists():
        if installed:
            raise Refusal("installed package has no native service entrypoint")
        return "missing"
    if not safe_tree(SERVICE):
        return "missing"
    # Native status uses 9>LOCK (write-open/truncate), even when the lock
    # already exists. A dry-run must never invoke it: report process census
    # only, clearly marked UNVERIFIED until native status after backup.
    if not safe_tree(LOCK):
        return "unverified-lock-absent"
    return "process-present-unverified" if processes() else "stopped-unverified"


def native_service_status():
    """Only after explicit confirmation and the verified private Config backup."""
    result = run([str(SERVICE), "status"], accepted=(0, 1, 2), timeout=20)
    if result.returncode == 2:
        raise Refusal("service reports unknown lifecycle owner; refuse purge")
    return "running" if result.returncode == 0 else "stopped"


def processes():
    result = run(["/bin/ps", "-A", "-ww", "-o", "pid=", "-o", "command="], timeout=15)
    found = []
    for line in result.stdout.splitlines():
        match = re.match(r"^\s*(\d+)\s+(.*)$", line)
        if not match:
            continue
        pid, command = int(match[1]), match[2]
        if pid in (os.getpid(), os.getppid()):
            continue
        if any(token in command for token in (
            "/usr/local/etc/zapret2/binaries/my/dvtws2",
            "/usr/local/opnsense/scripts/OPNsense/Zapret/",
            "/var/run/zapret2-restyle/strategy-lab/",
        )) or re.search(r"(?<![A-Za-z0-9_])dvtws2(?![A-Za-z0-9_])", command):
            found.append(pid)
    return found


def attest_processes(installed, status, candidates):
    """Reject an untracked process BEFORE pkg delete can change any state."""
    if candidates and status != "running":
        raise Refusal("unverified native process exists while service is not running")
    if status == "running":
        # Native status has already verified real child PID, supervisor
        # and Zapret-owned IPFW while holding the original FD9.
        # The broad ps census is FOREIGN-process detection: an empty
        # census does not negate a fully verified native RUNNING status.
        if not installed:
            raise Refusal("RUNNING service with no installed package")
        declared = set()
        for pidfile in (
            "/var/run/dvtws2.pid",
            "/var/run/zapret2-supervisor-daemon.pid",
            "/var/run/zapret2-supervisor-monitor.pid",
        ):
            if not safe_tree(pidfile):
                continue
            content = Path(pidfile).read_text(encoding="ascii", errors="replace").strip()
            if not content.isdecimal() or int(content) <= 1:
                raise Refusal("invalid service-owned PID record: " + pidfile)
            declared.add(int(content))
        if not declared:
            raise Refusal("RUNNING service has no owner PID-file evidence")
        if not set(candidates).issubset(declared):
            raise Refusal("unattributed native/foreign process: refuse pre-pkg deletion")


def owned_rules():
    loaded = run([KLDSTAT, "-q", "-m", "ipfw"], accepted=(0, 1))
    if loaded.returncode != 0:
        return []  # Never load IPFW/ipdivert just to purge.
    lines = run([IPFW, "-q", "list"]).stdout
    found = []
    for line in lines.splitlines():
        match = re.match(r"^\s*(\d{1,5})\s+(.*)$", line)
        if match is None:
            raise Refusal("unparseable native IPFW rule list")
        number, expression = int(match[1]), match[2]
        if 19000 <= number <= 19010 or 19100 <= number <= 19131:
            # Actual native ports: Strategies/Voice 989, Laboratory 9989.
            port = 989 if 19000 <= number <= 19010 else 9989
            if not re.search(r"\bdivert\s+" + str(port) + r"\b", expression) or (
                "not diverted not sockarg" not in expression
            ) or " xmit " not in " " + expression + " ":
                raise Refusal("unverified IPFW rule in Zapret2 number range: " + str(number))
            found.append(number)
    return found


def voice_tables():
    """Only ten exact native Voice table names, only the native addr type."""
    loaded = run([KLDSTAT, "-q", "-m", "ipfw"], accepted=(0, 1))
    if loaded.returncode != 0:
        return []
    found = []
    for name in VOICE_TABLES:
        result = run([IPFW, "table", name, "info"], accepted=(0, 1, 69, 71))
        if result.returncode != 0:
            if "No such process" in result.stderr or "does not exist" in result.stderr:
                continue
            raise Refusal("Voice IPFW table cannot be inspected: " + name)
        if not re.search(r"(?im)\btype\s*:\s*addr\b", result.stdout):
            raise Refusal("unexpected foreign Voice-table type: " + name)
        found.append(name)
    return found


def check_platform():
    if not sys.platform.startswith("freebsd"):
        raise Refusal("destructive purge is supported only on FreeBSD/OPNsense")
    if not Path("/usr/local/opnsense").is_dir():
        raise Refusal("not an OPNsense system")
    if os.geteuid() != 0:
        raise Refusal("root is required")


def backup_config():
    safe_config()
    folder = Path("/root/zapret2-restyle-purge-backups")
    if node(folder) is not None and not safe_tree(folder):
        raise Refusal("backup root cannot be trusted")
    folder.mkdir(mode=0o700, exist_ok=True)
    os.chmod(folder, 0o700)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = folder / ("config-" + stamp + "-" + str(os.getpid()) + ".xml")
    fd = os.open(backup, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as output, open(CONFIG, "rb") as source:
            shutil.copyfileobj(source, output)
            output.flush()
            os.fsync(output.fileno())
        if hashlib.sha256(CONFIG.read_bytes()).digest() != hashlib.sha256(backup.read_bytes()).digest():
            raise Refusal("config backup hash mismatch")
    except BaseException:
        backup.unlink(missing_ok=True)
        raise
    return backup


def write_private_report(backup, snapshot):
    """Small private inventory, no Config or resource contents."""
    installed, status, marker, repo, paths, rules, tables, pids = snapshot
    report = backup.with_name(backup.stem.replace("config-", "report-") + ".txt")
    lines = [
        "Zapret2 Restyle standalone purge inventory (pre-deletion)",
        "backup=" + str(backup),
        "backup_sha256=" + hashlib.sha256(backup.read_bytes()).hexdigest(),
        "package_installed=" + str(installed),
        "service_state=" + status,
        "firmware_marker=" + str(marker),
        "project_repo_present=" + str(repo),
        "owned_paths=" + ",".join(paths),
        "scoped_ipfw_rules=" + ",".join(map(str, rules)),
        "voice_ipfw_tables=" + ",".join(tables),
        "runtime_process_pids=" + ",".join(map(str, pids)),
        "NOTE: report contains no Config or resource file contents",
    ]
    fd = os.open(report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write("\n".join(lines) + "\n")
        output.flush()
        os.fsync(output.fileno())
    return report


def remove_config_node():
    # Native OPNsense Config API and its actual lock, NOT XML text replacement.
    php = r'''
require_once("script/load_phalcon.php");
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
    $root = $c->object();
    if (isset($root->OPNsense) && isset($root->OPNsense->Zapret)) {
        unset($root->OPNsense->Zapret);
        $c->save();
    }
} finally { $c->unlock(); }
'''
    run(["/usr/local/bin/php", "-r", php], timeout=40)


def delete_exact(path):
    if not safe_tree(path):
        return
    if stat.S_ISDIR(os.lstat(path).st_mode):
        shutil.rmtree(path)
    else:
        Path(path).unlink()


def repo_state():
    if REPO.exists():
        return "retained; GUI reinstall may remain available"
    return "absent; GUI reinstall requires re-adding repository"


def inventory(keep_repo):
    installed = pkg_installed()
    status = service_status(installed)
    marker = firmware_marker()
    saved, registered = config_state()
    repo = safe_repo()
    paths = [path for path in OWNED_TREES + OWNED_FILES if safe_tree(path)]
    rules, tables, pids = owned_rules(), voice_tables(), processes()
    print("Package:", "installed" if installed else "absent")
    print("Service:", status)
    print("Firmware marker:", "present" if marker else "absent")
    print("Firmware registration:", "present" if registered else "absent")
    print("Saved OPNsense.Zapret settings:", "present" if saved else "absent")
    print("Zapret-only owned paths (names, not contents):", len(paths))
    for path in paths:
        print("  ", path)
    print("Zapret-scoped IPFW rules:", ",".join(map(str, rules)) or "none")
    print("Zapret Voice destination tables:", ",".join(tables) or "none")
    print("Candidate runtime/worker processes:", len(pids))
    print("Project repository:", "present" if repo else "absent",
          "(KEEP)" if keep_repo else "(DELETE on purge)")
    return installed, status, marker, repo, paths, rules, tables, pids


def purge(keep_repo, yes_disposable):
    check_platform()
    snapshot = inventory(keep_repo)
    installed, status, marker, repo, paths, rules, tables, pids = snapshot
    # No status invocation, lock creation or mutation is permitted during
    # the read-only pre-confirmation inventory.
    if pids and status in ("missing", "unverified-lock-absent"):
        raise Refusal("native process exists without verifiable installed lock/service")
    if yes_disposable:
        if (os.environ.get("ZAPRET2_PURGE_DISPOSABLE_GUEST") != "1" or
                os.environ.get("ZAPRET2_G01_DISPOSABLE_NATIVE") != "1" or
                os.environ.get("GITHUB_ACTIONS") != "true"):
            raise Refusal("noninteractive purge requires isolated native CI opt-in")
        guest = run(["/sbin/sysctl", "-n", "kern.vm_guest"]).stdout.strip().lower()
        if guest in ("", "none", "unknown"):
            raise Refusal("noninteractive purge refused on a non-virtual host")
    else:
        phrase = input("Type PURGE OS-ZAPRET2-RESTYLE to destroy all Zapret data: ")
        if phrase != "PURGE OS-ZAPRET2-RESTYLE":
            raise Refusal("confirmation did not match; no changes")
    # Avoid partially deleting an installed package when the required native
    # registrar or Config API is unavailable.
    if not REGISTRAR.is_file() or not os.access(REGISTRAR, os.X_OK):
        raise Refusal("native firmware registrar unavailable")
    if not os.access("/usr/local/bin/php", os.X_OK):
        raise Refusal("native PHP Config API unavailable")
    if not os.access("/usr/local/sbin/configctl", os.X_OK):
        raise Refusal("native webgui reload action unavailable")
    backup = backup_config()
    print("Verified private OPNsense config backup:", backup)
    report = write_private_report(backup, snapshot)
    print("Private pre-deletion inventory report:", report)
    # On a never-started package the lock may not exist: first call of native
    # status would CREATE it. Initialize only after backup, never in dry-run.
    if installed and status == "unverified-lock-absent":
        if node(LOCK) is not None:
            raise Refusal("FD9 lifecycle lock unexpectedly appeared")
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        os.close(fd)
    if installed:
        # This native call takes the original FD9 and is deliberately delayed
        # until AFTER a private SHA-verified backup and purge confirmation.
        status = native_service_status()
        attest_processes(installed, status, processes())
    else:
        attest_processes(False, "missing", processes())
    # Let native pkg PRE_DEINSTALL own its own original FD9; holding it across
    # pkg delete could deadlock the package's real hooks.
    if installed:
        run(["/usr/sbin/pkg", "delete", "-y", PACKAGE], timeout=180)
        if pkg_installed():
            raise Refusal("pkg still reports installed after native delete")
    # Stock native Stop can leave a supervisor in its final teardown for
    # a moment. Wait only for natural exit; NEVER signal, kill or adopt it.
    # Refuse to delete its executable/resources if it remains after the bound.
    for _ in range(5):
        if not processes():
            break
        time.sleep(1)
    if processes():
        raise Refusal("Zapret native process survived pkg removal; refuse cleanup")
    if node(LOCK) is not None and not safe_tree(LOCK):
        raise Refusal("existing FD9 lifecycle lock is not trusted")
    lockfd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lockfd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise Refusal("original FD9 lock busy; pending transaction or owner") from error
        if processes():
            raise Refusal("new native process appeared after package deletion")
        if not REGISTRAR.is_file():
            raise Refusal("native OPNsense firmware registrar missing")
        # Stock registrar refuses removal while this metadata still exists.
        if firmware_marker():
            delete_exact("/usr/local/opnsense/version/zapret2-restyle")
        run([str(REGISTRAR), "remove", PACKAGE], timeout=35)
        current = owned_rules()
        for number in current:
            if number not in rules:
                raise Refusal("unexpected new scoped IPFW rule appeared")
            run([IPFW, "-q", "delete", str(number)], timeout=15)
        if owned_rules():
            raise Refusal("owned IPFW rules survived purge")
        for name in voice_tables():
            if name not in tables:
                raise Refusal("unexpected new Voice IPFW table appeared: " + name)
            run([IPFW, "-q", "table", name, "destroy"], timeout=15)
        if voice_tables():
            raise Refusal("Zapret Voice tables survived purge")
        remove_config_node()
        for path in OWNED_TREES + OWNED_FILES:
            if path == str(LOCK):
                continue
            delete_exact(path)
        if not keep_repo and repo:
            delete_exact(REPO)
        # Explicit purge only: refresh stock GUI menu/PHP cache.
        run(["/usr/local/sbin/configctl", "webgui", "restart"], timeout=60)
        # Delete ONLY the original FD9 inode while still holding that lock.
        # Releasing it first would allow a racing owner to replace the path
        # before an unrelated new inode is unlinked.
        held = os.fstat(lockfd)
        current = node(LOCK)
        if (current is None or current.st_dev != held.st_dev or
                current.st_ino != held.st_ino):
            raise Refusal("FD9 lock inode changed during purge; refuse unlink")
        os.unlink(LOCK)
    finally:
        fcntl.flock(lockfd, fcntl.LOCK_UN)
        os.close(lockfd)
    saved, registered = config_state()
    if (pkg_installed() or saved or registered or firmware_marker() or owned_rules()
            or voice_tables() or processes()
            or any(safe_tree(path) for path in OWNED_TREES + OWNED_FILES)
            or (not keep_repo and REPO.exists())):
        raise Refusal("post-purge residuals remain: manual review required")
    print("POSTCHECK: plugin/owned paths/IPFW are absent")
    print("PURGE COMPLETE; backup retained:", backup)
    print("Project repo:", repo_state())


def main():
    cli = argparse.ArgumentParser(description="Standalone explicit Zapret2 Restyle destructive cleanup")
    group = cli.add_mutually_exclusive_group()
    group.add_argument("--purge", action="store_true", help="destructively remove only verified Zapret2 resources")
    group.add_argument("--dry-run", action="store_true", help="inventory only (default)")
    cli.add_argument("--keep-repo", action="store_true", help="leave repository config for GUI reinstall")
    cli.add_argument("--yes-disposable", action="store_true", help="noninteractive only with ZAPRET2_PURGE_DISPOSABLE_GUEST=1")
    args = cli.parse_args()
    try:
        if args.purge:
            purge(args.keep_repo, args.yes_disposable)
        else:
            if args.yes_disposable:
                raise Refusal("--yes-disposable requires --purge")
            inventory(args.keep_repo)
            print("DRY RUN: no mutations; to erase data use --purge with explicit confirmation")
        return 0
    except (Refusal, OSError, ValueError, EOFError) as error:
        print("PURGE REFUSED:", error, file=sys.stderr)
        return 75


if __name__ == "__main__":
    sys.exit(main())
PY
