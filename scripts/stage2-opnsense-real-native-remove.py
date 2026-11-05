#!/usr/bin/env python3
"""Real native pkg removal followed by official OPNsense firmware unregister.

Run ONLY after real native clean install and packaged configctl read-only
checks on a disposable OPNsense 26.7. No owner installation, no simulated pkg.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

from stage2_source_revision import revision_from_makefile

HERE = Path(__file__).resolve().parent
import importlib.util


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


clean = load("stage2-opnsense-real-native-clean-install.py", "clean_remove_native")
native = clean.native
Refusal = clean.Refusal
need = clean.need
NAME = clean.NAME
VERSION = clean.VERSION
OPTIN = "ZAPRET2_STAGE2_REAL_FIRMWARE_REMOVE"
REGISTRATION = "/usr/local/opnsense/scripts/firmware/register.php"
CONFIG = Path("/conf/config.xml")
FILE_ROOT = Path("/usr/local")


def xml_root(contents):
    try:
        root = ET.fromstring(contents)
    except ET.ParseError:
        raise Refusal("FIRMWARE_REMOVE_CONFIG_INVALID_XML") from None
    need(root.tag == "opnsense", "FIRMWARE_REMOVE_CONFIG_WRONG_ROOT")
    return root


def plugin_list(root):
    node = root.find("system/firmware/plugins")
    need(node is not None, "FIRMWARE_REMOVE_PLUGIN_LIST_MISSING")
    names = [item for item in (node.text or "").split(",") if item]
    need(len(set(names)) == len(names), "FIRMWARE_REMOVE_PLUGIN_LIST_DUPLICATES")
    return names


def normalized(root):
    root = copy.deepcopy(root)
    for revision in root.findall("revision"):
        root.remove(revision)
    def strip_formatting(node):
        if not (node.text or "").strip():
            node.text = None
        node.tail = None
        for child in node:
            strip_formatting(child)
    strip_formatting(root)
    return ET.tostring(root, encoding="utf-8")


def check_official_unregistration(before, after):
    """Only registered package and Config revision metadata may change."""
    before_root, after_root = xml_root(before), xml_root(after)
    before_names = plugin_list(before_root)
    after_names = plugin_list(after_root)
    need(NAME in before_names and
         after_names == sorted(name for name in before_names if name != NAME),
         "FIRMWARE_REMOVE_REGISTRATION_NOT_EXACT")
    original_saved = before_root.find("OPNsense/Zapret")
    after_saved = after_root.find("OPNsense/Zapret")
    need((original_saved is None) == (after_saved is None),
         "FIRMWARE_REMOVE_SAVED_CONFIG_PRESENCE_CHANGED")
    if original_saved is not None:
        need(ET.tostring(original_saved) == ET.tostring(after_saved),
             "FIRMWARE_REMOVE_SAVED_CONFIG_MODIFIED")
    before_root.find("system/firmware/plugins").text = ",".join(after_names)
    need(normalized(before_root) == normalized(after_root),
         "FIRMWARE_REMOVE_CHANGED_UNRELATED_CONFIG")
    return {"status": "PASS_OFFICIAL_FIRMWARE_UNREGISTER_ONLY",
            "plugin_removed_from_firmware_registry": True,
            "other_config_preserved_semantically": True,
            "saved_zapret_config_present": original_saved is not None,
            "saved_zapret_config_retained_when_present": True}


def preflight():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "EXPLICIT_DISPOSABLE_FIRMWARE_REMOVE_OPTIN_REQUIRED")
    # The native.gate() predicate is intentionally restricted to the EMPTY
    # pre-install guest. This test runs AFTER actual pkg add, so reuse its
    # qualified target and exact git-head checks, plus the real installed
    # package identity, without weakening the clean-install gate.
    need(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "POSTINSTALL_REMOVE_NOT_FREEBSD_AMD64_ROOT")
    need(clean.required(["opnsense-version", "-a"], "OPNSENSE_VERSION_UNAVAILABLE")
         == "26.7", "POSTINSTALL_REMOVE_WRONG_OPNSENSE_ABI")
    need(clean.required(["pkg", "config", "ABI"], "PKG_ABI_UNAVAILABLE")
         == "FreeBSD:15:amd64", "POSTINSTALL_REMOVE_WRONG_PKG_ABI")
    need(clean.required(["sysctl", "-n", "kern.vm_guest"],
                        "VM_IDENTITY_UNAVAILABLE").lower()
         not in ("", "none", "unknown"),
         "POSTINSTALL_REMOVE_REQUIRES_VIRTUAL_GUEST")
    need(native.git_head() == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "POSTINSTALL_REMOVE_EXACT_SOURCE_SHA_MISMATCH")
    native.qualified_target()
    need(native.REVISION == revision_from_makefile(), "REVISION_NOT_CURRENT")
    installed = clean.run(["pkg", "info", "-e", NAME], timeout=20)
    need(installed.returncode == 0, "NATIVE_PACKAGE_NOT_INSTALLED")
    archive = native.ROOT / "dist" / (NAME + "-" + VERSION + ".pkg")
    need(archive.is_file() and not archive.is_symlink(),
         "NATIVE_ARCHIVE_UNAVAILABLE_FOR_INSTALLED_MANIFEST")
    archive_manifest, installed_manifest = clean.installed_pkg_manifest(archive)
    need(installed_manifest["name"] == NAME and
         installed_manifest["version"] == VERSION,
         "FOREIGN_INSTALLED_PACKAGE_IDENTITY")
    need(set(installed_manifest["scripts"]) == set(native.HOOKS.values()),
         "INSTALLED_FOUR_HOOKS_UNQUALIFIED")
    clean.cold_status()
    need(CONFIG.is_file() and not CONFIG.is_symlink(),
         "FIRMWARE_REMOVE_CONFIG_NOT_TRUSTED")
    before = CONFIG.read_bytes()
    need(NAME in plugin_list(xml_root(before)),
         "PACKAGE_NOT_REGISTERED_IN_FIRMWARE")
    return before, archive_manifest


def remove():
    before, manifest = preflight()
    expected_files = sorted(manifest["files"])
    need(bool(expected_files), "NATIVE_PACKAGE_HAS_NO_FILES")
    for path in expected_files:
        need(path.startswith("/usr/local/") and
             (Path(path).is_file() or Path(path).is_symlink()),
             "PRE_REMOVE_PACKAGED_FILE_MISSING:" + path)
    before_sha = hashlib.sha256(before).hexdigest()
    action = clean.run(["pkg", "-o", "REPO_AUTOUPDATE=false", "delete", "-y", NAME],
                       timeout=180)
    need(action.returncode == 0,
         "REAL_PKG_DELETE_HOOK_FAILURE:" + str(action.returncode) +
         ":" + action.stderr[-260:])
    query = clean.run(["pkg", "info", "-e", NAME], timeout=20)
    need(query.returncode == 1, "PACKAGE_REMAINS_IN_PKGDB_AFTER_DELETE")
    service = FILE_ROOT / native.SERVICE
    need(not service.exists() and not service.is_symlink(),
         "INSTALLED_SERVICE_REMAINS_AFTER_DELETE")
    for path in expected_files:
        item = Path(path)
        need(not item.exists() and not item.is_symlink(),
             "PACKAGED_FILE_REMAINS_AFTER_DELETE:" + path)
    for marker in clean.PRESERVED:
        item = Path(marker)
        need(not item.exists() and not item.is_symlink(),
             "REMOVAL_LEFT_RUNTIME_OR_RESTART_MARKER:" + marker)
    need(CONFIG.read_bytes() == before,
         "PKG_DELETE_CHANGED_CONFIG_BEFORE_OFFICIAL_UNREGISTER")
    # Mirrors the official OPNsense stable/26.7 firmware/remove.sh sequence.
    # Do not run autoremove: it could affect system-wide dependencies.
    register = clean.run([REGISTRATION, "remove", NAME], timeout=30)
    need(register.returncode == 0,
         "OFFICIAL_FIRMWARE_REMOVE_FAILED:" + str(register.returncode) +
         ":" + register.stderr[-260:])
    after = CONFIG.read_bytes()
    retained = check_official_unregistration(before, after)
    return {"schema": 1, "status": "PASS_REAL_NATIVE_PKG_DELETE_AND_FIRMWARE_REMOVE",
            "tested_exact_project_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
            "package": NAME + "-" + VERSION,
            "pkg_remove_with_native_hooks": True,
            "installed_pre_and_post_deinstall_hook_bytes_verified": True,
            "post_deinstall_independently_traced": False,
            "package_absent_from_pkgdb": True,
            "packaged_files_removed": len(expected_files),
            "no_leftover_restart_or_pid_markers": True,
            "config_before_pkg_delete_sha256": before_sha,
            "config_unchanged_by_pkg_delete": True,
            "official_unregister": retained,
            "owner_device_modified": False,
            "forced_reinstall_or_running_remove_tested": False}


def main():
    try:
        result = remove()
    except (Refusal, native.Refusal, native.private.old.Refusal,
            clean.prior.Refusal, OSError, KeyError, ValueError, TypeError) as exc:
        print("STAGE2_NATIVE_REMOVE=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_NATIVE_REMOVE=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
