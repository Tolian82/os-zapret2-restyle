#!/usr/bin/env python3
"""#1052 P2k8p: single original P2a -> PHP Config-held P1 -> v2 ACK.

The same ORIGINAL queue open-file description survives PHP/Python inheritance.
The original native Config::lock owns the only Model snapshot and root P1.
Legacy one-intent Config/ACK functions are REMOVED, not left dormant.
No active FD9 observer, configd worker, cron or old-generation replay.
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
from auto_detect_storage import ROOT as QUEUE_ROOT
from auto_detect_destination_commit import DestinationCommit
from auto_detect_fd import probe_pending_fd
from auto_detect_owner import GenerationProof, attest_running_generation
from auto_detect_epoch_receipts import EpochReceipts
from auto_detect_gui_hostlist import AUTO_HOSTLIST, AUTO_LOCK
from auto_detect_owned_sources import OWNED_ROOT
from auto_detect_cursor_chain import CursorChain, CursorChainRefused
from auto_detect_original_v2_prepare import (prepare_original_v2_locked,
                                             OriginalV2PrepareRefused)
from auto_detect_original_v2_model import (commit_with_original_v2_model,
                                           V2OriginalConfigRefused)
from auto_detect_original_v2_source import qualified_current_source

PENDING_NAME = re.compile(r'[0-9a-f]{32}-[0-9a-f]{32}\.txt\Z')

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


def _original_v2_cycle_locked(queue: DurableInbox, writer: DestinationCommit, *,
                              php_bin: str, php_script: Path, timeout: int,
                              attest=attest_running_generation,
                              inspect=probe_pending_fd) -> bool:
    """One P2a open-file description: prepare -> original PHP child -> v2 ACK.

    P2c/P2b attesters may be injected only by source test callers.
    Production uses the original fixed P2c/P2b and source paths.
    """
    if (not isinstance(writer, DestinationCommit) or
            writer.queue is not queue or writer.receipts.uid != queue.uid or
            writer.receipts.writer_gid != queue.writer_gid or
            not isinstance(queue, DurableInbox) or not queue._held or
            not callable(attest) or not callable(inspect)):
        raise OriginalLockRefused("original_v2_queue_config_owner_required")
    try:
        proof = qualified_current_source(attest(), queue)
        pending = prepare_original_v2_locked(
            queue, writer.receipts, attest=attest, inspect=inspect)
        if pending is None:
            return False
        tip = CursorChain(writer.receipts, queue).tip(proof)
        if (tip.open_intent is None or
                tip.open_intent["pending_name"] != pending.name or
                attest() != proof):
            raise OriginalLockRefused("original_v2_intent_or_owner_changed")
        result = _original_completion_locked(
            queue, pending, php_bin=php_bin,
            php_script=php_script, timeout=timeout)
        if attest() != proof:
            raise OriginalLockRefused("original_owner_changed_after_config_child")
        return CursorChain(writer.receipts, queue).acknowledge(
            proof, pending, result, writer, attest=attest, inspect=inspect)
    except (CursorChainRefused, OriginalV2PrepareRefused, OSError, ValueError,
            TypeError, KeyError) as exc:
        raise OriginalLockRefused("original_v2_transaction_or_ack_unavailable") from exc


def run_native_original_v2_cycle_once() -> bool:
    """Fixed native one-shot composer; NOT registered with configd/cron."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise OriginalLockRefused("original_native_fd9_required")
    import pwd
    from auto_detect_storage import ENGINE_USER
    try:
        gid = pwd.getpwnam(ENGINE_USER).pw_gid
        if gid <= 0:
            raise OriginalLockRefused("original_writer_gid_not_qualified")
        queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        writer = DestinationCommit(
            receipts, queue,
            {"auto": AUTO_HOSTLIST,
             "youtube": OWNED_ROOT / "youtube.txt",
             "user": OWNED_ROOT / "user.txt"}, AUTO_LOCK)
        with queue.exclusive():
            return _original_v2_cycle_locked(
                queue, writer, php_bin="/usr/local/bin/php",
                php_script=PHP_CONFIG, timeout=25)
    except (KeyError, OSError, QueueSafetyError) as exc:
        raise OriginalLockRefused("original_native_v2_source_unavailable") from exc


def _native_fd_child(pending_name: str, payload: dict) -> dict:
    """Original PHP Config child with BOTH verified inherited lock descriptors."""
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not PENDING_NAME.fullmatch(pending_name) or
            not isinstance(payload, dict) or
            set(payload) != {"manual_hostlists", "global_exclude",
                             "config_snapshot_sha256"} or
            not re.fullmatch("[0-9a-f]{64}",
                             str(payload["config_snapshot_sha256"]))):
        raise OriginalLockRefused("original_native_fd9_and_model_required")
    import pwd
    from auto_detect_storage import ENGINE_USER
    gid = pwd.getpwnam(ENGINE_USER).pw_gid
    if gid <= 0:
        raise OriginalLockRefused("unqualified_original_writer_gid")
    queue = DurableInbox(QUEUE_ROOT, owner_uid=0, writer_gid=gid)
    pending = queue.pending / pending_name
    with inherited_original_locks(queue, 3, 4, CONFIG_PATH, owner_uid=0):
        if pending not in queue.segments():
            raise OriginalLockRefused("original_pending_not_in_queue")
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        writer = DestinationCommit(
            receipts, queue,
            {"auto": AUTO_HOSTLIST,
             "youtube": OWNED_ROOT / "youtube.txt",
             "user": OWNED_ROOT / "user.txt"}, AUTO_LOCK)
        completion = commit_with_original_v2_model(
            writer, pending, owned_root=OWNED_ROOT,
            manual_hostlists=payload["manual_hostlists"],
            global_exclude=payload["global_exclude"])
        if completion.get("ack_authorized") is not False:
            raise OriginalLockRefused("original_v2_checkpoint_not_authorization")
        return completion


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if (len(argv) != 2 or argv[0] != "commit-fds" or
            not sys.platform.startswith("freebsd") or os.geteuid() != 0):
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
                raise OriginalLockRefused("oversized_original_model")
            chunks.append(piece)
        response = _native_fd_child(argv[1], json.loads(b"".join(chunks)))
        print(json.dumps(response, sort_keys=True, separators=(",", ":")))
        return 0
    except (OriginalLockRefused, V2OriginalConfigRefused,
            CursorChainRefused, OriginalV2PrepareRefused,
            QueueSafetyError, ValueError, OSError, TypeError, KeyError,
            RuntimeError):
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
