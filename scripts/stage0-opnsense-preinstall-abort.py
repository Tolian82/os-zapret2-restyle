#!/usr/bin/env python3
"""Characterize real pkg add -f with a refusing incoming pre-install hook.

Only a disposable OPNsense 26.7 KVM guest. Both packages are synthetic and
use a private pkg database and files underneath a new temporary directory.
An observed transaction outcome is not approval to upgrade Zapret2.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

FIXTURE = "zapret2-stage0-preinstall-refusal-fixture"
OLD_VERSION = "0.6.2_1"
NEW_VERSION = "0.6.2_37"
REFUSAL_LINE = "new:pre-install:refuse"


class Refusal(Exception):
    pass


def require(ok, reason):
    if not ok:
        raise Refusal(reason)


def invoke(argv, env=None, timeout=90):
    try:
        return subprocess.run(argv, capture_output=True, text=True, env=env,
                              check=False, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_PKG_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None


def successful(argv, env=None):
    result = invoke(argv, env)
    require(result.returncode == 0, "NATIVE_COMMAND_FAILED:" + " ".join(argv[:2]))
    return result.stdout


def phase_hook(trace, role, phase):
    require(role in ("old", "new") and phase in ("pre-install", "post-install",
             "pre-deinstall", "post-deinstall"), "UNSAFE_FIXTURE_HOOK")
    line = role + ":" + phase
    if role == "new" and phase == "pre-install":
        line = REFUSAL_LINE
    script = "#!/bin/sh\n/bin/echo '" + line + "' >> '" + str(trace) + "'\n"
    return script + ("exit 73\n" if line == REFUSAL_LINE else "exit 0\n")


def fixture(work, role, version, trace):
    base = work / ("stage-" + role)
    installed = work / "installed"
    marker = installed / "fixture-data"
    payload = (role + "\n").encode()
    staged = base / str(marker).lstrip("/")
    staged.parent.mkdir(parents=True)
    staged.write_bytes(payload)
    scripts = {phase: phase_hook(trace, role, phase) for phase in
               ("pre-install", "post-install", "pre-deinstall", "post-deinstall")}
    manifest = {
        "name": FIXTURE, "origin": "sysutils/" + FIXTURE, "version": version,
        "abi": "FreeBSD:15:amd64", "arch": "freebsd:15:x86:64",
        "prefix": str(installed), "comment": "Disposable pkg pre-install refusal fixture",
        "desc": "Private OPNsense package-manager lifecycle characterization",
        "maintainer": "test@example.invalid", "www": "https://example.invalid",
        "licenselogic": "single", "licenses": ["MIT"],
        "files": {str(marker): hashlib.sha256(payload).hexdigest()},
        "scripts": scripts,
    }
    source = work / (role + ".json")
    source.write_text(json.dumps(manifest), encoding="utf-8")
    output = work / ("package-" + role)
    output.mkdir()
    successful(["pkg", "create", "-M", str(source), "-r", str(base), "-o", str(output)])
    matches = list(output.glob(FIXTURE + "-" + version + ".pkg"))
    require(len(matches) == 1, "SYNTHETIC_PACKAGE_IDENTITY_MISMATCH")
    return matches[0], marker


def classify(exit_code, installed, payload, trace):
    require(REFUSAL_LINE in trace, "INCOMING_REFUSAL_HOOK_NOT_EXECUTED")
    require(trace[:2] == ["old:pre-install", "old:post-install"],
            "ORIGINAL_FIXTURE_INSTALL_NOT_TRACED")
    require(trace.count(REFUSAL_LINE) == 1, "REFUSAL_HOOK_DUPLICATED")
    if installed == FIXTURE + "|" + OLD_VERSION and payload == b"old\n":
        return "ABORT_PRESERVED_OLD_FIXTURE"
    if installed == FIXTURE + "|" + NEW_VERSION and payload == b"new\n":
        return "REPLACED_DESPITE_INCOMING_PRE_INSTALL_REFUSAL"
    return "PARTIAL_OR_INCONSISTENT_MUTATION_AFTER_REFUSAL"


def run_vm():
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "ONLY_ROOT_DISPOSABLE_OPNSENSE_AMD64")
    version = successful(["opnsense-version", "-a"]).strip()
    require(version.startswith("26.7"), "WRONG_OPNSENSE_GUEST")
    require(successful(["pkg", "config", "ABI"]).strip() == "FreeBSD:15:amd64",
            "WRONG_PKG_ABI")
    with tempfile.TemporaryDirectory(prefix="zapret2-stage0-incoming-pre-") as path:
        work = Path(path)
        db, cache = work / "pkgdb", work / "cache"
        db.mkdir(mode=0o700)
        cache.mkdir(mode=0o700)
        trace = work / "trace.txt"
        old, marker = fixture(work, "old", OLD_VERSION, trace)
        new, other_marker = fixture(work, "new", NEW_VERSION, trace)
        require(marker == other_marker, "FIXTURE_PAYLOAD_PATH_DIFFERENT")
        env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
                   ASSUME_ALWAYS_YES="yes")
        pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
        successful(pkg + ["add", str(old)], env)
        before = successful(pkg + ["query", "%n|%v", FIXTURE], env).strip()
        require(before == FIXTURE + "|" + OLD_VERSION and
                marker.read_bytes() == b"old\n", "PREDECESSOR_FIXTURE_NOT_INSTALLED")
        attempted = invoke(pkg + ["add", "-f", str(new)], env)
        query = invoke(pkg + ["query", "%n|%v", FIXTURE], env)
        require(query.returncode in (0, 1), "PKG_DB_UNREADABLE_AFTER_REFUSAL")
        installed = query.stdout.strip() if query.returncode == 0 else "ABSENT"
        payload = marker.read_bytes() if marker.is_file() and not marker.is_symlink() else None
        lines = trace.read_text(encoding="utf-8").splitlines()
        # A refusing hook must be observed, not inferred from a nonzero pkg
        # exit; always print enough exact native evidence before classification.
        print("STAGE0_PREINSTALL_NATIVE_OBSERVATION=" + json.dumps({
            "pkg_add_exit_code": attempted.returncode,
            "pkg_add_stdout_tail": attempted.stdout[-900:],
            "pkg_add_stderr_tail": attempted.stderr[-900:],
            "installed_after": installed,
            "payload_after": (payload.decode("ascii") if payload is not None else None),
            "hook_trace": lines,
        }, sort_keys=True), flush=True)
        outcome = classify(attempted.returncode, installed, payload, lines)
        return {
            "schema": 1, "status": "OBSERVED_INCOMING_PRE_INSTALL_REFUSAL_PKG_OUTCOME",
            "outcome": outcome, "pkg_add_exit_code": attempted.returncode,
            "installed_after": installed, "payload_after": (
                payload.decode("ascii") if payload is not None else None),
            "hook_trace": lines, "opnsense_version": version,
            "private_fixture_pkgdb": True, "private_fixture_payload": True,
            "synthetic_hooks_only": True, "actual_old_hook_tested": False,
            "actual_successor_tested": False,
            "independent_pretransaction_gate_qualified": False,
            "product_safety_acceptance_passed": False, "stage0_closed": False,
        }


def main():
    try:
        result = run_vm()
    except (Refusal, OSError, ValueError, UnicodeError) as exc:
        print("STAGE0_INCOMING_PREINSTALL=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    print("STAGE0_INCOMING_PREINSTALL=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
