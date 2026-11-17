"""Disposable-native failure injection helpers (never installed or invoked in production)."""
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time

WITNESS_RELATIVE = (
    "mvc/app/views/OPNsense/Zapret/diagnostics.volt",
    "mvc/app/views/OPNsense/Zapret/general.volt",
    "mvc/app/views/OPNsense/Zapret/voice.volt",
    "mvc/app/controllers/OPNsense/Zapret/forms/general.xml",
    "mvc/app/controllers/OPNsense/Zapret/forms/voice.xml",
    "mvc/app/models/OPNsense/Zapret/Menu/Menu.xml",
    "mvc/app/models/OPNsense/Zapret/ACL/ACL.xml",
    # Deliberately span early MVC and late package-owned support files.
    # These are never executed by the stopped engine in the disposable guest.
    "service/conf/actions.d/actions_zapret.conf",
    "service/templates/OPNsense/Zapret/hostlist.txt",
    "service/templates/OPNsense/Zapret/zapret.conf",
    "share/zapret2-restyle/purge-os-zapret2-restyle.sh",
)


def witness_state(witnesses):
    """Physical two-sided proof; an unrelated/half-written file is never PASS."""
    restored = dirty = missing = foreign = 0
    for path, original, marked in witnesses:
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            missing += 1
            continue
        except OSError:
            foreign += 1
            continue
        if data == original:
            restored += 1
        elif data == marked:
            dirty += 1
        else:
            foreign += 1
    return restored, dirty, missing, foreign


def select_native_witnesses(root, stage, run, need):
    probe = run(["/usr/bin/tar", "-xOf", str(stage), "+MANIFEST"], timeout=30)
    need(probe.returncode == 0 and len(probe.stdout) < 512 * 1024,
         "MIDEXTRACT_MANIFEST_UNAVAILABLE")
    manifest = json.loads(probe.stdout)
    entries = manifest.get("files")
    need(isinstance(entries, dict), "MIDEXTRACT_NO_MANIFEST_FILES")
    declared = {"/" + key.lstrip("/") for key in entries}
    witnesses = []
    for relative in WITNESS_RELATIVE:
        target = Path("/usr/local/opnsense") / relative
        source = root / "src" / "opnsense" / relative
        need(str(target) in declared and source.is_file(),
             "MIDEXTRACT_WITNESS_NOT_IN_EXACT_ARCHIVE")
        st = target.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
             st.st_nlink == 1 and st.st_size <= 1024 * 1024 and
             not (st.st_mode & 0o022), "MIDEXTRACT_WITNESS_NOT_TRUSTED")
        original = source.read_bytes()
        need(target.read_bytes() == original and len(original) > 0,
             "MIDEXTRACT_ORIGINAL_PACKAGE_BYTES_DRIFT")
        marker = b"\n<!-- VM-only native package extraction witness -->\n"
        marked = original + marker
        witnesses.append((target, original, marked))
    need(len(witnesses) >= 5, "MIDEXTRACT_TOO_FEW_WITNESSES")
    return witnesses


def trace_pkg_command(trace, stage):
    """Portable FreeBSD 15 truss form; -t filters exist only in newer HEAD."""
    return ["/usr/bin/truss", "-f", "-o", str(trace),
            "/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
            "add", "-f", str(stage)]



def interrupt_real_native_pkg_midextract(stage, witnesses, need):
    """A real pkg with syscall tracing for enough observation time.

    No pkg modifications, LD_PRELOAD, shell pkg interceptor, archive rewrite,
    GUI state mutation or alternate lifecycle owner. The test guest is discarded.
    """
    need(Path("/usr/bin/truss").is_file(), "MIDEXTRACT_NATIVE_TRUSS_UNAVAILABLE")
    # Refuse before any test-owned GUI marker write if the exact installed
    # FreeBSD ptrace tracer cannot actually run a harmless local command.
    with tempfile.TemporaryDirectory(prefix="native-truss-probe-", dir="/root") as preflight:
        probe = subprocess.run(["/usr/bin/truss", "-o", str(Path(preflight) / "trace"),
                                "/usr/bin/true"], capture_output=True, timeout=15)
        need(probe.returncode == 0, "MIDEXTRACT_TRUSS_NATIVE_PREFLIGHT_FAILED")
    # Distinct known tampered states are test-only evidence; never pre-corrupt
    # shared Apply/runtime/Config/IPFW. The old Auto generation must be STOPPED.
    for path, original, marked in witnesses:
        need(path.read_bytes() == original, "MIDEXTRACT_CHANGED_BEFORE_MARKING")
        path.write_bytes(marked)
    need(witness_state(witnesses) == (0, len(witnesses), 0, 0),
         "MIDEXTRACT_WITNESSES_NOT_READY")
    with tempfile.TemporaryDirectory(prefix="native-midextract-", dir="/root") as tmp:
        folder = Path(tmp)
        trace = folder / "syscalls.txt"
        output = folder / "pkg.log"
        postinstall = folder / "postinstall-entered"
        helper = folder / "register-guard.sh"
        helper.write_text(
            "#!/bin/sh\n"
            "[ \"${1:-}\" = install ] || exit 0\n"
            "printf 'postinstall-reached\\n' > '" + str(postinstall) + "'\n"
            "exit 82\n"
        )
        helper.chmod(0o700)
        env = dict(os.environ)
        env["FIRMWARE_REGISTER"] = str(helper)
        with output.open("wb") as pkg_out:
            proc = subprocess.Popen(
                trace_pkg_command(trace, stage),
                env=env, stdout=pkg_out, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            captured = None
            try:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    observation = witness_state(witnesses)
                    if postinstall.exists() or proc.poll() is not None:
                        # Bounded source-file census ONLY. No raw pkg/truss log,
                        # Config, hostlist, command argv or secret-bearing text.
                        print("NATIVE_MIDEXTRACT_WINDOW_REFUSAL=" + json.dumps({
                            "phase": "postinstall" if postinstall.exists() else "pkg-exited",
                            "restored": observation[0], "marked": observation[1],
                            "missing": observation[2], "foreign": observation[3],
                        }, sort_keys=True), flush=True)
                        need(False, "MIDEXTRACT_REACHED_POSTINSTALL" if postinstall.exists()
                             else "MIDEXTRACT_PKG_EXITED_WITHOUT_WINDOW")
                    if observation[0] > 0 and observation[1] + observation[2] > 0 and observation[3] == 0:
                        os.killpg(proc.pid, signal.SIGSTOP)
                        time.sleep(0.05)
                        captured = witness_state(witnesses)
                        need(captured[0] > 0 and captured[1] + captured[2] > 0 and
                             captured[3] == 0 and not postinstall.exists(),
                             "MIDEXTRACT_MIXED_WINDOW_NOT_STABLE")
                        break
                    # Mid-write transient bytes are expected while pkg extracts.
                    # Qualify only exact restored/marked/missing mixed states.
                    time.sleep(0.001)
                need(captured is not None, "MIDEXTRACT_NO_PHYSICAL_PARTIAL_WINDOW")
            finally:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=20)
            need(proc.returncode == -signal.SIGKILL,
                 "MIDEXTRACT_PKG_PROCESS_NOT_KILLED")
            need(not postinstall.exists() and
                 witness_state(witnesses) == captured,
                 "MIDEXTRACT_POST_KILL_FILE_STATE_DRIFT")
            return captured
