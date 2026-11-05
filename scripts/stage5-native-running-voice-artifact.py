#!/usr/bin/env python3
"""Stage 5: one actual native package across RUNNING upgrade and Voice HTTPS.

Source-only disposable OPNsense 26.7 qualification, NOT publication or final
all-feature acceptance. Reuses official Mk builder and installed Stage 2 tests.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

from stage2_source_revision import revision_from_makefile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REVISION = revision_from_makefile()
IDENTITY = "os-zapret2-restyle-0.6.2_" + REVISION
PACKAGE = ROOT / "dist" / (IDENTITY + ".pkg")
RECEIPT = ROOT / "dist" / "stage5-native-running-voice-artifact.json"
STATUS = "PASS_ONE_NATIVE_ARCHIVE_RUNNING_UPGRADE_SHARED_VOICE_HTTPS"
OPTIN = "ZAPRET2_STAGE5_RUNNING_VOICE_ARTIFACT"


class Refusal(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        "sha_running_voice_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def receipt_check(data, path, source_sha, *, verify_manifest=True):
    """Fail closed if the copied-back archive differs from the one installed."""
    need(isinstance(data, dict) and data.get("schema") == 1 and
         data.get("status") == STATUS and
         data.get("source_sha") == source_sha and
         isinstance(source_sha, str) and
         re.fullmatch(r"[a-f0-9]{40}", source_sha) is not None,
         "STAGE5_RUNNING_RECEIPT_SOURCE_OR_SCHEMA_MISMATCH")
    need(data.get("identity") == IDENTITY and
         data.get("filename") == PACKAGE.name and
         data.get("abi") == "FreeBSD:15:amd64" and
         data.get("revision") == REVISION,
         "STAGE5_RUNNING_RECEIPT_IDENTITY_OR_ABI_MISMATCH")
    need(all(data.get(flag) is True for flag in (
         "exact_old_running_to_native_pkg_replacement",
         "old_engine_processes_drained",
         "pkgdb_and_all_installed_file_bytes_verified",
         "original_four_hooks_equal",
         "shared_voice_original_fd9",
         "one_running_dvtws2",
         "python_down_shared_stop_refused",
         "stop_start_reuses_sealed_journal",
         "authenticated_https_voice_apply_and_restore",
         "stale_snapshot_refused",
         "native_config_model_restored",
         "unknown_plugin_xml_preserved",
         "loopback_only",
         "copyback_sha_required")) and
         data.get("published") is False and
         data.get("owner_device_changed") is False and
         data.get("all_feature_suites_qualified") is False,
         "STAGE5_RUNNING_RECEIPT_SCOPE_OR_GATES_INVALID")
    need(path == PACKAGE and path.is_file() and not path.is_symlink() and
         stat.S_ISREG(path.lstat().st_mode) and path.lstat().st_nlink == 1,
         "STAGE5_RUNNING_PACKAGE_PATH_UNQUALIFIED")
    digest = data.get("archive_sha256")
    need(isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest) and
         path.stat().st_size == data.get("archive_size_bytes") and
         sha256(path) == digest, "STAGE5_RUNNING_ARCHIVE_SHA_OR_BYTES_CHANGED")
    need(isinstance(data.get("installed_file_count"), int) and
         data["installed_file_count"] >= 200 and
         isinstance(data.get("manifest_sha256"), str) and
         re.fullmatch(r"[a-f0-9]{64}", data["manifest_sha256"]) and
         isinstance(data.get("engine_sha256"), str) and
         re.fullmatch(r"[a-f0-9]{64}", data["engine_sha256"]) and
         isinstance(data.get("native_deps"), list) and
         len(data["native_deps"]) == 7,
         "STAGE5_RUNNING_INSTALLED_RECEIPT_INVALID")
    if verify_manifest:
        standard = load("stage5-native-single-artifact.py")
        manifest, manhash = standard.read_manifest(path)
        need(manhash == data["manifest_sha256"] and
             manifest.get("name") == "os-zapret2-restyle" and
             manifest.get("version") == "0.6.2_" + REVISION and
             manifest.get("abi") == data["abi"] and
             isinstance(manifest.get("files"), dict) and
             len(manifest["files"]) == data["installed_file_count"] and
             sorted(manifest.get("deps", {})) == data["native_deps"] and
             set(manifest.get("scripts", {})) ==
             {"pre-install", "post-install", "pre-deinstall", "post-deinstall"},
             "STAGE5_RUNNING_MANIFEST_AND_INSTALLED_PKGDB_DIFFER")
    return digest


def cross_receipt_binding(clean, live):
    """Prove two independent disposable VM installations used identical bytes."""
    need(isinstance(clean, dict) and isinstance(live, dict) and
         clean.get("schema") == live.get("schema") == 1 and
         clean.get("status") == "PASS_STAGE5_ONE_NATIVE_PACKAGE_CLEAN_INSTALL_SHA_BOUND" and
         live.get("status") == STATUS and
         live.get("prebuilt_clean_install_same_archive") is True,
         "STAGE5_CROSS_TWO_GENUINE_RECEIPTS_REQUIRED")
    fields = (("project_sha", "source_sha"),
              ("archive_sha256", "archive_sha256"),
              ("manifest_sha256", "manifest_sha256"),
              ("archive_bytes", "archive_size_bytes"),
              ("checked_file_count", "installed_file_count"),
              ("native_dependencies", "native_deps"),
              ("revision", "revision"), ("identity", "identity"),
              ("abi", "abi"), ("filename", "filename"))
    for left, right in fields:
        need(clean.get(left) == live.get(right),
             "STAGE5_CROSS_ARCHIVE_OR_INSTALLED_FIELD_DIFFERENT:" + left)
    need(clean.get("genuine_clean_pkg_add") is True and
         clean.get("all_installed_package_files_equal") is True and
         clean.get("four_original_hooks_equal") is True and
         live.get("exact_old_running_to_native_pkg_replacement") is True and
         live.get("pkgdb_and_all_installed_file_bytes_verified") is True and
         live.get("authenticated_https_voice_apply_and_restore") is True and
         clean.get("owner_appliance_modified") is False and
         live.get("owner_device_changed") is False,
         "STAGE5_CROSS_BOTH_INSTALLATION_SCOPES_NOT_PROVEN")
    return clean["archive_sha256"]


def prebuilt_clean_receipt():
    need(os.environ.get("ZAPRET2_STAGE5_CROSS_VM") == "1",
         "STAGE5_CROSS_EXPLICIT_SECOND_GUEST_OPTIN_REQUIRED")
    standard = load("stage5-native-single-artifact.py")
    need(standard.RECEIPT.is_file() and not standard.RECEIPT.is_symlink(),
         "STAGE5_CROSS_FIRST_GUEST_RECEIPT_MISSING")
    try:
        record = json.loads(standard.RECEIPT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Refusal("STAGE5_CROSS_FIRST_GUEST_RECEIPT_INVALID") from None
    sha = standard.check_record(record, PACKAGE,
                                os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", ""))
    need(sha == record["archive_sha256"],
         "STAGE5_CROSS_ARCHIVE_SHA_MISMATCH_BEFORE_RUNNING")
    return record


def execute(old_archive, *, prebuilt_clean=False):
    required = ("GITHUB_ACTIONS", "ZAPRET2_NATIVE_BUILD_CI",
                "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_STAGE2_REAL_ACTIVE_SERVICE",
                "ZAPRET2_STAGE2_REAL_COMMON_VOICE",
                "ZAPRET2_STAGE2_REAL_VOICE_HTTP", OPTIN)
    for key in required:
        need(os.environ.get(key) == ("true" if key == "GITHUB_ACTIONS" else "1"),
             "STAGE5_RUNNING_DISPOSABLE_OPTIN_MISSING:" + key)
    running = load("stage2-opnsense-real-native-running-upgrade.py")
    running.require_disposable()
    running.clean.plugin_absent()
    running.stopped.check_old_archive(old_archive)
    need(not RECEIPT.exists() and not RECEIPT.is_symlink(),
         "STAGE5_RUNNING_RECEIPT_PREEXISTS")
    if prebuilt_clean:
        # A *different* fresh disposable OPNsense VM already built/installed
        # the exact archive, copied it back and rechecked it on the runner.
        # This second VM may ONLY consume that archive; never rebuild it.
        clean_record = prebuilt_clean_receipt()
        sha = clean_record["archive_sha256"]
        source_sha = running.native.git_head()
        need(source_sha == clean_record["project_sha"] and
             sha == sha256(PACKAGE),
             "STAGE5_CROSS_FIRST_GUEST_BYTES_OR_SOURCE_CHANGED")
        built = {"status": "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY",
                 "project_sha": source_sha,
                 "output": "dist/" + PACKAGE.name,
                 "real_native_pkg": {"sha256": sha}}
    else:
        need(not PACKAGE.exists() and not PACKAGE.is_symlink(),
             "STAGE5_RUNNING_PREEXISTING_PACKAGE_NOT_APPROVED")
        built = running.native.build()
    need(built.get("status") == "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY" and
         built.get("project_sha") == os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA") and
         running.native.ROOT / built["output"] == PACKAGE and
         built["real_native_pkg"]["sha256"] == sha256(PACKAGE),
         "STAGE5_RUNNING_SINGLE_NATIVE_MK_BUILD_UNQUALIFIED")
    archive_sha = built["real_native_pkg"]["sha256"]
    replacement = running.execute(old_archive, prebuilt_native_report=built)
    need(replacement.get("status") == "PASS_REAL_RUNNING_NATIVE_VERSION_REPLACEMENT" and
         replacement.get("new_temporary_pkg_sha256") == archive_sha and
         replacement.get("tested_exact_project_sha") == built["project_sha"] and
         replacement.get("installed_original_four_hooks_equal") is True and
         replacement.get("restored_runtime", {}).get("real_new_service_running") is True and
         replacement.get("restored_runtime", {}).get("old_processes_drained") is True and
         replacement.get("installed_files", {}).get("files_owned_by_real_pkgdb") is True and
         replacement.get("owner_appliance_modified") is False,
         "STAGE5_RUNNING_OLD_TO_NEW_INSTALL_WITNESS_FAILED")
    need(sha256(PACKAGE) == archive_sha, "STAGE5_RUNNING_ARCHIVE_CHANGED_AFTER_PKG_ADD")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    common_report = common.execute()
    need(common_report.get("status") == "PASS_REAL_INSTALLED_NATIVE_COMMON_VOICE" and
         common_report.get("original_fd9_common_journal_committed") is True and
         common_report.get("single_real_engine") is True and
         common_report.get("python_down_shared_stop_refused_before_mutation") is True and
         common_report.get("native_stop_start_restored_owner") is True and
         common_report.get("loopback_only") is True,
         "STAGE5_RUNNING_SHARED_VOICE_OWNER_REFUSED")
    http = load("stage2-opnsense-real-native-voice-http.py")
    https_report = http.execute()
    need(https_report.get("status") == "PASS_REAL_NATIVE_AUTHENTICATED_VOICE_HTTP_APPLY" and
         https_report.get("authenticated_native_http_api") is True and
         https_report.get("stale_snapshot_refused_before_mutation") is True and
         https_report.get("gui_apply_and_restore_committed_under_shared_fd9") is True and
         https_report.get("all_native_model_fields_restored") is True and
         https_report.get("unknown_plugin_xml_fields_unchanged") is True and
         https_report.get("loopback_only") is True,
         "STAGE5_RUNNING_REAL_HTTPS_VOICE_RECEIPT_REFUSED")
    need(sha256(PACKAGE) == archive_sha, "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_VOICE")
    # Recheck every on-disk package-owned file AFTER live service/Voice cycles.
    manifest, installed = running.clean.installed_pkg_manifest(PACKAGE)
    after = running.clean.verify_installed_files(PACKAGE, manifest)
    need(after["exact_installed_package_file_count"] ==
         replacement["installed_files"]["exact_installed_package_file_count"] and
         installed.get("deps") == replacement.get("native_dependencies"),
         "STAGE5_RUNNING_POST_VOICE_INSTALLED_FILES_CHANGED")
    active = load("stage2-opnsense-real-native-active-service.py")
    engine_sha = active.guest_preflight()
    state = common.witness(active, engine_sha, running=True)
    need(isinstance(state.get("pid"), int) and state["pid"] > 1 and
         len(state.get("rules", [])) == 2,
         "STAGE5_RUNNING_COMMON_FINAL_ENGINE_OR_IPFW_INVALID")
    standard = load("stage5-native-single-artifact.py")
    manifest, manifest_sha = standard.read_manifest(PACKAGE)
    report = {
        "schema": 1, "status": STATUS,
        "source_sha": built["project_sha"],
        "identity": IDENTITY, "filename": PACKAGE.name,
        "revision": REVISION, "abi": manifest["abi"],
        "archive_sha256": archive_sha, "archive_size_bytes": PACKAGE.stat().st_size,
        "manifest_sha256": manifest_sha,
        "native_deps": sorted(manifest["deps"]),
        "installed_file_count": after["exact_installed_package_file_count"],
        "engine_sha256": engine_sha,
        "exact_old_running_to_native_pkg_replacement": True,
        "old_engine_processes_drained": True,
        "pkgdb_and_all_installed_file_bytes_verified": True,
        "original_four_hooks_equal": True,
        "shared_voice_original_fd9": True,
        "one_running_dvtws2": True,
        "python_down_shared_stop_refused": True,
        "stop_start_reuses_sealed_journal": True,
        "authenticated_https_voice_apply_and_restore": True,
        "stale_snapshot_refused": True,
        "native_config_model_restored": True,
        "unknown_plugin_xml_preserved": True,
        "loopback_only": True, "copyback_sha_required": True,
        "published": False, "owner_device_changed": False,
        "all_feature_suites_qualified": False,
        "prebuilt_clean_install_same_archive": bool(prebuilt_clean),
        "browser_button_click_tested": False,
        "voice_media_tested": False,
        "real_wan_tested": False,
    }
    receipt_check(report, PACKAGE, built["project_sha"])
    RECEIPT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
    print("STAGE5_RUNNING_VOICE_ARTIFACT=" + json.dumps(report, sort_keys=True))
    return 0


def verify_copyback(source_sha):
    need(RECEIPT.is_file() and not RECEIPT.is_symlink(),
         "STAGE5_RUNNING_RECEIPT_NOT_COPIED_BACK")
    try:
        report = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise Refusal("STAGE5_RUNNING_RECEIPT_UNREADABLE") from None
    digest = receipt_check(report, PACKAGE, source_sha)
    print("PASS_STAGE5_RUNNING_VOICE_COPYBACK_SHA=" + digest)
    return 0


def verify_cross_copyback(source_sha):
    standard = load("stage5-native-single-artifact.py")
    need(RECEIPT.is_file() and not RECEIPT.is_symlink() and
         standard.RECEIPT.is_file() and not standard.RECEIPT.is_symlink(),
         "STAGE5_CROSS_COPYBACK_ONE_RECEIPT_MISSING")
    try:
        clean = json.loads(standard.RECEIPT.read_text(encoding="utf-8"))
        live = json.loads(RECEIPT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise Refusal("STAGE5_CROSS_COPYBACK_RECEIPT_NOT_JSON") from None
    standard.check_record(clean, PACKAGE, source_sha)
    receipt_check(live, PACKAGE, source_sha)
    sha = cross_receipt_binding(clean, live)
    print("PASS_STAGE5_ONE_ARCHIVE_TWO_DISPOSABLE_GUESTS_SHA=" + sha)
    return 0


def self_test():
    with tempfile.TemporaryDirectory(prefix="stage5-running-voice-negative-") as d:
        global PACKAGE
        initial = PACKAGE
        try:
            PACKAGE = Path(d) / initial.name
            PACKAGE.write_bytes(b"test-only-no-package-install")
            fixture = {
                "schema": 1, "status": STATUS,
                "source_sha": "a" * 40, "identity": IDENTITY,
                "filename": PACKAGE.name, "revision": REVISION,
                "abi": "FreeBSD:15:amd64",
                "archive_sha256": sha256(PACKAGE),
                "archive_size_bytes": PACKAGE.stat().st_size,
                "manifest_sha256": "b" * 64,
                "native_deps": list("abcdefg"),
                "installed_file_count": 292, "engine_sha256": "c" * 64,
                "published": False, "owner_device_changed": False,
                "all_feature_suites_qualified": False,
            }
            keys = ("exact_old_running_to_native_pkg_replacement",
                    "old_engine_processes_drained",
                    "pkgdb_and_all_installed_file_bytes_verified",
                    "original_four_hooks_equal",
                    "shared_voice_original_fd9", "one_running_dvtws2",
                    "python_down_shared_stop_refused",
                    "stop_start_reuses_sealed_journal",
                    "authenticated_https_voice_apply_and_restore",
                    "stale_snapshot_refused", "native_config_model_restored",
                    "unknown_plugin_xml_preserved", "loopback_only",
                    "copyback_sha_required")
            for key in keys:
                fixture[key] = True
            assert receipt_check(fixture, PACKAGE, "a" * 40, verify_manifest=False) == fixture["archive_sha256"]
            sample_clean = {
                "schema": 1, "status": "PASS_STAGE5_ONE_NATIVE_PACKAGE_CLEAN_INSTALL_SHA_BOUND",
                "project_sha": fixture["source_sha"],
                "archive_sha256": fixture["archive_sha256"],
                "manifest_sha256": fixture["manifest_sha256"],
                "archive_bytes": fixture["archive_size_bytes"],
                "checked_file_count": fixture["installed_file_count"],
                "native_dependencies": fixture["native_deps"],
                "revision": fixture["revision"], "identity": fixture["identity"],
                "abi": fixture["abi"], "filename": fixture["filename"],
                "genuine_clean_pkg_add": True, "all_installed_package_files_equal": True,
                "four_original_hooks_equal": True, "owner_appliance_modified": False,
            }
            fixture["prebuilt_clean_install_same_archive"] = True
            assert cross_receipt_binding(sample_clean, fixture) == fixture["archive_sha256"]
            for key, bad in (("archive_sha256", "f" * 64),
                             ("manifest_sha256", "f" * 64),
                             ("project_sha", "b" * 40),
                             ("archive_bytes", 1), ("checked_file_count", 1),
                             ("identity", "other-plugin"), ("genuine_clean_pkg_add", False)):
                broken = dict(sample_clean)
                broken[key] = bad
                try:
                    cross_receipt_binding(broken, fixture)
                except Refusal:
                    pass
                else:
                    raise AssertionError("cross-guest clean tamper accepted: " + key)
            fixture["prebuilt_clean_install_same_archive"] = False
            try:
                cross_receipt_binding(sample_clean, fixture)
            except Refusal:
                pass
            else:
                raise AssertionError("independent live rebuild misidentified as same archive")
            for key, value in (
                ("archive_sha256", "0" * 64), ("archive_size_bytes", 0),
                ("identity", "other"), ("native_deps", []),
                ("published", True), ("all_feature_suites_qualified", True),
                ("shared_voice_original_fd9", False),
                ("authenticated_https_voice_apply_and_restore", False),
                ("unknown_plugin_xml_preserved", False),
            ):
                changed = dict(fixture)
                changed[key] = value
                try:
                    receipt_check(changed, PACKAGE, "a" * 40, verify_manifest=False)
                except Refusal:
                    pass
                else:
                    raise AssertionError("tampered receipt accepted:" + key)
            try:
                receipt_check(fixture, PACKAGE, "f" * 40, verify_manifest=False)
            except Refusal:
                pass
            else:
                raise AssertionError("foreign source SHA accepted")
        finally:
            PACKAGE = initial
    print("PASS: same-archive RUNNING/Voice/HTTPS receipt and SHA tamper guards")
    return 0


def main():
    try:
        if sys.argv[1:] == ["--self-test"]:
            return self_test()
        if len(sys.argv) == 3 and sys.argv[1] == "run":
            return execute(Path(sys.argv[2]))
        if len(sys.argv) == 3 and sys.argv[1] == "run-prebuilt":
            return execute(Path(sys.argv[2]), prebuilt_clean=True)
        if len(sys.argv) == 3 and sys.argv[1] == "verify":
            return verify_copyback(sys.argv[2])
        if len(sys.argv) == 3 and sys.argv[1] == "verify-cross":
            return verify_cross_copyback(sys.argv[2])
        raise Refusal("STAGE5_RUNNING_USAGE_SELF_TEST_RUN_PREBUILT_VERIFY_CROSS")
    except (Refusal, OSError, KeyError, ValueError, TypeError) as e:
        print("STAGE5_RUNNING_VOICE_ARTIFACT=REFUSED:" + str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
