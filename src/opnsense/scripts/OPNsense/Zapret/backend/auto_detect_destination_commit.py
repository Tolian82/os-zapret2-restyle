#!/usr/bin/env python3
"""#1052 P2k8p: one v2 per-slot P2k2b destination CAS/checkpoint owner.

Original P2a queue, original Config/P1 and GUI destination flocks must be
held by the caller. No superseded single-intent destination entrypoint.
"""
from __future__ import annotations

from contextlib import contextmanager

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from auto_detect_epoch_receipts import EpochReceipts, ReceiptRefused, _canonical, _read, _sync, _write_once, _directory
from auto_detect_queue import DurableInbox

MAX_TARGET = 4 * 1024 * 1024
HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class DestinationRefused(ReceiptRefused):
    """The unacknowledged source stays retained on any unsafe destination."""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _target(path: Path, uid: int) -> tuple[bytes, os.stat_result]:
    """Strict regular-file snapshot; never trust a symlink or a stale FD."""
    try:
        parent = path.parent.lstat()
        st = path.lstat()
        if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != uid or
                parent.st_mode & 0o022 or
                not stat.S_ISREG(st.st_mode) or st.st_uid != uid or
                st.st_nlink != 1 or st.st_mode & 0o022 or
                st.st_size > MAX_TARGET):
            raise DestinationRefused("unsafe_destination")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            a = os.fstat(fd)
            data = os.read(fd, MAX_TARGET + 1)
            b = os.fstat(fd)
        finally:
            os.close(fd)
        identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns, x.st_mode)
        if identity(st) != identity(a) or identity(a) != identity(b) or len(data) != st.st_size:
            raise DestinationRefused("destination_changed_during_read")
        data.decode("utf-8")
        return data, st
    except (OSError, UnicodeError) as exc:
        raise DestinationRefused("destination_read_failed") from exc


def _edit(before: bytes, add: list[str], remove: list[str]) -> bytes:
    if (not isinstance(add, list) or not isinstance(remove, list) or
            len(add) + len(remove) > 4096 or
            any(type(x) is not str or not HOST.fullmatch(x) or ".." in x
                for x in add + remove)):
        raise DestinationRefused("invalid_domain_effects")
    text = before.decode("utf-8")
    # Preserve every non-owned modifier, comment and existing user row verbatim.
    lines = text.splitlines(keepends=True)
    removed = set(remove)
    out = [line for line in lines if line.rstrip("\r\n") not in removed]
    present = {line.rstrip("\r\n") for line in out}
    for host in sorted(set(add)):
        if host not in present:
            if out and not out[-1].endswith("\n"):
                out.append("\n")
            out.append(host + "\n")
            present.add(host)
    result = "".join(out).encode("utf-8")
    if len(result) > MAX_TARGET:
        raise DestinationRefused("destination_growth_limit")
    return result


def _replace(path: Path, current: bytes, expected: bytes, uid: int) -> None:
    """One protected same-directory replace after read-side CAS under GUI lock."""
    now, st = _target(path, uid)
    if now != current:
        raise DestinationRefused("destination_conflict_with_gui")
    temp = path.parent / (".auto-detect-" + secrets.token_hex(16) + ".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        os.fchown(fd, st.st_uid, st.st_gid)
        os.fchmod(fd, stat.S_IMODE(st.st_mode))
        data = memoryview(expected)
        while data:
            n = os.write(fd, data)
            if n <= 0:
                raise DestinationRefused("short_destination_write")
            data = data[n:]
        os.fsync(fd)
    finally:
        os.close(fd)
    # Writers that ignore the shared GUI lock are not trusted. Recheck before
    # replace; the next GUI implementation MUST acquire this same lock.
    try:
        again, check = _target(path, uid)
        if again != current or (check.st_dev, check.st_ino) != (st.st_dev, st.st_ino):
            raise DestinationRefused("destination_conflict_with_gui")
        os.replace(temp, path)
        _sync(path.parent)
    finally:
        if temp.exists():
            temp.unlink()
            _sync(path.parent)



@contextmanager
def exclusive_destination_lock(gui_lock: Path, owner_uid: int):
    """Shared native root flock for GUI save/read and P2k4 destination writes.

    This lock is intentionally independent of queue/FD9/Config locks; GUI
    edits neither assume nor acquire authority to mutate config.xml.
    """
    path = Path(gui_lock)
    if not path.is_absolute():
        raise DestinationRefused("unsafe_gui_lock_path")
    parent = path.parent.lstat()
    if (not stat.S_ISDIR(parent.st_mode) or parent.st_uid != owner_uid
            or parent.st_mode & 0o022):
        raise DestinationRefused("unsafe_gui_lock_directory")
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        st = os.fstat(fd)
        name = path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid != owner_uid or
                stat.S_IMODE(st.st_mode) != 0o600 or st.st_nlink != 1 or
                (st.st_dev, st.st_ino) != (name.st_dev, name.st_ino)):
            raise DestinationRefused("unsafe_gui_lock")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise DestinationRefused("gui_writer_busy") from None
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def qualified_destination_plan(folder: Path, intent: dict, uid: int,
                               targets: dict[str, Path] | None = None
                               ) -> tuple[dict, bytes]:
    """Verify the ONE immutable original plan, including pre-write inodes.

    Schema 2 was chosen for the current dormant journal, not as a legacy
    migration. A preimage identity must already exist INSIDE the original
    plan before the first physical destination write; replay cannot invent
    the identity after a GUI edit or a partial crash.
    """
    journal = folder / "destination"
    _directory(journal, uid)
    names = set(os.listdir(journal))
    if names - {"plan.json", "checkpoint.json"} or "plan.json" not in names:
        raise DestinationRefused("missing_or_foreign_destination_plan")
    plan_raw = _read(journal / "plan.json", uid)
    try:
        plan = json.loads(plan_raw)
    except (ValueError, UnicodeError) as exc:
        raise DestinationRefused("corrupt_destination_plan") from exc
    expected = {
        "schema": 2, "kind": "durable-destination-plan",
        "generation": intent["generation"],
        "pending_name": intent["pending_name"],
        "pending_sha256": intent["pending_sha256"],
        "evidence": intent["evidence"],
        "debug_end_offset": intent["debug_end_offset"],
        "debug_end_sha256": intent["debug_end_sha256"],
    }
    if (not isinstance(plan, dict) or
            set(plan) != set(expected) | {"writes"} or
            any(plan.get(k) != v for k, v in expected.items()) or
            not isinstance(plan.get("writes"), dict) or
            len(plan["writes"]) > 16 or
            (targets is not None and set(plan["writes"]) - set(targets))):
        raise DestinationRefused("destination_plan_not_bound_to_original_intent")
    for name, change in plan["writes"].items():
        identity = {
            "before_device", "before_inode", "before_ctime_ns",
            "before_mtime_ns", "before_size",
        }
        if (not isinstance(name, str) or
                not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", name) or
                not isinstance(change, dict) or
                set(change) != {"path", "before", "after", "add", "remove"} | identity or
                not isinstance(change.get("path"), str) or
                not Path(change["path"]).is_absolute() or
                (targets is not None and
                 change["path"] != str(targets[name])) or
                any(not isinstance(change.get(d), str) or
                    not SHA256.fullmatch(change[d])
                    for d in ("before", "after")) or
                any(type(change.get(k)) is not int or change[k] < 0
                    for k in identity) or
                change["before_inode"] == 0 or
                change["before_size"] > MAX_TARGET or
                any(type(change.get(k)) is not list or
                    len(change[k]) > 4096 or
                    any(type(x) is not str or
                        not HOST.fullmatch(x) or ".." in x
                        for x in change[k])
                    for k in ("add", "remove")) or
                len(change["add"]) + len(change["remove"]) > 4096):
            raise DestinationRefused("destination_preimage_plan_invalid")
    return plan, plan_raw


class DestinationCommit:
    """A prepared-intent journal: prepare -> per-file CAS -> checkpoint.

    The caller's owner/FD proofs are NOT implied by this API. No automatic
    invocation is installed. The queue lock must be held for every call, and
    GUI must use the same external lock before P3 enables native writes.
    """

    def __init__(self, receipts: EpochReceipts, queue: DurableInbox,
                 targets: dict[str, Path], gui_lock: Path):
        self.receipts, self.queue = receipts, queue
        self.targets = {k: Path(v) for k, v in targets.items()}
        self.gui_lock = Path(gui_lock)
        if (not self.targets or "auto" not in self.targets or
                any(not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}", k)
                    for k in self.targets) or
                len(set(self.targets.values())) != len(self.targets) or
                any(not p.is_absolute() for p in self.targets.values()) or
                not self.gui_lock.is_absolute() or
                self.gui_lock in self.targets.values()):
            raise DestinationRefused("unqualified_destination_mapping")

    @contextmanager
    def exclusive_targets(self):
        """Lock the P1 snapshot and P2k2b CAS under the same root flock."""
        if getattr(self, "_gui_held", False):
            raise DestinationRefused("gui_lock_already_held")
        with exclusive_destination_lock(self.gui_lock, self.receipts.uid):
            self._gui_held = True
            try:
                yield self
            finally:
                self._gui_held = False

    def _locked_commit(self, folder: Path, intent: dict, raw: bytes,
                       effects: dict) -> dict:
        if not getattr(self, "_gui_held", False):
            raise DestinationRefused("gui_lock_required")
        journal = folder / "destination"
        if not journal.exists() and not journal.is_symlink():
            journal.mkdir(mode=0o700)
            _sync(folder)
        _directory(journal, self.receipts.uid)
        names = set(os.listdir(journal))
        if names - {"plan.json", "checkpoint.json"}:
            raise DestinationRefused("foreign_destination_receipts")
        plan_path, checkpoint_path = journal / "plan.json", journal / "checkpoint.json"
        if "plan.json" not in names:
            writes = {}
            for name, change in sorted(effects.items()):
                path = self.targets[name]
                before, st = _target(path, self.receipts.uid)
                after = _edit(before, change["add"], change["remove"])
                writes[name] = {
                    "path": str(path), "before": _sha(before),
                    "after": _sha(after), "add": change["add"],
                    "remove": change["remove"],
                    "before_device": st.st_dev, "before_inode": st.st_ino,
                    "before_ctime_ns": st.st_ctime_ns,
                    "before_mtime_ns": st.st_mtime_ns,
                    "before_size": st.st_size,
                }
            plan = {"schema": 2, "kind": "durable-destination-plan",
                    "generation": intent["generation"],
                    "pending_name": intent["pending_name"],
                    "pending_sha256": intent["pending_sha256"],
                    "evidence": intent["evidence"],
                    "debug_end_offset": intent["debug_end_offset"],
                    "debug_end_sha256": intent["debug_end_sha256"],
                    "writes": writes}
            _write_once(journal, "plan.json", _canonical(plan), self.receipts.uid)
        plan, plan_raw = qualified_destination_plan(
            folder, intent, self.receipts.uid, targets=self.targets)
        if checkpoint_path.exists() or checkpoint_path.is_symlink():
            checkpoint = json.loads(_read(checkpoint_path, self.receipts.uid))
            if (checkpoint.get("plan_sha256") != _sha(plan_raw) or
                    checkpoint.get("evidence") != intent["evidence"] or
                    checkpoint.get("committed_cursor_offset") != intent["debug_end_offset"] or
                    checkpoint.get("committed_cursor_sha256") != intent["debug_end_sha256"]):
                raise DestinationRefused("checkpoint_differs_from_plan")
            return checkpoint  # never undo later GUI deletion on acknowledged replay
        # All-target preflight BEFORE any physical CAS replacement. A GUI
        # delete after an earlier write can restore the original BYTE digest
        # but not the original inode/ctime. The old content hash ALONE must
        # never authorize putting the manually deleted row back.
        todo = []
        for name, change in sorted(plan["writes"].items()):
            path = self.targets[name]
            current, st = _target(path, self.receipts.uid)
            if _sha(current) == change["after"]:
                continue  # fully applied (or a no-op); do not rewrite it
            if (_sha(current) != change["before"] or
                    (st.st_dev, st.st_ino, st.st_ctime_ns,
                     st.st_mtime_ns, st.st_size) !=
                    (change["before_device"], change["before_inode"],
                     change["before_ctime_ns"], change["before_mtime_ns"],
                     change["before_size"])):
                raise DestinationRefused("destination_gui_or_preimage_changed")
            new = _edit(current, change["add"], change["remove"])
            if _sha(new) != change["after"]:
                raise DestinationRefused("destination_plan_diverged")
            todo.append((path, current, new))
        for path, current, new in todo:
            _replace(path, current, new, self.receipts.uid)
        checkpoint = {"schema": 1, "kind": "destination-and-cursor-committed",
                      "generation": intent["generation"], "pending_name": intent["pending_name"],
                      "plan_sha256": _sha(plan_raw),
                      "evidence": intent["evidence"],
                      "committed_cursor_offset": intent["debug_end_offset"],
                      "committed_cursor_sha256": intent["debug_end_sha256"],
                      "ack_authorized": False}
        _write_once(journal, "checkpoint.json", _canonical(checkpoint), self.receipts.uid)
        return checkpoint


# TZ6v2 Shared Apply: the SAME original P2 destination CAS owner.
# No alternative file writer, no new CLI, no new Config writer or journal.
# The public operation is bound to the existing original FD9 + activating
# Shared Apply record + sealed original candidate. The low-level helper is
# deliberately private for controlled preflight/partial-failure tests.
SHARED_FOUND_NAMES = ("youtube", "user", "auto")
SHARED_FOUND_LIMIT = 40 * 1024


def _qualified_shared_found_batch(rows: dict) -> dict:
    from domain_policy import PublicSuffixList, normalize_found_editor

    if not isinstance(rows, dict) or list(rows) != list(SHARED_FOUND_NAMES):
        raise DestinationRefused("shared_found_batch_incomplete")
    psl = PublicSuffixList.load()
    out = {}
    identity = ("before_device", "before_inode", "before_ctime_ns",
                "before_mtime_ns", "before_size")
    for name in SHARED_FOUND_NAMES:
        entry = rows[name]
        if (not isinstance(entry, dict) or
                set(entry) != {"before", "after", "before_revision", *identity} or
                not isinstance(entry["before"], str) or
                not isinstance(entry["after"], str) or
                not isinstance(entry["before_revision"], str) or
                not SHA256.fullmatch(entry["before_revision"]) or
                any(type(entry.get(k)) is not int or entry[k] < 0 for k in identity) or
                entry["before_inode"] == 0):
            raise DestinationRefused("shared_found_candidate_shape")
        before, after = (entry[k].encode("utf-8") for k in ("before", "after"))
        if (len(before) > SHARED_FOUND_LIMIT or len(after) > SHARED_FOUND_LIMIT or
                entry["before_size"] != len(before) or
                _sha(b"present\0" + before) != entry["before_revision"]):
            raise DestinationRefused("shared_found_candidate_revision")
        try:
            for text in (entry["before"], entry["after"]):
                parsed = normalize_found_editor(text, name, psl=psl)["normalized"]
                if text != (parsed + "\n" if parsed else ""):
                    raise DestinationRefused("shared_found_candidate_noncanonical")
        except (ValueError, TypeError) as exc:
            raise DestinationRefused("shared_found_candidate_domain_policy") from exc
        out[name] = before, after, tuple(entry[k] for k in identity)
    return out


def _locked_shared_found_replace(rows: dict, targets: dict, *, uid: int,
                                 replace_fn=None) -> dict:
    """All-target preflight, original P2 CAS replacements, bounded compensation.

    Caller MUST hold original FD9 and Config→P2 destination lock. A fault is
    never sufficient proof that the whole Config/runtime transaction restored.
    """
    if (not isinstance(targets, dict) or
            list(targets) != list(SHARED_FOUND_NAMES) or
            len(set(map(str, targets.values()))) != len(SHARED_FOUND_NAMES)):
        raise DestinationRefused("shared_found_targets_incomplete")
    batch = _qualified_shared_found_batch(rows)
    replace = _replace if replace_fn is None else replace_fn
    original = {}
    for name in SHARED_FOUND_NAMES:
        path = Path(targets[name])
        if not path.is_absolute():
            raise DestinationRefused("shared_found_target_not_absolute")
        before, after, preimage = batch[name]
        now, st = _target(path, uid)
        observed = (st.st_dev, st.st_ino, st.st_ctime_ns,
                    st.st_mtime_ns, st.st_size)
        if now != before or observed != preimage:
            raise DestinationRefused("shared_found_preimage_changed")
        original[name] = (path, before, after)
    modified = []
    try:
        for name in SHARED_FOUND_NAMES:
            path, before, after = original[name]
            if before == after:
                continue
            # Include a replacement that may raise *after* os.replace/fsync.
            modified.append(name)
            replace(path, before, after, uid)
            actual, _ = _target(path, uid)
            if actual != after:
                raise DestinationRefused("shared_found_postwrite_unverified")
        return {
            "result": "files-applied-under-original-transaction",
            "files": {
                name: {"before_sha256": _sha(original[name][1]),
                       "after_sha256": _sha(original[name][2]),
                       "changed": original[name][1] != original[name][2]}
                for name in SHARED_FOUND_NAMES
            },
            # A file-only receipt is NOT durable Apply success.
            "config_committed": False, "commit_authorized": False,
        }
    except (OSError, ValueError, DestinationRefused) as error:
        try:
            for name in reversed(modified):
                path, before, after = original[name]
                current, _ = _target(path, uid)
                if current == after:
                    replace(path, after, before, uid)
                elif current != before:
                    raise DestinationRefused("shared_found_restore_foreign_state")
            for name in SHARED_FOUND_NAMES:
                path, before, _ = original[name]
                current, _ = _target(path, uid)
                if current != before:
                    raise DestinationRefused("shared_found_restore_mismatch")
        except (OSError, ValueError, DestinationRefused) as rollback:
            raise DestinationRefused("shared_found_requires_review") from rollback
        raise DestinationRefused("shared_found_restored_after_failure") from error


def shared_apply_found_files_original_fd9(operation_id: str, config_fd: int) -> dict:
    """Apply the three files ONLY from existing activating FD9/sealed plan.

    This API has NO registered configd action and cannot independently save
    Config or claim a successful native Apply. Its caller must additionally
    hold the original Config/P2 lock ordering across plan qualification.
    """
    import sys
    from shared_apply_seal import WORK, verify_seal
    from shared_apply_operation import SharedApplyOperation, OP_ID
    from auto_detect_owned_sources import OWNED_ROOT, read_owned
    from auto_detect_original_lock_handoff import (
        CONFIG_PATH, assert_inherited_config_fd)
    from auto_detect_gui_hostlist import AUTO_HOSTLIST, AUTO_LOCK
    from voice_ipfw_adapter import require_lifecycle_lock

    if (not sys.platform.startswith("freebsd") or os.geteuid() != 0 or
            not isinstance(operation_id, str) or not OP_ID.fullmatch(operation_id)):
        raise DestinationRefused("original_native_fd9_required")
    require_lifecycle_lock()
    # The original OPNsense Config lock is an inherited real open file
    # description; a JSON token or fresh guessed lock is insufficient.
    assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
    record = SharedApplyOperation().read()
    if (record is None or record["phase"] != "activating" or
            record["detail"]["id"] != operation_id or
            record["detail"]["page"] != "strategies"):
        raise DestinationRefused("original_apply_not_activating")
    work = WORK / operation_id
    signed = verify_seal(work, owner=0)
    target = work / "plan.json"
    st = target.lstat()
    if (not stat.S_ISREG(st.st_mode) or st.st_uid != 0 or
            st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600 or
            not 0 < st.st_size <= 4 * 1024 * 1024):
        raise DestinationRefused("shared_found_original_plan_untrusted")
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        pinned = os.fstat(fd)
        raw = os.read(fd, 4 * 1024 * 1024 + 1)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    identity = lambda x: (x.st_dev, x.st_ino, x.st_size, x.st_mtime_ns)
    if (identity(st) != identity(pinned) or identity(st) != identity(after) or
            len(raw) != st.st_size or
            _sha(raw) != signed["sha256"]["plan.json"]):
        raise DestinationRefused("shared_found_original_plan_changed")
    try:
        plan = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise DestinationRefused("shared_found_original_plan_invalid") from exc
    if (not isinstance(plan, dict) or plan.get("page") != "strategies" or
            not isinstance(plan.get("found_batch"), dict)):
        raise DestinationRefused("shared_found_plan_not_original_owner")
    targets = {"youtube": OWNED_ROOT / "youtube.txt",
               "user": OWNED_ROOT / "user.txt",
               "auto": AUTO_HOSTLIST}
    with exclusive_destination_lock(AUTO_LOCK, 0):
        owned = read_owned(OWNED_ROOT, owner_uid=0)
        if not isinstance(owned, dict) or list(owned) != ["youtube", "user"]:
            raise DestinationRefused("shared_found_known_owner_uninitialized")
        rows = plan["found_batch"]
        if not isinstance(rows, dict) or list(rows) != list(SHARED_FOUND_NAMES):
            raise DestinationRefused("shared_found_plan_not_complete")
        if any(owned[name] != rows[name].get("before") for name in ("youtube", "user")
               if isinstance(rows[name], dict)):
            raise DestinationRefused("shared_found_known_owner_changed")
        result = _locked_shared_found_replace(rows, targets, uid=0)
        assert_inherited_config_fd(config_fd, CONFIG_PATH, owner_uid=None)
        return result
