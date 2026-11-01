#!/usr/bin/env python3
"""Observe real FreeBSD pkg hook scheduling in a disposable VM, NOT OPNsense.

The immutable 0.6.2_1 archive must pass exact SHA and four-hook manifest
checks before creating distinct, safely named phase-tracer fixture packages.
The fixture hooks are intentionally NOT the production hook bodies. Results
must never be presented as old service FD9 or OPNsense native acceptance.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ARCHIVE_SHA = "1e21fbcac847529b94fea940241b4da7f86a42d33c129b7003ad04a72f4e5a0f"
PHASES = ("pre-install", "post-install", "pre-deinstall", "post-deinstall")
NAME = "zapret2-stage0-phase-order-fixture"
EXPECTED = (
    "old:pre-install", "old:post-install",
    "new:pre-install", "old:pre-deinstall",
    "old:post-deinstall", "new:post-install",
)


class Refusal(Exception):
    pass


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def check_archive(path):
    if digest(path.read_bytes()) != ARCHIVE_SHA:
        raise Refusal("IMMUTABLE_ARCHIVE_SHA256_MISMATCH")
    # Native bsdtar understands the actual zstd-compressed FreeBSD .pkg.
    try:
        manifest_raw = subprocess.run(["tar", "-xOf", str(path), "+MANIFEST"],
                                      capture_output=True, check=False, timeout=30)
        if manifest_raw.returncode:
            raise Refusal("ARCHIVE_MANIFEST_MISSING")
        manifest = json.loads(manifest_raw.stdout)
    except (OSError, ValueError, subprocess.SubprocessError):
        raise Refusal("ARCHIVE_MANIFEST_INVALID") from None
    if manifest.get("name") != "os-zapret2-restyle" or manifest.get("version") != "0.6.2_1":
        raise Refusal("PREDECESSOR_IDENTITY_MISMATCH")
    if manifest.get("abi") != "FreeBSD:15:amd64":
        raise Refusal("PREDECESSOR_ABI_MISMATCH")
    scripts = manifest.get("scripts")
    if not isinstance(scripts, dict):
        raise Refusal("PREDECESSOR_HOOKS_MISSING")
    hooks = {}
    for phase in PHASES:
        body = scripts.get(phase)
        if not isinstance(body, str) or not body.strip():
            raise Refusal("PREDECESSOR_HOOKS_MISSING")
        hooks[phase] = {"sha256": digest(body.encode("utf-8")),
                        "bytes": len(body.encode("utf-8"))}
    return hooks


def run(args, env=None, timeout=90):
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                env=env, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_PKG_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None
    if result.returncode:
        # This script runs only on a disposable FreeBSD VM, with fixture pkg
        # metadata. Keep bounded stderr for diagnosing real pkg refusals.
        diagnostic = " ".join(result.stderr.split())[:350]
        diagnostic = re.sub(r"https?://[^ ]+", "[url]", diagnostic)
        raise Refusal("NATIVE_PKG_COMMAND_FAILED:" + args[0] + ":" + args[1] +
                      ":rc=" + str(result.returncode) + ":" + diagnostic)
    return result.stdout


def phase_script(trace, role, phase):
    # These are intentionally synthetic tracers; NOT rewritten production hooks.
    if not re.fullmatch(r"[a-z-]+", role + phase):
        raise Refusal("UNSAFE_TEST_PHASE")
    return "#!/bin/sh\nprintf '%s\\n' '" + role + ":" + phase + "' >> '" + str(trace) + "'\nexit 0\n"


def build_fixture(work, role, version, trace):
    stage = work / ("stage-" + role)
    out = work / ("output-" + role)
    out.mkdir()
    installed = work / "installed"
    marker = installed / "stage0-fixture-marker"
    payload = ("stage0 fixture " + role + "\n").encode("ascii")
    file = stage / str(marker).lstrip("/")
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(payload)
    scripts = {phase: phase_script(trace, role, phase) for phase in PHASES}
    manifest = {"name": NAME, "origin": "sysutils/" + NAME,
                "version": version, "abi": "FreeBSD:15:amd64",
                "arch": "freebsd:15:x86:64", "prefix": str(installed),
                "comment": "Disposable package scheduler phase trace fixture",
                "desc": "Stage0 disposable real FreeBSD pkg phase scheduler witness",
                "maintainer": "test@example.invalid", "www": "https://example.invalid",
                "licenselogic": "single", "licenses": ["MIT"],
                "files": {str(marker): digest(payload)}, "scripts": scripts}
    mf = work / (role + ".json")
    mf.write_text(json.dumps(manifest), encoding="utf-8")
    run(["pkg", "create", "-M", str(mf), "-r", str(stage), "-o", str(out)])
    matches = list(out.glob(NAME + "-" + version + ".pkg"))
    if len(matches) != 1:
        raise Refusal("FIXTURE_BUILD_IDENTITY_MISMATCH")
    return matches[0]


def check_trace(lines):
    if tuple(lines) != EXPECTED:
        raise Refusal("ACTUAL_NATIVE_PKG_PHASE_ORDER_DIFFERENT")
    return True


def run_vm(archive, report):
    if os.uname().sysname != "FreeBSD" or os.uname().machine != "amd64" or os.geteuid() != 0:
        raise Refusal("ONLY_ROOT_DISPOSABLE_FREEBSD_AMD64")
    os_version = run(["freebsd-version", "-u"]).strip()
    if not os_version.startswith("15.1-"):
        raise Refusal("WRONG_FREEBSD_VM_RELEASE")
    hooks = check_archive(archive)
    with tempfile.TemporaryDirectory(prefix="zapret2-stage0-pkg-scheduler-") as root:
        work = Path(root)
        db = work / "pkgdb"
        cache = work / "cache"
        db.mkdir(mode=0o700)
        cache.mkdir(mode=0o700)
        trace = work / "phases.txt"
        old = build_fixture(work, "old", "0.6.2_1", trace)
        new = build_fixture(work, "new", "0.6.2_27", trace)
        env = os.environ.copy()
        env.update(PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
                   ASSUME_ALWAYS_YES="yes")
        # Real pkg, separate local DB, file payload strictly inside work.
        run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add", str(old)], env)
        run(["pkg", "-o", "REPO_AUTOUPDATE=false", "add", "-f", str(new)], env)
        rows = trace.read_text(encoding="ascii").splitlines()
        try:
            check_trace(rows)
        except Refusal:
            # Instrumented fixture phases are public synthetic labels,
            # safe to print even when the disposable guest fails to sync an artifact.
            print("STAGE0_OBSERVED_PHASES=" + json.dumps(rows))
            report.write_text(json.dumps({
                "status": "NOT_VERIFIED", "observed_order": rows,
                "expected_order": list(EXPECTED), "historical_hooks": hooks,
                "real_pkg_invoked": True, "opnsense_pkg_lifecycle_verified": False
            }, sort_keys=True), encoding="utf-8")
            raise
        installed = run(["pkg", "-o", "REPO_AUTOUPDATE=false", "query",
                         "%n|%v", NAME], env).strip()
        if installed != NAME + "|0.6.2_27":
            raise Refusal("REAL_PKG_INSTALLED_IDENTITY_MISMATCH")
        report.write_text(json.dumps({
            "status": "PASS_FREEBSD15_1_PKG_SCHEDULER",
            "freebsd_vm": os_version,
            "immutable_old_archive_sha256": ARCHIVE_SHA,
            "immutable_old_archive_four_hooks": hooks,
            "observed_order": rows, "real_pkg_invoked": True,
            "synthetic_tracer_scripts_not_real_hook_bodies": True,
            "isolated_pkg_database_and_payload": True,
            "opnsense_pkg_lifecycle_verified": False,
            "old_service_fd9_verified": False, "stage0_closed": False
        }, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--json", type=Path, required=True)
    args = parser.parse_args()
    try:
        run_vm(args.archive, args.json)
    except Refusal as exc:
        print("STAGE0_REAL_PKG_SCHEDULER=NOT_VERIFIED:" + str(exc))
        return 1
    print("STAGE0_REAL_PKG_SCHEDULER=PASS: FreeBSD15.1 real pkg phase order with synthetic isolated fixture")
    return 0


if __name__ == "__main__":
    sys.exit(main())
