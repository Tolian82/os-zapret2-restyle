#!/usr/bin/env python3
"""Disposable OPNsense G06: zero ordinary profiles and Voice-only shared FD9.

Runs after G04 genuine v1.0.7 first-install and saved-empty same-archive
reinstall. Only installed HTTPS Apply/configctl may change Config/runtime.
No direct IPFW, separate engine, WAN traffic or synthetic Config writer.
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
import time
import xml.etree.ElementTree as ET

from stage2_source_revision import revision_from_makefile, version_from_file

ROOT = Path(__file__).resolve().parent
CONFIG = Path("/conf/config.xml")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
PID = Path("/var/run/dvtws2.pid")
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
ORDINARY = ("--filter-tcp=65431\n--filter-l7=http\n--blob=http_iana_org\n"
            "--payload=http_req\n--lua-desync=fake:blob=http_iana_org:tcp_md5")
VOICE_ARGS = ("--filter-udp=3478\n--filter-l7=stun\n--payload=stun\n"
              "--lua-desync=fake:blob=0x00000000000000000000000000000000:repeats=2")
TARGET = "192.0.2.42/32"
SERVICES = ("telegram", "discord", "x", "sip", "custom")
OWNED = re.compile(r"^190(?:0[0-9]|10)\s")
LAB = re.compile(r"^191(?:[0-2][0-9]|3[01])\s")


class Refusal(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refusal(message)


def run(*argv, timeout=30):
    return subprocess.run(list(argv), check=False, timeout=timeout,
                          capture_output=True, text=True)


def output(*argv, timeout=30):
    result = run(*argv, timeout=timeout)
    need(result.returncode == 0, "G06_ACTION_REFUSED:" +
         Path(argv[0]).name + ":rc=" + str(result.returncode))
    return result.stdout


def module(filename):
    spec = importlib.util.spec_from_file_location(
        "g06_" + filename.replace(".", "_").replace("-", "_"), ROOT / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def rule_sets():
    listing = output("/sbin/ipfw", "-q", "list", timeout=15).splitlines()
    return ([row for row in listing if OWNED.match(row)],
            [row for row in listing if not OWNED.match(row)])


def check_rules(rows, voice, ordinary):
    need(len(rows) == int(voice) + int(ordinary), "G06_OWNED_RULE_COUNT_MISMATCH")
    if voice:
        need(rows[0].startswith("19000 divert 989 udp ") and
             "to table(zapret2_voice_telegram)" in rows[0] and
             "out not diverted not sockarg xmit lo0" in rows[0],
             "G06_VOICE_RULE_NOT_DESTINATION_SCOPED")
    if ordinary:
        nr = 19001 if voice else 19000
        need(rows[-1].startswith(str(nr) + " divert 989 tcp ") and
             "to any 65431 " in rows[-1] and
             "out not diverted not sockarg xmit lo0" in rows[-1],
             "G06_ORDINARY_RULE_NOT_PORT_SCOPED")
    need(not any("udp from any to any" in row for row in rows),
         "G06_WILDCARD_ORDINARY_UDP_INTERCEPT")


def fast():
    voice = ("19000 divert 989 udp from any to table(zapret2_voice_telegram) "
             "out not diverted not sockarg xmit lo0")
    ordinary = ("19001 divert 989 tcp from any to any 65431 "
                "out not diverted not sockarg xmit lo0")
    for rows, a, b in (([], 0, 0), ([voice], 1, 0), ([voice, ordinary], 1, 1)):
        check_rules(rows, a, b)
    for rows, a, b in (([ordinary], 0, 1), ([voice, voice], 1, 0),
                       ([voice.replace("table(zapret2_voice_telegram)", "any")], 1, 0),
                       ([voice.replace("lo0", "vtnet1")], 1, 0)):
        try:
            check_rules(rows, a, b)
        except Refusal:
            continue
        raise AssertionError("G06_SCOPED_IPFW_NEGATIVE_ACCEPTED")
    print("G06_NATIVE_SHARED_FAST=PASS")


def owner(page):
    need(JOURNAL.is_file() and not JOURNAL.is_symlink(),
         "G06_SHARED_JOURNAL_MISSING")
    st = JOURNAL.stat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
         st.st_mode & 0o077 == 0 and st.st_size < 8192,
         "G06_SHARED_FD9_JOURNAL_NOT_TRUSTED")
    data = json.loads(JOURNAL.read_text())
    detail = data.get("detail")
    need(data.get("schema") == 1 and data.get("phase") == "committed" and
         isinstance(detail, dict) and detail.get("page") == page and
         re.fullmatch(r"[a-f0-9]{32}", str(detail.get("id", ""))),
         "G06_SHARED_FD9_COMMIT_MISSING")
    return detail["id"]


def running(engine_sha, foreign_before, voice, ordinary, page):
    need(hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_sha,
         "G06_DVTWS2_BINARY_CHANGED")
    status = run(str(SERVICE), "status")
    need(status.returncode == 0 and "zapret is running" in status.stdout,
         "G06_ENGINE_NOT_RUNNING")
    value = PID.read_text().strip()
    need(value.isdigit() and int(value) > 1 and not PID.is_symlink(),
         "G06_REAL_ENGINE_PID_INVALID")
    census = output("/bin/ps", "-ax", "-o", "pid=", "-o", "command=")
    real = [int(row.strip().split(None, 1)[0])
            for row in census.splitlines()
            if len(row.strip().split(None, 1)) == 2 and
            row.strip().split(None, 1)[0].isdigit() and
            (row.strip().split(None, 1)[1] == str(ENGINE) or
             row.strip().split(None, 1)[1].startswith(str(ENGINE) + " "))]
    need(real == [int(value)], "G06_MULTIPLE_OR_FOREIGN_DVTWS2")
    rules, foreign = rule_sets()
    need(foreign == foreign_before, "G06_FOREIGN_IPFW_CHANGED")
    check_rules(rules, voice, ordinary)
    traffic = (ACTIVE / "traffic-user.conf").read_bytes()
    ordinary_text = traffic.decode("utf-8")
    if ordinary:
        # Blob resolver rewrites the user source to native absolute blob
        # references; compare semantics here, saved raw Config separately.
        need("--filter-tcp=65431" in ordinary_text and
             "--payload=http_req" in ordinary_text and
             "--lua-desync=fake:blob=http_iana_org:tcp_md5" in ordinary_text,
             "G06_RESOLVED_ORDINARY_PROFILE_MISSING")
    else:
        need(not ordinary_text.strip(), "G06_GHOST_ORDINARY_PROFILE")
    need((ACTIVE / "tcp-ports.txt").read_text().strip() ==
         ("65431" if ordinary else "") and
         not (ACTIVE / "udp-ports.txt").read_text().strip(),
         "G06_ZERO_ORDINARY_PORT_ARTIFACTS_INCONSISTENT")
    plan = json.loads((ACTIVE / "voice-plan.json").read_text())
    need(plan.get("schema") == 1 and
         plan.get("source", {}).get("ordinary_sha256") ==
         hashlib.sha256(traffic).hexdigest() and
         len(plan.get("profiles", [])) == int(voice),
         "G06_SHARED_RELEASE_ORDINARY_SHA_NOT_BOUND")
    tokens = (ACTIVE / "traffic.conf").read_text().split()
    need(tokens.count("--name=voice-telegram") == int(voice) and
         tokens.count("--new") == int(bool(voice and ordinary)) and
         bool(tokens) == bool(voice or ordinary),
         "G06_FABRICATED_EMPTY_ORDINARY_OR_MISSING_VOICE")
    if voice:
        table = output("/sbin/ipfw", "table", "zapret2_voice_telegram", "list")
        need("192.0.2.42" in table, "G06_VOICE_DESTINATION_TABLE_MISSING")
    cfg = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    need(cfg is not None and cfg.findtext("general/enabled") == "1" and
         cfg.findtext("general/waninterface") == "lo0" and
         (cfg.findtext("strategy/trafficargs") or "") ==
         (ORDINARY if ordinary else "") and
         (cfg.findtext("hostlist/youtubedomains") or "") == "" and
         cfg.findtext("voice/telegram/enabled") == ("1" if voice else "0"),
         "G06_NATIVE_CONFIG_NOT_SAVED_AS_REQUESTED")
    return {"pid": int(value), "id": owner(page), "rules": rules}


def strategies(web, text, first=False):
    node = web.api("GET", "/api/zapret/settings/get").get("zapret")
    need(isinstance(node, dict) and
         isinstance(node.get("hostlist", {}).get("telegramips"), str),
         "G06_FRESH_STRATEGIES_BASELINE_UNAVAILABLE")
    form = [("zapret[sync][telegramips_baseline]",
             node["hostlist"]["telegramips"]),
            ("zapret[strategy][trafficargs]", text)]
    if first:
        form.extend([("zapret[general][enabled]", "1"),
                     ("zapret[general][waninterface]", "lo0")])
    reply = web.api("POST", "/api/zapret/settings/apply", form)
    need(reply.get("result") == "saved" and reply.get("status") == "ok" and
         reply.get("applied") is True,
         "G06_STRATEGIES_HTTPS_APPLY_NOT_COMMITTED")


def voice_form(document, enabled):
    node, snap = document.get("zapret"), document.get("snapshot")
    need(isinstance(node, dict) and isinstance(snap, str) and
         re.fullmatch(r"[a-f0-9]{64}", snap) and
         isinstance(node.get("voice"), dict) and
         isinstance(node.get("hostlist"), dict),
         "G06_VOICE_MODEL_SNAPSHOT_INVALID")
    fields = [("zapret[sync][snapshot]", snap)]
    for name in SERVICES:
        row = node["voice"].get(name)
        need(isinstance(row, dict) and str(row.get("enabled")) in ("0", "1"),
             "G06_VOICE_SERVICE_MODEL_INCOMPLETE")
        state = ("1" if enabled else "0") if name == "telegram" else str(row["enabled"])
        need(name == "telegram" or state == "0", "G06_FOREIGN_VOICE_SERVICE_ENABLED")
        fields.extend([("zapret[voice][" + name + "][enabled]", state),
                       ("zapret[voice][" + name + "][args]",
                        VOICE_ARGS if name == "telegram" else str(row.get("args", ""))),
                       ("zapret[hostlist][" + name + "ips]",
                        TARGET if name == "telegram"
                        else str(node["hostlist"].get(name + "ips", "")))])
    need(len(fields) == 16, "G06_EXPECTED_FIVE_NATIVE_VOICE_SERVICES")
    return fields


def voice(web, enabled):
    loaded = web.api("GET", "/api/zapret/voice/load")
    result = web.api("POST", "/api/zapret/voice/apply",
                     voice_form(loaded, enabled))
    need(result.get("result") == "saved" and result.get("applied") is True,
         "G06_VOICE_HTTPS_APPLY_NOT_COMMITTED")


def lab_running_no_action(web, engine_sha, foreign_before, initial):
    """Exact native Stage10 and Stage90 with an installed RUNNING/no-action owner.

    Cancel once the real status.json records Stage10 PASS so this isolated
    lifecycle regression does not spend a full DPI search budget. All state
    and owner checks occur after the Lab's original-FD9 restoration.
    """
    job = None
    finished = False
    stage10_passed = False
    status_file = None
    saved = CONFIG.read_bytes()
    start = web.api("POST", "/api/zapret/strategy_lab/start", {
        "target": "yandex.ru", "mode": "standard", "language": "ru",
        "enable_quic": "0", "ipv6_enabled": "0",
    })
    need(start.get("status") == "ok" and
         start.get("state") == "queued" and
         isinstance(start.get("job_id"), str) and
         re.fullmatch(r"job\\.[A-Za-z0-9]{4,40}", start["job_id"]) is not None,
         "G11_NO_ACTION_NATIVE_LAB_NOT_QUEUED")
    job = start["job_id"]
    status_file = Path("/var/run/zapret2-restyle/strategy-lab/jobs") / job / "status.json"
    report = {}
    try:
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            observed = web.api("POST", "/api/zapret/strategy_lab/status",
                               {"job_id": job})
            need(observed.get("job_id") == job and observed.get("state") in (
                "queued", "running", "cancel_requested", "completed", "error"),
                "G11_NO_ACTION_NATIVE_LAB_STATUS_INVALID")
            try:
                state = json.loads(status_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
            stages = state.get("stages", [])
            if isinstance(stages, list):
                stage10_passed = stage10_passed or any(
                    isinstance(row, dict) and str(row.get("number")) == "10"
                    and row.get("status") == "PASS" for row in stages
                )
            if observed["state"] in ("completed", "error"):
                report = web.api("POST", "/api/zapret/strategy_lab/result",
                                 {"job_id": job})
                finished = True
                break
            # One read-only Stage10 witness is enough for this lifecycle test;
            # request normal cancellation rather than waiting for Stage50/60.
            if stage10_passed and observed["state"] == "running":
                web.api("POST", "/api/zapret/strategy_lab/cancel",
                        {"job_id": job})
            time.sleep(1)
        need(finished, "G11_NO_ACTION_NATIVE_LAB_TERMINAL_TIMEOUT")
        stages = report.get("stages", [])
        need(isinstance(stages, list) and any(
            isinstance(row, dict) and str(row.get("number")) == "10"
            and row.get("status") == "PASS" for row in stages
        ), "G11_NO_ACTION_STAGE10_FALSE_INCOMPLETE")
        need(any(isinstance(row, dict) and str(row.get("number")) == "90"
                 and row.get("status") == "PASS" for row in stages),
             "G11_NO_ACTION_STAGE90_FAILED")
        restored = report.get("restoration", {})
        need(isinstance(restored, dict) and
             restored.get("verified") is True and
             restored.get("initial_state") == "RUNNING" and
             restored.get("final_state") == "RUNNING" and
             restored.get("strategy_unchanged") is True and
             restored.get("temporary_runtime_clean") is True,
             "G11_NO_ACTION_RUNNING_OWNER_NOT_RESTORED")
        need(web.api("POST", "/api/zapret/strategy_lab/status",
                     {"job_id": "@active"}).get("status") == "idle",
             "G11_NO_ACTION_LAB_ACTIVE_JOB_NOT_CLEARED")
        after = running(engine_sha, foreign_before, 0, 0, "strategies")
        need(after["id"] == initial["id"] and
             CONFIG.read_bytes() == saved and not after["rules"],
             "G11_NO_ACTION_FD9_OWNER_OR_CONFIG_DRIFT")
        return {"stage10": "PASS", "stage90": "PASS",
                "initial_state": "RUNNING", "final_state": "RUNNING",
                "restoration_verified": True, "lab_outcome": report.get("outcome"),
                "job_id": job}
    finally:
        if job is not None and not finished:
            try:
                web.api("POST", "/api/zapret/strategy_lab/cancel",
                        {"job_id": job})
            except (RuntimeError, OSError, ValueError):
                pass


def execute():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("ZAPRET2_G06_SHARED_NATIVE") == "1" and
         os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         Path("/usr/local/opnsense").is_dir() and ENGINE.is_file(),
         "G06_DISPOSABLE_NATIVE_GUEST_REQUIRED")
    # vmactions sync=tar deliberately has no .git directory inside the guest.
    # The preceding G04 step has already built and installed the SAME native
    # archive using the CI-pinned source identity, then reinstalled that exact
    # physical package and attested its contents. Reuse that native witness.
    head = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(re.fullmatch(r"[a-f0-9]{40}", head) is not None,
         "G06_CI_PROJECT_SHA_NOT_QUALIFIED")
    package = ROOT.parent / "dist" / (
        "os-zapret2-restyle-" + version_from_file() + "_" +
        revision_from_makefile() + ".pkg")
    need(package.is_file() and not package.is_symlink() and
         package.stat().st_size > 1024,
         "G06_G04_EXACT_NATIVE_ARCHIVE_NOT_RETAINED")
    binary_sha = hashlib.sha256(ENGINE.read_bytes()).hexdigest()
    initial = CONFIG.read_bytes()
    cfg = ET.fromstring(initial).find("./OPNsense/Zapret")
    need(cfg is not None and cfg.findtext("general/enabled") == "0" and
         not (cfg.findtext("general/waninterface") or "") and
         not (cfg.findtext("strategy/trafficargs") or "") and
         not (cfg.findtext("hostlist/youtubedomains") or "") and
         cfg.findtext("voice/telegram/enabled") == "0",
         "G06_G04_EMPTY_SAVED_CONFIG_NOT_PRESENT")
    before, foreign_before = rule_sets()
    need(not before and not any(LAB.match(x) for x in foreign_before) and
         not PID.exists(), "G06_G04_LEFT_ACTIVE_OWNER")
    http_mod = module("stage2-opnsense-real-native-voice-http.py")
    boot = module("stage2-opnsense-real-native-boot-syshook.py")
    preserved = boot.config_except_model(initial)
    web = http_mod.GuestHttps()
    http_mod.login(web)

    strategies(web, "", first=True)
    empty_initial = running(binary_sha, foreign_before, 0, 0, "strategies")
    lab_empty = lab_running_no_action(web, binary_sha, foreign_before, empty_initial)
    voice(web, True)
    only = running(binary_sha, foreign_before, 1, 0, "voice")
    need(only["id"] != empty_initial["id"] and
         only["pid"] != empty_initial["pid"],
         "G06_VOICE_ONLY_OWNER_NOT_ROTATED")

    stale = voice_form(web.api("GET", "/api/zapret/voice/load"), True)
    stale = [(k, "f" * 64 if k == "zapret[sync][snapshot]" else v)
             for k, v in stale]
    saved = CONFIG.read_bytes()
    refused = web.api("POST", "/api/zapret/voice/apply", stale)
    need(refused.get("result") == "failed" and
         refused.get("applied") is False and CONFIG.read_bytes() == saved and
         running(binary_sha, foreign_before, 1, 0, "voice") == only,
         "G06_STALE_VOICE_CHANGED_COMMON_OWNER")

    strategies(web, ORDINARY)
    combined = running(binary_sha, foreign_before, 1, 1, "strategies")
    need(combined["id"] != only["id"] and combined["pid"] != only["pid"],
         "G06_COMBINED_OWNER_NOT_ROTATED")
    strategies(web, "")
    back = running(binary_sha, foreign_before, 1, 0, "strategies")
    need(back["id"] != combined["id"] and back["rules"] == only["rules"],
         "G06_REMOVING_LAST_ORDINARY_DID_NOT_RESTORE_VOICE_ONLY")
    voice(web, False)
    empty = running(binary_sha, foreign_before, 0, 0, "voice")
    need(empty["id"] != back["id"] and not empty["rules"],
         "G06_LAST_VOICE_OFF_LEFT_IPFW")

    output("/usr/local/sbin/configctl", "zapret", "stop", timeout=180)
    status = run(str(SERVICE), "status")
    owned_now, other_now = rule_sets()
    need(status.returncode == 1 and not PID.exists() and
         not owned_now and other_now == foreign_before and
         owner("voice") == empty["id"],
         "G06_NATIVE_EMPTY_STOP_NOT_CLEAN")
    output("/usr/local/sbin/configctl", "zapret", "start", timeout=300)
    restarted = running(binary_sha, foreign_before, 0, 0, "voice")
    need(restarted["id"] == empty["id"] and restarted["pid"] != empty["pid"],
         "G06_NATIVE_EMPTY_RESTART_LOST_SAVED_OWNER")
    voice(web, True)
    final = running(binary_sha, foreign_before, 1, 0, "voice")
    need(final["id"] != restarted["id"] and final["rules"] == only["rules"],
         "G06_NATIVE_VOICE_REENABLE_NOT_SCOPED")
    need(boot.config_except_model(CONFIG.read_bytes()) == preserved and
         not (ET.fromstring(CONFIG.read_bytes()).findtext(
             "./OPNsense/Zapret/strategy/trafficargs") or ""),
         "G06_FOREIGN_XML_CHANGED_OR_STRATEGY_BACKFILLED")
    output("/usr/local/sbin/configctl", "zapret", "stop", timeout=180)
    post, foreign_post = rule_sets()
    need(not PID.exists() and not post and foreign_post == foreign_before,
         "G06_FINAL_STOP_CHANGED_FOREIGN_IPFW")
    return {"status": "PASS_G06_REAL_NATIVE_SHARED_VOICE_ONLY",
            "source_sha": head, "engine_sha256": binary_sha,
            "source_provenance": "reused exact G04 native package witness",
            "real_no_action_engine": True,
            "native_lab_no_action": lab_empty,
            "voice_only_zero_ordinary_rules": True,
            "voice_combined_voice_empty_transitions": True,
            "common_original_fd9_https_owner": True,
            "stop_start_empty_reenable_voice": True,
            "stale_snapshot_refused_before_mutation": True,
            "foreign_ipfw_and_config_preserved": True,
            "post_activation_failure_rollback_tested": False,
            "real_voice_media_tested": False, "owner_live_tested": False}


def main():
    if sys.argv[1:] == ["--self-test"]:
        fast()
        return 0
    try:
        need(sys.argv[1:] == ["run"], "G06_RUN_OR_SELF_TEST_REQUIRED")
        value = execute()
    except (Refusal, OSError, ValueError, TypeError, KeyError,
            ET.ParseError, subprocess.TimeoutExpired) as error:
        print("G06_NATIVE_SHARED=REFUSED:" + str(error), file=sys.stderr)
        return 2
    print("G06_NATIVE_SHARED=" + json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
