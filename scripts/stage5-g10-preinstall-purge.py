#!/usr/bin/env python3
"""G10: verify a real orphaned-Config purge before one native package build.

Only on a disposable OPNsense guest. Not owner GUI or DPI-bypass evidence.
"""
import copy
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
PURGER = ROOT / "scripts/purge-os-zapret2-restyle.sh"
CONFIG = Path("/conf/config.xml")
SENTINEL = Path("/var/log/zapret2/g10-preinstall-orphan.log")
RECEIPT = ROOT / "dist/g10-preinstall-purge.json"
CLEAN = ROOT / "dist/stage5-native-single-artifact.json"
STATUS = "PASS_G10_NATIVE_ORPHAN_PURGE_BEFORE_CLEAN_PACKAGE"


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def command(argv, timeout=120, env=None):
    return subprocess.run(argv, check=False, capture_output=True, text=True,
                          timeout=timeout, env=env)


def tree():
    return ET.fromstring(CONFIG.read_bytes())


def unaffected(xml_root):
    clone = copy.deepcopy(xml_root)
    for revision in clone.findall("revision"):
        clone.remove(revision)
    opnsense = clone.find("OPNsense")
    if opnsense is not None:
        for item in opnsense.findall("Zapret"):
            opnsense.remove(item)
    if opnsense is not None and not list(opnsense) and not (opnsense.text or "").strip() and not opnsense.attrib:
        clone.remove(opnsense)
    for node in clone.iter():
        if not (node.text or "").strip():
            node.text = None
        node.tail = None
    return ET.tostring(clone, encoding="utf-8")


def validate(record, head):
    need(isinstance(record, dict) and record.get("schema") == 1 and
         record.get("status") == STATUS and
         re.fullmatch(r"[0-9a-f]{40}", head) is not None and
         record.get("project_sha") == head and
         record.get("disposable_opnsense") == "26.7" and
         record.get("abi") == "FreeBSD:15:amd64" and
         record.get("preexisting_package_absent") is True and
         record.get("native_config_orphan_seeded") is True and
         record.get("dry_run_preserved_config") is True and
         record.get("real_purge_completed") is True and
         record.get("orphan_and_zapret_node_absent") is True and
         record.get("unrelated_config_preserved") is True and
         record.get("postpurge_dry_run_clean") is True and
         record.get("candidate_package_built_during_purge") is False and
         record.get("owner_device_modified") is False,
         "G10_PURGE_ATTESTATION_MISSING_OR_FORGED")
    return True


def native():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G10_PREINSTALL_PURGE") == "1" and
         os.environ.get("ZAPRET2_PURGE_DISPOSABLE_GUEST") == "1" and
         os.environ.get("ZAPRET2_G01_DISPOSABLE_NATIVE") == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "G10_REQUIRES_EXPLICIT_DISPOSABLE_FREEBSD_GUEST")
    version = command(["/usr/local/sbin/opnsense-version", "-a"])
    abi = command(["/usr/sbin/pkg", "config", "ABI"])
    guest = command(["/sbin/sysctl", "-n", "kern.vm_guest"])
    need(version.returncode == 0 and version.stdout.strip() == "26.7" and
         abi.returncode == 0 and abi.stdout.strip() == "FreeBSD:15:amd64" and
         guest.returncode == 0 and guest.stdout.strip().lower() not in
         ("", "none", "unknown"), "G10_UNQUALIFIED_NATIVE_GUEST")
    head = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    git = command(["/usr/local/bin/git", "-c",
                   "safe.directory=" + str(ROOT.resolve()),
                   "-C", str(ROOT), "rev-parse", "HEAD"])
    need(git.returncode == 0 and git.stdout.strip() == head and
         re.fullmatch(r"[a-f0-9]{40}", head) is not None,
         "G10_SOURCE_HEAD_MISMATCH")
    need(PURGER.is_file() and not PURGER.is_symlink() and
         CONFIG.is_file() and not CONFIG.is_symlink() and
         not RECEIPT.exists() and not RECEIPT.is_symlink() and
         not CLEAN.exists(), "G10_NOT_FRESH_BEFORE_FIRST_PACKAGE")
    need(command(["/usr/sbin/pkg", "info", "-e", "os-zapret2-restyle"]).returncode == 1 and
         tree().find("./OPNsense/Zapret") is None and
         not SENTINEL.exists() and not SENTINEL.parent.exists() and
         not Path("/usr/local/etc/zapret2").exists(),
         "G10_GUEST_ALREADY_OWNED_OR_NOT_CLEAN")
    before = unaffected(tree())
    # The orphan is saved through the real, locked OPNsense Config API.
    php = r'''require_once('config.inc');
require_once('script/load_phalcon.php');
$c = \OPNsense\Core\Config::getInstance();
$c->lock();
try {
  $root = $c->object();
  if (!isset($root->OPNsense)) $root->addChild('OPNsense');
  if (isset($root->OPNsense->Zapret)) exit(73);
  $z = $root->OPNsense->addChild('Zapret');
  $z->addChild('purgeSentinel', 'g10-disposable-orphan');
  $c->save();
} finally { $c->unlock(); }'''
    seed = command(["/usr/local/bin/php", "-r", php])
    need(seed.returncode == 0 and
         tree().findtext("./OPNsense/Zapret/purgeSentinel") ==
         "g10-disposable-orphan", "G10_NATIVE_ORPHAN_CONFIG_NOT_SEEDED")
    SENTINEL.parent.mkdir(parents=True, exist_ok=False)
    SENTINEL.write_text("g10-disposable-orphan\n", encoding="utf-8")
    SENTINEL.chmod(0o600)
    seeded = CONFIG.read_bytes()
    dry = command(["/bin/sh", str(PURGER), "--dry-run"])
    need(dry.returncode == 0 and "DRY RUN:" in dry.stdout and
         CONFIG.read_bytes() == seeded and SENTINEL.is_file(),
         "G10_PURGE_DRY_RUN_MUTATED_OR_FAILED")
    purge = command(["/bin/sh", str(PURGER), "--purge", "--yes-disposable"], timeout=240)
    need(purge.returncode == 0 and "PURGE COMPLETE" in purge.stdout and
         "POSTCHECK:" in purge.stdout,
         "G10_REAL_NATIVE_PURGE_FAILED:" + str(purge.returncode) + ":" +
         purge.stderr[-350:])
    need(not SENTINEL.exists() and not SENTINEL.parent.exists() and
         tree().find("./OPNsense/Zapret") is None and
         command(["/usr/sbin/pkg", "info", "-e", "os-zapret2-restyle"]).returncode == 1,
         "G10_PURGE_LEFT_ORPHAN_OR_PKG")
    need(unaffected(tree()) == before, "G10_PURGE_CHANGED_FOREIGN_CONFIG")
    config_after = CONFIG.read_bytes()
    final = command(["/bin/sh", str(PURGER), "--dry-run"])
    need(final.returncode == 0 and "Package: absent" in final.stdout and
         "Saved OPNsense.Zapret settings: absent" in final.stdout and
         CONFIG.read_bytes() == config_after,
         "G10_POSTPURGE_NOT_CLEAN_OR_DRY_RUN_MUTATED")
    receipt = {"schema": 1, "status": STATUS, "project_sha": head,
               "disposable_opnsense": "26.7", "abi": "FreeBSD:15:amd64",
               "preexisting_package_absent": True,
               "native_config_orphan_seeded": True,
               "dry_run_preserved_config": True,
               "real_purge_completed": True,
               "orphan_and_zapret_node_absent": True,
               "unrelated_config_preserved": True,
               "postpurge_dry_run_clean": True,
               "candidate_package_built_during_purge": False,
               "owner_device_modified": False}
    validate(receipt, head)
    RECEIPT.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8")
    print("G10_NATIVE_PREINSTALL_PURGE=" + json.dumps(receipt, sort_keys=True))


def verify(head):
    need(RECEIPT.is_file() and not RECEIPT.is_symlink() and
         stat.S_ISREG(RECEIPT.lstat().st_mode) and
         CLEAN.is_file() and not CLEAN.is_symlink(),
         "G10_RECEIPTS_MISSING")
    record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    clean = json.loads(CLEAN.read_text(encoding="utf-8"))
    validate(record, head)
    need(clean.get("project_sha") == head and
         clean.get("genuine_clean_pkg_add") is True and
         clean.get("archive_sha256") is not None,
         "G10_PURGE_NOT_BOUND_TO_GUEST_A_INSTALL")
    print("PASS_G10_PURGE_THEN_SAME_SOURCE_GUEST_A_INSTALL")


def self_test():
    head = "a" * 40
    record = {"schema": 1, "status": STATUS, "project_sha": head,
              "disposable_opnsense": "26.7", "abi": "FreeBSD:15:amd64",
              "preexisting_package_absent": True,
              "native_config_orphan_seeded": True,
              "dry_run_preserved_config": True,
              "real_purge_completed": True,
              "orphan_and_zapret_node_absent": True,
              "unrelated_config_preserved": True,
              "postpurge_dry_run_clean": True,
              "candidate_package_built_during_purge": False,
              "owner_device_modified": False}
    validate(record, head)
    for key in record:
        bad = dict(record)
        bad[key] = None
        try:
            validate(bad, head)
        except Refusal:
            pass
        else:
            raise AssertionError("G10_FALSE_PURGE_PASS:" + key)
    need(unaffected(ET.fromstring("<opnsense><revision>2</revision><OPNsense><Zapret><x>1</x></Zapret></OPNsense><system><hostname>one</hostname></system></opnsense>")) ==
         unaffected(ET.fromstring("<opnsense><revision>3</revision><OPNsense></OPNsense><system><hostname>one</hostname></system></opnsense>")),
         "G10_FOREIGN_CONFIG_COMPARISON_BROKEN")
    print("PASS_G10_SOURCE_ORPHAN_PURGE_GUARDS")


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["run"]:
            native()
        elif len(sys.argv) == 3 and sys.argv[1] == "verify":
            verify(sys.argv[2])
        else:
            raise Refusal("G10_USAGE_SELF_TEST_RUN_VERIFY_HEAD")
        return 0
    except (Refusal, OSError, ValueError, ET.ParseError, subprocess.TimeoutExpired) as exc:
        print("G10_PREINSTALL_PURGE=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
