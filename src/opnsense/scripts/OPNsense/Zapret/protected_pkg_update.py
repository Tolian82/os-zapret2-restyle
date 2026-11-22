#!/usr/bin/env python3
"""Native, plugin-owned pkg replacement coordinator; never a pkg interceptor.

The installed zapret_service.sh is the only lifecycle/FD9 owner. This module
stages one immutable root-owned .pkg, calls that existing owner for prepare and
finish, and invokes ordinary pkg exactly once between those two transitions.
An interrupted/ambiguous replacement remains durably blocked for review.
"""
from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

PRODUCT = "os-zapret2-restyle"
BASE = Path("/var/db/zapret2/pkg-update")
ACTIVE = BASE / "operation.json"
LIFECYCLE = Path(os.environ.get("LIFECYCLE_LOCK_FILE",
                                "/var/run/zapret2-lifecycle.lock"))
SCRIPT_DIR = Path(__file__).resolve().parent
SERVICE = SCRIPT_DIR / "zapret_service.sh"
MAX_ARCHIVE = 256 * 1024 * 1024
MAX_MANIFEST = 512 * 1024
VERSION_PATTERN = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+_[0-9]+\Z")
FAILURE_MARKERS = (
    "PRE-INSTALL script failed", "PRE-DEINSTALL script failed",
    "POST-INSTALL script failed", "POST-DEINSTALL script failed",
    "lua script failed",
)


class Refused(Exception):
    pass


def need(ok: bool, reason: str) -> None:
    if not ok:
        raise Refused(reason)


def trusted_directory(path: Path) -> None:
    st = path.lstat()
    need(stat.S_ISDIR(st.st_mode) and st.st_uid == 0 and
         not (st.st_mode & 0o022), "UNTRUSTED_DIRECTORY")


def root_and_private_base() -> None:
    need(os.geteuid() == 0, "ROOT_REQUIRED")
    for parent in (Path("/var"), Path("/var/db")):
        trusted_directory(parent)
    if not BASE.parent.exists() and not BASE.parent.is_symlink():
        BASE.parent.mkdir(mode=0o700)
        fd = os.open(Path("/var/db"), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    trusted_directory(BASE.parent)
    if not BASE.exists() and not BASE.is_symlink():
        BASE.mkdir(mode=0o700)
    trusted_directory(BASE)
    need((BASE.stat().st_mode & 0o077) == 0, "UPDATE_DIRECTORY_NOT_PRIVATE")


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as src:
        for chunk in iter(lambda: src.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def inspect_regular(path: Path, *, private: bool) -> None:
    st = path.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1,
         "UNTRUSTED_PACKAGE_FILE")
    need(st.st_size > 0 and st.st_size <= MAX_ARCHIVE,
         "PACKAGE_SIZE_REFUSED")
    need(not (st.st_mode & (0o077 if private else 0o022)),
         "PACKAGE_PERMISSIONS_REFUSED")


def native_command(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, text=True, capture_output=True,
                              check=False, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Refused("NATIVE_COMMAND_FAILED_OR_TIMED_OUT") from exc


def manifest_identity(path: Path) -> str:
    out = native_command(["/usr/bin/tar", "-xOf", str(path), "+MANIFEST"])
    need(out.returncode == 0 and len(out.stdout) <= MAX_MANIFEST,
         "PACKAGE_MANIFEST_MISSING")
    try:
        manifest = json.loads(out.stdout)
    except (TypeError, ValueError) as exc:
        raise Refused("PACKAGE_MANIFEST_INVALID") from exc
    version = manifest.get("version")
    need(manifest.get("name") == PRODUCT and isinstance(version, str) and
         VERSION_PATTERN.fullmatch(version) is not None,
         "PACKAGE_IDENTITY_REFUSED")
    abi = native_command(["/usr/sbin/pkg", "config", "ABI"])
    need(abi.returncode == 0 and
         manifest.get("abi") == abi.stdout.strip(),
         "PACKAGE_ABI_REFUSED")
    return version


def installed_version() -> str:
    out = native_command(["/usr/sbin/pkg", "query", "%v", PRODUCT])
    need(out.returncode == 0 and
         VERSION_PATTERN.fullmatch(out.stdout.strip()) is not None,
         "INSTALLED_PRODUCT_MISSING")
    return out.stdout.strip()


def fd9_is_original_owner() -> None:
    need(os.geteuid() == 0, "ROOT_REQUIRED")
    actual = os.fstat(9)
    expected = LIFECYCLE.lstat()
    need(stat.S_ISREG(expected.st_mode) and expected.st_uid == 0 and
         actual.st_dev == expected.st_dev and
         actual.st_ino == expected.st_ino,
         "ORIGINAL_FD9_IDENTITY_REFUSED")
    # A fresh independent open MUST conflict with the already-held flock.
    other = os.open(LIFECYCLE, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            need(isinstance(exc, BlockingIOError) or
                 getattr(exc, "errno", None) in (errno.EWOULDBLOCK, errno.EAGAIN),
                 "FD9_LOCK_INSPECTION_FAILED")
        else:
            fcntl.flock(other, fcntl.LOCK_UN)
            raise Refused("ORIGINAL_FD9_NOT_HELD")
    finally:
        os.close(other)


def validated_stage(raw: str, digest: str, version: str) -> Path:
    need(re.fullmatch(r"[a-f0-9]{64}", digest) is not None and
         VERSION_PATTERN.fullmatch(version) is not None,
         "INVALID_CANDIDATE_ID")
    path = Path(raw)
    need(path.is_absolute() and path.parent == BASE and
         path.name.startswith("incoming-") and path.suffix == ".pkg",
         "STAGE_PATH_REFUSED")
    inspect_regular(path, private=True)
    need(hash_file(path) == digest and manifest_identity(path) == version,
         "STAGED_CANDIDATE_CHANGED")
    return path


def read_active() -> dict:
    fd = os.open(ACTIVE, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
             st.st_nlink == 1 and not (st.st_mode & 0o077) and
             0 < st.st_size <= 4096, "UNTRUSTED_ACTIVE_RECORD")
        raw = os.read(fd, 4097)
        need(len(raw) <= 4096, "ACTIVE_RECORD_TOO_LARGE")
        data = json.loads(raw)
        need(isinstance(data, dict) and data.get("schema") == 1 and
             data.get("phase") in ("prepared", "postinstall-attested") and
             data.get("was_running") in (True, False),
             "ACTIVE_RECORD_INVALID")
        return data
    finally:
        os.close(fd)


def validate_record(digest: str, version: str) -> dict:
    data = read_active()
    need(data.get("sha256") == digest and
         data.get("to_version") == version,
         "ACTIVE_OPERATION_MISMATCH")
    validated_stage(data["stage"], digest, version)
    return data


def durable_directory() -> None:
    fd = os.open(BASE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def record(raw: str, digest: str, version: str, running: str) -> None:
    fd9_is_original_owner()
    root_and_private_base()
    need(running in ("running", "stopped"), "PREVIOUS_STATE_REFUSED")
    need(not ACTIVE.exists() and not ACTIVE.is_symlink(),
         "PREVIOUS_UPDATE_REQUIRES_REVIEW")
    validated_stage(raw, digest, version)
    before = installed_version()
    data = {
        "schema": 1, "phase": "prepared",
        "stage": raw, "sha256": digest, "to_version": version,
        "from_version": before, "was_running": running == "running",
    }
    body = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    fd = os.open(ACTIVE, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(body)
            out.flush()
            os.fsync(out.fileno())
    finally:
        durable_directory()
    print("pkg-update-recorded=1")


def postinstall_attest() -> None:
    # Called only by the installed package's *actual* native POST_INSTALL
    # hook, AFTER all its mandatory registration/template/configd work.
    # The FD9 owner remains the sole writer of the existing operation.json.
    fd9_is_original_owner()
    root_and_private_base()
    data = read_active()
    need(data.get("phase") == "prepared", "POSTINSTALL_PHASE_REFUSED")
    validated_stage(data["stage"], data["sha256"], data["to_version"])
    data["phase"] = "postinstall-attested"
    body = (json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n").encode()
    need(len(body) <= 4096, "POSTINSTALL_RECORD_TOO_LARGE")
    fd, tmp = tempfile.mkstemp(prefix=".postinstall-", dir=BASE)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(body)
            output.flush()
            os.fsync(output.fileno())
        os.replace(tmp, ACTIVE)
        durable_directory()
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)
    print("pkg-update-postinstall-attested=1")


def inspect(digest: str, version: str) -> dict:
    fd9_is_original_owner()
    root_and_private_base()
    data = validate_record(digest, version)
    need(data.get("phase") == "postinstall-attested",
         "NATIVE_POSTINSTALL_NOT_ATTESTED")
    need(installed_version() == version, "SUCCESSOR_NOT_INSTALLED")
    return data


def complete(digest: str, version: str) -> None:
    inspect(digest, version)
    ACTIVE.unlink()
    durable_directory()
    print("pkg-update-committed=1")


def stage_archive(path: Path) -> tuple[Path, str, str]:
    root_and_private_base()
    need(not ACTIVE.exists() and not ACTIVE.is_symlink(),
         "PREVIOUS_UPDATE_REQUIRES_REVIEW")
    need(path.is_absolute(), "ABSOLUTE_PACKAGE_PATH_REQUIRED")
    inspect_regular(path, private=False)
    fd, target = tempfile.mkstemp(prefix="incoming-", suffix=".pkg", dir=BASE)
    staged = Path(target)
    try:
        with os.fdopen(fd, "wb") as output:
            with path.open("rb") as source:
                total = 0
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    total += len(chunk)
                    need(total <= MAX_ARCHIVE, "PACKAGE_SIZE_REFUSED")
                    output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        staged.chmod(0o600)
        durable_directory()
        digest = hash_file(staged)
        version = manifest_identity(staged)
        return staged, digest, version
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def restore_finish_evidence(finished: subprocess.CompletedProcess) -> str:
    """Bounded, non-authorizing reason; never echo child stdout/stderr or Config."""
    rc = str(finished.returncode) if finished.returncode in (0, 69, 70) else "other"
    if "pkg-update-finish-failed=boot" in (finished.stderr or ""):
        stage = "boot"
    else:
        stage = "unknown"
    guard = re.search(
        r"(?m)^shared-apply-guard=(activate|activated-journal|activated-bundle|"
        r"activated-probe|config-save|epoch-journal|saved-readback|"
        r"saved-probe|ipfw-commit|committed-probe|epoch-schema|"
        r"epoch-dispatch|epoch-attest|epoch-receipt)$",
        finished.stderr or "")
    return f"rc:{rc},stage:{stage},guard:{guard.group(1) if guard else 'unknown'}"


def replace(path: Path) -> None:
    stage, digest, version = stage_archive(path)
    prepared = False
    try:
        prior = installed_version()
        need(prior, "INSTALLED_PRODUCT_MISSING")
        result = native_command([str(SERVICE), "pkg-update-prepare",
                                 str(stage), digest, version], timeout=90)
        need(result.returncode == 0 and
             "zapret-pkg-update-prepared=1" in result.stdout,
             "NATIVE_PREPARE_REFUSED")
        prepared = True
        package = native_command(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                                  "add", "-f", str(stage)], timeout=240)
        combined = package.stdout + "\n" + package.stderr
        need(package.returncode == 0 and
             not any(marker in combined for marker in FAILURE_MARKERS) and
             "zapret-pkg-postinstall-guarded=1" in combined,
             "PACKAGE_OPERATION_NOT_CONFIRMED")
        need(installed_version() == version, "WRONG_INSTALLED_SUCCESSOR")
        finished = native_command([str(SERVICE), "pkg-update-finish",
                                   digest, version], timeout=120)
        if not (finished.returncode == 0 and
                "zapret-pkg-update-committed=1" in finished.stdout):
            # The protected record is retained. Do not leak native stderr,
            # stage paths, hostlists, or Config to the caller/log.
            print("pkg-update-restore-evidence=" + restore_finish_evidence(finished),
                  file=sys.stderr)
            raise Refused("RUNTIME_RESTORE_REQUIRES_REVIEW")
        need(not ACTIVE.exists() and not ACTIVE.is_symlink(),
             "UPDATE_RECORD_NOT_CLOSED")
        stage.unlink()
        durable_directory()
        print("pkg-update=verified-installed-and-restored")
    except Refused:
        # Once prepared, NEVER delete the record or restart an unknown runtime.
        # The original FD9 owner must review/resume a partially replaced pkg.
        if not prepared and not ACTIVE.exists() and not ACTIVE.is_symlink():
            stage.unlink(missing_ok=True)
        raise


def main(argv: list[str]) -> int:
    try:
        need(len(argv) >= 2, "MODE_REQUIRED")
        if argv[1] == "replace":
            need(len(argv) == 3, "PACKAGE_ARGUMENT_REQUIRED")
            replace(Path(argv[2]))
        elif argv[1] == "record":
            need(len(argv) == 6, "RECORD_ARGUMENTS_REQUIRED")
            record(argv[2], argv[3], argv[4], argv[5])
        elif argv[1] == "postinstall-attest":
            need(len(argv) == 2, "POSTINSTALL_ARGUMENTS_REFUSED")
            postinstall_attest()
        elif argv[1] in ("verify", "previous", "complete"):
            need(len(argv) == 4, "RECORD_ID_REQUIRED")
            if argv[1] == "complete":
                complete(argv[2], argv[3])
            else:
                data = inspect(argv[2], argv[3])
                if argv[1] == "previous":
                    print("running" if data["was_running"] else "stopped")
                else:
                    print("pkg-update-successor-verified=1")
        else:
            raise Refused("UNSUPPORTED_MODE")
    except (Refused, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        reason = str(exc) if isinstance(exc, Refused) else "NATIVE_STATE_UNAVAILABLE"
        print("pkg-update-refused=" + reason, file=sys.stderr)
        return 69
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
