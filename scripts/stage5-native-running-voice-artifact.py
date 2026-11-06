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
         "installed_exclude_backend_suites",
         "installed_exclude_preserves_native_owner",
         "installed_authenticated_exclude_apply_restore",
         "installed_native_authenticated_extra_remove",
         "installed_native_authenticated_extra_install",
         "installed_strategy_lab_idle_and_invalid_refused",
         "installed_extra_resources_offline_suites",
         "installed_lab_extra_preserves_native_owner",
         "installed_lab_mocked_job_e2e",
         "installed_resource_transaction_regressions",
         "installed_functional_owner_preserved",
         "installed_authenticated_lab_extra_http_status",
         "installed_authenticated_web_owner_preserved",
         "loopback_only",
         "copyback_sha_required")) and
         data.get("published") is False and
         data.get("owner_device_changed") is False and
         data.get("all_feature_suites_qualified") is False,
         "STAGE5_RUNNING_RECEIPT_SCOPE_OR_GATES_INVALID")
    install_scope = load("stage5-installed-extra-install-http.py")
    need(data.get("extra_install_source_commit") == install_scope.SOURCE_REVISION and
         isinstance(data.get("extra_install_catalog_content_sha256"), str) and
         re.fullmatch(r"[a-f0-9]{64}", data["extra_install_catalog_content_sha256"]) and
         type(data.get("extra_install_owned_count")) is int and
         0 < data["extra_install_owned_count"] <= 73,
         "STAGE5_RUNNING_EXTRA_INSTALL_PIN_AND_CONTENT_NOT_ATTESTED")
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
         live.get("installed_exclude_backend_suites") is True and
         live.get("installed_exclude_preserves_native_owner") is True and
         live.get("installed_authenticated_exclude_apply_restore") is True and
         live.get("installed_native_authenticated_extra_remove") is True and
         live.get("installed_native_authenticated_extra_install") is True and
         live.get("installed_strategy_lab_idle_and_invalid_refused") is True and
         live.get("installed_extra_resources_offline_suites") is True and
         live.get("installed_lab_extra_preserves_native_owner") is True and
         live.get("installed_lab_mocked_job_e2e") is True and
         live.get("installed_resource_transaction_regressions") is True and
         live.get("installed_functional_owner_preserved") is True and
         live.get("installed_authenticated_lab_extra_http_status") is True and
         live.get("installed_authenticated_web_owner_preserved") is True and
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
    exclude = load("stage5-installed-exclude.py")
    exclude_report = exclude.execute()
    need(exclude_report.get("status") == "PASS_STAGE5_INSTALLED_EXCLUDE_OFFLINE_BACKEND" and
         exclude_report.get("installed_global_exclusions_cli") is True and
         exclude_report.get("installed_dualstack_ipset_policy") is True and
         exclude_report.get("invalid_apply_argv_and_witness_unchanged") is True and
         exclude_report.get("native_config_fd9_and_ipfw_unchanged") is True and
         exclude_report.get("real_wan_or_ipv6_packets_tested") is False,
         "STAGE5_RUNNING_INSTALLED_EXCLUDE_BACKEND_UNQUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_EXCLUDE")
    lab_extra = load("stage5-installed-lab-resources.py")
    lab_extra_report = lab_extra.execute()
    lab_status = lab_extra_report.get("installed_strategy_lab", {})
    suites = lab_extra_report.get("installed_extra_suites", {})
    need(lab_extra_report.get("status") ==
         "PASS_STAGE5_INSTALLED_LAB_STATUS_EXTRA_OFFLINE" and
         lab_status.get("idle_status_queries") == 2 and
         lab_status.get("invalid_job_refused") is True and
         lab_status.get("invalid_target_refused") is True and
         lab_status.get("missing_job_refused") is True and
         lab_status.get("no_lab_job_launched") is True and
         suites.get("test-extra-resources-preflight.py", 0) >= 8 and
         suites.get("test-extra-resources-inventory-cache.py", 0) >= 8 and
         lab_extra_report.get("native_config_fd9_and_ipfw_unchanged") is True and
         lab_extra_report.get("strategy_lab_real_search_tested") is False and
         lab_extra_report.get("extra_resources_real_install_or_remove_tested") is False,
         "STAGE5_RUNNING_INSTALLED_LAB_EXTRA_NOT_QUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_LAB_EXTRA")
    functional = load("stage5-installed-functional.py")
    functional_report = functional.execute()
    need(functional_report.get("status") ==
         "PASS_STAGE5_INSTALLED_LAB_MOCKED_JOB_RESOURCE_TRANSACTION" and
         functional_report.get("installed_lab_mocked_job_scenarios", 0) >= 8 and
         functional_report.get("installed_resource_transaction_cases", 0) >= 35 and
         functional_report.get("real_config_shared_fd9_engine_ipfw_unchanged") is True and
         functional_report.get("service_and_probes_mocked_in_private_job_harness") is True and
         functional_report.get("actual_lab_network_probe_tested") is False and
         functional_report.get("actual_extra_install_remove_tested") is False and
         functional_report.get("owner_appliance_modified") is False,
         "STAGE5_RUNNING_INSTALLED_FUNCTIONAL_TESTS_UNQUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_FUNCTIONAL_FIXTURES")
    auth_web = load("stage5-installed-auth-web.py")
    auth_report = auth_web.execute()
    need(auth_report.get("status") ==
         "PASS_STAGE5_INSTALLED_AUTHENTICATED_LAB_EXTRA_HTTP_READONLY" and
         auth_report.get("installed_general_and_diagnostics_pages_served") is True and
         auth_report.get("stock_cookie_csrf_authenticated_https") is True and
         auth_report.get("installed_lab_http_idle_status") is True and
         auth_report.get("installed_lab_http_invalid_start_cancel_result_refused") is True and
         auth_report.get("installed_extra_http_status_and_inventory_endpoint") is True and
         auth_report.get("saved_config_original_fd9_engine_ipfw_unchanged") is True and
         auth_report.get("real_lab_probe_or_job_started") is False and
         auth_report.get("extra_resources_install_remove_tested") is False and
         auth_report.get("physical_browser_button_click_tested") is False and
         auth_report.get("owner_appliance_modified") is False,
         "STAGE5_RUNNING_INSTALLED_AUTH_WEB_NOT_QUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_AUTH_HTTP")
    exclude_https = load("stage5-installed-exclude-http-apply.py")
    exclude_https_report = exclude_https.execute()
    need(exclude_https_report.get("status") ==
         "PASS_STAGE5_INSTALLED_EXCLUDE_AUTHENTICATED_HTTPS_APPLY_RESTORE" and
         exclude_https_report.get("stock_cookie_csrf_authenticated_https") is True and
         exclude_https_report.get("installed_strategies_api_positive_exclude_apply") is True and
         exclude_https_report.get("real_invalid_full_family_refused_before_mutation") is True and
         exclude_https_report.get("native_exclude_domains_and_ipset_applied") is True and
         exclude_https_report.get("native_exclude_domains_and_ipset_restored") is True and
         exclude_https_report.get("real_fd9_dvtws2_restarted_twice") is True and
         exclude_https_report.get("native_config_other_model_and_ipfw_preserved") is True and
         exclude_https_report.get("real_wan_ipv6_packets_tested") is False and
         exclude_https_report.get("owner_appliance_modified") is False,
         "STAGE5_RUNNING_INSTALLED_EXCLUDE_HTTPS_APPLY_NOT_QUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_EXCLUDE_HTTPS")
    extra_remove = load("stage5-installed-extra-remove-http.py")
    remove_report = extra_remove.execute()
    need(remove_report.get("status") ==
         "PASS_STAGE5_INSTALLED_EXTRA_AUTHENTICATED_REMOVE_AND_NATIVE_TRIAL" and
         all(remove_report.get(field) is True for field in (
             "stock_authenticated_general_page_and_csrf",
             "read_only_noop_plan_and_refusal",
             "exact_local_git_head_and_single_test_file",
             "typed_confirmation_and_stale_digest_refused",
             "native_confirmed_remove_worker_completed",
             "correlated_operation_status_not_installed",
             "removed_only_test_file_upstream_bytes_intact",
             "native_saved_config_unchanged",
             "real_shared_strategies_fd9_owner_restarted",
             "native_lo0_ipfw_rules_preserved")) and
         remove_report.get("outside_network_access_used") is False and
         remove_report.get("additional_resources_install_tested") is False and
         remove_report.get("physical_browser_click_tested") is False and
         remove_report.get("owner_appliance_modified") is False,
         "STAGE5_RUNNING_NATIVE_AUTHENTICATED_EXTRA_REMOVE_NOT_QUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_EXTRA_REMOVE")
    extra_install = load("stage5-installed-extra-install-http.py")
    install_report = extra_install.execute()
    need(install_report.get("status") ==
         "PASS_STAGE5_INSTALLED_EXTRA_AUTHENTICATED_INSTALL_AND_NATIVE_RESTART" and
         install_report.get("source_commit") == extra_install.SOURCE_REVISION and
         type(install_report.get("installed_extra_resource_count")) is int and
         install_report["installed_extra_resource_count"] > 0 and
         all(install_report.get(flag) is True for flag in (
             "stock_authenticated_general_page_and_csrf",
             "get_method_refused_before_mutation",
             "real_github_revision_and_archive_verified",
             "exact_catalog_lua_bin_set_installed",
             "real_installed_resource_cache_verified",
             "correlated_ready_operation_and_revision",
             "real_shared_strategies_fd9_owner_restarted",
             "native_lo0_ipfw_rules_preserved",
             "native_saved_config_unchanged",
             "real_catalog_network_fetch_used")) and
         install_report.get("physical_browser_click_tested") is False and
         install_report.get("owner_appliance_modified") is False,
         "STAGE5_RUNNING_INSTALLED_NATIVE_REAL_EXTRA_INSTALL_UNQUALIFIED")
    need(sha256(PACKAGE) == archive_sha,
         "STAGE5_RUNNING_ARCHIVE_CHANGED_DURING_EXTRA_INSTALL")
    # Recheck every on-disk package-owned file AFTER live service/Voice cycles.
    manifest, installed = running.clean.installed_pkg_manifest(PACKAGE)
    after = running.clean.verify_installed_files(PACKAGE, manifest)
    need(after["exact_installed_package_file_count"] ==
         replacement["installed_files"]["exact_installed_package_file_count"] and
         installed.get("deps") == replacement.get("native_dependencies"),
         "STAGE5_RUNNING_POST_VOICE_INSTALLED_FILES_CHANGED")
    active = load("stage2-opnsense-real-native-active-service.py")
    engine_sha = active.guest_preflight()
    # The last successful native Apply is Strategies Exclude, not Voice.
    # Keep the strict page-scoped committed FD9 journal witness.
    state = common.witness(active, engine_sha, running=True, page='strategies')
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
        "installed_exclude_backend_suites": True,
        "installed_exclude_preserves_native_owner": True,
        "installed_authenticated_exclude_apply_restore": True,
        "installed_native_authenticated_extra_remove": True,
        "installed_native_authenticated_extra_install": True,
        "extra_install_source_commit": install_report["source_commit"],
        "extra_install_catalog_content_sha256": install_report["catalog_content_sha256"],
        "extra_install_owned_count": install_report["installed_extra_resource_count"],
        "installed_strategy_lab_idle_and_invalid_refused": True,
        "installed_extra_resources_offline_suites": True,
        "installed_lab_extra_preserves_native_owner": True,
        "installed_lab_mocked_job_e2e": True,
        "installed_resource_transaction_regressions": True,
        "installed_functional_owner_preserved": True,
        "installed_authenticated_lab_extra_http_status": True,
        "installed_authenticated_web_owner_preserved": True,
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
                "extra_install_source_commit": load("stage5-installed-extra-install-http.py").SOURCE_REVISION,
                "extra_install_catalog_content_sha256": "d" * 64,
                "extra_install_owned_count": 73,
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
                    "unknown_plugin_xml_preserved",
                    "installed_exclude_backend_suites",
                    "installed_exclude_preserves_native_owner",
                    "installed_authenticated_exclude_apply_restore",
                    "installed_native_authenticated_extra_remove",
                    "installed_native_authenticated_extra_install",
                    "installed_strategy_lab_idle_and_invalid_refused",
                    "installed_extra_resources_offline_suites",
                    "installed_lab_extra_preserves_native_owner",
                    "installed_lab_mocked_job_e2e",
                    "installed_resource_transaction_regressions",
                    "installed_functional_owner_preserved",
                    "installed_authenticated_lab_extra_http_status",
                    "installed_authenticated_web_owner_preserved",
                    "loopback_only",
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
                ("installed_exclude_backend_suites", False),
                ("installed_authenticated_exclude_apply_restore", False),
                ("installed_native_authenticated_extra_remove", False),
                ("installed_native_authenticated_extra_install", False),
                ("extra_install_source_commit", "f" * 40),
                ("extra_install_catalog_content_sha256", "bad"),
                ("extra_install_owned_count", 0),
                ("installed_lab_mocked_job_e2e", False),
                ("installed_resource_transaction_regressions", False),
                ("installed_authenticated_lab_extra_http_status", False),
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
