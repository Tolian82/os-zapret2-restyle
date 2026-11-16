#!/usr/bin/env python3
"""OWN70 STEP 1: actual _70 -> staged exact .pkg FD9 rescue -> native pkg add.

ONE disposable OPNsense VM only. Never run on an owner appliance. The source
package is not an installer; its trusted, uninstalled service tree is used
only for the original FD9 recovery and for existing pkg-hook SERVICE_SCRIPT.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SERVICE_REL = "opnsense/scripts/OPNsense/Zapret"
SERVICE = Path("/usr/local") / SERVICE_REL / "zapret_service.sh"
JOURNAL = Path("/var/db/zapret2/shared-apply/operation.json")
EPOCHS = Path("/var/db/zapret2/auto-detect-epochs")
ACTIVE = Path("/usr/local/etc/zapret2/runtime-v2")
PKG_NAME = "os-zapret2-restyle"
OLD_URL = ("https://github.com/Tolian82/os-zapret2-restyle/releases/"
           "download/v0.6.5_70/os-zapret2-restyle-0.6.5_70.pkg")
OLD_SHA256 = "18acb1793410c055820737c5a30eb9a317208f1aa6a70e7bbaccf1ad1c701644"
HEX32 = re.compile(r"[0-9a-f]{32}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")


class Refused(RuntimeError):
    pass


def need(value, reason):
    if not value:
        raise Refused(reason)


def run(argv, *, timeout=180, env=None):
    try:
        return subprocess.run(argv, capture_output=True, text=True,
                              timeout=timeout, check=False, env=env)
    except (OSError, subprocess.SubprocessError):
        raise Refused("native_command_unavailable_or_timeout:" + argv[0]) from None


def require(argv, reason, *, timeout=180, env=None):
    result = run(argv, timeout=timeout, env=env)
    need(result.returncode == 0, reason + ":rc=" + str(result.returncode))
    return result.stdout.strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(pkg):
    return json.loads(require(
        ["/usr/bin/tar", "-xOf", str(pkg), "+MANIFEST"], "native_pkg_manifest"))


def request(mode):
    need(mode in ("list", "auto"), "invalid_test_mode")
    xml = ET.fromstring(Path("/conf/config.xml").read_bytes())
    tg = xml.find("./OPNsense/Zapret/hostlist/telegramips")
    baseline = "" if tg is None or tg.text is None else tg.text
    fields = {"mode": mode}
    if mode == "list":
        source = xml.find("./OPNsense/Zapret/hostlist/youtubedomains")
        current = "" if source is None or source.text is None else source.text
        fields["youtubedomains"] = current.rstrip("\n") + "\nbridge-test.example.org\n"
    payload = {"page": "strategies", "fields": {"hostlist": fields},
               "sync": {"telegramips_baseline": baseline}}
    return base64.urlsafe_b64encode(json.dumps(
        payload, separators=(",", ":")).encode()).decode().rstrip("=")


def safe_member(member, prefix):
    # A package list entry must name a canonical relative regular source.
    path = PurePosixPath(member)
    cleaned = member.removeprefix("./")
    return (not member.startswith("/") and
            not member.startswith("../") and
            all(part not in (".", "..", "") for part in cleaned.split("/")) and
            cleaned.startswith(prefix + "/") and
            len(cleaned) <= 512 and
            path.name not in (".", ".."))


def staged_source(pkg, root):
    """Read only exact archive members under one protected unpublished tree."""
    need(root.is_dir() and not root.is_symlink() and
         root.stat().st_uid == 0 and stat.S_IMODE(root.stat().st_mode) == 0o700,
         "untrusted_staging_root")
    m = manifest(pkg)
    need(m.get("name") == PKG_NAME and m.get("abi") == "FreeBSD:15:amd64",
         "wrong_staged_native_manifest")
    tar = require(["/usr/bin/tar", "-tf", str(pkg)], "archive_index", timeout=40)
    prefix = "usr/local/" + SERVICE_REL
    entries = tar.splitlines()
    matches = [x for x in entries if safe_member(x, prefix)]
    need(len(matches) >= 100 and len(matches) == len(set(matches)),
         "incomplete_or_duplicated_staged_source")
    need(all(("/" + x.removeprefix("./")) in m.get("files", {})
             for x in matches), "unmanifested_staged_source")
    needed = ("/zapret_service.sh", "/python_runtime.sh",
              "/shared_apply_config.php",
              "/backend/shared_apply_operation.py",
              "/backend/auto_detect_owner.py",
              "/backend/auto_detect_post_drop.py")
    need(all(any(x.removeprefix("./").endswith(prefix + name) for x in matches)
                 for name in needed), "missing_native_rescue_components")
    # The local root staging is NOT the live /usr/local tree. All files
    # originate from the one verified .pkg, with no alternate installer.
    listing = require(["/usr/bin/tar", "-tvf", str(pkg)], "archive_types", timeout=40)
    trusted = [x for x in listing.splitlines()
               if any(x.endswith(" " + item) for item in matches)]
    need(len(trusted) == len(matches) and
         all(line.startswith("-") for line in trusted),
         "nonregular_staged_archive_entry")
    require(["/usr/bin/tar", "-xf", str(pkg), "-C", str(root), *matches],
            "archive_staging_refused", timeout=90)
    stage = root / prefix
    for x in matches:
        item = root / x.removeprefix("./")
        info = item.lstat()
        need(stat.S_ISREG(info.st_mode) and info.st_uid == 0 and
             info.st_nlink == 1 and not item.is_symlink(),
             "nonregular_staged_runtime_source")
    for name in needed:
        item = stage / name.lstrip("/")
        need(item.is_file() and not item.is_symlink(),
             "staged_component_missing")
    need(stat.S_IMODE((stage / "zapret_service.sh").stat().st_mode) == 0o755 and
         stat.S_IMODE((stage / "python_runtime.sh").stat().st_mode) == 0o755,
         "staged_executable_mode_changed")
    # Physical archive source must also be identical to exact checked-out
    # commit, not merely point at an arbitrary executable in /root.
    for name in needed:
        source = ROOT / "src" / SERVICE_REL / name.lstrip("/")
        need(source.is_file() and sha(source) == sha(stage / name.lstrip("/")),
             "staged_source_differs_from_qualified_candidate")
    return stage


def recovered_status(stage, action, *, optin=False, timeout=180):
    environment = dict(os.environ)
    environment.update({
        "SCRIPT_DIR": str(stage),
        "BACKEND_DIR": str(stage / "backend"),
        "PYTHON_RUNTIME": str(stage / "python_runtime.sh"),
    })
    if optin:
        environment["ZAPRET_OWNER_REVIEW_RECOVERY"] = "1"
    else:
        environment.pop("ZAPRET_OWNER_REVIEW_RECOVERY", None)
    return run(["/bin/sh", str(stage / "zapret_service.sh"), action],
               env=environment, timeout=timeout)


def native():
    import platform
    need(os.geteuid() == 0 and platform.system() == "FreeBSD" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_OWN70_NATIVE_BRIDGE") == "1" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1" and
         os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1",
         "disposable_opnsense_root_only")
    builder_spec = importlib.util.spec_from_file_location(
        "own70_native_pkg_builder", HERE / "native-opnsense-package.py")
    native_builder = importlib.util.module_from_spec(builder_spec)
    builder_spec.loader.exec_module(native_builder)
    native_builder.gate()
    need(run(["pkg", "info", "-e", PKG_NAME], timeout=20).returncode == 1,
         "disposable_guest_already_has_plugin")
    result = native_builder.build()
    pkg = ROOT / result["output"]
    need(sha(pkg) == result["real_native_pkg"]["sha256"] and
         manifest(pkg).get("version") == (
             (ROOT / "VERSION").read_text().strip() + "_" +
             re.search(r"PLUGIN_REVISION=\s*(\d+)", (ROOT / "Makefile").read_text()).group(1)),
         "candidate_native_pkg_not_exact")

    old = Path("/root/os-zapret2-restyle-0.6.5_70.pkg")
    require(["fetch", "-o", str(old), OLD_URL], "published_old_archive_fetch",
            timeout=100)
    need(sha(old) == OLD_SHA256 and
         manifest(old).get("version") == "0.6.5_70" and
         manifest(old).get("abi") == "FreeBSD:15:amd64",
         "historical_owner_pkg_sha_or_abi_changed")
    require(["pkg", "add", "-f", str(old)], "old_pkg_genuine_install",
            timeout=180)
    need(run([str(SERVICE), "status"], timeout=20).returncode == 1,
         "old_installed_cold_status_missing")

    def load_hyphenated(filename, identity):
        spec = importlib.util.spec_from_file_location(identity, HERE / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    witness = load_hyphenated("p5b2b-native-witness.py", "own70_p5b_fixture")
    witness.set_guest_lo0()
    g03 = load_hyphenated("stage2-opnsense-g03-first-install.py", "own70_g03_fixture")
    status = g03.dispatch_and_poll()
    need(status["installed"] == "1", "old_upstream_install_refused")
    require(["/usr/local/sbin/configctl", "zapret", "start"],
            "old_native_initial_start", timeout=130)

    # One genuine ordinary List common owner must exist as predecessor.
    old_list = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                    "strategies", request("list")], timeout=240)
    need(old_list.returncode == 0 and "applied-id=" in old_list.stdout,
         "old_installed_list_owner_not_committed")
    baseline = json.loads(JOURNAL.read_bytes())
    need(baseline.get("phase") == "committed" and
         run([str(SERVICE), "status"], timeout=20).returncode == 0,
         "old_list_not_running_committed")
    base_id = baseline["detail"]["id"]

    # This is the owner's actual GUI/configd entrypoint and published _70
    # code; never fabricate journal/epoch or forcibly kill a real process.
    broken = run(["/usr/local/sbin/configctl", "zapret", "shared_apply",
                  "strategies", request("auto")], timeout=240)
    state = json.loads(JOURNAL.read_bytes())
    generation = state["detail"]["id"]
    need(state.get("previous", {}).get("id") == base_id and
         state["detail"]["changed_fields"] == ["hostlist.mode"] and
         HEX32.fullmatch(generation), "native_old_auto_did_not_change_mode")
    reproduced = (broken.returncode != 0)
    if reproduced:
        need(state.get("phase") == "requires-review" and
             (EPOCHS / generation / "pretraffic.json").is_file() and
             not (EPOCHS / generation / "epoch.json").exists() and
             run([str(SERVICE), "status"], timeout=20).returncode == 2,
             "published_old_failure_did_not_match_observed_owner")
    else:
        # The fixture may produce shorter argv than the owner's real 2410
        # bytes. A successful ordinary Auto is NOT evidence of reviewed
        # recovery: qualify only the staged-hook RUNNING upgrade in this run.
        need(state.get("phase") == "committed" and
             (EPOCHS / generation / "epoch.json").is_file() and
             run([str(SERVICE), "status"], timeout=20).returncode == 0,
             "old_auto_was_neither_healthy_nor_reviewed")

    before_config = sha(Path("/conf/config.xml"))
    engine_pid = Path("/var/run/dvtws2.pid").read_text().strip().split()[0]
    need(engine_pid.isdecimal() and
         (ACTIVE / "auto-detect-generation.json").is_file(),
         "original_engine_or_map_not_running")

    # Use the exact SAME future .pkg, without installing its files,
    # replacing the old service or skipping any pkg hook.
    with tempfile.TemporaryDirectory(prefix="zapret-pkg-bridge-", dir="/root") as tmp:
        root = Path(tmp)
        os.chmod(root, 0o700)
        stage = staged_source(pkg, root)
        denied = recovered_status(stage, "shared-apply-recover-reviewed-native")
        need(denied.returncode == 75, "root_optin_gate_not_enforced")
        if reproduced:
            need(not (EPOCHS / generation / "epoch.json").exists(),
                 "denied_root_optin_mutated_epoch")
            rescue = recovered_status(stage, "shared-apply-recover-reviewed-native",
                                      optin=True, timeout=150)
            need(rescue.returncode == 0 and
                 "recovered-reviewed-native-id=" + generation in rescue.stdout and
                 (EPOCHS / generation / "epoch.json").is_file() and
                 json.loads(JOURNAL.read_bytes())["phase"] == "committed" and
                 sha(Path("/conf/config.xml")) == before_config,
                 "staged_package_original_fd9_recovery_unproven")

        # Both incoming and installed old hooks accept SERVICE_SCRIPT. They
        # still execute unchanged through genuine native pkg add -f.
        # Incoming PRE_INSTALL sees running=0, creates restart intent,
        # invokes the corrected staged Stop; old PRE_DEINSTALL sees STOPPED.
        # New POST_INSTALL starts the genuinely installed successor.
        override = dict(os.environ)
        override.update({
            "SERVICE_SCRIPT": str(stage / "zapret_service.sh"),
            "SCRIPT_DIR": str(stage),
            "BACKEND_DIR": str(stage / "backend"),
            "PYTHON_RUNTIME": str(stage / "python_runtime.sh"),
        })
        update = run(["pkg", "add", "-f", str(pkg)], timeout=210, env=override)
        need(update.returncode == 0, "native_old_hook_handoff_refused:" +
             str(update.returncode))
    version = require(["pkg", "query", "%v", PKG_NAME],
                      "installed_successor_version")
    need(version == manifest(pkg)["version"] and
         sha(Path("/conf/config.xml")) == before_config and
         run([str(SERVICE), "status"], timeout=30).returncode == 0 and
         not Path("/var/run/zapret2-restyle/pkg-replacement.restart").exists(),
         "native_pkg_successor_did_not_resume")
    new = json.loads(JOURNAL.read_bytes())
    need(new["phase"] == "committed" and new["detail"]["id"] != generation and
         (EPOCHS / generation / "retired.json").is_file() and
         (EPOCHS / new["detail"]["id"] / "epoch.json").is_file(),
         "old_auto_epoch_not_retired_or_successor_not_committed")
    print("OWN70_NATIVE_BRIDGE=" + json.dumps({
        "result": ("PASS_REAL_OLD_AUTO_FAIL_STAGED_RESCUE_PKG_ADD_RUNNING"
                   if reproduced else
                   "PASS_REAL_OLD_AUTO_RUNNING_STAGED_HOOK_PKG_ADD_ONLY"),
        "old_pkg_sha256": OLD_SHA256,
        "successor_pkg_sha256": sha(pkg),
        "old_requires_review_reproduced": reproduced,
        "original_fd9_epoch_completed": reproduced,
        "original_hook_source_bytes_unchanged": True,
        "native_pkg_add_completed": True,
        "old_auto_epoch_retired": True,
        "new_auto_epoch_committed": True,
        "saved_config_preserved": True,
        "new_service_running": True,
        "owner_appliance_modified": False,
    }, sort_keys=True))


def self_test():
    assert safe_member("./usr/local/opnsense/scripts/OPNsense/Zapret/a.py",
                       "usr/local/opnsense/scripts/OPNsense/Zapret")
    for name in ("/usr/local/opnsense/scripts/OPNsense/Zapret/a.py",
                 "../usr/local/opnsense/scripts/OPNsense/Zapret/a.py",
                 "usr/local/opnsense/scripts/OPNsense/Zapret/../a.py",
                 "usr/local/opnsense/scripts/OPNsense/Zapret/a.py/../../b"):
        need(not safe_member(name, "usr/local/opnsense/scripts/OPNsense/Zapret"),
             "unsafe_archive_entry_accepted")
    print("OWN70_NATIVE_BRIDGE_SOURCE=PASS")


if __name__ == "__main__":
    try:
        if sys.argv[1:] == ["--self-test"]:
            self_test()
        elif sys.argv[1:] == ["--native"]:
            native()
        else:
            raise Refused("explicit_self_test_or_disposable_native_required")
    except (OSError, ValueError, TypeError, KeyError, Refused) as exc:
        print("OWN70_NATIVE_BRIDGE=REFUSED:" + str(exc), file=sys.stderr)
        raise SystemExit(2)
