#!/usr/bin/env python3
"""Real-Git upstream fault matrix: abort the *whole* setup process group.

Unlike a mocked guard, this exercises the actual setup_transaction.sh,
real extra_resources_upstream_guard.py, real Git checkout and sealed binary /
non-Git bytes. Service and lockf are local isolated test doubles only.
No network, firewall, OPNsense files, package manager or root privileges.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
TRANSACTION = ROOT / "src/opnsense/scripts/OPNsense/Zapret/setup_transaction.sh"
GUARD = ROOT / "src/opnsense/scripts/OPNsense/Zapret/extra_resources_upstream_guard.py"
GIT = shutil.which("git")
if not GIT:
    raise RuntimeError("git is required for the real-upstream interruption test")


def script(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\nset -eu\n" + body, encoding="utf-8")
    path.chmod(0o755)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class UpstreamInterrupted(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="upstream-cut-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runtime = self.root / "zapret"
        (self.runtime / "lua").mkdir(parents=True)
        (self.runtime / "files/fake").mkdir(parents=True)
        (self.runtime / "binaries/my").mkdir(parents=True)
        self.old_lua = b"return 'old upstream lua'\n"
        self.old_blob = b"old Git tracked BIN\n"
        self.orphan_lua = b"original orphan lua bytes\n"
        self.orphan_blob = b"original orphan BIN bytes\n"
        self.adopted_blob = b"preexisting user's target-named BIN\n"
        self.managed = b"return 'pinned additional lua'\n"
        self.old_binary = b"original compiled executable\n"
        self.git("init", "-q")
        self.git("config", "user.name", "Upstream Test")
        self.git("config", "user.email", "git@example.invalid")
        (self.runtime / "lua/native.lua").write_bytes(self.old_lua)
        (self.runtime / "files/fake/old.bin").write_bytes(self.old_blob)
        (self.runtime / "README").write_bytes(b"original tracked README\n")
        self.git("add", "lua", "files", "README")
        self.git("commit", "-qm", "old upstream")
        self.git("tag", "v1.0.4")
        self.old_sha = self.git_out("rev-parse", "HEAD")
        (self.runtime / "lua/native.lua").write_bytes(b"return 'new upstream'\n")
        (self.runtime / "files/fake/old.bin").unlink()
        (self.runtime / "files/fake/target.bin").write_bytes(b"new upstream target BIN\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "new upstream")
        self.git("tag", "v1.0.3")
        self.new_sha = self.git_out("rev-parse", "HEAD")
        self.git("checkout", "-q", "--detach", self.old_sha)
        self.resources = {
            "lua/managed.lua": self.managed,
            "lua/unowned.lua": self.orphan_lua,
            "files/fake/unowned.bin": self.orphan_blob,
            # A target upstream commit adopts the old untracked pathname.
            "files/fake/target.bin": self.adopted_blob,
        }
        for name, raw in self.resources.items():
            dest = self.runtime / name
            dest.write_bytes(raw)
        (self.runtime / "binaries/my/dvtws2").write_bytes(self.old_binary)
        (self.runtime / "binaries/my/dvtws2").chmod(0o755)
        self.state = self.root / "state"
        (self.state / "extra-resources").mkdir(parents=True)
        (self.state / "extra-resources/installed.json").write_text(json.dumps({
            "schema": 1,
            "source_commit": "f" * 40,
            "files": {"lua/managed.lua": digest(self.managed)},
        }))
        (self.state / "runtime.release").write_text("v1.0.4\n")
        self.service_state = self.root / "service-state"
        self.service_state.write_text("running\n")
        self.originally_running = True
        self.log = self.root / "native-events"
        self._create_mocks()

    def git(self, *args: str) -> None:
        subprocess.run([GIT, "-C", str(self.runtime), *args],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def git_out(self, *args: str) -> str:
        return subprocess.run([GIT, "-C", str(self.runtime), *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def _create_mocks(self) -> None:
        self.service = self.root / "native-service"
        self.setup = self.root / "setup"
        self.lockf = self.root / "lockf"
        self.configctl = self.root / "configctl"
        script(self.lockf, r"""
[ "$1" = "-s" ] && [ "$2" = "-t" ] || exit 64
shift 3
shift
exec "$@"
""")
        script(self.configctl, 'printf "OK\\n"\n')
        script(self.service, r"""
case "$1" in
    status|strategy-lab-status)
        case "$(cat "$TEST_SERVICE_STATE")" in
            running) exit 0 ;;
            stopped) exit 1 ;;
            *) exit 2 ;;
        esac
        ;;
    strategy-lab-stop)
        echo STOP >> "$TEST_NATIVE_EVENTS"
        printf 'stopped\n' > "$TEST_SERVICE_STATE"
        ;;
    strategy-lab-start)
        echo START >> "$TEST_NATIVE_EVENTS"
        printf 'running\n' > "$TEST_SERVICE_STATE"
        if [ "$TEST_CUT_POINT" = start ] &&
           [ "$(git -C "$TEST_ZAPRET_DIR" rev-parse HEAD)" = "$TEST_TARGET_SHA" ]; then
            "$TEST_PYTHON" -c 'import os,signal; os.killpg(os.getpgrp(),signal.SIGKILL)'
        fi
        ;;
    upstream-install)
        [ "$SETUP_TRANSACTION_LOCK_OWNER" = 1 ] || exit 75
        echo FD9 >> "$TEST_NATIVE_EVENTS"
        ( STRATEGY_LAB_LIFECYCLE_OWNER=1 UPSTREAM_RUNTIME_LIFECYCLE_OWNER=1 \
            "$TEST_TRANSACTION" install-under-native-lock "$2" ) 9>"$TEST_FD9_FILE"
        ;;
    upstream-recover-mutating)
        [ "$SETUP_TRANSACTION_LOCK_OWNER" = 1 ] || exit 75
        echo RECOVERY_FD9 >> "$TEST_NATIVE_EVENTS"
        ( STRATEGY_LAB_LIFECYCLE_OWNER=1 UPSTREAM_RECOVERY_LIFECYCLE_OWNER=1 \
            "$TEST_TRANSACTION" recover-mutating-under-parent-lock ) 9>"$TEST_FD9_FILE"
        ;;
    *) exit 64 ;;
esac
""")
        script(self.setup, r"""
[ "$1" = install-under-parent-lock ] || exit 64
[ "$(cat "$TEST_SERVICE_STATE")" = stopped ] || exit 75
[ "$UPSTREAM_RUNTIME_LIFECYCLE_OWNER" = 1 ] || exit 75
[ -f "$TEST_ROLLBACK/checkpoint" ] || exit 69
"$TEST_PYTHON" "$TEST_GUARD" preflight-switch "$TEST_TARGET_SHA"
"$TEST_PYTHON" "$TEST_GUARD" prune-orphans "$TEST_TARGET_SHA"
echo PRUNED >> "$TEST_NATIVE_EVENTS"
if [ "$TEST_CUT_POINT" = prune ]; then
    "$TEST_PYTHON" -c 'import os,signal; os.killpg(os.getpgrp(),signal.SIGKILL)'
fi
git -C "$TEST_ZAPRET_DIR" checkout --detach "$TEST_TARGET_SHA" >/dev/null 2>&1
git -C "$TEST_ZAPRET_DIR" reset --hard "$TEST_TARGET_SHA" >/dev/null
echo CHECKED_OUT >> "$TEST_NATIVE_EVENTS"
if [ "$TEST_CUT_POINT" = checkout ]; then
    "$TEST_PYTHON" -c 'import os,signal; os.killpg(os.getpgrp(),signal.SIGKILL)'
fi
printf 'new compiled executable\n' > "$TEST_ZAPRET_DIR/binaries/my/dvtws2"
chmod 0755 "$TEST_ZAPRET_DIR/binaries/my/dvtws2"
echo BUILT >> "$TEST_NATIVE_EVENTS"
if [ "$TEST_CUT_POINT" = dirty ]; then
    printf 'foreign post-cut tracked edit\n' > "$TEST_ZAPRET_DIR/README"
fi
if [ "$TEST_CUT_POINT" = build ] || [ "$TEST_CUT_POINT" = dirty ]; then
    "$TEST_PYTHON" -c 'import os,signal; os.killpg(os.getpgrp(),signal.SIGKILL)'
fi
"$TEST_PYTHON" "$TEST_GUARD" verify-switch-complete
""")

    def environment(self, point: str) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "TEST_CUT_POINT": point,
            "TEST_SERVICE_STATE": str(self.service_state),
            "TEST_NATIVE_EVENTS": str(self.log),
            "TEST_ZAPRET_DIR": str(self.runtime),
            "TEST_TRANSACTION": str(TRANSACTION),
            "TEST_TARGET_SHA": self.new_sha,
            "TEST_FD9_FILE": str(self.root / "fd9"),
            "TEST_PYTHON": sys.executable,
            "TEST_GUARD": str(GUARD),
            "TEST_ROLLBACK": str(self.state / "runtime-rollback"),
            "SETUP_SCRIPT": str(self.setup),
            "SERVICE_SCRIPT": str(self.service),
            "CONFIGCTL": str(self.configctl),
            "GIT_BIN": GIT,
            "FIND_BIN": shutil.which("find") or "/usr/bin/find",
            "ZAPRET_DIR": str(self.runtime),
            "STATE_DIR": str(self.state),
            "ACTIVE_RELEASE_FILE": str(self.state / "runtime.release"),
            "SETUP_STATUS": str(self.state / "setup.status"),
            "ROLLBACK_DIR": str(self.state / "runtime-rollback"),
            "RUN_DIR": str(self.root / "run"),
            "LOCKF_BIN": str(self.lockf),
            "EXTRA_PYTHON": sys.executable,
            "EXTRA_GUARD": str(GUARD),
        })
        return env

    def cut(self, point: str) -> None:
        # Isolate the process group: SIGKILL must bypass shell EXIT traps and
        # ordinary rollback, without killing the Python test runner.
        result = subprocess.run([str(TRANSACTION), "install", "v1.0.3"],
                                env=self.environment(point), start_new_session=True,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, -signal.SIGKILL,
                         f"no hard interruption at {point}: {result.stderr}")
        checkpoint = self.state / "runtime-rollback/checkpoint"
        self.assertTrue(checkpoint.is_file(), "hard cut lost sealed checkpoint")
        self.assertIn("phase=mutating", checkpoint.read_text())
        self.assertEqual(self.service_state.read_text().strip(),
                         "running" if point == "start" else "stopped")
        original_saved = self.state / "runtime-rollback/untracked-resources"
        for name, raw in self.resources.items():
            self.assertEqual((original_saved / name).read_bytes(), raw)
        actual_events = self.log.read_text().splitlines()
        # If the original service was already stopped, repeating Stop is
        # neither required nor desirable; FD9 must still remain inherited.
        self.assertEqual(actual_events[:2], ["FD9", "STOP"] if
                         self.originally_running else ["FD9", "PRUNED"])

    def recover(self, point: str, expect_ok: bool) -> subprocess.CompletedProcess[str]:
        result = subprocess.run([str(TRANSACTION), "recover-mutating-stopped"],
                                env=self.environment(point), capture_output=True,
                                text=True, timeout=20)
        self.assertEqual(result.returncode == 0, expect_ok,
                         f"recovery result: {result.stdout}\n{result.stderr}")
        return result

    def assert_original(self, originally_running: bool = True) -> None:
        self.assertEqual(self.git_out("rev-parse", "HEAD"), self.old_sha)
        self.assertEqual((self.runtime / "lua/native.lua").read_bytes(), self.old_lua)
        self.assertEqual((self.runtime / "files/fake/old.bin").read_bytes(), self.old_blob)
        self.assertEqual((self.runtime / "README").read_bytes(), b"original tracked README\n")
        for name, raw in self.resources.items():
            self.assertEqual((self.runtime / name).read_bytes(), raw)
        self.assertEqual((self.runtime / "binaries/my/dvtws2").read_bytes(),
                         self.old_binary)
        self.assertEqual((self.state / "runtime.release").read_text(), "v1.0.4\n")
        self.assertEqual(self.service_state.read_text(),
                         "running\n" if originally_running else "stopped\n")
        self.assertFalse((self.state / "runtime-rollback").exists())

    def test_hard_cut_after_prune(self) -> None:
        self._perform_recovery("prune")

    def test_hard_cut_after_checkout(self) -> None:
        self._perform_recovery("checkout")

    def test_hard_cut_after_build(self) -> None:
        self._perform_recovery("build")

    def _perform_recovery(self, point: str) -> None:
        self.cut(point)
        self.assertEqual(self.git_out("rev-parse", "HEAD"),
                         self.old_sha if point == "prune" else self.new_sha)
        self.recover(point, True)
        self.assert_original()
        self.assertIn("RECOVERY_FD9", self.log.read_text())
        self.assertIn("START", self.log.read_text())

    def test_stopped_original_stays_stopped_after_prune_cut(self) -> None:
        self.service_state.write_text("stopped\n")
        self.originally_running = False
        self.cut("prune")
        self.recover("prune", True)
        self.assert_original(originally_running=False)
        self.assertNotIn("START", self.log.read_text())

    def test_power_cut_after_target_start_refuses_running_recovery(self) -> None:
        self.cut("start")
        self.assertEqual(self.git_out("rev-parse", "HEAD"), self.new_sha)
        self.recover("start", False)
        self.assertTrue((self.state / "runtime-rollback/checkpoint").is_file())
        self.assertEqual(self.service_state.read_text(), "running\n")
        # Only an explicitly verified STOPPED owner may be recovered.
        self.service_state.write_text("stopped\n")  # simulated owner stop
        self.recover("start", True)
        self.assert_original()

    def test_partial_checkout_dirty_tracked_refuses_without_overwrite(self) -> None:
        self.cut("dirty")
        dirty = (self.runtime / "README").read_bytes()
        self.recover("dirty", False)
        self.assertEqual((self.runtime / "README").read_bytes(), dirty)
        self.assertTrue((self.state / "runtime-rollback/checkpoint").exists())
        self.assertEqual(self.git_out("rev-parse", "HEAD"), self.new_sha)
        self.assertEqual(self.service_state.read_text(), "stopped\n")

    def test_tampered_saved_orphan_refuses_and_retains_evidence(self) -> None:
        self.cut("checkout")
        saved = self.state / "runtime-rollback/untracked-resources/files/fake/unowned.bin"
        saved.write_bytes(b"tampered evidence")
        self.recover("checkout", False)
        self.assertEqual(self.git_out("rev-parse", "HEAD"), self.new_sha)
        self.assertTrue((self.state / "runtime-rollback/checkpoint").exists())
        self.assertEqual(self.service_state.read_text(), "stopped\n")


if __name__ == "__main__":
    unittest.main()
