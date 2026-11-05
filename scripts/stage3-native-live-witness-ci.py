#!/usr/bin/env python3
"""CI-only separate-process loopback mTLS witness for genuine original-FD9 pkg.

Not a deployed, independent, owner-approved, externally durable witness.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import select
import sqlite3
import ssl
import stat
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT_NAME = 'ci-live-witness'
SHA = re.compile(r'[a-f0-9]{64}\Z')
COMMIT = re.compile(r'[a-f0-9]{40}\Z')
NONCE = re.compile(r'[a-f0-9]{32}\Z')
MAX_RECEIPT = 1200
TIMEOUT = 15

class Refusal(Exception):
    pass


def need(value, why):
    if not value:
        raise Refusal(why)


def mode():
    value = os.environ.get('ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS', '')
    need(value in ('', '1'), 'CI_LIVE_WITNESS_MODE_INVALID')
    if value:
        need(os.environ.get('GITHUB_ACTIONS') == 'true' and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_LIVE_WITNESS_CI') == '1' and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_MUTATING_PKG_CI') == '1' and
             os.environ.get('ZAPRET2_STAGE0_DISPOSABLE_OFFICIAL_MK') == '1' and
             os.environ.get('ZAPRET2_STAGE3_NATIVE_STDIN_PKG') == '1',
             'CI_LIVE_WITNESS_DISPOSABLE_OPTIN_REQUIRED')
    return value == '1'


def load(filename):
    spec = importlib.util.spec_from_file_location(
        'ci_fd9_' + filename.replace('-', '_').replace('.', '_'), HERE / filename)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def private_root(root):
    folder = Path(root) / ROOT_NAME
    st = folder.lstat()
    need(stat.S_ISDIR(st.st_mode) and st.st_uid == os.geteuid() and
         stat.S_IMODE(st.st_mode) == 0o700 and not folder.is_symlink(),
         'CI_LIVE_WITNESS_PRIVATE_ROOT_INVALID')
    return folder


def owned_bytes(path, limit=MAX_RECEIPT):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid() and
             before.st_nlink == 1 and stat.S_IMODE(before.st_mode) == 0o600 and
             0 < before.st_size <= limit, 'CI_LIVE_WITNESS_PRIVATE_FILE_INVALID')
        data = b''
        while True:
            chunk = os.read(fd, min(4096, limit + 1 - len(data)))
            if not chunk:
                break
            data += chunk
            need(len(data) <= limit, 'CI_LIVE_WITNESS_PRIVATE_FILE_TOO_LARGE')
        after = os.fstat(fd)
        need(len(data) == before.st_size and
             (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
              before.st_ctime_ns) ==
             (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
              after.st_ctime_ns), 'CI_LIVE_WITNESS_PRIVATE_FILE_CHANGED')
        return data
    finally:
        os.close(fd)


def openssl(*arguments):
    result = subprocess.run(['/usr/bin/openssl', *map(str, arguments)],
                            capture_output=True, check=False, timeout=20)
    need(result.returncode == 0,
         'CI_LIVE_WITNESS_OPENSSL_FAILURE:' + str(arguments[0]))
    return result.stdout


def prepare(root):
    need(mode(), 'CI_LIVE_WITNESS_NOT_ENABLED')
    folder = Path(root) / ROOT_NAME
    need(not folder.exists() and not folder.is_symlink(),
         'CI_LIVE_WITNESS_FOREIGN_ROOT_PRESENT')
    folder.mkdir(mode=0o700)
    private_root(root)
    ca_key, ca_cert = folder / 'ca.key', folder / 'ca.crt'
    openssl('genpkey', '-algorithm', 'RSA', '-pkeyopt', 'rsa_keygen_bits:2048',
            '-out', ca_key)
    openssl('req', '-x509', '-new', '-sha256', '-key', ca_key,
            '-out', ca_cert, '-days', '1', '-subj', '/CN=CI-FD9-Live-Witness-CA',
            '-addext', 'basicConstraints=critical,CA:TRUE',
            '-addext', 'keyUsage=critical,keyCertSign,cRLSign')
    for label, usage, san in (('server', 'serverAuth', 'subjectAltName=IP:127.0.0.1\n'),
                               ('client', 'clientAuth', '')):
        key = folder / (label + '.key')
        csr = folder / (label + '.csr')
        cert = folder / (label + '.crt')
        ext = folder / (label + '.ext')
        openssl('genpkey', '-algorithm', 'RSA', '-pkeyopt',
                'rsa_keygen_bits:2048', '-out', key)
        openssl('req', '-new', '-key', key, '-out', csr,
                '-subj', '/CN=CI-FD9-' + label)
        ext.write_text('basicConstraints=critical,CA:FALSE\n'
                       'keyUsage=digitalSignature,keyEncipherment\n'
                       'extendedKeyUsage=' + usage + '\n' + san)
        ext.chmod(0o600)
        openssl('x509', '-req', '-in', csr, '-CA', ca_cert, '-CAkey', ca_key,
                '-CAcreateserial', '-out', cert, '-days', '1', '-sha256',
                '-extfile', ext)
    for item in folder.iterdir():
        need(item.is_file() and not item.is_symlink(),
             'CI_LIVE_WITNESS_TLS_FIXTURE_UNSAFE')
        item.chmod(0o600)
    def thumb(label):
        der = ssl.PEM_cert_to_DER_cert((folder / (label + '.crt')).read_text())
        return hashlib.sha256(der).hexdigest()
    return {'client_sha256': thumb('client'), 'server_sha256': thumb('server')}


def accept_status_signer(root, secret):
    """Signer stays in witness-private fixture, never in operator role folder."""
    folder = private_root(root)
    target = folder / 'status.key'
    need(not target.exists() and not target.is_symlink(),
         'CI_LIVE_WITNESS_SIGNER_ALREADY_PRESENT')
    source = Path(secret)
    st = source.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid() and
         st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600,
         'CI_LIVE_WITNESS_SIGNER_UNSAFE')
    os.replace(source, target)
    need(owned_bytes(target, 8192).startswith(b'-----BEGIN PRIVATE KEY-----'),
         'CI_LIVE_WITNESS_SIGNER_BYTES_INVALID')
    return target


def start(root, ticket, head, old_archive, candidate_archive, nonce, resume=False):
    """Start actual mutually authenticated SQLite witness in another process."""
    folder = private_root(root)
    need(mode() and COMMIT.fullmatch(head) is not None and
         type(nonce) is str and NONCE.fullmatch(nonce) is not None,
         'CI_LIVE_WITNESS_START_SCOPE_INVALID')
    witness = load('stage3-prepkg-remote-witness-ci.py')
    database = folder / 'operations.sqlite'
    need(type(resume) is bool, 'CI_LIVE_WITNESS_RESTART_FLAG_INVALID')
    if resume:
        # A test witness can die after SQLite COMMIT. Never initialize/reset it.
        need(database.exists() and not database.is_symlink(),
             'CI_LIVE_WITNESS_RESTART_DB_UNTRUSTED')
        st = database.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid() and
             st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600,
             'CI_LIVE_WITNESS_RESTART_DB_UNTRUSTED')
        con = witness.open_existing(str(database))
        try:
            need(con.execute('PRAGMA quick_check').fetchone() == ('ok',),
                 'CI_LIVE_WITNESS_RESTART_DB_CORRUPT')
            rows = con.execute('SELECT id, serial FROM metadata').fetchall()
            need(len(rows) == 1 and rows[0][0] == 1 and
                 type(rows[0][1]) is int and rows[0][1] >= 0,
                 'CI_LIVE_WITNESS_RESTART_DB_METADATA_INVALID')
        finally:
            con.close()
    else:
        witness.initialize(str(database))
    grantroot = Path(root) / 'ci-operator-grant'
    cert_sha = hashlib.sha256(
        ssl.PEM_cert_to_DER_cert((folder / 'server.crt').read_text())).hexdigest()
    args = [sys.executable, '-u', str(HERE / 'stage3-prepkg-remote-witness-ci.py'),
            'serve', str(database), str(folder / 'status.key'),
            str(folder / 'ca.crt'), str(folder / 'server.crt'),
            str(folder / 'server.key'), ticket['client_sha256'],
            str(grantroot / 'signed-grant.json'),
            str(grantroot / 'signed-grant.sig'),
            str(grantroot / 'operator-public.pem'), ticket['operator_sha256'],
            head, str(old_archive), str(candidate_archive)]
    environment = {**os.environ, 'ZAPRET2_CI_REMOTE_WITNESS_ONLY': '1'}
    proc = subprocess.Popen(args, env=environment, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    try:
        need(select.select([proc.stdout], [], [], TIMEOUT)[0],
             'CI_LIVE_WITNESS_START_TIMED_OUT')
        line = proc.stdout.readline().strip()
        need(re.fullmatch(r'CI_WITNESS_PORT=[1-9][0-9]{0,4}', line) is not None,
             'CI_LIVE_WITNESS_LISTENER_NOT_AUTHENTIC:' + line[:80])
        port = int(line.split('=', 1)[1])
        need(0 < port < 65536 and proc.poll() is None,
             'CI_LIVE_WITNESS_INVALID_LISTENER')
        endpoint = folder / 'endpoint.json'
        fd = os.open(endpoint, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as out:
            out.write((json.dumps({'port': port, 'server_sha256': cert_sha,
                                   'head': head, 'client_sha256': ticket['client_sha256'],
                                   'nonce_sha256': hashlib.sha256(nonce.encode()).hexdigest()},
                                  sort_keys=True) + '\n').encode())
            out.flush()
            os.fsync(out.fileno())
        return proc
    except BaseException:
        stop(proc)
        raise


def stop(proc):
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
    if proc.stdout:
        proc.stdout.close()
    if proc.stderr:
        proc.stderr.close()


def endpoint(root, head, ticket, nonce):
    folder = private_root(root)
    value = json.loads(owned_bytes(folder / 'endpoint.json'))
    need(type(value) is dict and set(value) == {'port', 'server_sha256', 'head',
                                                'client_sha256','nonce_sha256'} and
         type(nonce) is str and NONCE.fullmatch(nonce) is not None and
         value['nonce_sha256'] == hashlib.sha256(nonce.encode()).hexdigest() and
         value['head'] == head and
         value['client_sha256'] == ticket['client_sha256'] and
         type(value['port']) is int and 0 < value['port'] < 65536 and
         type(value['server_sha256']) is str and
         SHA.fullmatch(value['server_sha256']) is not None,
         'CI_LIVE_WITNESS_ENDPOINT_NOT_BOUND')
    return value


def restart(root, ticket, head, old_archive, candidate_archive, nonce, proc):
    """Test-only witness recovery without erasing committed SQLite state.

    Callers still require a fresh signed STATUS under the inherited FD9.
    A failed replacement leaves no endpoint and no bypass.
    """
    need(mode() and isinstance(proc, subprocess.Popen),
         'CI_LIVE_WITNESS_RESTART_DISPOSABLE_PROC_REQUIRED')
    folder = private_root(root)
    endpoint(root, head, ticket, nonce)
    stop(proc)
    owned_bytes(folder / 'endpoint.json')
    (folder / 'endpoint.json').unlink()
    return start(root, ticket, head, old_archive, candidate_archive, nonce,
                 resume=True)


def make_request(action, expected, head, nonce, drop=False):
    need(type(head) is str and COMMIT.fullmatch(head) is not None and
         type(nonce) is str and NONCE.fullmatch(nonce) is not None,
         'CI_LIVE_WITNESS_TICKET_NONCE_INVALID')
    challenge = hashlib.sha256(
        ('fd9-ci-live|' + head + '|' + nonce + '|' +
         secrets.token_hex(32)).encode()).hexdigest()
    request = {'action': action, **expected, 'challenge_sha256': challenge}
    if drop:
        request['drop_after_commit'] = True
    return request


def exchange(root, ticket, head, nonce, fd9_check, phase, drop_consume=False):
    """RESERVE->CONSUME or fresh STATUS strictly under original FD9.

    A timed-out CONSUME is *not* accepted. A fresh challenged STATUS must
    return signed CONSUMED, from the same durable operation, or we refuse.
    """
    need(mode() and phase in ('consume', 'status') and callable(fd9_check),
         'CI_LIVE_WITNESS_PHASE_OR_FD9_REQUIRED')
    folder = private_root(root)
    ep = endpoint(root, head, ticket, nonce)
    guard = load('stage3-native-configd-operator-grant-ci.py')
    status = load('stage3-prepkg-signed-status.py')
    witness = load('stage3-prepkg-remote-witness-ci.py')
    expected = guard.expected_identity(head, ticket['checkpoint_sha256'],
                                       ticket['payload_sha256'],nonce)
    need(all(expected[k] == ticket[k] for k in expected),
         'CI_LIVE_WITNESS_OPERATION_SCOPE_DRIFT')
    public = status.private_read(str(Path(root) / 'ci-operator-grant' /
                                     'status-public.pem'), status.MAX_KEY)

    def send(action, drop=False):
        req = make_request(action, expected, head, nonce, drop=drop)
        fd9_check()
        raw, signature = witness.request(ep['port'], req, str(folder / 'ca.crt'),
                                         str(folder / 'client.crt'),
                                         str(folder / 'client.key'),
                                         ep['server_sha256'])
        untrusted = status.strict_json(raw)
        need(type(untrusted) is dict and
             type(untrusted.get('witness_sequence')) is int and
             untrusted['witness_sequence'] ==
             expected['checkpoint_sequence'] + (1 if action == 'RESERVE' else 2),
             'CI_LIVE_WITNESS_WITNESS_SEQUENCE_INVALID')
        proof = status.verify_response(raw, signature, public,
                                       ticket['status_sha256'],
                                       req['challenge_sha256'], expected['operation_id'],
                                       expected['payload_sha256'],
                                       expected['checkpoint_sha256'],
                                       expected['checkpoint_sequence'],
                                       untrusted['witness_sequence'], int(time.time()))
        need(proof['operation_action'] ==
             {'RESERVE': 'RESERVED', 'CONSUME': 'CONSUMED',
              'STATUS': 'CONSUMED'}[action] and
             proof['production_pkg_authorized'] is False and
             proof['independent_remote_witness_deployed'] is False and
             proof['witness_key_owner_approved'] is False,
             'CI_LIVE_WITNESS_UNQUALIFIED_SIGNED_STATUS')
        fd9_check()
        return untrusted['witness_sequence']

    if phase == 'consume':
        reservation = send('RESERVE')
        need(reservation >= expected['checkpoint_sequence'] + 1,
             'CI_LIVE_WITNESS_RESERVATION_SEQUENCE_INVALID')
        if drop_consume:
            try:
                send('CONSUME', drop=True)
            except (OSError, witness.Refusal, ValueError):
                pass  # Only a fresh signed STATUS can recover this ambiguity.
            else:
                raise Refusal('CI_LIVE_WITNESS_EXPECTED_LOST_REPLY')
            consumed = send('STATUS')
        else:
            consumed = send('CONSUME')
        need(consumed > reservation, 'CI_LIVE_WITNESS_CONSUMPTION_NOT_MONOTONIC')
    else:
        consumed = send('STATUS')
    need(consumed == expected['checkpoint_sequence'] + 2,
         'CI_LIVE_WITNESS_NO_CONSUMED_COMMIT')
    return {'ci_live_loopback_witness_consumed': True,
            'ci_external_witness_owner_approved': False,
            'ci_offhost_monotonic_store': False,
            'ci_production_pkg_authorized': False}


def confirm(root, ticket, head, nonce):
    """Controller's independent sqlite read-back after genuine native pkg."""
    folder = private_root(root)
    endpoint(root, head, ticket, nonce)
    database = folder / 'operations.sqlite'
    st = database.lstat()
    need(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid() and
         stat.S_IMODE(st.st_mode) == 0o600 and st.st_nlink == 1,
         'CI_LIVE_WITNESS_SQLITE_FILE_INVALID')
    con = sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True, timeout=5)
    try:
        rows = con.execute('SELECT op,payload,checkpoint,cpseq,state,witness_seq '
                           'FROM operations').fetchall()
        challenges = con.execute('SELECT count(*) FROM challenges').fetchone()[0]
        serial = con.execute('SELECT serial FROM metadata WHERE id=1').fetchone()[0]
    finally:
        con.close()
    need(len(rows) == 1 and rows[0] ==
         (ticket['operation_id'], ticket['payload_sha256'],
          ticket['checkpoint_sha256'], ticket['checkpoint_sequence'],
          'CONSUMED', serial) and
         serial == ticket['checkpoint_sequence'] + 2 and
         challenges in (3, 4),
         'CI_LIVE_WITNESS_ACTUAL_SQLITE_CONSUMPTION_NOT_PROVEN')
    return {'ci_real_sqlite_consumed': True, 'ci_challenges_consumed': challenges,
            'ci_status_signer_off_appliance': False,
            'ci_owner_approval_authenticated': False}


def cleanup(root):
    """Only remove strictly owned, CI-generated fixture files after stop()."""
    folder = private_root(root)
    known = {'ca.key', 'ca.crt', 'ca.srl', 'server.key', 'server.csr',
             'server.crt', 'server.ext', 'client.key', 'client.csr',
             'client.crt', 'client.ext', 'status.key', 'endpoint.json',
             'operations.sqlite'}
    actual = {p.name for p in folder.iterdir()}
    need(actual == known, 'CI_LIVE_WITNESS_FOREIGN_OR_MISSING_CLEANUP_FILE')
    for name in known:
        path = folder / name
        st = path.lstat()
        need(stat.S_ISREG(st.st_mode) and st.st_uid == os.geteuid() and
             st.st_nlink == 1 and stat.S_IMODE(st.st_mode) == 0o600,
             'CI_LIVE_WITNESS_CLEANUP_FILE_FOREIGN:' + name)
    for name in known:
        (folder / name).unlink()
    folder.rmdir()
