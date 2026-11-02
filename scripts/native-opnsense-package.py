#!/usr/bin/env python3
"""Single official OPNsense Mk/plugins.mk package engine; source-only Stage 2.

Safety: this builder is for *qualified isolated OPNsense 26.7 CI* until the
real installed successor/lifecycle acceptance is complete. It does not install
the built product package or authorize publication. Never run on owner device.
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
VERSION = "0.6.2"
REVISION = "64"
NAME = "os-zapret2-restyle"
ABI = "FreeBSD:15:amd64"
PROJECT_URL = "https://github.com/Tolian82/os-zapret2-restyle"
EXPECTED_ROLES = ("python-runtime", "engine-build-make", "engine-build-pkgconf",
                  "engine-runtime-luajit", "setup-git", "setup-json",
                  "private-trust-CA")
HOOKS = {"+PRE_INSTALL": "pre-install", "+POST_INSTALL": "post-install",
         "+PRE_DEINSTALL": "pre-deinstall", "+POST_DEINSTALL": "post-deinstall"}
SERVICE = "opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
BINARY = "libexec/zapret2-restyle/curl-impersonate/bin/curl-impersonate"
LAUNCHER = "libexec/zapret2-restyle/run-curl-impersonate.sh"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, HERE / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


private = load_module("stage2-opnsense-native-private-source.py", "signed_private")
provider = load_module("stage2-opnsense-native-provider-preflight.py",
                       "native_provider")
# These helpers have immutable earlier witness revision defaults. Reuse only
# source/ELF/guest verification primitives, NOT their old manifest verdicts.
private.old.REVISION = REVISION
provider.mk.REVISION = REVISION


class Refusal(Exception):
    pass


def need(ok, reason):
    if not ok:
        raise Refusal(reason)


def command(args, timeout=300):
    try:
        p = subprocess.run(args, capture_output=True, check=False,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_COMMAND_FAILED_OR_TIMEOUT:" + args[0]) from None
    need(p.returncode == 0,
         "NATIVE_COMMAND_REFUSED:" + args[0] + ":rc=" + str(p.returncode) +
         ":" + p.stderr[-400:].decode("utf-8", "replace"))
    return p.stdout


def git_head():
    expected = os.environ.get("ZAPRET2_NATIVE_PROJECT_SHA", "")
    need(re.fullmatch(r"[a-f0-9]{40}", expected) is not None,
         "CI_EXACT_PROJECT_SHA_REQUIRED")
    need(expected == os.environ.get("ZAPRET2_STAGE0_PROJECT_SHA"),
         "INDEPENDENT_PROJECT_SHA_BOUNDARIES_MISMATCH")
    private.old.source_identity()  # also binds project revision and official name
    private.tracked_file(ROOT / "src" / SERVICE, "100755")
    private.tracked_file(ROOT / "scripts" / "build-curl-impersonate.sh", "100755")
    for n in private.LAUNCHERS:
        private.tracked_file(ROOT / "scripts" / n, "100755")
    need(not command(["git", "-c", "safe.directory=" + str(ROOT), "-C",
                      str(ROOT), "status", "--porcelain", "--untracked-files=no"]),
         "SOURCE_CHECKOUT_HAS_UNCOMMITTED_CHANGES")
    return expected


def gate():
    need(os.environ.get("ZAPRET2_NATIVE_BUILD_CI") == "1" and
         os.environ.get("GITHUB_ACTIONS") == "true" and
         os.environ.get("ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK") == "1",
         "NATIVE_BUILD_NOT_OPTED_IN_TO_ISOLATED_CI")
    private.old.guest_gate()
    need(provider.command("opnsense-version", "-a") == "26.7",
         "NOT_OPNSENSE_26_7")
    need(provider.command("pkg", "config", "ABI") == ABI,
         "NOT_TARGET_FREEBSD15_ABI")


def installed_provider_names():
    observed = private.old.qualify_python_provider()
    raw = provider.command("pkg", "rquery", "-r", "OPNsense", "%n|%o|%v")
    catalog = provider.parse_catalog(raw)
    resolved = provider.resolve(catalog,
                                "python" + observed["native_plugin_python"])
    provider.installed_python_crosscheck(resolved, observed)
    expected_names = [resolved[role]["selected"]["name"] for role in EXPECTED_ROLES]
    installed = {}
    for role in EXPECTED_ROLES:
        selected = resolved[role]["selected"]
        name = selected["name"]
        record = provider.command("pkg", "query", "%n|%o|%v", name).split("|")
        need(len(record) == 3 and record[0] == name and
             record[1] == selected["origin"] and bool(record[2]),
             "UNQUALIFIED_INSTALLED_TARGET_DEPENDENCY:" + role)
        installed[name] = {"origin": record[1], "version": record[2]}
    need(len(installed) == len(EXPECTED_ROLES),
         "DUPLICATE_OR_MISSING_TARGET_RUNTIME_DEPENDENCY")
    return observed, installed, hashlib.sha256(raw.encode()).hexdigest()


def native_make_variables(plugin, sha, py, installed):
    keys = ("PLUGIN_PKGNAME", "PLUGIN_PKGVERSION", "PLUGIN_ABI", "PLUGIN_HASH",
            "PLUGIN_WWW", "PLUGIN_PYTHON", "PLUGIN_DEPENDS", "PLUGIN_DEVEL")
    result = {key: private.old.mkvar(plugin, sha, key) for key in keys}
    deps = result["PLUGIN_DEPENDS"].split()
    need(result["PLUGIN_PKGNAME"] == NAME and
         result["PLUGIN_PKGVERSION"] == VERSION + "_" + REVISION and
         result["PLUGIN_ABI"] == "26.7" and
         result["PLUGIN_HASH"] == sha and
         result["PLUGIN_WWW"] == PROJECT_URL and
         result["PLUGIN_PYTHON"] == py["native_plugin_python"] and
         result["PLUGIN_DEVEL"] == "" and
         len(deps) == len(installed) and set(deps) == set(installed),
         "NATIVE_MK_VARS_OR_REAL_DEPS_MISMATCH")
    return result


def archived_file(pkg, name):
    names = command(["tar", "-tf", str(pkg)]).decode().splitlines()
    member = private.old.exact_installed_tar_member(names, name)
    return command(["tar", "-xOf", str(pkg), member], timeout=35)


def verify_native_package(pkg, plugin, sha, deps, bundle):
    need(pkg.is_file() and not pkg.is_symlink(),
         "NATIVE_PKG_NOT_FOUND")
    try:
        manifest = json.loads(command(["tar", "-xOf", str(pkg), "+MANIFEST"]))
    except (ValueError, UnicodeDecodeError):
        raise Refusal("INVALID_NATIVE_PKG_MANIFEST") from None
    need(manifest.get("name") == NAME and
         manifest.get("version") == VERSION + "_" + REVISION and
         manifest.get("abi") == ABI and
         manifest.get("arch") == "freebsd:15:x86:64" and
         manifest.get("origin") == "opnsense/" + NAME and
         manifest.get("www") == PROJECT_URL,
         "NATIVE_PKG_IDENTITY_WRONG")
    need(set(manifest.get("deps", {})) == set(deps),
         "NATIVE_PKG_REAL_DEPENDENCIES_WRONG")
    for name, actual in deps.items():
        entry = manifest["deps"][name]
        need(entry.get("origin") == actual["origin"] and
             entry.get("version") == actual["version"],
             "NATIVE_PKG_DEPENDENCY_PROVIDER_MISMATCH:" + name)
    hooks = manifest.get("scripts", {})
    need(isinstance(hooks, dict) and set(hooks) == set(HOOKS.values()),
         "NATIVE_PKG_FOUR_HOOK_PHASES_CHANGED")
    for filename, phase in HOOKS.items():
        src = (plugin / filename).read_bytes()
        need(src.endswith(b"\n") and not src.endswith(b"\n\n"),
             "NATIVE_HOOK_SOURCE_ENDING_UNQUALIFIED")
        expected = src.replace(b"%", b"%25")[:-1]
        need(isinstance(hooks[phase], str) and hooks[phase].encode() == expected,
             "NATIVE_MANUAL_HOOK_BYTES_CHANGED:" + phase)
    files = manifest.get("files")
    need(isinstance(files, dict) and len(files) >= 290,
         "NATIVE_SOURCE_FILESET_INCOMPLETE")
    source = plugin / "src"
    name_to_source = {}
    for path in source.rglob("*"):
        need(not path.is_symlink(), "SOURCE_SYMLINK_NOT_QUALIFIED")
        if not path.is_file():
            continue
        rel = path.relative_to(source).as_posix()
        need("/usr/local/" + rel in files, "NATIVE_SOURCE_MISSING:" + rel)
        name_to_source[rel] = path
    need(len(name_to_source) == len(files) - 1,
         "NATIVE_UNEXPECTED_STAGED_FILE_COUNT")  # one generated version marker
    names = command(["tar", "-tf", str(pkg)]).decode().splitlines()
    modes = command(["tar", "-tvf", str(pkg)]).decode().splitlines()
    for rel, path in name_to_source.items():
        member = private.old.exact_installed_tar_member(names, rel)
        got = command(["tar", "-xOf", str(pkg), member], timeout=35)
        need(got == path.read_bytes(), "NATIVE_ARCHIVE_SOURCE_BYTES_CHANGED:" + rel)
    for rel in (SERVICE, BINARY, LAUNCHER,
                "libexec/zapret2-restyle/check-curl-impersonate.sh"):
        member = private.old.exact_installed_tar_member(names, rel)
        listed = [line.split()[0] for line in modes
                  if line.rstrip().endswith(" " + member)]
        need(listed == ["-rwxr-xr-x"],
             "NATIVE_ARCHIVED_SERVICE_OR_PRIVATE_NOT_0755:" + rel)
    need(hashlib.sha256(archived_file(pkg, BINARY)).hexdigest() ==
         bundle["private_binary_sha256"],
         "NATIVE_ARCHIVE_PRIVATE_ELF_SHA_CHANGED")
    # Official Mk annotation/version marker generated from exact project hash.
    annotation = manifest.get("annotations", {})
    marker = archived_file(pkg, "opnsense/version/zapret2-restyle")
    need(sha.encode() in marker and len(marker) >= 40,
         "NATIVE_PROJECT_HASH_ANNOTATION_MISSING")
    return {"name": manifest["name"], "version": manifest["version"],
            "actual_file_count": len(files),
            "actual_dependencies": manifest["deps"],
            "original_manual_hooks": list(HOOKS.values()),
            "source_service_mode": "0755", "private_executables_mode": "0755",
            "source_package_hash_annotation": True,
            "sha256": hashlib.sha256(pkg.read_bytes()).hexdigest()}


def build():
    gate()
    sha = git_head()
    py, installed, catalog_digest = installed_provider_names()
    with tempfile.TemporaryDirectory(prefix="zapret2-native-build-") as scratch:
        official = private.old.clone_official(Path(scratch))
        plugin = private.old.prepare_source(official)
        variables = native_make_variables(plugin, sha, py, installed)
        private_dir, bundle = private.prepare_private(plugin, Path(scratch))
        command(["make", "-C", str(plugin), "PLUGIN_HASH=" + sha,
                 "PLUGIN_WWW=" + PROJECT_URL, "package"], timeout=370)
        pkg = plugin / "work" / "pkg" / (NAME + "-" + VERSION + "_" + REVISION + ".pkg")
        evidence = verify_native_package(pkg, plugin, sha, installed, bundle)
        # Preserve the existing CLI delivery: one package in dist/, no
        # published repo/release and never install this candidate.
        output = ROOT / "dist"
        need(not output.is_symlink(), "DIST_IS_UNTRUSTED_SYMLINK")
        if output.exists():
            need(output.is_dir(), "DIST_IS_NOT_DIRECTORY")
            shutil.rmtree(output)
        output.mkdir()
        dest = output / pkg.name
        shutil.copyfile(pkg, dest)
        need(hashlib.sha256(dest.read_bytes()).hexdigest() == evidence["sha256"],
             "DIST_PACKAGE_SHA_CHANGED")
    return {"schema": 1, "status": "PASS_OFFICIAL_NATIVE_BUILD_SOURCE_ONLY",
            "project_sha": sha, "framework_sha": private.old.UPSTREAM_SHA,
            "target_abi": ABI, "provider_catalog_sha256": catalog_digest,
            "evaluated_native_make": variables,
            "private_signed_source_sha256": bundle["signed_freebsd_latest_package_sha256"],
            "private_elf_sha256": bundle["private_binary_sha256"],
            "private_chrome_profile": bundle["profile"],
            "private_target_libraries": bundle["target_ldd_libraries"],
            "real_native_pkg": evidence,
            "output": "dist/" + NAME + "-" + VERSION + "_" + REVISION + ".pkg",
            "production_script_uses_official_Mk": True,
            "actual_product_pkg_installed": False,
            "publication_approved": False, "owner_appliance_modified": False,
            "stage0_closed": False, "stage1_admitted": False}


def main():
    try:
        report = build()
    except (Refusal, private.old.Refusal, provider.Refusal,
            ValueError, TypeError, OSError, KeyError) as exc:
        print("NATIVE_OPNSENSE_PACKAGE=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("NATIVE_OPNSENSE_PACKAGE=" + json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
