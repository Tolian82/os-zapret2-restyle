#!/usr/bin/env python3
"""Stage 5: one native Mk package, one SHA-256, genuine installed witness.

This is a source-only CI artifact and clean-install qualification on a
disposable OPNsense 26.7 VM. It does NOT approve publication, replace the
final running/upgrade matrix, or authorize any owner-device operation.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from stage2_source_revision import revision_from_makefile

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
REVISION = revision_from_makefile()
IDENTITY = "os-zapret2-restyle-0.6.2_" + REVISION
ARCHIVE = ROOT / "dist" / (IDENTITY + ".pkg")
RECEIPT = ROOT / "dist" / "stage5-native-single-artifact.json"
SERVICES_ONLY = "PASS_STAGE5_ONE_NATIVE_PACKAGE_CLEAN_INSTALL_SHA_BOUND"


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_manifest(path):
    try:
        result = subprocess.run(["tar", "-xOf", str(path), "+MANIFEST"],
                                capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("STAGE5_ARCHIVE_MANIFEST_TOOL_UNAVAILABLE") from None
    need(result.returncode == 0 and len(result.stdout) <= 4 * 1024 * 1024,
         "STAGE5_ARCHIVE_MANIFEST_UNREADABLE")
    try:
        obj = json.loads(result.stdout)
    except ValueError:
        raise Refusal("STAGE5_ARCHIVE_MANIFEST_INVALID_JSON") from None
    need(isinstance(obj, dict), "STAGE5_ARCHIVE_MANIFEST_NOT_OBJECT")
    return obj, digest(result.stdout)


def check_record(record, package, source_sha, *, manifest=True):
    """Portable post-copyback witness for the EXACT installed archive bytes."""
    need(isinstance(record, dict) and record.get("schema") == 1 and
         record.get("status") == SERVICES_ONLY, "STAGE5_RECEIPT_SCHEMA_OR_STATUS")
    need(isinstance(source_sha, str) and
         re.fullmatch(r"[0-9a-f]{40}", source_sha) is not None and
         record.get("project_sha") == source_sha,
         "STAGE5_PROJECT_HEAD_DIFFERENT")
    need(record.get("identity") == IDENTITY and
         record.get("filename") == ARCHIVE.name and
         record.get("revision") == REVISION and
         record.get("abi") == "FreeBSD:15:amd64",
         "STAGE5_NATIVE_PACKAGE_IDENTITY_CHANGED")
    need(record.get("genuine_clean_pkg_add") is True and
         record.get("pkgdb_manifest_equal") is True and
         record.get("all_installed_package_files_equal") is True and
         record.get("four_original_hooks_equal") is True and
         record.get("native_service_cold_qualified") is True and
         record.get("same_archive_stopped_force_reinstall") is True and
         record.get("same_archive_reinstall_config_preserved") is True and
         record.get("same_archive_reinstall_pkgdb_hooks_equal") is True and
         record.get("same_archive_reinstall_payload_and_cold_equal") is True and
         record.get("owner_appliance_modified") is False and
         record.get("publication_approved") is False and
         record.get("final_lifecycle_matrix_qualified") is False,
         "STAGE5_PKGDB_OR_SCOPE_WITNESS_MISSING")
    sha = record.get("archive_sha256")
    need(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha) is not None,
         "STAGE5_ARCHIVE_SHA_INVALID")
    need(package == ARCHIVE and package.is_file() and
         not package.is_symlink() and stat.S_ISREG(package.lstat().st_mode) and
         package.lstat().st_nlink == 1,
         "STAGE5_NATIVE_ARCHIVE_MISSING_OR_NONREGULAR")
    need(package.stat().st_size == record.get("archive_bytes") and
         digest(package.read_bytes()) == sha,
         "STAGE5_COPIED_PACKAGE_SHA_OR_LENGTH_DIFFERENT")
    need(isinstance(record.get("manifest_sha256"), str) and
         re.fullmatch(r"[0-9a-f]{64}", record["manifest_sha256"]) is not None,
         "STAGE5_MANIFEST_SHA_INVALID")
    need(isinstance(record.get("checked_file_count"), int) and
         record["checked_file_count"] > 0 and
         isinstance(record.get("installed_elf_sha256"), str) and
         re.fullmatch(r"[0-9a-f]{64}", record["installed_elf_sha256"]) is not None,
         "STAGE5_INSTALLED_FILE_OR_ELF_WITNESS_MISSING")
    need(isinstance(record.get("native_dependencies"), list) and
         len(record["native_dependencies"]) == 7 and
         all(isinstance(x, str) and x for x in record["native_dependencies"]),
         "STAGE5_NATIVE_DEPENDENCY_RECEIPT_INVALID")
    if manifest:
        obj, manifest_sha = read_manifest(package)
        need(manifest_sha == record["manifest_sha256"] and
             obj.get("name") == "os-zapret2-restyle" and
             obj.get("version") == "0.6.2_" + REVISION and
             obj.get("abi") == "FreeBSD:15:amd64" and
             isinstance(obj.get("files"), dict) and
             len(obj["files"]) == record["checked_file_count"] and
             sorted(obj.get("deps", {})) == record["native_dependencies"] and
             set(obj.get("scripts", {})) ==
             {"pre-install", "post-install", "pre-deinstall", "post-deinstall"},
             "STAGE5_COPYBACK_MANIFEST_NOT_INSTALLED_IDENTITY")
    return sha



def prove_same_archive_stopped_reinstall(clean, first):
    """Qualify genuine STOPPED stock pkg add -f on the exact native archive.

    Called only after clean.execute() has verified the disposable OPNsense
    guest, checked-out project SHA and real clean Mk package installation.
    """
    need(os.environ.get("ZAPRET2_STAGE5_SAME_ARCHIVE_FORCE_REINSTALL") == "1",
         "STAGE5_SAME_ARCHIVE_FORCE_REINSTALL_DISPOSABLE_OPTIN_REQUIRED")
    need(ARCHIVE.is_file() and not ARCHIVE.is_symlink(),
         "STAGE5_REINSTALL_ORIGINAL_ARCHIVE_MISSING")
    sha = digest(ARCHIVE.read_bytes())
    need(sha == first["source_only_package_sha256"],
         "STAGE5_REINSTALL_PRE_ARCHIVE_SHA_DIFFERENT")
    before_xml = Path("/conf/config.xml").read_bytes()
    before_manifest, _ = clean.installed_pkg_manifest(ARCHIVE)

    spec = importlib.util.spec_from_file_location(
        "stage5_native_same_archive_reinstall",
        HERE / "stage2-opnsense-real-native-force-reinstall.py")
    force = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(force)
    need(force.REVISION == REVISION and force.clean.REVISION == REVISION and
         force.stopped.REVISION == REVISION,
         "STAGE5_REINSTALL_SOURCE_REVISION_MISMATCH")
    force.assert_cold()
    operation = force.force_same_version(ARCHIVE)  # stock pkg add -f, scripts on
    need(operation.get("genuine_pkg_add_force") is True and
         operation.get("postinstall_message_observed") is True,
         "STAGE5_REINSTALL_STOCK_PKG_OPERATION_NOT_PROVEN")
    after_manifest, _ = clean.installed_pkg_manifest(ARCHIVE)
    need(after_manifest == before_manifest and
         set(after_manifest.get("scripts", {})) ==
         {"pre-install", "post-install", "pre-deinstall", "post-deinstall"},
         "STAGE5_REINSTALL_PKGDB_MANIFEST_OR_HOOKS_DIFFERENT")
    files = clean.verify_installed_files(ARCHIVE, after_manifest)
    need(files.get("exact_installed_package_file_count") ==
         first["installed_payload"]["exact_installed_package_file_count"] and
         files.get("files_owned_by_real_pkgdb") is True,
         "STAGE5_REINSTALL_INSTALLED_PAYLOAD_DIFFERENT")
    force.assert_cold()
    config = force.stopped.prove_preserved_config(
        before_xml, Path("/conf/config.xml").read_bytes())
    need(config.get("all_non_registry_config_preserved") is True and
         config.get("plugin_name_registered") is True,
         "STAGE5_REINSTALL_SAVED_CONFIG_DIFFERENT")
    need(digest(ARCHIVE.read_bytes()) == sha,
         "STAGE5_REINSTALL_ARCHIVE_BYTES_CHANGED")
    return {
        "same_archive_stopped_force_reinstall": True,
        "same_archive_reinstall_config_preserved": True,
        "same_archive_reinstall_pkgdb_hooks_equal": True,
        "same_archive_reinstall_payload_and_cold_equal": True,
    }


def installed_run():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_STAGE5_SINGLE_ARTIFACT") == "1" and
         os.environ.get("ZAPRET2_STAGE2_REAL_CLEAN_INSTALL") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "STAGE5_DISPOSABLE_INSTALLED_TEST_OPTIN_REQUIRED")
    spec = importlib.util.spec_from_file_location(
        "stage5_real_clean_install", HERE / "stage2-opnsense-real-native-clean-install.py")
    clean = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(clean)
    result = clean.execute()
    need(result.get("status") == "PASS_REAL_OFFICIAL_NATIVE_CLEAN_INSTALL" and
         result.get("installed_successor_fresh_only") is True and
         result.get("owner_device_modified") is False and
         result.get("publication_approved") is False and
         result.get("real_native_pkgdb_and_original_hook_bodies_equal") is True and
         result.get("private_elf_digest_matched_signed_source") is True and
         result.get("installed_payload", {}).get("files_owned_by_real_pkgdb") is True and
         result.get("service", {}).get("installed_runtime_started") is False,
         "STAGE5_GENUINE_CLEAN_INSTALL_RECEIPT_REFUSED")
    need(not RECEIPT.exists() and not RECEIPT.is_symlink(),
         "STAGE5_RECEIPT_ALREADY_PRESENT")
    reinstall = prove_same_archive_stopped_reinstall(clean, result)
    artifact_sha = result["source_only_package_sha256"]
    manifest, manifest_sha = read_manifest(ARCHIVE)
    receipt = {
        "schema": 1,
        "status": SERVICES_ONLY,
        "project_sha": result["tested_exact_project_sha"],
        "framework_sha": result["framework_sha"],
        "identity": IDENTITY,
        "filename": ARCHIVE.name,
        "revision": REVISION,
        "abi": manifest["abi"],
        "archive_sha256": artifact_sha,
        "archive_bytes": ARCHIVE.stat().st_size,
        "manifest_sha256": manifest_sha,
        "native_dependencies": sorted(manifest["deps"]),
        "checked_file_count": result["installed_payload"]["exact_installed_package_file_count"],
        "installed_elf_sha256": result["installed_elf_sha256"],
        "genuine_clean_pkg_add": True,
        "pkgdb_manifest_equal": True,
        "all_installed_package_files_equal": True,
        "four_original_hooks_equal": True,
        "native_service_cold_qualified": True,
        **reinstall,
        "owner_appliance_modified": False,
        "publication_approved": False,
        "final_lifecycle_matrix_qualified": False,
        "release_or_pages_published": False,
    }
    check_record(receipt, ARCHIVE, result["tested_exact_project_sha"])
    RECEIPT.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n",
                       encoding="utf-8")
    need(RECEIPT.is_file() and not RECEIPT.is_symlink(),
         "STAGE5_ATTESTATION_NOT_REGULAR")
    print("STAGE5_SINGLE_ARTIFACT=" + json.dumps(receipt, sort_keys=True))
    return 0


def verified_copyback(source_sha):
    need(RECEIPT.is_file() and not RECEIPT.is_symlink(),
         "STAGE5_COPIED_RECEIPT_MISSING")
    try:
        record = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise Refusal("STAGE5_COPIED_RECEIPT_INVALID") from None
    sha = check_record(record, ARCHIVE, source_sha)
    print("PASS_STAGE5_COPIED_ARTIFACT_SHA=" + sha)
    return 0


def self_test():
    # The SHA, source identity, scope and receipt cannot be interchanged.
    with tempfile.TemporaryDirectory(prefix="stage5-self-test-") as d:
        global ARCHIVE
        original = ARCHIVE
        try:
            ARCHIVE = Path(d) / original.name
            ARCHIVE.write_bytes(b"disposable-package-archive-test-only")
            record = {
                "schema": 1, "status": SERVICES_ONLY,
                "project_sha": "a" * 40, "identity": IDENTITY,
                "filename": ARCHIVE.name, "revision": REVISION,
                "abi": "FreeBSD:15:amd64",
                "archive_sha256": digest(ARCHIVE.read_bytes()),
                "archive_bytes": ARCHIVE.stat().st_size,
                "manifest_sha256": "b" * 64,
                "native_dependencies": list("abcdefg"),
                "checked_file_count": 1, "installed_elf_sha256": "c" * 64,
                "genuine_clean_pkg_add": True, "pkgdb_manifest_equal": True,
                "all_installed_package_files_equal": True,
                "four_original_hooks_equal": True, "native_service_cold_qualified": True,
                "same_archive_stopped_force_reinstall": True,
                "same_archive_reinstall_config_preserved": True,
                "same_archive_reinstall_pkgdb_hooks_equal": True,
                "same_archive_reinstall_payload_and_cold_equal": True,
                "owner_appliance_modified": False, "publication_approved": False,
                "final_lifecycle_matrix_qualified": False,
            }
            assert check_record(record, ARCHIVE, "a" * 40, manifest=False) == record["archive_sha256"]
            for field, bad in (("archive_sha256", "0" * 64),
                               ("archive_bytes", 1),
                               ("genuine_clean_pkg_add", False),
                               ("same_archive_stopped_force_reinstall", False),
                               ("same_archive_reinstall_config_preserved", False),
                               ("same_archive_reinstall_pkgdb_hooks_equal", False),
                               ("same_archive_reinstall_payload_and_cold_equal", False),
                               ("publication_approved", True),
                               ("final_lifecycle_matrix_qualified", True),
                               ("identity", "foreign-plugin"),
                               ("native_dependencies", [])):
                altered = dict(record)
                altered[field] = bad
                try:
                    check_record(altered, ARCHIVE, "a" * 40, manifest=False)
                except Refusal:
                    pass
                else:
                    raise AssertionError("field tampering accepted: " + field)
            try:
                check_record(record, ARCHIVE, "f" * 40, manifest=False)
            except Refusal:
                pass
            else:
                raise AssertionError("foreign head accepted")
        finally:
            ARCHIVE = original
    saved = os.environ.pop("ZAPRET2_STAGE5_SAME_ARCHIVE_FORCE_REINSTALL", None)
    try:
        try:
            prove_same_archive_stopped_reinstall(None, {})
        except Refusal as exc:
            assert "DISPOSABLE_OPTIN_REQUIRED" in str(exc)
        else:
            raise AssertionError("native reinstall allowed without opt-in")
    finally:
        if saved is not None:
            os.environ["ZAPRET2_STAGE5_SAME_ARCHIVE_FORCE_REINSTALL"] = saved
    print("PASS: native single archive digest, head, reinstall and tamper negatives")
    return 0


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if sys.argv[1:] == ["run"]:
            return installed_run()
        if len(sys.argv) == 3 and sys.argv[1] == "verify":
            return verified_copyback(sys.argv[2])
        raise Refusal("STAGE5_USAGE_SELF_TEST_RUN_OR_VERIFY_HEAD")
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("STAGE5_SINGLE_ARTIFACT=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
