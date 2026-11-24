#!/usr/bin/env python3
"""S03e3: fail-closed evidence for genuine native WAN UserException in GUI.

This guard runs ONLY in the disposable OPNsense 26.7 guest after native plugin
install and BEFORE any saved WAN/engine setup. It is deliberately read-only:
prepare records Config/IPFW/process witnesses; verify requires exact parity.
A separate host Playwright script makes a REAL HTTPS POST to startAction; it
may only do so while this gate has proven an absent WAN, which causes
startAction to throw before parent::startAction and before physical Start.

The guest's own profile-locale changes occur OUTSIDE each witness interval.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

SCRIPT = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/wan_preflight.sh")
CONTROLLER = Path("/usr/local/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/ServiceController.php")
CONFIG = Path("/conf/config.xml")
MARKER = Path("stage5-browser-wan-ci.pub")
RECEIPT = Path("dist/s03e3-native-wan-refusal-witness.json")


class Refusal(Exception):
    pass


def need(condition, label):
    if not condition:
        raise Refusal(label)


def command(argv, timeout=20):
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=False, timeout=timeout)
        return (p.returncode, p.stdout, p.stderr)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("S03E3_NATIVE_QUERY_UNAVAILABLE") from None


def digest(data):
    return hashlib.sha256(data).hexdigest()


def guest_guard():
    need(sys.platform.startswith("freebsd") and os.geteuid() == 0 and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_STAGE5_BROWSER_WAN") == "1" and
         MARKER.is_file() and not MARKER.is_symlink() and
         MARKER.stat().st_size > 50,
         "S03E3_DISPOSABLE_OPNSENSE_GUARD_REFUSED")
    need(CONFIG.is_file() and not CONFIG.is_symlink() and
         SCRIPT.is_file() and not SCRIPT.is_symlink() and
         CONTROLLER.is_file() and not CONTROLLER.is_symlink(),
         "S03E3_INSTALLED_REAL_SOURCE_MISSING")
    source = CONTROLLER.read_text(encoding="utf-8")
    prefix = source.split("public function startAction(): array", 1)
    need(len(prefix) == 2, "S03E3_ACTUAL_START_ACTION_MISSING")
    body = prefix[1].split("private const RELEASE_PATTERN", 1)[0]
    need(body.count("configdRun('zapret wan_preflight'") == 1 and
         "throw new UserException(gettext('Select a WAN interface')" in body and
         body.find("throw new UserException(gettext('Select a WAN interface')") <
         body.find("return $this->verifiedLifecycleAction(\'start\');") and\n         "return parent::startAction();" not in body and
         "if ($result === 'wan-required')" in body,
         "S03E3_PRE_DISPATCH_USEREXCEPTION_GATE_CHANGED")
    # The native action is the genuinely installed PHP/configd preflight, not
    # a fixture. No script, XML, fd9, IPFW or process state is modified here.
    rc, output, _ = command([str(SCRIPT), "require"])
    need(rc == 0 and output == b"wan-required\n",
         "S03E3_WAN_REQUIRED_NOT_ATTESTED_BEFORE_BROWSER")
    rc, out, _ = command(["pkg", "info", "-e", "os-zapret2-restyle"])
    need(rc == 0, "S03E3_PLUGIN_NOT_INSTALLED")
    rc, proc, _ = command(["ps", "-axo", "command="])
    need(rc == 0 and b"dvtws2" not in proc and b"supervisor_loop.sh" not in proc,
         "S03E3_ENGINE_OR_SUPERVISOR_PRESENT")
    return True


def witness():
    guest_guard()
    rc, output, error = command(["/sbin/ipfw", "-q", "list"])
    kernel = (str(rc).encode() + b"\0" + output + b"\0" + error)
    return {
        "schema": 1,
        "config_sha256": digest(CONFIG.read_bytes()),
        "ipfw_read_sha256": digest(kernel),
        "wan_required": True,
        "engine_absent": True,
    }


def receipt_path(locale):
    need(locale in ("en", "ru"), "S03E3_INVALID_LOCALE_SCOPE")
    # The OPNsense VM wrapper may synchronize test-owned dist content across
    # shell steps. Never reuse a witness name between separate EN/RU phases.
    return RECEIPT.with_name("s03e3-native-wan-refusal-witness-" + locale + ".json")


def prepare(locale):
    target = receipt_path(locale)
    need(not target.exists() and not target.is_symlink(),
         "S03E3_RECEIPT_ALREADY_PRESENT_" + locale)
    observed = witness()
    target.parent.mkdir(parents=True, exist_ok=True)
    # No secrets are written: only digests and boolean witnesses.
    with target.open("x", encoding="utf-8") as out:
        os.chmod(target, 0o600)
        json.dump(observed, out, sort_keys=True)
        out.write("\n")
    print("S03E3_GENUINE_NATIVE_WAN_REQUIRED_PRE_DISPATCH_GUARD_" + locale.upper() + "=PASS")


def verify(locale):
    target = receipt_path(locale)
    need(target.is_file() and not target.is_symlink(),
         "S03E3_PREPARED_WITNESS_MISSING_" + locale)
    before = json.loads(target.read_text(encoding="utf-8"))
    need(before == witness(), "S03E3_REAL_BROWSER_CHANGED_CONFIG_IPFW_OR_ENGINE_" + locale)
    target.unlink()
    print("S03E3_REAL_BACKEND_USEREXCEPTION_NO_CONFIG_IPFW_ENGINE_CHANGE_" + locale.upper() + "=PASS")


def self_test():
    need(digest(b"alpha") != digest(b"beta"), "S03E3_BAD_DIGEST")
    need(not sys.platform.startswith("freebsd") or
         os.environ.get("ZAPRET2_STAGE5_BROWSER_WAN") != "1",
         "S03E3_SELF_TEST_ONLY_ON_HOST")
    need(receipt_path("en").name == "s03e3-native-wan-refusal-witness-en.json" and
         receipt_path("ru").name == "s03e3-native-wan-refusal-witness-ru.json",
         "S03E3_BAD_PER_LOCALE_WITNESS_PATH")
    print("S03E3_NATIVE_GUARD_SELF_TEST=PASS")


def main():
    try:
        args = sys.argv[1:]
        if args == ["--self-test"]:
            self_test()
        elif args in (["--prepare-en"], ["--prepare-ru"]):
            prepare(args[0][-2:])
        elif args in (["--verify-en"], ["--verify-ru"]):
            verify(args[0][-2:])
        else:
            raise Refusal("S03E3_BAD_MODE")
    except (Refusal, OSError, ValueError, KeyError) as exc:
        print("S03E3_NATIVE_FAIL=" + str(exc)[:160], file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
