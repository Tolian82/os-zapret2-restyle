#!/usr/bin/env python3
"""P0: one actual generated-auto map/first-match witness, disposable guest only.

Reuse the original portable generator witness, Voice compiler and native host
guard. No plugin, Config, production service or Strategy Lab is invoked.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src/opnsense/scripts/OPNsense/Zapret/backend"))
from voice_profile_compiler import SERVICES, compile_candidate

MARK = "P0_NATIVE_GENERATED_OBSERVER"
HOST = "127.0.0.1"
PORT, MIXED_PORT, IMPORT_PORT, DEFAULT_PORT, VOICE_PORT = range(6545, 6550)
DIVERT = 19899
RULES = (19351, 19352, 19353, 19354)
UNKNOWN = "unknown.generated.p0.invalid"
IP_ONLY = "ipset.generated.p0.invalid"


def need(ok: bool, code: str) -> None:
    if not ok:
        raise RuntimeError(code)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    need(spec is not None and spec.loader is not None, "P0_DEPENDENCY_MISSING")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def modules():
    original = load("p0_original_observer", HERE / "test-p0-native-auto-observer.py")
    generator = load("p0_actual_generator", ROOT / "docs/verification/test_p0_profile_attribution.py")
    return original, generator


def source_strategy() -> str:
    action = "--filter-l7=http\n--payload=http_req\n--lua-desync=multisplit:pos=method+2\n"
    return (f"--template=p0-http\n--filter-tcp={IMPORT_PORT}\n<HOSTLIST:youtube>\n" + action +
            f"--new=skipped\n--skip\n--filter-tcp={DEFAULT_PORT}\n<HOSTLIST:user>\n" + action +
            f"--new=known\n--filter-tcp={PORT}\n<HOSTLIST:youtube>\n" + action +
            f"--new=mixed\n--filter-tcp={MIXED_PORT}\n<HOSTLIST:user>\n<IPSET:telegram>\n" + action +
            "--new=imported\n--import=p0-http\n<HOSTLIST:user>\n")


def voice(case: Path) -> str:
    data = dict(strategy_wan="lo0", services={
        service: dict(enabled=False, args="", ips="") for service in SERVICES})
    data["services"]["telegram"] = dict(enabled=True, ips=HOST,
        args=f"--filter-udp={VOICE_PORT}\n--filter-l7=stun\n--payload=stun")
    text, plan = compile_candidate(data, case / "active/managed", {"telegram": [HOST]})
    need(len(plan["profiles"]) == 1 and plan["profiles"][0]["service"] == "telegram",
         "ORIGINAL_VOICE_COMPILER_NOT_USED")
    return text


def extra(case: Path) -> str:
    for filename in ("inbox.txt", "debug.log"):
        path = case / filename
        path.write_bytes(b"")
        path.chmod(0o666)  # Synthetic guest-only engine producer files.
    return (f"--debug=1\n--hostlist-auto-debug={case}/debug.log\n"
            f"--new=p0-observer\n--filter-tcp={PORT}\n--filter-l7=http\n"
            f"--hostlist-auto={case}/inbox.txt\n--hostlist-auto-fail-threshold=1\n"
            "--hostlist-auto-retrans-reset=0\n")


def fixture(generator, checkout: Path):
    test = generator.AttributionTests("runTest")
    test.setUp()
    try:
        data, mapping = test.generate(source_strategy(), voice=voice, extra=extra,
            checkout=checkout, divert=DIVERT, telegram_ips=HOST)
        case = test.last_case
        need([r["native_number"] for r in mapping["profiles"]]
             == [1, None, None, 2, 3, 4, 5, 6, 0], "GENERATED_NATIVE_NUMBER_MAP_INVALID")
        need([r["status"] for r in mapping["profiles"]]
             == ["excluded-voice", "non-executable-template", "non-executable-skip",
                 "known-hostlist", "excluded-ipset", "excluded-ipset",
                 "unknown-import", "unknown-extra", "unknown-native-default"],
             "GENERATED_SOURCE_ISOLATION_INVALID")
        need(mapping["profiles"][3]["source_number"] == 3 and
             mapping["profiles"][3]["hostlist"] == "youtube" and
             mapping["profiles"][4]["source_number"] == mapping["profiles"][5]["source_number"] == 4,
             "GENERATED_SOURCE_ORDINAL_LOST")
        # Make only this synthetic candidate's references usable on the guest.
        test.root.chmod(0o755)
        case.chmod(0o755)
        (case / "active").mkdir()
        shutil.copytree(case / "release/managed", case / "active/managed")
        observer = data["extra"].decode().split("--new=p0-observer\n", 1)[1].split()
        need(not any(t.startswith(("--lua-", "--import", "--ipset=")) for t in observer)
             and "--hostlist-auto-retrans-reset=0" in observer,
             "OBSERVER_COVERT_ACTION_OR_IPSET")
        return test, case, data, mapping
    except BaseException:
        test.doCleanups()
        raise


def rules() -> list[list[str]]:
    result = []
    common = ["out", "not", "diverted", "not", "sockarg", "xmit", "lo0"]
    for protocol, ports in (("tcp", f"{PORT},{MIXED_PORT},{IMPORT_PORT},{DEFAULT_PORT}"),
                            ("udp", str(VOICE_PORT))):
        result.append(["divert", str(DIVERT), protocol, "from", HOST, "to", HOST, ports, *common])
        result.append(["divert", str(DIVERT), protocol, "from", HOST, ports, "to", HOST, *common])
    return result


def selections(content: str) -> dict[tuple[int, str, str], set[int]]:
    """Use native dp_find search+match records, not startup profile banners."""
    found = {}
    current = None
    for line in content.splitlines():
        if line.startswith("packet: id="):
            current = None
        search = re.search(r"desync profile search for .* port=(\d+) .* l7proto=(\S+) .* hostname='([^']*)'", line)
        if search:
            current = (int(search[1]), search[2], search[3])
        match = re.search(r"desync profile (\d+) \([^)]*\) matches", line)
        if match and current is not None:
            found.setdefault(current, set()).add(int(match[1]))
    return found


def attest_selections(content: str) -> None:
    expected = {(PORT, "http", "youtube.com"): 2,
                (MIXED_PORT, "http", "example.org"): 3,
                (MIXED_PORT, "http", IP_ONLY): 4,
                (IMPORT_PORT, "http", "youtube.com"): 5,
                (DEFAULT_PORT, "http", "example.org"): 0,
                (PORT, "http", UNKNOWN): 6,
                (VOICE_PORT, "stun", ""): 1}
    actual = selections(content)
    for key, number in expected.items():
        need(actual.get(key) == {number}, f"NATIVE_SELECTION_MISMATCH:{key}:{actual.get(key)}")


def self_test() -> None:
    original, generator = modules()
    original.self_test()
    need(all(n not in range(19000, 19011) and n not in range(19100, 19132) for n in RULES),
         "PRODUCTION_RULE_COLLISION")
    with tempfile.TemporaryDirectory(prefix="p0-generated-source-") as dirname:
        checkout = Path(dirname)
        (checkout / "lua").mkdir()
        for name in ("zapret-lib.lua", "zapret-antidpi.lua"):
            (checkout / "lua" / name).write_text("return true\n")
        test, case, data, mapping = fixture(generator, checkout)
        try:
            api = test.implementation()
            need(api.lookup(mapping, data["generation"], data["final"], 2)["hostlist"] == "youtube",
                 "KNOWN_GENERATION_MAPPING_MISSING")
            need(api.lookup(mapping, "stale", data["final"], 6) is None, "STALE_GENERATION_ACCEPTED")
            need(api.lookup(mapping, data["generation"], data["final"], 6)["hostlist"] is None,
                 "UNKNOWN_OBSERVER_GUESSED_KNOWN_LIST")
            need((case / "active/managed/ipset-telegram.txt").read_text() == HOST + "\n",
                 "LOOPBACK_IPSET_NOT_GENERATED")
        finally:
            test.doCleanups()
    sample = "desync profile search for ipv4 ip=127.0.0.1 port=6545 icmp=255:255 l7proto=http ssid='' mark=0x00000000 hostname='youtube.com'\n"
    need(selections(sample + "desync profile 2 (known) matches\n")
         == {(PORT, "http", "youtube.com"): {2}}, "NATIVE_LOG_PARSER_INVALID")
    need(not selections("desync profile 2 (known) matches\n"), "STARTUP_BANNER_FALSE_POSITIVE")
    print(MARK + "_SELF_TEST=PASS_ACTUAL_GENERATOR_ONLY", flush=True)


def stun_exchange() -> None:
    payload = b"\x00\x01\x00\x00\x21\x12\xa4\x42" + b"p0-generated"
    response = b"\x01\x01" + payload[2:]
    need(len(payload) == 20, "STUN_FIXTURE_SIZE")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
        server.settimeout(3)
        client.settimeout(3)
        server.bind((HOST, VOICE_PORT))
        client.sendto(payload, (HOST, VOICE_PORT))
        data, peer = server.recvfrom(1024)
        need(data == payload, "GENERATED_VOICE_CHANGED_STUN")
        server.sendto(response, peer)
        need(client.recv(1024) == response, "GENERATED_VOICE_REPLY_NOT_DELIVERED")


def native(checkout: Path) -> None:
    original, generator = modules()
    guard = original.guard_module()
    root, engine, before = guard.guest_gate(checkout)
    test, case, data, mapping = fixture(generator, root)
    process = None
    installed = []
    log = case / "engine.log"
    inbox, debug = case / "inbox.txt", case / "debug.log"
    raw_identity = (inbox.stat().st_dev, inbox.stat().st_ino)
    debug_identity = (debug.stat().st_dev, debug.stat().st_ino)
    observed_clients = []
    try:
        try:
            with log.open("wb") as output:
                process = subprocess.Popen([str(engine), *data["final"].decode().split()],
                                           cwd=root, stdout=output, stderr=subprocess.STDOUT)
                time.sleep(0.5)
                need(process.poll() is None, "GENERATED_ENGINE_START_FAILED")
                identity = guard.cmd("ps", "-p", str(process.pid), "-o", "lstart=")
                need(identity.returncode == 0 and identity.stdout.strip(), "NATIVE_PROCESS_IDENTITY_MISSING")
                for number, args in zip(RULES, rules()):
                    need(guard.cmd("/sbin/ipfw", "-q", "add", str(number), *args).returncode == 0,
                         "ISOLATED_GENERATED_DIVERT_ADD_FAILED")
                    installed.append(number)
                for host, port in (("youtube.com", PORT), ("example.org", MIXED_PORT),
                                   (IP_ONLY, MIXED_PORT), ("youtube.com", IMPORT_PORT),
                                   ("example.org", DEFAULT_PORT)):
                    need(original.exchange(host, port=port, force_rst=True) == original.request(host),
                         "GENERATED_AUTHORIZED_HTTP_NOT_DELIVERED")
                stun_exchange()
                time.sleep(0.25)
                need(inbox.read_bytes() == b"", "EXCLUDED_OR_KNOWN_FLOW_ENTERED_OBSERVER")
                need(original.exchange(UNKNOWN, port=PORT, force_rst=True,
                     client_ports=observed_clients) == original.request(UNKNOWN), "UNKNOWN_HTTP_CHANGED_BEFORE_APPEND")
                time.sleep(0.5)
                need(inbox.read_text().splitlines() == [UNKNOWN], "GENERATED_RAW_APPEND_NOT_CONFIRMED")
                need(original.exchange(UNKNOWN, port=PORT, force_rst=False) == original.request(UNKNOWN),
                     "UNKNOWN_HTTP_CHANGED_AFTER_APPEND")
                current = guard.cmd("ps", "-p", str(process.pid), "-o", "lstart=")
                need(process.poll() is None and current.returncode == 0 and current.stdout == identity.stdout,
                     "GENERATION_PROCESS_CHANGED")
                need(data["final"] == (case / "final").read_bytes(), "GENERATED_ARGV_CHANGED")
                for number in RULES:
                    counter = guard.cmd("/sbin/ipfw", "-a", "list", str(number))
                    need(counter.returncode == 0 and re.search(rf"(?m)^0*{number}\s+[1-9]\d*\s+", counter.stdout),
                         "GENERATED_BIDIRECTIONAL_CAPTURE_NOT_CONFIRMED")
        finally:
            cleanup = []
            for number in reversed(installed):
                if guard.cmd("/sbin/ipfw", "-q", "delete", str(number)).returncode:
                    cleanup.append("GENERATED_RULE_DELETE_FAILED")
            if process is not None:
                if process.poll() is None:
                    process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            listing = guard.cmd("/sbin/ipfw", "-q", "list")
            if listing.returncode != 0 or listing.stdout != before:
                cleanup.append("GENERATED_IPFW_RESTORE_FAILED")
            if guard.cmd("pgrep", "-x", "dvtws2").returncode != 1:
                cleanup.append("GENERATED_ENGINE_REMAINS")
            need(not cleanup, ";".join(cleanup))

        content = log.read_text(errors="replace")
        attest_selections(content)
        need("* lua 'multisplit" in content, "AUTHORIZED_LUA_NOT_EXERCISED")
        need((inbox.stat().st_dev, inbox.stat().st_ino) == raw_identity and
             (debug.stat().st_dev, debug.stat().st_ino) == debug_identity,
             "RAW_DEBUG_FILE_GENERATION_CHANGED")
        positives = [line for line in debug.read_text().splitlines() if " : adding to " in line]
        need(len(positives) == 1 and re.search(
             re.escape(UNKNOWN) + r" : profile 6 \([^)]*\) : client " + re.escape(HOST) +
             ":" + str(observed_clients[0]) + r" : proto http : adding to " + re.escape(str(inbox)),
             positives[0]), "RAW_DEBUG_PROFILE_CLIENT_CORRELATION_MISSING")
        api = test.implementation()
        observer = api.lookup(mapping, data["generation"], data["final"], 6)
        need(observer is not None and observer["hostlist"] is None and observer["role"] == "extra",
             "RAW_EVENT_GUESSED_KNOWN_HOSTLIST")
        need(api.lookup(mapping, "stale", data["final"], 6) is None, "STALE_RAW_ATTRIBUTION_ACCEPTED")
        print(json.dumps(dict(generation=data["generation"], final_args_sha256=hashlib.sha256(data["final"]).hexdigest(),
              native_profile_numbers=[1, 2, 3, 4, 5, 6, 0], observer=6,
              known_hostlist_source=3, mixed_source=4, raw_events=1,
              raw_debug_same_generation=True, unknown_http_unchanged=True,
              ipfw_restored=True, engine_stopped=True)), flush=True)
        print(MARK + "=PASS_NATIVE_GENERATED_AUTO_MAP_LOOPBACK_ONLY", flush=True)
    except BaseException:
        if log.exists():
            print("P0_GENERATED_ENGINE_DIAGNOSTIC_TAIL\n" + log.read_text(errors="replace")[-14000:],
                  file=sys.stderr, flush=True)
        raise
    finally:
        test.doCleanups()


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif len(sys.argv) == 3 and sys.argv[1] == "--native":
            native(Path(sys.argv[2]))
        else:
            raise RuntimeError("usage: --self-test | --native /tmp/p4c3-native-*")
    except Exception as exc:
        print(MARK + "=REFUSED:" + str(exc), file=sys.stderr, flush=True)
        raise SystemExit(2)
