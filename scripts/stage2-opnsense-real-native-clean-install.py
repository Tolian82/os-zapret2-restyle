#!/usr/bin/env python3
"""Real FIRST CLEAN INSTALL of official native successor in disposable OPNsense.

Stage 2.23 bounded LH-01/LH-05 witness. Genuine pkg add and real hooks,
not a synthetic derived published archive. Never run on an owner appliance.
STOP before upgrade/RUNNING/faulted-removal; those are distinct acceptance.
"""
import hashlib
import fcntl
import importlib.util
import json
import os
from stage2_source_revision import revision_from_makefile, version_from_file
import copy
import re
from pathlib import Path
import stat
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
NAME = "os-zapret2-restyle"
REVISION = revision_from_makefile()
VERSION = version_from_file() + "_" + REVISION
OPTIN = "ZAPRET2_STAGE2_REAL_CLEAN_INSTALL"
PRESERVED = ("/var/run/zapret2-restyle/pkg-upgrade.restart",
             "/var/run/zapret2-restyle/pkg-replacement.restart",
             "/var/run/dvtws2.pid",
             "/var/run/zapret2-supervisor-daemon.pid",
             "/var/run/zapret2-supervisor-monitor.pid")


def load(filename, name):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


native = load("native-opnsense-package.py", "native_installed_candidate")
prior = load("stage0-installed-predecessor-readonly.py", "old_pkgdb_reader")


class Refusal(Exception):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def run(args, timeout=120, env=None):
    try:
        return subprocess.run(args, check=False, capture_output=True,
                              text=True, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("TARGET_COMMAND_UNAVAILABLE_OR_TIMEOUT:" + args[0]) from None


def required(args, reason, timeout=120):
    p = run(args, timeout=timeout)
    need(p.returncode == 0,
         reason + ":rc=" + str(p.returncode) + ":" + p.stderr[-260:])
    return p.stdout.strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plugin_absent():
    query = run(["pkg", "info", "-e", NAME], timeout=20)
    need(query.returncode == 1, "NONEMPTY_PLUGIN_PKGDB_BEFORE_CLEAN_INSTALL")
    root = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
    need(not root.exists() and not root.is_symlink(),
         "INSTALLED_SERVICE_ALREADY_EXISTS")
    for name in PRESERVED:
        p = Path(name)
        need(not p.exists() and not p.is_symlink(),
             "PREEXISTING_LIFECYCLE_MARKER:" + name)


def preflight():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true",
         "EXPLICIT_DISPOSABLE_REAL_PKG_INSTALL_OPTIN_REQUIRED")
    native.gate()  # original genuine KVM/OPNsense 26.7 identity
    need(native.REVISION == REVISION, "NATIVE_SOURCE_REVISION_NOT_CURRENT")
    plugin_absent()
    config = Path("/conf/config.xml")
    need(config.is_file() and not config.is_symlink(),
         "CLEAN_GUEST_OPNSENSE_CONFIG_MISSING")
    before = config.read_bytes()
    return before



def config_structure_diagnostic(before, after):
    """Redacted schema-only first-install delta: NEVER print XML values."""
    try:
        a = ET.fromstring(before)
        b = ET.fromstring(after)
    except ET.ParseError:
        return {"xml_schema_readable": False}
    if a.tag != b.tag:
        return {"root_tag_changed": True}
    changes = []
    aa = {x.tag: x for x in a}
    bb = {x.tag: x for x in b}
    for name in sorted(set(aa) | set(bb)):
        prior, current = aa.get(name), bb.get(name)
        if prior is not None and current is not None and (
                ET.tostring(prior) == ET.tostring(current)):
            continue
        if name in ("OPNsense", "installedpackages"):
            old_children = {e.tag: e for e in prior} if prior is not None else {}
            new_children = {e.tag: e for e in current} if current is not None else {}
            children = sorted(tag for tag in set(old_children) | set(new_children)
                              if tag not in old_children or tag not in new_children or
                              ET.tostring(old_children[tag]) !=
                              ET.tostring(new_children[tag]))
            # Do not expose arbitrary custom XML tags: enumerate only known
            # plugin sections. Unknown names become <redacted>.
            known = {"Zapret", "zapret2", "zapret", "firmware", "plugins"}
            changes.append({"section": name, "changed_children":
                            [x if x in known else "other" for x in children[:10]],
                            "child_count": len(children)})
        else:
            standard = {"system", "interfaces", "dhcpd", "unbound",
                        "filter", "nat", "widgets", "gateways"}
            changes.append({"section": name if name in standard else "other"})
    return {"xml_schema_readable": True, "changed_sections": changes[:20]}



def verify_official_first_install_registration(before, after):
    """Accept only what official register.php/Config::save() must modify.

    The genuine upstream register.php adds the native package name into
    system/firmware/plugins and Config::save() refreshes root revision.
    All other user configuration must be preserved semantically.
    """
    need(before != after, "OFFICIAL_PLUGIN_REGISTRATION_NOT_PERSISTED")
    try:
        old = ET.fromstring(before)
        new = ET.fromstring(after)
    except ET.ParseError:
        raise Refusal("REGISTERED_CONFIG_NOT_WELL_FORMED_XML") from None
    need(old.tag == "opnsense" and new.tag == "opnsense",
         "REGISTERED_OPNSENSE_CONFIG_ROOT_WRONG")
    original_firmware = old.find("system/firmware")
    installed_firmware = new.find("system/firmware")
    need(installed_firmware is not None and
         old.find("system") is not None and
         new.find("system") is not None,
         "FIRMWARE_PLUGIN_REGISTRY_MISSING")
    original_plugin_nodes = (original_firmware.findall("plugins")
                             if original_firmware is not None else [])
    current_plugin_nodes = installed_firmware.findall("plugins")
    need(len(original_plugin_nodes) <= 1 and len(current_plugin_nodes) == 1,
         "PLUGIN_REGISTRY_AMBIGUOUS")
    original_names = [
        x for x in (original_plugin_nodes[0].text or "").split(",") if x
    ] if original_plugin_nodes else []
    current_names = [x for x in (current_plugin_nodes[0].text or "").split(",") if x]
    need(NAME not in original_names and
         len(original_names) == len(set(original_names)) and
         current_names == sorted([*original_names, NAME]),
         "INSTALL_PLUGIN_REGISTRY_ADDED_OR_REMOVED_FOREIGN_ENTRIES")
    prior_type = (original_firmware.find("type")
                  if original_firmware is not None else None)
    current_types = installed_firmware.findall("type")
    added_type = False
    if prior_type is None:
        need(len(current_types) <= 1, "FIRMWARE_TYPE_AMBIGUOUS")
        if current_types:
            kind = current_types[0].text or ""
            need(re.fullmatch(r"[a-zA-Z0-9_-]{0,24}", kind) is not None,
                 "FIRMWARE_TYPE_UNQUALIFIED")
            added_type = True
    else:
        need(len(current_types) == 1 and
             ET.tostring(current_types[0]) == ET.tostring(prior_type),
             "EXISTING_FIRMWARE_TYPE_WAS_CHANGED")

    def normalize(root, remove_new_type):
        root = copy.deepcopy(root)
        revisions = root.findall("revision")
        need(len(revisions) <= 1, "CONFIG_REVISION_SECTION_AMBIGUOUS")
        for node in revisions:
            root.remove(node)
        system = root.find("system")
        fw = system.find("firmware") if system is not None else None
        if fw is not None:
            for el in fw.findall("plugins"):
                fw.remove(el)
            if remove_new_type:
                for el in fw.findall("type"):
                    fw.remove(el)
            # An absent firmware container is legitimately created by
            # register.php, but only its two known fields may be present.
            if len(fw) == 0 and not fw.attrib and not (fw.text or "").strip():
                system.remove(fw)
        def strip_formatting(el):
            if not (el.text or "").strip():
                el.text = None
            el.tail = None
            for child in el:
                strip_formatting(child)
        strip_formatting(root)
        return ET.tostring(root, encoding="utf-8")

    prior_normal = normalize(old, prior_type is None)
    actual_normal = normalize(new, added_type)
    need(prior_normal == actual_normal,
         "UNAUTHORIZED_CONFIG_MUTATION_BEYOND_OFFICIAL_REGISTRATION:" +
         json.dumps(config_structure_diagnostic(before, after),
                    sort_keys=True))
    return {"status": "PASS_OFFICIAL_FIRMWARE_REGISTER_ONLY",
            "registered_exact_new_plugin": NAME,
            "prior_plugin_count": len(original_names),
            "all_other_plugins_preserved": True,
            "allowed_new_firmware_type": added_type,
            "config_revision_metadata_updated": True,
            "all_other_config_sections_unchanged": True}


def pkg_add(archive):
    # No force, no -I, no --script-no-exec, no global FreeBSD repo override.
    # Real PRE_INSTALL and POST_INSTALL must run against clean OPNsense.
    result = run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add", str(archive)],
                 timeout=210)
    need(result.returncode == 0,
         "GENUINE_NATIVE_CLEAN_PKG_ADD_FAILED:rc=" +
         str(result.returncode) + ":" +
         (result.stdout + result.stderr)[-950:])
    need("os-zapret2-restyle was installed." in result.stdout,
         "ORIGINAL_POST_INSTALL_MESSAGE_NOT_OBSERVED")
    return {"pkg_returncode": result.returncode,
            "postinstall_success_message": True}


def installed_pkg_manifest(archive):
    archive_manifest = json.loads(
        required(["tar", "-xOf", str(archive), "+MANIFEST"],
                 "BUILT_NATIVE_MANIFEST_READ_FAILED"))
    raw = required(["pkg", "info", "-R", "--raw-format", "json", NAME],
                   "ACTUAL_INSTALLED_PKGDB_UNAVAILABLE")
    installed = prior.installed_manifest_from_json(raw)
    for key in ("name", "version", "origin", "arch"):
        need(installed.get(key) == archive_manifest.get(key),
             "INSTALLED_PKGDB_FIELD_CHANGED:" + key)
    if "abi" in installed:
        need(installed["abi"] == archive_manifest["abi"],
             "INSTALLED_NATIVE_ABI_CHANGED")
    need(installed.get("deps") == archive_manifest.get("deps"),
         "INSTALLED_REAL_DEPENDENCIES_DIFFER_FROM_ARCHIVE")
    scripts = archive_manifest.get("scripts", {})
    need(isinstance(scripts, dict) and
         set(scripts) == set(native.HOOKS.values()) and
         installed.get("scripts") == scripts,
         "INSTALLED_PKGDB_FOUR_AUTHENTIC_HOOKS_MISMATCH")
    return archive_manifest, installed


def verify_installed_files(archive, manifest):
    files = manifest.get("files")
    need(isinstance(files, dict) and bool(files),
         "NATIVE_PACKAGE_INSTALLED_MANIFEST_MISSING")
    tar_names = required(["tar", "-tf", str(archive)], "TAR_LIST_FAILED").splitlines()
    checked = 0
    for name in files:
        need(name.startswith("/usr/local/") and ".." not in Path(name).parts,
             "INSTALLED_MANIFEST_PATH_UNSAFE")
        member = native.private.old.exact_installed_tar_member(
            tar_names, name.removeprefix("/usr/local/"))
        expected_bytes = native.command(["tar", "-xOf", str(archive), member],
                                        timeout=30)
        local = Path(name)
        info = local.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_nlink >= 1,
             "INSTALLED_NOT_REGULAR:" + name)
        need(local.read_bytes() == expected_bytes,
             "INSTALLED_PAYLOAD_MISMATCH:" + name)
        actual_owner = required(["pkg", "which", "-q", name],
                                "PKG_FILE_OWNERSHIP_UNQUALIFIED")
        need(actual_owner in (NAME, NAME + "-" + VERSION),
             "INSTALLED_PKG_FILE_NOT_OWNED_BY_CANDIDATE:" + name)
        checked += 1
    for rel in (native.SERVICE, native.BINARY, native.LAUNCHER,
                "libexec/zapret2-restyle/check-curl-impersonate.sh"):
        p = Path("/usr/local") / rel
        need(stat.S_IMODE(p.lstat().st_mode) == 0o755,
             "INSTALLED_EXECUTABLE_NOT_0755:" + rel)
    # Stage 1.05 requires actual installed bytes, not merely a pkgdb path.
    policy_path = Path("/usr/local") / native.POLICY_DEST
    policy_bytes = (native.ROOT / "compatibility.json").read_bytes()
    need(policy_path.read_bytes() == policy_bytes and
         "/usr/local/" + native.POLICY_DEST in files,
         "POLICY_INSTALLED_BYTES_MISMATCH")
    need(checked == len(files), "INSTALLED_FILES_COUNT_MISMATCH")
    return {"exact_installed_package_file_count": checked,
            "files_owned_by_real_pkgdb": True,
            "compatibility_installed_equals_source": True,
            "compatibility_sha256": hashlib.sha256(policy_bytes).hexdigest(),
            "source_service_mode": "0755",
            "installed_private_executables_mode": "0755"}


def cold_status():
    service = Path("/usr/local") / native.SERVICE
    p = run([str(service), "status"], timeout=25)
    need(p.returncode == 1 and p.stdout.strip() ==
         "zapret is not running",
         "REAL_FRESH_INSTALLED_SERVICE_NOT_STOPPED:" +
         str(p.returncode) + ":" + (p.stdout + p.stderr)[-180:])
    for name in PRESERVED:
        x = Path(name)
        need(not x.exists() and not x.is_symlink(),
             "FRESH_PKG_LEFT_RESTART_OR_RUNTIME_OWNER:" + name)
    return {"direct_service_status_exit": p.returncode,
            "direct_service_status": p.stdout.strip(),
            "installed_runtime_started": False}


def python_down_installed_cold_status():
    """Only isolated OPNsense: no engine, no shared owner, deliberately broken
    Python launcher. Full RUNNING native owner acceptance is a separate gate."""
    service = Path("/usr/local") / native.SERVICE
    environment = dict(os.environ)
    environment["PYTHON_RUNTIME"] = "/nonexistent/zapret2-qualified-python-test"
    before_config = Path("/conf/config.xml").read_bytes()
    for action, expected_code, expected_output in (
        ("status", 1, "zapret is not running"),
        ("stop", 0, "zapret is not running (stopped)"),
        ("status", 1, "zapret is not running"),
    ):
        result = run([str(service), action], timeout=25, env=environment)
        need(result.returncode == expected_code and
             result.stdout.strip() == expected_output,
             "NATIVE_PYTHON_DOWN_COLD_" + action.upper() + "_FAILED:" +
             str(result.returncode) + ":" + (result.stdout + result.stderr)[-180:])
    start = run([str(service), "start"], timeout=25, env=environment)
    need(start.returncode == 69 and
         "python" in start.stderr.lower() and not start.stdout.strip(),
         "NATIVE_PYTHON_DOWN_START_DID_NOT_REFUSE_BEFORE_MUTATION:" +
         str(start.returncode) + ":" + (start.stdout + start.stderr)[-180:])
    need(Path("/conf/config.xml").read_bytes() == before_config,
         "NATIVE_PYTHON_DOWN_START_CHANGED_CONFIG")
    for name in PRESERVED:
        x = Path(name)
        need(not x.exists() and not x.is_symlink(),
             "NATIVE_PYTHON_DOWN_COLD_CREATED_OWNER:" + name)
    return {"native_python_down_cold_status": "STOPPED",
            "native_python_down_cold_stop": "IDEMPOTENT",
            "native_python_down_cold_start": "REFUSED_BEFORE_MUTATION",
            "native_python_down_running_owner_tested": False,
            "native_python_down_shared_owner_tested": False}


def execute():
    config_before = preflight()
    package = native.build()
    need(package["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY" and
         package["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA") and
         package["stage0_closed"] is False and
         package["publication_approved"] is False,
         "REAL_NATIVE_BUILDER_UNQUALIFIED")
    path = native.ROOT / package["output"]
    require_sha = package["real_native_pkg"]["sha256"]
    need(path.is_file() and not path.is_symlink() and digest(path) == require_sha,
         "PACKAGE_CHANGED_BEFORE_GENUINE_PKG_ADD")
    manifest_before = json.loads(
        required(["tar", "-xOf", str(path), "+MANIFEST"], "PREINSTALL_ARCHIVE_READ_FAILED"))
    need(manifest_before["version"] == VERSION and
         manifest_before["name"] == NAME and
         manifest_before["abi"] == native.qualified_target()["freebsd_pkg_abi"] and
         set(manifest_before.get("scripts", {})) == set(native.HOOKS.values()),
         "PREINSTALL_NATIVE_PACKAGE_IDENTITY_FAILED")
    installation = pkg_add(path)
    need(digest(path) == require_sha, "PACKAGE_CHANGED_DURING_INSTALL")
    manifest, pkgdb = installed_pkg_manifest(path)
    files = verify_installed_files(path, manifest)
    service = cold_status()
    python_down = python_down_installed_cold_status()
    config_after = Path("/conf/config.xml").read_bytes()
    registration = verify_official_first_install_registration(config_before,
                                                              config_after)
    return {"schema": 1,
            "status": "PASS_REAL_OFFICIAL_NATIVE_CLEAN_INSTALL",
            "tested_exact_project_sha": package["project_sha"],
            "framework_sha": package["framework_sha"],
            "package": NAME + "-" + VERSION,
            "source_only_package_sha256": require_sha,
            "real_pkg_add": installation,
            "real_native_pkgdb_and_original_hook_bodies_equal": True,
            "real_4_hook_bodies_recorded": True,
            "fresh_install_executed_pre_and_post_install": True,
            "predeinstall_and_postdeinstall_executed": False,
            "native_dependencies": pkgdb["deps"],
            "installed_payload": files,
            "service": service,
            "python_down_installed_cold": python_down,
            "opnsense_config_registry": registration,
            "installed_elf_sha256": digest(
                Path("/usr/local") / native.BINARY),
            "private_elf_digest_matched_signed_source": True,
            "owner_device_modified": False,
            "installed_successor_fresh_only": True,
            "old_predecessor_replacement_tested": False,
            "running_replacement_tested": False,
            "forced_reinstall_tested": False,
            "configctl_start_stop_tested": False,
            "rollback_and_failure_recovery_tested": False,
            "publication_approved": False,
            "stage0_closed": False, "stage1_admitted": False}


def main():
    try:
        report = execute()
    except (Refusal, native.Refusal, native.private.old.Refusal,
            prior.Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE2_REAL_INSTALLED=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_REAL_INSTALLED=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
