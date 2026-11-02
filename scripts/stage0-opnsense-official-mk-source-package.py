#!/usr/bin/env python3
"""Stage 0: true official OPNsense Mk/plugins.mk source-package witness.

Constructs a non-publishable, NON-INSTALLABLE qualification artifact inside a
fresh disposable OPNsense 26.7 CI guest. Does not modify production builder,
pkgdb of zapret2, service, configd, /conf, IPFW or owner's FreeBSD.conf.

The partial artifact has project source and exact authoritative manual hooks,
but intentionally lacks separately sourced signed private curl-impersonate
assets. Its 0644 historical service executable is an explicit open blocker.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
UPSTREAM = "https://github.com/opnsense/plugins.git"
UPSTREAM_SHA = "79a5f88b7b27a706c10511ea5587c9d0e0dbdced"
REVISION = "57"
VERSION = "0.6.2"
NAME = "os-zapret2-restyle"
KEY = "ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK"
PHASES = {
    "+PRE_INSTALL": "pre-install",
    "+POST_INSTALL": "post-install",
    "+PRE_DEINSTALL": "pre-deinstall",
    "+POST_DEINSTALL": "post-deinstall",
}
SERVICE = "opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
CURL = "libexec/zapret2-restyle/curl-impersonate"


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def cmd(args, cwd=None, timeout=250):
    try:
        p = subprocess.run(args, cwd=cwd, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_COMMAND_UNAVAILABLE_OR_TIMEOUT:" + args[0]) from None
    need(p.returncode == 0, "NATIVE_COMMAND_FAILED:" + args[0] + ":" +
         (p.stdout + p.stderr)[-500:])
    return p.stdout.strip()


def guest_gate():
    need(os.environ.get(KEY) == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
         os.uname().machine == "amd64",
         "EXPLICIT_ISOLATED_OPNSENSE_CI_OPTIN_REQUIRED")
    spec = importlib.util.spec_from_file_location(
        "stage0_opnsense_guest", HERE / "stage0-opnsense-guest-readonly.py")
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)
    need(guest.evaluate(guest.observe()).get("status") ==
         "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
         "FRESH_OPNSENSE_26_7_KVM_IDENTITY_UNQUALIFIED")


def source_identity():
    expected = os.environ.get("ZAPRET2_STAGE0_PROJECT_SHA", "")
    need(re.fullmatch("[a-f0-9]{40}", expected) is not None,
         "PROJECT_EXACT_HEAD_SHA_REQUIRED")
    # Only this exact CI checkout is trusted for one read-only git command:
    # the throwaway guest runs root but checkout files belong to the runner.
    # Never change system/global safe.directory, never use wildcard trust.
    need(ROOT.is_dir() and not ROOT.is_symlink(),
         "PROJECT_CHECKOUT_DIRECTORY_UNQUALIFIED")
    observed = cmd(["git", "-c", "safe.directory=" + str(ROOT),
                    "-C", str(ROOT), "rev-parse", "HEAD"])
    need(observed == expected, "PROJECT_CHECKOUT_NOT_EXACT_CI_HEAD")
    make = (ROOT / "Makefile").read_text(encoding="utf-8")
    ver = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    need(re.search(r"(?m)^PLUGIN_REVISION=\s*" + REVISION + r"$", make) and
         ver == VERSION and
         "PLUGIN_NAME=        zapret2-restyle" in make and
         '.include "../../Mk/plugins.mk"' in make,
         "PROJECT_NATIVE_MAKEFILE_IDENTITY_MISMATCH")
    return expected


def qualify_python_provider():
    path = Path("/usr/local/bin/python3")
    need(path.exists(), "QUALIFIED_GENERIC_PYTHON_LINK_MISSING")
    py = cmd([str(path), "-V"])
    m = re.fullmatch(r"Python 3\.(\d+)\.\d+", py)
    need(m is not None, "GENERIC_PYTHON_VERSION_UNQUALIFIED")
    short = "3" + m.group(1)
    owner = cmd(["pkg", "which", "-q", str(path)])
    need(owner == "opnsense" or owner.startswith("opnsense-"),
         "GENERIC_PYTHON_LINK_NOT_OWNED_BY_OPNSENSE")
    provider = cmd(["pkg", "query", "%n|%o|%v", "python" + short])
    parts = provider.split("|")
    need(len(parts) == 3 and parts[0] == "python" + short and
         parts[1] == "lang/python" + short and parts[2],
         "QUALIFIED_PYTHON_PKG_PROVIDER_MISMATCH")
    return {"python_runtime": py, "native_plugin_python": short,
            "generic_python_link_owner": owner,
            "installed_python_provider": provider}


def clone_official(work):
    target = work / "plugins"
    cmd(["git", "init", "-q", str(target)], timeout=60)
    cmd(["git", "-C", str(target), "remote", "add", "origin", UPSTREAM])
    cmd(["git", "-C", str(target), "fetch", "--no-tags", "--depth", "1",
         "origin", UPSTREAM_SHA])
    cmd(["git", "-C", str(target), "checkout", "--quiet", "--detach", "FETCH_HEAD"])
    need(cmd(["git", "-C", str(target), "rev-parse", "HEAD"]) ==
         UPSTREAM_SHA, "OFFICIAL_OPNSENSE_PLUGIN_FRAMEWORK_SHA_MISMATCH")
    for rel in ("Mk/plugins.mk", "Mk/defaults.mk", "Mk/common.mk",
                "Scripts/version.sh", "Templates/version"):
        need((target / rel).is_file() and
             not (target / rel).is_symlink(), "PINNED_MK_FRAMEWORK_INCOMPLETE:" + rel)
    return target


def prepare_source(official):
    target = official / "security" / "zapret2-restyle"
    need(not target.exists(), "OFFICIAL_SNAPSHOT_TARGET_COLLISION")
    target.mkdir()
    for name in ("Makefile", "VERSION", "pkg-descr"):
        source = ROOT / name
        need(source.is_file() and not source.is_symlink(),
             "PROJECT_SOURCE_ENTRY_UNQUALIFIED:" + name)
        shutil.copy2(source, target / name)
    for name in ("opnsense", "etc"):
        source = ROOT / "src" / name
        need(source.is_dir() and not source.is_symlink(),
             "PROJECT_SOURCE_DIRECTORY_UNQUALIFIED:" + name)
        shutil.copytree(source, target / "src" / name, symlinks=True)
    for old in PHASES:
        source = ROOT / "pkg" / old
        need(source.is_file() and not source.is_symlink(),
             "AUTHORITATIVE_HOOK_MISSING:" + old)
        shutil.copy2(source, target / old)
    return target


def mkvar(plugin, sha, key):
    return cmd(["make", "-C", str(plugin), "PLUGIN_HASH=" + sha,
                "PLUGIN_WWW=https://github.com/Tolian82/os-zapret2-restyle",
                "-V", key])


def native_variables(plugin, sha, provider):
    names = ("PLUGIN_PKGNAME", "PLUGIN_PKGVERSION", "PLUGIN_ABI",
             "PLUGIN_PYTHON", "PLUGIN_HASH", "PLUGIN_WWW",
             "PLUGIN_DEPENDS", "PLUGIN_DEVEL")
    got = {name: mkvar(plugin, sha, name) for name in names}
    need(got["PLUGIN_PKGNAME"] == NAME and
         got["PLUGIN_PKGVERSION"] == VERSION + "_" + REVISION and
         got["PLUGIN_ABI"] == "26.7" and
         got["PLUGIN_PYTHON"] == provider["native_plugin_python"] and
         got["PLUGIN_HASH"] == sha and
         got["PLUGIN_WWW"] == "https://github.com/Tolian82/os-zapret2-restyle" and
         got["PLUGIN_DEVEL"] == "",
         "OFFICIAL_MK_VARIABLE_EVALUATION_MISMATCH:" + repr(got))
    # Existing product Makefile still declares hardcoded python313; this
    # remains a Stage 2/3 migration defect, never normalized in this test.
    need(got["PLUGIN_DEPENDS"] == "python313",
         "CURRENT_SOURCE_DEPENDENCY_NOT_AS_AUDITED")
    return got


def manifest_identity(manifest, plugin, provider):
    need(manifest.get("name") == NAME and
         manifest.get("version") == VERSION + "_" + REVISION and
         manifest.get("origin") == "opnsense/" + NAME and
         manifest.get("www") == "https://github.com/Tolian82/os-zapret2-restyle",
         "NATIVE_PACKAGE_ORIGIN_OR_VERSION_WRONG")
    deps = manifest.get("deps")
    need(isinstance(deps, dict) and
         set(deps) == {"python313"} and
         isinstance(deps["python313"], dict) and
         deps["python313"].get("origin") == "lang/python313" and
         deps["python313"].get("version") ==
            provider["installed_python_provider"].split("|")[2],
         "NATIVE_PACKAGE_PROVIDER_DEPENDENCY_UNQUALIFIED")
    scripts = manifest.get("scripts")
    need(isinstance(scripts, dict) and set(scripts) == set(PHASES.values()),
         "NATIVE_SCRIPTS_MANUAL_PHASE_SET_CHANGED")
    for name, phase in PHASES.items():
        src = (plugin / name).read_bytes()
        target = scripts.get(phase)
        need(isinstance(target, str),
             "NATIVE_SCRIPT_NOT_UTF8_TEXT:" + phase)
        actual = target.encode()
        # Real OPNsense pkg 2.8 serializes literal '%' as '%25' in
        # +MANIFEST scripts and removes exactly ONE terminal LF. The former
        # is reversed by pkg_manifest.c url_decode() when reading; omitting
        # the terminal LF is shell-equivalent only for a verified final LF.
        # Do not admit any other change, whitespace shift or script rewrite.
        need(src.endswith(b"\n") and not src.endswith(b"\n\n"),
             "AUTHORITATIVE_HOOK_SINGLE_TERMINAL_LF_REQUIRED:" + phase)
        expected = src.replace(b"%", b"%25")[:-1]
        if actual != expected:
            first = next((i for i, (left, right) in
                          enumerate(zip(expected, actual)) if left != right),
                         min(len(expected), len(actual)))
            staged_file = plugin / "work" / "src" / name
            staged = staged_file.read_bytes() if staged_file.is_file() else b""
            raise Refusal(
                "NATIVE_SCRIPTS_MANUAL_HOOK_BYTES_CHANGED:" + phase +
                ":staged_len=" + str(len(staged)) +
                ":staged_sha256=" + hashlib.sha256(staged).hexdigest() +
                ":staged_same_as_source=" + str(staged == src) +
                ":canonical_len=" + str(len(expected)) +
                ":expected_encoded_window_hex=" +
                    expected[max(0, first - 10):first + 10].hex() +
                ":archive_window_hex=" +
                    actual[max(0, first - 10):first + 10].hex() +
                ":source_len=" + str(len(src)) +
                ":archive_len=" + str(len(actual)) +
                ":first_diff=" + str(first) +
                ":source_sha256=" + hashlib.sha256(src).hexdigest() +
                ":canonical_sha256=" + hashlib.sha256(expected).hexdigest() +
                ":archive_sha256=" + hashlib.sha256(actual).hexdigest())
    files = manifest.get("files")
    need(isinstance(files, dict) and len(files) > 100,
         "NATIVE_SOURCE_FILE_INVENTORY_TOO_SMALL")
    service = "/usr/local/" + SERVICE
    need(service in files, "NATIVE_INSTALLED_SERVICE_PATH_MISSING")
    return len(files)


def exact_installed_tar_member(names, installed_relative):
    # Names from tar -tf may start with './', but must otherwise match the
    # absolute installed package pathname without suffix or basename guessing.
    need(installed_relative and not installed_relative.startswith("/") and
         ".." not in Path(installed_relative).parts,
         "INSTALLED_TAR_MEMBER_INPUT_UNQUALIFIED")
    key = "usr/local/" + installed_relative
    matches = [name for name in names if name.lstrip("./") == key]
    need(len(matches) == 1, "OFFICIAL_ARCHIVE_SERVICE_MEMBER_UNQUALIFIED")
    return matches[0]


def evaluate_archive(archive, plugin, source_service, provider):
    need(archive.is_file() and not archive.is_symlink(),
         "OFFICIAL_NATIVE_ARCHIVE_NOT_FOUND")
    raw = cmd(["tar", "-xOf", str(archive), "+MANIFEST"])
    try:
        manifest = json.loads(raw)
    except ValueError:
        raise Refusal("NATIVE_ARCHIVE_MANIFEST_INVALID") from None
    count = manifest_identity(manifest, plugin, provider)
    names = cmd(["tar", "-tf", str(archive)]).splitlines()
    service_member = exact_installed_tar_member(names, SERVICE)
    try:
        actual = subprocess.run(["tar", "-xOf", str(archive), service_member],
                                capture_output=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_SERVICE_ARCHIVE_BYTES_UNAVAILABLE") from None
    need(actual.returncode == 0 and actual.stdout == source_service,
         "OFFICIAL_NATIVE_SOURCE_SERVICE_CONTENT_CHANGED")
    verbose = cmd(["tar", "-tvf", str(archive)]).splitlines()
    matching = [line for line in verbose if line.rstrip().endswith(" " + service_member)]
    need(len(matching) == 1 and matching[0].split()[0] == "-rw-r--r--",
         "HISTORICAL_SOURCE_MODE_NOT_PRESERVED_BY_NATIVE_BUILD")
    # The old production builder chmods this service during packaging,
    # while the official upstream native builder preserves its Git 100644.
    # This is an observed release BLOCKER, not a permission to auto-chmod.
    need(not any(CURL in x for x in names),
         "PARTIAL_SOURCE_PACKAGE_UNEXPECTED_PRIVATE_CURL_ARTIFACT")
    return {"source_file_count": count,
            "native_service_archive_mode": "0644",
            "native_service_mode_is_safe": False,
            "historical_git_mode_100644_preserved": True,
            "private_curl_assets_bundled": False,
            "source_service_sha256": hashlib.sha256(source_service).hexdigest(),
            "noninstallable_qualification_only": True,
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}


def run():
    guest_gate()
    sha = source_identity()
    provider = qualify_python_provider()
    source_service_path = ROOT / "src" / SERVICE
    info = source_service_path.lstat()
    need(stat.S_ISREG(info.st_mode) and not source_service_path.is_symlink() and
         stat.S_IMODE(info.st_mode) == 0o644,
         "CURRENT_GIT_SERVICE_MODE_DEBT_NOT_REPRODUCED")
    source_bytes = source_service_path.read_bytes()
    with tempfile.TemporaryDirectory(prefix="stage0-official-native-source-") as td:
        official = clone_official(Path(td))
        plugin = prepare_source(official)
        got = native_variables(plugin, sha, provider)
        cmd(["make", "-C", str(plugin), "PLUGIN_HASH=" + sha,
             "PLUGIN_WWW=https://github.com/Tolian82/os-zapret2-restyle",
             "package"], timeout=280)
        archive = plugin / "work" / "pkg" / (
            NAME + "-" + VERSION + "_" + REVISION + ".pkg")
        evidence = evaluate_archive(archive, plugin, source_bytes, provider)
    return {"schema": 1,
            "status": "PASS_OFFICIAL_MK_SOURCE_PACKAGE_WITH_BLOCKERS",
            "project_source_sha": sha,
            "official_opnsense_plugins_sha": UPSTREAM_SHA,
            "native_framework": "Mk/plugins.mk",
            "resolved_variables": got,
            "actual_installed_python_provider": provider,
            **evidence,
            "native_pkg_install_executed": False,
            "production_builder_replaced": False,
            "official_final_product_package_qualified": False,
            "stage0_closed": False}


def main():
    try:
        report = run()
    except (Refusal, OSError, ValueError, TypeError, KeyError) as exc:
        print("STAGE0_OFFICIAL_MK=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_OFFICIAL_MK=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
