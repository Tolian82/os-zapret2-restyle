#!/usr/bin/env python3
"""#1052 P2k8l: original queue -> PHP Config -> durable checkpoint -> ACK.

This module remains an import-only, unscheduled native worker seam. The
same ORIGINAL queue open-file description stays held across the PHP Config
child and P2k8k post-commit evidence before the P2a unlink. No active FD9
observer, cron/configd invocation or old-generation replay is enabled.
"""
from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

from auto_detect_queue import DurableInbox, QueueSafetyError
from auto_detect_destination_commit import DestinationCommit
from auto_detect_fd import probe_pending_fd
from auto_detect_owner import GenerationProof, attest_running_generation
from auto_detect_post_commit_ack import acknowledge_current_checkpoint
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_gui_hostlist import AUTO_HOSTLIST, AUTO_LOCK
from auto_detect_owned_sources import OWNED_ROOT
from auto_detect_verified_owned_commit import commit_with_locked_original_model

PENDING_NAME = re.compile(r'[0-9a-f]{32}-[0-9a-f]{32}\.txt\Z')
QUEUE_ROOT = Path('/var/db/zapret2-auto-detect')
PHP_CONFIG = Path('/usr/local/opnsense/scripts/OPNsense/Zapret/auto_detect_config_snapshot.php')
CONFIG_PATH = Path('/conf/config.xml')


class OriginalLockRefused(RuntimeError):
    """Refuse the batch without deleting pending or exposing domain content."""


def assert_inherited_config_fd(fd: int, path: Path, *, owner_uid: int | None = 0) -> None:
    """Prove same original locked Config inode/open description, not a token."""
    if (type(fd) is not int or fd < 3 or not Path(path).is_absolute() or
            (owner_uid is None and Path(path) != CONFIG_PATH)):
        # The original OPNsense Config is allowed a *non-root* native
        # uid only at its one hard-coded Config path, never any test path
        # or worker directory. OPNsense itself supplied the descriptor.
        raise OriginalLockRefused('invalid_original_config_fd')
    try:
        path = Path(path)
        named = path.lstat()
        held = os.fstat(fd)
        parent = path.parent.lstat()
        # OPNsense 26.7 native Config and /conf are *not* necessarily owned
        # by UID 0 (actual guest ownership can be UID 789, root group).
        # Distinguish its original Config-file owner from the separately
        # root-only queue. Never hard-code an appliance-specific UID.
        if owner_uid is None:
            valid_owner = (named.st_uid == held.st_uid == parent.st_uid and
                           named.st_gid == held.st_gid == parent.st_gid == 0)
        else:
            valid_owner = (named.st_uid == held.st_uid == parent.st_uid
                           == owner_uid)
        if (not stat.S_ISDIR(parent.st_mode) or
                parent.st_mode & 0o022 or
                not stat.S_ISREG(named.st_mode) or
                not stat.S_ISREG(held.st_mode) or
                not valid_owner or
                named.st_nlink != 1 or held.st_nlink != 1 or
                named.st_mode & 0o022 or
                (held.st_dev, held.st_ino) != (named.st_dev, named.st_ino) or
                stat.S_IMODE(held.st_mode) != stat.S_IMODE(named.st_mode)):
            raise OriginalLockRefused('unsafe_original_config_inode')
        separate = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            try:
                fcntl.flock(separate, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                pass
            else:
                fcntl.flock(separate, fcntl.LOCK_UN)
                raise OriginalLockRefused('original_config_unlocked')
        finally:
            os.close(separate)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise OriginalLockRefused('foreign_config_open_description') from None
    except OSError as exc:
        raise OriginalLockRefused('original_config_lock_unavailable') from exc


@contextmanager
def inherited_original_locks(queue: DurableInbox, queue_fd: int, config_fd: int,
                             config_path: Path, *, owner_uid: int = 0):
    """Adopt existing original locks in queue -> Config -> GUI order."""
    with queue.inherited_exclusive(queue_fd):
        # Queue/inbox/pending remain strictly ROOT-owned. Only the fixed
        # original OPNsense Config path may use its native Config account:
        # its file, descriptor and parent must share a UID and root GID.
        config_owner = None if Path(config_path) == CONFIG_PATH else owner_uid
        assert_inherited_config_fd(config_fd, config_path, owner_uid=config_owner)
        yield
        assert_inherited_config_fd(config_fd, config_path, owner_uid=config_owner)


def _original_completion_locked(queue: DurableInbox, pending: Path, *,
                                php_bin: str, php_script: Path,
                                timeout: int) -> dict:
    """One genuine PHP Config-held completion while ORIGINAL queue FD is held.

    The caller owns queue.exclusive(); this function MUST NOT take a second
    flock or return an ACK permission. The existing PHP and child still verify
    both original inherited queue and Config open-file descriptions.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(pending, Path) or pending.parent != queue.pending or
            not PENDING_NAME.fullmatch(pending.name) or
            type(timeout) is not int or not 1 <= timeout <= 120 or
            not isinstance(php_bin, str) or not php_bin or
            not isinstance(php_script, Path) or not php_script.is_absolute()):
        raise OriginalLockRefused('invalid_original_pending_cycle')
    if pending not in queue.segments():
        raise OriginalLockRefused('original_pending_missing')
    original_fd = queue.locked_fd
    try:
        result = subprocess.run(
            [php_bin, str(php_script), 'commit-with-fds',
             str(original_fd), pending.name],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, pass_fds=(original_fd,),
            timeout=timeout, check=False, close_fds=True)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OriginalLockRefused('original_config_owner_unavailable') from exc
    if result.returncode != 0 or not result.stdout or len(result.stdout) > 16384:
        raise OriginalLockRefused('original_config_child_refused')
    try:
        response = json.loads(result.stdout)
    except (UnicodeError, ValueError) as exc:
        raise OriginalLockRefused('invalid_original_owner_result') from exc
    if (not isinstance(response, dict) or
            response.get('kind') != 'destination-and-cursor-committed' or
            response.get('ack_authorized') is not False):
        raise OriginalLockRefused('unqualified_original_owner_result')
    return response  # returned child receipt, NOT ACK permission


def run_original_pending_cycle(queue: DurableInbox, pending: Path, *,
                               php_bin: str = '/usr/local/bin/php',
                               php_script: Path = PHP_CONFIG,
                               timeout: int = 120) -> dict:
    """Keep the previously qualified original queue/Config-only path inert."""
    if (not isinstance(queue, DurableInbox) or queue._held or
            not isinstance(pending, Path) or pending.parent != queue.pending):
        raise OriginalLockRefused('invalid_original_pending_cycle')
    with queue.exclusive():
        return _original_completion_locked(
            queue, pending, php_bin=php_bin, php_script=php_script,
            timeout=timeout)


def _original_commit_then_ack_locked(queue: DurableInbox, pending: Path,
                                     writer: DestinationCommit, *,
                                     php_bin: str, php_script: Path,
                                     timeout: int,
                                     attest=attest_running_generation,
                                     inspect=probe_pending_fd) -> bool:
    """Join real original PHP child + P2k8k ACK without releasing queue FD.

    Test injections of current P2c/FD evidence and a disposable PHP fixture
    are only possible through this private, import-only helper. Production
    entry below fixes original runtime paths and native attesters.
    """
    if (not isinstance(writer, DestinationCommit) or writer.queue is not queue or
            not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(pending, Path) or pending.parent != queue.pending or
            not PENDING_NAME.fullmatch(pending.name) or
            not callable(attest) or not callable(inspect)):
        raise OriginalLockRefused('original_locked_queue_and_writer_required')
    proof = attest()
    if (not isinstance(proof, GenerationProof) or
            proof.generation != proof.operation_id or
            proof.generation != pending.name[:32] or
            proof.raw_path != str(queue.inbox) or
            proof.debug_path != str(queue.root / 'debug.log') or
            (proof.observer_native_number, 'observer', None) not in proof.profiles):
        raise OriginalLockRefused('current_original_generation_required')
    # No unlocking/re-locking the queue between original PHP completion and
    # the protected P2k8k inode/hash, checkpoint and current FD verification.
    completion = _original_completion_locked(
        queue, pending, php_bin=php_bin, php_script=php_script,
        timeout=timeout)
    if attest() != proof:
        raise OriginalLockRefused('original_owner_changed_after_config_child')
    return acknowledge_current_checkpoint(
        writer, pending, completion, attest=attest, inspect=inspect)


def run_native_original_pending_ack_once(pending_name: str) -> bool:
    """DORMANT native one-segment path; NOT a registered CLI/configd action.

    Native ownership, original trusted paths, fixed short subprocess timeout
    and live P2c/P2b proofs cannot be overridden by CLI/env/input parameters.
    No directory or native observer is created here.
    """
    if (not sys.platform.startswith('freebsd') or os.geteuid() != 0 or
            type(pending_name) is not str or
            not PENDING_NAME.fullmatch(pending_name)):
        raise OriginalLockRefused('original_native_generation_required')
    import pwd
    from auto_detect_storage import ENGINE_USER
    writer_gid = pwd.getpwnam(ENGINE_USER).pw_gid
    if writer_gid <= 0:
        raise OriginalLockRefused('unqualified_original_engine_gid')
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=writer_gid)
    pending = queue.pending / pending_name
    writer = DestinationCommit(
        EpochReceipts(owner_uid=0), queue,
        {'auto': AUTO_HOSTLIST,
         'youtube': OWNED_ROOT / 'youtube.txt',
         'user': OWNED_ROOT / 'user.txt'}, AUTO_LOCK)
    with queue.exclusive():
        return _original_commit_then_ack_locked(
            queue, pending, writer, php_bin='/usr/local/bin/php',
            php_script=PHP_CONFIG, timeout=25)


def _native_fd_child(pending_name: str, payload: dict) -> dict:
    """CLI child of original PHP Config owner; no synthetic owner injection."""
    if (not sys.platform.startswith('freebsd') or os.geteuid() != 0 or
            not PENDING_NAME.fullmatch(pending_name) or
            not isinstance(payload, dict) or
            set(payload) != {'manual_hostlists','global_exclude','config_snapshot_sha256'} or
            not re.fullmatch('[0-9a-f]{64}', str(payload['config_snapshot_sha256']))):
        raise OriginalLockRefused('original_native_fd9_and_model_required')
    # Use the original P2g producer's ENGINE_USER/GID contract, not an
    # independently guessed same-named group entry.
    import pwd
    from auto_detect_storage import ENGINE_USER
    writer_gid = pwd.getpwnam(ENGINE_USER).pw_gid
    if writer_gid <= 0:
        raise OriginalLockRefused('unqualified_original_engine_gid')
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=writer_gid)
    pending = queue.pending / pending_name
    with inherited_original_locks(queue, 3, 4, CONFIG_PATH, owner_uid=0):
        if pending not in queue.segments():
            raise OriginalLockRefused('original_pending_not_in_queue')
        writer = DestinationCommit(
            EpochReceipts(owner_uid=0), queue,
            {'auto': AUTO_HOSTLIST,
             'youtube': OWNED_ROOT / 'youtube.txt',
             'user': OWNED_ROOT / 'user.txt'}, AUTO_LOCK)
        result = commit_with_locked_original_model(
            writer, pending, owned_root=OWNED_ROOT,
            manual_hostlists=payload['manual_hostlists'],
            global_exclude=payload['global_exclude'])
        if result.get('ack_authorized') is not False:
            raise OriginalLockRefused('ack_remains_unauthorized')
        return result


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if (len(argv) != 2 or argv[0] != 'commit-fds' or
            not sys.platform.startswith('freebsd') or os.geteuid() != 0):
        return 64
    try:
        chunks = []
        total = 0
        while True:
            piece = os.read(0, min(65536, (3 << 20) + 1 - total))
            if not piece:
                break
            total += len(piece)
            if total > (3 << 20):
                raise OriginalLockRefused('oversized_original_model')
            chunks.append(piece)
        result = _native_fd_child(argv[1], json.loads(b''.join(chunks)))
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except (OriginalLockRefused, QueueSafetyError, ValueError,
            OSError, TypeError, KeyError, RuntimeError):
        return 69


if __name__ == '__main__':
    raise SystemExit(main())
