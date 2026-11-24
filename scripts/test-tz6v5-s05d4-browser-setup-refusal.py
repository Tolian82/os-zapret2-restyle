#!/usr/bin/env python3
"""Exercise the installed first-install refusal and historical detail in Chromium."""
import hashlib
import os
from pathlib import Path
import runpy
import select
import shlex
import stat
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE_SETUP = Path("src/opnsense/scripts/OPNsense/Zapret/setup.sh")
SETUP = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/setup.sh")
STATE = Path("/var/db/zapret2-restyle")
STATUS = STATE / "setup.status"
PID = Path("/var/run/zapret2-restyle/setup.pid")
ENGINE = Path("/usr/local/etc/zapret2/binaries/my/dvtws2")
STAGE = Path("/usr/local/etc/zapret2.first-install")
GUEST = "/root/s05d4-browser-setup-refusal.py"
TITLE = {
    "en": "Last recorded first-install failure: could not obtain the list of stable Zapret2 releases.",
    "ru": "Последняя зафиксированная причина первой установки: не удалось получить список стабильных версий Zapret2.",
}
ERROR = {
    "en": "Could not obtain the list of stable Zapret2 releases. Reload and check the service state before retrying.",
    "ru": "Не удалось получить список стабильных версий Zapret2. Обновите страницу и проверьте состояние службы перед повтором.",
}
VERSION = "v1.0.7"
TERMINAL = b"failed\ncause=release-list-unavailable\n"


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def admitted():
    return (os.environ.get("GITHUB_ACTIONS") == "true" and
            os.environ.get("ZAPRET2_STAGE5_BROWSER_WAN") == "1")


def command(args, timeout=35, **kwargs):
    return subprocess.run(args, capture_output=True, timeout=timeout, check=False, **kwargs)


def absent(path):
    return not path.exists() and not path.is_symlink()


def fixture_script(original, cache):
    header, rest = original.split(b"\n", 1)
    need(header == b"#!/bin/sh", "SETUP_SHEBANG_CHANGED")
    return (header + b"\nexport FETCH_BIN=/usr/bin/false RELEASE_CACHE=" +
            shlex.quote(str(cache)).encode() + b"\n" + rest)


def replace_file(path, data, metadata):
    # Stage next to the original so that both replacement and restoration
    # are atomic. This applies only to the test guest's setup ingress.
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
        temporary = Path(f.name)
        try:
            f.write(data)
            f.flush()
            os.fchown(f.fileno(), metadata.st_uid, metadata.st_gid)
            os.fchmod(f.fileno(), stat.S_IMODE(metadata.st_mode))
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def expect_line(stream, expected, timeout=110):
    ready, _, _ = select.select([stream], [], [], timeout)
    need(ready and stream.readline().strip() == expected, "FIXTURE_PROTOCOL_" + expected)


def guest(original_sha):
    marker = HERE / "s05d4-disposable-ci.pub"
    need(admitted() and sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         marker.is_file() and not marker.is_symlink() and
         marker.read_bytes().startswith(b"ssh-ed25519 "),
         "DISPOSABLE_OPNSENSE_REQUIRED")
    need(command(["/usr/local/sbin/pkg", "info", "-e", "os-zapret2-restyle"]).returncode == 0,
         "INSTALLED_PLUGIN_REQUIRED")
    mode = SETUP.lstat()
    original = SETUP.read_bytes()
    need(stat.S_ISREG(mode.st_mode) and mode.st_uid == 0 and mode.st_nlink == 1 and
         hashlib.sha256(original).hexdigest() == original_sha,
         "INSTALLED_SETUP_NOT_SOURCE_IDENTICAL")
    inputs = [PID, ENGINE, STAGE, STATE / "first-install.intent", STATE / "runtime.release"]
    need(all(absent(p) for p in inputs), "COLD_PLUGIN_ONLY_REQUIRED")
    status_mode = None
    status_bytes = b""
    if not absent(STATUS):
        status_mode = STATUS.lstat()
        need(stat.S_ISREG(status_mode.st_mode) and status_mode.st_uid == 0 and
             status_mode.st_nlink == 1 and status_mode.st_size <= 128,
             "UNEXPECTED_ORIGINAL_SETUP_STATUS")
        status_bytes = STATUS.read_bytes()

    s04 = runpy.run_path(str(HERE / "s05d4-native-snapshot.py"))
    setup_script_changed = False
    with tempfile.TemporaryDirectory(prefix="s05d4-release-", dir=HERE) as work:
        cache = Path(work) / "release-cache"
        try:
            # First produce the historical record through the installed
            # setup transaction, original locks and actual resolver.
            result = command([str(SETUP.with_name("setup_transaction.sh")), "install", VERSION],
                             timeout=80, env={**os.environ, "FETCH_BIN": "/usr/bin/false",
                                              "RELEASE_CACHE": str(cache)})
            need(result.returncode == 69 and STATUS.read_bytes() == TERMINAL and
                 all(absent(p) for p in inputs), "ORIGINAL_SETUP_REFUSAL_NOT_RECORDED")

            # Give the page a valid selectable version. After it has loaded,
            # remove the test cache, forcing the next real configd query
            # through the same installed resolver to the failed fetch.
            cache.write_text(VERSION + "\n", encoding="ascii")
            original_check = fixture_script(original, cache)
            replace_file(SETUP, original_check, mode)
            setup_script_changed = True
            print("READY", flush=True)
            expect_line(sys.stdin, "BLOCK")
            cache.unlink()
            result = command([str(SETUP), "show"])
            need(result.returncode == 69 and not result.stdout, "RELEASE_LIST_STILL_AVAILABLE")

            def witness():
                observed = s04["snapshot"]()
                stable = {key: observed[key] for key in ("config", "engine", "kernel", "process")}
                for path in [STATUS, STATE / "runtime.release", STATE / "first-install.intent",
                             Path("/var/log/zapret2/setup.log"), PID, STAGE]:
                    stable[str(path)] = None if absent(path) else s04["file_record"](path)
                return stable

            before = witness()
            print("BLOCKED", flush=True)
            expect_line(sys.stdin, "VERIFY")
            need(witness() == before and all(absent(p) for p in inputs),
                 "BROWSER_CLICK_CHANGED_NATIVE_STATE")
        finally:
            if setup_script_changed:
                replace_file(SETUP, original, mode)
            if status_mode is None:
                STATUS.unlink(missing_ok=True)
            else:
                replace_file(STATUS, status_bytes, status_mode)
    need(SETUP.read_bytes() == original, "PACKAGE_SCRIPT_RESTORATION_FAILED")
    print("NATIVE_VERIFIED", flush=True)


def browser(mode):
    from playwright.sync_api import expect, sync_playwright

    need(admitted(), "DISPOSABLE_CHROMIUM_REQUIRED")
    p3 = runpy.run_path(str(HERE / "p3-browser-i18n.py"))
    ssh = Path(os.environ["RUNNER_TEMP"]) / "zapret2-browser-ssh"
    origin = p3["ORIGIN"]
    args = ["ssh", "-T", "-p", "32222", "-i", str(ssh / "key"),
            "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", "ConnectTimeout=20", "-o", "UserKnownHostsFile=" + str(ssh / "known_hosts"),
            "root@127.0.0.1", "env", "GITHUB_ACTIONS=true", "ZAPRET2_STAGE5_BROWSER_WAN=1",
            "/usr/local/bin/python3", GUEST, "--guest",
            hashlib.sha256(SOURCE_SETUP.read_bytes()).hexdigest()]
    with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          text=True, bufsize=1) as guest_process:
        try:
            expect_line(guest_process.stdout, "READY")
            with sync_playwright() as pw:
                chromium = pw.chromium.launch(
                    headless=True, executable_path=os.environ["STAGE5_LOCAL_CHROMIUM"])
                try:
                    context = chromium.new_context(ignore_https_errors=True)
                    page = context.new_page()
                    p3["login"](page)
                    p3["wait_native_load"](page, "/api/zapret/settings/get",
                                           "/ui/zapret", "frm_GeneralSettings")
                    p3["wait_locale"](page, mode)
                    select_version = page.locator("#zapretReleaseSelect")
                    select_version.select_option(VERSION, timeout=30000)
                    button = page.locator("#zapretReleaseApply")
                    expect(button).to_be_enabled(timeout=20000)
                    page.wait_for_function(
                        "(title) => document.querySelector('#zapretServiceStatus')?.title === title",
                        arg=TITLE[mode], timeout=25000)
                    guest_process.stdin.write("BLOCK\n")
                    guest_process.stdin.flush()
                    expect_line(guest_process.stdout, "BLOCKED")
                    def post_to(response, action):
                        return (response.request.method == "POST" and
                                response.url.split("?")[0] == origin + "/api/zapret/service/" + action)

                    with page.expect_response(lambda r: post_to(r, "runtime"),
                                              timeout=40000) as refresh:
                        with page.expect_response(lambda r: post_to(r, "install"),
                                                  timeout=35000) as installed:
                            button.click(timeout=15000)
                        result = installed.value
                    payload = result.json()
                    need(result.status == 500 and isinstance(payload, dict) and
                         payload.get("errorMessage") ==
                         "No stable bol-van/zapret2 releases could be obtained." and
                         bool(payload.get("errorTitle")), "REAL_INSTALL_HTTP_REFUSAL_MISSING")
                    state = refresh.value.json()
                    need(refresh.value.status == 200 and state.get("status") == "ok" and
                         state.get("busy") is False and state.get("installed") is False and
                         state.get("lastsetupfailure") == "release-list-unavailable",
                         "ORIGINAL_HISTORICAL_RECEIPT_NOT_RETAINED_AFTER_CLICK")
                    page.get_by_text(ERROR[mode], exact=True).wait_for(timeout=15000)
                    page.locator("#zapretReleaseApplyProgress:not(.fa-pulse)").wait_for(
                        state="attached", timeout=15000)
                    need(button.is_disabled(), "REVIEW_LOCK_LOST")
                    guest_process.stdin.write("VERIFY\n")
                    guest_process.stdin.flush()
                    expect_line(guest_process.stdout, "NATIVE_VERIFIED")
                finally:
                    chromium.close()
        finally:
            guest_process.stdin.close()
            guest_process.wait(timeout=35)
        need(guest_process.returncode == 0, "GUEST_FIXTURE_OR_RESTORATION_FAILED")
    print("S05D4_REAL_INSTALLED_CHROMIUM_HTTPS_RELEASE_REFUSAL_" + mode.upper() + "=PASS")


def self_test():
    original = SOURCE_SETUP.read_bytes()
    with tempfile.TemporaryDirectory(prefix="s05d4 source fixture ") as work:
        scratch = Path(work)
        cache = scratch / "releases"
        script = scratch / "setup.sh"
        lock = scratch / "lockf"
        script.write_bytes(fixture_script(original, cache))
        script.chmod(0o700)
        lock.write_text('#!/bin/sh\nshift 4\nexec "$@"\n', encoding="ascii")
        lock.chmod(0o700)
        cache.write_text(VERSION + "\n", encoding="ascii")
        env = {**os.environ, "STATE_DIR": work, "RUN_DIR": work, "LOCKF_BIN": str(lock)}
        args = [str(script), "show"]
        ready = command(args, env=env)
        need(ready.returncode == 0 and ready.stdout == (VERSION + "\n").encode(),
             "SOURCE_VALID_RELEASE_FIXTURE_FAILED")
        cache.unlink()
        blocked = command(args, env=env)
        need(blocked.returncode == 69 and not blocked.stdout, "SOURCE_UNAVAILABLE_RELEASE_FIXTURE_FAILED")
    print("S05D4_ORIGINAL_RESOLVER_FIXTURE_SOURCE=PASS")


if __name__ == "__main__":
    cli = sys.argv[1:]
    if cli == ["--self-test"]:
        self_test()
    elif cli in (["--browser-en"], ["--browser-ru"]):
        browser(cli[0][-2:])
    elif len(cli) == 2 and cli[0] == "--guest":
        guest(cli[1])
    else:
        sys.exit(64)
