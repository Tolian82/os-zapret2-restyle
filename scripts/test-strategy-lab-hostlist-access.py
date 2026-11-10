#!/usr/bin/env python3
"""Regression for owner-live Stage50 post-drop hostlist access and cleanup."""

from __future__ import annotations

import os
import pwd
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src/opnsense/scripts/OPNsense/Zapret"
sys.path.insert(0, str(SRC))
from strategy_lab_py import hostlist_access  # noqa: E402


def check(ok: bool, why: str) -> None:
    if not ok:
        raise AssertionError(why)


def can_read_as(uid: int, gid: int, path: Path) -> bool:
    script = """import os, sys
os.setgroups([])
os.setgid(int(sys.argv[1]))
os.setuid(int(sys.argv[2]))
with open(sys.argv[3], encoding='utf-8') as fd: fd.read()
"""
    return subprocess.run(
        [sys.executable, "-c", script, str(gid), str(uid), str(path)],
        capture_output=True, text=True, check=False,
    ).returncode == 0


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="g11-stage50-hostlist-") as temporary:
        root = Path(temporary)
        # The real failure had a nontraversable ancestor, not bad file bits.
        root.chmod(0o755)
        private = root / "protected-zapret2-runtime"
        private.mkdir(mode=0o750)
        original = private / "hostlist.txt"
        original.write_text("www.youtube.com\n", encoding="utf-8")
        original.chmod(0o644)
        staging = root / "root-owned-staging"
        staging.mkdir(mode=0o755)
        os.environ["STRATEGY_LAB_HOSTLIST_STAGING_DIR"] = str(staging)
        if os.geteuid() != 0:
            # Only isolated mocks explicitly enable unprivileged staging.
            os.environ["STRATEGY_LAB_TEST_WAN_OVERRIDE"] = "1"
            os.environ["STRATEGY_LAB_TEST_HOSTLIST_STAGING"] = "1"
        else:
            os.environ.pop("STRATEGY_LAB_TEST_HOSTLIST_STAGING", None)
        job_id = "job.TestG11"
        for invalid in ("../escape", "job.bad/../../target", "job.invalid-hyphen"):
            try:
                hostlist_access.path_for(invalid)
                raise AssertionError("unsafe job ID accepted")
            except ValueError:
                pass

        staged = hostlist_access.stage(job_id, ["www.youtube.com"])
        info = staged.stat()
        check(staged == staging / f"zapret2-lab-hostlist-{job_id}", "shadow path mismatch")
        check(stat.S_IMODE(info.st_mode) == 0o640, "hostlist permissions not group read only")
        check(staged.read_text() == "www.youtube.com\n", "staged data mismatch")
        check(stat.S_IMODE(private.stat().st_mode) == 0o750, "protected ancestor changed")
        check(stat.S_IMODE(original.stat().st_mode) == 0o644, "original hostlist modified")

        if os.geteuid() == 0:
            nobody = pwd.getpwnam("nobody")
            check(info.st_uid == 0 and info.st_gid == nobody.pw_gid, "staged owner/group mismatch")
            check(can_read_as(nobody.pw_uid, nobody.pw_gid, staged),
                  "post-drop nobody cannot read staged hostlist")
            check(not can_read_as(nobody.pw_uid, nobody.pw_gid, original),
                  "private original became readable to nobody")
            check(not can_read_as(65533, 65533, staged),
                  "unrelated UID gained access to staged hostlist")
            print("STAGE50_REAL_NOBODY_READ=PASS")
        else:
            print("STAGE50_REAL_NOBODY_READ=SKIPPED(non-root; native FreeBSD gate required)")

        staging.chmod(0o777)
        try:
            hostlist_access.stage("job.badMode", ["www.youtube.com"])
            raise AssertionError("insecure parent accepted")
        except RuntimeError:
            pass
        finally:
            staging.chmod(0o755)
        check(not (staging / "zapret2-lab-hostlist-job.badMode").exists(),
              "failed staging created a file")

        # Even when the leaf staging directory is 0755, a closed ancestor
        # must cause refusal; this was the exact owner _47 class of defect.
        nested_staging = private / "leaf-staging"
        nested_staging.mkdir(mode=0o755)
        os.environ["STRATEGY_LAB_HOSTLIST_STAGING_DIR"] = str(nested_staging)
        try:
            hostlist_access.stage("job.closedParent", ["www.youtube.com"])
            raise AssertionError("closed ancestor accepted for staged hostlist")
        except RuntimeError:
            pass
        finally:
            os.environ["STRATEGY_LAB_HOSTLIST_STAGING_DIR"] = str(staging)
        check(not (nested_staging / "zapret2-lab-hostlist-job.closedParent").exists(),
              "closed ancestor created an inaccessible shadow")

        shell = f'''. "{SRC}/strategy_lab/common.sh"
. "{SRC}/strategy_lab/runtime.sh"
strategy_lab_candidate_hostlist_shadow_cleanup {job_id}
strategy_lab_candidate_hostlist_shadow_cleanup {job_id}
'''
        result = subprocess.run(["/bin/sh", "-c", shell], capture_output=True,
                                text=True, check=False, env=os.environ.copy())
        check(result.returncode == 0, f"cleanup failed: {result.stderr[:200]}")
        check(not staged.exists(), "staged hostlist survived cleanup")
        check(original.exists() and stat.S_IMODE(private.stat().st_mode) == 0o750,
              "original private runtime changed during cleanup")
    print("STAGE50_PARENT_0750_SHADOW_ACCESS_AND_CLEANUP=PASS")


if __name__ == "__main__":
    main()
