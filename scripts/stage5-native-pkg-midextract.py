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
)


def witness_state(witnesses):
    """Physical two-sided proof; an unrelated/half-written file is never PASS."""
    restored = dirty = foreign = 0
    for path, original, marked in witnesses:
        try:
            data = path.read_bytes()
        except OSError:
            foreign += 1
            continue
        if data == original:
            restored += 1
        elif data == marked:
            dirty += 1
        else:
            foreign += 1
    return restored, dirty, foreign


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


def interrupt_real_native_pkg_midextract(stage, witnesses, need):
    """A real pkg with syscall tracing for enough observation time.

    No pkg modifications, LD_PRELOAD, shell pkg interceptor, archive rewrite,
    GUI state mutation or alternate lifecycle owner. The test guest is discarded.
    """
    need(Path("/usr/bin/truss").is_file(), "MIDEXTRACT_NATIVE_TRUSS_UNAVAILABLE")
    # Distinct known tampered states are test-only evidence; never pre-corrupt
    # shared Apply/runtime/Config/IPFW. The old Auto generation must be STOPPED.
    for path, original, marked in witnesses:
        need(path.read_bytes() == original, "MIDEXTRACT_CHANGED_BEFORE_MARKING")
        path.write_bytes(marked)
    need(witness_state(witnesses) == (0, len(witnesses), 0),
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
                ["/usr/bin/truss", "-f", "-t", "@file", "-o", str(trace),
                 "/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                 "add", "-f", str(stage)],
                env=env, stdout=pkg_out, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            captured = None
            try:
                deadline = time.monotonic() + 120
                while time.monotonic() < deadline:
                    need(not postinstall.exists(), "MIDEXTRACT_REACHED_POSTINSTALL")
                    need(proc.poll() is None, "MIDEXTRACT_PKG_EXITED_WITHOUT_WINDOW")
                    observation = witness_state(witnesses)
                    if observation[0] > 0 and observation[1] > 0 and observation[2] == 0:
                        os.killpg(proc.pid, signal.SIGSTOP)
                        time.sleep(0.05)
                        captured = witness_state(witnesses)
                        need(captured[0] > 0 and captured[1] > 0 and
                             captured[2] == 0 and not postinstall.exists(),
                             "MIDEXTRACT_MIXED_WINDOW_NOT_STABLE")
                        break
                    # Mid-write transient bytes are expected while pkg extracts.
                    # Qualify only an exact restored/marked mixed window.
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
