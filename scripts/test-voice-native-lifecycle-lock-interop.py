#!/usr/bin/env python3
"""Non-activating cross-process lifecycle flock/FreeBSD lockf FD9 contract.

All tests use two independent file descriptions on private temporary inodes.
They NEVER open /var/run/zapret2-lifecycle.lock, Config.xml, IPFW or dvtws2.
A passing test only establishes FreeBSD kernel lock interoperability: it
does NOT solve Config.save() release, distributed configd handoff, or Apply.
"""
from __future__ import annotations

import errno
import fcntl
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SERVICE = (ROOT / "src/opnsense/scripts/OPNsense/Zapret/zapret_service.sh")
IS_FREEBSD = sys.platform.startswith("freebsd")
FREEBSD_LOCKF = Path("/usr/bin/lockf")


class LifecycleLockInterop(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="voice-lock-interop-")
        self.addCleanup(self.temp.cleanup)
        self.lock = Path(self.temp.name) / "lifecycle.lock"
        self.lock.touch(mode=0o600)
        self.assertEqual(0o600, self.lock.stat().st_mode & 0o777)

    def _open(self, path=None):
        return os.open(path or self.lock, os.O_RDWR | os.O_CLOEXEC)

    def _freebsd_lockf(self, path, *, sleep=False):
        self.assertTrue(IS_FREEBSD and FREEBSD_LOCKF.is_file(),
                        "native lockf must exist on FreeBSD")
        if sleep:
            code = (
                '( /usr/bin/lockf -s -t 3 9 || exit 75; '
                'printf "OWNED\\n"; /bin/sleep 1 ) 9>"$VOICE_TEST_LOCK"'
            )
        else:
            code = (
                '( /usr/bin/lockf -s -t 0 9 && '
                'printf "OWNED\\n" ) 9>"$VOICE_TEST_LOCK"'
            )
        env = dict(os.environ, VOICE_TEST_LOCK=str(path))
        if sleep:
            return subprocess.Popen(
                ["/bin/sh", "-c", code], env=env, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True,
            )
        return subprocess.run(
            ["/bin/sh", "-c", code], env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=8, check=False,
        )

    def test_separate_file_descriptions_do_not_share_a_fake_owner(self):
        first = self._open()
        second = self._open()
        try:
            fcntl.flock(first, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(OSError) as denied:
                fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn(denied.exception.errno, (errno.EWOULDBLOCK, errno.EAGAIN))
            fcntl.flock(first, fcntl.LOCK_UN)
            fcntl.flock(second, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(second)
            os.close(first)

    def test_production_service_fd9_lock_path_is_still_shared(self):
        text = SERVICE.read_text(encoding="utf-8")
        self.assertIn('LIFECYCLE_LOCK_FILE="${LIFECYCLE_LOCK_FILE:-/var/run/zapret2-lifecycle.lock}"', text)
        self.assertIn('"${LOCKF_BIN}" -s -t "${_service_lock_timeout}" 9', text)
        self.assertIn(') 9>"${LIFECYCLE_LOCK_FILE}"', text)
        self.assertIn('preflight_voice_cutover_journals || return 69', text)

    @unittest.skipUnless(IS_FREEBSD, "requires native FreeBSD /usr/bin/lockf")
    def test_python_flock_blocks_native_lockf_fd9_and_release_allows_it(self):
        holder = self._open()
        try:
            fcntl.flock(holder, fcntl.LOCK_EX)
            blocked = self._freebsd_lockf(self.lock)
            self.assertNotEqual(0, blocked.returncode, blocked.stdout + blocked.stderr)
            self.assertNotIn("OWNED", blocked.stdout)
            fcntl.flock(holder, fcntl.LOCK_UN)
            acquired = self._freebsd_lockf(self.lock)
            self.assertEqual(0, acquired.returncode, acquired.stdout + acquired.stderr)
            self.assertEqual("OWNED", acquired.stdout.strip())
        finally:
            os.close(holder)

    @unittest.skipUnless(IS_FREEBSD, "requires native FreeBSD /usr/bin/lockf")
    def test_freebsd_fd9_owner_outlives_lockf_helper_not_parent_shell(self):
        contender = self._open()
        proc = self._freebsd_lockf(self.lock, sleep=True)
        try:
            line = proc.stdout.readline().strip()
            self.assertEqual("OWNED", line,
                             "FreeBSD lockf did not acquire FD9: " +
                             proc.stderr.read() if proc.poll() is not None
                             else "missing lock holder readiness")
            with self.assertRaises(OSError) as denied:
                fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertIn(denied.exception.errno, (errno.EWOULDBLOCK, errno.EAGAIN))
            self.assertEqual(0, proc.wait(timeout=8))
            fcntl.flock(contender, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(contender, fcntl.LOCK_UN)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)
            proc.stdout.close()
            proc.stderr.close()
            os.close(contender)

    @unittest.skipUnless(IS_FREEBSD, "requires native FreeBSD /usr/bin/lockf")
    def test_different_private_inode_is_not_falsely_contended(self):
        other = Path(self.temp.name) / "unrelated.lock"
        other.touch(mode=0o600)
        holder = self._open()
        try:
            fcntl.flock(holder, fcntl.LOCK_EX)
            acquired = self._freebsd_lockf(other)
            self.assertEqual(0, acquired.returncode, acquired.stdout + acquired.stderr)
            self.assertEqual("OWNED", acquired.stdout.strip())
        finally:
            os.close(holder)


if __name__ == "__main__":
    unittest.main(verbosity=2)
