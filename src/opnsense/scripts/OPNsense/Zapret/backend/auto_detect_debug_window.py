#!/usr/bin/env python3
"""P2k #1052: bounded read-only native raw/debug pairing proposal.

Evidence is structural, NOT an acknowledgement adapter. Native debug says
"adding to" BEFORE append_to_list_file; a positive debug line alone is not
proof of a durable raw write. The real FD9/FD + cursor persistence/sink remain
mandatory before production use.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import os
from pathlib import Path
import re
import stat

from auto_detect_owner import GenerationProof

MAX_DEBUG = 4 * 1024 * 1024
MAX_WINDOW = 256 * 1024
MAX_RAW = 4 * 1024 * 1024
MAX_EVENTS = 4096
GEN = re.compile(r"[a-f0-9]{32}\Z", re.ASCII)
HOST = re.compile(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?\Z", re.ASCII)
# Pinned upstream v1.0.7 params.c LOG_APPEND and desync.c auto_hostlist_failed.
ADD = re.compile(
    r"[^\r\n]{1,64} : (?P<host>[a-z0-9.-]{1,253}) : profile "
    r"(?P<profile>[1-9][0-9]{0,2}) \([^\r\n()]{0,64}\) : client "
    r"[^\r\n]{1,96} : proto (?:http|tls|quic) : adding to "
    r"(?P<path>/[^\r\n]{1,512})\Z", re.ASCII)


class DebugWindowRefused(ValueError):
    """Input survives; no cursor advancement or acknowledgment."""


@dataclass(frozen=True)
class Cursor:
    generation: str
    device: int
    inode: int
    offset: int
    prefix_sha256: str


@dataclass(frozen=True)
class Candidate:
    host: str
    native_number: int
    debug_offset: int


@dataclass(frozen=True)
class Window:
    candidates: tuple[Candidate, ...]
    proposed_cursor: Cursor


def _hostname(host: str) -> bool:
    if not HOST.fullmatch(host) or '..' in host or len(host) > 253:
        return False
    pieces = host.split('.')
    if len(pieces) < 2 or any(len(p) > 63 or p.startswith('-') or
                              p.endswith('-') for p in pieces):
        return False
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return True
    return False


def _owner(proof: GenerationProof, path: Path) -> None:
    if (not isinstance(proof, GenerationProof) or
            not GEN.fullmatch(proof.generation) or
            proof.generation != proof.operation_id or
            path != Path(proof.debug_path) or not path.is_absolute() or
            not Path(proof.raw_path).is_absolute() or
            proof.raw_path == proof.debug_path or
            not any(x == (proof.observer_native_number, 'observer', None)
                    for x in proof.profiles)):
        raise DebugWindowRefused('unqualified_generation_or_debug_path')


def _read_exact(path: Path, *, owner_uid: int, writer_gid: int | None) -> tuple[os.stat_result, bytes]:
    try:
        directory = path.parent.lstat()
        dm = stat.S_IMODE(directory.st_mode)
        if (not stat.S_ISDIR(directory.st_mode) or
                directory.st_uid != owner_uid or
                ((writer_gid is None and dm & 0o077) or
                 (writer_gid is not None and
                  (directory.st_gid != writer_gid or dm != 0o710)))):
            raise DebugWindowRefused('unsafe_native_debug_parent')
        before = path.lstat()
        mode = stat.S_IMODE(before.st_mode)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid != owner_uid or
                before.st_nlink != 1 or before.st_size > MAX_DEBUG or
                ((writer_gid is None and mode & 0o022) or
                 (writer_gid is not None and
                  (writer_gid <= 0 or before.st_gid != writer_gid or mode != 0o660)))):
            raise DebugWindowRefused('unsafe_native_debug_file')
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            start = os.fstat(fd)
            if (start.st_dev, start.st_ino, start.st_size, start.st_mtime_ns) != (
                    before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise DebugWindowRefused('debug_changed_before_read')
            data = bytearray()
            while len(data) <= MAX_DEBUG:
                buf = os.read(fd, min(65536, MAX_DEBUG + 1 - len(data)))
                if not buf:
                    break
                data.extend(buf)
            end = os.fstat(fd)
        finally:
            os.close(fd)
        current = path.lstat()
        if (len(data) != before.st_size or len(data) > MAX_DEBUG or
                (end.st_dev, end.st_ino, end.st_size, end.st_mtime_ns,
                 current.st_dev, current.st_ino, current.st_size,
                 current.st_mtime_ns) !=
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)):
            raise DebugWindowRefused('debug_modified_during_snapshot')
        return before, bytes(data)
    except OSError as exc:
        raise DebugWindowRefused('debug_read_unavailable') from exc


def empty_epoch(proof: GenerationProof, *, owner_uid: int = 0,
                writer_gid: int | None = None) -> Cursor:
    """Only start a new generation with an empty, root-attested debug inode."""
    path = Path(proof.debug_path) if isinstance(proof, GenerationProof) else Path('/')
    _owner(proof, path)
    info, data = _read_exact(path, owner_uid=owner_uid, writer_gid=writer_gid)
    if data:
        raise DebugWindowRefused('unowned_existing_debug_history')
    return Cursor(proof.generation, info.st_dev, info.st_ino, 0,
                  hashlib.sha256(b'').hexdigest())


def propose_window(proof: GenerationProof, cursor: Cursor, raw: bytes, *,
                   owner_uid: int = 0, writer_gid: int | None = None) -> Window:
    """Return a *non-authorizing* candidate and possible next cursor.

    A caller must separately attest process birth, all native writer FDs,
    actual old pending inode, and a durably idempotent final destination;
    this return value is NOT itself a committed callback or durable cursor.
    """
    path = Path(proof.debug_path) if isinstance(proof, GenerationProof) else Path('/')
    _owner(proof, path)
    if (not isinstance(cursor, Cursor) or cursor.generation != proof.generation or
            type(cursor.device) is not int or type(cursor.inode) is not int or
            type(cursor.offset) is not int or cursor.device < 0 or cursor.inode <= 0 or
            cursor.offset < 0 or not re.fullmatch('[a-f0-9]{64}', cursor.prefix_sha256)):
        raise DebugWindowRefused('untrusted_or_other_generation_cursor')
    if (type(raw) is not bytes or not raw or len(raw) > MAX_RAW or
            not raw.endswith(b'\n') or b'\r' in raw or b'\x00' in raw):
        raise DebugWindowRefused('invalid_or_incomplete_raw_segment')
    try:
        hosts = [part.decode('ascii') for part in raw.split(b'\n')[:-1]]
    except UnicodeError as exc:
        raise DebugWindowRefused('invalid_raw_encoding') from exc
    if (not 1 <= len(hosts) <= MAX_EVENTS or
            any(not _hostname(host) for host in hosts)):
        raise DebugWindowRefused('unqualified_raw_host')
    info, content = _read_exact(path, owner_uid=owner_uid, writer_gid=writer_gid)
    if ((info.st_dev, info.st_ino) != (cursor.device, cursor.inode) or
            cursor.offset > len(content) or
            hashlib.sha256(content[:cursor.offset]).hexdigest() != cursor.prefix_sha256):
        raise DebugWindowRefused('debug_cursor_replaced_truncated_or_rewritten')
    tail = content[cursor.offset:]
    if (len(tail) > MAX_WINDOW or (tail and not tail.endswith(b'\n')) or
            b'\x00' in tail):
        raise DebugWindowRefused('debug_window_oversized_or_incomplete')
    candidates = []
    pos = cursor.offset
    for line in tail.splitlines(keepends=True):
        try:
            decoded = line[:-1].decode('ascii')
        except UnicodeError as exc:
            raise DebugWindowRefused('invalid_debug_encoding') from exc
        if ' : adding to ' in decoded:
            m = ADD.fullmatch(decoded)
            if m is None or m.group('path') != proof.raw_path:
                raise DebugWindowRefused('ambiguous_or_wrong_native_add_event')
            number = int(m.group('profile'))
            host = m.group('host')
            if (not _hostname(host) or
                    (number, 'observer', None) not in proof.profiles):
                raise DebugWindowRefused('unauthorized_native_profile_or_host')
            candidates.append(Candidate(host, number, pos))
        # RST, reset, fail counter and NOT adding are NOT positives.
        pos += len(line)
    if [x.host for x in candidates] != hosts:
        raise DebugWindowRefused('raw_and_positive_debug_not_one_to_one')
    return Window(tuple(candidates), Cursor(proof.generation, info.st_dev,
                  info.st_ino, len(content), hashlib.sha256(content).hexdigest()))


def run_native_debug_collector() -> None:
    raise DebugWindowRefused('read_only_candidates_not_authorized_for_ack')


if __name__ == '__main__':
    run_native_debug_collector()
