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
from stage2_source_revision import revision_from_makefile
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
VERSION = "0.6.2_" + REVISION
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


def run(args, timeout=120):
    try:
        return subprocess.run(args, check=False, capture_output=True,
                              text=True, timeout=timeout)
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
    need(isinstance(files, dict) and
         "/usr/local/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_handoff.py" in files,
         "NATIVE_PACKAGE_SHARED_FD9_TRANSPORT_FILE_MISSING")
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


def verify_installed_managed_cli(archive, expected_sha):
    """Run the actual installed inspection-only CLI and prove no pkg side effects."""
    path = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_managed.py")
    source = native.ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend/native_pkg_managed.py"
    need(path.is_file() and not path.is_symlink() and
         path.read_bytes() == source.read_bytes(),
         "INSTALLED_MANAGED_CLI_BYTES_UNQUALIFIED")
    original_pkgdb = required(["pkg", "info", "-R", "--raw-format", "json", NAME],
                              "INSTALLED_MANAGED_CLI_PKGDB_MISSING")
    config_before = Path("/conf/config.xml").read_bytes()
    cli = [sys.executable, "-B", str(path)]
    exact = cli + ["inspect-candidate", str(archive), VERSION, expected_sha]
    response = run(exact, timeout=135)
    need(response.returncode == 0 and
         response.stdout.startswith("ZAPRET2_MANAGED="),
         "INSTALLED_MANAGED_CLI_READ_ONLY_POSITIVE_UNQUALIFIED:" +
         str(response.returncode) + ":" + response.stderr[-160:])
    try:
        result = json.loads(response.stdout.split("ZAPRET2_MANAGED=", 1)[1])
    except ValueError:
        raise Refusal("INSTALLED_MANAGED_CLI_RESPONSE_NOT_JSON") from None
    need(result.get("status") == "PASS_MANAGED_READ_ONLY_INSPECTION" and
         result.get("archive_sha256") == expected_sha and
         type(result.get("worker_pid")) is int and result["worker_pid"] > 1 and
         type(result.get("original_fd9_inode")) is int and
         result["original_fd9_inode"] > 0 and
         result.get("pkg_invoked") is False and
         result.get("old_owner_qualified") is False and
         result.get("lh08_ac11_accepted") is False,
         "INSTALLED_MANAGED_INSPECT_FALSE_PKG_AUTHORIZATION")
    invalid = run(cli + ["inspect-candidate", str(archive), VERSION, "0" * 64],
                  timeout=30)
    need(invalid.returncode == 78 and
         "ZAPRET2_MANAGED=REFUSED:" in invalid.stderr,
         "INSTALLED_MANAGED_WRONG_SHA_NOT_REFUSED")
    forbidden = run(cli + ["upgrade", str(archive), VERSION, expected_sha],
                    timeout=20)
    need(forbidden.returncode == 78 and
         "UPGRADE_NOT_IMPLEMENTED_NO_PKG" in forbidden.stderr,
         "INSTALLED_MANAGED_UNSAFE_UPGRADE_COMMAND_ACCEPTED")
    fd = os.open("/var/run/zapret2-lifecycle.lock",
                 os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        busy = run(exact, timeout=25)
        need(busy.returncode == 78 and
             "ORIGINAL_FD9_BUSY_BEFORE_INSPECTION" in busy.stderr,
             "INSTALLED_MANAGED_BUSY_FD9_NOT_REFUSED")
    finally:
        os.close(fd)
    predecessor = run(cli + ["inspect-predecessor", str(archive), VERSION, expected_sha],
                      timeout=135)
    need(predecessor.returncode == 0 and
         predecessor.stdout.startswith("ZAPRET2_MANAGED="),
         "INSTALLED_MANAGED_PREDECESSOR_COLD_SCREEN_UNQUALIFIED:" +
         str(predecessor.returncode) + ":" + predecessor.stderr[-160:])
    try:
        old_state = json.loads(predecessor.stdout.split("ZAPRET2_MANAGED=", 1)[1])
    except ValueError:
        raise Refusal("INSTALLED_MANAGED_PREDECESSOR_NOT_JSON") from None
    need(old_state.get("status") == "PASS_MANAGED_READ_ONLY_PREDECESSOR_SCREEN" and
         old_state.get("predecessor_cold_screened") is True and
         old_state.get("old_owner_qualified") is False and
         old_state.get("pkg_invoked") is False and
         old_state.get("lh08_ac11_accepted") is False,
         "INSTALLED_MANAGED_PREDECESSOR_FALSE_ADMISSION")
    need(required(["pkg", "info", "-R", "--raw-format", "json", NAME],
                  "MANAGED_POST_INSPECT_PKGDB_MISSING") == original_pkgdb and
         Path("/conf/config.xml").read_bytes() == config_before and
         digest(archive) == expected_sha and
         path.read_bytes() == source.read_bytes(),
         "MANAGED_INSPECTION_MUTATED_PKGDB_CONFIG_OR_CANDIDATE")
    return {"status": "PASS_INSTALLED_MANAGED_READ_ONLY_CLI",
            "real_detached_worker_pid": result["worker_pid"],
            "original_fd9_continuous": True,
            "actual_installed_script_exercised": True,
            "wrong_digest_refused": True,
            "busy_original_fd9_refused": True,
            "upgrade_command_refused_before_pkg": True,
            "installed_predecessor_cold_screened_read_only": True,
            "pkgdb_and_config_unchanged": True,
            "pkg_invoked_by_managed_cli": False,
            "old_owner_qualified": False,
            "lh08_ac11_accepted": False}


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
    managed = verify_installed_managed_cli(path, require_sha)
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
            "installed_managed_inspection": managed,
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
