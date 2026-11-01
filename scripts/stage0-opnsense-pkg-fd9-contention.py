#!/usr/bin/env python3
"""Stage 0: characterize original-FD9 style lock vs native pkg hook execution.

ONLY a disposable OPNsense 26.7 guest. Synthetic packages/private pkgdb; no
actual plugin install, Stop, IPFW mutation, owner's appliance or transaction
authorization. A pkg exit 0 after hook refusal is evidence of a hazard.
"""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

NAME = "zapret2-stage0-fd9-hook-fixture"
OLD = "0.6.2_1"
NEW = "0.6.2_39"
PHASES = ("pre-install", "post-install", "pre-deinstall", "post-deinstall")


class Refusal(Exception):
    pass


def require(yes, reason):
    if not yes:
        raise Refusal(reason)


def command(args, env=None):
    try:
        return subprocess.run(args, env=env, capture_output=True, text=True,
                              check=False, timeout=90)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_COMMAND_UNAVAILABLE_OR_TIMEOUT") from None


def must_succeed(args, env=None):
    r = command(args, env)
    require(r.returncode == 0,
            "NATIVE_FIXTURE_SETUP_REFUSED:" + " ".join(args[:3]) +
            ":" + str(r.returncode) + ":" + " ".join(r.stderr.split())[:150])
    return r.stdout


def phase_script(role, phase, trace, lock):
    require(role in ("old", "new") and phase in PHASES,
            "UNQUALIFIED_SYNTHETIC_PHASE")
    line = role + ":" + phase
    script = "#!/bin/sh\n"
    if role == "new" and phase in ("pre-install", "post-install"):
        script += (
            '(\n'
            '  /usr/bin/lockf -s -t 0 9\n'
            ') 9>"' + str(lock) + '"\n'
            'if [ "$?" -ne 0 ]; then\n'
            '  /bin/echo "' + line + ':FD9_BUSY" >> "' + str(trace) + '"\n'
            '  exit 73\n'
            'fi\n'
        )
        line += ":FD9_FREE"
    return script + '/bin/echo "' + line + '" >> "' + str(trace) + '"\nexit 0\n'


def build(work, role, version, trace, lock):
    stage = work / ("stage-" + role)
    prefix = work / "installed"
    marker = prefix / "fixture"
    payload = (role + "\n").encode("ascii")
    source_file = stage / str(marker).lstrip("/")
    source_file.parent.mkdir(parents=True, exist_ok=True)
    source_file.write_bytes(payload)
    scripts = {p: phase_script(role, p, trace, lock) for p in PHASES}
    manifest = {
        "name": NAME, "origin": "sysutils/" + NAME, "version": version,
        "abi": "FreeBSD:15:amd64", "arch": "freebsd:15:x86:64",
        "prefix": str(prefix), "comment": "Private FD9 pkg fixture",
        "desc": "Stage 0 disposable package hook lock contention witness",
        "maintainer": "test@example.invalid", "www": "https://example.invalid",
        "licenselogic": "single", "licenses": ["MIT"],
        "scripts": scripts,
        "files": {str(marker): hashlib.sha256(payload).hexdigest()},
    }
    source = work / (role + ".json")
    source.write_text(json.dumps(manifest), encoding="utf-8")
    output = work / ("packages-" + role)
    output.mkdir()
    must_succeed(["pkg", "create", "-M", str(source), "-r", str(stage), "-o", str(output)])
    paths = list(output.glob(NAME + "-" + version + ".pkg"))
    require(len(paths) == 1, "SYNTHETIC_ARCHIVE_IDENTITY_AMBIGUOUS")
    return paths[0], marker


def independent_fd9_probe(lock):
    script = '(/usr/bin/lockf -s -t 0 9) 9>"' + str(lock) + '"'
    return command(["/bin/sh", "-c", script]).returncode


def classify(rc, identity, payload, phases):
    require(phases[:2] == ["old:pre-install", "old:post-install"],
            "OLD_FIXTURE_SETUP_TRACE_UNVERIFIED")
    for entry in ("new:pre-install:FD9_BUSY", "new:post-install:FD9_BUSY"):
        require(phases.count(entry) == 1, "NEW_HOOK_LOCK_CONTENTION_NOT_TRACED:" + entry)
    if identity == NAME + "|" + NEW and payload == b"new\n":
        return "PKG_REPLACED_FIXTURE_DESPITE_BOTH_FD9_HOOK_REFUSALS"
    if identity == NAME + "|" + OLD and payload == b"old\n" and rc != 0:
        return "PKG_REFUSED_AND_PRESERVED_OLD_FIXTURE"
    return "PARTIAL_OR_INCONSISTENT_PKG_STATE_AFTER_LOCK_CONFLICT"


def prove(guest):
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "REQUIRES_ROOT_FREEBSD_AMD64")
    # Existing verified guest identity requires OPNsense 26.7/FreeBSD:15,
    # virtual execution and *no real old Zapret2 package installed*.
    identity = guest.evaluate(guest.observe())
    require(identity.get("status") == "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
            "UNQUALIFIED_OPNSENSE_GUEST")
    with tempfile.TemporaryDirectory(prefix="stage0-fd9-pkg-hook-") as folder:
        work = Path(folder)
        db = work / "pkgdb"
        cache = work / "cache"
        db.mkdir(mode=0o700)
        cache.mkdir(mode=0o700)
        env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
                   ASSUME_ALWAYS_YES="yes")
        pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
        lock = work / "lifecycle.lock"
        trace = work / "trace"
        old, marker = build(work, "old", OLD, trace, lock)
        new, check_marker = build(work, "new", NEW, trace, lock)
        require(marker == check_marker, "FIXTURE_MARKER_PATH_MISMATCH")
        must_succeed(pkg + ["add", str(old)], env)
        require(must_succeed(pkg + ["query", "%n|%v", NAME], env).strip() ==
                NAME + "|" + OLD and marker.read_bytes() == b"old\n",
                "OLD_SYNTHETIC_FIXTURE_NOT_INSTALLED")
        fd = os.open(lock, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(independent_fd9_probe(lock) != 0,
                    "PARENT_FD9_NOT_EXCLUSIVE_BEFORE_PKG")
            attempted = command(pkg + ["add", "-f", str(new)], env)
            require(independent_fd9_probe(lock) != 0,
                    "PARENT_FD9_LOST_DURING_PKG_TRANSACTION")
            q = command(pkg + ["query", "%n|%v", NAME], env)
            require(q.returncode in (0, 1), "PKGDB_UNREADABLE_AFTER_CONTENTION")
            installed = q.stdout.strip() if q.returncode == 0 else "ABSENT"
            payload = marker.read_bytes() if marker.is_file() and not marker.is_symlink() else None
            phases = trace.read_text(encoding="ascii").splitlines()
            outcome = classify(attempted.returncode, installed, payload, phases)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        require(independent_fd9_probe(lock) == 0,
                "PARENT_FD9_NOT_RELEASED_AFTER_EXPERIMENT")
        return {
            "schema": 1, "status": "OBSERVED_SYNTHETIC_PKG_HOOK_FD9_CONTENTION",
            "outcome": outcome, "pkg_exit_code": attempted.returncode,
            "pkg_stderr_tail": attempted.stderr[-500:],
            "hook_trace": phases, "installed_after": installed,
            "payload_after": payload.decode("ascii") if payload else None,
            "parent_fd9_held_across_pkg": True,
            "independent_contender_refused_before_and_after_pkg": True,
            "lock_available_after_release": True,
            "synthetic_pkg_only": True, "private_pkgdb_and_payload": True,
            "historical_old_hooks_executed": False,
            "real_predecessor_replaced": False,
            "transaction_owner_gate_implemented": False,
            "product_safety_acceptance_passed": False, "stage0_closed": False,
        }


def main():
    spec = importlib.util.spec_from_file_location(
        "guest", Path(__file__).with_name("stage0-opnsense-guest-readonly.py"))
    guest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guest)
    try:
        print("STAGE0_PKG_FD9=" + json.dumps(prove(guest), sort_keys=True))
    except (Refusal, OSError, ValueError, KeyError) as exc:
        print("STAGE0_PKG_FD9=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
