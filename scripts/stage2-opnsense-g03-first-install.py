#!/usr/bin/env python3
"""G03 real configd → GUI-selected upstream first-install on disposable OPNsense."""
import base64
import hashlib
import json
import os
import re
import runpy
import secrets
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path("/usr/local/etc/zapret2")
STATE = Path("/var/db/zapret2-restyle")
LAUNCHER = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup_launcher.sh")
RELEASE = "v1.0.7"


class Refusal(Exception):
    pass


def need(condition, message):
    if not condition:
        raise Refusal(message)


def run(argv, timeout=45):
    return subprocess.run(argv, text=True, capture_output=True,
                          timeout=timeout, check=False)


def status():
    p = run([str(LAUNCHER), "status"])
    need(p.returncode == 0, "G03_RUNTIME_STATUS_FAILED")
    data = dict(line.split("=", 1) for line in p.stdout.splitlines() if "=" in line)
    need(set(data) >= {"installed", "service", "version", "setup", "busy"},
         "G03_RUNTIME_STATUS_FIELDS_MISSING")
    return data


def dispatch_and_poll():
    # The actual selected-release action used by ServiceController.php.
    response = run(["/usr/local/sbin/configctl", "zapret", "setup_install", RELEASE])
    need(response.returncode == 0 and response.stdout.strip() == "OK",
         "G03_NATIVE_CONFIGD_DISPATCH_FAILED:" + response.stderr[-250:])
    deadline = time.monotonic() + 300
    saw_busy = False
    while time.monotonic() < deadline:
        current = status()
        saw_busy |= current["busy"] == "1" or current["setup"] == "installing"
        if (current["busy"] == "0" and current["setup"] == "ready" and
            current["installed"] == "1" and current["service"] == "stopped" and
            current["version"] == RELEASE and saw_busy):
            return current
        if current["busy"] == "0" and current["setup"] == "failed" and saw_busy:
            raise Refusal("G03_SETUP_WORKER_REPORTED_FAILURE")
        time.sleep(1)
    raise Refusal("G03_INSTALL_DID_NOT_REACH_VERIFIED_READY_STOPPED")


def five_hostlist_native_apply(config_path: Path):
    """Exercise the installed configd/FD9 path on the existing G03 guest."""
    service = LAUNCHER.with_name("zapret_service.sh")
    configctl = "/usr/local/sbin/configctl"
    journal = Path("/var/db/zapret2/shared-apply/operation.json")
    pidfile = Path("/var/run/dvtws2.pid")
    editor_names = {"youtube": "youtube_found", "user": "user_found", "auto": "shared_found"}
    runpy.run_path(str(Path(__file__).with_name("p5b2b-native-witness.py")))["set_guest_lo0"]()

    gui = runpy.run_path(str(Path(__file__).with_name("stage2-opnsense-real-native-voice-http.py")))
    web = gui["GuestHttps"]()
    try:
        gui["login"](web)
    except gui["Refusal"] as error:
        raise Refusal("FIVE_HOSTLIST_HTTPS_LOGIN_REFUSED:" + str(error)) from None

    def read():
        try:
            data = web.api("POST", "/api/zapret/settings/hostlistEditorsRead")
        except gui["Refusal"] as error:
            raise Refusal("FIVE_HOSTLIST_HTTPS_READ_REFUSED:" + str(error)) from None
        need(data.get("result") == "ok", "FIVE_HOSTLIST_READ_REFUSED")
        return data

    def apply(fields, snapshot=None, drafts=None):
        root = ET.fromstring(config_path.read_bytes())
        baseline = root.findtext("./OPNsense/Zapret/hostlist/telegramips") or ""
        if snapshot is None:
            request = json.dumps({"page": "strategies", "fields": fields,
                                  "sync": {"telegramips_baseline": baseline}},
                                 separators=(",", ":")).encode()
            token = base64.urlsafe_b64encode(request).decode().rstrip("=")
            result = run([configctl, "zapret", "shared_apply", "strategies", token], timeout=180)
            receipt = result.stdout.splitlines()[-1] if result.stdout.strip() else ""
            need(result.returncode == 0, "FIVE_HOSTLIST_CONFIGD_UNAVAILABLE")
            return receipt
        sources = {}
        for short, key in editor_names.items():
            editor = snapshot["editors"][key]
            sources[short] = {
                "base": {name: editor[name] for name in ("status", "revision", "content")},
                "draft": drafts.get(short, editor["content"]),
            }
        payload = {"schema_version": 1, "kind": "tz6v2-found-form-intent",
                   "config_revision": snapshot["config_revision"], "sources": sources}
        raw = json.dumps(payload, separators=(",", ":")).encode()
        boundary = "zapret-" + secrets.token_hex(16)
        parts = []

        def part(name, value, file_upload=False):
            headers = ['Content-Disposition: form-data; name="' + name + '"']
            if file_upload:
                headers[0] += '; filename="found-intent.json"'
                headers.append('Content-Type: application/json')
            parts.extend([("--" + boundary).encode(), *(h.encode() for h in headers), b"", value])

        part("zapret[sync][telegramips_baseline]", baseline.encode())
        part("found_intent_expected", b"1")
        for group, values in fields.items():
            for field, value in values.items():
                part(f"zapret[{group}][{field}]", value.encode())
        part("found_intent", raw, file_upload=True)
        parts.extend([("--" + boundary + "--").encode(), b""])
        req = urllib.request.Request(
            gui["ORIGIN"] + "/api/zapret/settings/apply", data=b"\r\n".join(parts),
            headers={"Content-Type": "multipart/form-data; boundary=" + boundary,
                     "X-CSRFToken": web.csrf_token, "Accept": "application/json",
                     "Referer": gui["ORIGIN"] + "/ui/zapret/general"}, method="POST")
        try:
            with web.client.open(req, timeout=180) as response:
                reply = json.loads(response.read(2 * 1024 * 1024))
        except urllib.error.HTTPError as error:
            raise Refusal("FIVE_HOSTLIST_HTTPS_APPLY_STATUS_" + str(error.code)) from None
        need(isinstance(reply, dict), "FIVE_HOSTLIST_HTTPS_APPLY_NOT_OBJECT")
        phase = json.loads(journal.read_bytes()).get("phase")
        reason = str(reply.get("reason", ""))
        message = str(reply.get("message", ""))
        fixed_messages = (
            "Missing or invalid Strategies baseline", "Select a WAN interface",
            "Untrusted found upload", "Untrusted native PHP upload", "Invalid native PHP upload",
            "Native PHP upload", "Not a native PHP upload", "Unqualified native PHP upload",
            "The discovered lists upload was not received",
            "Shared Strategies request", "Voice or shared Strategies settings changed",
        )
        print("FIVE_HOSTLIST_HTTPS=" + json.dumps({
            "result": reply.get("result") if reply.get("result") in ("saved", "failed") else "unknown",
            "reason": reason if re.fullmatch(r"[a-z0-9-]{1,100}", reason) else "unspecified",
            "phase": phase, "requires_review": reply.get("requires_review") is True,
            "field_error": reply.get("found_error") == {"source": "auto", "line": 1},
            "message_code": next((prefix for prefix in fixed_messages if message.startswith(prefix)),
                                 "other" if message else "none"),
            "validation_fields": sorted((reply.get("validations") or {}).keys()),
        }), flush=True)
        return reply

    def assert_commit(receipt, label):
        match = re.fullmatch(r"applied-id=([0-9a-f]{32})", receipt)
        record = json.loads(journal.read_bytes())
        reason = receipt if re.fullmatch(r"preflight-rejected=[a-z0-9-]+", receipt) else "unconfirmed"
        need(match is not None and record.get("phase") == "committed" and
             record["detail"]["id"] == match[1], "FIVE_HOSTLIST_" + label + "_" + reason)

    assert_commit(apply({"hostlist": {"mode": "list"}}), "LIST_BOOT")
    initial_pid = pidfile.read_text().split()[0]
    base = read()
    old_config = hashlib.sha256(config_path.read_bytes()).hexdigest()
    old_operation = journal.read_bytes()
    invalid = apply({}, base, {"auto": "!example.net\n"})
    need(pidfile.read_text().split()[0] == initial_pid and
         hashlib.sha256(config_path.read_bytes()).hexdigest() == old_config and
         journal.read_bytes() == old_operation and read() == base,
         "FIVE_HOSTLIST_INVALID_DRAFT_CHANGED_SAVED_STATE_OR_PROCESS")
    invalid_confirmed = (invalid.get("result") == "failed" and
                         invalid.get("found_error") == {"source": "auto", "line": 1})

    manual = {"youtubedomains": "!blocked.example.com\nmanual-youtube.example.org",
              "userdomains": "^exact.example.org\nmanual-user.example.com"}
    drafts = {"youtube": "sub.zapret-youtube.org\n", "user": "zapret-user.com\n",
              "auto": "zapret-auto.net\n"}
    running_reply = apply({"hostlist": manual}, base, drafts)
    need(running_reply.get("result") == "saved" and running_reply.get("applied") is True and
         json.loads(journal.read_bytes()).get("phase") == "committed" and
         journal.read_bytes() != old_operation, "FIVE_HOSTLIST_RUNNING_NOT_COMMITTED")
    running = read()["editors"]
    need(run([str(service), "status"]).returncode == 0 and
         pidfile.read_text().split()[0] != initial_pid and
         running["youtube_manual"]["content"] == manual["youtubedomains"] and
         running["user_manual"]["content"] == manual["userdomains"] and
         running["youtube_found"]["content"] == "zapret-youtube.org\n" and
         running["user_found"]["content"] == drafts["user"] and
         running["shared_found"]["content"] == drafts["auto"],
         "FIVE_HOSTLIST_RUNNING_RESTART_OR_PERSISTENCE_UNVERIFIED")

    need(run([str(service), "stop"]).returncode == 0 and status()["service"] == "stopped",
         "FIVE_HOSTLIST_STOP_FAILED")
    same_config = hashlib.sha256(config_path.read_bytes()).hexdigest()
    before_stopped_apply = journal.read_bytes()
    stopped_reply = apply({}, read(), {"auto": ""})
    need(stopped_reply.get("result") == "saved" and stopped_reply.get("applied") is True and
         json.loads(journal.read_bytes()).get("phase") == "committed" and
         journal.read_bytes() != before_stopped_apply, "FIVE_HOSTLIST_STOPPED_NOT_COMMITTED")
    need(status()["service"] == "stopped" and not pidfile.exists() and
         read()["editors"]["shared_found"]["content"] == "" and
         hashlib.sha256(config_path.read_bytes()).hexdigest() == same_config,
         "FIVE_HOSTLIST_STOPPED_APPLY_STARTED_SERVICE_OR_CHANGED_CONFIG")
    need(invalid_confirmed, "FIVE_HOSTLIST_INVALID_DRAFT_LACKS_FIELD_ERROR")
    print("FIVE_HOSTLIST_NATIVE=PASS_HTTPS_RUNNING_RESTART_STOPPED_APPLY", flush=True)


def native_template_snapshot():
    """Stock configd may have rendered three non-engine outputs already."""
    names = {"zapret.conf", "hostlist.txt", "hostlist-exclude.txt"}
    need(not ROOT.is_symlink(), "G03_UPSTREAM_ROOT_IS_SYMLINK")
    if not ROOT.exists():
        return {}
    need(ROOT.is_dir(), "G03_UPSTREAM_ROOT_NOT_DIRECTORY")
    found = {}
    for p in ROOT.iterdir():
        need(p.name in names and p.is_file() and not p.is_symlink(),
             "G03_FOREIGN_UPSTREAM_ROOT_ENTRY:" + p.name)
        found[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return found


def main():
    need(os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_G03_DISPOSABLE_NATIVE") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "G03_DISPOSABLE_OPNSENSE_ONLY")
    need(Path("/usr/local/opnsense").is_dir() and LAUNCHER.is_file(),
         "G03_NOT_AN_INSTALLED_OPNSENSE_PLUGIN")
    template_before = native_template_snapshot()
    need(not (ROOT / ".git").exists() and
         not (ROOT / "binaries/my/dvtws2").exists(),
         "G03_ALREADY_HAS_UPSTREAM_ENGINE")
    need(not (STATE / "runtime.release").exists() and
         not (STATE / "first-install.intent").exists() and
         not (STATE / "runtime-rollback").exists(),
         "G03_OLD_RELEASE_OR_RECOVERY_PRESENT")
    initial = status()
    need(initial["installed"] == "0" and initial["busy"] == "0",
         "G03_ENGINE_ALREADY_INSTALLED")
    cfg = Path("/conf/config.xml")
    need(cfg.is_file() and not cfg.is_symlink(), "G03_CONFIG_MISSING")
    config_before = hashlib.sha256(cfg.read_bytes()).hexdigest()
    # A freshly installed disposable OPNsense guest may not have loaded
    # the IPFW kernel module yet. That is an acceptable baseline: this
    # first-runtime setup must not activate IPFW or create rules by itself.
    ipfw_before = run(["/sbin/ipfw", "list"], timeout=15)
    module_before = run(["/sbin/kldstat", "-n", "ipfw"], timeout=15)

    first = dispatch_and_poll()
    need((ROOT / "binaries/my/dvtws2").is_file() and
         os.access(ROOT / "binaries/my/dvtws2", os.X_OK),
         "G03_COMPILED_DVTWS2_MISSING")
    for relative, target in {
        "nfq2/dvtws2": "../binaries/my/dvtws2",
        "ip2net/ip2net": "../binaries/my/ip2net",
        "mdig/mdig": "../binaries/my/mdig",
    }.items():
        symlink = ROOT / relative
        need(symlink.is_symlink() and os.readlink(symlink) == target,
             "G03_EXPECTED_COMPILER_LINK_MISSING_OR_UNSAFE:" + relative)
    commit = run(["/usr/local/bin/git", "-C", str(ROOT), "rev-parse", "HEAD"])
    tag = run(["/usr/local/bin/git", "-C", str(ROOT), "rev-parse",
               "refs/tags/" + RELEASE + "^{commit}"])
    need(commit.returncode == 0 and tag.returncode == 0 and
         commit.stdout.strip() == tag.stdout.strip(),
         "G03_GIT_TARGET_NOT_EXACT_RELEASE")
    need((STATE / "runtime.release").read_text().strip() == RELEASE,
         "G03_COMMITTED_RELEASE_MARKER_MISSING")
    need(not Path(str(ROOT) + ".first-install").exists() and
         not (STATE / "first-install.intent").exists() and
         not (STATE / "runtime-rollback").exists(),
         "G03_FIRST_INSTALL_RESIDUE")
    for name, expected in template_before.items():
        candidate = ROOT / name
        need(candidate.is_file() and not candidate.is_symlink() and
             hashlib.sha256(candidate.read_bytes()).hexdigest() == expected,
             "G03_STOCK_CONFIGD_TEMPLATE_NOT_PRESERVED:" + name)
    # One genuine same-release reinstall tests the existing old-runtime path,
    # not a second package build or a separate VM.
    second = dispatch_and_poll()
    need(second == first, "G03_SAME_RELEASE_REINSTALL_STATE_CHANGED")
    need(hashlib.sha256(cfg.read_bytes()).hexdigest() == config_before,
         "G03_UNEXPECTED_OPNSENSE_CONFIG_MUTATION")
    after = run(["/sbin/ipfw", "list"], timeout=15)
    module_after = run(["/sbin/kldstat", "-n", "ipfw"], timeout=15)
    need(after.returncode == ipfw_before.returncode and
         after.stdout == ipfw_before.stdout and
         module_after.returncode == module_before.returncode and
         module_after.stdout == module_before.stdout,
         "G03_FIRST_INSTALL_CHANGED_IPFW_STATE")
    print("G03_NATIVE=" + json.dumps({
        "status": "PASS_G03_REAL_CONFIGD_FIRST_INSTALL_AND_REINSTALL",
        "engine_release": RELEASE,
        "installed": True,
        "service_stopped": True,
        "same_release_reinstalled": True,
        "original_fd9_transaction": True,
        "stock_configd_templates_preserved": True,
        "ipfw_initially_loaded": ipfw_before.returncode == 0,
        "no_foreign_config_or_ipfw_change": True,
        "owner_browser_tested": False
    }, sort_keys=True))
    five_hostlist_native_apply(cfg)


def bounded_disposable_failure_evidence():
    """Only on this disposable CI guest; never print Config or secrets."""
    log = Path("/var/log/zapret2/setup.log")
    if not log.is_file() or log.is_symlink():
        print("G03_SETUP_LOG=missing", file=sys.stderr)
    else:
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-36:]
        print("G03_SETUP_LOG_TAIL_BEGIN", file=sys.stderr)
        for line in tail:
            line = re.sub(r"https?://\S+", "[external-url]", line)
            line = re.sub(r"\b[A-Fa-f0-9]{40,}\b", "[digest]", line)
            if re.search(r"token|authorization|password|secret|api[_-]?key|credential", line, re.I):
                line = "[redacted sensitive log line]"
            print("G03_SETUP_LOG: " + line[:220], file=sys.stderr)
        print("G03_SETUP_LOG_TAIL_END", file=sys.stderr)
    for path in (STATE / "setup.status", STATE / "first-install.intent"):
        if path.is_file() and not path.is_symlink():
            # Intent/status contain only a bounded release identity/phase.
            values = path.read_text(errors="replace").splitlines()[:3]
            print(f"G03_STATE:{path.name}=" + "|".join(v[:65] for v in values),
                  file=sys.stderr)
    for item in (ROOT / ".git", Path(str(ROOT) + ".first-install"),
                 STATE / "runtime.release"):
        print(f"G03_PATH:{item.name} present={item.exists()} linked={item.is_symlink()}",
              file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (Refusal, OSError, subprocess.TimeoutExpired, ValueError) as exc:
        print("G03_NATIVE=REFUSED:" + str(exc), file=sys.stderr)
        if os.environ.get("ZAPRET2_G03_DISPOSABLE_NATIVE") == "1":
            bounded_disposable_failure_evidence()
        sys.exit(1)
