#!/usr/bin/env python3
"""Stage 2.26: test genuine native .pkg hook payloads through sandbox mocks.

This is package-artifact and mocked-hook evidence ONLY. It does not run pkg
add/delete/upgrade, acquire production FD9 or establish an atomic pre-pkg veto.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
HOOKS = {
    "+PRE_INSTALL": "pre-install",
    "+POST_INSTALL": "post-install",
    "+PRE_DEINSTALL": "pre-deinstall",
    "+POST_DEINSTALL": "post-deinstall",
}
NAME = "os-zapret2-restyle"
EXPECTED_TESTS = (
    ("sh", "scripts/test-package-lifecycle-restart.sh",
     "PASS: package replacement preserves complete service state without reboot"),
    (sys.executable, "scripts/test-package-cold-kernel.py",
     "PASS: preinstall refuses unsafe old PRE-DEINSTALL after verified cold kernel"),
)


class Refusal(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def identity(root):
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    match = re.search(r"^PLUGIN_REVISION=\s*(\d+)\s*$", makefile, re.M)
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+", version)) and match is not None,
            "INVALID_SOURCE_PACKAGE_IDENTITY")
    compatibility = json.loads((root / "compatibility.json").read_text(encoding="utf-8"))
    platforms = compatibility.get("supported_platforms", [])
    require(isinstance(platforms, list) and len(platforms) == 1 and
            isinstance(platforms[0], dict), "UNQUALIFIED_TARGET_POLICY")
    abi = platforms[0].get("freebsd_pkg_abi")
    require(abi == "FreeBSD:15:amd64", "UNQUALIFIED_TARGET_ABI")
    return version + "_" + match.group(1), abi


def fetch_manifest(package):
    try:
        completed = subprocess.run(["tar", "-xOf", str(package), "+MANIFEST"],
                                   capture_output=True, timeout=35, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_MANIFEST_UNREADABLE") from None
    require(completed.returncode == 0, "NATIVE_MANIFEST_EXTRACTION_FAILED")
    try:
        return json.loads(completed.stdout)
    except (ValueError, UnicodeDecodeError):
        raise Refusal("NATIVE_MANIFEST_NOT_JSON") from None


def verify_hook_bodies(manifest, root, version, abi):
    require(isinstance(manifest, dict), "NATIVE_MANIFEST_NOT_OBJECT")
    require(manifest.get("name") == NAME and
            manifest.get("version") == version and
            manifest.get("abi") == abi and
            manifest.get("arch") == "freebsd:" + abi.split(":")[1] + ":x86:64" and
            manifest.get("origin") == "opnsense/" + NAME,
            "NATIVE_PACKAGE_IDENTITY_MISMATCH")
    scripts = manifest.get("scripts")
    require(isinstance(scripts, dict) and set(scripts) == set(HOOKS.values()),
            "NATIVE_PACKAGE_HOOK_PHASE_SET_CHANGED")
    extracted = {}
    for file_name, phase in HOOKS.items():
        source = (root / "pkg" / file_name).read_bytes()
        require(source.startswith(b"#!/bin/sh\n") and source.endswith(b"\n")
                and not source.endswith(b"\n\n"),
                "SOURCE_HOOK_BOUNDARY_INVALID:" + phase)
        encoded = source.replace(b"%", b"%25")[:-1]
        packaged = scripts[phase]
        require(isinstance(packaged, str) and packaged.encode("utf-8") == encoded,
                "NATIVE_MANIFEST_HOOK_BYTES_CHANGED:" + phase)
        decoded = packaged.encode("utf-8").replace(b"%25", b"%") + b"\n"
        require(decoded == source, "NATIVE_HOOK_DECODE_DIFFERED:" + phase)
        extracted[file_name] = decoded
    return extracted


def execute_mock_regressions(root, extracted):
    result = {}
    with tempfile.TemporaryDirectory(prefix="zapret2-native-hook-mock-") as directory:
        location = Path(directory)
        env = os.environ.copy()
        for file_name, payload in extracted.items():
            hook = location / file_name
            hook.write_bytes(payload)
            hook.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            env["ZAPRET2_TEST_" + file_name[1:]] = str(hook)
        for exe, path, expected in EXPECTED_TESTS:
            try:
                completed = subprocess.run(
                    [exe, str(root / path)], cwd=root, env=env,
                    capture_output=True, text=True, timeout=110, check=False)
            except (OSError, subprocess.SubprocessError):
                raise Refusal("NATIVE_HOOK_MOCK_TEST_UNAVAILABLE:" + path) from None
            require(completed.returncode == 0 and
                    expected in completed.stdout,
                    "NATIVE_HOOK_MOCK_REGRESSION_REFUSED:" + path + ":rc=" +
                    str(completed.returncode) + ":diagnostic=" +
                    repr((completed.stdout + completed.stderr)[-500:]))
            result[path] = "MOCK_BEHAVIOR_PASSED"
    return result


def run(package, root=ROOT):
    require(package.is_file() and not package.is_symlink(),
            "NATIVE_PACKAGE_FILE_UNQUALIFIED")
    version, abi = identity(root)
    require(package.name == NAME + "-" + version + ".pkg",
            "NATIVE_PACKAGE_FILENAME_IDENTITY_MISMATCH")
    hooks = verify_hook_bodies(fetch_manifest(package), root, version, abi)
    tests = execute_mock_regressions(root, hooks)
    return {
        "schema": 1,
        "status": "PASS_NATIVE_PACKAGE_HOOK_MOCK_REGRESSION_ONLY",
        "source_version": version,
        "package_sha256": hashlib.sha256(package.read_bytes()).hexdigest(),
        "native_hook_phases": list(HOOKS.values()),
        "source_equals_packaged_hooks": True,
        "sandbox_mock_checks": tests,
        "native_pkg_replacement_executed": False,
        "pre_pkg_admission_enforced": False,
        "lh08_ac11_accepted": False,
        "owner_appliance_modified": False,
    }


def main():
    if len(sys.argv) != 2:
        print("NATIVE_HOOK_MOCK=REFUSED:EXACT_PACKAGE_PATH_REQUIRED", file=sys.stderr)
        return 2
    try:
        print("NATIVE_HOOK_MOCK=" + json.dumps(
            run(Path(sys.argv[1])), sort_keys=True))
        return 0
    except (Refusal, OSError, ValueError, KeyError, TypeError) as exc:
        print("NATIVE_HOOK_MOCK=REFUSED:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
