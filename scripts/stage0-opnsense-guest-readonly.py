#!/usr/bin/env python3
"""Fail-closed, read-only identity gate for a fresh disposable OPNsense 26.7 CI VM.

This qualifies ONLY the guest product/OS/ABI/virtualization and an absent
predecessor. No published package is installed, no service or FD9 is touched.
The third-party-built VM image is not independently SHA-attested by this test.
"""
import json
import os
import subprocess
import sys

NAME = "os-zapret2-restyle"
PRODUCT_ABI = "26.7"
PKG_ABI = "FreeBSD:15:amd64"


class Refusal(Exception):
    pass


def query(args, allowed=(0,)):
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, check=False, timeout=20)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("GUEST_READ_ONLY_COMMAND_FAILED_OR_TIMEOUT:" + args[0]) from None
    if proc.returncode not in allowed:
        raise Refusal("GUEST_READ_ONLY_COMMAND_REFUSED:" + args[0])
    return proc.returncode, proc.stdout.decode("utf-8", "replace").strip()


def evaluate(observed):
    if observed["uid"] != 0:
        raise Refusal("GUEST_NOT_ROOT")
    if observed["os"] != "FreeBSD" or observed["arch"] != "amd64":
        raise Refusal("GUEST_NOT_FREEBSD_AMD64")
    if observed["product_abi"] != PRODUCT_ABI:
        raise Refusal("GUEST_WRONG_OPNSENSE_ABI")
    if observed["package_abi"] != PKG_ABI:
        raise Refusal("GUEST_WRONG_PACKAGE_ABI")
    if not observed["userland"].startswith("15."):
        raise Refusal("GUEST_WRONG_FREEBSD_USERLAND")
    if observed["virtualization"].lower() in ("", "none", "unknown"):
        raise Refusal("GUEST_NOT_VIRTUALIZED")
    if observed["old_plugin_pkg_exists"]:
        raise Refusal("GUEST_NOT_FRESH_PREDECESSOR_ABSENT")
    return {
        "schema": 1, "status": "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
        "product_abi": PRODUCT_ABI, "package_abi": PKG_ABI,
        "freebsd_userland": observed["userland"],
        "virtualization_reported": observed["virtualization"],
        "old_plugin_pkg_exists": False,
        "official_image_sha256_independently_verified": False,
        "third_party_vm_image_provenance_independently_verified": False,
        "actual_published_predecessor_installed": False,
        "real_installed_predecessor_provenance_tested": False,
        "real_service_fd9_tested": False,
        "native_successor_tested": False,
        "stage0_closed": False,
    }


def observe():
    uname = os.uname()
    _, product = query(["opnsense-version", "-a"])
    _, pkg_abi = query(["pkg", "config", "ABI"])
    _, userland = query(["freebsd-version", "-u"])
    _, vm = query(["sysctl", "-n", "kern.vm_guest"])
    rc, _ = query(["pkg", "info", "-e", NAME], allowed=(0, 1))
    return {
        "uid": os.geteuid(), "os": uname.sysname, "arch": uname.machine,
        "product_abi": product, "package_abi": pkg_abi,
        "userland": userland, "virtualization": vm,
        "old_plugin_pkg_exists": rc == 0,
    }


def main():
    try:
        result = evaluate(observe())
    except (Refusal, OSError, KeyError) as exc:
        print("STAGE0_OPNSENSE_GUEST=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_OPNSENSE_GUEST=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
