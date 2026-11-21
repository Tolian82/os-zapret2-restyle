#!/usr/bin/env python3
"""#1052 P2k8p: single original P2a -> PHP Config-held P1 -> v2 ACK.

The same ORIGINAL queue open-file description survives PHP/Python inheritance.
The original native Config::lock owns the only Model snapshot and root P1.
Legacy one-intent Config/ACK functions are REMOVED, not left dormant.
No second worker/Config writer, second lifecycle lock or old-generation replay.
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
from auto_detect_destination_commit import DestinationCommit, DestinationRefused
from auto_detect_fd import (probe_pending_fd, probe_stopped_pending_fd,
                            probe_stopped_learning_pending_fd)
from auto_detect_owner import (GenerationProof, attest_running_generation,
                               attest_stopped_generation)
from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused
from auto_detect_gui_hostlist import AUTO_HOSTLIST, AUTO_LOCK
from auto_detect_owned_sources import OWNED_ROOT
from auto_detect_cursor_chain import CursorChain, CursorChainRefused, _checkpoint
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
                                timeout: int, retired: bool = False,
                                learning: bool = False,
                                stopped_learning: bool = False) -> dict:
    """One genuine PHP Config-held completion while ORIGINAL queue FD is held.

    The caller owns queue.exclusive(); this function MUST NOT take a second
    flock or return an ACK permission. The existing PHP and child still verify
    both original inherited queue and Config open-file descriptions.
    """
    if (not isinstance(queue, DurableInbox) or not queue._held or
            not isinstance(pending, Path) or pending.parent != queue.pending or
            not (re.fullmatch(r"[0-9a-f]{32}", pending.name) if learning
                 else PENDING_NAME.fullmatch(pending.name)) or
            (learning and retired) or
            (stopped_learning and (retired or not learning)) or
            type(timeout) is not int or not 1 <= timeout <= 120 or
            not isinstance(php_bin, str) or not php_bin or
            not isinstance(php_script, Path) or not php_script.is_absolute()):
        raise OriginalLockRefused('invalid_original_pending_cycle')
    if not learning and pending not in queue.segments():
        raise OriginalLockRefused('original_pending_missing')
    original_fd = queue.locked_fd
    if retired or learning:
        from voice_ipfw_adapter import require_lifecycle_lock
        require_lifecycle_lock()
    try:
        result = subprocess.run(
            [php_bin, str(php_script),
             'commit-stopped-learning-with-fds' if stopped_learning else
             'commit-learning-with-fds' if learning else
             'commit-retired-with-fds' if retired else 'commit-with-fds',
             str(original_fd), pending.name],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            pass_fds=(original_fd, 9) if retired or learning else (original_fd,),
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
            response.get('kind') != ('original-learning-minute-completed' if learning
                                     else 'destination-and-cursor-committed') or
            (learning and (type(response.get('processed')) is not bool or
                           response.get('generation') != pending.name)) or
            response.get('ack_authorized') is not False):
        raise OriginalLockRefused('unqualified_original_owner_result')
    return response  # returned child receipt, NOT ACK permission


def _original_v2_cycle_locked(queue: DurableInbox, writer: DestinationCommit, *,
                              php_bin: str, php_script: Path, timeout: int,
                              attest=attest_running_generation,
                              inspect=probe_pending_fd,
                              retired: bool = False) -> bool:
    """One P2a open-file description: prepare -> PHP child -> v2 ACK.

    After physical unlink with a completed checkpoint, recover ONLY the ACK;
    original PHP/Config must not run again for that same immutable intent.
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
        chain = CursorChain(writer.receipts, queue)
        # Crash window: the original P2a unlink succeeded but the cursor
        # ACK receipt was not fsynced. The immutable Config/P1 checkpoint
        # is already complete; do NOT replay PHP/Config or a later raw batch.
        # Recover only that original ACK with the same live P2c/FD9 owner.
        if not queue.segments():
            chain.ensure_capacity(proof, attest=attest)
            prior = chain.tip(proof)
            if prior.open_intent is not None:
                if prior.open_folder is None:
                    raise OriginalLockRefused("missing_original_open_cursor_folder")
                absent = queue.pending / prior.open_intent["pending_name"]
                if absent.exists() or absent.is_symlink():
                    raise OriginalLockRefused("missing_pending_identity_not_proven")
                verified = _checkpoint(
                    prior.open_folder, prior.open_intent,
                    writer.receipts.uid, targets=writer.targets)
                if verified is None or attest() != proof:
                    raise OriginalLockRefused("missing_pending_without_original_checkpoint")
                if not chain.acknowledge(
                    proof, absent, verified[0], writer,
                    attest=attest, inspect=inspect):
                    raise OriginalLockRefused("original_post_unlink_ack_not_durable")
                return True
        pending = prepare_original_v2_locked(
            queue, writer.receipts, attest=attest, inspect=inspect,
            inspect_debug=inspect)
        if pending is None:
            return False
        tip = chain.tip(proof)
        if (tip.open_intent is None or
                tip.open_intent["pending_name"] != pending.name or
                attest() != proof):
            raise OriginalLockRefused("original_v2_intent_or_owner_changed")
        result = _original_completion_locked(
            queue, pending, php_bin=php_bin,
            php_script=php_script, timeout=timeout, retired=retired)
        if attest() != proof:
            raise OriginalLockRefused("original_owner_changed_after_config_child")
        if not chain.acknowledge(
            proof, pending, result, writer, attest=attest, inspect=inspect):
            # A completed Config/P1 checkpoint is NOT a completed physical
            # ACK. If old FD/inode changed during the final race, retain
            # pending and report a refusal rather than a false idle minute.
            raise OriginalLockRefused("original_physical_ack_not_durable")
        return True
    except (CursorChainRefused, OriginalV2PrepareRefused, DestinationRefused,
            ReceiptRefused, OSError, ValueError, TypeError, KeyError) as exc:
        raise OriginalLockRefused("original_v2_transaction_or_ack_unavailable") from exc


def run_native_original_v2_cycle_once(*, retired: bool = False,
                                      learning: bool = False,
                                      stopped_learning: bool = False) -> bool:
    """One original FD9 service-owned native minute, with no new worker."""
    if not sys.platform.startswith("freebsd") or os.geteuid() != 0:
        raise OriginalLockRefused("original_native_fd9_required")
    # Defense in depth: do not trust that only the registered configd
    # wrapper can import this function. Require the actual held lock
    # BEFORE opening P2a raw/pending or Config.
    from voice_ipfw_adapter import require_lifecycle_lock
    try:
        require_lifecycle_lock()
    except RuntimeError as exc:
        raise OriginalLockRefused("original_native_fd9_not_held") from exc
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
            if stopped_learning and (not learning or retired):
                raise OriginalLockRefused("stopped_learning_requires_original_mode")
            if learning:
                if retired:
                    raise OriginalLockRefused("learning_minute_cannot_be_retired_raw")
                from auto_detect_owner import (
                    attest_learning_running_generation,
                    attest_learning_stopped_generation,
                )
                proof = (attest_learning_stopped_generation() if stopped_learning
                         else attest_learning_running_generation())
                response = _original_completion_locked(
                    queue, queue.pending / proof.generation,
                    php_bin="/usr/local/bin/php", php_script=PHP_CONFIG,
                    timeout=25, learning=True,
                    stopped_learning=stopped_learning)
                return response["processed"]
            return _original_v2_cycle_locked(
                queue, writer, php_bin="/usr/local/bin/php",
                php_script=PHP_CONFIG, timeout=25,
                attest=attest_stopped_generation if retired else attest_running_generation,
                inspect=probe_stopped_pending_fd if retired else probe_pending_fd,
                retired=retired)
    except (KeyError, OSError, QueueSafetyError) as exc:
        raise OriginalLockRefused("original_native_v2_source_unavailable") from exc



# The 4-MiB per-manual fields, preserved 1-MiB exclusions, JSON metadata and
# escaping need a separate *finite* original PHP->Python FD payload budget.
# This is NOT a configd argv, HTTP POST or mutable system/PHP memory limit.
MAX_ORIGINAL_MODEL_WIRE = 16 << 20


def read_bounded_original_model(reader=os.read) -> bytes:
    chunks = []
    total = 0
    while True:
        piece = reader(0, min(65536, MAX_ORIGINAL_MODEL_WIRE + 1 - total))
        if not piece:
            break
        total += len(piece)
        if total > MAX_ORIGINAL_MODEL_WIRE:
            raise OriginalLockRefused("oversized_original_model")
        chunks.append(piece)
    return b"".join(chunks)


def _native_fd_child(pending_name: str, payload: dict, *,
                     retired: bool = False, learning: bool = False,
                     stopped_learning: bool = False) -> dict:
    """Original PHP Config child with BOTH verified inherited lock descriptors."""
    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not (re.fullmatch(r"[0-9a-f]{32}", pending_name) if learning
                 else PENDING_NAME.fullmatch(pending_name)) or
            (learning and retired) or
            (stopped_learning and (not learning or retired)) or
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
        if not learning and pending not in queue.segments():
            raise OriginalLockRefused("original_pending_not_in_queue")
        receipts = EpochReceipts(owner_uid=0, writer_gid=gid)
        writer = DestinationCommit(
            receipts, queue,
            {"auto": AUTO_HOSTLIST,
             "youtube": OWNED_ROOT / "youtube.txt",
             "user": OWNED_ROOT / "user.txt"}, AUTO_LOCK)
        if learning:
            from auto_detect_owner import (
                attest_learning_running_generation,
                attest_learning_stopped_generation, WORK,
            )
            from auto_detect_original_v2_model import process_original_learning_cycle
            learning_attest = (attest_learning_stopped_generation if stopped_learning
                               else attest_learning_running_generation)
            proof = learning_attest()
            if proof.generation != pending_name:
                raise OriginalLockRefused("learning_original_generation_changed_in_child")
            processed = process_original_learning_cycle(
                writer, proof, WORK / proof.operation_id, config_fd=4,
                config_path=CONFIG_PATH, owned_root=OWNED_ROOT,
                manual_hostlists=payload["manual_hostlists"],
                global_exclude=payload["global_exclude"],
                attest=learning_attest,
                inspect=probe_stopped_learning_pending_fd if stopped_learning else probe_pending_fd,
                stopped=stopped_learning)
            return dict(kind="original-learning-minute-completed", processed=processed,
                        generation=proof.generation, ack_authorized=False)
        completion = commit_with_original_v2_model(
            writer, pending, owned_root=OWNED_ROOT,
            manual_hostlists=payload["manual_hostlists"],
            global_exclude=payload["global_exclude"],
            attest=attest_stopped_generation if retired else attest_running_generation,
            inspect=probe_stopped_pending_fd if retired else probe_pending_fd,
            running_live=not retired)
        if completion.get("ack_authorized") is not False:
            raise OriginalLockRefused("original_v2_checkpoint_not_authorization")
        return completion


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if (len(argv) != 2 or argv[0] not in (
            "commit-fds", "commit-retired-fds", "commit-learning-fds",
            "commit-stopped-learning-fds") or
            not sys.platform.startswith("freebsd") or os.geteuid() != 0):
        return 64
    try:
        response = _native_fd_child(argv[1], json.loads(read_bounded_original_model()),
                                    retired=argv[0] == "commit-retired-fds",
                                    learning=argv[0] in (
                                        "commit-learning-fds",
                                        "commit-stopped-learning-fds"),
                                    stopped_learning=argv[0] ==
                                        "commit-stopped-learning-fds")
        print(json.dumps(response, sort_keys=True, separators=(",", ":")))
        return 0
    except (OriginalLockRefused, V2OriginalConfigRefused,
            CursorChainRefused, OriginalV2PrepareRefused,
            QueueSafetyError, ValueError, OSError, TypeError, KeyError,
            RuntimeError):
        return 69


if __name__ == "__main__":
    raise SystemExit(main())
