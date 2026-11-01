#!/usr/bin/env python3
"""Disposable FreeBSD15.1 pkgdb roundtrip for the installed predecessor preflight.

Only synthetic, non-mutating hook bodies are INSTALLED; published 0.6.2_1
archive is READ, never added. Temp pkg DB and payload are private.
This does not exercise OPNsense, old service, FD9 or package replacement.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "predecessor", ROOT / "stage0-installed-predecessor-readonly.py")
pre = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pre)


def check_platform(attested, sysname, machine, uid, release):
    if not attested:
        raise pre.Refusal("DISPOSABLE_VM_ATTESTATION_REQUIRED")
    if (sysname, machine, uid) != ("FreeBSD", "amd64", 0) or not release.startswith("15.1-"):
        raise pre.Refusal("REQUIRES_ROOT_DISPOSABLE_FREEBSD_15_1_AMD64")


def call(argv, env=None):
    try:
        result = subprocess.run(argv, capture_output=True, text=True, env=env,
                                timeout=60, check=False)
    except (OSError, subprocess.SubprocessError):
        raise pre.Refusal("NATIVE_FIXTURE_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode:
        diagnostic = " ".join(result.stderr.split())[:200]
        raise pre.Refusal("NATIVE_FIXTURE_COMMAND_FAILED:" + Path(argv[0]).name
                          + ":" + str(result.returncode) + ":" + diagnostic)
    return result.stdout


def fixture_manifest(installed_path, payload):
    return {
        "name": pre.NAME, "origin": "security/zapret2-stage0-pkgdb-fixture",
        "version": pre.VERSION, "abi": pre.ABI, "arch": "freebsd:15:x86:64",
        "prefix": str(installed_path.parent),
        "comment": "Disposable OPNsense predecessor pkgdb format fixture",
        "desc": "Offline FreeBSD pkgdb roundtrip, no old service or real package installation",
        "maintainer": "fixture@example.invalid", "www": "https://example.invalid",
        "licenselogic": "single", "licenses": ["MIT"],
        "files": {str(installed_path): pre.digest(payload)},
        "scripts": {p: "#!/bin/sh\nexit 0\n" for p in pre.PHASES},
    }


def native_roundtrip(archive):
    old, original_service = pre.archive_data(archive)  # Exact published SHA guard.
    if old.get("name") != pre.NAME or old.get("version") != pre.VERSION:
        raise pre.Refusal("IMMUTABLE_OLD_PACKAGE_NOT_EXPECTED")
    with tempfile.TemporaryDirectory(prefix="stage0-native-pkgdb-") as td:
        root = Path(td)
        db, cache, dist = (root / "db", root / "cache", root / "dist")
        for directory in (db, cache, dist):
            directory.mkdir(mode=0o700)
        installed = root / "installed" / "mock-service.sh"
        staged = root / "stage" / str(installed).lstrip("/")
        staged.parent.mkdir(parents=True)
        payload = b"#!/bin/sh\nexit 0\n"
        staged.write_bytes(payload)
        staged.chmod(0o755)
        fixture = fixture_manifest(installed, payload)
        manifest_path = root / "fixture.json"
        manifest_path.write_text(json.dumps(fixture))
        pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
        env = os.environ.copy()
        env.update(PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache), ASSUME_ALWAYS_YES="yes")
        call([*pkg, "create", "-M", str(manifest_path), "-r", str(root / "stage"), "-o", str(dist)], env)
        paths = list(dist.glob(pre.NAME + "-" + pre.VERSION + ".pkg"))
        if len(paths) != 1:
            raise pre.Refusal("SYNTHETIC_PACKAGE_NOT_CREATED_EXACTLY_ONCE")
        call([*pkg, "add", str(paths[0])], env)
        raw = call([*pkg, "info", "-R", "--raw-format", "json", pre.NAME], env)
        try:
            current = json.loads(raw)
        except (TypeError, ValueError):
            raise pre.Refusal("REAL_PKG_INSTALLED_RAW_MANIFEST_NOT_JSON") from None
        owner = call([*pkg, "which", "-q", str(installed)], env).strip()
        state = installed.lstat()
        if not stat.S_ISREG(state.st_mode):
            raise pre.Refusal("SYNTHETIC_INSTALLED_PAYLOAD_NOT_REGULAR")
        # "26.7" below is a controlled fixture, NOT observed from OPNsense.
        verified = pre.verify_data(fixture, current, payload, installed.read_bytes(),
                                   owner, stat.S_IMODE(state.st_mode), "26.7", pre.ABI, "fixture-vm")
        if verified["real_fd9_tested"] or verified["actual_pkg_replacement"]:
            raise pre.Refusal("SYNTHETIC_FIXTURE_CLAIMED_REAL_LIFECYCLE")
        return {
            "schema": 1, "status": "PASS_FREEBSD15_1_SYNTHETIC_PKGDB_FORMAT",
            "exact_archived_package_sha256": pre.ARCHIVE_SHA,
            "archived_service_sha256": pre.digest(original_service),
            "native_pkg_raw_manifest_has_original_hook_bodies": True,
            "native_pkg_which_owner_matches": True,
            "native_installed_payload_mode": oct(stat.S_IMODE(state.st_mode)),
            "synthetic_hooks_only": True, "isolated_pkg_db_and_payload": True,
            "actual_opnsense_installed_predecessor": False,
            "actual_fd9_or_old_service": False, "actual_package_replacement": False,
            "stage0_closed": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--disposable-freebsd-vm", action="store_true")
    args = parser.parse_args()
    try:
        sysname, machine = os.uname().sysname, os.uname().machine
        release = call(["freebsd-version", "-u"]).strip() if args.disposable_freebsd_vm and sysname == "FreeBSD" else ""
        check_platform(args.disposable_freebsd_vm, sysname, machine, os.geteuid(), release)
        print("STAGE0_NATIVE_PKGDB=" + json.dumps(native_roundtrip(args.archive), sort_keys=True))
    except (pre.Refusal, OSError) as exc:
        print("STAGE0_NATIVE_PKGDB=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
