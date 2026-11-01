#!/usr/bin/env python3
"""Stage 0: separate package guard versus historical FD9 and unguarded native pkg.

Disposable OPNsense KVM ONLY. The authentic archived predecessor is installed
read-only for Status/provenance; every forced pkg replacement targets synthetic
fixtures in a PRIVATE package database and private payload directory.
No production upgrade helper, Stop/Start, IPFW mutation or gateway access.
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

HERE = Path(__file__).resolve().parent
FIXTURE = "zapret2-stage0-sidecar-only-fixture"
PHASES = ("pre-install", "post-install", "pre-deinstall", "post-deinstall")
SERVICE = "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"


class Refusal(Exception):
    pass


def require(ok, code):
    if not ok:
        raise Refusal(code)


def load(filename):
    spec = importlib.util.spec_from_file_location(
        filename.replace(".", "_").replace("-", "_"), HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def command(args, env=None):
    try:
        return subprocess.run(args, env=env, capture_output=True, text=True,
                              timeout=95, check=False)
    except (OSError, subprocess.SubprocessError):
        raise Refusal("NATIVE_COMMAND_FAILED_OR_TIMEOUT") from None


def done(args, env=None):
    result = command(args, env)
    require(result.returncode == 0, "FIXTURE_OPERATION_FAILED:" +
            str(result.returncode) + ":" + result.stderr.strip()[:180])
    return result.stdout


def native_lock_contender(path):
    # Independent shell opens FD9 *anew*, as historical service does.
    return command(["/bin/sh", "-c",
                    '(/usr/bin/lockf -s -t 0 9) 9>"$1"',
                    "sh", str(path)]).returncode


def build_fixture(work, role, version, trace, installed):
    require(role in ("old", "guarded", "direct"), "UNKNOWN_FIXTURE_ROLE")
    require(version in ("0.6.2_1", "0.6.2_40", "0.6.2_41"),
            "UNKNOWN_FIXTURE_VERSION")
    staging = work / ("staging-" + role)
    marker = installed / "fixture"
    payload = (role + "\n").encode("ascii")
    in_stage = staging / str(marker).lstrip("/")
    in_stage.parent.mkdir(parents=True)
    in_stage.write_bytes(payload)
    scripts = {}
    for phase in PHASES:
        tag = role + ":" + phase
        if role == "guarded" and phase in ("pre-install", "post-install"):
            script = (
                "#!/bin/sh\n"
                '"' + SERVICE + '" status >/dev/null 2>&1\n'
                'status=$?\n'
                'if [ "$status" -eq 1 ]; then\n'
                '  /bin/echo "' + tag + ':OLD_STATUS_STOPPED" >> "' + str(trace) + '"\n'
                '  exit 0\n'
                'fi\n'
                '/bin/echo "' + tag + ':OLD_STATUS_REFUSED" >> "' + str(trace) + '"\n'
                'exit 73\n'
            )
        else:
            script = ('#!/bin/sh\n/bin/echo "' + tag + '" >> "' +
                      str(trace) + '"\nexit 0\n')
        scripts[phase] = script
    manifest = {
        "name": FIXTURE, "origin": "sysutils/" + FIXTURE, "version": version,
        "abi": "FreeBSD:15:amd64", "arch": "freebsd:15:x86:64",
        "prefix": str(installed), "comment": "Isolated pkg sidecar lock fixture",
        "desc": "Private native package/FD9 scheduling test",
        "maintainer": "test@example.invalid", "www": "https://example.invalid",
        "licenselogic": "single", "licenses": ["MIT"],
        "scripts": scripts, "files": {str(marker): hashlib.sha256(payload).hexdigest()},
    }
    source = work / (role + ".json")
    source.write_text(json.dumps(manifest), encoding="utf-8")
    out = work / ("packages-" + role)
    out.mkdir()
    done(["pkg", "create", "-M", str(source), "-r", str(staging), "-o", str(out)])
    archives = list(out.glob(FIXTURE + "-" + version + ".pkg"))
    require(len(archives) == 1, "PACKAGE_FIXTURE_ARCHIVE_AMBIGUOUS")
    return archives[0], marker


def fixture_state(pkg, env, marker):
    r = command(pkg + ["query", "%n|%v", FIXTURE], env)
    require(r.returncode == 0, "FIXTURE_PKGDB_QUERY_FAILED")
    require(marker.is_file() and not marker.is_symlink(),
            "FIXTURE_PAYLOAD_MISSING_OR_FOREIGN")
    return r.stdout.strip(), marker.read_bytes()


def classify(positive_rc, direct_rc, guarded, bypass, traces):
    require(positive_rc == 0 and guarded ==
            (FIXTURE + "|0.6.2_40", b"guarded\n"),
            "SIDECAR_GUARDED_FIXTURE_NOT_INSTALLED")
    require(traces[:2] == ["old:pre-install", "old:post-install"],
            "INITIAL_OLD_FIXTURE_HOOKS_NOT_TRACED")
    for label in ("guarded:pre-install:OLD_STATUS_STOPPED",
                  "guarded:post-install:OLD_STATUS_STOPPED"):
        require(traces.count(label) == 1,
                "GENUINE_OLD_SERVICE_HOOK_STATUS_NOT_PROVEN:" + label)
    require(direct_rc == 0 and bypass == (FIXTURE + "|0.6.2_41", b"direct\n"),
            "DIRECT_PKG_SIDECAR_BYPASS_NOT_OBSERVED")
    require(traces.count("direct:pre-install") == 1 and
            traces.count("direct:post-install") == 1,
            "DIRECT_PKG_HOOKS_NOT_TRACED")
    return "SIDECAR_COMPATIBLE_BUT_DIRECT_PKG_BYPASSES_LOCK"


def prove(archive, guest, installed, old_status):
    require(os.geteuid() == 0 and os.uname().sysname == "FreeBSD" and
            os.uname().machine == "amd64", "REQUIRES_ROOT_FREEBSD_AMD64")
    require(guest.evaluate(guest.observe()).get("status") ==
            "PASS_ISOLATED_OPNSENSE_26_7_GUEST_IDENTITY",
            "UNQUALIFIED_DISPOSABLE_GUEST")
    # Install only the exact immutable public predecessor on throwaway guest.
    original = installed.install_and_verify(archive)
    pre = installed.pre
    fd9 = old_status
    hostname = pre.run("hostname", "-s").decode().strip()
    baseline = pre.run_guest(archive, hostname)
    require(baseline["status"] == "PASS_READ_ONLY_PROVENANCE",
            "HISTORICAL_PREDECESSOR_NOT_AUTHENTIC")
    fd9.assert_fresh_no_shared_journal()
    with tempfile.TemporaryDirectory(prefix="stage0-sidecar-lock-") as t:
        work = Path(t)
        db = work / "pkgdb"
        cache = work / "cache"
        payload = work / "payload"
        db.mkdir(mode=0o700)
        cache.mkdir(mode=0o700)
        env = dict(os.environ, PKG_DBDIR=str(db), PKG_CACHEDIR=str(cache),
                   ASSUME_ALWAYS_YES="yes",
                   LIFECYCLE_LOCK_FILE=str(work / "historical-fd9.lock"),
                   LOCKF_BIN="/usr/bin/lockf")
        pkg = ["pkg", "-o", "REPO_AUTOUPDATE=false"]
        trace = work / "hooks.trace"
        old, marker = build_fixture(work, "old", "0.6.2_1", trace, payload)
        new, checked_marker = build_fixture(work, "guarded", "0.6.2_40", trace, payload)
        direct, direct_marker = build_fixture(work, "direct", "0.6.2_41", trace, payload)
        require(marker == checked_marker == direct_marker,
                "INCONSISTENT_PRIVATE_FIXTURE_FILE")
        done(pkg + ["add", str(old)], env)
        require(fixture_state(pkg, env, marker) ==
                (FIXTURE + "|0.6.2_1", b"old\n"),
                "INITIAL_PRIVATE_FIXTURE_NOT_AUTHENTIC")
        # Completely separate controller gate. Historical Status still opens
        # its ORIGINAL FD9 and must return genuine STOPPED, without timeout.
        guard_file = work / "package-sidecar.lock"
        fd = os.open(guard_file, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            require(native_lock_contender(guard_file) != 0,
                    "INDEPENDENT_PACKAGE_GUARD_NOT_EXCLUSIVE")
            require(native_lock_contender(work / "historical-fd9.lock") == 0,
                    "ORIGINAL_FD9_INCORRECTLY_HELD_BY_PACKAGE_GUARD")
            initial = fd9.call_status(work / "historical-fd9.lock")
            fd9.prove_stopped(initial)
            # First operation represents a cooperating pkg frontend. Hooks
            # themselves call the genuine installed old service Status.
            cooperating = command(pkg + ["add", "-f", str(new)], env)
            guarded = fixture_state(pkg, env, marker)
            require(native_lock_contender(guard_file) != 0,
                    "SIDECAR_GUARD_LOST_AFTER_COOPERATING_PKG")
            after_cooperating = fd9.call_status(work / "historical-fd9.lock")
            fd9.prove_stopped(after_cooperating)
            # Same native pkg can be called DIRECTLY without consulting this
            # independent controller lock. This is the unsafe bypass witness.
            bypass_call = command(pkg + ["add", "-f", str(direct)], env)
            bypass = fixture_state(pkg, env, marker)
            require(native_lock_contender(guard_file) != 0,
                    "SIDECAR_GUARD_LOST_DURING_DIRECT_PKG")
            trace_lines = trace.read_text(encoding="ascii").splitlines()
            outcome = classify(cooperating.returncode, bypass_call.returncode,
                               guarded, bypass, trace_lines)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
        require(native_lock_contender(guard_file) == 0,
                "SIDECAR_LOCK_NOT_RELEASED")
        require(pre.run_guest(archive, hostname) == baseline,
                "AUTHENTIC_INSTALLED_PREDECESSOR_CHANGED")
        final_status = fd9.call_status(work / "historical-fd9.lock")
        fd9.prove_stopped(final_status)
    fd9.assert_fresh_no_shared_journal()
    return {
        "schema": 1, "status": "OBSERVED_ISOLATED_PACKAGE_SIDECAR_BYPASS",
        "outcome": outcome,
        "real_old_service_status_under_separate_guard": "STOPPED",
        "real_old_status_called_by_incoming_synthetic_hooks": True,
        "cooperating_pkg_rc": cooperating.returncode,
        "direct_uncoordinated_pkg_rc": bypass_call.returncode,
        "cooperating_synthetic_after": guarded[0],
        "direct_synthetic_after": bypass[0],
        "native_hook_trace": trace_lines,
        "independent_sidecar_lock_held_during_both_pkg_calls": True,
        "historical_fd9_unblocked_by_sidecar": True,
        "sidecar_released_after_test": True,
        "genuine_original_installed_provenance_preserved": True,
        "genuine_original_installed_service_stopped_after": True,
        "private_synthetic_pkgdb_and_payload": True,
        "unguarded_native_pkg_bypass_observed": True,
        "transaction_guard_enforced_for_direct_pkg": False,
        "real_predecessor_replaced": False,
        "real_running_or_foreign_ipfw_tested": False,
        "product_safety_acceptance_passed": False,
        "stage0_closed": False,
    }


def main():
    if len(sys.argv) != 2:
        print("STAGE0_SIDECAR=REFUSED:ARCHIVE_PATH_REQUIRED", file=sys.stderr)
        return 2
    guest = load("stage0-opnsense-guest-readonly.py")
    installed = load("stage0-opnsense-installed-predecessor.py")
    fd9 = load("stage0-opnsense-old-service-fd9.py")
    try:
        print("STAGE0_SIDECAR=" + json.dumps(
            prove(Path(sys.argv[1]), guest, installed, fd9), sort_keys=True))
    except (Refusal, installed.pre.Refusal, guest.Refusal, OSError, ValueError,
            KeyError, TypeError) as exc:
        print("STAGE0_SIDECAR=REFUSED:" + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
