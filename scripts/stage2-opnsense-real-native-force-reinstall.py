#!/usr/bin/env python3
"""Actual same-version pkg add -f, STOPPED native owner, isolated OPNsense only.

The phase order and hook failure rollback remain unproven by this witness.
Do not run against an owner system. No package is published.
"""
import json
import os
from pathlib import Path
import sys

import importlib.util

HERE = Path(__file__).resolve().parent
REVISION = "80"
OPTIN = "ZAPRET2_STAGE2_REAL_SAME_VERSION_REINSTALL"


def load(name):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_").replace(".", "_"),
                                                  HERE / name)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


clean = load("stage2-opnsense-real-native-clean-install.py")
stopped = load("stage2-opnsense-real-native-stopped-upgrade.py")
native = clean.native


class Refusal(Exception):
    pass


def need(value, reason):
    if not value:
        raise Refusal(reason)


def preflight():
    need(os.environ.get(OPTIN) == "1" and
         os.environ.get("ZAPRET2_STAGE2_REAL_CLEAN_INSTALL") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true",
         "EXPLICIT_DISPOSABLE_SAME_VERSION_REINSTALL_OPTIN_REQUIRED")
    before = clean.preflight()  # actually checks native target, source and cold guest
    need(native.REVISION == REVISION and clean.REVISION == REVISION and
         stopped.REVISION == REVISION,
         "CURRENT_NATIVE_SOURCE_REVISIONS_MISMATCH")
    return before


def force_same_version(archive):
    """Real pkg command, original scripts enabled; no fake or script suppression."""
    result = clean.run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add",
                        "-f", str(archive)], timeout=240)
    need(result.returncode == 0,
         "GENUINE_FORCE_REINSTALL_PKG_NONZERO:" + str(result.returncode) +
         ":" + (result.stdout + result.stderr)[-380:])
    need("os-zapret2-restyle was installed." in result.stdout,
         "FORCE_REINSTALL_ORIGINAL_POSTINSTALL_SUCCESS_NOT_OBSERVED")
    need("Reinstalling" in result.stdout or "Installing" in result.stdout or
         "Upgrading" in result.stdout,
         "FORCE_REINSTALL_PKG_OPERATION_NOT_OBSERVED")
    return {"pkg_exit_zero": True, "postinstall_message_observed": True,
            "genuine_pkg_add_force": True, "same_version_not_upgraded": True}


def assert_cold():
    state = clean.cold_status()
    kernel = stopped.verify_cold_runtime()
    need(state["direct_service_status_exit"] == 1 and
         state["installed_runtime_started"] is False and
         kernel["no_plugin_processes_or_markers"] is True and
         kernel["no_ipfw_or_ipdivert_kernel_ownership"] is True,
         "FORCED_SAME_REVISION_RUNTIME_NOT_COLD")
    return {"real_direct_status_stopped": True,
            "no_restart_markers_or_processes": True,
            "no_ipfw_ipdivert_owner": True}


def execute():
    initial_xml = preflight()
    package = native.build()  # source-built official Mk, real private binary
    need(package["status"] == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY" and
         package["project_sha"] == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA"),
         "OFFICIAL_NATIVE_SOURCE_BUILD_NOT_PROVEN")
    path = native.ROOT / package["output"]
    sha = package["real_native_pkg"]["sha256"]
    need(path.is_file() and not path.is_symlink() and clean.digest(path) == sha,
         "NATIVE_ARCHIVE_BEFORE_FIRST_INSTALL_UNQUALIFIED")
    first = clean.pkg_add(path)
    manifest, installed = clean.installed_pkg_manifest(path)
    need(manifest["version"] == "0.6.2_" + REVISION,
         "FIRST_INSTALLED_NATIVE_PACKAGE_VERSION_MISMATCH")
    first_files = clean.verify_installed_files(path, manifest)
    need(first_files["exact_installed_package_file_count"] == 291,
         "FIRST_NATIVE_INSTALL_291_FILES_NOT_VERIFIED")
    first_cold = assert_cold()
    xml_after_first = Path("/conf/config.xml").read_bytes()
    first_registry = clean.verify_official_first_install_registration(
        initial_xml, xml_after_first)
    need(clean.digest(path) == sha, "ARCHIVE_CHANGED_AFTER_FIRST_INSTALL")

    second = force_same_version(path)
    need(clean.digest(path) == sha,
         "ARCHIVE_CHANGED_DURING_FORCED_REINSTALL")
    same_manifest, same_installed = clean.installed_pkg_manifest(path)
    need(same_manifest["version"] == manifest["version"] and
         same_installed["deps"] == installed["deps"] and
         same_manifest.get("scripts") == manifest.get("scripts"),
         "SAME_VERSION_PKGDB_HOOK_OR_PROVIDER_CHANGED")
    second_files = clean.verify_installed_files(path, same_manifest)
    second_cold = assert_cold()
    registry = stopped.prove_preserved_config(
        xml_after_first, Path("/conf/config.xml").read_bytes())
    return {"schema": 1, "status": "PASS_REAL_NATIVE_STOPPED_SAME_VERSION_FORCE_REINSTALL",
            "tested_exact_project_sha": package["project_sha"],
            "same_pkg_version_both_sides": clean.NAME + "-0.6.2_" + REVISION,
            "source_native_archive_sha256": sha,
            "actual_first_pkg": first,
            "actual_force_same_pkg": second,
            "first_native_owned_files": first_files,
            "postforce_native_owned_files": second_files,
            "original_four_pkgdb_scripts_byte_equal": True,
            "actual_native_dependencies": same_installed["deps"],
            "cold_before": first_cold,
            "cold_after": second_cold,
            "first_registry": first_registry,
            "config_preservation": registry,
            "same_version_force_true_native_pkg": True,
            "old_predeinstall_execution_proven": False,
            "root_pkg_failure_rollback_proven": False,
            "running_same_version_reinstall_tested": False,
            "safe_configd_worker_identity_tested": False,
            "stage0_closed": False, "owner_device_modified": False,
            "publication_approved": False}


def main():
    try:
        report = execute()
    except (Refusal, clean.Refusal, stopped.Refusal, native.Refusal,
            OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE2_FORCE_REINSTALL=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE2_FORCE_REINSTALL=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
