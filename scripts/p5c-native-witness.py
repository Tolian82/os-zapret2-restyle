#!/usr/bin/env python3
"""P5c one disposable installed configd preview witness (not owner/browser proof).

No additional original-builder native matrix: one existing installed package,
one upstream setup, and STOPPED/RUNNING/missing-runtime/stale-tab API boundary.
"""
import base64
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path("/conf/config.xml")
SERVICE = Path("/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
CLI = "/usr/local/sbin/configctl"


def load_helpers():
    spec = importlib.util.spec_from_file_location(
        "p5c_existing_witness", ROOT / "scripts/p5b2b-native-witness.py"
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def native():
    h = load_helpers()
    h.need(
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1"
        and os.environ.get("ZAPRET2_P5C_DISPOSABLE_NATIVE") == "1"
        and platform.system() == "FreeBSD"
        and os.geteuid() == 0
        and SERVICE.is_file() and CONFIG.is_file()
        and h.run("pkg", "info", "-e", "os-zapret2-restyle", timeout=12).returncode == 0,
        "not-disposable-installed-OPNsense",
    )

    def envelope(fields, baseline=None):
        active = ET.fromstring(CONFIG.read_bytes())
        node = active.find("./OPNsense/Zapret/hostlist/telegramips")
        token = "" if node is None or node.text is None else node.text
        if baseline is not None:
            token = baseline
        data = {"page": "strategies", "fields": fields,
                "sync": {"telegramips_baseline": token}}
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    def under_fd9_snapshot():
        h.hold_fd9()
        try:
            return h.snapshot()
        finally:
            os.close(9)

    def preview(label, fields=None, baseline=None, native_expected=None):
        before = under_fd9_snapshot()
        command = h.run(CLI, "zapret", "strategy_preview",
                        envelope(fields or {}, baseline), timeout=165)
        after = under_fd9_snapshot()
        h.need(before == after, "mutated-permanent-state:" + label)
        h.need(not list(Path("/tmp").glob("zapret-p5b-*")),
               "private-preview-workspace-left:" + label)
        h.need(command.returncode == 0, "configd-exit:" + label)
        try:
            response = json.loads(command.stdout.decode("utf-8").strip())
        except (UnicodeError, ValueError):
            raise RuntimeError("P5C_REFUSED:non-json-configd-reply:" + label) from None
        h.need(response.get("result") == "preview" and
               response.get("saved") is False and response.get("applied") is False and
               response.get("safe_to_apply") is False, "unsafe-receipt:" + label)
        if native_expected is not None:
            n = response.get("native_validation", {})
            h.need(n.get("engine_native_dry_run") == native_expected and
                   n.get("mapped_validation") == "native_mapped_valid",
                   "native-dry-run-not-attested:" + label)
        return response

    # Select a real WAN model field on this ONE disposable guest only, well
    # before any measured preview, as required by the original native builder.
    h.set_guest_lo0()
    h.need(not Path("/usr/local/etc/zapret2/binaries/my/dvtws2").exists(),
           "runtime-before-install")
    pre = preview("missing-runtime")
    h.need(pre["native_validation"]["engine_native_dry_run"] != "passed",
           "false-runtime-availability")
    install_spec = importlib.util.spec_from_file_location(
        "p5c_g03", ROOT / "scripts/stage2-opnsense-g03-first-install.py"
    )
    g03 = importlib.util.module_from_spec(install_spec)
    install_spec.loader.exec_module(g03)
    installed = g03.dispatch_and_poll()
    h.need(installed["installed"] == "1" and installed["service"] == "stopped",
           "engine-setup-refused")

    # Native changes in the API submission must never write a saved list.
    preview("stopped-unsaved-domain", {
        "hostlist": {"userdomains": "p5c-only.example.com"}
    }, native_expected="passed")
    invalid = preview("stale-telegram-baseline", baseline="deliberately-stale")
    h.need(invalid["status"] == "NATIVE_CANDIDATE_REFUSED" and
           invalid["native_validation"]["engine_native_dry_run"] == "not_run",
           "stale-baseline-not-refused")

    started = False
    try:
        h.need(h.run(CLI, "zapret", "start", timeout=100).returncode == 0,
               "disposable-service-start")
        started = True
        preview("running-unsaved-domain", {
            "hostlist": {"userdomains": "p5c-only.example.com"}
        }, native_expected="passed")
    finally:
        if started:
            h.need(h.run(CLI, "zapret", "stop", timeout=100).returncode == 0,
                   "disposable-service-stop")
    print("P5C_NATIVE=" + json.dumps({
        "status": "PASS_NATIVE_CONFIGD_UNSAVED_PREVIEW_NO_MUTATION",
        "scenarios": ["missing-runtime", "stopped-unsaved-domain",
                      "stale-telegram-baseline", "running-unsaved-domain"],
        "browser_ru_en": False, "owner_appliance": False, "p6_accepted": False,
    }, sort_keys=True))


def self_test():
    h = load_helpers()
    h.need(not (platform.system() == "FreeBSD" and
                os.environ.get("ZAPRET2_P5C_DISPOSABLE_NATIVE") == "1"),
           "fast-mode-native-optin")
    print("P5C_NATIVE_FAST=PASS")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif sys.argv[1:] == ["--native"]:
        native()
    else:
        raise SystemExit("usage: --self-test|--native")
