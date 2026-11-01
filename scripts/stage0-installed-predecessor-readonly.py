#!/usr/bin/env python3
"""Read-only old-package provenance gate for a disposable OPNsense guest.

This is not a service/FD9 or pkg-upgrade test. Never use it as permission to
replace a package. The caller must independently verify guest isolation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ARCHIVE_SHA = "1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f"
NAME = "os-zapret2-restyle"
VERSION = "0.6.2_1"
ABI = "FreeBSD:15:amd64"
SERVICE = "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
PHASES = ("pre-install", "post-install", "pre-deinstall", "post-deinstall")


class Refusal(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def run(*argv):
    try:
        p = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           check=False, timeout=15)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("READ_ONLY_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None
    if p.returncode:
        raise Refusal("READ_ONLY_COMMAND_REFUSED:" + argv[0])
    return p.stdout


def archive_data(path):
    blob = path.read_bytes()
    if digest(blob) != ARCHIVE_SHA:
        raise Refusal("PUBLISHED_PACKAGE_SHA256_MISMATCH")
    try:
        old = json.loads(run("tar", "-xOf", str(path), "+MANIFEST"))
    except (ValueError, TypeError):
        raise Refusal("ARCHIVE_MANIFEST_INVALID") from None
    entries = run("tar", "-tf", str(path)).decode("utf-8").splitlines()
    matches = [x for x in entries if x.lstrip("./") == SERVICE.lstrip("/")]
    if len(matches) != 1:
        raise Refusal("ARCHIVED_SERVICE_PATH_AMBIGUOUS_OR_ABSENT")
    return old, run("tar", "-xOf", str(path), matches[0])


def installed_manifest_from_json(raw):
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        raise Refusal("INSTALLED_RAW_MANIFEST_NOT_JSON") from None
    if isinstance(parsed, list):
        if len(parsed) != 1 or not isinstance(parsed[0], dict):
            raise Refusal("INSTALLED_RAW_MANIFEST_NOT_EXACTLY_ONE_PACKAGE")
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        raise Refusal("INSTALLED_RAW_MANIFEST_NOT_OBJECT")
    return parsed


def verify_data(archived, installed, archived_service, installed_service, owner,
                mode, product, pkg_abi, guest):
    if product != "26.7":
        raise Refusal("UNQUALIFIED_OPNSENSE_PRODUCT_ABI")
    if pkg_abi != ABI:
        raise Refusal("UNQUALIFIED_PACKAGE_ABI")
    if not guest or guest.lower() in ("none", "unknown", ""):
        raise Refusal("NO_VIRTUAL_GUEST_WITNESS")
    if not isinstance(archived, dict) or archived.get("abi") != ABI:
        raise Refusal("ARCHIVE_PACKAGE_IDENTITY_MISMATCH")
    if not isinstance(installed, dict):
        raise Refusal("INSTALLED_PACKAGE_IDENTITY_MISMATCH")
    # The trusted archive SHA authenticates these provenance fields. Both
    # native pkg representations must identify the same arch and origin;
    # matching an ABI alone must not admit an inconsistent package.
    for key in ("arch", "origin"):
        value = archived.get(key)
        if not isinstance(value, str) or not value or installed.get(key) != value:
            raise Refusal("INSTALLED_PACKAGE_IDENTITY_" + key.upper() + "_MISMATCH")
    # A native installed manifest may omit ABI; only the independently
    # queried target ABI plus matching archive arch then justify acceptance.
    installed_abi = installed.get("abi")
    if installed_abi is not None and installed_abi != ABI:
        raise Refusal("INSTALLED_PACKAGE_IDENTITY_ABI_MISMATCH")
    for item, manifest in (("ARCHIVE", archived), ("INSTALLED", installed)):
        if manifest.get("name") != NAME or manifest.get("version") != VERSION:
            raise Refusal(item + "_PACKAGE_IDENTITY_MISMATCH")
        hooks = manifest.get("scripts")
        # Unrecognized lifecycle scripts may execute independently of the
        # four approved phases. Refuse additions, not just modified bodies.
        if not isinstance(hooks, dict) or set(hooks) != set(PHASES) or any(
            not isinstance(hooks[p], str) or not hooks[p].startswith("#!/bin/sh\n")
            for p in PHASES
        ):
            raise Refusal(item + "_FOUR_MANUAL_HOOKS_MISSING_OR_EXTRA")
    for phase in PHASES:
        if archived["scripts"][phase] != installed["scripts"][phase]:
            raise Refusal("INSTALLED_HOOK_BODY_MISMATCH:" + phase)
    if not archived_service or archived_service != installed_service:
        raise Refusal("INSTALLED_SERVICE_BYTES_DIFFER_FROM_ARCHIVE")
    if mode != 0o755:
        raise Refusal("INSTALLED_SERVICE_MODE_NOT_0755")
    if owner not in (NAME, NAME + "-" + VERSION):
        raise Refusal("INSTALLED_SERVICE_PACKAGE_OWNER_UNPROVEN")
    return {
        "schema": 1, "status": "PASS_READ_ONLY_PROVENANCE", "package": NAME + "-" + VERSION,
        "product_abi": product, "pkg_abi": pkg_abi, "virtual_guest_reported": guest,
        "service_sha256": digest(installed_service),
        "original_hooks_sha256": {p: digest(archived["scripts"][p].encode()) for p in PHASES},
        "real_fd9_tested": False, "actual_pkg_replacement": False,
        "native_successor_package_tested": False,
        "isolated_environment_independently_attested": False,
    }


def run_guest(archive, expected_hostname):
    if os.geteuid() != 0 or os.uname().sysname != "FreeBSD" or os.uname().machine != "amd64":
        raise Refusal("REQUIRES_ROOT_FREEBSD_AMD64")
    hostname = run("hostname", "-s").decode().strip()
    if not expected_hostname or expected_hostname != hostname:
        raise Refusal("EXPECTED_GUEST_HOSTNAME_MISMATCH")
    product = run("opnsense-version", "-a").decode().strip()
    pkg_abi = run("pkg", "config", "ABI").decode().strip()
    guest = run("sysctl", "-n", "kern.vm_guest").decode().strip()
    old, payload = archive_data(archive)
    current = installed_manifest_from_json(
        run("pkg", "info", "-R", "--raw-format", "json", NAME))
    service = Path(SERVICE)
    info = service.lstat()  # Do not follow symlinks to unrelated files.
    if not stat.S_ISREG(info.st_mode):
        raise Refusal("INSTALLED_SERVICE_NOT_REGULAR")
    local = service.read_bytes()
    owner = run("pkg", "which", "-q", SERVICE).decode().strip()
    return verify_data(old, current, payload, local, owner,
                       stat.S_IMODE(info.st_mode), product, pkg_abi, guest)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--archive", type=Path, required=True, help="Exact immutable 0.6.2_1.pkg")
    ap.add_argument("--isolated-guest", action="store_true", help="Operator attests non-production disposable OPNsense VM")
    ap.add_argument("--expected-hostname", required=True, help="Expected disposable guest hostname")
    args = ap.parse_args()
    if not args.isolated_guest:
        print("REFUSED:NO_ISOLATED_GUEST_ATTESTATION", file=sys.stderr)
        return 2
    try:
        print(json.dumps(run_guest(args.archive, args.expected_hostname), sort_keys=True))
        return 0
    except (Refusal, OSError) as exc:
        print("REFUSED:" + (str(exc) if isinstance(exc, Refusal) else "FILE_UNAVAILABLE"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
