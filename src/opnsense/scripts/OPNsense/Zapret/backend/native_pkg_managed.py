#!/usr/bin/env python3
"""Root-only installed managed package *inspection* CLI, not an updater.

The launcher transfers an exclusive original historical FD9 via SCM_RIGHTS to
an independently supervised child; no pkg mutation path is implemented.  All
non-inspection commands, including upgrade, fail closed before any operation.
"""
import array
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
import native_pkg_handoff as transport
import native_pkg_candidate as candidate

LOCK = Path('/var/run/zapret2-lifecycle.lock')
MAX_MESSAGE = 4096


class ManagedRefusal(Exception):
    pass


def require(condition, code):
    if not condition:
        raise ManagedRefusal(code)


def original_lock_fd():
    """Acquire and retain real exclusive FD9; never truncate historical inode."""
    require(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
            os.uname().machine == 'amd64', 'ROOT_FREEBSD_MANAGED_INSPECTION_ONLY')
    require(LOCK == transport.LOCK and not LOCK.is_symlink(),
            'HISTORICAL_LOCK_PATH_UNTRUSTED')
    try:
        fd = os.open(LOCK, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        created = True
    except FileExistsError:
        fd = os.open(LOCK, os.O_RDWR | os.O_NOFOLLOW)
        created = False
    try:
        st = os.fstat(fd)
        current = LOCK.lstat()
        require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and st.st_nlink == 1 and
                not (stat.S_IMODE(st.st_mode) & 0o022) and
                (st.st_dev, st.st_ino) == (current.st_dev, current.st_ino),
                'ORIGINAL_LOCK_INODE_UNTRUSTED')
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ManagedRefusal('ORIGINAL_FD9_BUSY_BEFORE_INSPECTION') from None
        transport.verify_original_lock(fd, st.st_ino)
        return fd, created, st.st_ino
    except BaseException:
        os.close(fd)
        raise


def _product_script_identity():
    path = Path(__file__)
    require(path.is_absolute() and not path.is_symlink(), 'MANAGED_SOURCE_UNTRUSTED')
    st = path.lstat()
    require(stat.S_ISREG(st.st_mode) and st.st_uid == 0 and
            st.st_nlink == 1 and not (stat.S_IMODE(st.st_mode) & 0o022),
            'MANAGED_SOURCE_INODE_UNTRUSTED')
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def _read_response(sock):
    chunks = []
    total = 0
    while True:
        block = sock.recv(1024)
        if not block:
            break
        total += len(block)
        require(total <= MAX_MESSAGE, 'MANAGED_RESULT_OVERSIZE')
        chunks.append(block)
    try:
        return json.loads(b''.join(chunks))
    except (UnicodeError, ValueError):
        raise ManagedRefusal('MANAGED_WORKER_RESULT_NOT_JSON') from None


def inspect_independent(archive, version, digest):
    """Genuine detached subprocess owns transferred original FD9 until result."""
    require(isinstance(archive, Path), 'PACKAGE_REQUEST_PATH_REQUIRED')
    candidate.identity(archive, version, digest)
    source, source_sha = _product_script_identity()
    fd, created, inode = original_lock_fd()
    parent = child = None
    proc = None
    try:
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_STREAM)
        # FD9 is reserved for the transferred lifecycle owner inside the worker.
        if child.fileno() == 9:
            moved = fcntl.fcntl(child.fileno(), fcntl.F_DUPFD, 10)
            child.close()
            child = socket.socket(fileno=moved)
        head, nonce = secrets.token_hex(20), secrets.token_hex(16)
        parent.settimeout(95)
        command = [sys.executable, '-B', str(source), '--worker',
                   str(child.fileno()), head, nonce, source_sha,
                   str(os.getpid()), str(archive), version, digest]
        proc = subprocess.Popen(command, close_fds=True, pass_fds=(child.fileno(),),
                                start_new_session=True, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        child.close()
        packet = {'head': head, 'nonce': nonce, 'created': created, 'inode': inode}
        parent.sendmsg([json.dumps(packet, sort_keys=True).encode('ascii')],
                       [(socket.SOL_SOCKET, socket.SCM_RIGHTS,
                         array.array('i', [fd]))])
        parent.shutdown(socket.SHUT_WR)
        result = _read_response(parent)
        require(proc.wait(timeout=12) == 0 and isinstance(result, dict) and
                result.get('status') == 'PASS_MANAGED_READ_ONLY_INSPECTION' and
                result.get('worker_pid') == proc.pid and
                result.get('session_head') == head and
                result.get('nonce_sha256') == hashlib.sha256(nonce.encode()).hexdigest() and
                result.get('original_fd9_inode') == inode and
                result.get('archive_sha256') == digest and
                result.get('pkg_invoked') is False and
                result.get('old_owner_qualified') is False and
                result.get('lh08_ac11_accepted') is False,
                'MANAGED_WORKER_ATTESTATION_UNQUALIFIED')
        transport.verify_original_lock(fd, inode)
        return result
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
        raise ManagedRefusal('MANAGED_INSPECTION_WORKER_UNAVAILABLE:' +
                             type(exc).__name__) from None
    finally:
        if parent is not None:
            parent.close()
        if child is not None:
            child.close()
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=8)
        os.close(fd)


def worker(socket_fd, head, nonce, source_sha, parent_pid,
           archive, version, digest):
    """This cannot dispatch pkg; it receives only a read-only archive probe."""
    require(os.geteuid() == 0 and os.uname().sysname == 'FreeBSD' and
            os.uname().machine == 'amd64', 'ROOT_FREEBSD_WORKER_REQUIRED')
    source, observed_sha = _product_script_identity()
    require(observed_sha == source_sha and os.getppid() == int(parent_pid),
            'WORKER_SOURCE_OR_PARENT_CHANGED')
    with socket.socket(fileno=int(socket_fd)) as conn:
        conn.settimeout(45)
        received, fields = transport.receive_original_fd9(conn, head=head, nonce=nonce)
        try:
            os.dup2(received, 9)
            if received != 9:
                os.close(received)
            result = candidate.inspect_with_original_fd9(
                Path(archive), version, digest, fields['inode'])
            require(result['status'] == 'READ_ONLY_NATIVE_PKG_ARCHIVE_BOUND' and
                    result['sha256'] == digest, 'WORKER_CANDIDATE_UNQUALIFIED')
            answer = {'status': 'PASS_MANAGED_READ_ONLY_INSPECTION',
                      'worker_pid': os.getpid(), 'session_head': head,
                      'nonce_sha256': hashlib.sha256(nonce.encode()).hexdigest(),
                      'original_fd9_inode': fields['inode'],
                      'archive_sha256': digest, 'pkg_invoked': False,
                      'old_owner_qualified': False, 'lh08_ac11_accepted': False}
            conn.sendall(json.dumps(answer, sort_keys=True).encode('ascii'))
            return answer
        finally:
            os.close(9)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) == 4 and args[0] == 'inspect-candidate':
            result = inspect_independent(Path(args[1]), args[2], args[3])
            print('ZAPRET2_MANAGED=' + json.dumps(result, sort_keys=True))
            return 0
        if len(args) == 9 and args[0] == '--worker':
            worker(*args[1:])
            return 0
        raise ManagedRefusal('UPGRADE_NOT_IMPLEMENTED_NO_PKG')
    except (ManagedRefusal, candidate.CandidateRefusal,
            transport.HandoffRefusal, OSError, ValueError) as exc:
        print('ZAPRET2_MANAGED=REFUSED:' + str(exc), file=sys.stderr)
        return 78


if __name__ == '__main__':
    sys.exit(main())
