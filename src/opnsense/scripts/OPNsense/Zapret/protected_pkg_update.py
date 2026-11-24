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


def native_command(args: list[str], timeout: int = 90, *,
                   env: dict[str, str] | None = None,
                   binary: bool = False) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, text=not binary, capture_output=True,
                              check=False, timeout=timeout, env=env)
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


def stage_archive(path: Path, *, continuation: bool = False) -> tuple[Path, str, str]:
    root_and_private_base()
    if not continuation:
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
    # Trust only one exact, original stage marker on a refused finish.
    # Do not classify text embedded in foreign child stderr or an rc0/69.
    markers = (re.findall(
        r"(?m)^pkg-update-finish-failed=(boot|start|verify)$",
        finished.stderr or "") if finished.returncode == 70 else [])
    stage = markers[0] if len(markers) == 1 else "unknown"
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


def continuation_predecessor(data: dict) -> tuple[dict, str]:
    """Retain the exact failed POST_INSTALL record inside the SAME journal."""
    link = data.get("continuation")
    need(isinstance(link, dict) and set(link) == {"record", "sha256"} and
         isinstance(link["record"], str), "CONTINUATION_PROOF_MISSING")
    raw = link["record"].encode("utf-8")
    need(0 < len(raw) <= 4096 and
         hashlib.sha256(raw).hexdigest() == link["sha256"],
         "CONTINUATION_PREDECESSOR_CHANGED")
    prior = json.loads(raw)
    need(isinstance(prior, dict) and prior.get("schema") == 1 and
         prior.get("phase") == "postinstall-attested" and
         type(prior.get("was_running")) is bool and
         "continuation" not in prior and
         data.get("from_version") == prior.get("to_version") and
         data.get("was_running") is prior["was_running"],
         "CONTINUATION_PREDECESSOR_INVALID")
    validated_stage(prior["stage"], prior["sha256"], prior["to_version"])
    return prior, link["sha256"]


def continue_record(raw: str, digest: str, version: str,
                    expected_record: str) -> None:
    """Original FD9 only; shell has independently proved committed STOPPED.

    No runtime/Config writes, no source graft and no unlink of the old record.
    Atomic replacement publishes either the intact old operation or the new
    prepared operation containing its exact bytes and archive identity.
    """
    fd9_is_original_owner()
    root_and_private_base()
    need(re.fullmatch(r"[a-f0-9]{64}", expected_record) is not None,
         "RECORD_SHA_REQUIRED")
    data = read_active()
    current_raw = ACTIVE.read_bytes()
    need(hashlib.sha256(current_raw).hexdigest() == expected_record and
         json.loads(current_raw) == data, "ACTIVE_OPERATION_CHANGED")
    validated_stage(raw, digest, version)
    if "continuation" in data:
        prior, _ = continuation_predecessor(data)
        need(data["stage"] == raw and data["sha256"] == digest and
             data["to_version"] == version, "CONTINUATION_TARGET_CHANGED")
        current = installed_version()
        need(current in (prior["to_version"], version),
             "CONTINUATION_INSTALLED_IDENTITY_CHANGED")
        if data["phase"] == "postinstall-attested":
            need(current == version, "SUCCESSOR_NOT_INSTALLED")
            print("zapret-pkg-update-continue=finish")
        else:
            print("zapret-pkg-update-continue=prepared")
        return
    need(data["phase"] == "postinstall-attested" and
         type(data.get("was_running")) is bool and
         installed_version() == data.get("to_version"),
         "POSTINSTALL_CONTINUATION_REQUIRED")
    validated_stage(data["stage"], data["sha256"], data["to_version"])
    ordering = native_command(["/usr/sbin/pkg", "version", "-t", version,
                               data["to_version"]])
    need(ordering.returncode == 0 and ordering.stdout.strip() == ">",
         "CONTINUATION_REQUIRES_NEWER_PACKAGE")
    updated = {"schema": 1, "phase": "prepared", "stage": raw,
               "sha256": digest, "to_version": version,
               "from_version": data["to_version"],
               "was_running": data["was_running"],
               "continuation": {"record": current_raw.decode("utf-8"),
                                "sha256": expected_record}}
    body = (json.dumps(updated, sort_keys=True, separators=(",", ":")) + "\n").encode()
    need(len(body) <= 4096, "CONTINUATION_RECORD_TOO_LARGE")
    fd, tmp = tempfile.mkstemp(prefix=".continue-", dir=BASE)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(body)
            output.flush()
            os.fsync(output.fileno())
        # Compare again immediately before the one journal publication.
        need(ACTIVE.read_bytes() == current_raw, "ACTIVE_OPERATION_CHANGED")
        os.replace(tmp, ACTIVE)
        durable_directory()
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)
    print("zapret-pkg-update-continue=prepared")


def continue_postinstall(path: Path, original_record_sha: str) -> None:
    """Explicit recovery of one failed restore, using ordinary native pkg.

    May run from a verified package staging tree; installed sources remain
    untouched until pkg replaces its whole payload. Original archive flock
    serializes recovery coordinators; FD9 remains owned only by the service.
    """
    root_and_private_base()
    data = read_active()
    prior = data
    if "continuation" in data:
        prior, previous_sha = continuation_predecessor(data)
        need(previous_sha == original_record_sha, "ORIGINAL_RECORD_SHA_MISMATCH")
    else:
        need(data["phase"] == "postinstall-attested" and
             hash_file(ACTIVE) == original_record_sha,
             "POSTINSTALL_CONTINUATION_REQUIRED")
    old_archive = validated_stage(prior["stage"], prior["sha256"], prior["to_version"])
    # Lock the retained ORIGINAL archive, not a second lifecycle/Config lock.
    fd = os.open(old_archive, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refused("CONTINUATION_ALREADY_RUNNING") from exc
        identity = os.fstat(fd)
        named = old_archive.lstat()
        need((identity.st_dev, identity.st_ino) == (named.st_dev, named.st_ino)
             and read_active() == data, "ACTIVE_OPERATION_CHANGED")
        need(path.is_absolute(), "ABSOLUTE_PACKAGE_PATH_REQUIRED")
        inspect_regular(path, private=False)
        if "continuation" in data:
            stage = validated_stage(data["stage"], data["sha256"], data["to_version"])
            digest, version = data["sha256"], data["to_version"]
            need(hash_file(path) == digest and manifest_identity(path) == version,
                 "CONTINUATION_TARGET_CHANGED")
        else:
            stage, digest, version = stage_archive(path, continuation=True)
        expected = hash_file(ACTIVE)
        clean_env = {"PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin",
                     "LC_ALL": "C"}
        staged_env = {**clean_env, "SCRIPT_DIR": str(SCRIPT_DIR),
                      "BACKEND_DIR": str(SCRIPT_DIR / "backend"),
                      "PYTHON_RUNTIME": str(SCRIPT_DIR / "python_runtime.sh"),
                      "ZAPRET_INSTALLED_SUPERVISOR_LOOP":
                      "/usr/local/opnsense/scripts/OPNsense/Zapret/supervisor_loop.sh"}
        prepared = native_command([str(SERVICE), "pkg-update-continue-prepare",
                                   str(stage), digest, version, expected],
                                  timeout=90, env=staged_env)
        need(prepared.returncode == 0, "NATIVE_CONTINUATION_REFUSED")
        if "zapret-pkg-update-continue=prepared" in prepared.stdout:
            package = native_command(["/usr/sbin/pkg", "-o", "REPO_AUTOUPDATE=false",
                                      "add", "-f", str(stage)], timeout=240,
                                     env=clean_env)
            combined = package.stdout + "\n" + package.stderr
            need(package.returncode == 0 and
                 not any(marker in combined for marker in FAILURE_MARKERS) and
                 "zapret-pkg-postinstall-guarded=1" in combined,
                 "PACKAGE_OPERATION_NOT_CONFIRMED")
        else:
            need("zapret-pkg-update-continue=finish" in prepared.stdout,
                 "NATIVE_CONTINUATION_RECEIPT_MISSING")
        need(installed_version() == version, "WRONG_INSTALLED_SUCCESSOR")
        installed_service = "/usr/local/opnsense/scripts/OPNsense/Zapret/zapret_service.sh"
        finished = native_command([installed_service, "pkg-update-finish", digest,
                                   version], timeout=120, env=clean_env)
        need(finished.returncode == 0 and
             "zapret-pkg-update-committed=1" in finished.stdout and
             not ACTIVE.exists() and not ACTIVE.is_symlink(),
             "RUNTIME_RESTORE_REQUIRES_REVIEW")
        stage.unlink()
        durable_directory()
        print("pkg-update=verified-continued-and-restored")
    finally:
        os.close(fd)


def stage_recovery_code(package: Path, expected_sha: str) -> Path:
    """Read a verified package's existing service into private staging.

    Archive names never select filesystem destinations. There is no external
    installer asset, installed-source patch, Config writer or hook override.
    The bootstrap itself must be the exact coordinator from this same .pkg.
    """
    root_and_private_base()
    need(package.is_absolute() and
         re.fullmatch(r"[a-f0-9]{64}", expected_sha) is not None,
         "RECOVERY_PACKAGE_SHA_REQUIRED")
    inspect_regular(package, private=False)
    need(hash_file(package) == expected_sha, "RECOVERY_PACKAGE_CHANGED")
    manifest_identity(package)
    manifest = json.loads(native_command(
        ["/usr/bin/tar", "-xOf", str(package), "+MANIFEST"]).stdout)
    index = native_command(["/usr/bin/tar", "-tf", str(package)])
    need(index.returncode == 0 and len(index.stdout) <= 4 * 1024 * 1024 and
         isinstance(manifest.get("files"), dict), "RECOVERY_PACKAGE_INDEX_REFUSED")
    prefixes = ("usr/local/opnsense/scripts/OPNsense/Zapret/",
                "usr/local/opnsense/mvc/app/controllers/OPNsense/Zapret/Api/")
    selected = {}
    for member in index.stdout.splitlines():
        key = member.removeprefix("./").removeprefix("/")
        if not key.startswith(prefixes) or key.endswith("/"):
            continue
        need(re.fullmatch(r"[A-Za-z0-9_./-]+", key) is not None and
             all(part not in ("", ".", "..") for part in key.split("/")) and
             key not in selected and "/" + key in manifest["files"],
             "RECOVERY_PACKAGE_MEMBER_REFUSED")
        selected[key] = member
    coordinator = prefixes[0] + "protected_pkg_update.py"
    need(coordinator in selected and prefixes[0] + "zapret_service.sh" in selected,
         "RECOVERY_SERVICE_MISSING")
    me = Path(__file__)
    inspect_regular(me, private=False)
    own = native_command(["/usr/bin/tar", "-xOf", str(package), selected[coordinator]],
                         binary=True)
    need(own.returncode == 0 and own.stdout == me.read_bytes(),
         "RECOVERY_COORDINATOR_SOURCE_MISMATCH")
    root = Path(tempfile.mkdtemp(prefix="code-", dir=BASE))
    total = 0
    for key, member in sorted(selected.items()):
        item = native_command(["/usr/bin/tar", "-xOf", str(package), member],
                              binary=True)
        body = item.stdout
        total += len(body)
        need(item.returncode == 0 and len(body) <= 4 * 1024 * 1024 and
             total <= 32 * 1024 * 1024, "RECOVERY_CODE_SIZE_REFUSED")
        target = root / key
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o755 if key.endswith(".sh") else 0o644)
        with os.fdopen(fd, "wb") as output:
            output.write(body)
            output.flush()
            os.fsync(output.fileno())
    need(hash_file(package) == expected_sha, "RECOVERY_PACKAGE_CHANGED")
    # Persist the complete uninstalled tree BEFORE allowing its FD9 entry.
    for directory in sorted((p for p in root.rglob("*") if p.is_dir()),
                            key=lambda p: len(p.parts), reverse=True):
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    durable_directory()
    return root / prefixes[0]


def bootstrap_continuation(package: Path, digest: str, target: Path,
                           original_record_sha: str) -> None:
    stage = stage_recovery_code(package, digest)
    environment = {"PATH": "/sbin:/bin:/usr/sbin:/usr/bin:/usr/local/sbin:/usr/local/bin",
                   "LC_ALL": "C", "SCRIPT_DIR": str(stage),
                   "BACKEND_DIR": str(stage / "backend"),
                   "PYTHON_RUNTIME": str(stage / "python_runtime.sh")}
    completed = native_command([str(stage / "zapret_service.sh"),
                               "pkg-update-continue", str(target),
                               original_record_sha], timeout=480, env=environment)
    need(completed.returncode == 0 and
         "pkg-update=verified-continued-and-restored" in completed.stdout,
         "STAGED_CONTINUATION_REQUIRES_REVIEW")
    print("pkg-recovery=verified-installed-and-restored")


def main(argv: list[str]) -> int:
    try:
        need(len(argv) >= 2, "MODE_REQUIRED")
        if argv[1] == "replace":
            need(len(argv) == 3, "PACKAGE_ARGUMENT_REQUIRED")
            replace(Path(argv[2]))
        elif argv[1] == "continue-postinstall":
            need(len(argv) == 4, "CONTINUATION_ARGUMENTS_REQUIRED")
            continue_postinstall(Path(argv[2]), argv[3])
        elif argv[1] == "continue-record":
            need(len(argv) == 6, "CONTINUATION_RECORD_ARGUMENTS_REQUIRED")
            continue_record(argv[2], argv[3], argv[4], argv[5])
        elif argv[1] == "bootstrap-continuation":
            need(len(argv) == 6, "RECOVERY_BOOTSTRAP_ARGUMENTS_REQUIRED")
            bootstrap_continuation(Path(argv[2]), argv[3], Path(argv[4]), argv[5])
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
