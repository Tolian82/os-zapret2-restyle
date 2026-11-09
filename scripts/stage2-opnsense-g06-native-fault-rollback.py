#!/usr/bin/env python3
"""G06 S2: deterministic post-activation rollback to genuine Voice-only.

One disposable OPNsense 26.7 guest after real G04 fresh pkg/upstream v1.0.7.
Reuse the existing G05 private COPY of installed native service; fail exactly
after genuine common process/IPFW activation, before native Config::save.
No production script patch, extra daemon/FD9 or direct kernel/Config edits.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
OPTIN = "ZAPRET2_G06_FAULT_NATIVE"
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def load(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "g06_fault_" + name.replace(".", "_").replace("-", "_"), HERE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strategies_envelope(ordinary: str, telegram_baseline: str) -> str:
    need(isinstance(ordinary, str) and isinstance(telegram_baseline, str) and
         telegram_baseline.strip() in ("192.0.2.42", "192.0.2.42/32"),
         "G06_FAULT_UNSAFE_OR_UNEXPECTED_TARGET")
    candidate = {
        "page": "strategies",
        "fields": {"strategy": {"trafficargs": ordinary}},
        "sync": {"telegramips_baseline": telegram_baseline},
    }
    encoded = json.dumps(candidate, ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def self_test():
    g05 = load("stage2-opnsense-g05-wan-rollback.py")
    g05.self_test()
    envelope = strategies_envelope("--filter-tcp=65431", "192.0.2.42/32")
    decoded = json.loads(base64.urlsafe_b64decode(
        envelope + "=" * (-len(envelope) % 4)))
    need(decoded["page"] == "strategies" and
         decoded["fields"] == {"strategy": {"trafficargs": "--filter-tcp=65431"}} and
         decoded["sync"] == {"telegramips_baseline": "192.0.2.42/32"},
         "G06_FAULT_ENVELOPE_NOT_EXACT_NATIVE_FORMAT")
    for wrong in ("", "0.0.0.0/0", "192.0.2.43/32"):
        try:
            strategies_envelope("", wrong)
        except Refusal:
            pass
        else:
            raise AssertionError("G06_FAULT_UNSAFE_SCOPE_ACCEPTED")
    print("G06_NATIVE_FAULT_FAST=PASS")


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.environ.get(OPTIN) == "1" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         Path("/usr/local/opnsense").is_dir(),
         "G06_FAULT_DISPOSABLE_ROOT_GUEST_REQUIRED")
    g06 = load("stage2-opnsense-g06-native-shared-voice.py")
    g05 = load("stage2-opnsense-g05-wan-rollback.py")
    voice = load("stage2-opnsense-real-native-voice-http.py")
    boot = load("stage2-opnsense-real-native-boot-syshook.py")

    # G04 successfully qualified the exact physical Mk archive, restored
    # user-empty strategy, and left the installed genuine engine STOPPED.
    initial = g06.CONFIG.read_bytes()
    z = ET.fromstring(initial).find("./OPNsense/Zapret")
    need(z is not None and z.findtext("general/enabled") == "0" and
         not (z.findtext("general/waninterface") or "") and
         not (z.findtext("strategy/trafficargs") or "") and
         not (z.findtext("hostlist/youtubedomains") or "") and
         z.findtext("voice/telegram/enabled") == "0",
         "G06_FAULT_G04_EMPTY_NATIVE_CONFIG_MISSING")
    engine_sha = hashlib.sha256(g06.ENGINE.read_bytes()).hexdigest()
    owned, foreign = g06.rule_sets()
    need(not owned and not g06.PID.exists() and
         not any(g06.LAB.match(row) for row in foreign),
         "G06_FAULT_OLD_NATIVE_OWNER_NOT_COLD")
    https = voice.GuestHttps()
    voice.login(https)
    # Create the old single committed native owner by the UNMODIFIED
    # authenticated HTTPS worker. No separate Engine/IPFW setup.
    g06.strategies(https, "", first=True)
    g06.voice(https, True)
    before = g06.running(engine_sha, foreign, voice=1, ordinary=0, page="voice")
    xml_before = g06.CONFIG.read_bytes()
    model = https.api("GET", "/api/zapret/settings/get").get("zapret")
    need(isinstance(model, dict) and
         isinstance(model.get("hostlist", {}).get("telegramips"), str),
         "G06_FAULT_STRATEGIES_BASELINE_UNAVAILABLE")
    baseline = model["hostlist"]["telegramips"]
    original_journal = json.loads(g06.JOURNAL.read_text())
    need(original_journal.get("phase") == "committed" and
         original_journal.get("detail", {}).get("id") == before["id"] and
         original_journal.get("detail", {}).get("page") == "voice",
         "G06_FAULT_ORIGINAL_VOICE_OWNER_UNTRUSTED")
    need(g06.ORDINARY and "--filter-tcp=65431" in g06.ORDINARY,
         "G06_FAULT_NEW_ORDINARY_PROFILE_MISSING")

    source = SERVICE.read_text()
    service_info = SERVICE.lstat()
    need(stat.S_ISREG(service_info.st_mode) and
         service_info.st_uid == 0 and not SERVICE.is_symlink(),
         "G06_FAULT_PRODUCTION_SERVICE_NOT_TRUSTED")
    # Exactly the already accepted G05 source-anchored private-copy seam;
    # it refuses if the underlying lifecycle or save ordering changed.
    modified = g05.fault_copy(source)
    need(modified != source and
         modified.count("g05-activated-before-config-save") == 1,
         "G06_FAULT_PRIVATE_COPY_NOT_WITNESSED")

    with tempfile.TemporaryDirectory(prefix="g06-fault-", dir="/root") as directory:
        root = Path(directory)
        private_service = root / "service-instrumented.sh"
        marker = root / "after-real-activation"
        private_service.write_text(modified, encoding="utf-8")
        private_service.chmod(0o700)
        env = dict(os.environ, G05_FAULT_MARKER=str(marker))
        result = subprocess.run(
            [str(private_service), "shared-apply-run", "strategies",
             strategies_envelope(g06.ORDINARY, baseline)],
            capture_output=True, text=True, timeout=500,
            check=False, env=env)
        need(result.returncode == 69 and
             "applied-id=" not in result.stdout and
             marker.is_file() and
             marker.read_text() == "g05-activated-before-config-save\n",
             "G06_FAULT_DID_NOT_REJECT_AFTER_REAL_ACTIVATION")

    # The prior persisted Config remains BYTE-IDENTICAL. The native journal
    # truthfully says RESTORED(previous=old Voice-only committed owner).
    need(g06.CONFIG.read_bytes() == xml_before,
         "G06_FAULT_REPLACED_PERSISTED_NATIVE_CONFIG")
    record = json.loads(g06.JOURNAL.read_text())
    previous_id = g05.restored_predecessor(
        record, original_journal["detail"], page="voice")
    need(previous_id == before["id"],
         "G06_FAULT_JOURNAL_LOST_VOICE_ONLY_OWNER")
    # Reuse every original G06 real PID/manifest/IPv4 IPFW/foreign witness.
    # Adapt ONLY its read-only journal classification for RESTORED, as in G05.
    old_owner_reader = g06.owner
    def read_restored(page):
        need(page == "voice", "G06_FAULT_WRONG_RESTORED_PAGE")
        return g05.restored_predecessor(
            json.loads(g06.JOURNAL.read_text()),
            original_journal["detail"], page=page)
    try:
        g06.owner = read_restored
        after = g06.running(engine_sha, foreign, voice=1, ordinary=0, page="voice")
    finally:
        g06.owner = old_owner_reader
    need(after["id"] == before["id"] and after["pid"] != before["pid"] and
         after["rules"] == before["rules"] and
         g06.CONFIG.read_bytes() == xml_before,
         "G06_FAULT_PREVIOUS_VOICE_ONLY_PID_IPFW_NOT_RESTORED")

    # Same original installed HTTPS path must remain usable immediately
    # after rollback; no manual Config/IPFW/journal repair is permitted.
    g06.strategies(https, g06.ORDINARY)
    combined = g06.running(engine_sha, foreign, voice=1,
                           ordinary=1, page="strategies")
    need(combined["id"] != before["id"] and
         combined["pid"] != after["pid"],
         "G06_FAULT_FOLLOWUP_COMBINED_APPLY_DID_NOT_ROTATE_OWNER")
    g06.strategies(https, "")
    final = g06.running(engine_sha, foreign, voice=1,
                        ordinary=0, page="strategies")
    need(final["id"] != combined["id"] and
         final["rules"] == before["rules"] and
         boot.config_except_model(xml_before) ==
         boot.config_except_model(g06.CONFIG.read_bytes()),
         "G06_FAULT_FOLLOWUP_VOICE_ONLY_OR_FOREIGN_CONFIG_CHANGED")

    # Normal service Stop leaves no plugin IPFW, no test daemon and no
    # native active PID. Only the test's disposable VM is affected.
    g06.output("/usr/local/sbin/configctl", "zapret", "stop", timeout=180)
    owned, outsider = g06.rule_sets()
    need(not owned and not g06.PID.exists() and outsider == foreign,
         "G06_FAULT_FINAL_NATIVE_STOP_NOT_CLEAN")
    return {
        "status": "PASS_G06_REAL_POST_ACTIVATION_VOICE_ONLY_ROLLBACK",
        "source_sha": os.environ["ZAPRET2_NATIVE_PROJECT_SHA"],
        "instrumentation": "reused exact G05 private service fault copy",
        "native_real_engine_sha256": engine_sha,
        "post_activation_pre_config_save_refusal": True,
        "terminal_restored_previous_voice_owner": True,
        "config_byte_identical_on_failure": True,
        "previous_voice_only_pid_and_ipfw_restored": True,
        "two_followup_unmodified_https_apply": True,
        "final_native_stop_and_foreign_ipfw_clean": True,
        "original_fd9_shared_lifecycle": True,
        "production_script_modified": False,
        "unmodified_https_fault_tested": False,
        "owner_live_tested": False,
    }


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "G06_FAULT_RUN_OR_SELF_TEST_REQUIRED")
        result = execute()
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            ET.ParseError, subprocess.TimeoutExpired) as exc:
        print("G06_NATIVE_FAULT=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("G06_NATIVE_FAULT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
