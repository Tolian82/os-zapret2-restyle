#!/usr/bin/env python3
"""G06 LC-07 experimental evidence only: no user profile on real FreeBSD dvtws2.

Run AFTER the real G04 installed-native package/upstream/empty-save witness, in
the SAME disposable OPNsense 26.7 guest. No production runtime or Config edits.
A process / --dry-run result alone is not accepted as packet-safety evidence:
a narrowly scoped temporary localhost-only IPFW divert must carry intact data.
The experiment decides which LC-07 implementation branch is viable; it does
NOT qualify the full G06 Voice-only lifecycle or physical owner appliance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET

ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
RELEASE = Path("/var/db/zapret2-restyle/runtime.release")
CONFIG = Path("/conf/config.xml")
PID = Path("/var/run/dvtws2.pid")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
IPFW = "/sbin/ipfw"
OWNED = re.compile(r"^\s*(?:190(?:0[0-9]|10)|191(?:[0-2][0-9]|3[01]))\s")
PAYLOAD = b"G06 no-action scoped localhost passthrough 2026\n"


class Refusal(RuntimeError):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def call(args, timeout=20):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          check=False)


def rules():
    got = call([IPFW, "-q", "list"], timeout=10)
    need(got.returncode == 0, "G06_IPFW_MODULE_OR_RULES_UNAVAILABLE")
    return got.stdout.splitlines()


def model_empty():
    z = ET.fromstring(CONFIG.read_bytes()).find("./OPNsense/Zapret")
    need(z is not None and (z.findtext("strategy/trafficargs") or "") == "" and
         (z.findtext("hostlist/youtubedomains") or "") == "" and
         z.findtext("general/enabled", "0") == "0",
         "G06_SAVED_EMPTY_OWNER_CONFIG_NOT_ATTESTED")


def local_echo(port_ready, result):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        sock.settimeout(9)
        port_ready.append(sock.getsockname()[1])
        port_ready.append(True)
        client, _ = sock.accept()
        with client:
            client.settimeout(6)
            data = b""
            while len(data) < len(PAYLOAD):
                part = client.recv(len(PAYLOAD) - len(data))
                if not part:
                    break
                data += part
            result.append(data)
            client.sendall(data)
    except (OSError, TimeoutError) as exc:
        result.append("server-error:" + type(exc).__name__)
    finally:
        sock.close()


def run_no_action(engine_hash, original_config, original_rules):
    dry = call([str(ENGINE), "--port=989", "--dry-run"], timeout=25)
    # Strictly distinguish an observed native refusal from a claim of success.
    if dry.returncode:
        need(CONFIG.read_bytes() == original_config and rules() == original_rules,
             "G06_DRYRUN_REFUSAL_CHANGED_NATIVE_CONFIG_OR_IPFW")
        return {
            "status": "G06_NATIVE_EXPERIMENT_DRYRUN_REFUSED",
            "branch": "B_candidate_not_yet_qualified",
            "dry_run_rc": dry.returncode,
            "diagnostic": (dry.stderr or dry.stdout)[-240:],
            "no_action_proved": False,
            "production_code_changed": False,
        }

    engine = None
    added = False
    before_pid = PID.exists()
    port = []
    received = []
    echo_thread = None
    primary = None
    packet_counter = None
    try:
        # Not a new service manager: short-lived PRIVATE test child only,
        # no configd, startup hook or service state publication.
        engine = subprocess.Popen(
            [str(ENGINE), "--port=989"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE)
        time.sleep(2)
        need(engine.poll() is None,
             "G06_DRYRUN_ACCEPTED_BUT_NO_PROFILE_ENGINE_EXITED")
        need(hashlib.sha256(ENGINE.read_bytes()).hexdigest() == engine_hash,
             "G06_TEST_ENGINE_CHANGED_DURING_PROBE")
        echo_thread = threading.Thread(
            target=local_echo, args=(port, received), daemon=True)
        echo_thread.start()
        for _ in range(60):
            if len(port) == 2:
                break
            time.sleep(0.05)
        need(len(port) == 2 and 1024 <= port[0] <= 65535,
             "G06_TEST_LOOPBACK_SERVER_NOT_READY")
        # Strict test-owned single destination only; no broad WAN divert.
        # Baseline must have no plugin/Lab rules at all before this step.
        cmd = [IPFW, "-q", "add", "19000", "divert", "989",
               "tcp", "from", "any", "to", "127.0.0.1",
               str(port[0]), "out", "not", "diverted",
               "not", "sockarg", "xmit", "lo0"]
        a = call(cmd)
        need(a.returncode == 0,
             "G06_SCOPED_ONLY_IPFW_DIVERT_INSTALL_FAILED")
        added = True
        need(engine.poll() is None,
             "G06_TEST_ENGINE_DIED_AFTER_LOCAL_DIVERT")
        with socket.create_connection(("127.0.0.1", port[0]), timeout=8) as s:
            s.settimeout(8)
            s.sendall(PAYLOAD)
            echo = b""
            while len(echo) < len(PAYLOAD):
                part = s.recv(len(PAYLOAD) - len(echo))
                if not part:
                    break
                echo += part
        echo_thread.join(timeout=7)
        need(received == [PAYLOAD] and echo == PAYLOAD,
             "G06_NO_ACTION_LOCALHOST_PAYLOAD_CHANGED_OR_LOST")
        count = call([IPFW, "-a", "list", "19000"])
        need(count.returncode == 0 and
             re.search(r"(?m)^\s*19000\s+[1-9][0-9]*\s", count.stdout),
             "G06_TEMP_DIVERT_PACKET_COUNTER_NOT_PROVEN")
        packet_counter = count.stdout.strip()[:200]
        need(engine.poll() is None,
             "G06_NO_ACTION_DVTWS_ENGINE_NOT_STABLE_AFTER_PACKETS")
    except (Refusal, OSError, subprocess.TimeoutExpired) as exc:
        primary = str(exc)
    finally:
        if added:
            # Remove only test-created exact rule. Never sweep a numeric range.
            deletion = call([IPFW, "-q", "delete", "19000"])
            if deletion.returncode:
                primary = (primary or "") + ";G06_EXACT_TEST_RULE_DELETE_FAILED"
        if engine is not None:
            if engine.poll() is None:
                engine.terminate()
                try:
                    engine.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    engine.kill()
                    engine.wait(timeout=5)
            if engine.stderr:
                engine.stderr.close()
        if echo_thread is not None:
            echo_thread.join(timeout=1)
        if CONFIG.read_bytes() != original_config or rules() != original_rules:
            primary = (primary or "") + ";G06_CONFIG_OR_FOREIGN_IPFW_NOT_RESTORED"
        if PID.exists() != before_pid:
            primary = (primary or "") + ";G06_TEST_CREATED_OR_DELETED_SERVICE_PID"
    need(primary is None, primary or "G06_UNKNOWN_NATIVE_FAILURE")
    return {
        "status": "G06_NATIVE_EXPERIMENT_NO_ACTION_PACKET_PASSTHROUGH",
        "branch": "A_candidate_not_yet_full_G06_acceptance",
        "real_dry_run": True,
        "real_engine_lived_across_packet": True,
        "test_only_localhost_scoped_divert": True,
        "packet_counter_witness": packet_counter,
        "payload_exact": True,
        "config_and_foreign_ipfw_restored": True,
        "no_action_proved": True,
        "production_code_changed": False,
    }


def self_test():
    need(OWNED.search("19000 divert 989 tcp ") is not None,
         "G06_TEST_SCOPED_RULE_PARSER")
    need(OWNED.search("19131 divert 989 tcp ") is not None,
         "G06_TEST_LAB_RULE_PARSER")
    need(OWNED.search("65535 allow ip from any to any") is None,
         "G06_TEST_FOREIGN_RULE_PARSER")
    need(PAYLOAD.endswith(b"\n"), "G06_TEST_PAYLOAD_MARKER")
    print("PASS_G06_EXPERIMENT_SOURCE_SAFE_SCOPE_AND_NO_PROFILE_CASE=1")


def main():
    if sys.argv[1:] == ["--self-test"]:
        self_test()
        return
    need(not sys.argv[1:], "G06_UNEXPECTED_ARGUMENTS")
    for key in ("GITHUB_ACTIONS", "ZAPRET2_NATIVE_BUILD_CI",
                "ZAPRET2_G06_NO_ACTION_NATIVE"):
        need(os.environ.get(key) == ("true" if key == "GITHUB_ACTIONS" else "1"),
             "G06_NATIVE_DISPOSABLE_OPTIN_MISSING:" + key)
    need(os.uname().sysname == "FreeBSD" and os.geteuid() == 0 and
         Path("/usr/local/opnsense").is_dir(),
         "G06_NOT_ROOT_DISPOSABLE_OPNSENSE")
    need(ENGINE.is_file() and not ENGINE.is_symlink() and
         os.access(ENGINE, os.X_OK) and RELEASE.is_file() and
         RELEASE.read_text().strip() == "v1.0.7",
         "G06_PINNED_REAL_ENGINE_NOT_INSTALLED")
    need(CONFIG.is_file() and not CONFIG.is_symlink(),
         "G06_NATIVE_CONFIG_UNSAFE")
    model_empty()
    need(not PID.exists(), "G06_ACTIVE_SERVICE_OWNER_CONFLICT")
    started = call([str(SERVICE), "status"])
    need("zapret is running" not in started.stdout,
         "G06_SERVICE_ALREADY_RUNNING")
    original_config = CONFIG.read_bytes()
    original_rules = rules()
    need(not any(OWNED.match(row) for row in original_rules),
         "G06_OTHER_LIFECYCLE_IPFW_OWNER_PRESENT")
    # Version strings can differ between binary builds; the immutable
    # selected release marker and native Git tag/HEAD prove exact identity.
    root = "/usr/local/etc/zapret2"
    git_head = call(["/usr/local/bin/git", "-C", root, "rev-parse", "HEAD"])
    git_tag = call(["/usr/local/bin/git", "-C", root, "rev-parse",
                    "refs/tags/v1.0.7^{commit}"])
    need(git_head.returncode == git_tag.returncode == 0 and
         git_head.stdout.strip() == git_tag.stdout.strip() and
         re.fullmatch(r"[a-f0-9]{40}", git_head.stdout.strip()),
         "G06_ENGINE_SOURCE_NOT_PINNED_V1_0_7")
    version = call([str(ENGINE), "--version"])
    need(version.returncode == 0, "G06_ENGINE_VERSION_COMMAND_REFUSED")
    digest = hashlib.sha256(ENGINE.read_bytes()).hexdigest()
    result = run_no_action(digest, original_config, original_rules)
    result.update({"engine_version": "v1.0.7",
                   "engine_sha256": digest,
                   "owner_browser_tested": False,
                   "voice_only_tested": False})
    print("G06_NATIVE_EXPERIMENT=" + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, ValueError, ET.ParseError,
            subprocess.TimeoutExpired) as exc:
        print("G06_NATIVE_EXPERIMENT=REFUSED:" + str(exc), file=sys.stderr)
        sys.exit(1)
