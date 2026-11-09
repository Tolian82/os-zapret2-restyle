#!/usr/bin/env python3
"""G05 S2: deterministic post-activation, pre-Config-save failure in one native guest.

The fixture runs a PRIVATE COPY of the installed, otherwise original service
entrypoint. One source-anchored shell call to the native Config writer is
replaced by an explicit 69 refusal *after* actual engine/IPFW activation.
No product source, installed script, global Config or IPFW adapter is patched.
The original FD9 transaction, native engine and rollback are exercised.
This is instrumented disposable-native evidence, NOT unmodified HTTPS fault.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from types import SimpleNamespace
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
OPTIN = "ZAPRET2_G05_ROLLBACK_NATIVE"
STATUS = "PASS_G05_POST_ACTIVATION_PRE_SAVE_NATIVE_ROLLBACK"
SAVE_LINE = '    shared_apply_native_config save "$_shared_apply_id" "$_shared_apply_page"\n'
SAVE_STATUS = '    _shared_apply_save_status=$?\n'
FAULT_LINE = (
    '    # G05 TEMPORARY TEST COPY ONLY: fail after a real activation.\n'
    '    printf "%s\\n" g05-activated-before-config-save > "${G05_FAULT_MARKER:?}"\n'
    '    (exit 69)\n'
)


class Refusal(RuntimeError):
    pass


def need(condition, reason):
    if not condition:
        raise Refusal(reason)


def load(filename):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "g05_rollback_" + filename.replace("-", "_").replace(".", "_"),
        HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fault_copy(source):
    """Keep all unmodified entrypoint code and one deterministic fault seam."""
    need(source.count(SAVE_LINE + SAVE_STATUS) == 1,
         "G05_FAULT_NATIVE_CONFIG_CALL_NOT_UNIQUE")
    need(source.count('    if ! apply_runtime_attest_activated; then\n') == 1,
         "G05_FAULT_POST_ACTIVATION_PROOF_MISSING")
    need(source.index('    if ! apply_runtime_attest_activated; then\n') <
         source.index(SAVE_LINE), "G05_FAULT_WOULD_PRECEDE_ACTIVATION")
    need(source.count('    if [ "$_shared_apply_save_status" -ne 0 ]; then\n') == 1,
         "G05_FAULT_RESTORE_BRANCH_MISSING")
    return source.replace(SAVE_LINE, FAULT_LINE, 1)


def envelope(wan, baseline):
    need(wan == "wan", "G05_FAULT_UNEXPECTED_TARGET")
    need(isinstance(baseline, str) and
         baseline.strip() in ("192.0.2.42", "192.0.2.42/32"),
         "G05_FAULT_NOT_DISPOSABLE_VOICE_BASELINE")
    request = {"page": "strategies", "fields": {"general": {"waninterface": wan}},
               "sync": {"telegramips_baseline": baseline}}
    payload = json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode()
    return base64.urlsafe_b64encode(payload).decode().rstrip("=")


def restored_predecessor(record, expected, *, page):
    """Attest terminal rollback *and* the unchanged prior committed owner."""
    need(isinstance(expected, dict) and expected.get("page") == page and
         isinstance(expected.get("id"), str) and
         len(expected["id"]) == 32 and
         all(c in "0123456789abcdef" for c in expected["id"]),
         "G05_FAULT_ORIGINAL_OWNER_UNTRUSTED")
    need(isinstance(record, dict) and record.get("schema") == 1 and
         record.get("phase") == "restored" and
         record.get("previous") == expected and
         isinstance(record.get("detail"), dict) and
         record["detail"].get("page") == "strategies" and
         isinstance(record["detail"].get("id"), str) and
         len(record["detail"]["id"]) == 32 and
         all(c in "0123456789abcdef" for c in record["detail"]["id"]) and
         record["detail"]["id"] != expected["id"],
         "G05_FAULT_TERMINAL_RESTORED_PREDECESSOR_MISMATCH")
    return expected["id"]


def execute():
    for key in ("GITHUB_ACTIONS", "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK",
                "ZAPRET2_NATIVE_BUILD_CI", "ZAPRET2_STAGE0_DISPOSABLE_RUNNING_TEST",
                "ZAPRET2_STAGE2_REAL_RUNNING_UPGRADE",
                "ZAPRET2_STAGE2_REAL_ACTIVE_SERVICE",
                "ZAPRET2_STAGE2_REAL_COMMON_VOICE",
                "ZAPRET2_STAGE2_REAL_VOICE_HTTP",
                "ZAPRET2_G05_RUNNING_WAN_NATIVE", OPTIN):
        need(os.environ.get(key) == ("true" if key == "GITHUB_ACTIONS" else "1"),
             "G05_FAULT_DISPOSABLE_GUEST_OPTIN_REQUIRED:" + key)
    need(os.uname().sysname == "FreeBSD" and os.geteuid() == 0,
         "G05_FAULT_FREEBSD_ROOT_REQUIRED")
    active = load("stage2-opnsense-real-native-active-service.py")
    common = load("stage2-opnsense-real-native-shared-voice.py")
    voice = load("stage2-opnsense-real-native-voice-http.py")
    g05 = load("stage2-opnsense-g05-wan-running.py")
    save = load("stage2-opnsense-g05-wan-save.py")
    boot = load("stage2-opnsense-real-native-boot-syshook.py")
    engine_sha = active.guest_preflight()
    device = g05.native_wan_device()
    web = voice.GuestHttps()
    voice.login(web)
    before, baseline = g05.read_model(web)
    need(g05.logical_wan(before, save) == "lo0" and
         before["voice"]["telegram"]["enabled"] == "1",
         "G05_FAULT_INITIAL_COMMON_OWNER_MISSING")
    xml_before = active.CONFIG.read_bytes()
    old = g05.shared_owner(active, common, engine_sha, "lo0")
    original_journal = json.loads(common.JOURNAL.read_text())
    need(original_journal.get("phase") == "committed" and
         original_journal.get("detail", {}).get("id") == old["id"],
         "G05_FAULT_ORIGINAL_JOURNAL_NOT_COMMITTED")

    # Use the same installed service code, not a new runner or transaction.
    info = SERVICE.lstat()
    need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and not SERVICE.is_symlink(),
         "G05_FAULT_INSTALLED_SERVICE_UNTRUSTED")
    source = SERVICE.read_text()
    patched = fault_copy(source)
    need(patched != source and patched.count("g05-activated-before-config-save") == 1,
         "G05_FAULT_COPY_NOT_ISOLATED")
    with tempfile.TemporaryDirectory(prefix="g05-rollback-", dir="/root") as directory:
        root = Path(directory)
        service = root / "service-instrumented.sh"
        marker = root / "post-activation-marker"
        service.write_text(patched)
        service.chmod(0o700)
        env = dict(os.environ, G05_FAULT_MARKER=str(marker))
        result = subprocess.run(
            [str(service), "shared-apply-run", "strategies", envelope("wan", baseline)],
            capture_output=True, text=True, timeout=500, check=False, env=env)
        need(result.returncode == 69 and
             "applied-id=" not in result.stdout and
             marker.read_text() == "g05-activated-before-config-save\n",
             "G05_FAULT_NOT_REJECTED_AFTER_ACTIVATION")

    # Old native Config and model MUST be unchanged, while actual rollback
    # restarts the prior engine and restores both Voice and ordinary IPFW.
    need(active.CONFIG.read_bytes() == xml_before,
         "G05_FAULT_MODIFIED_NATIVE_CONFIG")
    after, _ = g05.read_model(web)
    voice.attest_complete_native_model(before, after)
    # The shared journal deliberately records the failed transaction as
    # terminal RESTORED; its `previous` is the unchanged committed owner.
    # Only the journal reader is adapted for this specific proof. All other
    # engine/PID/Voice/IPFW checks reuse the unmodified native G05 witness.
    def restored_checked(record, *, page):
        return restored_predecessor(record, original_journal["detail"], page=page)
    restored_common = SimpleNamespace(
        JOURNAL=common.JOURNAL, invoke=common.invoke,
        checked_journal=restored_checked)
    witness = g05.shared_owner(active, restored_common, engine_sha, "lo0")
    need(witness["id"] == old["id"] and witness["pid"] != old["pid"] and
         witness["rules"] == old["rules"],
         "G05_FAULT_PREVIOUS_FD9_VOICE_IPFW_NOT_RESTORED")
    need(boot.config_except_model(xml_before) ==
         boot.config_except_model(active.CONFIG.read_bytes()) and
         voice.native_unmanaged_xml(xml_before) ==
         voice.native_unmanaged_xml(active.CONFIG.read_bytes()),
         "G05_FAULT_FOREIGN_CONFIG_CHANGED")

    # Subsequent UNMODIFIED authenticated HTTPS full Apply must still work:
    # no special manual cleanup, journal intervention or alternate writer.
    forward = web.api("POST", "/api/zapret/settings/apply",
                      g05.form("wan", baseline))
    need(forward.get("result") == "saved" and forward.get("applied") is True,
         "G05_FAULT_FOLLOWUP_NATIVE_APPLY_FAILED")
    moved = g05.shared_owner(active, common, engine_sha, device)
    need(moved["id"] != old["id"], "G05_FAULT_STALE_OLD_OWNER_AFTER_RETRY")
    moved_model, moved_baseline = g05.read_model(web)
    g05.preserved_other_model(before, moved_model)
    back = web.api("POST", "/api/zapret/settings/apply",
                   g05.form("lo0", moved_baseline))
    need(back.get("result") == "saved" and back.get("applied") is True,
         "G05_FAULT_FOLLOWUP_NATIVE_REVERSE_FAILED")
    end, _ = g05.read_model(web)
    voice.attest_complete_native_model(before, end)
    restored = g05.shared_owner(active, common, engine_sha, "lo0")
    need(restored["id"] != moved["id"] and
         restored["rules"] == old["rules"] and
         boot.config_except_model(xml_before) ==
         boot.config_except_model(active.CONFIG.read_bytes()) and
         voice.native_unmanaged_xml(xml_before) ==
         voice.native_unmanaged_xml(active.CONFIG.read_bytes()),
         "G05_FAULT_FINAL_NATIVE_STATE_NOT_RESTORED")
    return {
        "status": STATUS, "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        "instrumentation": "private service copy; Config save -> deterministic 69",
        "real_original_fd9": True,
        "real_kernel_ipfw_and_voice_rollback": True,
        "previous_owner_after_fault": True,
        "native_config_byte_identical": True,
        "subsequent_two_unmodified_https_apply": True,
        "production_script_modified": False,
        "physical_owner_browser_tested": False,
        "tun_opt_tested": False,
    }


def self_test():
    seed = (
        "    if ! apply_runtime_attest_activated; then\n"
        '    if ! shared_apply_bundle_service verify "x"; then\n'
        + SAVE_LINE + SAVE_STATUS +
        '    if [ "$_shared_apply_save_status" -ne 0 ]; then\n'
    )
    patched = fault_copy(seed)
    need(SAVE_LINE not in patched and FAULT_LINE in patched and
         SAVE_STATUS in patched, "G05_FAULT_SELFTEST_FAILED")
    for damaged in (
        seed.replace(SAVE_LINE, ""),
        seed.replace(SAVE_LINE + SAVE_STATUS, 2 * (SAVE_LINE + SAVE_STATUS)),
        seed.replace("apply_runtime_attest_activated", "fake_witness"),
    ):
        try:
            fault_copy(damaged)
        except Refusal:
            pass
        else:
            raise AssertionError("unsafe fixture source admitted")
    previous = {"id": "a" * 32, "page": "strategies", "candidate": "b" * 64}
    restored = {"schema": 1, "phase": "restored",
                "detail": {"id": "c" * 32, "page": "strategies"},
                "previous": previous}
    need(restored_predecessor(restored, previous, page="strategies") == previous["id"],
         "G05_FAULT_PREDECESSOR_SELFTEST")
    for bad in (
        dict(restored, phase="committed"),
        dict(restored, previous=dict(previous, id="d" * 32)),
        dict(restored, detail=dict(restored["detail"], id=previous["id"])),
        dict(restored, previous=None),
    ):
        try:
            restored_predecessor(bad, previous, page="strategies")
        except Refusal:
            pass
        else:
            raise AssertionError("invalid terminal rollback journal admitted")
    raw = envelope("wan", "192.0.2.42/32")
    decoded = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    need(decoded["fields"] == {"general": {"waninterface": "wan"}},
         "G05_FAULT_ENVELOPE_MALFORMED")
    print("PASS: G05 private native rollback fault seam and request envelope")


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "G05_FAULT_EXPECTED_RUN_OR_SELF_TEST")
        result = execute()
    except (Refusal, OSError, ValueError, TypeError, KeyError, ET.ParseError,
            subprocess.TimeoutExpired) as err:
        print("G05_ROLLBACK_NATIVE=REFUSED:" + str(err), file=sys.stderr)
        return 2
    print("G05_ROLLBACK_NATIVE=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
